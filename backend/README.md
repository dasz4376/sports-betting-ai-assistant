# 🏈 NFL Betting AI - Backend

Backend system for the NFL Betting Analytics AI - handles data ingestion, storage, feature engineering, ML predictions, and betting insights.

## 🎯 Features

- **Automated Data Pipeline**: Daily stats updates (11:59 PM) and game-time odds updates (11 AM, 3 PM, 5 PM, 7 PM, 8 PM)
- **ESPN Integration**: Teams, players, stats, injuries, depth charts, and game results
- **Odds API Integration**: Real-time NFL odds and player props from multiple sportsbooks
- **RESTful API**: FastAPI endpoints for frontend consumption
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Scheduled Jobs**: APScheduler for automated updates

## 📦 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **HTTP Client**: httpx (async)
- **Scheduler**: APScheduler
- **ML Libraries**: scikit-learn, XGBoost, LightGBM (ready for Phase 2)

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- The Odds API key (get free key at https://the-odds-api.com/)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Database

Create a PostgreSQL database:

```bash
createdb nfl_betting_ai
```

### 3. Configure Environment

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/nfl_betting_ai

# API Keys
ODDS_API_KEY=your_odds_api_key_here

# Application
ENVIRONMENT=development
DEBUG=True

# Scheduler
STATS_UPDATE_TIME=23:59
ODDS_UPDATE_TIMES=11:00,15:00,17:00,19:00,20:00

# Timezone
TIMEZONE=America/New_York
```

### 4. Run the Application

```bash
python main.py
```

The server will start at: http://localhost:8000

### 5. View API Documentation

FastAPI automatically generates interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📁 Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── database.py            # Database connection and session management
├── models.py              # SQLAlchemy database models
├── requirements.txt       # Python dependencies
├── services/              # Business logic services
│   ├── espn_fetcher.py   # ESPN API data fetcher
│   ├── odds_fetcher.py   # The Odds API fetcher
│   └── scheduler.py       # Automated data update scheduler
└── README.md             # This file
```

## 🗄️ Database Schema

### Core Tables

- **teams**: NFL teams with conference/division info
- **players**: Player profiles with position, team, status
- **games**: Game schedule, scores, and status
- **player_stats**: Raw player statistics per game
- **stats_features**: Engineered features (rolling averages, trends)
- **odds**: Game odds and player props from sportsbooks
- **matchups**: Defensive matchup assignments (CB vs WR, etc.)
- **injuries**: Injury reports with status
- **predictions**: ML model predictions and results

## 🔄 Data Update Schedule

### Stats Updates (11:59 PM Daily)
- Teams and rosters
- Injury reports
- Game results and scores
- Player statistics for completed games

### Odds Updates (Game-Time Optimized)
- **11 AM**: Early line movements, Sunday morning updates
- **3 PM**: Pre-game adjustments (1 PM ET games starting)
- **5 PM**: Live adjustments during afternoon games
- **7 PM**: Pre-prime time updates
- **8 PM**: Sunday/Monday Night Football updates

## 🔌 API Endpoints

### Teams
- `GET /api/teams` - List all teams
- `GET /api/teams/{id}` - Get team details
- `GET /api/teams/{id}/players` - Get team roster

### Players
- `GET /api/players?position=QB&team_id=1` - List players (with filters)
- `GET /api/players/{id}` - Get player details

### Games
- `GET /api/games?season=2024&week=12` - List games (with filters)
- `GET /api/games/{id}` - Get game details

### Injuries
- `GET /api/injuries?team_id=1&active_only=true` - Get injury reports

### Odds
- `GET /api/odds/games?market_type=spreads` - Get game odds
- `GET /api/odds/props?prop_type=player_pass_yards` - Get player props

### Admin (Testing)
- `POST /api/admin/update-stats` - Manually trigger stats update
- `POST /api/admin/update-odds` - Manually trigger odds update

## 🧪 Testing the Fetchers

Test ESPN API integration:
```bash
python services/espn_fetcher.py
```

Test Odds API integration:
```bash
python services/odds_fetcher.py
```

Run the scheduler standalone:
```bash
python services/scheduler.py
```

## 📊 Current Implementation Status

### ✅ Phase 1: Data Foundation (COMPLETED)
- [x] Database schema
- [x] ESPN NFL data fetchers
- [x] Odds API fetchers
- [x] Scheduled data updates
- [x] FastAPI REST endpoints

### 🔨 Phase 2: Intelligence Layer (NEXT)
- [ ] Feature engineering (rolling averages, matchups)
- [ ] ML model training for stat predictions
- [ ] Prediction storage and evaluation
- [ ] Continuous learning loop

### 📋 Phase 3: Betting Logic (PLANNED)
- [ ] Edge detection (model predictions vs odds)
- [ ] Parlay builder with correlation avoidance
- [ ] Value bet identification
- [ ] Explanation engine

### 🤖 Phase 4: Conversational Interface (PLANNED)
- [ ] ChatGPT-style interface
- [ ] Natural language query processing
- [ ] Conversational betting recommendations

## 🔑 API Keys

### The Odds API
Get your free API key at: https://the-odds-api.com/
- Free tier: 500 requests/month
- Our schedule uses ~20-30 requests/day
- Recommended: $30-50/month plan for full coverage

### ESPN APIs
ESPN's public APIs are free and don't require authentication.

## ⚠️ Important Notes

### Rate Limiting
- ESPN: We add 0.5-1 second delays between requests to be respectful
- Odds API: Limited by your plan's quota - monitor remaining requests

### Database Maintenance
- Consider setting up automated backups
- Plan for database migrations (use Alembic)
- Index frequently queried columns for performance

### Production Deployment
- Update CORS origins in `main.py`
- Set DEBUG=False in production
- Use environment variables for sensitive data
- Set up proper logging
- Consider using Gunicorn/Uvicorn workers

## 📈 Next Steps

1. **Start the server**: `python main.py` - scheduler begins collecting data automatically
2. **Monitor logs**: Check that data updates run successfully
3. **Accumulate data**: Let it run for several weeks to build training dataset
4. **Train ML models**: Once you have sufficient data (Week 3+)
5. **Build frontend**: Create ChatGPT-style interface (Phase 4)

> **Note:** Models need at least 50 games of data per position to train effectively. The system will collect data automatically - just let it run!

## 🤝 Contributing

This is a private project. For questions or issues, refer to the project breakdown document.

## 📄 License

Private project - All rights reserved.

---

**Made with 🔥 for NFL analytics and betting insights**

