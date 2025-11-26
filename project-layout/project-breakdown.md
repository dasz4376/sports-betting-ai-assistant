# 🧠🔥 Sports Betting Analytics AI — Full Project Breakdown

A fully autonomous, continuously learning sports analytics & betting insights AI that predicts outcomes, analyzes matchups, evaluates odds, understands defender vs offense matchups, and communicates like ChatGPT.

**Current Phase: NFL Only** (NBA support planned for future)

# 📚 1. Project Summary

This AI system:
- Pulls live player & team stats
- Learns player habits and tendencies
- Understands defensive matchups including shadow coverage
- Tracks injuries and depth chart changes
- Reads real sportsbook odds
- Predicts outcomes across all stat types
- Builds parlays and evaluates value
- Responds in natural language like ChatGPT
- Retrains weekly to become smarter over time

# ⚙️ 2. System Overview

The system contains:
1. Conversational Layer — Chat interface  
2. Data Layer — Stats + odds ingestion  
3. Feature Layer — Matchups, usage, trends  
4. Learning Layer — ML models  
5. Betting Layer — Odds evaluation + parlays  

# 🏈📈 3. Data Sources With Endpoints (All in One Place)

Below is a full, uninterrupted list of every endpoint used.

**Current Implementation: NFL Only**

# 🏈 ESPN NFL ENDPOINTS (STATS, PLAYERS, MATCHUPS)

All NFL teams:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams

Specific team (roster, stats):
https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{teamId}

Team depth chart:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{teamId}/depthchart

Team schedule:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{teamId}/schedule

NFL player profile:
https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/{playerId}

NFL player stats:
https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/{playerId}/statistics

NFL game summary / box score:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={gameId}

NFL injuries:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries

NFL scoreboard:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard


# 🏀 ESPN NBA ENDPOINTS (FUTURE IMPLEMENTATION)

All NBA teams:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams

Specific NBA team:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{teamId}

NBA player profile:
https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{playerId}

NBA player stats:
https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{playerId}/statistics

NBA game summary:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gameId}

NBA injuries:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries

NBA scoreboard:
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard


# 🎰 ODDS API ENDPOINTS (REAL SPORTSBOOK ODDS)

**Current Implementation: NFL Only**

List all sports:
https://api.the-odds-api.com/v4/sports/?apiKey=YOUR_API_KEY

NFL odds (moneyline, spread, totals):
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey=YOUR_API_KEY&regions=us&markets=h2h,spreads,totals

NFL player props:
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey=YOUR_API_KEY&regions=us&markets=player_props


# Supported OddsAPI Markets (NFL - Current Implementation)

h2h — Moneyline  
spreads — Spread bets  
totals — Over/Under  
player_props — All player props  
player_pass_yards — NFL passing yards  
player_rush_yards — NFL rushing yards  
player_rec_yards — NFL receiving yards  
player_receptions — NFL receptions  
player_td_scoring — NFL touchdowns  


# 🔁 4. Automated Data Pipeline

Stats updater:
- Pulls stats once daily at 11:59 PM
- Updates logs
- Computes rolling averages
- Updates usage metrics
- Captures all completed games from the day

Odds updater:
- Pulls odds every X time (11 AM, 3 PM, 5 PM, 7 PM, 8 PM)
- Tracks line movement
- Computes implied probabilities
- Optimized for API quota management

Database tables:
- players
- teams
- games
- stats_raw
- stats_features
- odds
- matchups
- injuries
- model_predictions

# 🧰 5. Feature Engineering (Matchup Intelligence)

Offensive features (NFL):
- Targets, touches, snaps, routes
- Rolling averages
- Trend slope
- Consistency score
- Red zone usage
- Home/away splits

Defensive features (NFL):
- Yards allowed
- Catch rate allowed
- TDs allowed
- Coverage grades
- Pressure rate (for QBs)
- Rush defense ranking

Matchup assignments (NFL):
- CB1 vs WR1
- Slot CB vs slot WR
- LB vs TE/RB
- Safety coverage vs deep threats
- Adjusts for injuries and rotations

Context features:
- Weather
- Home/away
- Spread & total
- Pace of play
- Rest days

# 🤖 6. Prediction Models

Prediction models per stat (NFL):
- Receptions
- Receiving yards
- Rushing yards
- Passing yards
- Passing completions
- Passing TDs
- Rushing TDs
- Receiving TDs
- Interceptions (for QBs)

Model types:
- XGBoost
- LightGBM
- Random Forest
- Neural Networks
- LSTM (optional)

Model outputs:
- Expected value
- Probability distribution
- Over/under probability
- Confidence score
- Variance rating

# 🔁 7. Continuous Learning Loop

Each game:
1. Insert new stats
2. Update features
3. Compare prediction vs actual
4. Log error
5. Retrain models weekly
6. Improve over time

# 🎰 8. Betting Engine

Odds intelligence:
- Converts odds formats
- Calculates implied probability
- Finds edges

Parlay builder:
- Filters legs by probability
- Avoids over-correlation
- Builds 2–6 leg parlays
- Supports target payouts

Explanation engine:
- Shows matchup reasoning
- Shows trends
- Shows injuries
- Shows probability breakdown

# 💬 9. Conversational Interface

User can ask:
- “Give me a safe 3-leg parlay.”
- “Who will score a TD?”
- “Is Player X in a good matchup?”
- “Build me a $5 → $200 parlay.”

AI responds like ChatGPT.

# 🛡️ 10. Safety / Legal
Entertainment only.  
No guaranteed wins.  
No automated betting.  
Encourages responsible use.

# 🚀 11. Optional Advanced Features
- Live in-game predictions
- Monte Carlo sims
- Defensive heatmaps
- Coaching tendencies
- SGP correlation maps
- Personalized profiles

# 🧾 12. Final Description

A fully autonomous, continuously learning NFL betting analytics AI that pulls live stats, analyzes matchups, predicts outcomes, evaluates sportsbook odds, and builds parlays with explanations through a ChatGPT-style interface. The system improves every week.

**Current Phase:** NFL implementation with daily stats updates (11:59 PM) and strategic odds updates around game times (11 AM, 3 PM, 5 PM, 7 PM, 8 PM).

**Future Expansion:** NBA support will be added in Phase 2.

