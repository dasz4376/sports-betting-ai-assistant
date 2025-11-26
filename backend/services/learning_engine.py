"""
Learning Engine - Makes the AI truly self-learning

This service:
1. Tracks accuracy by bet type (combined vs single, anytime TD, etc.)
2. Tracks player-specific hit rates
3. Provides confidence adjustments based on historical performance

The AI learns patterns like:
- "Combined stats hit at 72%" → boost combined bets
- "Derrick Henry hits rushing overs 78% of the time" → boost his overs
- "My passing yard predictions are 15% off on average" → adjust accordingly
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import BetTypeAccuracy, PlayerHitRate, Prediction, Player, PlayerStats
from typing import Dict, Optional
from datetime import datetime


class LearningEngine:
    """Self-learning engine that improves predictions based on historical accuracy"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_confidence_adjustment(self, player_id: int, prop_type: str, 
                                   bet_category: str = "single", 
                                   position: str = None) -> float:
        """
        Get the confidence adjustment for a specific prediction.
        
        Returns a value to ADD to confidence score:
        - Positive: This bet type/player historically performs well
        - Negative: This bet type/player historically underperforms
        - Zero: Not enough data or neutral performance
        """
        total_adjustment = 0.0
        
        # 1. Get bet type accuracy adjustment
        bet_type_adj = self._get_bet_type_adjustment(bet_category, prop_type, position)
        total_adjustment += bet_type_adj
        
        # 2. Get player-specific adjustment
        player_adj = self._get_player_adjustment(player_id, prop_type)
        total_adjustment += player_adj
        
        # Cap the adjustment to prevent extreme swings
        return max(-20, min(20, total_adjustment))
    
    def _get_bet_type_adjustment(self, bet_category: str, prop_type: str, 
                                  position: str = None) -> float:
        """Get adjustment based on how well this bet type performs historically"""
        # Try specific match first (category + prop + position)
        query = self.db.query(BetTypeAccuracy).filter(
            BetTypeAccuracy.bet_category == bet_category,
            BetTypeAccuracy.season == 2025
        )
        
        if prop_type:
            query = query.filter(BetTypeAccuracy.prop_type == prop_type)
        if position:
            query = query.filter(BetTypeAccuracy.position == position)
        
        record = query.first()
        
        if record and record.total_predictions >= 10:  # Need enough data
            return record.confidence_adjustment
        
        # Fall back to just bet category
        record = self.db.query(BetTypeAccuracy).filter(
            BetTypeAccuracy.bet_category == bet_category,
            BetTypeAccuracy.prop_type.is_(None),
            BetTypeAccuracy.position.is_(None),
            BetTypeAccuracy.season == 2025
        ).first()
        
        if record and record.total_predictions >= 10:
            return record.confidence_adjustment
        
        return 0.0
    
    def _get_player_adjustment(self, player_id: int, prop_type: str) -> float:
        """Get adjustment based on this player's historical hit rate"""
        record = self.db.query(PlayerHitRate).filter(
            PlayerHitRate.player_id == player_id,
            PlayerHitRate.prop_type == prop_type,
            PlayerHitRate.season == 2025
        ).first()
        
        if record and record.total_games >= 3:  # Need at least 3 games
            return record.confidence_adjustment
        
        return 0.0
    
    def update_after_game(self, game_id: int):
        """
        Update all learning tables after a game completes.
        This is where the AI learns from its predictions.
        """
        print(f"\n📚 LEARNING ENGINE: Updating from game {game_id}")
        
        # Get all predictions for this game that have actual values
        predictions = self.db.query(Prediction).filter(
            Prediction.game_id == game_id,
            Prediction.actual_value.isnot(None)
        ).all()
        
        if not predictions:
            print("   No predictions to learn from")
            return
        
        print(f"   Learning from {len(predictions)} predictions...")
        
        for pred in predictions:
            # Update bet type accuracy
            self._update_bet_type_accuracy(pred)
            
            # Update player hit rate
            self._update_player_hit_rate(pred)
        
        # Recalculate all confidence adjustments
        self._recalculate_adjustments()
        
        self.db.commit()
        print("   ✓ Learning complete!")
    
    def _update_bet_type_accuracy(self, pred: Prediction):
        """Update accuracy stats for this bet type"""
        bet_category = pred.bet_category or "single"
        prop_type = pred.prop_type or pred.stat_type
        
        # Get player position
        player = self.db.query(Player).filter_by(id=pred.player_id).first()
        position = player.position if player else None
        
        # Find or create record
        record = self.db.query(BetTypeAccuracy).filter(
            BetTypeAccuracy.bet_category == bet_category,
            BetTypeAccuracy.prop_type == prop_type,
            BetTypeAccuracy.position == position,
            BetTypeAccuracy.season == 2025
        ).first()
        
        if not record:
            record = BetTypeAccuracy(
                bet_category=bet_category,
                prop_type=prop_type,
                position=position,
                season=2025
            )
            self.db.add(record)
        
        # Update stats
        record.total_predictions += 1
        if pred.was_accurate:
            record.accurate_predictions += 1
        if pred.hit_over:
            record.total_hit_over += 1
        
        # Recalculate percentages
        record.accuracy_pct = (record.accurate_predictions / record.total_predictions) * 100
        record.hit_rate = (record.total_hit_over / record.total_predictions) * 100
        
        # Update average error
        if pred.prediction_error:
            current_total_error = record.avg_error * (record.total_predictions - 1)
            record.avg_error = (current_total_error + pred.prediction_error) / record.total_predictions
    
    def _update_player_hit_rate(self, pred: Prediction):
        """Update hit rate stats for this player/prop combo"""
        prop_type = pred.prop_type or pred.stat_type
        
        # Find or create record
        record = self.db.query(PlayerHitRate).filter(
            PlayerHitRate.player_id == pred.player_id,
            PlayerHitRate.prop_type == prop_type,
            PlayerHitRate.season == 2025
        ).first()
        
        if not record:
            record = PlayerHitRate(
                player_id=pred.player_id,
                prop_type=prop_type,
                season=2025
            )
            self.db.add(record)
        
        # Update stats
        record.total_games += 1
        if pred.hit_over:
            record.times_hit_over += 1
        
        record.hit_rate = (record.times_hit_over / record.total_games) * 100
        
        # Update variance tracking
        if pred.prediction_error:
            current_total_var = record.avg_variance * (record.total_games - 1)
            record.avg_variance = (current_total_var + pred.prediction_error) / record.total_games
    
    def _recalculate_adjustments(self):
        """
        Recalculate confidence adjustments based on historical accuracy.
        
        Logic:
        - 70%+ accuracy → +10 to +15 confidence boost
        - 60-70% accuracy → +5 confidence boost  
        - 50-60% accuracy → no adjustment
        - 40-50% accuracy → -5 confidence penalty
        - <40% accuracy → -10 to -15 confidence penalty
        """
        # Update bet type adjustments
        bet_types = self.db.query(BetTypeAccuracy).filter(
            BetTypeAccuracy.total_predictions >= 5,  # Need some data
            BetTypeAccuracy.season == 2025
        ).all()
        
        for bt in bet_types:
            bt.confidence_adjustment = self._calculate_adjustment(bt.accuracy_pct, bt.total_predictions)
        
        # Update player adjustments
        player_rates = self.db.query(PlayerHitRate).filter(
            PlayerHitRate.total_games >= 3,  # Need some data
            PlayerHitRate.season == 2025
        ).all()
        
        for pr in player_rates:
            pr.confidence_adjustment = self._calculate_adjustment(pr.hit_rate, pr.total_games)
    
    def _calculate_adjustment(self, accuracy: float, sample_size: int) -> float:
        """
        Calculate confidence adjustment based on accuracy.
        
        Sample size matters - more data = more confident in adjustment.
        """
        # Base adjustment from accuracy
        if accuracy >= 75:
            base = 15
        elif accuracy >= 70:
            base = 10
        elif accuracy >= 65:
            base = 7
        elif accuracy >= 60:
            base = 4
        elif accuracy >= 55:
            base = 0
        elif accuracy >= 50:
            base = -3
        elif accuracy >= 45:
            base = -6
        elif accuracy >= 40:
            base = -10
        else:
            base = -15
        
        # Scale by sample size confidence (more samples = trust adjustment more)
        if sample_size >= 50:
            confidence_multiplier = 1.0
        elif sample_size >= 30:
            confidence_multiplier = 0.8
        elif sample_size >= 15:
            confidence_multiplier = 0.6
        elif sample_size >= 10:
            confidence_multiplier = 0.4
        else:
            confidence_multiplier = 0.2
        
        return round(base * confidence_multiplier, 1)
    
    def get_learning_report(self) -> Dict:
        """Get a report of what the AI has learned"""
        report = {
            "bet_type_insights": [],
            "player_insights": [],
            "recommendations": []
        }
        
        # Bet type insights
        bet_types = self.db.query(BetTypeAccuracy).filter(
            BetTypeAccuracy.total_predictions >= 10,
            BetTypeAccuracy.season == 2025
        ).order_by(BetTypeAccuracy.accuracy_pct.desc()).all()
        
        for bt in bet_types:
            report["bet_type_insights"].append({
                "category": bt.bet_category,
                "prop_type": bt.prop_type,
                "position": bt.position,
                "accuracy": round(bt.accuracy_pct, 1),
                "hit_rate": round(bt.hit_rate, 1),
                "sample_size": bt.total_predictions,
                "adjustment": bt.confidence_adjustment
            })
        
        # Top performing players
        top_players = self.db.query(PlayerHitRate).filter(
            PlayerHitRate.total_games >= 5,
            PlayerHitRate.season == 2025
        ).order_by(PlayerHitRate.hit_rate.desc()).limit(20).all()
        
        for pr in top_players:
            player = self.db.query(Player).filter_by(id=pr.player_id).first()
            if player:
                report["player_insights"].append({
                    "player": player.name,
                    "position": player.position,
                    "prop_type": pr.prop_type,
                    "hit_rate": round(pr.hit_rate, 1),
                    "games": pr.total_games,
                    "adjustment": pr.confidence_adjustment
                })
        
        # Generate recommendations
        if bet_types:
            best = max(bet_types, key=lambda x: x.accuracy_pct)
            worst = min(bet_types, key=lambda x: x.accuracy_pct)
            
            report["recommendations"].append(
                f"BEST: {best.bet_category} {best.prop_type or ''} ({best.accuracy_pct:.0f}% accuracy)"
            )
            report["recommendations"].append(
                f"WORST: {worst.bet_category} {worst.prop_type or ''} ({worst.accuracy_pct:.0f}% accuracy)"
            )
        
        return report
    
    def print_learning_status(self):
        """Print what the AI has learned so far"""
        print("\n" + "="*70)
        print("🧠 AI LEARNING STATUS")
        print("="*70)
        
        # Bet type stats
        bet_types = self.db.query(BetTypeAccuracy).filter(
            BetTypeAccuracy.total_predictions >= 5,
            BetTypeAccuracy.season == 2025
        ).order_by(BetTypeAccuracy.accuracy_pct.desc()).all()
        
        if bet_types:
            print("\n📊 BET TYPE ACCURACY (what the AI has learned):")
            print("-"*70)
            for bt in bet_types:
                adj_str = f"+{bt.confidence_adjustment}" if bt.confidence_adjustment >= 0 else str(bt.confidence_adjustment)
                print(f"  {bt.bet_category:10} | {bt.prop_type or 'all':25} | "
                      f"{bt.accuracy_pct:5.1f}% | adj: {adj_str:5}")
        else:
            print("\n📊 No bet type data yet - AI will learn after games complete")
        
        # Player stats
        player_count = self.db.query(PlayerHitRate).filter(
            PlayerHitRate.total_games >= 3,
            PlayerHitRate.season == 2025
        ).count()
        
        print(f"\n👤 Tracking {player_count} player/prop combinations")
        
        # Top reliable players
        reliable = self.db.query(PlayerHitRate).filter(
            PlayerHitRate.total_games >= 5,
            PlayerHitRate.hit_rate >= 65,
            PlayerHitRate.season == 2025
        ).order_by(PlayerHitRate.hit_rate.desc()).limit(5).all()
        
        if reliable:
            print("\n🔥 MOST RELIABLE PLAYERS (AI will boost their confidence):")
            for pr in reliable:
                player = self.db.query(Player).filter_by(id=pr.player_id).first()
                if player:
                    print(f"  {player.name:25} | {pr.prop_type:20} | {pr.hit_rate:.0f}% hit rate")
        
        print("="*70 + "\n")

