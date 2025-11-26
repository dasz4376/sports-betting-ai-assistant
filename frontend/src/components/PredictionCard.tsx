interface PredictionCardProps {
  playerName: string
  position: string
  team: string
  stat: string
  predicted: number
  confidence: number
  opponent?: string
}

export function PredictionCard({
  playerName,
  position,
  team,
  stat,
  predicted,
  confidence,
  opponent
}: PredictionCardProps) {
  const getConfidenceColor = (conf: number) => {
    if (conf >= 80) return 'text-betting-green'
    if (conf >= 60) return 'text-yellow-400'
    return 'text-betting-red'
  }

  const getConfidenceBg = (conf: number) => {
    if (conf >= 80) return 'from-green-500/20 to-green-600/20 border-green-500/30'
    if (conf >= 60) return 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/30'
    return 'from-red-500/20 to-red-600/20 border-red-500/30'
  }

  return (
    <div className="glass rounded-xl p-5 border border-dark-border hover:border-blue-500/50 transition-all animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xl">
            🏈
          </div>
          <div>
            <h3 className="font-bold text-lg text-white">{playerName}</h3>
            <p className="text-sm text-gray-400">{position} • {team}</p>
          </div>
        </div>
        
        {opponent && (
          <div className="text-right">
            <p className="text-xs text-gray-500">vs</p>
            <p className="text-sm font-semibold text-gray-300">{opponent}</p>
          </div>
        )}
      </div>

      {/* Prediction */}
      <div className={`bg-gradient-to-r ${getConfidenceBg(confidence)} rounded-lg p-4 border`}>
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{stat}</p>
            <p className="text-3xl font-bold text-white">{predicted.toFixed(1)}</p>
          </div>
          
          <div className="text-right">
            <p className="text-xs text-gray-400 mb-1">Confidence</p>
            <p className={`text-2xl font-bold ${getConfidenceColor(confidence)}`}>
              {confidence}%
            </p>
          </div>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="mt-3 w-full bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            confidence >= 80
              ? 'bg-gradient-to-r from-green-500 to-green-600'
              : confidence >= 60
              ? 'bg-gradient-to-r from-yellow-500 to-yellow-600'
              : 'bg-gradient-to-r from-red-500 to-red-600'
          }`}
          style={{ width: `${confidence}%` }}
        />
      </div>
    </div>
  )
}


