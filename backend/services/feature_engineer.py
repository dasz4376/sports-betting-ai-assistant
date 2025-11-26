"""
Feature Engineering Service
Computes season averages and ML features for each player (one record per player)
"""
from typing import Dict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Player, Game, PlayerStats, StatsFeatures


class FeatureEngineer:
    """Computes season averages and features for ML models"""
    
    def __init__(self, db: Session):
        self.db = db
        self.current_season = 2025  # ESPN uses the ending year of the season
    
    def compute_all_features(self):
        """Compute features for all players with stats"""
        print("\n" + "="*60)
        print("COMPUTING PLAYER SEASON AVERAGES")
        print("="*60 + "\n")
        
        # Get all players who have stats
        players_with_stats = self.db.query(PlayerStats.player_id).distinct().all()
        player_ids = [p[0] for p in players_with_stats]
        
        print(f"Computing features for {len(player_ids)} players...")
        
        features_created = 0
        features_updated = 0
        
        for player_id in player_ids:
            created = self.compute_player_features(player_id)
            if created:
                features_created += 1
            else:
                features_updated += 1
        
        self.db.commit()
        
        print(f"\n{'='*60}")
        print(f"FEATURES COMPLETED")
        print(f"Created: {features_created} | Updated: {features_updated}")
        print(f"{'='*60}\n")
        
        return features_created + features_updated
    
    def compute_player_features(self, player_id: int) -> bool:
        """
        Compute season averages for a specific player
        Returns True if created new record, False if updated existing
        """
        player = self.db.query(Player).get(player_id)
        if not player:
            return False
        
        # Get all stats for this player this season
        stats = self.db.query(PlayerStats, Game).join(
            Game, PlayerStats.game_id == Game.id
        ).filter(
            PlayerStats.player_id == player_id,
            Game.season == self.current_season
        ).order_by(Game.game_date).all()
        
        if not stats:
            return False
        
        # Check if feature record exists
        existing = self.db.query(StatsFeatures).filter_by(
            player_id=player_id
        ).first()
        
        # Compute averages
        features_data = self._compute_season_averages(stats, player)
        
        if existing:
            # Update existing record
            for key, value in features_data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now()
            return False
        else:
            # Create new record
            features = StatsFeatures(
                player_id=player_id,
                player_name=player.name,
                player_position=player.position,
                season=self.current_season,
                **features_data
            )
            self.db.add(features)
            return True
    
    def _compute_season_averages(self, stats: list, player: Player) -> Dict:
        """Compute all season averages and features"""
        games_played = len(stats)
        
        # Extract stats by position
        passing_yards = []
        passing_tds = []
        rushing_yards = []
        rushing_tds = []
        receiving_yards = []
        receiving_tds = []
        receptions = []
        targets = []
        target_shares = []
        
        # Offensive negative stats
        interceptions = []
        sacks_taken = []
        
        # Defensive stats
        tackles = []
        sacks_def = []
        interceptions_def = []
        pass_deflections = []
        tackles_for_loss = []
        
        # Collect data from all games
        for stat, game in stats:
            # Offensive stats
            passing_yards.append(float(stat.passing_yards or 0))
            passing_tds.append(float(stat.passing_touchdowns or 0))
            rushing_yards.append(float(stat.rushing_yards or 0))
            rushing_tds.append(float(stat.rushing_touchdowns or 0))
            receiving_yards.append(float(stat.receiving_yards or 0))
            receiving_tds.append(float(stat.receiving_touchdowns or 0))
            receptions.append(float(stat.receptions or 0))
            targets.append(float(stat.receiving_targets or 0))
            
            # Offensive negative stats
            interceptions.append(float(stat.interceptions or 0))
            sacks_taken.append(float(stat.sacks_taken or 0))
            
            # Compute target share for this game (simplified - just use targets as proxy)
            target_shares.append(float(stat.receiving_targets or 0))
            
            # Defensive stats
            tackles.append(float(stat.tackles_total or 0))
            sacks_def.append(float(stat.sacks or 0))
            interceptions_def.append(float(stat.interceptions_def or 0))
            pass_deflections.append(float(stat.pass_deflections or 0))
            tackles_for_loss.append(float(stat.tackles_for_loss or 0))
        
        # Compute position-specific totals
        if player.position == 'QB':
            position_yards = [py + ry for py, ry in zip(passing_yards, rushing_yards)]
            position_tds = [pt + rt for pt, rt in zip(passing_tds, rushing_tds)]
        elif player.position == 'RB':
            position_yards = [ry + recy for ry, recy in zip(rushing_yards, receiving_yards)]
            position_tds = [rt + rect for rt, rect in zip(rushing_tds, receiving_tds)]
        elif player.position in ['WR', 'TE']:
            position_yards = receiving_yards
            position_tds = receiving_tds
        else:
            position_yards = [ry + recy for ry, recy in zip(rushing_yards, receiving_yards)]
            position_tds = [rt + rect for rt, rect in zip(rushing_tds, receiving_tds)]
        
        # Compute last 3 games average
        last_3_yards = position_yards[-3:] if len(position_yards) >= 3 else position_yards
        last_3_tds = position_tds[-3:] if len(position_tds) >= 3 else position_tds
        
        # Compute home/away splits
        home_yards = []
        away_yards = []
        for (stat, game), yards in zip(stats, position_yards):
            if game.home_team_id == player.team_id:
                home_yards.append(yards)
            else:
                away_yards.append(yards)
        
        # Compute consistency (coefficient of variation inverse)
        consistency = self._compute_consistency(position_yards)
        
        return {
            'games_played': games_played,
            # Offensive Stats
            'avg_passing_yards': np.mean(passing_yards) if passing_yards else 0,
            'avg_passing_tds': np.mean(passing_tds) if passing_tds else 0,
            'avg_interceptions': np.mean(interceptions) if interceptions else 0,  # INTs THROWN (negative)
            'avg_sacks_taken': np.mean(sacks_taken) if sacks_taken else 0,  # Times SACKED (negative)
            'avg_rushing_yards': np.mean(rushing_yards) if rushing_yards else 0,
            'avg_rushing_tds': np.mean(rushing_tds) if rushing_tds else 0,
            'avg_receiving_yards': np.mean(receiving_yards) if receiving_yards else 0,
            'avg_receiving_tds': np.mean(receiving_tds) if receiving_tds else 0,
            'avg_receptions': np.mean(receptions) if receptions else 0,
            'avg_targets': np.mean(targets) if targets else 0,
            'total_yards': sum(position_yards),
            'total_tds': sum(position_tds),
            'total_interceptions': int(sum(interceptions)),  # Total INTs THROWN (negative)
            'total_sacks_taken': float(sum(sacks_taken)),  # Total times SACKED (negative)
            'last_3_avg_yards': np.mean(last_3_yards) if last_3_yards else 0,
            'last_3_avg_tds': np.mean(last_3_tds) if last_3_tds else 0,
            'consistency_score': consistency,
            'home_avg_yards': np.mean(home_yards) if home_yards else 0,
            'away_avg_yards': np.mean(away_yards) if away_yards else 0,
            'avg_target_share': np.mean(target_shares) if target_shares else 0,
            # Defensive Stats
            'avg_tackles': np.mean(tackles) if tackles else 0,
            'avg_sacks_def': np.mean(sacks_def) if sacks_def else 0,  # Sacks MADE (positive)
            'avg_interceptions_def': np.mean(interceptions_def) if interceptions_def else 0,  # INTs CAUGHT (positive)
            'avg_pass_deflections': np.mean(pass_deflections) if pass_deflections else 0,
            'avg_tackles_for_loss': np.mean(tackles_for_loss) if tackles_for_loss else 0,
            'total_tackles': int(sum(tackles)),
            'total_sacks_def': float(sum(sacks_def)),  # Total sacks MADE (positive)
            'total_interceptions_def': int(sum(interceptions_def))  # Total INTs CAUGHT (positive)
        }
    
    def _compute_consistency(self, values: list) -> float:
        """Compute consistency score (inverse of coefficient of variation)"""
        if len(values) < 2 or np.mean(values) == 0:
            return 0.0
        
        cv = np.std(values) / np.mean(values)
        consistency = 1.0 / (1.0 + cv) if cv > 0 else 1.0
        
        return float(consistency)


def compute_features_for_all():
    """Standalone function to compute features"""
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        engineer = FeatureEngineer(db)
        features_count = engineer.compute_all_features()
        return features_count
    finally:
        db.close()


if __name__ == "__main__":
    compute_features_for_all()
