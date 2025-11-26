# 🚀 Quick Setup Guide

Get your NFL Betting AI running in 5 minutes!

## Step 1: Install Prerequisites

### Python
Download Python 3.10 or newer from [python.org](https://www.python.org/downloads/)

### PostgreSQL
Download PostgreSQL from [postgresql.org](https://www.postgresql.org/download/)

Or use Docker:
```bash
docker run --name nfl-betting-db -e POSTGRES_PASSWORD=mypassword -e POSTGRES_DB=nfl_betting_ai -p 5432:5432 -d postgres:14
```

### Get API Key
1. Visit [The Odds API](https://the-odds-api.com/)
2. Sign up for free account
3. Get your API key (500 requests/month free)

## Step 2: Backend Setup

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Configure Environment
Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/nfl_betting_ai
ODDS_API_KEY=paste_your_key_here
ENVIRONMENT=development
DEBUG=True
STATS_UPDATE_TIME=23:59
ODDS_UPDATE_TIMES=11:00,15:00,17:00,19:00,20:00
TIMEZONE=America/New_York
```

### Create Database
If not using Docker:
```bash
createdb nfl_betting_ai
```

Or in PostgreSQL:
```sql
CREATE DATABASE nfl_betting_ai;
```

## Step 3: Run the Application

```bash
cd backend
python main.py
```

You should see:
```
Starting NFL Betting AI Backend...
Initializing database...
Starting data scheduler...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Verify It's Working

### Check API Documentation
Open your browser to: **http://localhost:8000/docs**

You should see the interactive Swagger UI with all API endpoints.

### Test Endpoints

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Get Teams:**
```bash
curl http://localhost:8000/api/teams
```

**Trigger Initial Data Load:**
```bash
curl -X POST http://localhost:8000/api/admin/update-stats
curl -X POST http://localhost:8000/api/admin/update-odds
```

## Step 5: Initial Data Population

The scheduler will automatically pull data at the configured times:
- **Stats:** 11:59 PM daily
- **Odds:** 11 AM, 3 PM, 5 PM, 7 PM, 8 PM

Just leave the server running and it will collect data going forward!

### Manual Trigger (Optional)

You can also trigger updates manually to get started immediately:

```bash
# In another terminal window:
curl -X POST http://localhost:8000/api/admin/update-stats
curl -X POST http://localhost:8000/api/admin/update-odds
```

Watch the server logs to see progress.

## Step 6: Verify Data Loaded

Check that data is in the database:

```bash
# Get teams
curl http://localhost:8000/api/teams

# Get players
curl http://localhost:8000/api/players?position=QB

# Get injuries
curl http://localhost:8000/api/injuries

# Get current games
curl http://localhost:8000/api/games
```

## Step 7: Train ML Models (Once You Have Data)

After running for a few days and accumulating stats:

```bash
cd backend
python -c "
from database import SessionLocal
from services.predictor import StatPredictor

db = SessionLocal()
predictor = StatPredictor(db)
predictor.retrain_all_models()
db.close()
"
```

## 🎯 You're Ready!

Your NFL Betting AI is now running! Here's what happens automatically:

✅ **Every Day at 11:59 PM**: Updates teams, players, games, injuries, stats  
✅ **5 Times Daily**: Updates odds for upcoming games  
✅ **Weekly**: Retrains ML models (once set up)  
✅ **Always**: Generates predictions and finds betting edges  

## 📊 Next Steps

### Explore the API
- Visit http://localhost:8000/docs
- Try different endpoints
- Filter by position, team, season, week

### Test Individual Components
```bash
cd backend

# Test ESPN fetcher
python services/espn_fetcher.py

# Test Odds API
python services/odds_fetcher.py

# Test feature engineering
python services/feature_engineer.py

# Test betting engine
python services/betting_engine.py
```

### Monitor Logs
Watch the console for scheduled job execution and any errors.

### Check Database
Connect to PostgreSQL and explore the tables:
```sql
\c nfl_betting_ai
\dt  -- List all tables
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM players;
SELECT COUNT(*) FROM games;
SELECT COUNT(*) FROM player_stats;
```

## ⚠️ Troubleshooting

### Can't Connect to Database
- Check PostgreSQL is running: `pg_isready`
- Verify connection string in `.env`
- Check firewall/permissions

### API Key Not Working
- Verify key is correct in `.env`
- Check quota at https://the-odds-api.com/account
- Ensure no extra spaces in key

### Import Errors
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (need 3.10+)

### No Data Loading
- Check API endpoints are accessible
- Verify network connection
- Check scheduler logs for errors
- Try manual trigger: `POST /api/admin/update-stats`

### Port Already in Use
- Change port in main.py: `uvicorn.run("main:app", port=8001)`
- Or kill process on port 8000: `lsof -ti:8000 | xargs kill`

## 🎓 Learning Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **The Odds API Docs**: https://the-odds-api.com/liveapi/guides/v4/
- **ESPN API**: No official docs, but endpoints are discoverable

## 💬 Need Help?

Refer to:
- `README.md` - Full project documentation
- `backend/README.md` - Backend-specific details
- `project-layout/project-breakdown.md` - Original project specs

## 🎉 Success Checklist

- [ ] Python 3.10+ installed
- [ ] PostgreSQL running
- [ ] Backend dependencies installed
- [ ] .env file configured with API key
- [ ] Database created
- [ ] Server starts without errors
- [ ] Can access API docs at localhost:8000/docs
- [ ] Data loading (manually or scheduled)
- [ ] Teams/players visible in API responses
- [ ] Ready to train ML models!

---

**You're all set! Let the system run and accumulate data. The AI gets smarter every week! 🚀**

