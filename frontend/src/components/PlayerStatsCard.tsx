interface PlayerStatsProps {
  playerName: string
  position: string
  team: string
  gamesPlayed: number
  stats: {
    label: string
    value: number
    total?: number
  }[]
}

export function PlayerStatsCard({
  playerName,
  position,
  team,
  gamesPlayed,
  stats
}: PlayerStatsProps) {
  return (
    <div className="glass rounded-xl p-5 border border-dark-border hover:border-blue-500/50 transition-all animate-slide-up">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-2xl shadow-lg">
          📊
        </div>
        <div className="flex-1">
          <h3 className="font-bold text-xl text-white">{playerName}</h3>
          <p className="text-sm text-gray-400">{position} • {team}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Games</p>
          <p className="text-lg font-bold text-white">{gamesPlayed}</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        {stats.map((stat, idx) => (
          <div
            key={idx}
            className="bg-dark-card rounded-lg p-3 border border-dark-border hover:border-blue-500/30 transition-colors"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
              {stat.label}
            </p>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold text-white">
                {stat.value.toFixed(1)}
              </p>
              <p className="text-xs text-gray-400">
                /game
              </p>
            </div>
            {stat.total !== undefined && (
              <p className="text-xs text-gray-500 mt-1">
                Total: {stat.total.toFixed(0)}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-dark-border">
        <p className="text-xs text-gray-500 text-center">
          Season Averages • 2025 NFL Season
        </p>
      </div>
    </div>
  )
}


