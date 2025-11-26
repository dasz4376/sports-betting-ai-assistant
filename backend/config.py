"""
Configuration settings for the NFL Betting AI backend
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/nfl_betting_ai"
    
    # API Keys
    ODDS_API_KEY: str = ""
    GOOGLE_GEMINI_API_KEY: str = ""
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Scheduler Settings
    STATS_UPDATE_TIME: str = "23:59"  # 11:59 PM daily stats update
    ODDS_UPDATE_TIMES: str = "12:00,15:00,19:00"  # 3 updates on game days only (saves API credits)
    
    # Timezone
    TIMEZONE: str = "America/New_York"
    
    # NFL Season Settings
    CURRENT_SEASON: int = 2025  # ESPN uses ending year (2024-2025 season = 2025)
    CURRENT_WEEK: int = 13  # Updated for Thanksgiving week
    
    # ESPN API
    ESPN_BASE_URL: str = "https://site.api.espn.com/apis/site/v2"
    ESPN_CORE_URL: str = "https://sports.core.api.espn.com/v2"
    
    # The Odds API
    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"
    ODDS_API_REGION: str = "us"
    ODDS_API_MARKETS: str = "h2h,spreads,totals"
    
    # Player Prop Markets - 15 core markets optimized for API quota
    # Cost: 10 × 15 markets × 1 region = 150 credits per request
    # With $30/month plan (20,000 credits): ~133 requests = 4-5 per day
    ODDS_API_PROP_MARKETS: str = "player_anytime_td,player_tds_over,player_pass_tds,player_pass_yds,player_pass_completions,player_pass_attempts,player_pass_interceptions,player_rush_yds,player_reception_yds,player_receptions,player_pass_rush_yds,player_rush_reception_yds,player_field_goals,player_kicking_points,player_pats"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

