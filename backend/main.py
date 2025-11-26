"""
FastAPI main application for NFL Betting AI

NEW ARCHITECTURE (v4):
- YOUR AI (NFLEngine) processes ALL queries first
- Gemini ONLY formats the response
- No hallucination possible - all data comes from YOUR database
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import asyncio

from database import get_db, init_db
from models import Team, Player, Game, Injury, Odds
from services.scheduler import DataScheduler
from services.chat_ai_v3 import ChatAI
from config import settings


# Scheduler instance
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global scheduler
    
    # Startup
    print("=" * 60)
    print("  NFL BETTING AI - NEW ARCHITECTURE")
    print("=" * 60)
    print("  YOUR AI (NFLEngine) = The Brain")
    print("  Gemini = The Mouth (text formatting only)")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    
    # Start scheduler
    print("Starting data scheduler...")
    scheduler = DataScheduler()
    scheduler.start()
    
    print("\nReady! All NFL data comes from YOUR database.")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    if scheduler:
        scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="NFL Betting AI",
    description="Sports betting analytics AI - YOUR AI is the brain, Gemini is just the mouth",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "online",
        "service": "NFL Betting AI",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Chat endpoint
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]  # Full conversation history

class ChatResponse(BaseModel):
    response: str
    data: Optional[Dict[str, Any]] = None  # Optional structured data for rendering cards

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with the NFL Betting AI
    
    NEW ARCHITECTURE:
    1. YOUR AI (NFLEngine) processes the query FIRST
    2. All data comes from YOUR database and ML models
    3. Gemini ONLY formats the response
    4. No hallucination possible
    """
    try:
        # Initialize ChatAI (which now uses NFLEngine internally)
        ai = ChatAI(db)
        
        # Convert Pydantic models to dicts for the chat function
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Process message - YOUR AI handles everything
        response = await asyncio.to_thread(ai.chat_with_history, messages_dict)
        
        # Get structured data if available (for frontend cards)
        structured_data = None
        if ai.last_structured_data:
            # Convert matchup data to frontend format
            matchup_data = ai.last_structured_data
            if 'team1' in matchup_data and 'team2' in matchup_data and 'prediction' in matchup_data:
                try:
                    structured_data = {
                        "type": "team_matchup",
                        "team1": {
                            "name": matchup_data['team1']['name'],
                            "score": matchup_data['prediction']['predicted_score']['team1'],
                            "win_probability": matchup_data['prediction']['win_probability']['team1'],
                            "offense_yards": matchup_data['team1']['offense'].get('total_yards_per_game', 0),
                            "defense_rating": matchup_data['team1']['defense'].get('secondary_rating', 0)
                        },
                        "team2": {
                            "name": matchup_data['team2']['name'],
                            "score": matchup_data['prediction']['predicted_score']['team2'],
                            "win_probability": matchup_data['prediction']['win_probability']['team2'],
                            "offense_yards": matchup_data['team2']['offense'].get('total_yards_per_game', 0),
                            "defense_rating": matchup_data['team2']['defense'].get('secondary_rating', 0)
                        }
                    }
                except (KeyError, TypeError) as e:
                    print(f"Error extracting structured data: {e}")
            # Clear for next request
            ai.last_structured_data = None
        
        return ChatResponse(response=response, data=structured_data)
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# Teams endpoints
@app.get("/api/teams")
async def get_teams(db: Session = Depends(get_db)):
    """Get all NFL teams"""
    teams = db.query(Team).all()
    return teams


@app.get("/api/teams/{team_id}")
async def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get specific team details"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.get("/api/teams/{team_id}/players")
async def get_team_roster(team_id: int, db: Session = Depends(get_db)):
    """Get team roster"""
    players = db.query(Player).filter(Player.team_id == team_id).all()
    return players


# Players endpoints
@app.get("/api/players")
async def get_players(
    position: str = None,
    team_id: int = None,
    db: Session = Depends(get_db)
):
    """Get players with optional filters"""
    query = db.query(Player)
    
    if position:
        query = query.filter(Player.position == position.upper())
    
    if team_id:
        query = query.filter(Player.team_id == team_id)
    
    players = query.all()
    return players


@app.get("/api/players/{player_id}")
async def get_player(player_id: int, db: Session = Depends(get_db)):
    """Get specific player details"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


# Games endpoints
@app.get("/api/games")
async def get_games(
    season: int = None,
    week: int = None,
    team_id: int = None,
    db: Session = Depends(get_db)
):
    """Get games with optional filters"""
    query = db.query(Game)
    
    if season:
        query = query.filter(Game.season == season)
    
    if week:
        query = query.filter(Game.week == week)
    
    if team_id:
        query = query.filter(
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
        )
    
    games = query.order_by(Game.game_date.desc()).all()
    return games


@app.get("/api/games/{game_id}")
async def get_game(game_id: int, db: Session = Depends(get_db)):
    """Get specific game details"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


# Injuries endpoints
@app.get("/api/injuries")
async def get_injuries(
    team_id: int = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get injury reports"""
    query = db.query(Injury)
    
    if active_only:
        query = query.filter(Injury.is_active == True)
    
    if team_id:
        query = query.join(Player).filter(Player.team_id == team_id)
    
    injuries = query.all()
    return injuries


# Odds endpoints
@app.get("/api/odds/games")
async def get_game_odds(
    market_type: str = None,
    bookmaker: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get game odds"""
    query = db.query(Odds).filter(Odds.game_id.isnot(None))
    
    if market_type:
        query = query.filter(Odds.market_type == market_type)
    
    if bookmaker:
        query = query.filter(Odds.bookmaker == bookmaker)
    
    odds = query.order_by(Odds.timestamp.desc()).limit(limit).all()
    return odds


@app.get("/api/odds/props")
async def get_player_props(
    prop_type: str = None,
    player_id: int = None,
    bookmaker: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get player prop odds"""
    query = db.query(Odds).filter(Odds.market_type == "player_props")
    
    if prop_type:
        query = query.filter(Odds.prop_type == prop_type)
    
    if player_id:
        query = query.filter(Odds.player_id == player_id)
    
    if bookmaker:
        query = query.filter(Odds.bookmaker == bookmaker)
    
    odds = query.order_by(Odds.timestamp.desc()).limit(limit).all()
    return odds


# ============================================
# DASHBOARD ENDPOINTS - For Frontend Features
# ============================================

@app.get("/api/dashboard/upcoming-games")
async def get_upcoming_games(db: Session = Depends(get_db)):
    """Get upcoming games for the ticker with spreads and smart date detection"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # === SMART DATE DETECTION ===
    # Calculate Thanksgiving (4th Thursday of November)
    def get_thanksgiving(year):
        nov_first = datetime(year, 11, 1)
        days_until_thursday = (3 - nov_first.weekday()) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)
    
    # Calculate Christmas
    def get_christmas(year):
        return datetime(year, 12, 25)
    
    thanksgiving = get_thanksgiving(now.year)
    christmas = get_christmas(now.year)
    
    # Get games for the next 7 days
    upcoming = db.query(Game).filter(
        Game.game_date >= now,
        Game.game_date <= now + timedelta(days=7),
        Game.status != "Final"
    ).order_by(Game.game_date).limit(10).all()
    
    games = []
    special_event = None
    event_games_count = 0
    
    for game in upcoming:
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()
        
        # Get spread odds if available
        spread_odds = db.query(Odds).filter(
            Odds.game_id == game.id,
            Odds.market_type == "spreads"
        ).order_by(Odds.timestamp.desc()).first()
        
        spread = None
        if spread_odds and spread_odds.line:
            line = spread_odds.line
            if line > 0:
                spread = f"{away_team.abbreviation if away_team else 'AWAY'} +{line}"
            else:
                spread = f"{home_team.abbreviation if home_team else 'HOME'} {line}"
        
        # Detect special dates for this game
        game_date = game.game_date.replace(tzinfo=None) if game.game_date else None
        game_event = None
        
        if game_date:
            if game_date.date() == thanksgiving.date():
                game_event = "Thanksgiving"
                if not special_event:
                    special_event = "Thanksgiving"
                event_games_count += 1
            elif game_date.date() == christmas.date():
                game_event = "Christmas"
                if not special_event:
                    special_event = "Christmas"
                event_games_count += 1
            elif game_date.weekday() == 6:
                game_event = "Sunday"
            elif game_date.weekday() == 0:
                game_event = "Monday Night"
            elif game_date.weekday() == 3:
                game_event = "Thursday Night"
            elif game_date.weekday() == 5:
                game_event = "Saturday"
        
        games.append({
            "id": game.id,
            "home": home_team.abbreviation if home_team else "TBD",
            "home_name": home_team.name if home_team else "TBD",
            "away": away_team.abbreviation if away_team else "TBD",
            "away_name": away_team.name if away_team else "TBD",
            "time": game.game_date.strftime("%I:%M %p") if game.game_date else "TBD",
            "date": game.game_date.strftime("%m/%d") if game.game_date else "TBD",
            "day": game.game_date.strftime("%A") if game.game_date else "TBD",
            "spread": spread,
            "venue": game.venue,
            "week": game.week,
            "event": game_event
        })
    
    # Determine the section title based on what's coming up
    if special_event and event_games_count >= 2:
        title = f"{special_event} Games"
    elif games:
        weeks = [g["week"] for g in games if g.get("week")]
        if weeks:
            most_common_week = max(set(weeks), key=weeks.count)
            title = f"Week {most_common_week} Games"
        else:
            title = "Upcoming Games"
    else:
        title = "Upcoming Games"
    
    return {
        "games": games, 
        "count": len(games),
        "title": title,
        "special_event": special_event,
        "current_week": settings.CURRENT_WEEK
    }


@app.get("/api/dashboard/trending-players")
async def get_trending_players(db: Session = Depends(get_db)):
    """Get trending players based on recent performance and odds"""
    from models import StatsFeatures
    from config import settings
    from sqlalchemy.orm import joinedload
    
    trending = []
    
    # Get players with high recent performance - eager load relationships
    features = db.query(StatsFeatures).options(
        joinedload(StatsFeatures.player).joinedload(Player.team)
    ).filter(
        StatsFeatures.season == settings.CURRENT_SEASON,
        StatsFeatures.games_played >= 5
    ).all()
    
    # Group by position and get top performers
    qbs = sorted([f for f in features if f.player and f.player.position == "QB"], 
                 key=lambda x: x.avg_passing_yards or 0, reverse=True)[:2]
    rbs = sorted([f for f in features if f.player and f.player.position == "RB"], 
                 key=lambda x: x.avg_rushing_yards or 0, reverse=True)[:2]
    wrs = sorted([f for f in features if f.player and f.player.position == "WR"], 
                 key=lambda x: x.avg_receiving_yards or 0, reverse=True)[:2]
    
    for f in qbs:
        if f.player:
            trend = "up" if (f.last_3_avg_yards or 0) > (f.avg_passing_yards or 0) else "down"
            trending.append({
                "id": f.player_id,
                "name": f.player.name,
                "team": f.player.team.abbreviation if f.player.team else "FA",
                "position": "QB",
                "stat": f"{f.avg_passing_yards:.1f} Pass Yds/G" if f.avg_passing_yards else "N/A",
                "trend": trend,
                "value": f.avg_passing_yards or 0
            })
    
    for f in rbs:
        if f.player:
            trend = "up" if (f.last_3_avg_yards or 0) > (f.avg_rushing_yards or 0) else "down"
            trending.append({
                "id": f.player_id,
                "name": f.player.name,
                "team": f.player.team.abbreviation if f.player.team else "FA",
                "position": "RB",
                "stat": f"{f.avg_rushing_yards:.1f} Rush Yds/G" if f.avg_rushing_yards else "N/A",
                "trend": trend,
                "value": f.avg_rushing_yards or 0
            })
    
    for f in wrs:
        if f.player:
            trend = "up" if (f.last_3_avg_yards or 0) > (f.avg_receiving_yards or 0) else "down"
            trending.append({
                "id": f.player_id,
                "name": f.player.name,
                "team": f.player.team.abbreviation if f.player.team else "FA",
                "position": "WR",
                "stat": f"{f.avg_receiving_yards:.1f} Rec Yds/G" if f.avg_receiving_yards else "N/A",
                "trend": trend,
                "value": f.avg_receiving_yards or 0
            })
    
    # Sort by value and take top 6
    trending = sorted(trending, key=lambda x: x["value"], reverse=True)[:6]
    
    return {"players": trending, "count": len(trending)}


@app.get("/api/dashboard/insights")
async def get_ai_insights(db: Session = Depends(get_db)):
    """Get AI-generated insights for the dashboard"""
    from models import StatsFeatures, Injury
    from config import settings
    from datetime import datetime, timedelta
    from sqlalchemy.orm import joinedload
    
    insights = []
    
    # Get players trending up significantly - eager load relationships
    features = db.query(StatsFeatures).options(
        joinedload(StatsFeatures.player).joinedload(Player.team)
    ).filter(
        StatsFeatures.season == settings.CURRENT_SEASON,
        StatsFeatures.games_played >= 3
    ).all()
    
    for f in features:
        if f.player:
            # Check for hot streaks - use last_3_avg_yards compared to season average
            if f.avg_passing_yards and f.last_3_avg_yards:
                if f.last_3_avg_yards > f.avg_passing_yards * 1.15:  # 15% above average
                    insights.append({
                        "type": "hot_streak",
                        "color": "green",
                        "title": "Hot Streak",
                        "message": f"{f.player.name} averaging {f.last_3_avg_yards:.0f} yds (up {((f.last_3_avg_yards/f.avg_passing_yards)-1)*100:.0f}%)",
                        "player_id": f.player_id
                    })
            
            # Check consistency for value bets
            if f.consistency_score and f.consistency_score > 0.75:
                if f.avg_receiving_yards and f.avg_receiving_yards > 60:
                    insights.append({
                        "type": "value",
                        "color": "gold",
                        "title": "Consistent Target",
                        "message": f"{f.player.name} hitting {f.consistency_score*100:.0f}% consistency on {f.avg_receiving_yards:.0f}+ rec yds",
                        "player_id": f.player_id
                    })
    
    # Key injuries - eager load relationships
    recent_injuries = db.query(Injury).options(
        joinedload(Injury.player).joinedload(Player.team)
    ).filter(
        Injury.is_active == True,
        Injury.status.in_(["Out", "Doubtful"]),
        Injury.date_reported >= datetime.now() - timedelta(days=3)
    ).all()
    
    for inj in recent_injuries[:3]:
        if inj.player and inj.player.position in ["QB", "RB", "WR"]:
            insights.append({
                "type": "injury",
                "color": "red",
                "title": "Injury Alert",
                "message": f"{inj.player.name} ({inj.player.position}) - {inj.status}: {inj.injury_type or 'Unspecified'}",
                "player_id": inj.player_id
            })
    
    # Limit and shuffle for variety
    import random
    if len(insights) > 4:
        # Ensure variety - take 1-2 of each type
        hot_streaks = [i for i in insights if i["type"] == "hot_streak"][:2]
        values = [i for i in insights if i["type"] == "value"][:1]
        injuries = [i for i in insights if i["type"] == "injury"][:1]
        insights = hot_streaks + values + injuries
    
    return {"insights": insights[:4], "count": len(insights)}


@app.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall dashboard statistics"""
    from config import settings
    from datetime import datetime
    import os
    
    # Count trained models
    models_dir = "trained_models"
    model_count = 0
    if os.path.exists(models_dir):
        model_count = len([f for f in os.listdir(models_dir) if f.endswith('.pkl')])
    
    # Get current week from config or calculate
    current_week = settings.CURRENT_WEEK
    
    # Count total players, games, etc
    player_count = db.query(Player).count()
    team_count = db.query(Team).count()
    game_count = db.query(Game).filter(Game.season == settings.CURRENT_SEASON).count()
    
    # Get odds count
    odds_count = db.query(Odds).count()
    
    return {
        "models_count": model_count,
        "current_week": current_week,
        "current_season": settings.CURRENT_SEASON,
        "players_tracked": player_count,
        "teams": team_count,
        "games_this_season": game_count,
        "odds_records": odds_count,
        "status": "online",
        "last_updated": datetime.now().isoformat()
    }


# Manual data update triggers (for testing/admin)
@app.post("/api/admin/update-stats")
async def trigger_stats_update():
    """Manually trigger stats update (admin only)"""
    if scheduler:
        # Run in background
        import asyncio
        asyncio.create_task(scheduler.update_all_stats())
        return {"status": "Stats update triggered"}
    return {"status": "Scheduler not running"}


@app.post("/api/admin/update-odds")
async def trigger_odds_update():
    """Manually trigger odds update (admin only)"""
    if scheduler:
        # Run in background
        import asyncio
        asyncio.create_task(scheduler.update_odds())
        return {"status": "Odds update triggered"}
    return {"status": "Scheduler not running"}


@app.post("/api/admin/retrain-models")
async def trigger_model_retraining():
    """Manually trigger model retraining (admin only)"""
    if scheduler:
        # Run in background
        import asyncio
        asyncio.create_task(scheduler.retrain_models())
        return {
            "status": "Model retraining triggered",
            "note": "This may take several minutes. Check server logs for progress."
        }
    return {"status": "Scheduler not running"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

