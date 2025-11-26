"""
One-Time Odds Fetcher
Run this script manually to fetch current odds and store them in the database.
This does NOT use the scheduler - you control when to call the API to save credits.

Usage: python fetch_odds_once.py

Markets fetched:
- Game odds: moneyline (h2h), spreads, totals
- Player props: anytime TD, TDs over, passing yards/TDs/completions/attempts/INTs,
  rushing yards, receiving yards, receptions, combined yards, kicking

This fetches ALL available NFL games.
"""

import asyncio
from datetime import datetime, timedelta
from database import SessionLocal
from services.odds_fetcher import OddsFetcher
from models import Odds, Player, Game
from config import settings
import httpx


# Team name mappings (Odds API uses different names than ESPN)
TEAM_NAME_MAP = {
    # Odds API name -> ESPN name patterns
    "Arizona Cardinals": "Cardinals",
    "Atlanta Falcons": "Falcons",
    "Baltimore Ravens": "Ravens",
    "Buffalo Bills": "Bills",
    "Carolina Panthers": "Panthers",
    "Chicago Bears": "Bears",
    "Cincinnati Bengals": "Bengals",
    "Cleveland Browns": "Browns",
    "Dallas Cowboys": "Cowboys",
    "Denver Broncos": "Broncos",
    "Detroit Lions": "Lions",
    "Green Bay Packers": "Packers",
    "Houston Texans": "Texans",
    "Indianapolis Colts": "Colts",
    "Jacksonville Jaguars": "Jaguars",
    "Kansas City Chiefs": "Chiefs",
    "Las Vegas Raiders": "Raiders",
    "Los Angeles Chargers": "Chargers",
    "Los Angeles Rams": "Rams",
    "Miami Dolphins": "Dolphins",
    "Minnesota Vikings": "Vikings",
    "New England Patriots": "Patriots",
    "New Orleans Saints": "Saints",
    "New York Giants": "Giants",
    "New York Jets": "Jets",
    "Philadelphia Eagles": "Eagles",
    "Pittsburgh Steelers": "Steelers",
    "San Francisco 49ers": "49ers",
    "Seattle Seahawks": "Seahawks",
    "Tampa Bay Buccaneers": "Buccaneers",
    "Tennessee Titans": "Titans",
    "Washington Commanders": "Commanders",
}


def find_game_by_teams(db, home_team: str, away_team: str):
    """Find a game by team names, handling name variations"""
    # Try direct match first
    game = db.query(Game).filter(
        Game.home_team_name.ilike(f'%{home_team}%'),
        Game.away_team_name.ilike(f'%{away_team}%'),
        Game.game_date >= datetime.utcnow() - timedelta(hours=6)  # Include games from today
    ).first()
    
    if game:
        return game
    
    # Try with mapped names
    home_short = TEAM_NAME_MAP.get(home_team, home_team.split()[-1])
    away_short = TEAM_NAME_MAP.get(away_team, away_team.split()[-1])
    
    game = db.query(Game).filter(
        Game.home_team_name.ilike(f'%{home_short}%'),
        Game.away_team_name.ilike(f'%{away_short}%'),
        Game.game_date >= datetime.utcnow() - timedelta(hours=6)
    ).first()
    
    return game


# All the prop markets to fetch
PROP_MARKETS = [
    "player_anytime_td",
    "player_tds_over", 
    "player_pass_tds",
    "player_pass_yds",
    "player_pass_completions",
    "player_pass_attempts",
    "player_pass_interceptions",
    "player_rush_yds",
    "player_reception_yds",
    "player_receptions",
    "player_pass_rush_yds",
    "player_rush_reception_yds",
    "player_field_goals",
    "player_kicking_points",
    "player_pats"
]


async def fetch_and_store_odds():
    """Fetch odds for ALL NFL games and ALL markets, store in database"""
    
    # Check API key
    if not settings.ODDS_API_KEY:
        print("ERROR: ODDS_API_KEY not set in .env file!")
        print("Get your free API key at: https://the-odds-api.com/")
        return
    
    print("=" * 60)
    print("ONE-TIME ODDS FETCH - ALL GAMES, ALL MARKETS")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    print("\nMarkets to fetch:")
    print("  Game: moneyline, spreads, totals")
    print(f"  Props: {len(PROP_MARKETS)} markets")
    for market in PROP_MARKETS:
        print(f"    - {market}")
    
    fetcher = OddsFetcher()
    db = SessionLocal()
    
    try:
        # 1. Fetch game odds (moneyline, spreads, totals) for ALL games
        print("\n" + "-" * 60)
        print("[1/2] Fetching GAME ODDS for all NFL games...")
        print("-" * 60)
        game_odds = await fetcher.get_nfl_odds()
        print(f"\n  Found {len(game_odds)} NFL games with odds available")
        
        if game_odds:
            print("\n  Games found:")
            for game in game_odds:
                print(f"    - {game.get('away_team')} @ {game.get('home_team')}")
        
        game_odds_count = 0
        games_linked = 0
        games_not_found = []
        
        for game in game_odds:
            home_team = game.get("home_team", "")
            away_team = game.get("away_team", "")
            
            # Find the game in our database
            db_game = find_game_by_teams(db, home_team, away_team)
            game_id = db_game.id if db_game else None
            
            if game_id:
                games_linked += 1
            else:
                games_not_found.append(f"{away_team} @ {home_team}")
            
            for bookmaker in game.get("bookmakers", []):
                bookmaker_name = bookmaker.get("name", "")
                
                # Store moneyline
                if "moneyline" in bookmaker.get("markets", {}):
                    ml = bookmaker["markets"]["moneyline"]
                    odds_record = Odds(
                        game_id=game_id,
                        bookmaker=bookmaker_name,
                        market_type="moneyline",
                        home_odds=ml.get(home_team),
                        away_odds=ml.get(away_team),
                        timestamp=datetime.utcnow()
                    )
                    db.add(odds_record)
                    game_odds_count += 1
                
                # Store spreads
                if "spreads" in bookmaker.get("markets", {}):
                    spreads = bookmaker["markets"]["spreads"]
                    for team, data in spreads.items():
                        odds_record = Odds(
                            game_id=game_id,
                            bookmaker=bookmaker_name,
                            market_type="spread",
                            line=data.get("point"),
                            home_odds=data.get("price") if team == home_team else None,
                            away_odds=data.get("price") if team == away_team else None,
                            timestamp=datetime.utcnow()
                        )
                        db.add(odds_record)
                        game_odds_count += 1
                
                # Store totals
                if "totals" in bookmaker.get("markets", {}):
                    totals = bookmaker["markets"]["totals"]
                    for direction, data in totals.items():
                        odds_record = Odds(
                            game_id=game_id,
                            bookmaker=bookmaker_name,
                            market_type="total",
                            line=data.get("point"),
                            over_odds=data.get("price") if direction == "Over" else None,
                            under_odds=data.get("price") if direction == "Under" else None,
                            timestamp=datetime.utcnow()
                        )
                        db.add(odds_record)
                        game_odds_count += 1
        
        db.commit()
        print(f"\n  Stored {game_odds_count} game odds records")
        print(f"  Games linked to DB: {games_linked}/{len(game_odds)}")
        if games_not_found:
            print(f"  Games NOT found in DB ({len(games_not_found)}):")
            for g in games_not_found[:5]:
                print(f"    - {g}")
        
        # 2. Fetch player props for ALL markets (must be fetched per-event)
        print("\n" + "-" * 60)
        print("[2/2] Fetching PLAYER PROPS for all games...")
        print("-" * 60)
        
        all_markets = ",".join(PROP_MARKETS)
        print(f"\n  Markets: {len(PROP_MARKETS)} prop types")
        print("  Note: Player props must be fetched per-game (API requirement)")
        
        # Get list of all events first
        events_url = f"{settings.ODDS_API_BASE_URL}/sports/americanfootball_nfl/events"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            events_response = await client.get(events_url, params={"apiKey": settings.ODDS_API_KEY})
            events = events_response.json() if events_response.status_code == 200 else []
            
            print(f"\n  Found {len(events)} NFL events (games)")
            
            remaining = events_response.headers.get("x-requests-remaining", "?")
            used = events_response.headers.get("x-requests-used", "?")
            print(f"  API Quota - Used: {used}, Remaining: {remaining}")
            
            if not events:
                print("  No events found, skipping props")
                props = []
            else:
                # Fetch props for each event
                props = []
                
                # Limit games to save API credits (set to None for all games)
                # Set to None to fetch ALL games, or a number to limit
                MAX_GAMES_FOR_PROPS = None  # Fetch ALL games for complete odds data
                games_to_fetch = events[:MAX_GAMES_FOR_PROPS] if MAX_GAMES_FOR_PROPS else events
                
                print(f"\n  Fetching props for {len(games_to_fetch)} games (this uses 1 API call per game)...")
                if MAX_GAMES_FOR_PROPS and len(events) > MAX_GAMES_FOR_PROPS:
                    print(f"  (Limited to {MAX_GAMES_FOR_PROPS} games to save API credits)")
                
                for i, event in enumerate(games_to_fetch):
                    event_id = event.get("id")
                    home = event.get("home_team", "?")
                    away = event.get("away_team", "?")
                    
                    # Find the game_id for this event
                    db_game = find_game_by_teams(db, home, away)
                    event_game_id = db_game.id if db_game else None
                    
                    print(f"    [{i+1}/{len(games_to_fetch)}] {away} @ {home}...", end=" ")
                    
                    # Fetch odds for this specific event with player props
                    event_odds_url = f"{settings.ODDS_API_BASE_URL}/sports/americanfootball_nfl/events/{event_id}/odds"
                    
                    try:
                        props_response = await client.get(event_odds_url, params={
                            "apiKey": settings.ODDS_API_KEY,
                            "regions": "us",
                            "markets": all_markets,
                            "oddsFormat": "american"
                        })
                        
                        if props_response.status_code == 200:
                            event_data = props_response.json()
                            
                            # Parse bookmakers and markets
                            for bookmaker in event_data.get("bookmakers", []):
                                bookmaker_name = bookmaker.get("key", "")
                                
                                for market in bookmaker.get("markets", []):
                                    market_key = market.get("key", "")
                                    
                                    for outcome in market.get("outcomes", []):
                                        prop = {
                                            "game_id": event_game_id,
                                            "home_team": home,
                                            "away_team": away,
                                            "bookmaker": bookmaker_name,
                                            "prop_type": market_key,
                                            "player_name": outcome.get("description", ""),
                                            "line": outcome.get("point"),
                                            "over_under": outcome.get("name"),
                                            "odds": outcome.get("price")
                                        }
                                        props.append(prop)
                            
                            linked_str = "linked" if event_game_id else "NO GAME ID"
                            print(f"OK ({linked_str})")
                        else:
                            print(f"Error {props_response.status_code}")
                            
                    except Exception as e:
                        print(f"Error: {e}")
                
                # Update quota info
                remaining = props_response.headers.get("x-requests-remaining", "?") if 'props_response' in dir() else "?"
                used = props_response.headers.get("x-requests-used", "?") if 'props_response' in dir() else "?"
                print(f"\n  API Quota after props - Used: {used}, Remaining: {remaining}")
        
        print(f"\n  Received {len(props)} player prop lines total")
        
        # Group by market type for summary
        market_counts = {}
        props_count = 0
        players_found = set()
        
        for prop in props:
            player_name = prop.get("player_name", "")
            prop_type = prop.get("prop_type", "")
            
            # Count by market
            market_counts[prop_type] = market_counts.get(prop_type, 0) + 1
            
            # Try to find player in our database
            player = db.query(Player).filter(
                Player.name.ilike(f'%{player_name}%')
            ).first()
            
            player_id = player.id if player else None
            if player:
                players_found.add(player_name)
            
            # Store the prop (player_name stored via player_id relationship)
            # Handle different prop types:
            # - Anytime TD: outcome is "Yes" or player name, odds go in over_odds
            # - Most props: outcome is "Over" or "Under"
            over_under = prop.get("over_under", "")
            odds_value = prop.get("odds")
            
            # For Anytime TD, the outcome is usually "Yes" or the player's name
            is_anytime_td = "anytime_td" in prop_type.lower()
            
            if is_anytime_td:
                # Anytime TD - store odds in over_odds (means "Yes, they will score")
                over_odds = odds_value
                under_odds = None
            elif over_under == "Over":
                over_odds = odds_value
                under_odds = None
            elif over_under == "Under":
                over_odds = None
                under_odds = odds_value
            else:
                # Unknown format - store in over_odds by default
                over_odds = odds_value
                under_odds = None
            
            odds_record = Odds(
                game_id=prop.get("game_id"),
                player_id=player_id,
                bookmaker=prop.get("bookmaker", ""),
                market_type="player_props",
                prop_type=prop_type,
                line=prop.get("line"),
                over_odds=over_odds,
                under_odds=under_odds,
                timestamp=datetime.utcnow()
            )
            db.add(odds_record)
            props_count += 1
        
        db.commit()
        
        # Show breakdown by market
        print("\n  Props by market:")
        for market, count in sorted(market_counts.items()):
            print(f"    - {market}: {count} lines")
        
        print(f"\n  Total stored: {props_count} player prop records")
        print(f"  Matched {len(players_found)} players to our database")
        
        # Summary
        print("\n" + "=" * 60)
        print("FETCH COMPLETE!")
        print("=" * 60)
        print(f"  Games found: {len(game_odds)}")
        print(f"  Game Odds stored: {game_odds_count} records")
        print(f"  Player Props stored: {props_count} records")
        print(f"  Total new records: {game_odds_count + props_count}")
        print(f"  Players matched to DB: {len(players_found)}")
        print(f"\nThe AI can now compare predictions to sportsbook lines!")
        print("Run this script again anytime you want fresh odds data.")
        
        # Show API quota
        print("\n" + "-" * 60)
        print("API QUOTA INFO")
        print("-" * 60)
        print("Check your usage at: https://the-odds-api.com/account/")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def clear_old_odds():
    """Clear all old odds from database before fresh fetch"""
    db = SessionLocal()
    try:
        count = db.query(Odds).delete()
        db.commit()
        print(f"Cleared {count} old odds records")
    finally:
        db.close()


def show_current_odds_count():
    """Show how many odds records are in the database"""
    db = SessionLocal()
    try:
        total = db.query(Odds).count()
        game_odds = db.query(Odds).filter(Odds.market_type != "player_props").count()
        props = db.query(Odds).filter(Odds.market_type == "player_props").count()
        
        print("\nCurrent odds in database:")
        print(f"  Game odds: {game_odds}")
        print(f"  Player props: {props}")
        print(f"  Total: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("NFL ODDS FETCHER")
    print("=" * 60)
    
    print("\nChecking current odds data...")
    show_current_odds_count()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        response = sys.argv[1]
    else:
        print("\nOptions:")
        print("  1. Fetch fresh odds (keeps existing)")
        print("  2. Clear old odds, then fetch fresh")
        print("  3. Just clear old odds")
        print("  4. Cancel")
        
        print("\nChoose option (1-4):")
        response = input("> ").strip()
    
    if response == '1':
        print("\nFetching fresh odds...")
        asyncio.run(fetch_and_store_odds())
    elif response == '2':
        print("\nClearing old odds...")
        asyncio.run(clear_old_odds())
        print("\nFetching fresh odds...")
        asyncio.run(fetch_and_store_odds())
    elif response == '3':
        print("\nClearing old odds...")
        asyncio.run(clear_old_odds())
        print("Done!")
    else:
        print("Cancelled. Run again when ready.")

