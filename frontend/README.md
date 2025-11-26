# NFL Betting AI - Frontend

Modern, beautiful React + TypeScript + TailwindCSS frontend for the NFL Betting AI.

## Features

- 🤖 **ChatGPT-Style Interface** - Natural language conversations with the AI
- 🎨 **Beautiful Dark Theme** - Optimized for betting (easy on the eyes)
- ⚡ **Real-time Predictions** - Get instant player prop predictions
- ⚔️ **Team Matchups** - Compare teams with detailed breakdowns
- 🏥 **Injury Reports** - Track player health status
- 📊 **Player Stats** - Historical and predictive statistics

## Tech Stack

- **React 18** - Modern UI library
- **TypeScript** - Type safety
- **Vite** - Lightning-fast build tool
- **TailwindCSS** - Utility-first styling
- **NFL Color Palette** - Custom theme matching NFL branding

## Getting Started

### Prerequisites
- Node.js 18+ installed
- Backend running on `http://localhost:8000`

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## API Configuration

The frontend connects to the backend at `http://localhost:8000/api/chat`

To change the API URL, edit `src/App.tsx`:

```typescript
const response = await fetch('http://YOUR_BACKEND_URL/api/chat', {
  // ...
})
```

## Quick Actions

The interface includes pre-built queries:
- 🏆 Top QBs
- ⚔️ Team Matchup
- 🏥 Injuries
- 📊 Predictions

## Chat Examples

Try asking:
- "How will AJ Brown do against the Bears?"
- "Compare Eagles vs Cowboys"
- "Who is injured on the Chiefs?"
- "Predict Saquon Barkley rushing yards"
- "Who will be defending Travis Kelce?"

## Customization

### Colors

Edit `tailwind.config.js` to customize the theme:

```js
colors: {
  'nfl-blue': '#013369',
  'betting-green': '#10b981',
  // ... add more colors
}
```

### Quick Actions

Edit the quick action buttons in `src/App.tsx` to add your own shortcuts.

## Development Tips

- Hot Module Replacement (HMR) is enabled for instant updates
- TypeScript will catch type errors before runtime
- The chat interface automatically scrolls to new messages
- Press Enter to send messages (Shift+Enter for new line)

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx          # Main chat interface component
│   ├── main.tsx         # App entry point
│   └── index.css        # Global styles + Tailwind
├── index.html           # HTML template
├── tailwind.config.js   # Tailwind configuration
├── tsconfig.json        # TypeScript configuration
└── vite.config.ts       # Vite configuration
```

## Troubleshooting

### Backend Connection Error
If you see "Connection error" messages:
1. Make sure the backend is running: `cd backend && uvicorn main:app --reload`
2. Check that it's accessible at `http://localhost:8000`
3. Verify CORS is enabled in the backend

### Styling Issues
If Tailwind classes don't work:
1. Make sure `npm install` completed successfully
2. Check that `postcss.config.js` exists
3. Restart the dev server

### TypeScript Errors
Run type checking: `npm run build`

## Future Enhancements

- [ ] Add prediction confidence meters
- [ ] Display team logos and player headshots
- [ ] Show live game scores
- [ ] Add betting odds comparison
- [ ] Multi-tab interface (chat, stats, matchups)
- [ ] Save chat history
- [ ] Export predictions to PDF

---

Built with ❤️ for smart sports betting

