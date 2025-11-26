"""
Database models for NFL Betting AI
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Team(Base):
    """NFL Teams"""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    espn_team_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    abbreviation = Column(String, nullable=False)
    location = Column(String)
    conference = Column(String)
    division = Column(String)
    logo_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    players = relationship("Player", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")


class Player(Base):
    """NFL Players"""
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    espn_player_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    jersey_number = Column(String)
    team_id = Column(Integer, ForeignKey("teams.id"))
    height = Column(String)
    weight = Column(Integer)
    age = Column(Integer)
    experience = Column(Integer)
    status = Column(String)  # active, injured, inactive
    headshot_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStats", back_populates="player")
    injuries = relationship("Injury", back_populates="player")


class Game(Base):
    """NFL Games"""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    espn_game_id = Column(String, unique=True, index=True, nullable=False)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    game_date = Column(DateTime(timezone=True), nullable=False)
    
    # Team Information
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    home_team_name = Column(String)  # Denormalized for easier querying
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_name = Column(String)  # Denormalized for easier querying
    
    # Game Results
    home_score = Column(Integer)
    away_score = Column(Integer)
    winner_team_id = Column(Integer, ForeignKey("teams.id"))  # NULL for ties
    winner_team_name = Column(String)  # Denormalized for easier querying
    
    status = Column(String)  # scheduled, in_progress, final
    venue = Column(String)
    weather = Column(JSON)  # temperature, wind, precipitation, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    stats = relationship("PlayerStats", back_populates="game")
    odds = relationship("Odds", back_populates="game")


class PlayerStats(Base):
    """Player statistics for a specific game
    
    These stats map directly to player prop markets:
    - passing_yards → player_pass_yds, player_pass_yds_alternate, player_pass_yds_h1, player_pass_yds_q1
    - passing_touchdowns → player_pass_tds, player_pass_tds_alternate, player_pass_tds_h1, player_pass_tds_q1
    - passing_completions → player_pass_completions, player_pass_completions_alternate
    - passing_attempts → player_pass_attempts, player_pass_attempts_alternate
    - interceptions → player_pass_interceptions, player_pass_interceptions_alternate
    - rushing_yards → player_rush_yds, player_rush_yds_alternate, player_rush_yds_q1
    - rushing_attempts → player_rush_attempts, player_rush_attempts_alternate
    - rushing_touchdowns → player_tds_over (combined with receiving TDs)
    - receiving_yards → player_reception_yds, player_reception_yds_alternate, player_reception_yds_q1
    - receptions → player_receptions, player_receptions_alternate
    - receiving_touchdowns → player_tds_over (combined with rushing TDs)
    
    Combined props calculated from multiple fields:
    - player_pass_rush_yds = passing_yards + rushing_yards
    - player_rush_reception_yds = rushing_yards + receiving_yards
    - player_pass_rush_reception_yds = passing_yards + rushing_yards + receiving_yards
    """
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player_name = Column(String, nullable=True)  # Denormalized for easy viewing
    player_position = Column(String, nullable=True)  # Player position (QB, RB, WR, LB, CB, etc.) - Critical for AI to identify defensive players
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Offensive Stats (map to player props)
    passing_yards = Column(Float, default=0)  # → player_pass_yds
    passing_completions = Column(Integer, default=0)  # → player_pass_completions
    passing_attempts = Column(Integer, default=0)  # → player_pass_attempts
    passing_touchdowns = Column(Integer, default=0)  # → player_pass_tds
    interceptions = Column(Integer, default=0)  # → player_pass_interceptions (INTs THROWN by QB - negative stat)
    sacks_taken = Column(Float, default=0)  # Times QB was SACKED (negative stat for offense)
    
    rushing_yards = Column(Float, default=0)  # → player_rush_yds
    rushing_attempts = Column(Integer, default=0)  # → player_rush_attempts
    rushing_touchdowns = Column(Integer, default=0)  # → player_tds_over (part of)
    
    receptions = Column(Integer, default=0)  # → player_receptions
    receiving_yards = Column(Float, default=0)  # → player_reception_yds
    receiving_targets = Column(Integer, default=0)  # (no direct prop market yet)
    receiving_touchdowns = Column(Integer, default=0)  # → player_tds_over (part of)
    
    # Defensive Stats (for defensive players)
    tackles_total = Column(Integer, default=0)  # Total tackles (solo + assisted)
    tackles_solo = Column(Integer, default=0)  # Solo tackles
    tackles_for_loss = Column(Integer, default=0)  # Tackles behind line of scrimmage
    sacks = Column(Float, default=0)  # Sacks (can be fractional for assisted)
    qb_hits = Column(Integer, default=0)  # QB hits (including sacks)
    interceptions_def = Column(Integer, default=0)  # Interceptions made
    pass_deflections = Column(Integer, default=0)  # Passes defended
    forced_fumbles = Column(Integer, default=0)  # Fumbles forced
    fumble_recoveries = Column(Integer, default=0)  # Fumbles recovered
    defensive_tds = Column(Integer, default=0)  # Pick-six, scoop-and-score, etc.
    safeties = Column(Integer, default=0)  # Safeties recorded
    
    # Additional Stats
    fumbles = Column(Integer, default=0)
    fumbles_lost = Column(Integer, default=0)
    snaps = Column(Integer)
    routes_run = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    player = relationship("Player", back_populates="stats")
    game = relationship("Game", back_populates="stats")


class StatsFeatures(Base):
    """Season averages and computed features for ML models (one record per player)"""
    __tablename__ = "stats_features"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, unique=True)
    player_name = Column(String, nullable=False)  # Denormalized for easier querying
    player_position = Column(String, nullable=True)  # Player position (QB, RB, WR, LB, CB, etc.) - Critical for AI to identify defensive players
    season = Column(Integer, nullable=False, default=2025)  # Season year (ESPN uses ending year)
    games_played = Column(Integer, default=0)  # Number of games with stats
    
    # Season Averages (per game)
    avg_passing_yards = Column(Float, default=0)
    avg_passing_tds = Column(Float, default=0)
    avg_interceptions = Column(Float, default=0)  # QB interceptions thrown (negative stat)
    avg_sacks_taken = Column(Float, default=0)  # Times QB was sacked (negative stat)
    avg_rushing_yards = Column(Float, default=0)
    avg_rushing_tds = Column(Float, default=0)
    avg_receiving_yards = Column(Float, default=0)
    avg_receiving_tds = Column(Float, default=0)
    avg_receptions = Column(Float, default=0)
    avg_targets = Column(Float, default=0)
    
    # Season Totals
    total_yards = Column(Float, default=0)  # Position-specific total yards
    total_tds = Column(Float, default=0)    # Position-specific total TDs
    total_interceptions = Column(Integer, default=0)  # Total INTs thrown by QB (negative)
    total_sacks_taken = Column(Float, default=0)  # Total times QB was sacked (negative)
    
    # Recent Form (last 3 games)
    last_3_avg_yards = Column(Float, default=0)
    last_3_avg_tds = Column(Float, default=0)
    
    # Consistency
    consistency_score = Column(Float, default=0)  # Coefficient of variation (inverse)
    
    # Home/Away Splits
    home_avg_yards = Column(Float, default=0)
    away_avg_yards = Column(Float, default=0)
    
    # Usage Metrics (for WR/TE)
    avg_target_share = Column(Float, default=0)  # Average % of team targets
    
    # Defensive Averages (for defensive players)
    avg_tackles = Column(Float, default=0)
    avg_sacks_def = Column(Float, default=0)  # Sacks made by defender (positive stat)
    avg_interceptions_def = Column(Float, default=0)  # INTs caught by defender (positive stat)
    avg_pass_deflections = Column(Float, default=0)
    avg_tackles_for_loss = Column(Float, default=0)
    total_tackles = Column(Integer, default=0)
    total_sacks_def = Column(Float, default=0)  # Total sacks made by defender
    total_interceptions_def = Column(Integer, default=0)  # Total INTs caught by defender
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to Player
    player = relationship("Player")


class Odds(Base):
    """Sportsbook odds for games and player props
    
    Supports ALL 46 verified player prop markets:
    - Passing: player_pass_yds, player_pass_tds, player_pass_completions, etc.
    - Rushing: player_rush_yds, player_rush_attempts, player_rush_longest, etc.
    - Receiving: player_reception_yds, player_receptions, player_reception_longest, etc.
    - Combined: player_pass_rush_yds, player_rush_reception_yds, player_pass_rush_reception_yds
    - Touchdowns: player_1st_td, player_anytime_td, player_last_td, player_tds_over, etc.
    - Kicking: player_field_goals, player_kicking_points, player_pats
    - Plus alternate lines and quarter/half-specific versions
    """
    __tablename__ = "odds"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)  # For player props
    
    # Odds Type
    market_type = Column(String, nullable=False)  # h2h, spreads, totals, player_props
    prop_type = Column(String)  # Stores one of 46 prop market keys (e.g., player_pass_yds, player_rush_yds)
    
    # Sportsbook
    bookmaker = Column(String, nullable=False)
    
    # Odds Data
    line = Column(Float)  # Spread/total line or prop line
    over_odds = Column(Integer)  # American odds for over
    under_odds = Column(Integer)  # American odds for under
    home_odds = Column(Integer)  # For moneyline
    away_odds = Column(Integer)  # For moneyline
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="odds")


class Matchup(Base):
    """Defensive matchup assignments (CB vs WR, LB vs TE, etc.)"""
    __tablename__ = "matchups"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    offensive_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    defensive_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    
    # Matchup Info
    matchup_type = Column(String)  # CB1_vs_WR1, Slot_CB_vs_Slot_WR, LB_vs_TE, etc.
    coverage_percentage = Column(Float)  # % of snaps defender covers this receiver
    
    # Defensive Stats Against
    yards_allowed_avg = Column(Float)
    catches_allowed_avg = Column(Float)
    touchdowns_allowed_avg = Column(Float)
    catch_rate_allowed = Column(Float)
    coverage_grade = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Injury(Base):
    """Player injury reports"""
    __tablename__ = "injuries"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player_name = Column(String, nullable=False)  # Denormalized for easier querying
    
    status = Column(String, nullable=False)  # Out, Questionable, Doubtful, Probable
    injury_type = Column(String)  # Knee, Ankle, Hamstring, etc.
    description = Column(Text)
    
    date_reported = Column(DateTime(timezone=True), nullable=False)
    date_updated = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    player = relationship("Player", back_populates="injuries")


class Prediction(Base):
    """ML model predictions for player stats
    
    Generates predictions for all major prop markets:
    - Passing: player_pass_yds, player_pass_tds, player_pass_completions, player_pass_attempts, player_pass_interceptions
    - Rushing: player_rush_yds, player_rush_attempts
    - Receiving: player_reception_yds, player_receptions
    - Combined: player_pass_rush_yds, player_rush_reception_yds
    - Touchdowns: player_tds_over, player_anytime_td (probability)
    
    The AI compares these predictions to bookmaker lines to find +EV betting opportunities.
    """
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Prediction Type (matches prop market keys)
    stat_type = Column(String, nullable=False)  # e.g., player_pass_yds, player_rush_yds, player_reception_yds
    prop_type = Column(String)  # More specific: passing_yards, rushing_yards, etc.
    bet_category = Column(String)  # single, combined, anytime_td - for learning which types hit more
    
    # Prediction Values
    predicted_value = Column(Float, nullable=False)
    predicted_over_prob = Column(Float)  # Probability of going over a line
    predicted_under_prob = Column(Float)  # Probability of going under
    confidence_score = Column(Float)
    variance_rating = Column(Float)
    
    # Line info (for tracking if we beat the line)
    line_used = Column(Float)  # The betting line we predicted against
    
    # Model Info
    model_version = Column(String)
    features_used = Column(JSON)
    
    # Actual Result (filled in after game)
    actual_value = Column(Float)
    prediction_error = Column(Float)
    was_accurate = Column(Boolean)  # Did prediction fall within acceptable range?
    hit_over = Column(Boolean)  # Did actual exceed the line? (for over/under tracking)
    
    # Season tracking
    season = Column(Integer, default=2025)
    week = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BetTypeAccuracy(Base):
    """
    Tracks historical accuracy by bet type - AI learns from this!
    
    The AI uses this to adjust confidence scores:
    - If combined stats hit at 72%, boost confidence for combined bets
    - If anytime TD for RBs with 0.8+ TD/game hits at 85%, boost those
    - If single stat passing yards only hits at 55%, reduce confidence
    """
    __tablename__ = "bet_type_accuracy"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # What we're tracking
    bet_category = Column(String, nullable=False)  # single, combined, anytime_td
    prop_type = Column(String)  # specific prop: passing_yards, rushing + receiving_yards, etc.
    position = Column(String)  # QB, RB, WR, TE - accuracy varies by position
    
    # Accuracy stats (rolling, updated after each game)
    total_predictions = Column(Integer, default=0)
    accurate_predictions = Column(Integer, default=0)
    total_hit_over = Column(Integer, default=0)  # Times the over hit
    accuracy_pct = Column(Float, default=50.0)  # Calculated accuracy percentage
    hit_rate = Column(Float, default=50.0)  # How often overs hit
    avg_error = Column(Float, default=0.0)  # Average prediction error
    
    # Confidence adjustment the AI should apply
    # Positive = boost confidence, Negative = reduce confidence
    confidence_adjustment = Column(Float, default=0.0)
    
    # Time tracking
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    season = Column(Integer, default=2025)


class PlayerHitRate(Base):
    """
    Tracks individual player tendencies - AI learns who's reliable!
    
    Examples:
    - "Derrick Henry hits rushing over 78% of the time" → boost his overs
    - "Tyreek Hill is boom/bust, only hits 45%" → reduce confidence
    - "Travis Kelce hits anytime TD at 60% when his avg is 0.7 TD/game"
    """
    __tablename__ = "player_hit_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # What prop we're tracking for this player
    prop_type = Column(String, nullable=False)  # passing_yards, rushing_yards, anytime_td, etc.
    
    # Hit rate stats
    total_games = Column(Integer, default=0)
    times_hit_over = Column(Integer, default=0)  # Times they exceeded their average/line
    hit_rate = Column(Float, default=50.0)  # Percentage
    
    # Consistency (lower = more consistent)
    avg_variance = Column(Float, default=0.0)  # How much they vary from their average
    
    # The adjustment AI should apply for this player/prop combo
    confidence_adjustment = Column(Float, default=0.0)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    season = Column(Integer, default=2025)
    
    # Relationship
    player = relationship("Player")

