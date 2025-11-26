interface TeamMatchupProps {
  team1: {
    name: string
    record: string
    predicted_score: number
    win_probability: number
    offense_yards: number
    defense_rating: number
  }
  team2: {
    name: string
    record: string
    predicted_score: number
    win_probability: number
    offense_yards: number
    defense_rating: number
  }
  scheduled: boolean
  week?: number
  date?: string
}

export function TeamMatchupCard({
  team1,
  team2,
  scheduled,
  week,
  date
}: TeamMatchupProps) {
  const team1Favored = team1.win_probability > team2.win_probability

  return (
    <div className="glass rounded-xl p-6 border border-dark-border animate-slide-up">
      {/* Game Info */}
      {scheduled && (
        <div className="text-center mb-4 pb-4 border-b border-dark-border">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Week {week}</p>
          <p className="text-sm text-gray-400">{date}</p>
        </div>
      )}

      {!scheduled && (
        <div className="text-center mb-4 pb-4 border-b border-dark-border">
          <p className="text-xs text-yellow-500 uppercase tracking-wide">Hypothetical Matchup</p>
        </div>
      )}

      {/* Teams Side-by-Side */}
      <div className="grid grid-cols-3 gap-4 items-center">
        {/* Team 1 */}
        <div className="text-center">
          <div className={`w-20 h-20 mx-auto mb-3 rounded-full bg-gradient-to-br ${
            team1Favored ? 'from-betting-green to-green-600' : 'from-gray-600 to-gray-700'
          } flex items-center justify-center text-3xl shadow-lg`}>
            🏈
          </div>
          <h3 className="font-bold text-lg text-white mb-1">{team1.name}</h3>
          <p className="text-xs text-gray-400 mb-2">{team1.record}</p>
          
          {/* Predicted Score */}
          <div className={`rounded-lg p-3 ${
            team1Favored ? 'bg-green-500/20 border-green-500/40' : 'bg-gray-700/50 border-gray-600'
          } border`}>
            <p className="text-3xl font-bold text-white">{team1.predicted_score}</p>
            <p className="text-xs text-gray-400 mt-1">{team1.win_probability}% win</p>
          </div>

          {/* Stats */}
          <div className="mt-3 space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Off Yards/G:</span>
              <span className="text-gray-300">{team1.offense_yards.toFixed(1)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Def Rating:</span>
              <span className="text-gray-300">{team1.defense_rating.toFixed(1)}</span>
            </div>
          </div>
        </div>

        {/* VS Divider */}
        <div className="text-center">
          <div className="text-gray-500 text-sm font-bold mb-2">VS</div>
          <div className="h-px bg-dark-border"></div>
        </div>

        {/* Team 2 */}
        <div className="text-center">
          <div className={`w-20 h-20 mx-auto mb-3 rounded-full bg-gradient-to-br ${
            !team1Favored ? 'from-betting-green to-green-600' : 'from-gray-600 to-gray-700'
          } flex items-center justify-center text-3xl shadow-lg`}>
            🏈
          </div>
          <h3 className="font-bold text-lg text-white mb-1">{team2.name}</h3>
          <p className="text-xs text-gray-400 mb-2">{team2.record}</p>
          
          {/* Predicted Score */}
          <div className={`rounded-lg p-3 ${
            !team1Favored ? 'bg-green-500/20 border-green-500/40' : 'bg-gray-700/50 border-gray-600'
          } border`}>
            <p className="text-3xl font-bold text-white">{team2.predicted_score}</p>
            <p className="text-xs text-gray-400 mt-1">{team2.win_probability}% win</p>
          </div>

          {/* Stats */}
          <div className="mt-3 space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Off Yards/G:</span>
              <span className="text-gray-300">{team2.offense_yards.toFixed(1)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Def Rating:</span>
              <span className="text-gray-300">{team2.defense_rating.toFixed(1)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Winner Banner */}
      <div className="mt-5 pt-4 border-t border-dark-border text-center">
        <p className="text-sm text-gray-400">Predicted Winner</p>
        <p className="text-xl font-bold gradient-text">
          {team1Favored ? team1.name : team2.name}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {Math.max(team1.win_probability, team2.win_probability).toFixed(1)}% confidence
        </p>
      </div>
    </div>
  )
}


