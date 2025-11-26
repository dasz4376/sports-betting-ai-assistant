import { useState, useRef, useEffect } from 'react'
import './index.css'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface Game {
  id: number
  home: string
  home_name: string
  away: string
  away_name: string
  time: string
  date: string
  day: string
  spread: string | null
  week: number
  event: string | null
}

interface TrendingPlayer {
  id: number
  name: string
  team: string
  position: string
  stat: string
  trend: 'up' | 'down'
}

interface Insight {
  type: string
  color: string
  title: string
  message: string
}

interface DashboardStats {
  models_count: number
  current_week: number
  current_season: number
  players_tracked: number
  teams: number
  games_this_season: number
  odds_records: number
  status: string
}

const API_BASE = 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const [upcomingGames, setUpcomingGames] = useState<Game[]>([])
  const [trendingPlayers, setTrendingPlayers] = useState<TrendingPlayer[]>([])
  const [insights, setInsights] = useState<Insight[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [dashboardLoading, setDashboardLoading] = useState(true)

  useEffect(() => {
    const fetchDashboardData = async () => {
      setDashboardLoading(true)
      try {
        const [gamesRes, playersRes, insightsRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/dashboard/upcoming-games`),
          fetch(`${API_BASE}/api/dashboard/trending-players`),
          fetch(`${API_BASE}/api/dashboard/insights`),
          fetch(`${API_BASE}/api/dashboard/stats`)
        ])
        
        if (gamesRes.ok) {
          const data = await gamesRes.json()
          setUpcomingGames(data.games || [])
        }
        if (playersRes.ok) {
          const data = await playersRes.json()
          setTrendingPlayers(data.players || [])
        }
        if (insightsRes.ok) {
          const data = await insightsRes.json()
          setInsights(data.insights || [])
        }
        if (statsRes.ok) {
          setStats(await statsRes.json())
        }
      } catch (error) {
        console.error('Error:', error)
      } finally {
        setDashboardLoading(false)
      }
    }
    
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (customMessage?: string) => {
    const messageText = customMessage || input
    if (!messageText.trim() || isLoading) return

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date()
    }])
    setInput('')
    setIsLoading(true)
    setChatOpen(true)

    try {
      // Build messages array for the API (including the new user message)
      const apiMessages = [
        ...messages.map(m => ({ role: m.role, content: m.content })),
        { role: 'user', content: messageText }
      ]
      
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages })
      })

      const data = await response.json()
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || data.detail || 'I processed your request.',
        timestamp: new Date()
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error.',
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  // Separate games by type
  const thanksgivingGames = upcomingGames.filter(g => g.event === 'Thanksgiving')
  const otherGames = upcomingGames.filter(g => g.event !== 'Thanksgiving')

  return (
    <div className="min-h-screen bg-[#0B0F1A]">
      {/* Animated Games Ticker Banner */}
      {upcomingGames.length > 0 && (
        <div className="bg-[#060911] border-b border-white/5 overflow-hidden">
          <div className="flex items-center">
            {/* Label */}
            <div className="flex-shrink-0 bg-emerald-500 text-black text-xs font-bold px-4 py-2 z-10">
              {thanksgivingGames.length > 0 ? '🦃 THANKSGIVING' : `WEEK ${stats?.current_week}`}
            </div>
            
            {/* Auto-scrolling ticker */}
            <div className="flex-1 overflow-hidden relative">
              <div className="animate-ticker flex items-center gap-8 py-2 whitespace-nowrap">
                {/* Duplicate games for seamless loop */}
                {[...upcomingGames, ...upcomingGames].map((game, i) => (
                  <div 
                    key={`${game.id}-${i}`}
                    onClick={() => sendMessage(`analyze ${game.away_name} vs ${game.home_name}`)}
                    className="flex items-center gap-3 cursor-pointer hover:text-emerald-400 transition-colors group"
                  >
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      game.event === 'Thanksgiving' ? 'bg-amber-500/20 text-amber-400' : 'bg-white/5 text-gray-500'
                    }`}>
                      {game.event === 'Thanksgiving' ? '🦃 THU' : game.day?.slice(0,3).toUpperCase()}
                    </span>
                    <span className="text-sm font-semibold text-white group-hover:text-emerald-400">{game.away}</span>
                    <span className="text-xs text-gray-600">vs</span>
                    <span className="text-sm font-semibold text-white group-hover:text-emerald-400">{game.home}</span>
                    <span className="text-xs text-emerald-400 font-mono">{game.time}</span>
                    <span className="text-gray-700">•</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sticky Header */}
      <header className="sticky top-0 z-40 bg-[#0B0F1A]/95 backdrop-blur-md border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-400 flex items-center justify-center text-base">
              🏈
            </div>
            <span className="font-semibold text-white">Autonomi AI</span>
            <span className={`text-xs ${stats?.status === 'online' ? 'text-emerald-400' : 'text-gray-500'}`}>
              ● {stats?.status === 'online' ? 'Live' : 'Offline'}
            </span>
          </div>
          
          <button 
            onClick={() => setChatOpen(true)}
            className="bg-white/5 hover:bg-white/10 text-white font-medium px-4 py-2 rounded-lg text-sm transition-colors border border-white/10 flex items-center gap-2"
          >
            <span>💬</span> Chat with AI
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Hero Section with Week Display */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="bg-emerald-500 text-black text-xs font-bold px-3 py-1 rounded">
                WEEK {stats?.current_week}
              </div>
              <span className="text-gray-500 text-sm">{stats?.current_season} NFL Season</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">
              {thanksgivingGames.length > 0 ? '🦃 Thanksgiving Week' : 'Your Betting Edge'}
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {stats?.models_count} ML models • {stats?.players_tracked?.toLocaleString()} players tracked
            </p>
          </div>
          <div className="hidden md:flex items-center gap-3">
            <button 
              onClick={() => sendMessage('give me a parlay')}
              className="bg-emerald-500 hover:bg-emerald-400 text-black font-medium px-5 py-2.5 rounded-lg text-sm transition-colors"
            >
              🎯 Quick Parlay
            </button>
            <button 
              onClick={() => sendMessage('find value bets')}
              className="bg-white/5 hover:bg-white/10 text-white font-medium px-5 py-2.5 rounded-lg text-sm transition-colors border border-white/10"
            >
              💰 Value Bets
            </button>
          </div>
        </div>

        {/* Thanksgiving Games - Only if there are any */}
        {thanksgivingGames.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">🦃</span>
              <h2 className="text-lg font-semibold text-white">Thanksgiving Games</h2>
              <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">Tomorrow</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {thanksgivingGames.map((game) => (
                <div 
                  key={game.id}
                  onClick={() => sendMessage(`analyze ${game.away_name} vs ${game.home_name}`)}
                  className="bg-gradient-to-br from-amber-500/10 to-orange-500/5 border border-amber-500/20 rounded-xl p-5 cursor-pointer hover:border-amber-500/40 transition-all group"
                >
                  <div className="flex justify-between items-center text-xs text-amber-400 mb-4">
                    <span>🦃 Thanksgiving</span>
                    <span className="font-mono">{game.time}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-center flex-1">
                      <div className="text-2xl font-bold text-white group-hover:text-amber-400 transition-colors">{game.away}</div>
                      <div className="text-xs text-gray-500 mt-1 truncate">{game.away_name}</div>
                    </div>
                    <div className="text-gray-600 text-sm px-3">@</div>
                    <div className="text-center flex-1">
                      <div className="text-2xl font-bold text-white group-hover:text-amber-400 transition-colors">{game.home}</div>
                      <div className="text-xs text-gray-500 mt-1 truncate">{game.home_name}</div>
                    </div>
                  </div>
                  {game.spread && (
                    <div className="mt-4 text-center">
                      <span className="text-xs bg-black/30 text-gray-400 px-3 py-1 rounded-full">{game.spread}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Quick Actions</h3>
              <div className="space-y-2">
                {[
                  { icon: '🎯', label: 'Build a Parlay', query: 'give me a 5 leg parlay' },
                  { icon: '💰', label: 'Find Value Bets', query: 'find me value bets' },
                  { icon: '📊', label: 'Top Quarterbacks', query: 'who are the top QBs' },
                  { icon: '🏥', label: 'Injury Report', query: 'show injury report' },
                ].map((action, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(action.query)}
                    className="w-full flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.05] border border-transparent hover:border-white/10 transition-all text-left"
                  >
                    <span className="text-lg">{action.icon}</span>
                    <span className="text-sm text-gray-300">{action.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Trending Players */}
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-400">Trending Players</h3>
                <span className="text-xs text-emerald-400">● Live</span>
              </div>
              {dashboardLoading ? (
                <div className="space-y-3">
                  {[1,2,3,4].map(i => <div key={i} className="h-12 bg-white/5 rounded-lg animate-pulse"></div>)}
                </div>
              ) : trendingPlayers.length > 0 ? (
                <div className="space-y-2">
                  {trendingPlayers.map((player) => (
                    <div 
                      key={player.id}
                      onClick={() => sendMessage(`predict ${player.name} stats`)}
                      className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/[0.03] cursor-pointer transition-colors"
                    >
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center text-xs font-bold text-emerald-400">
                        {player.team}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">{player.name}</div>
                        <div className="text-xs text-gray-500">{player.stat}</div>
                      </div>
                      <span className={`text-sm ${player.trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {player.trend === 'up' ? '↑' : '↓'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No data available</p>
              )}
            </div>
          </div>

          {/* Center & Right - Other Games + Insights */}
          <div className="lg:col-span-2 space-y-6">
            {/* Week Games */}
            {otherGames.length > 0 && (
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Week {stats?.current_week} Games</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {otherGames.slice(0, 9).map((game) => (
                    <div 
                      key={game.id}
                      onClick={() => sendMessage(`analyze ${game.away_name} vs ${game.home_name}`)}
                      className="bg-white/[0.02] border border-white/5 rounded-lg p-3 cursor-pointer hover:border-emerald-500/30 transition-all"
                    >
                      <div className="flex justify-between items-center text-xs text-gray-500 mb-2">
                        <span>{game.day}</span>
                        <span className="text-emerald-400 font-mono">{game.time}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-white">{game.away}</span>
                        <span className="text-gray-600">@</span>
                        <span className="font-semibold text-white">{game.home}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Insights */}
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5">
              <h3 className="text-sm font-medium text-gray-400 mb-4">AI Insights</h3>
              {dashboardLoading ? (
                <div className="space-y-3">
                  {[1,2,3].map(i => <div key={i} className="h-16 bg-white/5 rounded-lg animate-pulse"></div>)}
                </div>
              ) : insights.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {insights.map((insight, i) => (
                    <div 
                      key={i}
                      className={`p-4 rounded-lg border ${
                        insight.color === 'green' ? 'bg-emerald-500/10 border-emerald-500/20' :
                        insight.color === 'red' ? 'bg-red-500/10 border-red-500/20' :
                        'bg-amber-500/10 border-amber-500/20'
                      }`}
                    >
                      <div className={`text-xs font-semibold mb-1 ${
                        insight.color === 'green' ? 'text-emerald-400' :
                        insight.color === 'red' ? 'text-red-400' :
                        'text-amber-400'
                      }`}>
                        {insight.title}
                      </div>
                      <div className="text-sm text-gray-300">{insight.message}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No insights available</p>
              )}
            </div>

            {/* Features */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 text-center">
                <div className="text-2xl mb-2">🎯</div>
                <div className="text-xs text-gray-400">Smart Parlays</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 text-center">
                <div className="text-2xl mb-2">📈</div>
                <div className="text-xs text-gray-400">ML Predictions</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 text-center">
                <div className="text-2xl mb-2">💡</div>
                <div className="text-xs text-gray-400">Value Detection</div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Chat Button */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 shadow-lg shadow-emerald-500/25 flex items-center justify-center text-xl hover:scale-110 transition-transform z-50"
        >
          💬
        </button>
      )}

      {/* Chat Panel */}
      <div className={`fixed inset-y-0 right-0 w-full md:w-[420px] bg-[#0B0F1A] border-l border-white/5 transform transition-transform duration-300 z-50 ${chatOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-sm">
              🤖
            </div>
            <div>
              <div className="font-medium text-white text-sm">Autonomi AI</div>
              <div className="text-xs text-gray-500">NFL Assistant</div>
            </div>
          </div>
          <button 
            onClick={() => setChatOpen(false)}
            className="w-8 h-8 rounded-lg hover:bg-white/5 flex items-center justify-center text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="overflow-y-auto p-4 space-y-4" style={{ height: 'calc(100vh - 140px)' }}>
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-3xl mb-3">🏈</div>
              <p className="text-sm text-gray-500 mb-6">Ask me about parlays, predictions, or matchups</p>
              <div className="space-y-2">
                {['Give me a thanksgiving parlay', 'Top rushing yards this week', 'Chiefs vs Cowboys analysis'].map((q, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(q)}
                    className="w-full text-left p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                    msg.role === 'user' 
                      ? 'bg-emerald-500 text-black' 
                      : 'bg-white/[0.05] text-gray-200'
                  }`}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white/[0.05] rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                      <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <div className="p-4 border-t border-white/5">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
              placeholder="Ask anything..."
              className="flex-1 bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-black font-medium px-4 rounded-xl transition-colors"
            >
              ↑
            </button>
          </div>
        </div>
      </div>

      {chatOpen && <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setChatOpen(false)} />}
    </div>
  )
}

export default App
