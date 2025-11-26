# 🏈 NFL Betting AI - Full Stack Application

An AI-powered NFL betting assistant that provides data-driven predictions, matchup analysis, and injury reports through a beautiful ChatGPT-style interface.

## 🎯 Features

### Backend (Python/FastAPI)
- ✅ **21 Trained ML Models** (XGBoost, LightGBM, Random Forest)
- ✅ **Matchup-Aware Predictions** (factors in opponent defense)
- ✅ **Injury-Aware Analysis** (weighted by severity)
- ✅ **Continuous Learning** (self-improving with post-game analysis)
- ✅ **Automated Data Updates** (daily stats, weekly retraining)
- ✅ **Comprehensive API** (RESTful endpoints for all features)

### Frontend (React/TypeScript)
- ✅ **ChatGPT-Style Interface** (natural language conversations)
- ✅ **Modern Dark Theme** (optimized for sports betting)
- ✅ **Real-time Predictions** (instant ML-powered insights)
- ✅ **Beautiful UI** (TailwindCSS with glassmorphism effects)
- ✅ **Quick Actions** (pre-built common queries)
- ✅ **Responsive Design** (works on all devices)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL database
- Google Gemini API key

### 1. Clone & Setup Environment

```bash
# Navigate to project
cd "d:\Autonomi(My Last Chance)"

# Backend setup
cd backend
cp .env.example .env  # Edit with your API keys

# Frontend setup (already done)
cd ../frontend
```

### 2. Start the Application

**Option A: Single Command (Recommended)**
```bash
py start.py
```
This starts both backend and frontend. Press `Ctrl+C` to stop all servers.

**Option B: Use the Batch File**
```bash
# Double-click START_APP.bat or:
START_APP.bat
```

**Option C: Manual Start**

Terminal 1 - Backend:
```bash
cd backend
py start_api_only.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### 3. Access the App

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## 💬 Using the AI

### Chat Interface

Open http://localhost:5173 and start chatting!

**Example Questions:**
```
How will AJ Brown do against the Bears?
Compare Eagles vs Cowboys
Who is injured on the Chiefs?
Predict Saquon Barkley rushing yards
Who will be defending Travis Kelce?
Show me the top QBs this week
```

### Quick Actions

Use the pre-built buttons:
- 🏆 **Top QBs** - See highest-performing quarterbacks
- ⚔️ **Team Matchup** - Compare two teams
- 🏥 **Injuries** - View current injury reports
- 📊 **Predictions** - Get player predictions

---

## 📊 What the AI Can Do

### Player Predictions
- Passing yards/TDs
- Rushing yards/TDs
- Receiving yards/TDs/receptions
- Defensive stats (tackles, sacks, interceptions)

### Team Analysis
- Head-to-head matchups
- Offensive/defensive breakdowns
- Win probability predictions
- Season records and momentum

### Matchup Intelligence
- Which CBs will cover which receivers
- Opponent defensive strengths/weaknesses
- Injury impact on matchups
- Historical trends

### Data Queries
- Player season stats
- Team rosters by position
- Current injury reports
- Upcoming game schedules

---

## 🏗️ Project Structure

```
d:\Autonomi(My Last Chance)/
├── backend/                    # Python/FastAPI backend
│   ├── services/
│   │   ├── chat_ai_v3.py      # Gemini-powered chat
│   │   ├── predictor.py       # ML models (BettingAI)
│   │   ├── matchup_analyzer.py # Matchup intelligence
│   │   ├── continuous_learning.py # Post-game analysis
│   │   └── scheduler.py       # Automated updates
│   ├── models.py              # Database models
│   ├── main.py                # FastAPI app
│   └── trained_models/        # Saved ML models
│
├── frontend/                   # React/TypeScript frontend
│   ├── src/
│   │   ├── App.tsx            # Main chat interface
│   │   ├── main.tsx           # App entry
│   │   └── index.css          # Tailwind styles
│   ├── tailwind.config.js     # Custom theme
│   └── vite.config.ts         # Vite configuration
│
├── start.py                   # Single-command startup (recommended)
├── START_APP.bat              # Batch file startup
└── README.md                  # This file
```

---

## 🎨 Frontend Customization

### Colors (tailwind.config.js)
```js
colors: {
  'nfl-blue': '#013369',      // NFL primary
  'betting-green': '#10b981',  // Win/positive
  'betting-red': '#ef4444',    // Loss/negative
  'dark-bg': '#0f172a',        // Background
  'dark-card': '#1e293b',      // Cards
}
```

### Quick Actions (App.tsx)
Add your own shortcuts in the quick actions section.

---

## 🔧 Configuration

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:PASSWORD@localhost/nfl_betting_ai
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
ODDS_API_KEY=your_odds_api_key_here  # Optional
```

### Frontend
API URL is hardcoded in `src/App.tsx`. Change if deploying:
```typescript
const response = await fetch('http://localhost:8000/api/chat', {
```

---

## 📈 Data Updates

### Automated Schedule
- **Daily (11:59 PM):** Stats update
- **Daily (12:00 PM):** Injury reports
- **Weekly (Tuesday 3 AM):** Model retraining
- **Weekly (Tuesday 4 AM):** Continuous learning analysis

### Manual Updates
```bash
cd backend

# Update stats
py update_stats.py

# Retrain models
py train_all_21_props.py

# Run continuous learning
py run_continuous_learning.py
```

---

## 🧪 Testing

### Backend
```bash
cd backend
py -m pytest  # If tests are set up
```

### Frontend
```bash
cd frontend
npm run build  # Type checking
npm run preview  # Test production build
```

---

## 🚢 Deployment

### Backend (FastAPI)
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Consider using:
- **Gunicorn** for production WSGI server
- **Docker** for containerization
- **Nginx** for reverse proxy

### Frontend (React)
```bash
cd frontend
npm run build
# Deploy the 'dist' folder to:
# - Vercel
# - Netlify
# - AWS S3 + CloudFront
```

Update API URL in build to point to production backend.

---

## 🐛 Troubleshooting

### "Connection error" in frontend
1. Check backend is running: `http://localhost:8000`
2. Verify CORS is enabled (already configured)
3. Check browser console for errors

### Database errors
1. Ensure PostgreSQL is running
2. Check DATABASE_URL in `.env`
3. Run migrations: `cd backend && alembic upgrade head`

### Gemini API errors
1. Verify GOOGLE_GEMINI_API_KEY is set
2. Check API quota/limits
3. Ensure billing is enabled

### Missing predictions
1. Check if models are trained: `ls backend/trained_models/`
2. Train models: `cd backend && py train_all_21_props.py`
3. Check data is loaded: Query database

---

## 📝 TODO / Future Enhancements

- [ ] Add user authentication
- [ ] Save chat history
- [ ] Display team logos and player headshots
- [ ] Add betting odds (re-enable Odds API)
- [ ] Export predictions to PDF
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Live game updates
- [ ] Push notifications for predictions

---

## 🤝 Contributing

This is a personal project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

Private project - All rights reserved

---

## 🙏 Acknowledgments

- **ESPN API** - Player and game data
- **Google Gemini** - Conversational AI
- **The Odds API** - Betting odds (optional)
- **Tailwind Labs** - Beautiful UI framework
- **Vite Team** - Lightning-fast build tool

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review backend logs
3. Check browser console
4. Ensure all dependencies are installed

---

**Built with ❤️ for smart sports betting**

**Stack:** Python • FastAPI • PostgreSQL • React • TypeScript • TailwindCSS • Machine Learning

**Status:** ✅ Production Ready
