"""
Matchup Analyzer - Calculates opponent defensive strength features

This module analyzes how opponent defenses impact player performance:
- Pass rush strength (affects QB passing, sacks taken)
- Secondary strength (affects passing/receiving yards, INTs)
- Run defense strength (affects rushing yards)
- Coverage quality (affects target distribution)

Used for:
1. Training ML models with historical matchup data
2. Making matchup-aware predictions for upcoming games
3. Continuous learning from post-game results
"""
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import Player, Game, PlayerStats, StatsFeatures, Team, Injury
from datetime import datetime, timedelta


class MatchupAnalyzer:
    """Analyzes opponent defensive strength for matchup-aware predictions"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_opponent_team_id(self, player_id: int, game_id: int) -> Optional[int]:
        """Get the opponent team ID for a player in a specific game"""
        # Get player's team
        player = self.db.query(Player).filter_by(id=player_id).first()
        if not player:
            return None
        
        # Get game
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return None
        
        # Determine opponent
        if player.team_id == game.home_team_id:
            return game.away_team_id
        elif player.team_id == game.away_team_id:
            return game.home_team_id
        
        return None
    
    def get_defensive_features(
        self, 
        opponent_team_id: int, 
        season: int, 
        up_to_week: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate defensive strength features for an opponent team
        
        Args:
            opponent_team_id: The opposing team's ID
            season: Season year
            up_to_week: Only include games up to this week (for historical accuracy)
        
        Returns:
            Dictionary of defensive features averaged per game
        """
        # Get all defensive players on opponent team
        defensive_positions = ['CB', 'S', 'DB', 'LB', 'DE', 'DT', 'OLB', 'ILB', 'MLB']
        
        defensive_players = self.db.query(Player).filter(
            Player.team_id == opponent_team_id,
            Player.position.in_(defensive_positions)
        ).all()
        
        if not defensive_players:
            return self._get_empty_defensive_features()
        
        player_ids = [p.id for p in defensive_players]
        
        # Query their stats features (season averages)
        query = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_(player_ids),
            StatsFeatures.season == season
        )
        
        # If up_to_week specified, we'd need to recalculate (for now use full season)
        # TODO: Implement week-by-week defensive features for more accurate historical data
        
        defensive_stats = query.all()
        
        if not defensive_stats:
            return self._get_empty_defensive_features()
        
        # Aggregate defensive stats
        total_games = sum(s.games_played for s in defensive_stats) or 1
        
        # Pass Rush Stats (affects QB passing, sacks taken)
        total_sacks = sum(s.avg_sacks_def * s.games_played for s in defensive_stats)
        total_qb_hits = sum(getattr(s, 'avg_qb_hits', 0) * s.games_played for s in defensive_stats)
        total_tfls = sum(getattr(s, 'avg_tackles_for_loss', 0) * s.games_played for s in defensive_stats)
        
        # Secondary Stats (affects passing yards, INTs, completions)
        total_ints = sum(s.avg_interceptions_def * s.games_played for s in defensive_stats)
        total_pass_def = sum(getattr(s, 'avg_pass_deflections', 0) * s.games_played for s in defensive_stats)
        
        # Run Defense Stats (affects rushing yards)
        total_tackles = sum(s.avg_tackles * s.games_played for s in defensive_stats)
        total_solo_tackles = sum(getattr(s, 'avg_tackles_solo', 0) * s.games_played for s in defensive_stats)
        
        # Forced Fumbles (general defensive pressure)
        total_forced_fumbles = sum(getattr(s, 'avg_forced_fumbles', 0) * s.games_played for s in defensive_stats)
        
        # Calculate per-game averages
        num_defenders = len(defensive_stats)
        
        return {
            # Pass Rush Strength (higher = tougher for QB)
            'opp_sacks_per_game': total_sacks / total_games if total_games > 0 else 0,
            'opp_qb_hits_per_game': total_qb_hits / total_games if total_games > 0 else 0,
            'opp_tfls_per_game': total_tfls / total_games if total_games > 0 else 0,
            'opp_pass_rush_pressure': (total_sacks + total_qb_hits + total_tfls) / total_games if total_games > 0 else 0,
            
            # Secondary Strength (higher = tougher for WRs)
            'opp_ints_per_game': total_ints / total_games if total_games > 0 else 0,
            'opp_pass_def_per_game': total_pass_def / total_games if total_games > 0 else 0,
            'opp_secondary_strength': (total_ints + total_pass_def) / total_games if total_games > 0 else 0,
            
            # Run Defense Strength (higher = tougher for RBs)
            'opp_tackles_per_game': total_tackles / total_games if total_games > 0 else 0,
            'opp_solo_tackles_per_game': total_solo_tackles / total_games if total_games > 0 else 0,
            'opp_run_def_strength': (total_tackles + total_tfls) / total_games if total_games > 0 else 0,
            
            # Overall Defensive Strength
            'opp_forced_fumbles_per_game': total_forced_fumbles / total_games if total_games > 0 else 0,
            'opp_defensive_playmakers': num_defenders,  # Number of active defensive players
        }
    
    def _get_empty_defensive_features(self) -> Dict[str, float]:
        """Return zero values when no defensive data available"""
        return {
            'opp_sacks_per_game': 0.0,
            'opp_qb_hits_per_game': 0.0,
            'opp_tfls_per_game': 0.0,
            'opp_pass_rush_pressure': 0.0,
            'opp_ints_per_game': 0.0,
            'opp_pass_def_per_game': 0.0,
            'opp_secondary_strength': 0.0,
            'opp_tackles_per_game': 0.0,
            'opp_solo_tackles_per_game': 0.0,
            'opp_run_def_strength': 0.0,
            'opp_forced_fumbles_per_game': 0.0,
            'opp_defensive_playmakers': 0.0,
            'opp_key_injuries': 0.0,
            'own_team_key_injuries': 0.0,
        }
    
    def get_injury_impact(
        self,
        team_id: int,
        game_date: datetime,
        position_group: str = 'all'
    ) -> Dict[str, float]:
        """
        Calculate injury impact for a team around a specific game date
        
        Args:
            team_id: Team ID to check injuries for
            game_date: Game date (check injuries within 7 days)
            position_group: 'offense', 'defense', or 'all'
        
        Returns:
            Dictionary with injury impact metrics
        """
        # Query recent injuries (within 7 days of game)
        date_range_start = game_date - timedelta(days=7)
        date_range_end = game_date + timedelta(days=1)
        
        injuries = self.db.query(Injury).join(
            Player, Injury.player_id == Player.id
        ).filter(
            Player.team_id == team_id,
            Injury.date_reported >= date_range_start,
            Injury.date_reported <= date_range_end,
            Injury.is_active == True,
            Injury.status.in_(['Out', 'Doubtful', 'Questionable'])  # Active injury statuses
        ).all()
        
        if not injuries:
            return {
                'key_injuries': 0,
                'out_players': 0,
                'doubtful_players': 0,
                'questionable_players': 0,
                'injured_starters': 0,
            }
        
        # Categorize injuries
        out_count = 0
        doubtful_count = 0
        questionable_count = 0
        starter_injuries = 0
        
        # Positions that are considered "key" for matchup impact
        key_offensive_positions = ['QB', 'RB', 'WR', 'TE', 'LT', 'RT', 'C', 'LG', 'RG']
        key_defensive_positions = ['CB', 'S', 'LB', 'DE', 'DT', 'OLB', 'ILB', 'MLB', 'FS', 'SS']
        
        for injury in injuries:
            player = self.db.query(Player).filter_by(id=injury.player_id).first()
            if not player:
                continue
            
            # Filter by position group if specified
            if position_group == 'offense' and player.position not in key_offensive_positions:
                continue
            elif position_group == 'defense' and player.position not in key_defensive_positions:
                continue
            
            # Count by severity
            if injury.status == 'Out':
                out_count += 1
                # Assume starter-level players (have significant stats)
                features = self.db.query(StatsFeatures).filter_by(
                    player_id=player.id,
                    season=2025
                ).first()
                if features and features.games_played >= 5:
                    starter_injuries += 1
            elif injury.status == 'Doubtful':
                doubtful_count += 1
            elif injury.status == 'Questionable':
                questionable_count += 1
        
        # Calculate weighted injury impact
        # Out = 1.0, Doubtful = 0.7, Questionable = 0.3
        injury_impact = (out_count * 1.0) + (doubtful_count * 0.7) + (questionable_count * 0.3)
        
        return {
            'key_injuries': injury_impact,
            'out_players': out_count,
            'doubtful_players': doubtful_count,
            'questionable_players': questionable_count,
            'injured_starters': starter_injuries,
        }
    
    def get_matchup_features_for_prediction(
        self,
        player_id: int,
        game_id: int,
        prop_type: str
    ) -> Dict[str, float]:
        """
        Get relevant matchup features for a specific prediction type
        
        Different prop types need different defensive features:
        - QB passing: pass rush + secondary
        - QB rushing: run defense + pass rush (rushes when pressured)
        - WR/TE receiving: secondary
        - RB rushing: run defense
        - RB receiving: secondary (when run D is strong, RB catches passes)
        """
        # Get opponent
        opponent_team_id = self.get_opponent_team_id(player_id, game_id)
        if not opponent_team_id:
            return self._get_empty_defensive_features()
        
        # Get game to determine season and date
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return self._get_empty_defensive_features()
        
        # Get player's team
        player = self.db.query(Player).filter_by(id=player_id).first()
        if not player:
            return self._get_empty_defensive_features()
        
        # Get all defensive features
        all_features = self.get_defensive_features(opponent_team_id, game.season)
        
        # Get injury data
        opponent_injuries = self.get_injury_impact(opponent_team_id, game.game_date, position_group='defense')
        own_team_injuries = self.get_injury_impact(player.team_id, game.game_date, position_group='offense')
        
        # Add injury impact to features
        all_features['opp_key_injuries'] = opponent_injuries['key_injuries']
        all_features['own_team_key_injuries'] = own_team_injuries['key_injuries']
        
        # Filter features based on prop type
        if prop_type in ['passing_yards', 'passing_tds', 'passing_completions', 'passing_attempts', 'interceptions']:
            # QB passing affected by pass rush + secondary + injuries
            return {
                'opp_pass_rush_pressure': all_features['opp_pass_rush_pressure'],
                'opp_sacks_per_game': all_features['opp_sacks_per_game'],
                'opp_qb_hits_per_game': all_features['opp_qb_hits_per_game'],
                'opp_secondary_strength': all_features['opp_secondary_strength'],
                'opp_ints_per_game': all_features['opp_ints_per_game'],
                'opp_pass_def_per_game': all_features['opp_pass_def_per_game'],
                'opp_key_injuries': all_features['opp_key_injuries'],  # Injured defenders = easier
                'own_team_key_injuries': all_features['own_team_key_injuries'],  # Injured O-line = harder
            }
        
        elif prop_type in ['sacks_taken']:
            # Sacks taken directly related to pass rush + O-line injuries
            return {
                'opp_pass_rush_pressure': all_features['opp_pass_rush_pressure'],
                'opp_sacks_per_game': all_features['opp_sacks_per_game'],
                'opp_qb_hits_per_game': all_features['opp_qb_hits_per_game'],
                'opp_tfls_per_game': all_features['opp_tfls_per_game'],
                'opp_key_injuries': all_features['opp_key_injuries'],  # Injured pass rushers = fewer sacks
                'own_team_key_injuries': all_features['own_team_key_injuries'],  # Injured O-line = more sacks
            }
        
        elif prop_type in ['rushing_yards', 'rushing_tds', 'rushing_attempts']:
            # Rushing affected by run defense (and QB rush affected by pass rush)
            if player and player.position == 'QB':
                # Mobile QB: rushes more when pass rush is strong
                return {
                    'opp_run_def_strength': all_features['opp_run_def_strength'],
                    'opp_tackles_per_game': all_features['opp_tackles_per_game'],
                    'opp_pass_rush_pressure': all_features['opp_pass_rush_pressure'],  # QB-specific
                    'opp_key_injuries': all_features['opp_key_injuries'],
                    'own_team_key_injuries': all_features['own_team_key_injuries'],
                }
            else:
                # RB: pure run defense
                return {
                    'opp_run_def_strength': all_features['opp_run_def_strength'],
                    'opp_tackles_per_game': all_features['opp_tackles_per_game'],
                    'opp_solo_tackles_per_game': all_features['opp_solo_tackles_per_game'],
                    'opp_tfls_per_game': all_features['opp_tfls_per_game'],
                    'opp_key_injuries': all_features['opp_key_injuries'],  # Injured LBs = more rushing yards
                    'own_team_key_injuries': all_features['own_team_key_injuries'],  # Injured O-line = fewer yards
                }
        
        elif prop_type in ['receiving_yards', 'receiving_tds', 'receptions', 'receiving_targets']:
            # Receiving affected by secondary + injuries
            return {
                'opp_secondary_strength': all_features['opp_secondary_strength'],
                'opp_ints_per_game': all_features['opp_ints_per_game'],
                'opp_pass_def_per_game': all_features['opp_pass_def_per_game'],
                'opp_key_injuries': all_features['opp_key_injuries'],  # Injured CBs/Safeties = more receiving yards
                'own_team_key_injuries': all_features['own_team_key_injuries'],  # Injured QB/O-line = fewer targets
            }
        
        elif prop_type in ['tackles_total', 'tackles_solo', 'sacks', 'interceptions_def', 
                           'pass_deflections', 'tackles_for_loss', 'qb_hits', 'forced_fumbles']:
            # Defensive player stats: need OPPONENT OFFENSE strength
            # TODO: Implement offensive strength features (O-line quality, QB tendency to throw INTs, etc.)
            return {}  # For now, return empty (defensive predictions work without matchup features)
        
        # Default: return all features
        return all_features
    
    def calculate_historical_matchup_features(
        self,
        player_id: int,
        game_id: int,
        prop_type: str
    ) -> Dict[str, float]:
        """
        Calculate matchup features for a historical game
        This ensures we only use data available BEFORE that game (no look-ahead bias)
        
        For now, uses season averages. TODO: Implement week-by-week calculation.
        """
        return self.get_matchup_features_for_prediction(player_id, game_id, prop_type)
    
    def analyze_team_matchup(self, team1_id: int, team2_id: int) -> Dict:
        """
        Comprehensive team vs team matchup analysis
        
        Returns detailed breakdown of:
        - Offensive strengths (QB, RB, WR/TE production)
        - Defensive strengths (pass rush, secondary, run defense)
        - Key player stats
        - Matchup advantages/disadvantages
        - Score prediction and win probability
        """
        from datetime import datetime
        
        team1 = self.db.query(Team).filter_by(id=team1_id).first()
        team2 = self.db.query(Team).filter_by(id=team2_id).first()
        
        if not team1 or not team2:
            return {"error": "Teams not found"}
        
        # ========== TEAM RECORDS ==========
        
        # Get all games for team 1
        team1_games = self.db.query(Game).filter(
            (
                (Game.home_team_id == team1_id) | (Game.away_team_id == team1_id)
            ) &
            (Game.status == "STATUS_FINAL") &
            (Game.season == 2025)
        ).all()
        
        team1_wins = sum(1 for g in team1_games if g.winner_team_id == team1_id)
        team1_losses = len(team1_games) - team1_wins
        
        # Get all games for team 2
        team2_games = self.db.query(Game).filter(
            (
                (Game.home_team_id == team2_id) | (Game.away_team_id == team2_id)
            ) &
            (Game.status == "STATUS_FINAL") &
            (Game.season == 2025)
        ).all()
        
        team2_wins = sum(1 for g in team2_games if g.winner_team_id == team2_id)
        team2_losses = len(team2_games) - team2_wins
        
        # Calculate win percentages
        team1_win_pct = team1_wins / len(team1_games) if team1_games else 0
        team2_win_pct = team2_wins / len(team2_games) if team2_games else 0
        
        # Recent momentum (last 3 games)
        team1_recent_games = sorted(team1_games, key=lambda g: g.game_date, reverse=True)[:3]
        team1_recent_wins = sum(1 for g in team1_recent_games if g.winner_team_id == team1_id)
        
        team2_recent_games = sorted(team2_games, key=lambda g: g.game_date, reverse=True)[:3]
        team2_recent_wins = sum(1 for g in team2_recent_games if g.winner_team_id == team2_id)
        
        # Check if they have an upcoming scheduled game
        now = datetime.utcnow()
        scheduled_game = self.db.query(Game).filter(
            (
                ((Game.home_team_id == team1_id) & (Game.away_team_id == team2_id)) |
                ((Game.home_team_id == team2_id) & (Game.away_team_id == team1_id))
            ) &
            (Game.game_date > now) &
            (Game.status != "STATUS_FINAL")
        ).order_by(Game.game_date).first()
        
        # ========== OFFENSIVE ANALYSIS ==========
        
        # Get offensive players
        team1_offensive = self.db.query(Player).filter(
            Player.team_id == team1_id,
            Player.position.in_(['QB', 'RB', 'WR', 'TE'])
        ).all()
        
        team2_offensive = self.db.query(Player).filter(
            Player.team_id == team2_id,
            Player.position.in_(['QB', 'RB', 'WR', 'TE'])
        ).all()
        
        # Get stats
        team1_off_features = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_([p.id for p in team1_offensive]),
            StatsFeatures.season == 2025
        ).all()
        
        team2_off_features = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_([p.id for p in team2_offensive]),
            StatsFeatures.season == 2025
        ).all()
        
        # Offensive breakdown by position
        def analyze_offense(features_list, players_list):
            # QB stats
            qb_players = [p for p in players_list if p.position == 'QB']
            qb_features = [f for f in features_list if f.player_position == 'QB' and f.games_played >= 3]
            
            qb_analysis = {}
            if qb_features:
                qb_analysis = {
                    'passing_yards_per_game': sum(f.avg_passing_yards or 0 for f in qb_features),
                    'passing_tds_per_game': sum(f.avg_passing_tds or 0 for f in qb_features),
                    'rushing_yards_per_game': sum(f.avg_rushing_yards or 0 for f in qb_features),
                    'interceptions_per_game': sum(f.avg_interceptions or 0 for f in qb_features),
                    'sacks_taken_per_game': sum(f.avg_sacks_taken or 0 for f in qb_features),
                    'top_qb': qb_features[0].player_name if qb_features else None
                }
            
            # RB stats
            rb_features = [f for f in features_list if f.player_position == 'RB' and f.games_played >= 3]
            rb_analysis = {
                'rushing_yards_per_game': sum(f.avg_rushing_yards or 0 for f in rb_features),
                'rushing_tds_per_game': sum(f.avg_rushing_tds or 0 for f in rb_features),
                'receiving_yards_per_game': sum(f.avg_receiving_yards or 0 for f in rb_features),
                'top_rb': rb_features[0].player_name if rb_features else None
            }
            
            # WR/TE stats
            wr_features = [f for f in features_list if f.player_position in ['WR', 'TE'] and f.games_played >= 3]
            wr_analysis = {
                'receiving_yards_per_game': sum(f.avg_receiving_yards or 0 for f in wr_features),
                'receiving_tds_per_game': sum(f.avg_receiving_tds or 0 for f in wr_features),
                'receptions_per_game': sum(f.avg_receptions or 0 for f in wr_features),
                'top_receivers': [f.player_name for f in sorted(wr_features, key=lambda x: x.avg_receiving_yards or 0, reverse=True)[:3]]
            }
            
            # Total offense
            total_yards = (
                qb_analysis.get('passing_yards_per_game', 0) +
                qb_analysis.get('rushing_yards_per_game', 0) +
                rb_analysis['rushing_yards_per_game'] +
                rb_analysis['receiving_yards_per_game'] +
                wr_analysis['receiving_yards_per_game']
            )
            
            total_tds = (
                (qb_analysis.get('passing_tds_per_game', 0) if qb_analysis else 0) +
                (qb_analysis.get('rushing_tds_per_game', 0) if qb_analysis else 0) +
                rb_analysis['rushing_tds_per_game'] +
                wr_analysis['receiving_tds_per_game']
            )
            
            return {
                'qb': qb_analysis,
                'rb': rb_analysis,
                'wr_te': wr_analysis,
                'total_yards_per_game': total_yards,
                'total_tds_per_game': total_tds
            }
        
        team1_offense_breakdown = analyze_offense(team1_off_features, team1_offensive)
        team2_offense_breakdown = analyze_offense(team2_off_features, team2_offensive)
        
        # ========== DEFENSIVE ANALYSIS ==========
        
        # Get defensive players
        team1_defensive = self.db.query(Player).filter(
            Player.team_id == team1_id,
            Player.position.in_(['CB', 'S', 'DB', 'LB', 'DE', 'DT', 'OLB', 'ILB', 'MLB'])
        ).all()
        
        team2_defensive = self.db.query(Player).filter(
            Player.team_id == team2_id,
            Player.position.in_(['CB', 'S', 'DB', 'LB', 'DE', 'DT', 'OLB', 'ILB', 'MLB'])
        ).all()
        
        # Get defensive stats
        team1_def_stats = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_([p.id for p in team1_defensive]),
            StatsFeatures.season == 2025
        ).all()
        
        team2_def_stats = self.db.query(StatsFeatures).filter(
            StatsFeatures.player_id.in_([p.id for p in team2_defensive]),
            StatsFeatures.season == 2025
        ).all()
        
        # Defensive breakdown
        def analyze_defense(features_list):
            if not features_list:
                return {
                    'sacks_per_game': 0,
                    'tackles_per_game': 0,
                    'interceptions_per_game': 0,
                    'pass_deflections_per_game': 0,
                    'pass_rush_rating': 0,
                    'secondary_rating': 0,
                    'run_def_rating': 0
                }
            
            sacks = sum(f.avg_sacks_def or 0 for f in features_list)
            tackles = sum(f.avg_tackles or 0 for f in features_list)
            ints = sum(f.avg_interceptions_def or 0 for f in features_list)
            pass_defs = sum(f.avg_pass_deflections or 0 for f in features_list)
            
            # Calculate ratings (more comprehensive)
            pass_rush_rating = sacks * 10  # Sacks are high value
            # Secondary rating: interceptions (very rare, high value) + pass deflections (more common, moderate value)
            secondary_rating = (ints * 25) + (pass_defs * 5)  # INTs worth 5x pass deflections
            run_def_rating = tackles / len(features_list) if features_list else 0  # Avg tackles per player
            
            return {
                'sacks_per_game': sacks,
                'tackles_per_game': tackles,
                'interceptions_per_game': ints,
                'pass_deflections_per_game': pass_defs,
                'pass_rush_rating': pass_rush_rating,
                'secondary_rating': secondary_rating,
                'run_def_rating': run_def_rating
            }
        
        team1_defense = analyze_defense(team1_def_stats)
        team2_defense = analyze_defense(team2_def_stats)
        
        # Get matchup-specific defensive features
        team1_def_features = self.get_defensive_features(team1_id, 2025)
        team2_def_features = self.get_defensive_features(team2_id, 2025)
        
        # ========== MATCHUP PREDICTION ==========
        
        # Team 1 offense vs Team 2 defense
        # Reduce Team 1's expected output based on Team 2's defensive strength
        team1_offense_vs_team2_def = team1_offense_breakdown['total_yards_per_game'] * (
            1 - (team2_def_features['opp_pass_rush_pressure'] + 
                 team2_def_features['opp_secondary_strength'] + 
                 team2_def_features['opp_run_def_strength']) / 100
        )
        
        team2_offense_vs_team1_def = team2_offense_breakdown['total_yards_per_game'] * (
            1 - (team1_def_features['opp_pass_rush_pressure'] + 
                 team1_def_features['opp_secondary_strength'] + 
                 team1_def_features['opp_run_def_strength']) / 100
        )
        
        # Score prediction (TDs * 7 + field goals)
        team1_base_score = (team1_offense_breakdown['total_tds_per_game'] * 7) + 9  # TDs + ~3 FGs
        team2_base_score = (team2_offense_breakdown['total_tds_per_game'] * 7) + 9
        
        # Adjust for opponent defense
        team1_predicted_score = team1_base_score * (1 - (team2_def_features['opp_defensive_playmakers'] / 100))
        team2_predicted_score = team2_base_score * (1 - (team1_def_features['opp_defensive_playmakers'] / 100))
        
        # Factor in team records and momentum
        # Teams with better records and recent momentum get a boost
        team1_record_boost = (team1_win_pct - 0.5) * 3  # +/- up to 1.5 points
        team2_record_boost = (team2_win_pct - 0.5) * 3
        
        team1_momentum_boost = (team1_recent_wins - 1.5) * 1.5  # Recent wins add confidence
        team2_momentum_boost = (team2_recent_wins - 1.5) * 1.5
        
        team1_predicted_score += team1_record_boost + team1_momentum_boost
        team2_predicted_score += team2_record_boost + team2_momentum_boost
        
        # Ensure realistic range
        team1_predicted_score = max(14, min(38, team1_predicted_score))
        team2_predicted_score = max(14, min(38, team2_predicted_score))
        
        # Win probability (more comprehensive)
        score_diff = team1_predicted_score - team2_predicted_score
        
        # Base win prob on score diff (each point = 3% shift)
        team1_win_prob = 50 + (score_diff * 3)
        
        # Adjust for record differential
        record_diff = (team1_win_pct - team2_win_pct) * 20  # Up to +/- 10%
        team1_win_prob += record_diff
        
        # Adjust for momentum
        momentum_diff = (team1_recent_wins - team2_recent_wins) * 5  # Up to +/- 7.5%
        team1_win_prob += momentum_diff
        
        # Cap between 10-90%
        team1_win_prob = max(10, min(90, team1_win_prob))
        
        # ========== KEY MATCHUP ADVANTAGES ==========
        
        advantages = []
        
        # Offensive advantages with detailed explanations
        team1_qb_passing = team1_offense_breakdown['qb'].get('passing_yards_per_game', 0)
        team2_secondary = team2_defense['secondary_rating']
        if team1_qb_passing > team2_secondary:
            advantages.append({
                "matchup": f"{team1.name} passing attack vs {team2.name} secondary",
                "advantage_to": team1.name,
                "explanation": f"{team1.name} averages {team1_qb_passing:.1f} passing yards/game while {team2.name} allows passing with secondary rating of {team2_secondary:.1f}. This is a significant mismatch.",
                "impact": "high"
            })
        
        team1_rb_rushing = team1_offense_breakdown['rb']['rushing_yards_per_game']
        team2_run_def = team2_defense['run_def_rating']
        if team1_rb_rushing > team2_run_def / 10:
            advantages.append({
                "matchup": f"{team1.name} rushing game vs {team2.name} run defense",
                "advantage_to": team1.name,
                "explanation": f"{team1.name} RBs average {team1_rb_rushing:.1f} rushing yards/game. {team2.name} run defense rating is {team2_run_def:.1f}, indicating a weaker front 7.",
                "impact": "medium"
            })
        
        team2_qb_passing = team2_offense_breakdown['qb'].get('passing_yards_per_game', 0)
        team1_secondary = team1_defense['secondary_rating']
        if team2_qb_passing > team1_secondary:
            advantages.append({
                "matchup": f"{team2.name} passing attack vs {team1.name} secondary",
                "advantage_to": team2.name,
                "explanation": f"{team2.name} averages {team2_qb_passing:.1f} passing yards/game while {team1.name} secondary rating is {team1_secondary:.1f}.",
                "impact": "high"
            })
        
        team2_rb_rushing = team2_offense_breakdown['rb']['rushing_yards_per_game']
        team1_run_def = team1_defense['run_def_rating']
        if team2_rb_rushing > team1_run_def / 10:
            advantages.append({
                "matchup": f"{team2.name} rushing game vs {team1.name} run defense",
                "advantage_to": team2.name,
                "explanation": f"{team2.name} RBs average {team2_rb_rushing:.1f} rushing yards/game against {team1.name} run defense rating of {team1_run_def:.1f}.",
                "impact": "medium"
            })
        
        # Defensive advantages
        team1_pass_rush = team1_defense['pass_rush_rating']
        team2_sacks_taken = team2_offense_breakdown['qb'].get('sacks_taken_per_game', 0)
        if team1_pass_rush > team2_sacks_taken * 5:
            advantages.append({
                "matchup": f"{team1.name} pass rush vs {team2.name} O-line",
                "advantage_to": team1.name,
                "explanation": f"{team1.name} pass rush rating is {team1_pass_rush:.1f} while {team2.name} QB takes {team2_sacks_taken:.2f} sacks/game, suggesting O-line vulnerabilities.",
                "impact": "high"
            })
        
        team2_pass_rush = team2_defense['pass_rush_rating']
        team1_sacks_taken = team1_offense_breakdown['qb'].get('sacks_taken_per_game', 0)
        if team2_pass_rush > team1_sacks_taken * 5:
            advantages.append({
                "matchup": f"{team2.name} pass rush vs {team1.name} O-line",
                "advantage_to": team2.name,
                "explanation": f"{team2.name} pass rush rating is {team2_pass_rush:.1f} against {team1.name} QB who takes {team1_sacks_taken:.2f} sacks/game.",
                "impact": "high"
            })
        
        # ========== BUILD RESPONSE ==========
        
        result = {
            "team1": {
                "name": team1.name,
                "record": f"{team1_wins}-{team1_losses}",
                "win_percentage": round(team1_win_pct * 100, 1),
                "recent_form": f"{team1_recent_wins}-{len(team1_recent_games) - team1_recent_wins} in last 3",
                "offense": team1_offense_breakdown,
                "defense": {
                    "sacks_per_game": team1_defense['sacks_per_game'],
                    "tackles_per_game": team1_defense['tackles_per_game'],
                    "interceptions_per_game": team1_defense['interceptions_per_game'],
                    "pass_rush_rating": round(team1_defense['pass_rush_rating'], 1),
                    "secondary_rating": round(team1_defense['secondary_rating'], 1),
                    "run_def_rating": round(team1_defense['run_def_rating'], 1)
                }
            },
            "team2": {
                "name": team2.name,
                "record": f"{team2_wins}-{team2_losses}",
                "win_percentage": round(team2_win_pct * 100, 1),
                "recent_form": f"{team2_recent_wins}-{len(team2_recent_games) - team2_recent_wins} in last 3",
                "offense": team2_offense_breakdown,
                "defense": {
                    "sacks_per_game": team2_defense['sacks_per_game'],
                    "tackles_per_game": team2_defense['tackles_per_game'],
                    "interceptions_per_game": team2_defense['interceptions_per_game'],
                    "pass_rush_rating": round(team2_defense['pass_rush_rating'], 1),
                    "secondary_rating": round(team2_defense['secondary_rating'], 1),
                    "run_def_rating": round(team2_defense['run_def_rating'], 1)
                }
            },
            "prediction": {
                "predicted_score": {
                    "team1": round(team1_predicted_score, 1),
                    "team2": round(team2_predicted_score, 1)
                },
                "win_probability": {
                    "team1": round(team1_win_prob, 1),
                    "team2": round(100 - team1_win_prob, 1)
                },
                "prediction_factors": {
                    "team1_offensive_strength": f"{team1_offense_breakdown['total_yards_per_game']:.1f} yards/game, {team1_offense_breakdown['total_tds_per_game']:.2f} TDs/game",
                    "team2_offensive_strength": f"{team2_offense_breakdown['total_yards_per_game']:.1f} yards/game, {team2_offense_breakdown['total_tds_per_game']:.2f} TDs/game",
                    "team1_defensive_impact": f"Facing {team2.name} defense with {team2_def_features['opp_pass_rush_pressure']:.1f} pass rush pressure",
                    "team2_defensive_impact": f"Facing {team1.name} defense with {team1_def_features['opp_pass_rush_pressure']:.1f} pass rush pressure",
                    "team1_record_impact": f"{team1_win_pct * 100:.1f}% win rate, {team1_recent_wins}/3 recent wins",
                    "team2_record_impact": f"{team2_win_pct * 100:.1f}% win rate, {team2_recent_wins}/3 recent wins"
                },
                "summary": f"Prediction based on: offensive/defensive player stats, season records ({team1.name} {team1_wins}-{team1_losses}, {team2.name} {team2_wins}-{team2_losses}), recent momentum, and matchup-specific advantages."
            },
            "key_matchup_advantages": advantages[:6],  # Top 6 advantages with explanations
            "game_info": {}
        }
        
        # Add scheduled game info if exists
        if scheduled_game:
            result["game_info"] = {
                "scheduled": True,
                "week": scheduled_game.week,
                "date": scheduled_game.game_date.strftime("%A, %B %d at %I:%M %p"),
                "venue": scheduled_game.venue,
                "home_team": team1.name if scheduled_game.home_team_id == team1_id else team2.name
            }
        else:
            result["game_info"] = {
                "scheduled": False,
                "note": "Hypothetical matchup analysis (not scheduled)"
            }
        
        return result

