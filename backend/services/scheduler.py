"""
Task scheduler for automated data updates
- Stats updates: Daily at 11:59 PM
- Odds updates: 11 AM, 3 PM, 5 PM, 7 PM, 8 PM
- Model retraining: Weekly on Tuesdays at 3:00 AM
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from config import settings
from services.espn_fetcher import ESPNFetcher
from services.odds_fetcher import OddsFetcher
from database import SessionLocal
from models import Team, Player, Game, PlayerStats, Odds, Injury
import asyncio


class DataScheduler:
    """Manages scheduled data updates"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone(settings.TIMEZONE)
        self.espn_fetcher = ESPNFetcher()
        self.odds_fetcher = OddsFetcher()
        
    def start(self):
        """Start the scheduler"""
        self._schedule_stats_update()
        # self._schedule_odds_updates()  # DISABLED - Uncomment to re-enable odds updates
        self._schedule_injury_update()
        self._schedule_model_retraining()
        self._schedule_continuous_learning()
        self.scheduler.start()
        print(f"Scheduler started in timezone: {settings.TIMEZONE}")
        print(f"Stats update scheduled for: {settings.STATS_UPDATE_TIME}")
        # print(f"Odds updates scheduled for: {settings.ODDS_UPDATE_TIMES}")  # DISABLED
        print(f"Injury updates scheduled for: Daily at 12:00 PM")
        print(f"Model retraining scheduled for: Tuesdays at 3:00 AM")
        print(f"Continuous Learning scheduled for: Tuesdays at 4:00 AM (after retraining)")
        print(f"\n⚠️  ODDS UPDATES ARE CURRENTLY DISABLED")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        print("Scheduler stopped")
    
    def _schedule_stats_update(self):
        """Schedule daily stats update at 11:59 PM"""
        # Parse time from config (format: "HH:MM")
        hour, minute = map(int, settings.STATS_UPDATE_TIME.split(":"))
        
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=self.timezone
        )
        
        self.scheduler.add_job(
            self.update_all_stats,
            trigger=trigger,
            id="stats_update",
            name="Daily Stats Update",
            replace_existing=True
        )
    
    def _schedule_odds_updates(self):
        """Schedule odds updates at game-time intervals (only on game days)"""
        # Parse times from config (format: "HH:MM,HH:MM,...")
        times = settings.ODDS_UPDATE_TIMES.split(",")
        
        for idx, time_str in enumerate(times):
            hour, minute = map(int, time_str.strip().split(":"))
            
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.timezone
            )
            
            self.scheduler.add_job(
                self.update_odds_if_game_day,
                trigger=trigger,
                id=f"odds_update_{idx}",
                name=f"Odds Update {time_str} (game days only)",
                replace_existing=True
            )
    
    def _schedule_injury_update(self):
        """Schedule daily injury update at 12:00 PM"""
        trigger = CronTrigger(
            hour=12,
            minute=0,
            timezone=self.timezone
        )
        
        self.scheduler.add_job(
            self.update_injuries,
            trigger=trigger,
            id="injury_update",
            name="Daily Injury Update",
            replace_existing=True
        )
    
    def _schedule_model_retraining(self):
        """Schedule weekly model retraining on Tuesday at 3 AM"""
        trigger = CronTrigger(
            day_of_week='tue',  # Tuesday (day after Monday Night Football)
            hour=3,
            minute=0,
            timezone=self.timezone
        )
        
        self.scheduler.add_job(
            self.retrain_models,
            trigger=trigger,
            id="model_retraining",
            name="Weekly Model Retraining",
            replace_existing=True
        )
    
    def _schedule_continuous_learning(self):
        """Schedule weekly continuous learning analysis on Tuesday at 4 AM (after retraining)"""
        trigger = CronTrigger(
            day_of_week='tue',  # Tuesday - runs 1 hour after retraining
            hour=4,
            minute=0,
            timezone=self.timezone
        )
        
        self.scheduler.add_job(
            self.run_continuous_learning,
            trigger=trigger,
            id="continuous_learning",
            name="Weekly Continuous Learning Analysis",
            replace_existing=True
        )
    
    async def update_all_stats(self):
        """
        Main stats update job - runs daily at 11:59 PM
        Updates: teams, players, games, injuries, and player stats
        """
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] Starting daily stats update...")
        print(f"{'='*60}\n")
        
        db = SessionLocal()
        
        try:
            # 1. Update teams
            await self._update_teams(db)
            
            # 2. Update injuries
            await self._update_injuries(db)
            
            # 3. Update games and scores
            await self._update_games(db)
            
            # 4. Update player stats for completed games
            await self._update_player_stats(db)
            
            # 5. Compute features for machine learning
            self._compute_features(db)
            
            db.commit()
            print(f"\n[{datetime.now()}] Stats update completed successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"\n[{datetime.now()}] ERROR during stats update: {e}")
            raise
        finally:
            db.close()
    
    async def _update_teams(self, db):
        """Update teams and rosters"""
        print("Updating teams and rosters...")
        teams_data = await self.espn_fetcher.get_all_teams()
        
        for team_data in teams_data:
            # Check if team exists
            team = db.query(Team).filter_by(espn_team_id=team_data["espn_team_id"]).first()
            
            if team:
                # Update existing team
                for key, value in team_data.items():
                    setattr(team, key, value)
            else:
                # Create new team
                team = Team(**team_data)
                db.add(team)
        
        db.commit()
        print(f"[OK] Updated {len(teams_data)} teams")
        
        # Update rosters for each team
        print("Updating player rosters...")
        teams = db.query(Team).all()
        total_players = 0
        
        for team in teams:
            team_details = await self.espn_fetcher.get_team_details(team.espn_team_id)
            roster = team_details.get("roster", [])
            
            for player_data in roster:
                player = db.query(Player).filter_by(
                    espn_player_id=player_data["espn_player_id"]
                ).first()
                
                if player:
                    # Update existing player
                    player.team_id = team.id
                    player.name = player_data["name"]
                    player.position = player_data["position"]
                    player.jersey_number = player_data.get("jersey_number")
                    player.headshot_url = player_data.get("headshot_url")
                else:
                    # Create new player
                    player = Player(
                        **player_data,
                        team_id=team.id
                    )
                    db.add(player)
                
                total_players += 1
            
            db.commit()
            await asyncio.sleep(0.5)  # Rate limiting
        
        print(f"[OK] Updated {total_players} players")
    
    async def _update_injuries(self, db):
        """Update injury reports"""
        print("Updating injury reports...")
        injuries_data = await self.espn_fetcher.get_injuries()
        
        # Mark all existing injuries as inactive first
        db.query(Injury).update({"is_active": False})
        
        for injury_data in injuries_data:
            # Find player by ESPN ID
            player = db.query(Player).filter_by(
                espn_player_id=injury_data["player_id"]
            ).first()
            
            if player:
                # Check if injury already exists
                injury = db.query(Injury).filter_by(
                    player_id=player.id,
                    is_active=True
                ).first()
                
                if injury:
                    # Update existing injury
                    injury.status = injury_data["status"]
                    injury.injury_type = injury_data["injury_type"]
                    injury.description = injury_data["description"]
                    injury.is_active = True
                else:
                    # Create new injury
                    injury = Injury(
                        player_id=player.id,
                        player_name=player.name,
                        status=injury_data["status"],
                        injury_type=injury_data["injury_type"],
                        description=injury_data["description"],
                        date_reported=injury_data["date_reported"],
                        is_active=True
                    )
                    db.add(injury)
        
        db.commit()
        print(f"[OK] Updated {len(injuries_data)} injuries")
    
    def _get_current_nfl_week(self, db=None) -> int:
        """Determine the current NFL week based on database or default to 13"""
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # Find the most recent completed game
            latest_game = db.query(Game).filter(
                Game.status == "STATUS_FINAL",
                Game.season == settings.CURRENT_SEASON
            ).order_by(Game.week.desc()).first()
            
            if latest_game:
                # Current week is the week after the last completed game
                return min(latest_game.week + 1, 18)
            
            # Default to week 13 if no games found
            return 13
        finally:
            if should_close:
                db.close()
    
    async def _update_games(self, db):
        """Update games and scores from scoreboard (current + upcoming weeks)"""
        print("Updating games and scores...")
        
        # Fetch current week and next 4 weeks to always have upcoming schedule
        current_week = self._get_current_nfl_week(db)
        print(f"  Current NFL week detected: {current_week}")
        all_games_data = []
        
        for week_offset in range(5):  # Current week + 4 weeks ahead
            week = current_week + week_offset
            if week > 18:  # NFL regular season ends at week 18
                break
            
            print(f"  Fetching Week {week}...")
            week_games = await self.espn_fetcher.get_scoreboard(season=settings.CURRENT_SEASON, week=week)
            all_games_data.extend(week_games)
            await asyncio.sleep(0.3)  # Rate limiting
        
        games_data = all_games_data
        
        for game_data in games_data:
            # Find teams
            home_team = db.query(Team).filter_by(
                espn_team_id=game_data["home_team_id"]
            ).first()
            away_team = db.query(Team).filter_by(
                espn_team_id=game_data["away_team_id"]
            ).first()
            
            if not home_team or not away_team:
                continue
            
            # Check if game exists
            game = db.query(Game).filter_by(
                espn_game_id=game_data["espn_game_id"]
            ).first()
            
            # Determine winner
            winner_team_id = None
            winner_team_name = None
            if game_data["home_score"] > game_data["away_score"]:
                winner_team_id = home_team.id
                winner_team_name = home_team.name
            elif game_data["away_score"] > game_data["home_score"]:
                winner_team_id = away_team.id
                winner_team_name = away_team.name
            
            if game:
                # Update existing game
                game.status = game_data["status"]
                game.home_score = game_data["home_score"]
                game.away_score = game_data["away_score"]
                game.home_team_name = home_team.name
                game.away_team_name = away_team.name
                game.winner_team_id = winner_team_id
                game.winner_team_name = winner_team_name
            else:
                # Create new game
                game = Game(
                    espn_game_id=game_data["espn_game_id"],
                    season=game_data["season"],
                    week=game_data["week"],
                    game_date=game_data["date"],
                    home_team_id=home_team.id,
                    home_team_name=home_team.name,
                    away_team_id=away_team.id,
                    away_team_name=away_team.name,
                    home_score=game_data["home_score"],
                    away_score=game_data["away_score"],
                    winner_team_id=winner_team_id,
                    winner_team_name=winner_team_name,
                    status=game_data["status"],
                    venue=game_data["venue"]
                )
                db.add(game)
        
        db.commit()
        print(f"[OK] Updated {len(games_data)} games")
    
    async def _update_player_stats(self, db):
        """Update player stats for completed games"""
        print("Updating player stats for completed games...")
        
        # Get recently completed games that don't have stats yet
        completed_games = db.query(Game).filter(
            Game.status == "final"
        ).all()
        
        stats_count = 0
        for game in completed_games[:10]:  # Limit to 10 most recent games to avoid rate limits
            # Check if we already have stats for this game
            existing_stats = db.query(PlayerStats).filter_by(game_id=game.id).first()
            if existing_stats:
                continue
            
            print(f"  Fetching stats for game {game.espn_game_id}...")
            game_summary = await self.espn_fetcher.get_game_summary(game.espn_game_id)
            
            for player_stat in game_summary.get("players_stats", []):
                # Find player
                player = db.query(Player).filter_by(
                    espn_player_id=player_stat["player_id"]
                ).first()
                
                if not player:
                    continue
                
                # Parse stats
                stats = player_stat.get("stats", {})
                
                # Helper function to safely parse defensive stats
                def parse_defensive_stat(value, is_float=False):
                    if not value or value == '0':
                        return 0.0 if is_float else 0
                    try:
                        # Handle strings like "1-5" (sacks-yards) - take first number
                        if isinstance(value, str) and '-' in value:
                            value = value.split('-')[0]
                        return float(value) if is_float else int(float(value))
                    except (ValueError, TypeError):
                        return 0.0 if is_float else 0
                
                # Determine if this is a defensive player
                # Defensive positions: LB, CB, S, DE, DT, DB, OLB, MLB, ILB, SS, FS, NT, DL
                is_defensive = player.position in ['LB', 'CB', 'S', 'DE', 'DT', 'DB', 'OLB', 'MLB', 'ILB', 'SS', 'FS', 'NT', 'DL']
                
                # Create player stats record with offensive and defensive stats
                player_stats = PlayerStats(
                    player_id=player.id,
                    player_name=player.name,  # Include player name for easy viewing
                    player_position=player.position,  # Include player position for AI context
                    game_id=game.id,
                    # Offensive Stats (for offensive players)
                    passing_yards=float(stats.get("passing_yards", 0) or 0),
                    passing_completions=int(stats.get("completions", 0) or 0),
                    passing_attempts=int(stats.get("passing_attempts", 0) or 0),
                    passing_touchdowns=int(stats.get("passing_touchdowns", 0) or 0),
                    interceptions=int(stats.get("interceptions", 0) or 0),  # QB interceptions THROWN (negative stat)
                    sacks_taken=parse_defensive_stat(stats.get("sacks") or stats.get("sack"), is_float=True) if not is_defensive else 0.0,  # Times QB was SACKED (negative stat)
                    rushing_yards=float(stats.get("rushing_yards", 0) or 0),
                    rushing_attempts=int(stats.get("rushing_attempts", 0) or 0),
                    rushing_touchdowns=int(stats.get("rushing_touchdowns", 0) or 0),
                    receptions=int(stats.get("receptions", 0) or 0),
                    receiving_yards=float(stats.get("receiving_yards", 0) or 0),
                    receiving_targets=int(stats.get("targets", 0) or 0),
                    receiving_touchdowns=int(stats.get("receiving_touchdowns", 0) or 0),
                    # Defensive Stats (ONLY for defensive positions)
                    # For QBs/offensive players, sacks/INTs represent negative stats (sacked, threw INT) so we skip them
                    tackles_total=parse_defensive_stat(stats.get("total_tackles") or stats.get("tot")) if is_defensive else 0,
                    tackles_solo=parse_defensive_stat(stats.get("solo_tackles") or stats.get("solo")) if is_defensive else 0,
                    tackles_for_loss=parse_defensive_stat(stats.get("tackles_for_loss") or stats.get("tfl")) if is_defensive else 0,
                    sacks=parse_defensive_stat(stats.get("sacks") or stats.get("sack"), is_float=True) if is_defensive else 0.0,  # Sacks MADE by defender (positive stat)
                    qb_hits=parse_defensive_stat(stats.get("qb_hits") or stats.get("qbhits")) if is_defensive else 0,
                    interceptions_def=parse_defensive_stat(stats.get("int")) if is_defensive else 0,  # Defensive INTs CAUGHT (positive stat)
                    pass_deflections=parse_defensive_stat(stats.get("pass_deflections") or stats.get("pd")) if is_defensive else 0,
                    forced_fumbles=parse_defensive_stat(stats.get("forced_fumbles") or stats.get("ff")) if is_defensive else 0,
                    fumble_recoveries=parse_defensive_stat(stats.get("fumble_recoveries") or stats.get("fr")) if is_defensive else 0,
                    defensive_tds=parse_defensive_stat(stats.get("defensive_touchdowns")) if is_defensive else 0,
                    safeties=parse_defensive_stat(stats.get("safeties") or stats.get("sfty")) if is_defensive else 0
                )
                db.add(player_stats)
                stats_count += 1
            
            db.commit()
            await asyncio.sleep(1)  # Rate limiting
        
        print(f"[OK] Updated stats for {stats_count} player performances")
    
    async def update_odds_if_game_day(self):
        """
        Smart odds update - only runs if there are games today
        Saves API credits by skipping non-game days
        """
        # Check if there are games today
        has_games = await self._check_games_today()
        
        if not has_games:
            print(f"[{datetime.now()}] No games today - skipping odds update (saving API credits)")
            return
        
        # If we have games, fetch odds
        print(f"[{datetime.now()}] Games today - proceeding with odds update")
        await self.update_odds()
    
    async def _check_games_today(self) -> bool:
        """
        Check if there are any NFL games today
        Returns: True if games today, False otherwise
        """
        try:
            scoreboard = await self.espn_fetcher.get_scoreboard()
            
            if not scoreboard:
                return False
            
            # Check if any games are today
            today = datetime.now(self.timezone).date()
            
            for game in scoreboard:
                game_date = game.get("date")
                if game_date:
                    # Parse game date
                    if isinstance(game_date, str):
                        game_date = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                    
                    # Convert to our timezone and check if it's today
                    game_date_local = game_date.astimezone(self.timezone).date()
                    
                    if game_date_local == today:
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error checking for games today: {e}")
            # On error, default to fetching odds (better safe than sorry)
            return True
    
    async def update_odds(self):
        """
        Odds update job - runs at game-time intervals
        Updates: game odds and player props
        """
        print(f"\n[{datetime.now()}] Starting odds update...")
        
        db = SessionLocal()
        
        try:
            # 1. Update game odds
            await self._update_game_odds(db)
            
            # 2. Update player props
            await self._update_player_props(db)
            
            db.commit()
            print(f"[{datetime.now()}] Odds update completed!\n")
            
        except Exception as e:
            db.rollback()
            print(f"[{datetime.now()}] ERROR during odds update: {e}\n")
            raise
        finally:
            db.close()
    
    async def _update_game_odds(self, db):
        """Update game odds (moneyline, spreads, totals)"""
        print("Fetching game odds...")
        games_odds = await self.odds_fetcher.get_nfl_odds()
        
        odds_count = 0
        for game_odds in games_odds:
            # Try to find matching game in database
            # This is tricky since ESPN IDs != Odds API IDs
            # For now, we'll store all odds with timestamp
            
            for bookmaker in game_odds["bookmakers"]:
                # Store moneyline odds
                if "moneyline" in bookmaker["markets"]:
                    for team, odds_value in bookmaker["markets"]["moneyline"].items():
                        odds_record = Odds(
                            market_type="h2h",
                            bookmaker=bookmaker["name"],
                            home_odds=odds_value if team == game_odds["home_team"] else None,
                            away_odds=odds_value if team == game_odds["away_team"] else None,
                            timestamp=datetime.utcnow()
                        )
                        db.add(odds_record)
                        odds_count += 1
                
                # Store spread odds
                if "spreads" in bookmaker["markets"]:
                    for team, spread_data in bookmaker["markets"]["spreads"].items():
                        odds_record = Odds(
                            market_type="spreads",
                            bookmaker=bookmaker["name"],
                            line=spread_data["point"],
                            home_odds=spread_data["price"] if team == game_odds["home_team"] else None,
                            away_odds=spread_data["price"] if team == game_odds["away_team"] else None,
                            timestamp=datetime.utcnow()
                        )
                        db.add(odds_record)
                        odds_count += 1
                
                # Store totals odds
                if "totals" in bookmaker["markets"]:
                    for direction, total_data in bookmaker["markets"]["totals"].items():
                        odds_record = Odds(
                            market_type="totals",
                            bookmaker=bookmaker["name"],
                            line=total_data["point"],
                            over_odds=total_data["price"] if direction == "Over" else None,
                            under_odds=total_data["price"] if direction == "Under" else None,
                            timestamp=datetime.utcnow()
                        )
                        db.add(odds_record)
                        odds_count += 1
        
        db.commit()
        print(f"[OK] Stored {odds_count} game odds records")
    
    async def _update_player_props(self, db):
        """Update player prop odds"""
        print("Fetching player props...")
        props = await self.odds_fetcher.get_nfl_player_props()
        
        for prop in props:
            # Try to find matching player
            # This requires fuzzy name matching since names might differ
            # For now, store all props
            
            odds_record = Odds(
                market_type="player_props",
                prop_type=prop["prop_type"],
                bookmaker=prop["bookmaker"],
                line=prop["line"],
                over_odds=prop["odds"] if prop["over_under"] == "Over" else None,
                under_odds=prop["odds"] if prop["over_under"] == "Under" else None,
                timestamp=datetime.utcnow()
            )
            db.add(odds_record)
        
        db.commit()
        print(f"[OK] Stored {len(props)} player prop records")
    
    def _compute_features(self, db):
        """Compute ML features (season averages) for all players with stats"""
        from services.feature_engineer import FeatureEngineer
        
        print("Computing season averages for all players...")
        engineer = FeatureEngineer(db)
        
        # Compute features for all players (FeatureEngineer handles the logic internally)
        import asyncio
        asyncio.run(engineer.compute_all_features())
        
        print("[OK] Updated season averages for all players")
    
    async def update_injuries(self):
        """
        Daily injury update job - runs at 12:00 PM
        Updates injury status for all players
        """
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] Updating injury data...")
        print(f"{'='*60}\n")
        
        db = SessionLocal()
        
        try:
            injuries_data = await self.espn_fetcher.get_injuries()
            print(f"Found {len(injuries_data)} injured players from ESPN")
            
            # Mark all existing injuries as inactive
            db.query(Injury).update({"is_active": False})
            
            loaded = 0
            skipped = 0
            
            for injury_data in injuries_data:
                # Find player by ESPN ID (much more reliable than name matching)
                player = db.query(Player).filter_by(
                    espn_player_id=str(injury_data["player_id"])
                ).first()
                
                if not player:
                    skipped += 1
                    continue
                
                # Create or update injury
                injury = db.query(Injury).filter_by(player_id=player.id).first()
                
                date_reported = injury_data.get("date_reported")
                if isinstance(date_reported, str):
                    try:
                        date_reported = datetime.fromisoformat(date_reported.replace('Z', '+00:00'))
                    except:
                        date_reported = datetime.now()
                elif not date_reported:
                    date_reported = datetime.now()
                
                if injury:
                    injury.player_name = player.name
                    injury.status = injury_data["status"]
                    injury.injury_type = injury_data.get("injury_type", "Unknown")
                    injury.description = injury_data.get("description", "")
                    injury.date_reported = date_reported
                    injury.is_active = True
                else:
                    injury = Injury(
                        player_id=player.id,
                        player_name=player.name,
                        status=injury_data["status"],
                        injury_type=injury_data.get("injury_type", "Unknown"),
                        description=injury_data.get("description", ""),
                        date_reported=date_reported,
                        is_active=True
                    )
                    db.add(injury)
                
                loaded += 1
            
            db.commit()
            
            print(f"\nInjury update completed:")
            print(f"  Loaded: {loaded}")
            print(f"  Not in database: {skipped}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            db.rollback()
            print(f"\n[{datetime.now()}] ERROR during injury update: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
    
    async def retrain_models(self):
        """
        Weekly model retraining job - runs on Tuesdays at 3 AM
        Retrains all ML models with accumulated data
        """
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] Starting weekly model retraining...")
        print(f"{'='*60}\n")
        
        db = SessionLocal()
        
        try:
            # Import BettingAI here to avoid circular imports
            from services.predictor import BettingAI
            
            # Initialize Betting AI
            ai = BettingAI(db)
            
            # Retrain all models
            print("Retraining all prop models...")
            results = ai.train_all_props()
            
            # Log results
            print("\n" + "="*60)
            print("RETRAINING SUMMARY")
            print("="*60)
            
            for prop_type, model_data in results.items():
                best_model = model_data['best_model']
                best_r2 = model_data['results'][best_model]['r2']
                best_mae = model_data['results'][best_model]['mae']
                print(f"\n{prop_type}:")
                print(f"  Best Model: {best_model}")
                print(f"  MAE: {best_mae:.2f}")
                print(f"  R²: {best_r2:.3f}")
            
            print("\n" + "="*60)
            print(f"[{datetime.now()}] Model retraining completed successfully!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n[{datetime.now()}] ERROR during model retraining: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
    
    async def run_continuous_learning(self):
        """
        Weekly continuous learning analysis - runs on Tuesdays at 4 AM (after retraining)
        Analyzes prediction accuracy from completed games
        """
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] Starting continuous learning analysis...")
        print(f"{'='*60}\n")
        
        db = SessionLocal()
        
        try:
            # Import ContinuousLearning here to avoid circular imports
            from services.continuous_learning import ContinuousLearning
            
            # Initialize Continuous Learning
            cl = ContinuousLearning(db)
            
            # Analyze last week's completed games
            print("Analyzing completed games from last week...")
            result = cl.analyze_completed_games(weeks_back=1)
            
            print(f"\nGames Analyzed: {result['games_analyzed']}")
            print(f"Predictions Updated: {result['predictions_updated']}")
            
            if result['predictions_updated'] > 0:
                # Generate accuracy report
                print("\nGenerating accuracy report...")
                report = cl.get_accuracy_report()
                
                print(f"\nOverall Accuracy: {report['overall_accuracy']:.1f}%")
                print(f"Total Validated Predictions: {report['total_predictions']}")
                
                # Show prop type accuracy
                print("\nProp Type Accuracy:")
                for prop_type, stats in sorted(report['by_prop_type'].items(), 
                                              key=lambda x: x[1]['accuracy_pct'], 
                                              reverse=True)[:5]:
                    print(f"  {prop_type:25} | {stats['accuracy_pct']:5.1f}% | Error: {stats['avg_error']:.2f}")
            
            print(f"\n{'='*60}")
            print(f"[{datetime.now()}] Continuous learning analysis completed!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n[{datetime.now()}] ERROR during continuous learning: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()


# Run scheduler as standalone service
async def run_scheduler():
    """Run the scheduler service"""
    scheduler = DataScheduler()
    scheduler.start()
    
    print("\nScheduler is running. Press Ctrl+C to stop.")
    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(run_scheduler())

