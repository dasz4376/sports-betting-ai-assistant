"""
Smart Picks Engine - Advanced Pick Selection for Better Parlays

This module provides intelligent pick selection based on:
1. Edge Analysis - How far is our prediction from typical lines?
2. Trend Analysis - Is the player trending up or down?
3. Matchup Grades - How favorable is this matchup?
4. Correlation Awareness - Don't pick conflicting props
5. Value Scoring - Balance probability vs potential return
6. Historical Accuracy - How accurate have we been on this player/prop type?
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from models import Player, Game, PlayerStats, StatsFeatures, Team, Injury
from datetime import datetime, timedelta
import numpy as np


class SmartPicksEngine:
    """
    Advanced pick selection engine that analyzes multiple factors
    to find the BEST betting opportunities
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_player_trend(self, player_id: int, stat_type: str, num_games: int = 5) -> Dict:
        """
        Analyze if a player is trending UP or DOWN
        
        Returns:
            - trend_direction: 'up', 'down', or 'stable'
            - trend_strength: 0-100 (how strong the trend is)
            - recent_avg: average of last N games
            - season_avg: full season average
            - variance: how consistent the player is
        """
        # Get player's recent game stats
        player = self.db.query(Player).filter_by(id=player_id).first()
        if not player:
            return {"error": "Player not found"}
        
        # Get recent stats
        recent_stats = self.db.query(PlayerStats).join(
            Game, PlayerStats.game_id == Game.id
        ).filter(
            PlayerStats.player_id == player_id,
            Game.status == "STATUS_FINAL"
        ).order_by(desc(Game.game_date)).limit(num_games).all()
        
        if len(recent_stats) < 3:
            return {
                "trend_direction": "unknown",
                "trend_strength": 0,
                "reason": "Not enough recent games"
            }
        
        # Map stat type to attribute
        stat_attr_map = {
            'passing_yards': 'passing_yards',
            'rushing_yards': 'rushing_yards',
            'receiving_yards': 'receiving_yards',
            'receptions': 'receptions',
            'passing_tds': 'passing_touchdowns',
            'rushing_tds': 'rushing_touchdowns',
            'receiving_tds': 'receiving_touchdowns',
        }
        
        attr = stat_attr_map.get(stat_type)
        if not attr:
            return {"trend_direction": "unknown", "trend_strength": 0}
        
        # Get stat values (most recent first)
        values = [getattr(s, attr, 0) or 0 for s in recent_stats]
        
        if not values or all(v == 0 for v in values):
            return {"trend_direction": "unknown", "trend_strength": 0}
        
        # Calculate trend
        # Recent average (first half) vs older average (second half)
        half = len(values) // 2
        recent_half = values[:half] if half > 0 else values[:1]
        older_half = values[half:] if half > 0 else values[1:]
        
        recent_avg = np.mean(recent_half)
        older_avg = np.mean(older_half) if older_half else recent_avg
        season_avg = np.mean(values)
        
        # Calculate trend direction and strength
        if older_avg > 0:
            trend_pct = ((recent_avg - older_avg) / older_avg) * 100
        else:
            trend_pct = 0
        
        if trend_pct > 10:
            trend_direction = "up"
            trend_strength = min(100, abs(trend_pct))
        elif trend_pct < -10:
            trend_direction = "down"
            trend_strength = min(100, abs(trend_pct))
        else:
            trend_direction = "stable"
            trend_strength = 0
        
        # Calculate variance (consistency)
        variance = np.std(values) if len(values) > 1 else 0
        consistency = max(0, 100 - (variance / max(season_avg, 1) * 100))
        
        return {
            "trend_direction": trend_direction,
            "trend_strength": round(trend_strength, 1),
            "recent_avg": round(recent_avg, 1),
            "older_avg": round(older_avg, 1),
            "season_avg": round(season_avg, 1),
            "variance": round(variance, 1),
            "consistency": round(consistency, 1),
            "games_analyzed": len(values),
            "last_game_value": values[0] if values else 0
        }
    
    def calculate_matchup_grade(
        self, 
        player_id: int, 
        opponent_team_id: int, 
        stat_type: str
    ) -> Dict:
        """
        Grade how favorable this matchup is (A+ to F)
        
        Considers:
        - Opponent's defensive ranking for this stat type
        - Points allowed to position
        - Recent defensive performance
        """
        player = self.db.query(Player).filter_by(id=player_id).first()
        if not player:
            return {"grade": "N/A", "reason": "Player not found"}
        
        # Get opponent's defensive stats
        defensive_positions = ['CB', 'S', 'DB', 'LB', 'DE', 'DT', 'OLB', 'ILB', 'MLB']
        
        defensive_players = self.db.query(Player).filter(
            Player.team_id == opponent_team_id,
            Player.position.in_(defensive_positions)
        ).all()
        
        if not defensive_players:
            return {"grade": "C", "score": 50, "reason": "No defensive data"}
        
        # Get their stats
        def_stats = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_([p.id for p in defensive_players]),
            StatsFeatures.season == 2025
        ).all()
        
        if not def_stats:
            return {"grade": "C", "score": 50, "reason": "No defensive stats"}
        
        # Calculate defensive strength for this stat type
        if stat_type in ['passing_yards', 'passing_tds']:
            # QB facing this defense - look at pass rush + secondary
            sacks = sum(s.avg_sacks_def or 0 for s in def_stats)
            ints = sum(s.avg_interceptions_def or 0 for s in def_stats)
            pass_def = sum(s.avg_pass_deflections or 0 for s in def_stats)
            
            # Lower is better for offense
            def_strength = sacks * 10 + ints * 20 + pass_def * 3
            
        elif stat_type in ['rushing_yards', 'rushing_tds']:
            # RB facing this defense - look at run defense
            tackles = sum(s.avg_tackles or 0 for s in def_stats)
            tfls = sum(s.avg_tackles_for_loss or 0 for s in def_stats)
            
            def_strength = tackles + tfls * 5
            
        elif stat_type in ['receiving_yards', 'receiving_tds', 'receptions']:
            # WR/TE facing this defense - look at secondary
            ints = sum(s.avg_interceptions_def or 0 for s in def_stats)
            pass_def = sum(s.avg_pass_deflections or 0 for s in def_stats)
            
            def_strength = ints * 15 + pass_def * 3
        else:
            def_strength = 50
        
        # Normalize to 0-100 scale (inverted - lower def_strength = better matchup)
        # Typical range is 0-200, so divide by 2
        matchup_score = max(0, min(100, 100 - def_strength / 2))
        
        # Convert to letter grade
        if matchup_score >= 85:
            grade = "A+"
        elif matchup_score >= 75:
            grade = "A"
        elif matchup_score >= 65:
            grade = "B+"
        elif matchup_score >= 55:
            grade = "B"
        elif matchup_score >= 45:
            grade = "C+"
        elif matchup_score >= 35:
            grade = "C"
        elif matchup_score >= 25:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "grade": grade,
            "score": round(matchup_score, 1),
            "defensive_strength": round(def_strength, 1),
            "recommendation": "favorable" if matchup_score >= 55 else "unfavorable" if matchup_score < 40 else "neutral"
        }
    
    def calculate_edge(
        self, 
        predicted_value: float, 
        typical_line: float = None,
        stat_type: str = None
    ) -> Dict:
        """
        Calculate the "edge" - how much better/worse than typical
        
        If no typical_line provided, use historical averages for the stat type
        """
        # Typical betting lines by stat type (rough estimates)
        typical_lines = {
            'passing_yards': 225,
            'passing_tds': 1.5,
            'rushing_yards': 65,
            'rushing_tds': 0.5,
            'receiving_yards': 55,
            'receiving_tds': 0.4,
            'receptions': 4.5,
        }
        
        if typical_line is None and stat_type:
            typical_line = typical_lines.get(stat_type, predicted_value)
        elif typical_line is None:
            return {"edge": 0, "edge_pct": 0}
        
        edge = predicted_value - typical_line
        edge_pct = (edge / typical_line * 100) if typical_line > 0 else 0
        
        return {
            "edge": round(edge, 1),
            "edge_pct": round(edge_pct, 1),
            "typical_line": typical_line,
            "recommendation": "strong_over" if edge_pct > 15 else "over" if edge_pct > 5 else "under" if edge_pct < -5 else "pass"
        }
    
    def calculate_smart_score(
        self,
        prediction: Dict,
        trend: Dict,
        matchup: Dict,
        edge: Dict
    ) -> float:
        """
        Calculate a comprehensive "smart score" for a pick
        
        Weighs all factors to produce a single score (0-100)
        Higher = better pick
        """
        score = 0
        
        # 1. Base confidence from model (30% weight)
        confidence = prediction.get('confidence', 50)
        score += (confidence / 100) * 30
        
        # 2. Trend bonus (20% weight)
        if trend.get('trend_direction') == 'up':
            score += (trend.get('trend_strength', 0) / 100) * 20
        elif trend.get('trend_direction') == 'down':
            score -= (trend.get('trend_strength', 0) / 100) * 10
        else:
            score += 10  # Stable is okay
        
        # 3. Matchup grade (25% weight)
        matchup_score = matchup.get('score', 50)
        score += (matchup_score / 100) * 25
        
        # 4. Consistency bonus (15% weight)
        consistency = trend.get('consistency', 50)
        score += (consistency / 100) * 15
        
        # 5. Edge bonus (10% weight)
        edge_pct = abs(edge.get('edge_pct', 0))
        score += min(10, edge_pct / 2)
        
        return round(score, 1)
    
    def get_best_picks(
        self,
        predictions: List[Dict],
        num_picks: int = 10,
        min_smart_score: float = 50
    ) -> List[Dict]:
        """
        From a list of predictions, select the BEST picks
        
        Analyzes each prediction and returns top picks sorted by smart score
        """
        analyzed_picks = []
        
        for pred in predictions:
            player_id = pred.get('player_id')
            player_name = pred.get('player_name')
            stat_type = pred.get('stat_type')
            predicted_value = pred.get('predicted_value', 0)
            
            if not player_id or not stat_type:
                continue
            
            # Get player's team for matchup analysis
            player = self.db.query(Player).filter_by(id=player_id).first()
            if not player:
                continue
            
            # Get game info for opponent
            game_id = pred.get('game_id')
            game = self.db.query(Game).filter_by(id=game_id).first() if game_id else None
            
            # Determine opponent
            if game:
                if player.team_id == game.home_team_id:
                    opponent_id = game.away_team_id
                else:
                    opponent_id = game.home_team_id
            else:
                opponent_id = None
            
            # Analyze trend
            trend = self.analyze_player_trend(player_id, stat_type)
            
            # Analyze matchup
            matchup = self.calculate_matchup_grade(player_id, opponent_id, stat_type) if opponent_id else {"grade": "C", "score": 50}
            
            # Calculate edge
            edge = self.calculate_edge(predicted_value, stat_type=stat_type)
            
            # Calculate smart score
            smart_score = self.calculate_smart_score(pred, trend, matchup, edge)
            
            # Build enhanced prediction
            enhanced_pred = {
                **pred,
                "trend": trend,
                "matchup_grade": matchup,
                "edge": edge,
                "smart_score": smart_score,
                "pick_quality": "excellent" if smart_score >= 70 else "good" if smart_score >= 55 else "fair" if smart_score >= 40 else "poor"
            }
            
            # Only include if meets minimum score
            if smart_score >= min_smart_score:
                analyzed_picks.append(enhanced_pred)
        
        # Sort by smart score (descending)
        analyzed_picks.sort(key=lambda x: x['smart_score'], reverse=True)
        
        return analyzed_picks[:num_picks]
    
    def check_correlation(self, picks: List[Dict]) -> List[Dict]:
        """
        Check for correlated picks that might conflict
        
        Example: If we pick QB passing yards OVER and WR receiving yards UNDER,
        these are negatively correlated and one might hurt the other.
        
        Returns picks with correlation warnings
        """
        warnings = []
        
        for i, pick1 in enumerate(picks):
            for pick2 in picks[i+1:]:
                # Same game, check for conflicts
                if pick1.get('game_id') == pick2.get('game_id'):
                    team1 = pick1.get('team')
                    team2 = pick2.get('team')
                    stat1 = pick1.get('stat_type')
                    stat2 = pick2.get('stat_type')
                    
                    # Positive correlation: Same team passing/receiving
                    if team1 == team2:
                        if ('passing' in stat1 and 'receiving' in stat2) or ('receiving' in stat1 and 'passing' in stat2):
                            warnings.append({
                                "pick1": pick1.get('player_name'),
                                "pick2": pick2.get('player_name'),
                                "type": "positive_correlation",
                                "note": f"Both depend on {team1}'s passing game - if one hits, other likely does too"
                            })
        
        return warnings
    
    def generate_parlay_recommendations(
        self,
        predictions: List[Dict],
        num_legs: int = 5,
        strategy: str = "balanced"
    ) -> Dict:
        """
        Generate smart parlay recommendations
        
        Strategies:
        - "safe": High confidence, lower variance picks
        - "balanced": Mix of safety and upside
        - "aggressive": Higher risk, higher potential reward
        """
        # Get best picks
        if strategy == "safe":
            min_score = 60
            picks = self.get_best_picks(predictions, num_legs * 2, min_score)
            # Filter for high consistency
            picks = [p for p in picks if p.get('trend', {}).get('consistency', 0) >= 60]
        elif strategy == "aggressive":
            min_score = 40
            picks = self.get_best_picks(predictions, num_legs * 2, min_score)
            # Prefer trending up players
            picks = sorted(picks, key=lambda x: x.get('trend', {}).get('trend_strength', 0) if x.get('trend', {}).get('trend_direction') == 'up' else 0, reverse=True)
        else:  # balanced
            min_score = 50
            picks = self.get_best_picks(predictions, num_legs * 2, min_score)
        
        # Take top N
        selected_picks = picks[:num_legs]
        
        # Check correlations
        correlations = self.check_correlation(selected_picks)
        
        # Calculate overall parlay quality
        if selected_picks:
            avg_smart_score = sum(p['smart_score'] for p in selected_picks) / len(selected_picks)
            avg_confidence = sum(p.get('confidence', 50) for p in selected_picks) / len(selected_picks)
        else:
            avg_smart_score = 0
            avg_confidence = 0
        
        return {
            "strategy": strategy,
            "picks": selected_picks,
            "num_legs": len(selected_picks),
            "correlations": correlations,
            "parlay_quality": {
                "average_smart_score": round(avg_smart_score, 1),
                "average_confidence": round(avg_confidence, 1),
                "rating": "excellent" if avg_smart_score >= 65 else "good" if avg_smart_score >= 55 else "fair"
            },
            "recommendation": f"This {strategy} {len(selected_picks)}-leg parlay has an average smart score of {avg_smart_score:.1f}/100"
        }

