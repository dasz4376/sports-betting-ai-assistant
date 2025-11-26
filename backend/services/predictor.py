"""
Complete NFL Betting AI Prediction Engine

Features:
- Trains ML models (XGBoost, LightGBM, Random Forest) on historical data
- Makes predictions for upcoming player props
- Compares predictions vs sportsbook odds to find edges
- Generates betting recommendations with confidence scores
- Tracks prediction accuracy after games complete
- Retrains weekly with new data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path
import pickle

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb

from sqlalchemy import and_
from sqlalchemy.orm import Session
from models import Player, Game, PlayerStats, StatsFeatures, Team, Odds, Prediction
from services.matchup_analyzer import MatchupAnalyzer


class BettingAI:
    """Complete NFL Betting AI - trains models, makes predictions, finds edges"""
    
    def __init__(self, db: Session):
        self.db = db
        self.models = {}
        self.models_dir = Path("trained_models")
        self.models_dir.mkdir(exist_ok=True)
        self.matchup_analyzer = MatchupAnalyzer(db)
        
        # Define prop types we predict
        # NOTE: 'target' must match stats_features column names (avg_{target})
        self.prop_types = {
            # QB Passing Props
            'passing_yards': {'target': 'passing_yards', 'positions': ['QB']},
            'passing_tds': {'target': 'passing_tds', 'positions': ['QB']},  # matches avg_passing_tds
            'passing_completions': {'target': 'passing_completions', 'positions': ['QB']},
            'passing_attempts': {'target': 'passing_attempts', 'positions': ['QB']},
            'interceptions': {'target': 'interceptions', 'positions': ['QB']},  # INTs thrown
            'sacks_taken': {'target': 'sacks_taken', 'positions': ['QB']},  # Times sacked
            
            # Rushing Props
            'rushing_yards': {'target': 'rushing_yards', 'positions': ['QB', 'RB', 'WR']},
            'rushing_tds': {'target': 'rushing_tds', 'positions': ['QB', 'RB', 'WR']},  # matches avg_rushing_tds
            'rushing_attempts': {'target': 'rushing_attempts', 'positions': ['QB', 'RB', 'WR']},
            
            # Receiving Props
            'receiving_yards': {'target': 'receiving_yards', 'positions': ['WR', 'TE', 'RB']},
            'receiving_tds': {'target': 'receiving_tds', 'positions': ['WR', 'TE', 'RB']},  # matches avg_receiving_tds
            'receptions': {'target': 'receptions', 'positions': ['WR', 'TE', 'RB']},
            'receiving_targets': {'target': 'targets', 'positions': ['WR', 'TE', 'RB']},  # matches avg_targets
            
            # Defensive Props
            'tackles_total': {'target': 'tackles_total', 'positions': ['LB', 'CB', 'S', 'DE', 'DT', 'DB', 'OLB', 'MLB', 'ILB', 'SS', 'FS']},
            'tackles_solo': {'target': 'tackles_solo', 'positions': ['LB', 'CB', 'S', 'DE', 'DT', 'DB', 'OLB', 'MLB', 'ILB', 'SS', 'FS']},
            'sacks': {'target': 'sacks', 'positions': ['DE', 'DT', 'LB', 'OLB', 'MLB']},  # Sacks made
            'interceptions_def': {'target': 'interceptions_def', 'positions': ['CB', 'S', 'DB', 'SS', 'FS', 'LB']},  # INTs caught
            'pass_deflections': {'target': 'pass_deflections', 'positions': ['CB', 'S', 'DB', 'SS', 'FS']},
            'tackles_for_loss': {'target': 'tackles_for_loss', 'positions': ['LB', 'DE', 'DT', 'OLB', 'MLB']},
            'qb_hits': {'target': 'qb_hits', 'positions': ['DE', 'DT', 'LB', 'OLB']},
            'forced_fumbles': {'target': 'forced_fumbles', 'positions': ['LB', 'DE', 'DT', 'CB', 'S']},
        }
    
    # ========================================================================
    # TRAINING METHODS
    # ========================================================================
    
    def load_training_data(self, prop_type: str) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load training data for a specific prop type from the database.
        Returns: (features_df, target_series)
        """
        print(f"\nLoading training data for {prop_type}...")
        
        prop_config = self.prop_types[prop_type]
        target_stat = prop_config['target']
        valid_positions = prop_config['positions']
        
        # Query player stats with their season features
        query = self.db.query(
            PlayerStats,
            StatsFeatures,
            Player,
            Game,
            Team  # Opponent team
        ).join(
            Player, PlayerStats.player_id == Player.id
        ).join(
            StatsFeatures, and_(
                StatsFeatures.player_id == Player.id,
                StatsFeatures.season == 2025
            )
        ).join(
            Game, PlayerStats.game_id == Game.id
        ).outerjoin(
            Team, 
            # Get opponent team
            (Player.team_id == Game.home_team_id) & (Team.id == Game.away_team_id) |
            (Player.team_id == Game.away_team_id) & (Team.id == Game.home_team_id)
        ).filter(
            Player.position.in_(valid_positions),
            StatsFeatures.games_played >= 3  # At least 3 games of history
        ).all()
        
        if not query:
            print(f"  [WARNING] No data found for {prop_type}")
            return None, None
        
        # Build feature matrix
        data = []
        for stat, features, player, game, opponent_team in query:
            # Get target value
            target_value = getattr(stat, target_stat, 0) or 0
            
            # Skip if player didn't participate
            if target_value == 0 and getattr(stat, 'snaps', None) == 0:
                continue
            
            # Is this a home game?
            is_home = player.team_id == game.home_team_id
            
            row = {
                # Target
                'target': float(target_value),
                
                # Player identity features
                'position': player.position,
                'games_played': features.games_played,
                
                # Season averages
                'avg_stat': getattr(features, f'avg_{target_stat}', 0) or 0,
                'total_yards': features.total_yards or 0,
                'total_tds': features.total_tds or 0,
                
                # Recent form
                'last_3_avg_yards': features.last_3_avg_yards or 0,
                'last_3_avg_tds': features.last_3_avg_tds or 0,
                
                # Consistency
                'consistency_score': features.consistency_score or 0,
                
                # Home/Away splits
                'is_home': int(is_home),
                'home_avg_yards': features.home_avg_yards or 0,
                'away_avg_yards': features.away_avg_yards or 0,
                
                # Usage (for receivers)
                'avg_target_share': features.avg_target_share or 0,
                'avg_receptions': features.avg_receptions or 0,
                'avg_targets': features.avg_targets or 0,
                
                # Game context
                'week': game.week,
                'opponent_team_id': opponent_team.id if opponent_team else 0,
            }
            
            # ADD MATCHUP FEATURES (opponent defensive strength)
            matchup_features = self.matchup_analyzer.calculate_historical_matchup_features(
                player_id=player.id,
                game_id=game.id,
                prop_type=prop_type
            )
            row.update(matchup_features)
            
            # Position-specific features
            if player.position == 'QB':
                row['avg_passing_yards'] = features.avg_passing_yards or 0
                row['avg_passing_tds'] = features.avg_passing_tds or 0
                row['avg_rushing_yards'] = features.avg_rushing_yards or 0
                row['avg_interceptions'] = features.avg_interceptions or 0
                row['avg_sacks_taken'] = features.avg_sacks_taken or 0
            elif player.position == 'RB':
                row['avg_rushing_yards'] = features.avg_rushing_yards or 0
                row['avg_rushing_tds'] = features.avg_rushing_tds or 0
                row['avg_receiving_yards'] = features.avg_receiving_yards or 0
                row['avg_receiving_tds'] = features.avg_receiving_tds or 0
            elif player.position in ['WR', 'TE']:
                row['avg_receiving_yards'] = features.avg_receiving_yards or 0
                row['avg_receiving_tds'] = features.avg_receiving_tds or 0
                row['avg_receptions'] = features.avg_receptions or 0
            elif player.position in ['LB', 'CB', 'S', 'DE', 'DT', 'DB', 'OLB', 'MLB', 'ILB', 'SS', 'FS', 'NT', 'DL']:
                # Defensive player stats
                row['avg_tackles'] = features.avg_tackles or 0
                row['avg_sacks_def'] = features.avg_sacks_def or 0
                row['avg_interceptions_def'] = features.avg_interceptions_def or 0
                row['avg_pass_deflections'] = features.avg_pass_deflections or 0
                row['avg_tackles_for_loss'] = features.avg_tackles_for_loss or 0
                row['total_tackles'] = features.total_tackles or 0
                row['total_sacks_def'] = features.total_sacks_def or 0
            
            data.append(row)
        
        if not data:
            print(f"  [WARNING] No valid training data for {prop_type}")
            return None, None
        
        df = pd.DataFrame(data)
        
        # Encode categorical features
        df = pd.get_dummies(df, columns=['position'], prefix='pos')
        
        # Separate features and target
        target = df['target']
        features = df.drop(['target'], axis=1)
        
        # Handle NaN values
        features = features.fillna(0)
        
        print(f"  [OK] Loaded {len(df)} samples")
        print(f"       Average {prop_type}: {target.mean():.1f}")
        
        return features, target
    
    def train_models_for_prop(self, prop_type: str) -> Dict:
        """Train multiple ML models for a specific prop type"""
        print(f"\n{'='*60}")
        print(f"TRAINING MODELS FOR: {prop_type.upper()}")
        print(f"{'='*60}")
        
        # Load data
        X, y = self.load_training_data(prop_type)
        
        if X is None or len(X) < 50:
            print(f"  [SKIP] Not enough data for {prop_type}")
            return None
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")
        
        models = {}
        results = {}
        
        # 1. XGBoost
        print("\n1. XGBoost...")
        xgb_model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1)
        xgb_model.fit(X_train, y_train)
        xgb_pred = xgb_model.predict(X_test)
        models['xgboost'] = xgb_model
        results['xgboost'] = {
            'mae': mean_absolute_error(y_test, xgb_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, xgb_pred)),
            'r2': r2_score(y_test, xgb_pred)
        }
        print(f"   MAE: {results['xgboost']['mae']:.2f} | R²: {results['xgboost']['r2']:.3f}")
        
        # 2. LightGBM
        print("2. LightGBM...")
        lgb_model = lgb.LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1, verbose=-1)
        lgb_model.fit(X_train, y_train)
        lgb_pred = lgb_model.predict(X_test)
        models['lightgbm'] = lgb_model
        results['lightgbm'] = {
            'mae': mean_absolute_error(y_test, lgb_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, lgb_pred)),
            'r2': r2_score(y_test, lgb_pred)
        }
        print(f"   MAE: {results['lightgbm']['mae']:.2f} | R²: {results['lightgbm']['r2']:.3f}")
        
        # 3. Random Forest
        print("3. Random Forest...")
        rf_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        models['random_forest'] = rf_model
        results['random_forest'] = {
            'mae': mean_absolute_error(y_test, rf_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, rf_pred)),
            'r2': r2_score(y_test, rf_pred)
        }
        print(f"   MAE: {results['random_forest']['mae']:.2f} | R²: {results['random_forest']['r2']:.3f}")
        
        # Find best model
        best_model_name = min(results, key=lambda k: results[k]['mae'])
        
        print(f"\n[BEST] {best_model_name.upper()} - MAE: {results[best_model_name]['mae']:.2f}")
        
        # Save models
        model_data = {
            'models': models,
            'results': results,
            'best_model': best_model_name,
            'feature_names': list(X.columns),
            'prop_type': prop_type,
            'trained_at': datetime.now().isoformat(),
        }
        
        model_path = self.models_dir / f"{prop_type}_models.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"[SAVED] {model_path}")
        
        return model_data
    
    def train_all_props(self):
        """Train models for all prop types"""
        print("\n" + "="*60)
        print("TRAINING NFL BETTING AI - ALL PROPS")
        print("="*60)
        
        all_results = {}
        for prop_type in self.prop_types.keys():
            result = self.train_models_for_prop(prop_type)
            if result:
                all_results[prop_type] = result
        
        print("\n" + "="*60)
        print("TRAINING COMPLETE")
        print("="*60)
        
        return all_results
    
    # ========================================================================
    # PREDICTION METHODS
    # ========================================================================
    
    def load_model(self, prop_type: str) -> Dict:
        """Load trained model from disk"""
        model_path = self.models_dir / f"{prop_type}_models.pkl"
        
        if not model_path.exists():
            return None
        
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    
    def predict_player_prop(
        self,
        player_id: int,
        game_id: int,
        prop_type: str,
        is_home: bool
    ) -> Dict:
        """
        Make a prediction for a specific player prop
        Args:
            player_id: Player database ID
            game_id: Upcoming game ID
            prop_type: Type of prop (e.g., 'passing_yards')
            is_home: Is the player's team playing at home?
        Returns: Prediction dictionary
        """
        # Load model
        model_data = self.load_model(prop_type)
        if not model_data:
            return {"error": f"No trained model for {prop_type}"}
        
        # Get best model
        best_model_name = model_data['best_model']
        model = model_data['models'][best_model_name]
        feature_names = model_data['feature_names']
        
        # Get player and features
        player = self.db.query(Player).filter_by(id=player_id).first()
        if not player:
            return {"error": "Player not found"}
        
        features = self.db.query(StatsFeatures).filter_by(
            player_id=player_id,
            season=2025
        ).first()
        if not features:
            return {"error": "No features found for player"}
        
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return {"error": "Game not found"}
        
        # Build feature vector
        target_stat = self.prop_types[prop_type]['target']
        
        # Get opponent team ID
        opponent_team_id = self.matchup_analyzer.get_opponent_team_id(player_id, game_id)
        
        row = {
            'games_played': features.games_played,
            'avg_stat': getattr(features, f'avg_{target_stat}', 0) or 0,
            'total_yards': features.total_yards or 0,
            'total_tds': features.total_tds or 0,
            'last_3_avg_yards': features.last_3_avg_yards or 0,
            'last_3_avg_tds': features.last_3_avg_tds or 0,
            'consistency_score': features.consistency_score or 0,
            'is_home': int(is_home),
            'home_avg_yards': features.home_avg_yards or 0,
            'away_avg_yards': features.away_avg_yards or 0,
            'avg_target_share': features.avg_target_share or 0,
            'avg_receptions': features.avg_receptions or 0,
            'avg_targets': features.avg_targets or 0,
            'week': game.week,
            'opponent_team_id': opponent_team_id or 0,
        }
        
        # ADD MATCHUP FEATURES (opponent defense + injuries)
        matchup_features = self.matchup_analyzer.get_matchup_features_for_prediction(
            player_id=player_id,
            game_id=game_id,
            prop_type=prop_type
        )
        row.update(matchup_features)
        
        # Position-specific features
        if player.position == 'QB':
            row['avg_passing_yards'] = features.avg_passing_yards or 0
            row['avg_passing_tds'] = features.avg_passing_tds or 0
            row['avg_rushing_yards'] = features.avg_rushing_yards or 0
            row['avg_interceptions'] = features.avg_interceptions or 0
            row['avg_sacks_taken'] = features.avg_sacks_taken or 0
        elif player.position == 'RB':
            row['avg_rushing_yards'] = features.avg_rushing_yards or 0
            row['avg_rushing_tds'] = features.avg_rushing_tds or 0
            row['avg_receiving_yards'] = features.avg_receiving_yards or 0
            row['avg_receiving_tds'] = features.avg_receiving_tds or 0
        elif player.position in ['WR', 'TE']:
            row['avg_receiving_yards'] = features.avg_receiving_yards or 0
            row['avg_receiving_tds'] = features.avg_receiving_tds or 0
            row['avg_receptions'] = features.avg_receptions or 0
        elif player.position in ['LB', 'CB', 'S', 'DE', 'DT', 'DB', 'OLB', 'MLB', 'ILB', 'SS', 'FS', 'NT', 'DL']:
            # Defensive player stats
            row['avg_tackles'] = features.avg_tackles or 0
            row['avg_sacks_def'] = features.avg_sacks_def or 0
            row['avg_interceptions_def'] = features.avg_interceptions_def or 0
            row['avg_pass_deflections'] = features.avg_pass_deflections or 0
            row['avg_tackles_for_loss'] = features.avg_tackles_for_loss or 0
            row['total_tackles'] = features.total_tackles or 0
            row['total_sacks_def'] = features.total_sacks_def or 0
        
        # Create DataFrame with all feature names (including one-hot encoded positions)
        X = pd.DataFrame([row])
        
        # Add position one-hot encoding
        for feature_name in feature_names:
            if feature_name.startswith('pos_') and feature_name not in X.columns:
                X[feature_name] = 0
        if f'pos_{player.position}' in feature_names:
            X[f'pos_{player.position}'] = 1
        
        # Ensure correct column order
        X = X.reindex(columns=feature_names, fill_value=0)
        
        # Make prediction
        predicted_value = model.predict(X)[0]
        
        # Calculate confidence based on consistency score (0-100)
        confidence = features.consistency_score * 100 if features.consistency_score else 50
        
        result = {
            'player_id': player_id,
            'player_name': player.name,
            'position': player.position,
            'team': player.team.name if player.team else "Unknown",
            'game_id': game_id,
            'prop_type': prop_type,
            'predicted_value': round(predicted_value, 2),
            'confidence': round(confidence, 1),
            'model_used': best_model_name,
            'season_avg': round(row['avg_stat'], 2),
            'recent_form': round(row['last_3_avg_yards'], 2)
        }
        
        return result
    
    def store_prediction(
        self,
        player_id: int,
        game_id: int,
        prop_type: str,
        predicted_value: float,
        confidence: float,
        bet_category: str = "single",
        line_used: float = None,
        model_version: str = None
    ) -> Prediction:
        """
        Store a prediction to the database for learning tracking.
        
        This enables the AI to learn from its own predictions by:
        1. Recording what we predicted
        2. Later comparing to actual results
        3. Tracking accuracy by bet type, player, etc.
        """
        # Convert numpy types to native Python types
        predicted_value = float(predicted_value) if predicted_value is not None else 0.0
        confidence = float(confidence) if confidence is not None else 50.0
        line_used = float(line_used) if line_used is not None else None
        
        # Get game week
        game = self.db.query(Game).filter_by(id=game_id).first()
        week = game.week if game else None
        
        # Check if prediction already exists
        existing = self.db.query(Prediction).filter_by(
            player_id=player_id,
            game_id=game_id,
            prop_type=prop_type,
            season=2025
        ).first()
        
        if existing:
            # Update existing prediction
            existing.predicted_value = predicted_value
            existing.confidence_score = confidence
            existing.bet_category = bet_category
            existing.line_used = line_used
            existing.model_version = model_version
            return existing
        
        # Create new prediction
        prediction = Prediction(
            player_id=player_id,
            game_id=game_id,
            stat_type=prop_type,  # Legacy field
            prop_type=prop_type,  # New field for learning
            bet_category=bet_category,  # single, combined, anytime_td
            predicted_value=predicted_value,
            confidence_score=confidence,
            line_used=line_used,
            model_version=model_version,
            season=2025,
            week=week
        )
        
        self.db.add(prediction)
        self.db.commit()
        
        return prediction
    
    def store_parlay_predictions(self, picks: list, game_ids: list = None):
        """
        Store all predictions from a parlay for learning.
        
        This lets the AI learn:
        - Which pick types hit more often
        - Which players are reliable
        - Whether combined stats beat single stats
        """
        stored_count = 0
        
        for pick in picks:
            player_id = pick.get('player_id')
            game_id = pick.get('game_id')
            
            if not player_id:
                continue
            
            # Determine bet category
            stat_type = pick.get('stat_type', pick.get('prop_type', ''))
            if '+' in stat_type or 'combined' in stat_type.lower():
                bet_category = "combined"
            elif 'anytime' in stat_type.lower() or 'td' in stat_type.lower():
                bet_category = "anytime_td"
            else:
                bet_category = "single"
            
            self.store_prediction(
                player_id=player_id,
                game_id=game_id,
                prop_type=stat_type,
                predicted_value=pick.get('predicted_value', pick.get('line', 0)),
                confidence=pick.get('confidence', 50),
                bet_category=bet_category,
                line_used=pick.get('line'),
                model_version="parlay_v1"
            )
            stored_count += 1
        
        print("[*] Stored", stored_count, "predictions for learning")
    
    # ========================================================================
    # EDGE DETECTION & BETTING RECOMMENDATIONS
    # ========================================================================
    
    def find_edges(
        self,
        game_id: int,
        min_edge: float = 10.0,
        min_confidence: float = 60.0
    ) -> List[Dict]:
        """
        Find betting edges by comparing predictions vs sportsbook odds
        Args:
            game_id: Game to analyze
            min_edge: Minimum edge percentage to recommend
            min_confidence: Minimum confidence score
        Returns: List of betting recommendations
        """
        print(f"\nFinding edges for game {game_id}...")
        
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return []
        
        # Get all odds for this game
        odds = self.db.query(Odds).filter_by(game_id=game_id).all()
        if not odds:
            print("  No odds found for this game")
            return []
        
        edges = []
        
        for odd in odds:
            if odd.prop_type and odd.player_name:
                # This is a player prop
                # Find the player
                player = self.db.query(Player).filter_by(name=odd.player_name).first()
                if not player:
                    continue
                
                # Determine if player is home
                is_home = player.team_id == game.home_team_id
                
                # Map odds prop_type to our prop_type
                prop_map = {
                    'player_pass_yds': 'passing_yards',
                    'player_rush_yds': 'rushing_yards',
                    'player_reception_yds': 'receiving_yards',
                    'player_receptions': 'receptions',
                    'player_pass_tds': 'passing_tds',
                }
                
                our_prop_type = prop_map.get(odd.prop_type)
                if not our_prop_type:
                    continue
                
                # Make prediction
                prediction = self.predict_player_prop(
                    player.id,
                    game_id,
                    our_prop_type,
                    is_home
                )
                
                if 'error' in prediction:
                    continue
                
                # Calculate edge
                bookmaker_line = odd.point if odd.point else 0
                our_prediction = prediction['predicted_value']
                edge = our_prediction - bookmaker_line
                edge_pct = (edge / bookmaker_line * 100) if bookmaker_line > 0 else 0
                
                confidence = prediction['confidence']
                
                # Check if this meets our edge criteria
                if abs(edge_pct) >= min_edge and confidence >= min_confidence:
                    recommendation = {
                        'player_name': player.name,
                        'position': player.position,
                        'team': player.team.name if player.team else "Unknown",
                        'prop_type': our_prop_type,
                        'bookmaker_line': bookmaker_line,
                        'our_prediction': our_prediction,
                        'edge': round(edge, 2),
                        'edge_pct': round(edge_pct, 2),
                        'confidence': confidence,
                        'recommendation': 'OVER' if edge > 0 else 'UNDER',
                        'bookmaker': odd.bookmaker,
                        'odds_over': odd.price_over,
                        'odds_under': odd.price_under,
                        'model': prediction['model_used']
                    }
                    edges.append(recommendation)
        
        # Sort by edge percentage (absolute value)
        edges.sort(key=lambda x: abs(x['edge_pct']), reverse=True)
        
        print(f"  Found {len(edges)} betting opportunities")
        
        return edges
    
    def print_betting_recommendations(self, edges: List[Dict]):
        """Pretty print betting recommendations"""
        if not edges:
            print("\n[NO EDGES FOUND] No betting opportunities meet criteria")
            return
        
        print("\n" + "="*80)
        print("BETTING RECOMMENDATIONS")
        print("="*80)
        
        for i, edge in enumerate(edges, 1):
            print(f"\n{i}. {edge['player_name']} ({edge['position']}) - {edge['team']}")
            print(f"   Prop: {edge['prop_type'].replace('_', ' ').title()}")
            print(f"   Bookmaker Line: {edge['bookmaker_line']:.1f} ({edge['bookmaker']})")
            print(f"   Our Prediction: {edge['our_prediction']:.1f}")
            print(f"   Edge: {edge['edge']:+.1f} ({edge['edge_pct']:+.1f}%)")
            print(f"   Confidence: {edge['confidence']:.0f}%")
            print(f"   RECOMMENDATION: {edge['recommendation']}")
            print(f"   Odds: Over {edge['odds_over']} | Under {edge['odds_under']}")
        
        print("\n" + "="*80)


# Example usage
def test_betting_ai():
    """Test the complete betting AI"""
    from database import SessionLocal
    
    db = SessionLocal()
    ai = BettingAI(db)
    
    print("NFL Betting AI initialized!")
    print("Ready to train models and find edges.\n")
    
    db.close()


if __name__ == "__main__":
    test_betting_ai()
