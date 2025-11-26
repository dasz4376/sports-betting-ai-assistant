interface InjuryInfo {
  player: string
  position: string
  injury_type: string
  date_reported: string
}

interface InjuryReportProps {
  team: string
  out: InjuryInfo[]
  doubtful: InjuryInfo[]
  questionable: InjuryInfo[]
}

export function InjuryReport({
  team,
  out,
  doubtful,
  questionable
}: InjuryReportProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'out':
        return 'from-red-500 to-red-600'
      case 'doubtful':
        return 'from-orange-500 to-orange-600'
      case 'questionable':
        return 'from-yellow-500 to-yellow-600'
      default:
        return 'from-gray-500 to-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'out':
        return '🚫'
      case 'doubtful':
        return '⚠️'
      case 'questionable':
        return '❓'
      default:
        return '🏥'
    }
  }

  const totalInjuries = out.length + doubtful.length + questionable.length

  return (
    <div className="glass rounded-xl p-5 border border-dark-border animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-bold text-xl text-white">{team} Injury Report</h3>
          <p className="text-sm text-gray-400">
            {totalInjuries} {totalInjuries === 1 ? 'player' : 'players'} with injury designation
          </p>
        </div>
        <div className="text-3xl">🏥</div>
      </div>

      {totalInjuries === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-400">✓ No active injuries reported</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* OUT */}
          {out.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{getStatusIcon('out')}</span>
                <h4 className="font-semibold text-red-400 uppercase text-sm">
                  Out ({out.length})
                </h4>
              </div>
              <div className="space-y-2">
                {out.map((injury, idx) => (
                  <div
                    key={idx}
                    className="bg-gradient-to-r from-red-500/10 to-transparent border-l-4 border-red-500 rounded-r p-3"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-white">{injury.player}</p>
                        <p className="text-xs text-gray-400">{injury.position}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-300">{injury.injury_type}</p>
                        <p className="text-xs text-gray-500">{injury.date_reported}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* DOUBTFUL */}
          {doubtful.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{getStatusIcon('doubtful')}</span>
                <h4 className="font-semibold text-orange-400 uppercase text-sm">
                  Doubtful ({doubtful.length})
                </h4>
              </div>
              <div className="space-y-2">
                {doubtful.map((injury, idx) => (
                  <div
                    key={idx}
                    className="bg-gradient-to-r from-orange-500/10 to-transparent border-l-4 border-orange-500 rounded-r p-3"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-white">{injury.player}</p>
                        <p className="text-xs text-gray-400">{injury.position}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-300">{injury.injury_type}</p>
                        <p className="text-xs text-gray-500">{injury.date_reported}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* QUESTIONABLE */}
          {questionable.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{getStatusIcon('questionable')}</span>
                <h4 className="font-semibold text-yellow-400 uppercase text-sm">
                  Questionable ({questionable.length})
                </h4>
              </div>
              <div className="space-y-2">
                {questionable.map((injury, idx) => (
                  <div
                    key={idx}
                    className="bg-gradient-to-r from-yellow-500/10 to-transparent border-l-4 border-yellow-500 rounded-r p-3"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-white">{injury.player}</p>
                        <p className="text-xs text-gray-400">{injury.position}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-300">{injury.injury_type}</p>
                        <p className="text-xs text-gray-500">{injury.date_reported}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer Note */}
      <div className="mt-4 pt-4 border-t border-dark-border">
        <p className="text-xs text-gray-500 text-center">
          💡 Predictions automatically adjust for injury severity
        </p>
      </div>
    </div>
  )
}


