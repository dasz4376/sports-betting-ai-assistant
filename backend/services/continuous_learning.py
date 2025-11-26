"""
Continuous Learning Loop - Post-Game Analysis
Compares predictions to actual results and triggers retraining when needed
"""

from sqlalchemy.orm import Session
from models import Prediction, PlayerStats, Game, Player
from services.predictor import BettingAI
from services.learning_engine import LearningEngine
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List

class ContinuousLearning:
    """Analyzes prediction accuracy and triggers retraining when needed"""
    
    def __init__(self, db: Session):
        self.db = db
        self.betting_ai = BettingAI(db)
        self.learning_engine = LearningEngine(db)
    
    def analyze_completed_games(self, weeks_back: int = 1) -> Dict:
        """
        Analyze all completed games from the last N weeks
        Compare predictions to actual results
        """
        print(f"\n{'='*80}")
        print(f"CONTINUOUS LEARNING: Analyzing Last {weeks_back} Week(s)")
        print(f"{'='*80}\n")
        
        # Get completed games from last N weeks
        cutoff_date = datetime.utcnow() - timedelta(weeks=weeks_back)
        completed_games = self.db.query(Game).filter(
            Game.status == "STATUS_FINAL",
            Game.game_date >= cutoff_date,
            Game.season == 2025
        ).all()
        
        if not completed_games:
            print("No completed games found in the specified time range.")
            return {"games_analyzed": 0, "predictions_updated": 0}
        
        print(f"Found {len(completed_games)} completed games to analyze...\n")
        
        predictions_updated = 0
        total_error = 0
        prop_accuracy = {}
        
        for game in completed_games:
            print(f"Analyzing: Week {game.week} - {game.away_team_name} @ {game.home_team_name}")
            
            # Get all player stats from this game
            game_stats = self.db.query(PlayerStats).filter_by(
                game_id=game.id,
                season=2025
            ).all()
            
            for stat in game_stats:
                # Find any predictions made for this player/game
                predictions = self.db.query(Prediction).filter_by(
                    player_id=stat.player_id,
                    game_id=game.id,
                    season=2025
                ).all()
                
                for pred in predictions:
                    # Map prop type to actual stat field
                    actual_value = self._get_actual_value(stat, pred.prop_type)
                    
                    if actual_value is None:
                        continue  # Skip if stat not available
                    
                    # Update prediction with actual result
                    pred.actual_value = actual_value
                    pred.prediction_error = abs(pred.predicted_value - actual_value)
                    
                    # Calculate if prediction was accurate (within 20% for continuous, exact for binary)
                    if pred.prop_type in ['passing_tds', 'rushing_tds', 'receiving_tds']:
                        # Binary/count - must be within 1
                        pred.was_accurate = abs(pred.predicted_value - actual_value) <= 1
                    else:
                        # Continuous - within 20%
                        if actual_value > 0:
                            error_pct = abs(pred.predicted_value - actual_value) / actual_value
                            pred.was_accurate = error_pct <= 0.20
                        else:
                            pred.was_accurate = pred.predicted_value <= 10  # Close to zero
                    
                    # Track if the over hit (for over/under learning)
                    if pred.predicted_value and actual_value:
                        # For overs, we typically bet on the predicted value
                        # If actual > 90% of prediction, consider it a "hit"
                        pred.hit_over = actual_value >= (pred.predicted_value * 0.9)
                    
                    # Track by prop type
                    prop_key = pred.prop_type or pred.stat_type
                    if prop_key not in prop_accuracy:
                        prop_accuracy[prop_key] = {"correct": 0, "total": 0, "total_error": 0}
                    
                    prop_accuracy[prop_key]["total"] += 1
                    prop_accuracy[prop_key]["total_error"] += pred.prediction_error
                    if pred.was_accurate:
                        prop_accuracy[prop_key]["correct"] += 1
                    
                    predictions_updated += 1
                    total_error += pred.prediction_error
        
        # Commit all updates
        self.db.commit()
        
        # Update learning engine for each game
        print(f"\n🧠 Updating AI learning from completed games...")
        for game in completed_games:
            self.learning_engine.update_after_game(game.id)
        
        # Print what the AI learned
        self.learning_engine.print_learning_status()
        
        # Print summary
        print(f"\n{'='*80}")
        print("ANALYSIS SUMMARY")
        print(f"{'='*80}")
        print(f"Games Analyzed: {len(completed_games)}")
        print(f"Predictions Updated: {predictions_updated}")
        
        if predictions_updated > 0:
            avg_error = total_error / predictions_updated
            print(f"Average Prediction Error: {avg_error:.2f}")
            
            print(f"\nAccuracy by Prop Type:")
            print(f"{'-'*80}")
            
            retrain_needed = []
            
            for prop_type, stats in sorted(prop_accuracy.items()):
                accuracy_pct = (stats["correct"] / stats["total"]) * 100
                avg_error = stats["total_error"] / stats["total"]
                
                status = "✓" if accuracy_pct >= 60 else "✗ NEEDS RETRAIN"
                if accuracy_pct < 60:
                    retrain_needed.append(prop_type)
                
                print(f"{prop_type:25} | Accuracy: {accuracy_pct:5.1f}% | Avg Error: {avg_error:6.2f} | {status}")
            
            # Trigger retraining for underperforming props
            if retrain_needed:
                print(f"\n{'='*80}")
                print(f"RETRAINING REQUIRED for {len(retrain_needed)} prop types:")
                print(", ".join(retrain_needed))
                print(f"{'='*80}\n")
                
                self._trigger_selective_retrain(retrain_needed)
            else:
                print(f"\n✓ All prop types performing well (>60% accuracy)")
        
        return {
            "games_analyzed": len(completed_games),
            "predictions_updated": predictions_updated,
            "prop_accuracy": prop_accuracy,
            "retrain_needed": retrain_needed if predictions_updated > 0 else []
        }
    
    def _get_actual_value(self, stat: PlayerStats, prop_type: str) -> float:
        """Map prop type to actual stat value"""
        stat_map = {
            'passing_yards': stat.passing_yards,
            'passing_tds': stat.passing_tds,
            'rushing_yards': stat.rushing_yards,
            'rushing_tds': stat.rushing_tds,
            'receiving_yards': stat.receiving_yards,
            'receiving_tds': stat.receiving_tds,
            'receptions': stat.receptions,
            'tackles_total': stat.tackles,
            'sacks': stat.sacks_def,
            'interceptions': stat.interceptions_def,
        }
        
        return stat_map.get(prop_type)
    
    def _trigger_selective_retrain(self, prop_types: List[str]):
        """Retrain only specific prop types that need improvement"""
        print(f"Starting selective retraining for {len(prop_types)} prop types...\n")
        
        for prop_type in prop_types:
            print(f"Retraining: {prop_type}")
            try:
                result = self.betting_ai.train_models_for_prop(prop_type)
                print(f"  ✓ Retrained {prop_type}: {result['models_trained']} models")
            except Exception as e:
                print(f"  ✗ Error retraining {prop_type}: {e}")
        
        print(f"\n✓ Selective retraining complete!")
    
    def get_accuracy_report(self) -> Dict:
        """Get overall accuracy report for all predictions"""
        all_predictions = self.db.query(Prediction).filter(
            Prediction.actual_value.isnot(None),  # Only predictions we've validated
            Prediction.season == 2025
        ).all()
        
        if not all_predictions:
            return {"message": "No validated predictions yet"}
        
        report = {
            "total_predictions": len(all_predictions),
            "accurate_predictions": sum(1 for p in all_predictions if p.was_accurate),
            "overall_accuracy": 0,
            "by_prop_type": {},
            "by_player_position": {}
        }
        
        # Overall accuracy
        report["overall_accuracy"] = (report["accurate_predictions"] / report["total_predictions"]) * 100
        
        # By prop type
        prop_groups = {}
        for pred in all_predictions:
            if pred.prop_type not in prop_groups:
                prop_groups[pred.prop_type] = []
            prop_groups[pred.prop_type].append(pred)
        
        for prop_type, preds in prop_groups.items():
            accurate = sum(1 for p in preds if p.was_accurate)
            avg_error = np.mean([p.prediction_error for p in preds if p.prediction_error is not None])
            
            report["by_prop_type"][prop_type] = {
                "total": len(preds),
                "accurate": accurate,
                "accuracy_pct": (accurate / len(preds)) * 100,
                "avg_error": round(avg_error, 2)
            }
        
        # By player position
        position_groups = {}
        for pred in all_predictions:
            player = self.db.query(Player).filter_by(id=pred.player_id).first()
            if player and player.position:
                if player.position not in position_groups:
                    position_groups[player.position] = []
                position_groups[player.position].append(pred)
        
        for position, preds in position_groups.items():
            accurate = sum(1 for p in preds if p.was_accurate)
            report["by_player_position"][position] = {
                "total": len(preds),
                "accurate": accurate,
                "accuracy_pct": (accurate / len(preds)) * 100
            }
        
        return report

