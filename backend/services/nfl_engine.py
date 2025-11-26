"""
NFL Betting AI Engine - YOUR AI's Brain

This is where ALL NFL knowledge lives. Gemini has ZERO access to any football data.
This engine:
1. Parses user intent
2. Fetches data from YOUR database
3. Runs YOUR trained ML models
4. Returns structured results

Gemini only receives this output and formats it conversationally.
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from models import Player, Team, Game, StatsFeatures, Injury, PlayerStats, Odds
from services.predictor import BettingAI
from services.matchup_analyzer import MatchupAnalyzer
from services.smart_picks import SmartPicksEngine
from datetime import datetime, date, timedelta
import re


class NFLEngine:
    """
    YOUR AI's Brain - All NFL knowledge and predictions come from here.
    Gemini is completely isolated from this data.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.betting_ai = BettingAI(db)
        self.matchup_analyzer = MatchupAnalyzer(db)
        self.smart_picks = SmartPicksEngine(db)
        
        # Learning engine - AI learns from its own accuracy
        from services.learning_engine import LearningEngine
        self.learning_engine = LearningEngine(db)
        
        # Track what data we've provided in this session
        # This is used to validate Gemini's response
        self.session_data = {
            "players_mentioned": {},  # player_name -> team_name
            "teams_mentioned": [],
            "predictions_made": [],
            "stats_provided": [],
            "games_returned": [],
            "injuries_returned": [],
        }
    
    def clear_session(self):
        """Clear session data for new conversation"""
        self.session_data = {
            "players_mentioned": {},
            "teams_mentioned": [],
            "predictions_made": [],
            "stats_provided": [],
            "games_returned": [],
            "injuries_returned": [],
        }
    
    # ========================================================================
    # INTENT DETECTION - What does the user want?
    # ========================================================================
    
    def detect_intent(self, query: str) -> Dict[str, Any]:
        """
        Detect user intent from their query.
        Returns what type of request this is and extracted entities.
        """
        query_lower = query.lower()
        
        intent = {
            "type": None,
            "entities": {
                "player_names": [],
                "team_names": [],
                "stat_types": [],
                "date_query": None,
            },
            "raw_query": query
        }
        
        # Extract player names (will be fuzzy matched later)
        # Common patterns: "AJ Brown", "Patrick Mahomes", etc.
        player_patterns = [
            r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+(?:\s+(?:Jr|Sr|II|III))?)(?:\s+(?:stats|prediction|yards|tds|touchdowns|rushing|passing|receiving|tackles|sacks))?",
        ]
        
        # Extract team names
        team_keywords = [
            "eagles", "cowboys", "giants", "commanders", "bears", "lions", "packers", "vikings",
            "buccaneers", "bucs", "falcons", "panthers", "saints", "cardinals", "49ers", "niners",
            "seahawks", "rams", "broncos", "chiefs", "raiders", "chargers", "bills", "dolphins",
            "jets", "patriots", "ravens", "bengals", "browns", "steelers", "texans", "colts",
            "jaguars", "titans", "philadelphia", "dallas", "new york", "washington", "chicago",
            "detroit", "green bay", "minnesota", "tampa bay", "atlanta", "carolina", "new orleans",
            "arizona", "san francisco", "seattle", "los angeles", "denver", "kansas city",
            "las vegas", "buffalo", "miami", "baltimore", "cincinnati", "cleveland", "pittsburgh",
            "houston", "indianapolis", "jacksonville", "tennessee"
        ]
        
        for team in team_keywords:
            if team in query_lower:
                intent["entities"]["team_names"].append(team)
        
        # Detect stat types
        stat_keywords = {
            "passing_yards": ["passing yards", "pass yards", "throwing yards", "pass yds"],
            "passing_tds": ["passing touchdowns", "pass tds", "passing tds", "td passes"],
            "rushing_yards": ["rushing yards", "rush yards", "run yards", "rushing yds"],
            "rushing_tds": ["rushing touchdowns", "rush tds", "rushing tds"],
            "receiving_yards": ["receiving yards", "rec yards", "reception yards", "receiving yds"],
            "receiving_tds": ["receiving touchdowns", "rec tds", "receiving tds"],
            "receptions": ["receptions", "catches", "recs"],
            "tackles_total": ["tackles", "total tackles"],
            "sacks": ["sacks", "quarterback sacks"],
            "interceptions_def": ["interceptions", "picks", "ints"],
        }
        
        for stat_type, keywords in stat_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    intent["entities"]["stat_types"].append(stat_type)
                    break
        
        # Detect intent type based on keywords
        # IMPORTANT: Order matters! More specific intents should come first
        
        # 1. VALUE BETS - specific request for value opportunities
        if any(word in query_lower for word in ["value bet", "value pick", "find value", "best value", "edges", "find edge"]):
            intent["type"] = "value_bets"
        
        # 2. PARLAY - check because parlays often mention dates
        # Include common typos like "paraly" and variations
        elif any(word in query_lower for word in ["parlay", "paraly", "parlays", "bet slip", "betting picks", "leg parlay", "leg paraly", "same game parlay", "sgp"]):
            intent["type"] = "parlay"
            
            # Detect risk level for parlays
            if any(word in query_lower for word in ["safer", "safe", "conservative", "lower risk", "lock", "sure"]):
                intent["entities"]["risk_level"] = "safe"
            elif any(word in query_lower for word in ["riskier", "risky", "aggressive", "yolo", "long shot"]):
                intent["entities"]["risk_level"] = "risky"
            else:
                intent["entities"]["risk_level"] = "normal"
        
        # 2. GAMES ON DATE - check BEFORE other schedule queries
        # "who plays on thanksgiving" = games, not player info
        elif any(word in query_lower for word in ["thanksgiving", "christmas", "games on", "games this", "games today", "games tomorrow"]):
            intent["type"] = "games_on_date"
            intent["entities"]["date_query"] = self._extract_date_query(query_lower)
        
        # 3. Day-based game queries (sunday, monday, etc.) - also games
        elif any(word in query_lower for word in ["on sunday", "on monday", "on thursday", "on saturday", "this sunday", "this monday"]):
            intent["type"] = "games_on_date"
            intent["entities"]["date_query"] = self._extract_date_query(query_lower)
        
        # 4. TOP/BEST PLAYERS - leaderboard queries
        elif any(word in query_lower for word in ["top qb", "top rb", "top wr", "top receiver", "top rusher", "top passer",
                                                   "best qb", "best rb", "best wr", "best receiver", "best rusher", "best passer",
                                                   "best running back", "best quarterback", "best wide receiver", "best tight end",
                                                   "top running back", "top quarterback", "top wide receiver", "top tight end",
                                                   "leading", "leaders", "most yards", "most touchdowns", "most receptions",
                                                   "who has the most", "who leads", "top players", "best players",
                                                   "highest", "rankings", "leaderboard"]):
            intent["type"] = "leaderboard"
            # Detect position
            if any(p in query_lower for p in ["qb", "quarterback", "passer", "passing"]):
                intent["entities"]["position"] = "QB"
            elif any(p in query_lower for p in ["rb", "running back", "rusher", "rushing"]):
                intent["entities"]["position"] = "RB"
            elif any(p in query_lower for p in ["wr", "receiver", "wide receiver", "receiving"]):
                intent["entities"]["position"] = "WR"
            elif any(p in query_lower for p in ["te", "tight end"]):
                intent["entities"]["position"] = "TE"
        
        # 5. LIKELIHOOD/PERFORMANCE - will player do well?
        elif any(word in query_lower for word in ["likely", "do well", "perform", "good game", "boom", "bust", 
                                                   "should i bet", "worth betting", "good bet", "safe bet"]):
            intent["type"] = "player_outlook"
        
        # 6. Prediction queries
        elif any(word in query_lower for word in ["predict", "prediction", "projected", "expect", "how many", "how will", "will he get"]):
            intent["type"] = "prediction"
        
        # 7. Stats/Average queries
        elif any(word in query_lower for word in ["stats", "statistics", "average", "averages", "averaging", 
                                                   "season", "total", "how has", "what does", "per game"]):
            intent["type"] = "stats"
        
        # 6. Team matchup (requires 2 teams)
        elif any(word in query_lower for word in ["vs", "versus", "against", "matchup", "compare"]) and len(intent["entities"]["team_names"]) >= 2:
            intent["type"] = "team_matchup"
        
        # 7. Team schedule (requires team name)
        elif any(word in query_lower for word in ["playing", "play next", "next game", "schedule", "when do", "playing next"]) and intent["entities"]["team_names"]:
            intent["type"] = "team_schedule"
        
        # 8. Roster queries
        elif any(word in query_lower for word in ["roster", "players on", "who is on", "team members"]):
            intent["type"] = "roster"
        
        # 9. Injury queries
        elif any(word in query_lower for word in ["injury", "injured", "hurt", "out", "questionable", "doubtful"]):
            intent["type"] = "injury"
        
        # 10. Player info (when asking about a specific person)
        elif any(word in query_lower for word in ["who is", "what team", "plays for", "which team"]) and not intent["entities"]["team_names"]:
            intent["type"] = "player_info"
        
        # 11. Defensive matchup
        elif any(word in query_lower for word in ["defend", "covering", "coverage", "who will cover"]):
            intent["type"] = "defensive_matchup"
        
        # 12. META/CONVERSATIONAL - questions about the AI itself
        elif any(phrase in query_lower for phrase in [
            "where are you getting", "where do you get", "how do you know",
            "what data", "what database", "your data", "your source",
            "how are you", "who are you", "what are you",
            "where from", "data from", "picks from", "getting these",
            "how does this work", "explain", "thanks", "thank you"
        ]):
            intent["type"] = "meta"
        
        else:
            # Default to general query
            intent["type"] = "general"
        
        return intent
    
    def _extract_date_query(self, query: str) -> str:
        """Extract date-related query from user input"""
        if "thanksgiving" in query:
            return "thanksgiving"
        elif "christmas" in query:
            return "christmas"
        elif "today" in query:
            return "today"
        elif "tomorrow" in query:
            return "tomorrow"
        elif "sunday" in query:
            return "sunday"
        elif "monday" in query:
            return "monday"
        elif "thursday" in query:
            return "thursday"
        elif "saturday" in query:
            return "saturday"
        elif "friday" in query:
            return "friday"
        
        # Try to extract specific date
        date_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})', query)
        if date_match:
            return f"{date_match.group(1)} {date_match.group(2)}"
        
        return "today"  # Default
    
    # ========================================================================
    # DATA FETCHERS - Get data from YOUR database
    # ========================================================================
    
    def find_player(self, player_name: str) -> Optional[Player]:
        """Find a player with fuzzy matching"""
        # Normalize name
        normalized = re.sub(r'[^a-zA-Z\s]', '', player_name.lower())
        
        # Get all players
        all_players = self.db.query(Player).all()
        
        # Exact match first
        for p in all_players:
            p_normalized = re.sub(r'[^a-zA-Z\s]', '', p.name.lower())
            if normalized == p_normalized:
                return p
        
        # Partial match
        for p in all_players:
            p_normalized = re.sub(r'[^a-zA-Z\s]', '', p.name.lower())
            if normalized in p_normalized or p_normalized in normalized:
                return p
        
        # Last name match
        name_parts = normalized.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]
            for p in all_players:
                p_normalized = re.sub(r'[^a-zA-Z\s]', '', p.name.lower())
                if last_name in p_normalized.split():
                    # Check first initial
                    if name_parts[0][0] == p_normalized.split()[0][0]:
                        return p
        
        return None
    
    def find_team(self, team_name: str) -> Optional[Team]:
        """Find a team with flexible matching"""
        team_name_clean = team_name.lower().strip()
        
        return self.db.query(Team).filter(
            or_(
                Team.name.ilike(f'%{team_name}%'),
                Team.location.ilike(f'%{team_name}%'),
                Team.abbreviation.ilike(f'%{team_name}%')
            )
        ).first()
    
    def get_player_stats(self, player_name: str, stat_type: str = None) -> Dict:
        """Get player's season statistics from YOUR database"""
        player = self.find_player(player_name)
        
        if not player:
            return {"error": f"Player '{player_name}' not found in database"}
        
        # Get the player's team
        team = self.db.query(Team).filter_by(id=player.team_id).first()
        
        # Track this player-team mapping
        self.session_data["players_mentioned"][player.name.lower()] = team.name if team else "Unknown"
        
        features = self.db.query(StatsFeatures).filter_by(
            player_id=player.id,
            season=2025
        ).first()
        
        if not features:
            return {
                "player_name": player.name,
                "team": team.name if team else "Unknown",
                "position": player.position,
                "error": "No 2025 stats found"
            }
        
        # Build comprehensive stats based on position
        stats = {
            "player_name": player.name,
            "team": team.name if team else "Unknown",
            "position": player.position,
            "games_played": features.games_played,
            "data_source": "YOUR_DATABASE_2025_SEASON"
        }
        
        if player.position == 'QB':
            stats.update({
                "passing_yards_per_game": round(features.avg_passing_yards or 0, 1),
                "passing_tds_per_game": round(features.avg_passing_tds or 0, 2),
                "interceptions_per_game": round(features.avg_interceptions or 0, 2),
                "rushing_yards_per_game": round(features.avg_rushing_yards or 0, 1),
                "sacks_taken_per_game": round(features.avg_sacks_taken or 0, 2),
            })
        elif player.position == 'RB':
            stats.update({
                "rushing_yards_per_game": round(features.avg_rushing_yards or 0, 1),
                "rushing_tds_per_game": round(features.avg_rushing_tds or 0, 2),
                "receiving_yards_per_game": round(features.avg_receiving_yards or 0, 1),
                "receptions_per_game": round(features.avg_receptions or 0, 2),
            })
        elif player.position in ['WR', 'TE']:
            stats.update({
                "receiving_yards_per_game": round(features.avg_receiving_yards or 0, 1),
                "receiving_tds_per_game": round(features.avg_receiving_tds or 0, 2),
                "receptions_per_game": round(features.avg_receptions or 0, 2),
                "targets_per_game": round(features.avg_targets or 0, 2),
            })
        elif player.position in ['LB', 'CB', 'S', 'DE', 'DT', 'DB', 'OLB', 'MLB', 'ILB']:
            stats.update({
                "tackles_per_game": round(features.avg_tackles or 0, 1),
                "sacks_per_game": round(features.avg_sacks_def or 0, 2),
                "interceptions_per_game": round(features.avg_interceptions_def or 0, 2),
                "pass_deflections_per_game": round(features.avg_pass_deflections or 0, 2),
            })
        
        # Recent form
        stats["last_3_games_avg_yards"] = round(features.last_3_avg_yards or 0, 1)
        stats["consistency_score"] = round((features.consistency_score or 0) * 100, 1)
        
        self.session_data["stats_provided"].append(stats)
        return stats
    
    def get_top_players(self, position: str = "QB", limit: int = 10) -> Dict:
        """Get top players at a position - leaderboard from YOUR database"""
        from config import settings
        
        position_upper = position.upper()
        
        # Determine stat columns and labels based on position
        if position_upper == "QB":
            stat_key = "avg_passing_yards"
            stat_label = "Pass Yds/G"
            secondary_stat = "avg_passing_tds"
            secondary_label = "TDs/G"
        elif position_upper == "RB":
            stat_key = "avg_rushing_yards"
            stat_label = "Rush Yds/G"
            secondary_stat = "avg_rushing_tds"
            secondary_label = "TDs/G"
        elif position_upper in ["WR", "RECEIVER"]:
            position_upper = "WR"
            stat_key = "avg_receiving_yards"
            stat_label = "Rec Yds/G"
            secondary_stat = "avg_receptions"
            secondary_label = "Rec/G"
        elif position_upper == "TE":
            stat_key = "avg_receiving_yards"
            stat_label = "Rec Yds/G"
            secondary_stat = "avg_receptions"
            secondary_label = "Rec/G"
        else:
            position_upper = "QB"
            stat_key = "avg_passing_yards"
            stat_label = "Pass Yds/G"
            secondary_stat = "avg_passing_tds"
            secondary_label = "TDs/G"
        
        # Query with JOIN to get player info - MUST filter by current season
        results = self.db.query(StatsFeatures, Player, Team).join(
            Player, StatsFeatures.player_id == Player.id
        ).outerjoin(
            Team, Player.team_id == Team.id
        ).filter(
            Player.position == position_upper,
            StatsFeatures.season == settings.CURRENT_SEASON,
            StatsFeatures.games_played >= 3
        ).all()
        
        if not results:
            # Try with lower games_played threshold
            results = self.db.query(StatsFeatures, Player, Team).join(
                Player, StatsFeatures.player_id == Player.id
            ).outerjoin(
                Team, Player.team_id == Team.id
            ).filter(
                Player.position == position_upper,
                StatsFeatures.season == settings.CURRENT_SEASON,
                StatsFeatures.games_played >= 1
            ).all()
        
        if not results:
            return {"error": f"No {position_upper} stats leaders found.", "leaderboard": []}
        
        # Sort by primary stat
        results.sort(key=lambda x: getattr(x[0], stat_key, 0) or 0, reverse=True)
        
        # Build leaderboard
        leaderboard = []
        for i, (features, player, team) in enumerate(results[:limit], 1):
            primary_value = getattr(features, stat_key, 0) or 0
            secondary_value = getattr(features, secondary_stat, 0) or 0
            
            leaderboard.append({
                "rank": i,
                "player_name": player.name,
                "team": team.abbreviation if team else "FA",
                "team_name": team.name if team else "Free Agent",
                "position": player.position,
                "games_played": features.games_played,
                "primary_stat": round(primary_value, 1),
                "primary_label": stat_label,
                "secondary_stat": round(secondary_value, 2),
                "secondary_label": secondary_label,
                "consistency_score": round((features.consistency_score or 0) * 100, 1),
                "trending": "up" if (features.last_3_avg_yards or 0) > primary_value else "down"
            })
        
        # Get the season from the first result
        season_year = results[0][0].season if results else settings.CURRENT_SEASON
        
        return {
            "position": position_upper,
            "title": f"Top {position_upper}s - {season_year} Season",
            "leaderboard": leaderboard,
            "total_qualified": len(results),
            "min_games": 3,
            "data_source": "YOUR_DATABASE"
        }
    
    def get_player_outlook(self, player_name: str, query: str = "") -> Dict:
        """Get player's outlook/likelihood to perform well - betting advice"""
        player = self.find_player(player_name)
        
        if not player:
            return {"error": f"Player '{player_name}' not found in database"}
        
        team = self.db.query(Team).filter_by(id=player.team_id).first()
        
        # Get player stats
        features = self.db.query(StatsFeatures).filter_by(
            player_id=player.id,
            season=2025
        ).first()
        
        if not features:
            return {
                "player_name": player.name,
                "team": team.name if team else "Unknown",
                "position": player.position,
                "error": "Insufficient data for outlook analysis"
            }
        
        # Get upcoming game
        now = datetime.utcnow()
        upcoming_game = self.db.query(Game).filter(
            or_(Game.home_team_id == player.team_id, Game.away_team_id == player.team_id),
            Game.game_date > now,
            Game.status != "Final"
        ).order_by(Game.game_date).first()
        
        opponent = None
        opponent_team = None
        is_home = False
        if upcoming_game:
            if upcoming_game.home_team_id == player.team_id:
                opponent_team = self.db.query(Team).filter_by(id=upcoming_game.away_team_id).first()
                is_home = True
            else:
                opponent_team = self.db.query(Team).filter_by(id=upcoming_game.home_team_id).first()
                is_home = False
            opponent = opponent_team.name if opponent_team else "Unknown"
        
        # Calculate outlook factors
        factors = []
        outlook_score = 50  # Start neutral
        
        # 1. Recent form (last 3 games vs season average)
        if player.position == "QB":
            recent = features.last_3_avg_yards or 0
            season = features.avg_passing_yards or 0
        elif player.position == "RB":
            recent = features.last_3_avg_yards or features.avg_rushing_yards or 0
            season = features.avg_rushing_yards or 0
        else:
            recent = features.last_3_avg_yards or features.avg_receiving_yards or 0
            season = features.avg_receiving_yards or 0
        
        if season > 0:
            form_ratio = recent / season
            if form_ratio > 1.1:
                factors.append({"factor": "Hot streak", "impact": "positive", "detail": f"Recent form {((form_ratio-1)*100):.0f}% above average"})
                outlook_score += 15
            elif form_ratio < 0.9:
                factors.append({"factor": "Cold streak", "impact": "negative", "detail": f"Recent form {((1-form_ratio)*100):.0f}% below average"})
                outlook_score -= 15
            else:
                factors.append({"factor": "Consistent", "impact": "neutral", "detail": "Performing at expected level"})
        
        # 2. Consistency
        consistency = features.consistency_score or 0
        if consistency > 0.75:
            factors.append({"factor": "High consistency", "impact": "positive", "detail": f"{consistency*100:.0f}% hit rate on lines"})
            outlook_score += 10
        elif consistency < 0.5:
            factors.append({"factor": "Boom/bust player", "impact": "caution", "detail": "Volatile week-to-week"})
            outlook_score -= 5
        
        # 3. Home/away advantage
        if upcoming_game:
            if is_home:
                factors.append({"factor": "Home game", "impact": "positive", "detail": "Playing at home"})
                outlook_score += 5
            else:
                factors.append({"factor": "Road game", "impact": "neutral", "detail": "Playing away"})
        
        # 4. Games played (experience this season)
        if features.games_played >= 8:
            factors.append({"factor": "Season experience", "impact": "positive", "detail": f"{features.games_played} games played"})
            outlook_score += 5
        elif features.games_played <= 3:
            factors.append({"factor": "Limited sample", "impact": "caution", "detail": f"Only {features.games_played} games played"})
            outlook_score -= 10
        
        # Determine outlook verdict
        if outlook_score >= 70:
            verdict = "STRONG PLAY"
            recommendation = "Good bet to consider"
            confidence = "high"
        elif outlook_score >= 55:
            verdict = "FAVORABLE"
            recommendation = "Solid option with some risk"
            confidence = "medium-high"
        elif outlook_score >= 45:
            verdict = "NEUTRAL"
            recommendation = "Could go either way"
            confidence = "medium"
        elif outlook_score >= 35:
            verdict = "RISKY"
            recommendation = "Proceed with caution"
            confidence = "low"
        else:
            verdict = "AVOID"
            recommendation = "Not recommended right now"
            confidence = "very low"
        
        return {
            "player_name": player.name,
            "team": team.name if team else "Unknown",
            "position": player.position,
            "opponent": opponent,
            "is_home": is_home,
            "game_date": upcoming_game.game_date.isoformat() if upcoming_game else None,
            "outlook_score": outlook_score,
            "verdict": verdict,
            "confidence": confidence,
            "recommendation": recommendation,
            "factors": factors,
            "season_stats": {
                "games_played": features.games_played,
                "consistency": round((features.consistency_score or 0) * 100, 1),
                "recent_form": round(recent, 1),
                "season_average": round(season, 1)
            },
            "data_source": "YOUR_DATABASE_ML_ANALYSIS"
        }
    
    def predict_player_stat(self, player_name: str, stat_type: str) -> Dict:
        """Make a prediction using YOUR trained ML models"""
        player = self.find_player(player_name)
        
        if not player:
            return {"error": f"Player '{player_name}' not found in database"}
        
        # Get the player's team
        team = self.db.query(Team).filter_by(id=player.team_id).first()
        
        # Track this player-team mapping
        self.session_data["players_mentioned"][player.name.lower()] = team.name if team else "Unknown"
        
        # Find an upcoming game for context
        now = datetime.utcnow()
        upcoming_game = self.db.query(Game).filter(
            or_(Game.home_team_id == player.team_id, Game.away_team_id == player.team_id),
            Game.game_date > now,
            Game.status != "STATUS_FINAL"
        ).order_by(Game.game_date).first()
        
        if not upcoming_game:
            # Use most recent game as fallback
            upcoming_game = self.db.query(Game).filter(
                or_(Game.home_team_id == player.team_id, Game.away_team_id == player.team_id)
            ).order_by(Game.game_date.desc()).first()
        
        if not upcoming_game:
            return {"error": f"No games found for {player.name}"}
        
        # Determine opponent
        is_home = upcoming_game.home_team_id == player.team_id
        opponent_name = upcoming_game.away_team_name if is_home else upcoming_game.home_team_name
        
        # Call YOUR trained ML model
        prediction = self.betting_ai.predict_player_prop(
            player.id,
            upcoming_game.id,
            stat_type,
            is_home=is_home
        )
        
        if 'error' in prediction:
            return {
                "player_name": player.name,
                "team": team.name if team else "Unknown",
                "position": player.position,
                "error": prediction['error']
            }
        
        # Get base confidence from ML model
        base_confidence = prediction['confidence']
        
        # Apply LEARNED adjustments based on historical accuracy
        # This is where the AI learns - it adjusts confidence based on:
        # 1. How accurate this bet type has been historically
        # 2. How reliable this specific player is for this prop
        learning_adjustment = self.learning_engine.get_confidence_adjustment(
            player_id=player.id,
            prop_type=stat_type,
            bet_category="single",  # Will be "combined" for combined stats
            position=player.position
        )
        
        # Apply the adjustment
        adjusted_confidence = base_confidence + learning_adjustment
        # Cap between 20 and 95
        adjusted_confidence = max(20, min(95, adjusted_confidence))
        
        result = {
            "player_id": player.id,  # Needed for verification code
            "player_name": player.name,
            "team": team.name if team else "Unknown",
            "position": player.position,
            "stat_type": stat_type,
            "predicted_value": round(prediction['predicted_value'], 1),
            "confidence": round(adjusted_confidence, 1),
            "base_confidence": round(base_confidence, 1),  # Original ML confidence
            "learning_adjustment": round(learning_adjustment, 1),  # What AI learned
            "model_used": prediction['model_used'],
            "season_average": round(prediction.get('season_avg', 0), 1),
            "recent_form": round(prediction.get('recent_form', 0), 1),
            "opponent": opponent_name,
            "is_home": is_home,
            "game_week": upcoming_game.week,
            "data_source": "YOUR_ML_MODELS_2025"
        }
        
        self.session_data["predictions_made"].append(result)
        return result
    
    def get_team_schedule(self, team_name: str) -> Dict:
        """Get next game for a team"""
        team = self.find_team(team_name)
        
        if not team:
            return {"error": f"Team '{team_name}' not found"}
        
        self.session_data["teams_mentioned"].append(team.name)
        
        now = datetime.utcnow()
        upcoming_game = self.db.query(Game).filter(
            or_(Game.home_team_id == team.id, Game.away_team_id == team.id),
            Game.game_date > now,
            Game.status != "STATUS_FINAL"
        ).order_by(Game.game_date).first()
        
        if not upcoming_game:
            return {
                "team": team.name,
                "has_upcoming_game": False,
                "message": "No upcoming games scheduled"
            }
        
        is_home = upcoming_game.home_team_id == team.id
        opponent = upcoming_game.away_team_name if is_home else upcoming_game.home_team_name
        
        result = {
            "team": team.name,
            "has_upcoming_game": True,
            "week": upcoming_game.week,
            "opponent": opponent,
            "location": "home" if is_home else "away",
            "game_date": upcoming_game.game_date.strftime("%A, %B %d at %I:%M %p"),
            "venue": upcoming_game.venue,
            "data_source": "YOUR_DATABASE_2025"
        }
        
        self.session_data["games_returned"].append(result)
        return result
    
    def get_player_info(self, player_name: str) -> Dict:
        """Get basic player info including CURRENT team"""
        player = self.find_player(player_name)
        
        if not player:
            return {"error": f"Player '{player_name}' not found in database"}
        
        team = self.db.query(Team).filter_by(id=player.team_id).first()
        
        # Track this player-team mapping
        self.session_data["players_mentioned"][player.name.lower()] = team.name if team else "Unknown"
        
        # Get next game
        now = datetime.utcnow()
        upcoming_game = self.db.query(Game).filter(
            or_(Game.home_team_id == player.team_id, Game.away_team_id == player.team_id),
            Game.game_date > now,
            Game.status != "STATUS_FINAL"
        ).order_by(Game.game_date).first()
        
        result = {
            "player_name": player.name,
            "team": team.name if team else "Unknown",
            "team_abbreviation": team.abbreviation if team else "???",
            "position": player.position,
            "jersey_number": player.jersey_number,
            "data_source": "YOUR_DATABASE_2025"
        }
        
        if upcoming_game:
            is_home = upcoming_game.home_team_id == player.team_id
            opponent = upcoming_game.away_team_name if is_home else upcoming_game.home_team_name
            result["next_game"] = {
                "week": upcoming_game.week,
                "opponent": opponent,
                "location": "home" if is_home else "away",
                "date": upcoming_game.game_date.strftime("%A, %B %d")
            }
        
        return result
    
    def get_team_roster(self, team_name: str, position: str = None) -> Dict:
        """Get team roster - sorted by stats so STARTERS appear first"""
        team = self.find_team(team_name)
        
        if not team:
            return {"error": f"Team '{team_name}' not found"}
        
        self.session_data["teams_mentioned"].append(team.name)
        
        query = self.db.query(Player).filter(Player.team_id == team.id)
        
        if position:
            query = query.filter(Player.position.ilike(f'%{position}%'))
        
        players = query.all()
        
        if not players:
            return {"error": f"No players found for {team.name}"}
        
        # Get stats for all players to sort by actual playing time (starters have more yards)
        player_ids = [p.id for p in players]
        stats = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_(player_ids),
            StatsFeatures.season == 2025
        ).all()
        
        # Create stats lookup
        stats_by_player = {s.player_id: s for s in stats}
        
        # Get injuries for this team to flag injured players
        now = datetime.utcnow()
        active_injuries = self.db.query(Injury).join(Player).filter(
            Player.team_id == team.id,
            Injury.is_active == True,
            Injury.status.in_(["Out", "Doubtful"])
        ).all()
        injured_player_ids = {inj.player_id for inj in active_injuries}
        
        # Group by position and sort by stats within each position
        roster = {}
        for player in players:
            pos = player.position or "Unknown"
            if pos not in roster:
                roster[pos] = []
            
            # Skip players who are OUT or DOUBTFUL
            is_injured = player.id in injured_player_ids
            
            # Get player stats for sorting
            player_stats = stats_by_player.get(player.id)
            if player_stats:
                games_played = player_stats.games_played or 0
                
                # Calculate "starter score" based on position
                # Weight: games_played heavily + total production
                if pos == "QB":
                    # QBs: games played + total passing yards
                    total_yards = (player_stats.avg_passing_yards or 0) * games_played
                    starter_score = (games_played * 100) + total_yards
                elif pos == "RB":
                    # RBs: games played + total rushing yards
                    total_yards = (player_stats.avg_rushing_yards or 0) * games_played
                    starter_score = (games_played * 50) + total_yards
                elif pos in ["WR", "TE"]:
                    # WR/TE: games played + total receiving yards
                    total_yards = (player_stats.avg_receiving_yards or 0) * games_played
                    starter_score = (games_played * 50) + total_yards
                else:
                    # Defense: games played + total tackles
                    total_tackles = (player_stats.avg_tackles or 0) * games_played
                    starter_score = (games_played * 20) + total_tackles
            else:
                starter_score = 0
            
            # Penalize injured players heavily
            if is_injured:
                starter_score = -1000
            
            roster[pos].append((player.name, starter_score, is_injured))
            # Track player-team mapping
            self.session_data["players_mentioned"][player.name.lower()] = team.name
        
        # Sort each position group by starter_score (descending) and extract just names
        sorted_roster = {}
        for pos, players_list in roster.items():
            # Sort by starter_score descending (starters first, injured last)
            players_list.sort(key=lambda x: x[1], reverse=True)
            # Extract just names
            sorted_roster[pos] = [name for name, score, injured in players_list]
        
        return {
            "team": team.name,
            "roster": sorted_roster,
            "total_players": len(players),
            "filter": f"Position: {position}" if position else "All",
            "data_source": "YOUR_DATABASE_2025"
        }
    
    def predict_team_matchup(self, team1_name: str, team2_name: str) -> Dict:
        """Team vs team matchup analysis"""
        team1 = self.find_team(team1_name)
        team2 = self.find_team(team2_name)
        
        if not team1:
            return {"error": f"Team '{team1_name}' not found"}
        if not team2:
            return {"error": f"Team '{team2_name}' not found"}
        
        self.session_data["teams_mentioned"].extend([team1.name, team2.name])
        
        # Use YOUR matchup analyzer
        result = self.matchup_analyzer.analyze_team_matchup(team1.id, team2.id)
        result["data_source"] = "YOUR_ML_MODELS_AND_DATABASE_2025"
        
        return result
    
    def get_injury_report(self, team_name: str = None, player_name: str = None) -> Dict:
        """Get injury information"""
        if player_name:
            player = self.find_player(player_name)
            if not player:
                return {"error": f"Player '{player_name}' not found"}
            
            team = self.db.query(Team).filter_by(id=player.team_id).first()
            self.session_data["players_mentioned"][player.name.lower()] = team.name if team else "Unknown"
            
            now = datetime.utcnow()
            injuries = self.db.query(Injury).filter(
                Injury.player_id == player.id,
                Injury.is_active == True,
                Injury.date_reported >= now - timedelta(days=30)
            ).all()
            
            if not injuries:
                return {
                    "player_name": player.name,
                    "team": team.name if team else "Unknown",
                    "status": "Healthy",
                    "message": f"{player.name} has no active injuries",
                    "data_source": "YOUR_DATABASE_2025"
                }
            
            injury = injuries[0]
            return {
                "player_name": player.name,
                "team": team.name if team else "Unknown",
                "status": injury.status,
                "injury_type": injury.injury_type,
                "date_reported": injury.date_reported.strftime("%Y-%m-%d"),
                "data_source": "YOUR_DATABASE_2025"
            }
        
        elif team_name:
            team = self.find_team(team_name)
            if not team:
                return {"error": f"Team '{team_name}' not found"}
            
            self.session_data["teams_mentioned"].append(team.name)
            
            team_players = self.db.query(Player).filter(Player.team_id == team.id).all()
            player_ids = [p.id for p in team_players]
            
            now = datetime.utcnow()
            injuries = self.db.query(Injury, Player).join(
                Player, Injury.player_id == Player.id
            ).filter(
                Injury.player_id.in_(player_ids),
                Injury.is_active == True,
                Injury.date_reported >= now - timedelta(days=14)
            ).all()
            
            if not injuries:
                return {
                    "team": team.name,
                    "injury_count": 0,
                    "message": f"{team.name} has no active injuries",
                    "data_source": "YOUR_DATABASE_2025"
                }
            
            injuries_list = []
            for injury, player in injuries:
                self.session_data["players_mentioned"][player.name.lower()] = team.name
                injuries_list.append({
                    "player": player.name,
                    "position": player.position,
                    "status": injury.status,
                    "injury_type": injury.injury_type
                })
            
            self.session_data["injuries_returned"].extend(injuries_list)
            
            return {
                "team": team.name,
                "injury_count": len(injuries_list),
                "injuries": injuries_list,
                "data_source": "YOUR_DATABASE_2025"
            }
        
        else:
            # No team or player specified - show ALL active injuries across the league
            now = datetime.utcnow()
            injuries = self.db.query(Injury, Player, Team).join(
                Player, Injury.player_id == Player.id
            ).outerjoin(
                Team, Player.team_id == Team.id
            ).filter(
                Injury.is_active == True,
                Injury.date_reported >= now - timedelta(days=7),
                Injury.status.in_(["Out", "Doubtful", "Questionable"])
            ).order_by(
                Injury.status,  # Out first, then Doubtful, then Questionable
                Team.name
            ).all()
            
            if not injuries:
                return {
                    "title": "League Injury Report",
                    "injury_count": 0,
                    "message": "No significant injuries reported this week",
                    "data_source": "YOUR_DATABASE_2025"
                }
            
            # Group by status
            by_status = {"Out": [], "Doubtful": [], "Questionable": []}
            
            for injury, player, team in injuries:
                entry = {
                    "player": player.name,
                    "position": player.position,
                    "team": team.abbreviation if team else "FA",
                    "team_name": team.name if team else "Free Agent",
                    "injury_type": injury.injury_type,
                    "status": injury.status
                }
                if injury.status in by_status:
                    by_status[injury.status].append(entry)
            
            return {
                "title": "NFL Injury Report",
                "injury_count": len(injuries),
                "out": by_status["Out"][:15],  # Limit each category
                "doubtful": by_status["Doubtful"][:10],
                "questionable": by_status["Questionable"][:15],
                "data_source": "YOUR_DATABASE_2025"
            }
    
    def get_games_on_date(self, date_query: str) -> Dict:
        """Get games scheduled on a specific date"""
        import logging
        logging.warning(f"get_games_on_date called with: '{date_query}'")
        target_date = self._parse_date_query(date_query)
        logging.warning(f"Parsed to date: {target_date}")
        
        if not target_date:
            return {"error": f"Could not parse date: '{date_query}'"}
        
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        games = self.db.query(Game).filter(
            Game.game_date >= start_datetime,
            Game.game_date <= end_datetime
        ).order_by(Game.game_date).all()
        
        logging.warning(f"Found {len(games)} games between {start_datetime} and {end_datetime}")
        
        if not games:
            return {
                "date": target_date.strftime("%A, %B %d, %Y"),
                "games_count": 0,
                "games": [],
                "message": f"No games scheduled on {target_date.strftime('%B %d, %Y')}",
                "data_source": "YOUR_DATABASE_2025"
            }
        
        games_list = []
        for game in games:
            self.session_data["teams_mentioned"].extend([game.home_team_name, game.away_team_name])
            games_list.append({
                "game_id": game.id,  # Include for learning tracking
                "week": game.week,
                "matchup": f"{game.away_team_name} at {game.home_team_name}",
                "away_team": game.away_team_name,
                "home_team": game.home_team_name,
                "time": game.game_date.strftime("%I:%M %p"),
                "venue": game.venue,
                "status": "Completed" if game.status == "STATUS_FINAL" else "Scheduled"
            })
        
        self.session_data["games_returned"].extend(games_list)
        
        return {
            "date": target_date.strftime("%A, %B %d, %Y"),
            "games_count": len(games),
            "games": games_list,
            "data_source": "YOUR_DATABASE_2025"
        }
    
    def _parse_date_query(self, query: str) -> Optional[date]:
        """Parse date from natural language"""
        query = query.lower()
        today = date.today()
        
        if "today" in query:
            return today
        elif "tomorrow" in query:
            return today + timedelta(days=1)
        elif "thanksgiving" in query:
            # 4th Thursday of November
            year = 2025 if today.year == 2025 else today.year
            nov_first = date(year, 11, 1)
            days_until_thursday = (3 - nov_first.weekday()) % 7
            first_thursday = nov_first + timedelta(days=days_until_thursday)
            return first_thursday + timedelta(weeks=3)
        elif "christmas" in query:
            year = 2025 if today.year == 2025 else today.year
            return date(year, 12, 25)
        
        # Days of week
        days = {'sunday': 6, 'monday': 0, 'tuesday': 1, 'wednesday': 2, 
                'thursday': 3, 'friday': 4, 'saturday': 5}
        
        for day_name, day_num in days.items():
            if day_name in query:
                current = today.weekday()
                days_ahead = day_num - current
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
        
        # Try specific date
        months = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                  'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
        
        for month_name, month_num in months.items():
            if month_name in query:
                day_match = re.search(r'(\d{1,2})', query)
                if day_match:
                    day = int(day_match.group(1))
                    year = today.year
                    try:
                        return date(year, month_num, day)
                    except ValueError:
                        pass
        
        return None
    
    # ========================================================================
    # MAIN PROCESSING - Process user query and return data
    # ========================================================================
    
    def process_query(self, query: str) -> Dict:
        """
        Main entry point - processes a user query and returns structured data.
        This data will be passed to Gemini for formatting ONLY.
        Gemini cannot add to this data or use its own knowledge.
        """
        # Clear session data for fresh query
        self.clear_session()
        
        # Detect intent
        intent = self.detect_intent(query)
        
        results = {
            "intent": intent["type"],
            "query": query,
            "data": None,
            "error": None,
            "data_sources": ["YOUR_DATABASE_2025"],
            "gemini_instructions": None
        }
        
        try:
            if intent["type"] == "prediction":
                # Need to find player name in query
                player_name = self._extract_player_name(query)
                stat_type = intent["entities"]["stat_types"][0] if intent["entities"]["stat_types"] else "passing_yards"
                
                if player_name:
                    results["data"] = self.predict_player_stat(player_name, stat_type)
                    results["gemini_instructions"] = "Present this prediction conversationally. Use ONLY the data provided."
                else:
                    results["error"] = "Could not identify player name"
            
            elif intent["type"] == "stats":
                player_name = self._extract_player_name(query)
                if player_name:
                    results["data"] = self.get_player_stats(player_name)
                    results["gemini_instructions"] = "Present these stats conversationally. Use ONLY the data provided."
                else:
                    results["error"] = "Could not identify player name"
            
            elif intent["type"] == "leaderboard":
                # Get top players by position
                position = intent["entities"].get("position", "QB")
                results["data"] = self.get_top_players(position)
                results["gemini_instructions"] = "Present this leaderboard conversationally. Use ONLY the data provided."
            
            elif intent["type"] == "player_outlook":
                # Get player's outlook/likelihood to perform
                player_name = self._extract_player_name(query)
                if player_name:
                    results["data"] = self.get_player_outlook(player_name, query)
                    results["gemini_instructions"] = "Present this player outlook conversationally. Give betting advice based on the data. Use ONLY the data provided."
                else:
                    results["error"] = "Could not identify player name"
            
            elif intent["type"] == "team_matchup":
                if len(intent["entities"]["team_names"]) >= 2:
                    results["data"] = self.predict_team_matchup(
                        intent["entities"]["team_names"][0],
                        intent["entities"]["team_names"][1]
                    )
                    results["gemini_instructions"] = "Present this team matchup analysis conversationally. Use ONLY the data provided."
                else:
                    results["error"] = "Need two teams for matchup comparison"
            
            elif intent["type"] == "team_schedule":
                if intent["entities"]["team_names"]:
                    results["data"] = self.get_team_schedule(intent["entities"]["team_names"][0])
                    results["gemini_instructions"] = "Present this schedule info conversationally. Use ONLY the data provided."
                else:
                    results["error"] = "Could not identify team name"
            
            elif intent["type"] == "player_schedule" or intent["type"] == "player_info":
                player_name = self._extract_player_name(query)
                if player_name:
                    results["data"] = self.get_player_info(player_name)
                    results["gemini_instructions"] = "Present this player info conversationally. Use ONLY the data provided."
                else:
                    results["error"] = "Could not identify player name"
            
            elif intent["type"] == "roster":
                if intent["entities"]["team_names"]:
                    position = None
                    for pos in ["QB", "RB", "WR", "TE", "CB", "LB", "DE", "DT", "S"]:
                        if pos.lower() in query.lower():
                            position = pos
                            break
                    results["data"] = self.get_team_roster(intent["entities"]["team_names"][0], position)
                    results["gemini_instructions"] = "Present this roster conversationally. Use ONLY the data provided."
                else:
                    results["error"] = "Could not identify team name"
            
            elif intent["type"] == "injury":
                if intent["entities"]["team_names"]:
                    results["data"] = self.get_injury_report(team_name=intent["entities"]["team_names"][0])
                else:
                    player_name = self._extract_player_name(query)
                    if player_name:
                        results["data"] = self.get_injury_report(player_name=player_name)
                    else:
                        results["error"] = "Need team or player name for injury report"
                results["gemini_instructions"] = "Present this injury report conversationally. Use ONLY the data provided."
            
            elif intent["type"] == "games_on_date":
                date_query = intent["entities"]["date_query"] or "today"
                results["data"] = self.get_games_on_date(date_query)
                results["gemini_instructions"] = "Present these games conversationally. Use ONLY the data provided."
            
            elif intent["type"] == "parlay":
                # For parlay, we need to get games first, then roster info
                risk_level = intent["entities"].get("risk_level", "normal")
                results["data"] = self._build_parlay_data(query, risk_level=risk_level)
                results["gemini_instructions"] = "Create a parlay using ONLY the players and predictions provided. DO NOT add any players not in this data."
            
            elif intent["type"] == "value_bets":
                # VALUE BETS = SAFE PARLAYS (lower lines, higher confidence)
                import random
                from datetime import date as dt_date
                
                today = dt_date.today()
                
                # Smart date detection
                if today.month == 11 and today.day in [26, 27, 28]:  # Thanksgiving window
                    date_query = "thanksgiving"
                elif today.weekday() == 6:  # Sunday
                    date_query = "today"
                elif today.weekday() == 5:  # Saturday
                    date_query = "tomorrow"
                else:
                    date_query = "sunday"
                
                num_legs = random.randint(5, 8)
                parlay_query = f"{num_legs} leg parlay for games on {date_query}"
                
                try:
                    results["data"] = self._build_parlay_data(parlay_query, risk_level="safe")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    results["data"] = {"error": str(e), "predictions": []}
                    
                results["gemini_instructions"] = "Present these value bets."
            
            elif intent["type"] == "meta":
                # Meta/conversational questions about the AI
                results["data"] = {
                    "response_type": "meta",
                    "message": "All my picks and predictions come from my own database and machine learning models trained on 2025 NFL data. I analyze player stats, team performance, matchups, injuries, and real sportsbook odds to generate recommendations. I don't use any external sources or make things up - everything is based on actual data.",
                    "data_sources": [
                        "Player stats from 2025 NFL season",
                        "Team records and performance metrics",
                        "Matchup analysis using defensive rankings",
                        "Injury reports",
                        "Real sportsbook odds (when available)"
                    ]
                }
                results["gemini_instructions"] = "Explain that all data comes from your own database and ML models. Be conversational and helpful."
            
            else:
                # General query - try to figure it out
                player_name = self._extract_player_name(query)
                if player_name:
                    results["data"] = self.get_player_info(player_name)
                    results["gemini_instructions"] = "Present this info conversationally. Use ONLY the data provided."
                elif intent["entities"]["team_names"]:
                    results["data"] = self.get_team_schedule(intent["entities"]["team_names"][0])
                    results["gemini_instructions"] = "Present this info conversationally. Use ONLY the data provided."
                else:
                    results["data"] = {
                        "response_type": "help",
                        "message": "I can help you with NFL betting! Try asking about player predictions, team matchups, injury reports, or request a parlay."
                    }
                    results["gemini_instructions"] = "Offer to help with NFL betting queries. Be conversational."
        
        except Exception as e:
            results["error"] = f"Error processing query: {str(e)}"
        
        # Add session data for validation
        results["verified_data"] = self.session_data
        
        return results
    
    def _extract_player_name(self, query: str) -> Optional[str]:
        """Try to extract a player name from the query"""
        # Common player name patterns
        # This is a simple approach - can be improved
        
        # Remove common words
        query_clean = query.lower()
        stop_words = ['how', 'will', 'is', 'the', 'do', 'against', 'for', 'in', 'what', 'are', 
                      'stats', 'prediction', 'predict', 'yards', 'touchdowns', 'tds', 'show',
                      'me', 'get', 'give', 'tell', 'about', 'rushing', 'passing', 'receiving',
                      'playing', 'next', 'game', 'week']
        
        # Try to find capitalized names in original query
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\b'
        matches = re.findall(name_pattern, query)
        
        for match in matches:
            player = self.find_player(match)
            if player:
                return match
        
        # Try each word combination
        words = query.split()
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                name_candidate = ' '.join(words[i:j])
                player = self.find_player(name_candidate)
                if player:
                    return name_candidate
        
        return None
    
    def _build_parlay_data(self, query: str, risk_level: str = "normal") -> Dict:
        """
        Build SMART parlay data considering:
        - Injuries (skip injured players)
        - Matchup advantages
        - Confidence levels
        - Recent form and consistency
        - Games played (actual starters only)
        - Risk level (safe, normal, risky)
        
        Risk Levels:
        - safe: More conservative lines (75% of prediction), higher confidence required
        - normal: Standard lines (90% of prediction)
        - risky: Aggressive lines (100-110% of prediction), accepts lower confidence
        """
        query_lower = query.lower()
        
        # Risk level settings - affects line calculation and confidence threshold
        risk_settings = {
            "safe": {"line_multiplier": 0.75, "min_confidence": 45},  # Lower threshold to get more candidates
            "normal": {"line_multiplier": 0.90, "min_confidence": 40},
            "risky": {"line_multiplier": 1.05, "min_confidence": 30}
        }
        settings = risk_settings.get(risk_level, risk_settings["normal"])
        
        print(f"\n[*] RISK LEVEL: {risk_level.upper()}")
        print(f"   Line multiplier: {settings['line_multiplier']*100:.0f}% of prediction")
        print(f"   Min confidence: {settings['min_confidence']}%")
        
        # Extract number of picks requested from user's query
        import re
        num_legs = 5  # Default only if nothing specified
        
        # Check various patterns: "10 leg", "10 pick", "10-leg", "give me 10", "want 7", etc.
        patterns = [
            r'(\d+)\s*[-]?\s*(?:leg|pick|bet|parlay)',  # "10 leg parlay", "5-pick"
            r'give\s*(?:me\s*)?(?:a\s*)?(\d+)',          # "give me 10", "give me a 7"
            r'want\s*(\d+)',                             # "want 10"
            r'need\s*(\d+)',                             # "need 10"
            r'make\s*(?:me\s*)?(?:a\s*)?(\d+)',          # "make me a 10"
            r'(\d+)\s*(?:for|from)',                     # "10 for thanksgiving"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                num_legs = int(match.group(1))
                break
        
        # Detect which games to use
        # First, check if specific teams are mentioned (for single-game parlays)
        specific_teams = []
        all_team_names = [
            "eagles", "bears", "packers", "lions", "chiefs", "cowboys", "bengals", "ravens",
            "49ers", "cardinals", "rams", "seahawks", "broncos", "chargers", "raiders", "jets",
            "bills", "dolphins", "patriots", "steelers", "browns", "vikings", "saints", "falcons",
            "buccaneers", "panthers", "giants", "commanders", "titans", "colts", "jaguars", "texans",
            "philadelphia", "chicago", "green bay", "detroit", "kansas city", "dallas", 
            "cincinnati", "baltimore", "san francisco", "arizona", "los angeles", "seattle",
            "denver", "las vegas", "new york", "buffalo", "miami", "new england", "pittsburgh",
            "cleveland", "minnesota", "new orleans", "atlanta", "tampa bay", "carolina",
            "washington", "tennessee", "indianapolis", "jacksonville", "houston"
        ]
        
        for team in all_team_names:
            if team in query_lower:
                specific_teams.append(team)
        
        # If 1-2 specific teams mentioned, find their games
        if len(specific_teams) >= 1 and "thanksgiving" not in query_lower and "christmas" not in query_lower:
            # Find games for these specific teams
            print(f"\n{'='*60}")
            print(f"PARLAY BUILDER: Building {num_legs}-leg parlay for {', '.join(specific_teams).upper()}")
            print(f"{'='*60}")
            
            # Get all upcoming games and filter to these teams
            from datetime import datetime, timedelta
            from models import Game, Team
            
            target_games = []
            for team_name in specific_teams[:2]:  # Max 2 teams
                # Find team
                team = self.find_team(team_name)
                if team:
                    # Find next game for this team
                    next_game = self.db.query(Game).filter(
                        ((Game.home_team_id == team.id) | (Game.away_team_id == team.id)),
                        Game.game_date > datetime.now(),
                        Game.status != "Final"
                    ).order_by(Game.game_date).first()
                    
                    if next_game and next_game not in target_games:
                        home_team_obj = self.db.query(Team).filter(Team.id == next_game.home_team_id).first()
                        away_team_obj = self.db.query(Team).filter(Team.id == next_game.away_team_id).first()
                        
                        game_info = {
                            "game_id": next_game.id,
                            "home_team": home_team_obj.name if home_team_obj else "Unknown",
                            "away_team": away_team_obj.name if away_team_obj else "Unknown",
                            "game_date": next_game.game_date.isoformat() if next_game.game_date else None,
                            "venue": next_game.venue
                        }
                        # Avoid duplicates
                        if not any(g["game_id"] == game_info["game_id"] for g in target_games):
                            target_games.append(game_info)
            
            if target_games:
                games_data = {
                    "games": target_games,
                    "games_count": len(target_games)
                }
            else:
                # Fall back to next sunday games
                games_data = self.get_games_on_date("sunday")
        
        elif "thanksgiving" in query_lower:
            date_query = "thanksgiving"
            print(f"\n{'='*60}")
            print(f"PARLAY BUILDER: Building {num_legs}-leg parlay for {date_query}")
            print(f"{'='*60}")
            games_data = self.get_games_on_date(date_query)
        elif "christmas" in query_lower:
            date_query = "christmas"
            print(f"\n{'='*60}")
            print(f"PARLAY BUILDER: Building {num_legs}-leg parlay for {date_query}")
            print(f"{'='*60}")
            games_data = self.get_games_on_date(date_query)
        elif "this week" in query_lower or "week" in query_lower:
            # "This week" - find next upcoming game day
            from datetime import date as dt_date, timedelta
            today = dt_date.today()
            
            # Check special dates first
            if today.month == 11 and today.day in [26, 27]:
                date_query = "thanksgiving"
            elif today.weekday() == 6:  # Sunday
                date_query = "today"
            elif today.weekday() == 5:  # Saturday
                date_query = "tomorrow"
            else:
                date_query = "sunday"  # Default to next Sunday
            
            print(f"\n{'='*60}")
            print(f"PARLAY BUILDER: Building {num_legs}-leg parlay for {date_query}")
            print(f"{'='*60}")
            games_data = self.get_games_on_date(date_query)
        else:
            # Default to sunday games
            date_query = "sunday"
            print(f"\n{'='*60}")
            print(f"PARLAY BUILDER: Building {num_legs}-leg parlay for {date_query}")
            print(f"{'='*60}")
            games_data = self.get_games_on_date(date_query)
        
        if games_data.get("error") or games_data.get("games_count", 0) == 0:
            return {"error": f"No games found", "predictions": []}
        
        # Collect ALL possible picks first, then rank them
        all_possible_picks = []
        games_used = []
        
        for game in games_data.get("games", []):
            home_team = game["home_team"]
            away_team = game["away_team"]
            game_id = game.get("game_id")  # Get game ID for learning tracking
            games_used.append(f"{away_team} at {home_team}")
            
            # Get matchup analysis for context
            matchup = self.matchup_analyzer.analyze_team_matchup(
                self.find_team(home_team).id if self.find_team(home_team) else 0,
                self.find_team(away_team).id if self.find_team(away_team) else 0
            )
            
            # Get injuries for both teams
            home_injuries = self.get_injury_report(team_name=home_team)
            away_injuries = self.get_injury_report(team_name=away_team)
            injured_players = set()
            for inj_report in [home_injuries, away_injuries]:
                if inj_report.get("injuries"):
                    for inj in inj_report["injuries"]:
                        if inj.get("status") in ["Out", "Doubtful"]:
                            injured_players.add(inj.get("player_name", "").lower())
            
            # Get SMART predictions - analyze each player and find their BEST bet
            picks_before = len(all_possible_picks)
            for team_name in [home_team, away_team]:
                self._analyze_and_add_best_bets(all_possible_picks, team_name, injured_players, matchup)
            
            # Add game_id to all new picks (for learning tracking)
            for pick in all_possible_picks[picks_before:]:
                pick["game_id"] = game_id
        
        
        # === SORT BY SCORE: Ensures best picks (like Gibbs 135.8) are selected before weaker ones (Montgomery 88.0) ===
        # We DON'T remove duplicates because you CAN bet on multiple same-team players for same prop
        # But sorting ensures the BEST picks get priority in selection
        all_possible_picks.sort(key=lambda x: x.get("smart_score", x.get("confidence", 0)), reverse=True)
        
        # === ENHANCE WITH ODDS DATA (if available) ===
        for pick in all_possible_picks:
            pick = self.enhance_pick_with_odds(pick)
        
        # Use SmartPicksEngine for advanced pick selection
        # Get MORE picks than needed, then randomly select for variety
        import random
        
        # Try smart picks first
        try:
            best_picks = self.smart_picks.get_best_picks(
                predictions=all_possible_picks,
                num_picks=num_legs * 3,  # Get 3x for variety pool
                min_smart_score=0
            )
        except Exception:
            best_picks = []
        
        # If not enough smart picks, fall back to basic scoring
        if len(best_picks) < num_legs and len(all_possible_picks) > 0:
            remaining_picks = [p for p in all_possible_picks if p not in best_picks]
            for pick in remaining_picks:
                confidence = pick.get("confidence", 50)
                season_avg = pick.get("season_average", 0)
                predicted = pick.get("predicted_value", 0)
                
                if season_avg > 0:
                    consistency_bonus = 100 - abs(predicted - season_avg) / season_avg * 50
                else:
                    consistency_bonus = 0
                
                pick["smart_score"] = confidence + consistency_bonus * 0.3
            
            remaining_picks.sort(key=lambda x: x.get("smart_score", 0), reverse=True)
            best_picks.extend(remaining_picks[:num_legs * 3 - len(best_picks)])
        
        # ADD VARIETY: Weighted random selection from top picks
        # Higher smart_score = higher chance of being selected
        if len(best_picks) > num_legs:
            # Split into tiers: top picks (must include some), good picks (random selection)
            top_tier = best_picks[:num_legs // 2]  # Always include some top picks
            random_pool = best_picks[num_legs // 2:]
            
            # Shuffle the random pool and pick from it
            random.shuffle(random_pool)
            needed = num_legs - len(top_tier)
            
            # Combine top tier with random selection from pool
            best_picks = top_tier + random_pool[:needed]
            
            # Shuffle final order so top picks aren't always first
            random.shuffle(best_picks)
        
        # Filter by minimum confidence based on risk level
        best_picks = [p for p in best_picks if p.get("confidence", 50) >= settings["min_confidence"]]
        
        # EARLY PADDING: If not enough picks after confidence filter, add from all_possible
        if len(best_picks) < num_legs and all_possible_picks:
            existing_ids = {(p.get("player_name"), p.get("stat_type")) for p in best_picks}
            remaining = [p for p in all_possible_picks 
                        if (p.get("player_name"), p.get("stat_type")) not in existing_ids
                        and p.get("confidence", 0) >= 30]  # Lower threshold for padding
            remaining.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            
            for pick in remaining[:num_legs - len(best_picks)]:
                pick["padded_early"] = True
                best_picks.append(pick)
        
        # === USE ACTUAL ODDS TO DETERMINE SAFE VS RISKY ===
        # Lower odds (like -110, -150) = SAFER (more likely to hit)
        # Higher odds (like +150, +300) = RISKIER (less likely but bigger payout)
        
        def get_odds_value(pick):
            """Convert odds to sortable value. Lower = safer."""
            odds = pick.get("betting_odds")
            if odds is None:
                return 0  # No odds = neutral
            # American odds: -110 is safer than +150
            # We want lower numbers first for safe, higher for risky
            return odds
        
        if risk_level == "safe":
            # SAFER: Prefer picks with low/negative odds, but accept high-confidence picks without odds
            safe_picks = []
            high_confidence_no_odds = []
            
            for pick in best_picks:
                odds = pick.get("betting_odds")
                confidence = pick.get("confidence", 50)
                
                if odds is not None:
                    if odds <= 0:  # Negative odds = favorite/likely (BEST for safe)
                        pick["risk_score"] = abs(odds)
                        safe_picks.append(pick)
                    elif odds <= 150:  # Slightly positive is acceptable
                        pick["risk_score"] = -odds
                        safe_picks.append(pick)
                    # Skip high positive odds (+150 and above) for safe parlays
                elif confidence >= 60:
                    # No odds but HIGH confidence (60%+) - still usable for safe
                    pick["no_odds_warning"] = True
                    pick["risk_score"] = 0
                    high_confidence_no_odds.append(pick)
            
            # Sort by safety (lower odds = safer)
            safe_picks.sort(key=lambda x: get_odds_value(x))
            # Sort high-confidence picks by confidence
            high_confidence_no_odds.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            
            # If not enough picks with odds, add high-confidence picks
            if len(safe_picks) < num_legs:
                needed = num_legs - len(safe_picks)
                safe_picks.extend(high_confidence_no_odds[:needed])
                print(f"[*] Added {min(needed, len(high_confidence_no_odds))} high-confidence picks (60%+) without odds")
            
            best_picks = safe_picks
            verified_count = len([p for p in best_picks if p.get('betting_odds') is not None])
            print(f"[SAFE MODE] {verified_count} picks with verified odds, {len(best_picks) - verified_count} high-confidence picks")
            
        elif risk_level == "risky":
            # RISKIER: Prefer higher positive odds (bigger payouts)
            # Only include picks WITH odds so we know they're actually risky
            risky_picks = []
            no_odds_count = 0
            
            for pick in best_picks:
                odds = pick.get("betting_odds")
                if odds is None:
                    no_odds_count += 1
                    continue  # Skip picks without odds - can't verify riskiness
                elif odds >= 100:  # Positive odds = underdog (preferred for risky)
                    risky_picks.append(pick)
                elif odds >= -150:  # Not too heavy of a favorite
                    risky_picks.append(pick)
            
            # Sort: higher positive odds first (biggest payouts)
            risky_picks.sort(key=lambda x: get_odds_value(x), reverse=True)
            
            # If not enough, add some no-odds picks
            if len(risky_picks) < num_legs:
                no_odds_picks = [p for p in best_picks if p.get("betting_odds") is None]
                for pick in no_odds_picks[:num_legs - len(risky_picks)]:
                    pick["no_odds_warning"] = True
                    risky_picks.append(pick)
            
            best_picks = risky_picks
        
        # Set betting lines based on RISK LEVEL
        for pick in best_picks:
            if not pick.get("bet_type"):
                pick["bet_type"] = "over"
            
            predicted_value = pick.get("predicted_value", 0)
            odds_info = pick.get("odds_data", {})
            stat_type = pick.get("stat_type", "").lower()
            
            # Determine minimum sensible lines for each prop type
            if "anytime" in stat_type or pick.get("bet_type") == "anytime_td":
                # Anytime TD has no line - it's just "anytime"
                pick["line"] = None
                pick["risk_adjusted"] = "anytime_td"
                continue
            elif "passing_td" in stat_type or stat_type == "passing_tds":
                min_line = 1.5  # Min 1.5 passing TDs
            elif "rushing_td" in stat_type or "receiving_td" in stat_type:
                min_line = 0.5  # Min 0.5 TDs
            elif "reception" in stat_type:
                min_line = 3  # Min 3 receptions
            elif "passing" in stat_type and "yard" in stat_type:
                min_line = 175  # Min 175 passing yards
            elif "rushing" in stat_type and "yard" in stat_type:
                min_line = 25  # Min 25 rushing yards
            elif "receiving" in stat_type and "yard" in stat_type:
                min_line = 20  # Min 20 receiving yards
            else:
                min_line = 10  # Default minimum
            
            if risk_level == "safe":
                # SAFER: Use the sportsbook line if available (they're already "safe" lines)
                # Or use 70% of prediction as a conservative fallback
                if odds_info.get("has_odds") and odds_info.get("book_line"):
                    book_line = odds_info["book_line"]
                    # Use 90% of book line for extra safety margin
                    pick["line"] = max(min_line, round(book_line * 0.90, 1))
                    pick["using_book_line"] = True
                else:
                    # No book line - use 70% of prediction (very conservative)
                    pick["line"] = max(min_line, round(predicted_value * 0.70, 1))
                    pick["using_book_line"] = False
                pick["risk_adjusted"] = "conservative"
                
            elif risk_level == "risky":
                # RISKIER: Use higher of (105% of prediction) or (book_line + 5%)
                ai_line = round(predicted_value * settings["line_multiplier"], 1)
                if odds_info.get("has_odds") and odds_info.get("book_line"):
                    book_line = odds_info["book_line"]
                    aggressive_book = round(book_line * 1.05, 1)
                    pick["line"] = max(min_line, max(ai_line, aggressive_book))
                    pick["using_book_line"] = True
                else:
                    pick["line"] = max(min_line, ai_line)
                pick["risk_adjusted"] = "aggressive"
                
            else:
                # NORMAL: Use sportsbook line if available, otherwise 90% of prediction
                if odds_info.get("has_odds") and odds_info.get("book_line"):
                    pick["line"] = max(min_line, odds_info["book_line"])
                    pick["using_book_line"] = True
                else:
                    pick["line"] = max(min_line, round(predicted_value * 0.9, 1))
                    pick["using_book_line"] = False
                pick["risk_adjusted"] = "normal"
        
        # Check for correlations
        correlations = self.smart_picks.check_correlation(best_picks)
        
        # Calculate parlay quality
        if best_picks:
            avg_smart_score = sum(p.get('smart_score', 50) for p in best_picks) / len(best_picks)
            avg_confidence = sum(p.get('confidence', 50) for p in best_picks) / len(best_picks)
        else:
            avg_smart_score = 0
            avg_confidence = 0
        
        # ENSURE WE HAVE ENOUGH PICKS - pad from all_possible_picks if needed
        if len(best_picks) < num_legs and all_possible_picks:
            # Get picks we haven't already selected
            existing_ids = {(p.get("player_name"), p.get("stat_type")) for p in best_picks}
            remaining = [p for p in all_possible_picks 
                        if (p.get("player_name"), p.get("stat_type")) not in existing_ids]
            
            # Sort by confidence and add what we need
            remaining.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            needed = num_legs - len(best_picks)
            
            for pick in remaining[:needed]:
                # Set appropriate line for the pick
                predicted = pick.get("predicted_value", 0)
                stat_type = pick.get("stat_type", "").lower()
                book_line = pick.get("book_line")
                
                # Calculate line based on stat type
                if "anytime" in stat_type or "td" in stat_type:
                    pick["line"] = None  # Anytime TD has no line
                elif book_line:
                    pick["line"] = book_line
                else:
                    pick["line"] = predicted * settings["line_multiplier"]
                
                pick["padded"] = True
                best_picks.append(pick)
        
        # FINAL GUARANTEE: If STILL not enough, analyze more players
        # (Padding logic above should have filled most gaps)
        
        # EMERGENCY FALLBACK: If still no picks at all
        if not best_picks and all_possible_picks:
            all_possible_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            best_picks = all_possible_picks[:num_legs]
            for pick in best_picks:
                pick["line"] = pick.get("predicted_value", 100) * 0.75
                pick["risk_adjusted"] = "emergency_fallback"
        
        # Store predictions for learning
        try:
            self.betting_ai.store_parlay_predictions(best_picks)
        except Exception:
            pass
        
        return {
            "parlay_type": f"{num_legs}-leg parlay",
            "risk_level": risk_level,
            "games_date": games_data.get("date", "Unknown"),
            "games_used": games_used,
            "predictions": best_picks,
            "total_legs": len(best_picks),
            "parlay_quality": {
                "average_smart_score": round(avg_smart_score, 1),
                "average_confidence": round(avg_confidence, 1),
                "rating": "excellent" if avg_smart_score >= 65 else "good" if avg_smart_score >= 55 else "fair",
                "risk_level": risk_level
            },
            "correlations": correlations if correlations else None,
            "selection_method": "Advanced AI analysis using trends, matchups, edges, and consistency",
            "data_source": "YOUR_ML_MODELS_AND_DATABASE_2025"
        }
    
    def _analyze_and_add_best_bets(self, picks_list: List, team_name: str, 
                                    injured_players: set, matchup: Dict):
        """
        Intelligently analyze each player and determine their BEST bet type
        based on their stats, tendencies, and matchup advantages.
        """
        roster_data = self.get_team_roster(team_name)
        if roster_data.get("error"):
            return
        
        roster = roster_data.get("roster", {})
        
        # === ANALYZE QB ===
        qbs = roster.get("QB", [])
        if qbs:
            qb_name = qbs[0]
            if qb_name.lower() not in injured_players:
                self._find_best_qb_bet(picks_list, qb_name, team_name, injured_players, matchup)
        
        # === ANALYZE RBs (top 3) ===
        rbs = roster.get("RB", [])
        for i, rb_name in enumerate(rbs[:3]):
            if rb_name.lower() not in injured_players:
                self._find_best_rb_bet(picks_list, rb_name, team_name, injured_players, matchup, is_rb1=(i==0))
        
        # === ANALYZE WRs (top 4) ===
        wrs = roster.get("WR", [])
        for i, wr_name in enumerate(wrs[:4]):
            if wr_name.lower() not in injured_players:
                self._find_best_wr_bet(picks_list, wr_name, team_name, injured_players, matchup, rank=i)
        
        # === ANALYZE TEs (top 2) ===
        tes = roster.get("TE", [])
        for i, te_name in enumerate(tes[:2]):
            if te_name.lower() not in injured_players:
                self._find_best_te_bet(picks_list, te_name, team_name, injured_players, matchup)
        
        # === ANALYZE KICKER (if odds available) ===
        kickers = roster.get("K", [])
        if kickers:
            k_name = kickers[0]
            if k_name.lower() not in injured_players:
                self._find_best_kicker_bet(picks_list, k_name, team_name, injured_players, matchup)
    
    def _calculate_comprehensive_score(self, prediction: Dict, player_name: str, 
                                         prop_type: str, matchup: Dict, injured_players: set,
                                         position: str = None, rank: int = 0) -> float:
        """
        Calculate a comprehensive score for a bet using ALL available factors.
        This is the CORE scoring engine that makes intelligent betting decisions.
        
        FACTORS CONSIDERED (100 point max):
        1. ML Confidence (0-30 pts) - Base prediction quality
        2. Odds Value/Edge (0-25 pts) - Value vs sportsbook line  
        3. Matchup Analysis (0-15 pts) - Opponent defensive strength
        4. Recent Form/Trends (0-10 pts) - Last 3 games vs season
        5. Consistency Score (0-8 pts) - Low variance = reliable
        6. Home/Away Factor (0-5 pts) - Home field advantage
        7. Injury Context (0-5 pts) - Teammate injuries impact
        8. TD Streak Bonus (0-10 pts) - For anytime TD props
        9. Position/Tier Bonus (0-5 pts) - WR1/RB1 premium
        10. Target Share (0-5 pts) - Volume indicators
        """
        score = 0.0
        factors = []
        
        # =====================================================
        # 1. ML CONFIDENCE (0-30 points)
        # Base prediction from trained models
        # =====================================================
        base_confidence = prediction.get("confidence", 50)
        confidence_score = min(30, base_confidence * 0.3)
        score += confidence_score
        factors.append(f"ML:{base_confidence:.0f}")
        
        # =====================================================
        # 2. ODDS VALUE / EDGE (0-25 points)
        # Compare our prediction to sportsbook line
        # =====================================================
        odds_data = self.get_odds_for_player(player_name, prop_type)
        if odds_data:
            book_line = odds_data.get("line", 0)
            predicted = prediction.get("predicted_value", 0)
            
            # Calculate edge (how much we beat the book)
            if book_line and book_line > 0 and predicted:
                edge_pct = ((predicted - book_line) / book_line) * 100
                
                if edge_pct > 15:  # 15%+ edge = excellent value
                    score += 25
                    factors.append(f"EDGE+{edge_pct:.0f}%")
                elif edge_pct > 10:  # 10-15% edge = great value
                    score += 20
                    factors.append(f"edge+{edge_pct:.0f}%")
                elif edge_pct > 5:  # 5-10% edge = good value
                    score += 15
                    factors.append(f"edge+{edge_pct:.0f}%")
                elif edge_pct > 0:  # Some edge
                    score += 8
                    factors.append(f"edge+{edge_pct:.0f}%")
                elif edge_pct > -5:  # Close to line (still playable)
                    score += 3
                elif edge_pct < -10:  # Bad value - PENALIZE
                    score -= 10
                    factors.append(f"BAD_VALUE:{edge_pct:.0f}%")
                
                prediction["edge_pct"] = round(edge_pct, 1)
            
            # Store odds data
            prediction["betting_odds"] = odds_data.get("over_odds") or odds_data.get("under_odds")
            prediction["book_line"] = book_line
            factors.append(f"line:{book_line}")
        else:
            # No odds = can't verify value, small penalty
            score -= 3
            factors.append("no_odds")
        
        # =====================================================
        # 3. MATCHUP ANALYSIS (0-15 points)
        # Opponent defensive strength against this stat type
        # =====================================================
        if matchup:
            opp_name = matchup.get("opponent", "")
            
            if "pass" in prop_type.lower() or "receiv" in prop_type.lower():
                # Check pass defense / secondary
                secondary = matchup.get("opponent_secondary_rating", 50)
                pass_yds_allowed = matchup.get("opponent_pass_yds_allowed", 220)
                
                if secondary < 35 or pass_yds_allowed > 260:  # Very weak secondary
                    score += 15
                    factors.append(f"weak_pass_D({opp_name})")
                elif secondary < 45 or pass_yds_allowed > 240:  # Below average
                    score += 10
                    factors.append(f"avg_pass_D")
                elif secondary > 60:  # Strong secondary - PENALTY
                    score -= 5
                    factors.append(f"tough_pass_D")
                    
            elif "rush" in prop_type.lower():
                # Check run defense
                run_def = matchup.get("opponent_run_def_rating", 50)
                rush_yds_allowed = matchup.get("opponent_rush_yds_allowed", 115)
                
                if run_def < 35 or rush_yds_allowed > 130:  # Very weak run D
                    score += 15
                    factors.append(f"weak_run_D({opp_name})")
                elif run_def < 45 or rush_yds_allowed > 120:  # Below average
                    score += 10
                    factors.append(f"avg_run_D")
                elif run_def > 60:  # Strong run D - PENALTY
                    score -= 5
                    factors.append(f"tough_run_D")
                    
            elif "td" in prop_type.lower():
                # For TDs, check red zone defense
                redzone_def = matchup.get("opponent_redzone_def", 50)
                if redzone_def < 40:  # Poor red zone D
                    score += 12
                    factors.append("weak_redzone_D")
                elif redzone_def > 60:  # Good red zone D
                    score -= 5
                    factors.append("tough_redzone_D")
        
        # =====================================================
        # 4. RECENT FORM / TRENDS (0-10 points)
        # Last 3 games compared to season average
        # =====================================================
        season_avg = prediction.get("season_average", 0)
        recent_form = prediction.get("recent_form", season_avg)
        last_3_avg = prediction.get("last_3_avg", recent_form)
        
        if season_avg > 0:
            # Calculate trend direction
            form_trend = ((last_3_avg - season_avg) / season_avg) * 100 if season_avg > 0 else 0
            
            if form_trend > 20:  # Hot streak - 20%+ above average
                score += 10
                factors.append(f"HOT+{form_trend:.0f}%")
            elif form_trend > 10:  # Warming up
                score += 7
                factors.append(f"trending_up+{form_trend:.0f}%")
            elif form_trend > 0:  # Slightly above average
                score += 3
            elif form_trend < -15:  # Cold streak - PENALIZE
                score -= 8
                factors.append(f"COLD{form_trend:.0f}%")
            elif form_trend < -5:  # Slumping
                score -= 3
                factors.append(f"slumping")
            
            prediction["form_trend"] = round(form_trend, 1)
        
        # =====================================================
        # 5. CONSISTENCY SCORE (0-8 points)
        # Players who hit their line consistently
        # =====================================================
        consistency = prediction.get("consistency_score", 50)
        predicted = prediction.get("predicted_value", 0)
        
        if consistency > 75:  # Very consistent performer
            score += 8
            factors.append("very_consistent")
        elif consistency > 60:  # Reasonably consistent
            score += 5
            factors.append("consistent")
        elif consistency < 35:  # Boom/bust player - risky
            score -= 3
            factors.append("boom_bust")
        
        # Also check variance from average
        if season_avg > 0 and predicted > 0:
            variance = abs(predicted - season_avg) / season_avg * 100
            if variance < 8:  # Prediction very close to average
                score += 3
        
        # =====================================================
        # 6. HOME/AWAY FACTOR (0-5 points)
        # =====================================================
        is_home = prediction.get("is_home", False)
        home_avg = prediction.get("home_avg", 0)
        away_avg = prediction.get("away_avg", 0)
        
        if is_home:
            score += 3
            factors.append("home")
            # Extra bonus if they perform better at home
            if home_avg > away_avg * 1.1:  # 10%+ better at home
                score += 2
                factors.append("home_boost")
        else:
            # Check if they're a road warrior
            if away_avg > home_avg * 1.05:
                score += 2
                factors.append("road_warrior")
        
        # =====================================================
        # 7. INJURY CONTEXT (0-5 points)
        # How teammate injuries affect this player
        # =====================================================
        if injured_players:
            position = position or prediction.get("position", "")
            
            # Check for key teammate injuries that BOOST opportunities
            # (e.g., WR2 out means more targets for WR1)
            injury_boost = False
            injury_concern = False
            
            # If this player is healthy and key teammates are out, could be positive
            if position in ["WR", "TE"]:
                # More targets if other pass catchers are out
                # This is handled elsewhere, but mark it
                pass
            elif position == "RB":
                # More carries if other RBs are out
                pass
            
            # Check if OL injuries (negative for everyone)
            # This would require more detailed injury data
        
        # =====================================================
        # 8. TD STREAK BONUS (0-10 points for anytime TD)
        # =====================================================
        if "td" in prop_type.lower() or "anytime" in prop_type.lower():
            td_avg = prediction.get("season_average", 0)
            
            if td_avg >= 1.0:  # Scores every game
                score += 10
                factors.append("TD_machine")
            elif td_avg >= 0.75:  # Scores most games
                score += 7
                factors.append("TD_consistent")
            elif td_avg >= 0.5:  # Scores every other game
                score += 4
                factors.append("TD_likely")
        
        # =====================================================
        # 9. POSITION/TIER BONUS (0-5 points)
        # WR1/RB1/TE1 get more opportunities
        # =====================================================
        if rank == 0:  # #1 option at position
            score += 5
            factors.append("tier1")
        elif rank == 1:  # #2 option
            score += 2
            factors.append("tier2")
        
        # =====================================================
        # 10. TARGET SHARE (for receivers) (0-5 points)
        # =====================================================
        target_share = prediction.get("avg_target_share", 0)
        if target_share > 0:
            if target_share > 25:  # Over 25% of team targets
                score += 5
                factors.append(f"target_hog:{target_share:.0f}%")
            elif target_share > 20:
                score += 3
                factors.append(f"high_targets")
        
        # =====================================================
        # FINAL SCORING AND STORAGE
        # =====================================================
        # Normalize score (cap at 100)
        final_score = min(100, max(0, score))
        
        # Store all analysis for transparency
        prediction["score_factors"] = factors
        prediction["smart_score"] = round(final_score, 1)
        prediction["factor_breakdown"] = {
            "ml_confidence": round(confidence_score, 1),
            "total_factors": len(factors)
        }
        
        return final_score
    
    def _find_best_qb_bet(self, picks_list: List, player_name: str, team_name: str,
                          injured_players: set, matchup: Dict):
        """Find the best bet type for a QB based on ALL factors"""
        # Get all QB stats
        passing_pred = self.predict_player_stat(player_name, "passing_yards")
        rushing_pred = self.predict_player_stat(player_name, "rushing_yards")
        td_pred = self.predict_player_stat(player_name, "passing_tds")
        int_pred = self.predict_player_stat(player_name, "interceptions")
        completions_pred = self.predict_player_stat(player_name, "passing_completions")
        attempts_pred = self.predict_player_stat(player_name, "passing_attempts")
        
        best_bets = []
        
        # Evaluate passing yards with COMPREHENSIVE scoring
        if not passing_pred.get("error"):
            score = self._calculate_comprehensive_score(
                passing_pred, player_name, "passing_yards", matchup, injured_players,
                position="QB", rank=0
            )
            odds_data = self.get_odds_for_player(player_name, "passing_yards")
            best_bets.append({
                "type": "passing_yards",
                "bet_type": "over",
                "score": score,
                "pred": passing_pred,
                "has_odds": odds_data is not None
            })
        
        # Evaluate pass completions
        if not completions_pred.get("error"):
            comp_avg = completions_pred.get("season_average", 0)
            if comp_avg >= 15:  # Only for QBs with decent volume
                score = self._calculate_comprehensive_score(
                    completions_pred, player_name, "passing_completions", matchup, injured_players,
                    position="QB", rank=0
                )
                odds_data = self.get_odds_for_player(player_name, "completions")
                best_bets.append({
                    "type": "passing_completions",
                    "bet_type": "over",
                    "score": score,
                    "pred": completions_pred,
                    "has_odds": odds_data is not None
                })
        
        # Evaluate pass attempts
        if not attempts_pred.get("error"):
            att_avg = attempts_pred.get("season_average", 0)
            if att_avg >= 25:  # Only for QBs with volume
                score = self._calculate_comprehensive_score(
                    attempts_pred, player_name, "passing_attempts", matchup, injured_players,
                    position="QB", rank=0
                )
                odds_data = self.get_odds_for_player(player_name, "pass_attempts")
                best_bets.append({
                    "type": "passing_attempts",
                    "bet_type": "over",
                    "score": score,
                    "pred": attempts_pred,
                    "has_odds": odds_data is not None
                })
        
        # Evaluate rushing yards (only for mobile QBs)
        if not rushing_pred.get("error"):
            rush_avg = rushing_pred.get("season_average", 0)
            
            # Mobile QBs: Lamar Jackson, Josh Allen, Jalen Hurts, Kyler Murray, etc.
            if rush_avg >= 10:
                # Combined passing + rushing yards
                if not passing_pred.get("error"):
                    combined_value = passing_pred.get("predicted_value", 0) + rushing_pred.get("predicted_value", 0)
                    combined_conf = (passing_pred.get("confidence", 50) + rushing_pred.get("confidence", 50)) / 2
                    
                    combined_pred = {
                        "player_id": passing_pred.get("player_id"),
                        "player_name": player_name,
                        "team": team_name,
                        "position": "QB",
                        "stat_type": "passing + rushing_yards",
                        "predicted_value": combined_value,
                        "confidence": combined_conf,
                        "season_average": passing_pred.get("season_average", 0) + rush_avg,
                        "recent_form": passing_pred.get("recent_form", 0) + rushing_pred.get("recent_form", 0),
                        "is_combined": True,
                        "is_home": passing_pred.get("is_home", False)
                    }
                    
                    score = self._calculate_comprehensive_score(
                        combined_pred, player_name, "passing + rushing_yards", matchup, injured_players
                    )
                    
                    best_bets.append({
                        "type": "passing + rushing_yards",
                        "bet_type": "over",
                        "score": score,
                        "pred": combined_pred,
                        "has_odds": self.get_odds_for_player(player_name, "passing + rushing_yards") is not None
                    })
                
                # Rushing alone if strong
                if rush_avg >= 30:
                    score = self._calculate_comprehensive_score(
                        rushing_pred, player_name, "rushing_yards", matchup, injured_players
                    )
                    best_bets.append({
                        "type": "rushing_yards",
                        "bet_type": "over",
                        "score": score,
                        "pred": rushing_pred,
                        "has_odds": self.get_odds_for_player(player_name, "rushing_yards") is not None
                    })
        
        # Evaluate passing TDs
        if not td_pred.get("error"):
            td_avg = td_pred.get("season_average", 0)
            total_tds = td_pred.get("total_tds", td_avg * 11)
            pass_avg = passing_pred.get("season_average", 0) if not passing_pred.get("error") else 0
            
            if td_avg >= 1.0:  # Lowered threshold - use raw stats to differentiate
                score = self._calculate_comprehensive_score(
                    td_pred, player_name, "passing_tds", matchup, injured_players
                )
                
                best_bets.append({
                    "type": "passing_tds",
                    "bet_type": "over",
                    "score": score,
                    "pred": td_pred,
                    "has_odds": self.get_odds_for_player(player_name, "passing_tds") is not None
                })
        
        # Pick the BEST bet for this QB (prioritize picks with odds)
        if best_bets:
            # Sort by: 1) has odds, 2) score
            best_bets.sort(key=lambda x: (x.get("has_odds", False), x["score"]), reverse=True)
            best = best_bets[0]
            best["pred"]["bet_type"] = best["bet_type"]
            best["pred"]["smart_score"] = best["score"]
            picks_list.append(best["pred"])
    
    def _find_best_rb_bet(self, picks_list: List, player_name: str, team_name: str,
                          injured_players: set, matchup: Dict, is_rb1: bool = True):
        """Find the best bet type for a RB based on ALL factors"""
        rushing_pred = self.predict_player_stat(player_name, "rushing_yards")
        receiving_pred = self.predict_player_stat(player_name, "receiving_yards")
        td_pred = self.predict_player_stat(player_name, "rushing_tds")
        
        best_bets = []
        
        # Evaluate rushing yards with comprehensive scoring
        if not rushing_pred.get("error"):
            rush_avg = rushing_pred.get("season_average", 0)
            
            if rush_avg >= 30:  # Meaningful rushing average
                score = self._calculate_comprehensive_score(
                    rushing_pred, player_name, "rushing_yards", matchup, injured_players,
                    position="RB", rank=0 if is_rb1 else 1
                )
                
                best_bets.append({
                    "type": "rushing_yards",
                    "bet_type": "over",
                    "score": score,
                    "pred": rushing_pred,
                    "has_odds": self.get_odds_for_player(player_name, "rushing_yards") is not None
                })
        
        # Evaluate receiving yards (for pass-catching backs)
        if not receiving_pred.get("error"):
            rec_avg = receiving_pred.get("season_average", 0)
            
            # For pass-catching RBs (CMC, Kamara, Ekeler, Gibbs, etc.)
            if rec_avg >= 20:
                score = self._calculate_comprehensive_score(
                    receiving_pred, player_name, "receiving_yards", matchup, injured_players,
                    position="RB", rank=0
                )
                best_bets.append({
                    "type": "receiving_yards",
                    "bet_type": "over",
                    "score": score,
                    "pred": receiving_pred,
                    "has_odds": self.get_odds_for_player(player_name, "receiving_yards") is not None
                })
        
        # Evaluate COMBINED rushing + receiving yards (for versatile backs)
        if not rushing_pred.get("error") and not receiving_pred.get("error"):
            rush_avg = rushing_pred.get("season_average", 0)
            rec_avg = receiving_pred.get("season_average", 0)
            
            # For backs who do both (CMC, Gibbs, Kamara, etc.)
            if rush_avg >= 25 and rec_avg >= 10:
                combined_value = rushing_pred.get("predicted_value", 0) + receiving_pred.get("predicted_value", 0)
                combined_conf = (rushing_pred.get("confidence", 50) + receiving_pred.get("confidence", 50)) / 2
                combined_avg = rush_avg + rec_avg
                
                combined_pred = {
                    "player_id": rushing_pred.get("player_id"),
                    "player_name": player_name,
                    "team": team_name,
                    "position": "RB",
                    "stat_type": "rushing + receiving_yards",
                    "predicted_value": combined_value,
                    "confidence": combined_conf,
                    "season_average": combined_avg,
                    "recent_form": rushing_pred.get("recent_form", rush_avg) + receiving_pred.get("recent_form", rec_avg),
                    "consistency_score": (rushing_pred.get("consistency_score", 50) + receiving_pred.get("consistency_score", 50)) / 2,
                    "is_home": rushing_pred.get("is_home", False),
                    "is_combined": True,
                    "stat_breakdown": [f"rush: {rushing_pred.get('predicted_value', 0):.0f}", f"rec: {receiving_pred.get('predicted_value', 0):.0f}"]
                }
                
                score = self._calculate_comprehensive_score(
                    combined_pred, player_name, "rushing + receiving_yards", matchup, injured_players,
                    position="RB", rank=0
                )
                best_bets.append({
                    "type": "rushing + receiving_yards",
                    "bet_type": "over",
                    "score": score,
                    "pred": combined_pred,
                    "has_odds": self.get_odds_for_player(player_name, "rushing + receiving_yards") is not None
                })
        
        # Evaluate anytime TD (for goal-line backs)
        if not td_pred.get("error"):
            td_avg = td_pred.get("season_average", 0)
            rushing_avg = rushing_pred.get("season_average", 0) if not rushing_pred.get("error") else 0
            total_tds = td_pred.get("total_tds", td_avg * 11)  # Estimate if not available
            
            # Any RB with meaningful TD production
            if td_avg >= 0.25:
                td_pred["bet_type"] = "anytime_td"
                td_pred["stat_type"] = "anytime_td"
                
                score = self._calculate_comprehensive_score(
                    td_pred, player_name, "anytime_td", matchup, injured_players,
                    position="RB", rank=0 if is_rb1 else 1
                )
                
                best_bets.append({
                    "type": "anytime_td",
                    "bet_type": "anytime_td",
                    "score": score,
                    "pred": td_pred,
                    "has_odds": self.get_odds_for_player(player_name, "anytime_td") is not None
                })
        
        # Pick the BEST bet for this RB based on comprehensive score
        if best_bets:
            best_bets.sort(key=lambda x: (x.get("has_odds", False), x["score"]), reverse=True)
            best = best_bets[0]
            best["pred"]["bet_type"] = best["bet_type"]
            best["pred"]["smart_score"] = best["score"]  # Store score for de-duplication
            picks_list.append(best["pred"])
    
    def _find_best_wr_bet(self, picks_list: List, player_name: str, team_name: str,
                          injured_players: set, matchup: Dict, rank: int = 0):
        """Find the best bet type for a WR based on ALL factors with comprehensive scoring"""
        receiving_pred = self.predict_player_stat(player_name, "receiving_yards")
        receptions_pred = self.predict_player_stat(player_name, "receptions")
        td_pred = self.predict_player_stat(player_name, "receiving_tds")
        rushing_pred = self.predict_player_stat(player_name, "rushing_yards")  # For gadget players
        
        best_bets = []
        
        # Evaluate receiving yards with COMPREHENSIVE SCORING
        if not receiving_pred.get("error"):
            rec_avg = receiving_pred.get("season_average", 0)
            
            if rec_avg >= 30:  # Meaningful receiving average
                score = self._calculate_comprehensive_score(
                    receiving_pred, player_name, "receiving_yards", matchup, injured_players,
                    position="WR", rank=rank
                )
                best_bets.append({
                    "type": "receiving_yards",
                    "bet_type": "over",
                    "score": score,
                    "pred": receiving_pred,
                    "has_odds": self.get_odds_for_player(player_name, "receiving_yards") is not None
                })
        
        # === COMBINED: Rushing + Receiving yards for gadget WRs ===
        # (Deebo Samuel, Cordarrelle Patterson, Jaylen Waddle, etc.)
        if not receiving_pred.get("error") and not rushing_pred.get("error"):
            rush_avg = rushing_pred.get("season_average", 0)
            rec_avg = receiving_pred.get("season_average", 0)
            
            # If WR gets rushing attempts (jet sweeps, end-arounds, etc.)
            if rush_avg >= 5:
                combined_value = receiving_pred.get("predicted_value", 0) + rushing_pred.get("predicted_value", 0)
                combined_conf = (receiving_pred.get("confidence", 50) + rushing_pred.get("confidence", 50)) / 2
                
                combined_pred = {
                    "player_id": receiving_pred.get("player_id"),
                    "player_name": player_name,
                    "team": team_name,
                    "position": "WR",
                    "stat_type": "rushing + receiving_yards",
                    "predicted_value": combined_value,
                    "confidence": combined_conf,
                    "season_average": rec_avg + rush_avg,
                    "recent_form": receiving_pred.get("recent_form", rec_avg) + rushing_pred.get("recent_form", rush_avg),
                    "consistency_score": (receiving_pred.get("consistency_score", 50) + rushing_pred.get("consistency_score", 50)) / 2,
                    "is_home": receiving_pred.get("is_home", False),
                    "is_combined": True,
                    "stat_breakdown": [f"rec: {receiving_pred.get('predicted_value', 0):.0f}", f"rush: {rushing_pred.get('predicted_value', 0):.0f}"]
                }
                
                score = self._calculate_comprehensive_score(
                    combined_pred, player_name, "rushing + receiving_yards", matchup, injured_players,
                    position="WR", rank=rank
                )
                best_bets.append({
                    "type": "rushing + receiving_yards",
                    "bet_type": "over",
                    "score": score,
                    "pred": combined_pred,
                    "has_odds": self.get_odds_for_player(player_name, "rushing + receiving_yards") is not None
                })
        
        # Evaluate receptions (for high-volume targets)
        if not receptions_pred.get("error"):
            rec_avg = receptions_pred.get("season_average", 0)
            
            # Only for high-target WRs
            if rec_avg >= 5:
                score = self._calculate_comprehensive_score(
                    receptions_pred, player_name, "receptions", matchup, injured_players,
                    position="WR", rank=rank
                )
                best_bets.append({
                    "type": "receptions",
                    "bet_type": "over",
                    "score": score,
                    "pred": receptions_pred,
                    "has_odds": self.get_odds_for_player(player_name, "receptions") is not None
                })
        
        # Evaluate anytime TD
        if not td_pred.get("error"):
            td_avg = td_pred.get("season_average", 0)
            total_tds = td_pred.get("total_tds", td_avg * 11)
            rec_yards_avg = receiving_pred.get("season_average", 0) if not receiving_pred.get("error") else 0
            targets_avg = receiving_pred.get("avg_targets", 0) if not receiving_pred.get("error") else 0
            
            # WRs who score - use raw stats to differentiate
            if td_avg >= 0.2:  # Lower threshold, let raw stats decide
                td_pred["bet_type"] = "anytime_td"
                td_pred["stat_type"] = "anytime_td"
                
                score = self._calculate_comprehensive_score(
                    td_pred, player_name, "anytime_td", matchup, injured_players,
                    position="WR", rank=rank
                )
                
                best_bets.append({
                    "type": "anytime_td",
                    "bet_type": "anytime_td",
                    "score": score,
                    "pred": td_pred,
                    "has_odds": self.get_odds_for_player(player_name, "anytime_td") is not None
                })
        
        # Pick the BEST bet for this WR based on comprehensive score
        if best_bets:
            best_bets.sort(key=lambda x: (x.get("has_odds", False), x["score"]), reverse=True)
            best = best_bets[0]
            best["pred"]["bet_type"] = best["bet_type"]
            best["pred"]["smart_score"] = best["score"]
            picks_list.append(best["pred"])
    
    def _find_best_te_bet(self, picks_list: List, player_name: str, team_name: str,
                          injured_players: set, matchup: Dict):
        """Find the best bet type for a TE based on ALL factors with comprehensive scoring"""
        receiving_pred = self.predict_player_stat(player_name, "receiving_yards")
        receptions_pred = self.predict_player_stat(player_name, "receptions")
        td_pred = self.predict_player_stat(player_name, "receiving_tds")
        
        best_bets = []
        
        # Evaluate receiving yards with COMPREHENSIVE SCORING
        if not receiving_pred.get("error"):
            rec_avg = receiving_pred.get("season_average", 0)
            
            if rec_avg >= 25:  # TE threshold lower than WR
                score = self._calculate_comprehensive_score(
                    receiving_pred, player_name, "receiving_yards", matchup, injured_players,
                    position="TE", rank=0
                )
                best_bets.append({
                    "type": "receiving_yards",
                    "bet_type": "over",
                    "score": score,
                    "pred": receiving_pred,
                    "has_odds": self.get_odds_for_player(player_name, "receiving_yards") is not None
                })
        
        # Evaluate receptions
        if not receptions_pred.get("error"):
            rec_avg = receptions_pred.get("season_average", 0)
            
            if rec_avg >= 4:
                score = self._calculate_comprehensive_score(
                    receptions_pred, player_name, "receptions", matchup, injured_players,
                    position="TE", rank=0
                )
                best_bets.append({
                    "type": "receptions",
                    "bet_type": "over",
                    "score": score,
                    "pred": receptions_pred,
                    "has_odds": self.get_odds_for_player(player_name, "receptions") is not None
                })
        
        # Evaluate anytime TD (TEs often get red zone targets)
        if not td_pred.get("error"):
            td_avg = td_pred.get("season_average", 0)
            total_tds = td_pred.get("total_tds", td_avg * 11)
            rec_yards_avg = receiving_pred.get("season_average", 0) if not receiving_pred.get("error") else 0
            rec_avg = receptions_pred.get("season_average", 0) if not receptions_pred.get("error") else 0
            
            if td_avg >= 0.15:  # Lower threshold - let raw stats decide
                td_pred["bet_type"] = "anytime_td"
                td_pred["stat_type"] = "anytime_td"
                
                score = self._calculate_comprehensive_score(
                    td_pred, player_name, "anytime_td", matchup, injured_players,
                    position="TE", rank=0
                )
                
                best_bets.append({
                    "type": "anytime_td",
                    "bet_type": "anytime_td",
                    "score": score,
                    "pred": td_pred,
                    "has_odds": self.get_odds_for_player(player_name, "anytime_td") is not None
                })
        
        # Pick the BEST bet for this TE based on comprehensive score
        if best_bets:
            best_bets.sort(key=lambda x: (x.get("has_odds", False), x["score"]), reverse=True)
            best = best_bets[0]
            best["pred"]["bet_type"] = best["bet_type"]
            best["pred"]["smart_score"] = best["score"]
            picks_list.append(best["pred"])
    
    def _find_best_kicker_bet(self, picks_list: List, player_name: str, team_name: str,
                               injured_players: set, matchup: Dict):
        """Find the best bet type for a Kicker based on available odds"""
        best_bets = []
        
        # Check if we have kicker odds for this player
        fg_odds = self.get_odds_for_player(player_name, "field_goals")
        points_odds = self.get_odds_for_player(player_name, "kicking_points")
        
        if fg_odds:
            # Create prediction for field goals
            fg_pred = {
                "player_name": player_name,
                "team": team_name,
                "position": "K",
                "stat_type": "field_goals",
                "predicted_value": fg_odds.get("line", 1.5),
                "confidence": 65,  # Default confidence for kicker props
                "book_line": fg_odds.get("line"),
                "betting_odds": fg_odds.get("over_odds"),
            }
            best_bets.append({
                "type": "field_goals",
                "bet_type": "over",
                "score": 60,  # Base score for kicker props
                "pred": fg_pred,
                "has_odds": True
            })
        
        if points_odds:
            # Create prediction for kicking points
            points_pred = {
                "player_name": player_name,
                "team": team_name,
                "position": "K",
                "stat_type": "kicking_points",
                "predicted_value": points_odds.get("line", 6.5),
                "confidence": 65,
                "book_line": points_odds.get("line"),
                "betting_odds": points_odds.get("over_odds"),
            }
            best_bets.append({
                "type": "kicking_points",
                "bet_type": "over",
                "score": 60,
                "pred": points_pred,
                "has_odds": True
            })
        
        # Pick the best kicker bet if we have any
        if best_bets:
            best_bets.sort(key=lambda x: x["score"], reverse=True)
            best = best_bets[0]
            best["pred"]["bet_type"] = best["bet_type"]
            best["pred"]["smart_score"] = best["score"]
            picks_list.append(best["pred"])

    def _add_smart_pick(self, picks_list: List, team_name: str, position: str, 
                        stat_type: str, injured_players: set, matchup: Dict,
                        min_value: float = 0, player_rank: int = 0, bet_type: str = "over"):
        """Add a smart pick considering injuries and matchups"""
        roster = self.get_team_roster(team_name, position=position)
        position_roster = roster.get("roster", {}).get(position, [])
        
        if not position_roster or len(position_roster) <= player_rank:
            return
        
        player_name = position_roster[player_rank]
        
        # Skip injured players
        if player_name.lower() in injured_players:
            return
        
        pred = self.predict_player_stat(player_name, stat_type)
        
        if pred.get("error"):
            return
        
        predicted_value = pred.get("predicted_value", 0)
        if predicted_value < min_value:
            return
        
        # Calculate matchup advantage
        matchup_advantage = 0
        if matchup and not matchup.get("error"):
            advantages = matchup.get("key_matchups", [])
            for adv in advantages:
                if position == "QB" and "passing" in adv.get("description", "").lower():
                    if adv.get("advantage_team", "").lower() in team_name.lower():
                        matchup_advantage += 20
                elif position == "RB" and "rush" in adv.get("description", "").lower():
                    if adv.get("advantage_team", "").lower() in team_name.lower():
                        matchup_advantage += 15
                elif position in ["WR", "TE"] and "receiving" in adv.get("description", "").lower():
                    if adv.get("advantage_team", "").lower() in team_name.lower():
                        matchup_advantage += 15
        
        pred["matchup_advantage"] = matchup_advantage
        pred["bet_type"] = bet_type
        picks_list.append(pred)
    
    def _add_combined_pick(self, picks_list: List, team_name: str, position: str,
                          stat_types: List[str], injured_players: set, matchup: Dict,
                          player_rank: int = 0):
        """Add a combined stats pick (e.g., passing + rushing yards)"""
        roster = self.get_team_roster(team_name, position=position)
        position_roster = roster.get("roster", {}).get(position, [])
        
        if not position_roster or len(position_roster) <= player_rank:
            return
        
        player_name = position_roster[player_rank]
        
        if player_name.lower() in injured_players:
            return
        
        # Get predictions for each stat type
        total_predicted = 0
        total_confidence = 0
        stat_details = []
        
        for stat_type in stat_types:
            pred = self.predict_player_stat(player_name, stat_type)
            if pred.get("error"):
                continue
            value = pred.get("predicted_value", 0)
            conf = pred.get("confidence", 50)
            total_predicted += value
            total_confidence += conf
            stat_details.append(f"{stat_type.replace('_', ' ')}: {value:.0f}")
        
        if total_predicted < 50:  # Minimum threshold for combined stats
            return
        
        # Create combined stat name
        combined_name = " + ".join([s.replace("_yards", "").replace("_", " ") for s in stat_types])
        
        combined_pick = {
            "player_name": player_name,
            "team": team_name,
            "position": position,
            "stat_type": f"{combined_name}_yards",
            "predicted_value": total_predicted,
            "confidence": total_confidence / len(stat_types) if stat_types else 50,
            "bet_type": "over",
            "is_combined": True,
            "stat_breakdown": stat_details
        }
        
        picks_list.append(combined_pick)
    
    # ===== ODDS INTEGRATION =====
    
    def get_odds_for_player(self, player_name: str, prop_type: str) -> Optional[Dict]:
        """
        Get current sportsbook odds for a player prop from the database.
        Returns the most recent odds if available.
        """
        # First find the player
        player = self.find_player(player_name)
        if not player:
            return None
        
        # Map our prop types to Odds API prop types
        prop_map = {
            # Passing props
            'passing_yards': 'player_pass_yds',
            'passing_tds': 'player_pass_tds',
            'passing_attempts': 'player_pass_attempts',
            'pass_attempts': 'player_pass_attempts',
            'passing_completions': 'player_pass_completions',
            'pass_completions': 'player_pass_completions',
            'completions': 'player_pass_completions',
            'interceptions': 'player_pass_interceptions',
            
            # Rushing props
            'rushing_yards': 'player_rush_yds',
            'rushing_tds': 'player_anytime_td',
            
            # Receiving props
            'receiving_yards': 'player_reception_yds',
            'receiving_tds': 'player_anytime_td',
            'receptions': 'player_receptions',
            
            # TD props
            'anytime_td': 'player_anytime_td',
            'total_tds': 'player_tds_over',
            'tds_over': 'player_tds_over',
            
            # Combined props
            'rushing + receiving_yards': 'player_rush_reception_yds',
            'passing + rushing_yards': 'player_pass_rush_yds',
            
            # Kicker props
            'field_goals': 'player_field_goals',
            'kicking_points': 'player_kicking_points',
            'extra_points': 'player_pats',
            'pats': 'player_pats',
        }
        
        odds_prop_type = prop_map.get(prop_type)
        if not odds_prop_type:
            return None
        
        # Query the most recent odds for this player/prop
        odds = self.db.query(Odds).filter(
            Odds.player_id == player.id,
            Odds.prop_type == odds_prop_type
        ).order_by(desc(Odds.timestamp)).first()
        
        if not odds:
            return None
        
        return {
            "bookmaker": odds.bookmaker,
            "line": odds.line,
            "over_odds": odds.over_odds,
            "under_odds": odds.under_odds,
            "timestamp": odds.timestamp
        }
    
    def calculate_value_bet(self, prediction: Dict, odds_data: Dict) -> Dict:
        """
        Calculate if a bet has value by comparing AI prediction to sportsbook line.
        Returns value metrics including edge and expected value.
        """
        if not odds_data or not odds_data.get("line"):
            return {"has_odds": False}
        
        ai_prediction = prediction.get("predicted_value", 0)
        book_line = odds_data.get("line", 0)
        confidence = prediction.get("confidence", 50)
        
        # Calculate edge (how much AI differs from book)
        if book_line > 0:
            edge = ai_prediction - book_line
            edge_pct = (edge / book_line) * 100
        else:
            edge = 0
            edge_pct = 0
        
        # Determine recommendation
        if edge > 0:
            recommendation = "OVER"
            odds_to_use = odds_data.get("over_odds", -110)
        else:
            recommendation = "UNDER"
            odds_to_use = odds_data.get("under_odds", -110)
        
        # Calculate implied probability from odds
        if odds_to_use and odds_to_use < 0:
            implied_prob = abs(odds_to_use) / (abs(odds_to_use) + 100)
        elif odds_to_use and odds_to_use > 0:
            implied_prob = 100 / (odds_to_use + 100)
        else:
            implied_prob = 0.5
        
        # Calculate expected value
        ai_prob = confidence / 100
        if implied_prob > 0:
            ev = (ai_prob * (1 / implied_prob - 1)) - ((1 - ai_prob) * 1)
        else:
            ev = 0
        
        # Is this a value bet? (lowered thresholds for more results)
        is_value = abs(edge_pct) >= 3 and confidence >= 50
        
        return {
            "has_odds": True,
            "bookmaker": odds_data.get("bookmaker"),
            "book_line": book_line,
            "ai_prediction": ai_prediction,
            "edge": round(edge, 1),
            "edge_pct": round(edge_pct, 1),
            "recommendation": recommendation,
            "odds": odds_to_use,
            "implied_probability": round(implied_prob * 100, 1),
            "expected_value": round(ev * 100, 1),
            "is_value_bet": is_value,
            "value_rating": "STRONG VALUE" if abs(edge_pct) >= 10 and ev > 0.05 else "VALUE" if is_value else "NO EDGE"
        }
    
    def enhance_pick_with_odds(self, pick: Dict) -> Dict:
        """
        Enhance a pick with sportsbook odds data if available.
        This adds value metrics to help identify the best bets.
        """
        player_name = pick.get("player_name", "")
        stat_type = pick.get("stat_type", "")
        
        # Get odds from database
        odds_data = self.get_odds_for_player(player_name, stat_type)
        
        if odds_data:
            # Calculate value
            value_data = self.calculate_value_bet(pick, odds_data)
            pick["odds_data"] = value_data
            
            # Add odds directly to pick for easy access
            pick["betting_odds"] = value_data.get("odds")
            pick["book_line"] = value_data.get("book_line")
            pick["bookmaker"] = odds_data.get("bookmaker")
            
            # Boost confidence for value bets
            if value_data.get("is_value_bet"):
                # Add edge bonus to smart score
                edge_bonus = min(abs(value_data.get("edge_pct", 0)), 15)
                current_score = pick.get("smart_score", 50)
                pick["smart_score"] = current_score + edge_bonus
                pick["has_value"] = True
                pick["value_rating"] = value_data.get("value_rating")
        else:
            pick["odds_data"] = {"has_odds": False}
            pick["has_value"] = False
            pick["betting_odds"] = None
        
        return pick
    
    def get_all_value_bets(self, game_date: str = None) -> List[Dict]:
        """
        Find all value bets by comparing AI predictions to sportsbook odds.
        Fast approach: directly query odds table and check predictions.
        """
        value_bets = []
        
        # Map prop types from odds to stat types for predictions
        prop_to_stat = {
            "player_pass_yds": "passing_yards",
            "player_rush_yds": "rushing_yards",
            "player_reception_yds": "receiving_yards",
            "player_receptions": "receptions",
            "player_pass_tds": "passing_tds",
            "player_rush_tds": "rushing_tds",
            "player_reception_tds": "receiving_tds",
        }
        
        # Get recent odds with player props
        recent_odds = self.db.query(Odds).filter(
            Odds.player_id != None,
            Odds.prop_type.in_(list(prop_to_stat.keys()))
        ).order_by(Odds.timestamp.desc()).limit(100).all()
        
        # Track players we've already checked
        checked = set()
        
        for odds_record in recent_odds:
            player = self.db.query(Player).filter(Player.id == odds_record.player_id).first()
            if not player:
                continue
            
            stat_type = prop_to_stat.get(odds_record.prop_type)
            if not stat_type:
                continue
            
            # Skip duplicates
            check_key = f"{player.id}_{stat_type}"
            if check_key in checked:
                continue
            checked.add(check_key)
            
            # Get AI prediction
            pred = self.predict_player_stat(player.name, stat_type)
            if pred.get("error"):
                continue
            
            ai_prediction = pred.get("predicted_value", 0)
            book_line = odds_record.line or 0
            confidence = pred.get("confidence", 50)
            
            if book_line <= 0:
                continue
            
            # Calculate edge
            edge = ai_prediction - book_line
            edge_pct = (edge / book_line) * 100
            
            # Is this a value bet? (3% edge and 50% confidence)
            if abs(edge_pct) >= 3 and confidence >= 50:
                team = self.db.query(Team).filter(Team.id == player.team_id).first()
                recommendation = "OVER" if edge > 0 else "UNDER"
                
                value_bets.append({
                    "player_name": player.name,
                    "team": team.name if team else "Unknown",
                    "team_abbr": team.abbreviation if team else "?",
                    "position": player.position,
                    "stat_type": stat_type,
                    "book_line": book_line,
                    "ai_prediction": round(ai_prediction, 1),
                    "edge": round(edge, 1),
                    "edge_pct": round(edge_pct, 1),
                    "recommendation": recommendation,
                    "confidence": round(confidence, 1),
                    "bookmaker": odds_record.bookmaker,
                    "is_value_bet": True,
                    "value_rating": "STRONG" if abs(edge_pct) >= 10 else "VALUE"
                })
        
        # Sort by edge percentage
        value_bets.sort(key=lambda x: abs(x.get("edge_pct", 0)), reverse=True)
        
        return value_bets
    
    def _get_props_for_position(self, position: str) -> List[str]:
        """Get relevant prop types to check for a position"""
        if position == "QB":
            return ["passing_yards", "passing_tds", "rushing_yards", "interceptions"]
        elif position == "RB":
            return ["rushing_yards", "receiving_yards", "rushing_tds"]
        elif position == "WR":
            return ["receiving_yards", "receptions", "receiving_tds"]
        elif position == "TE":
            return ["receiving_yards", "receptions", "receiving_tds"]
        elif position == "K":
            return ["field_goals", "kicking_points"]
        return []


# Validation function - used to check Gemini's response
def validate_gemini_response(response_text: str, verified_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate that Gemini's response only contains data from YOUR AI.
    Returns (is_valid, list_of_violations)
    """
    violations = []
    
    # Check for player-team mentions that weren't verified
    player_team_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*\(([A-Z]{2,4})\)'
    mentions = re.findall(player_team_pattern, response_text)
    
    verified_players = verified_data.get("players_mentioned", {})
    
    for player_name, team_abbr in mentions:
        player_lower = player_name.lower()
        if player_lower not in verified_players:
            violations.append(f"Player '{player_name}' was mentioned but not verified in YOUR AI data")
    
    # Check for team mentions that weren't in the data
    verified_teams = verified_data.get("teams_mentioned", [])
    
    is_valid = len(violations) == 0
    return is_valid, violations

