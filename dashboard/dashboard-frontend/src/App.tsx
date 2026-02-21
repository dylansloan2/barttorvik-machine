import { useState, useEffect, useCallback } from 'react'
import { LogIn, LogOut, TrendingUp, TrendingDown, Trophy, RefreshCw, BarChart3, Users, Target, Zap } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface BetItem {
  team_name: string
  ticker: string
  market_type: string
  conference: string
  yes_price: number
  no_price: number
  yes_ask: number
  no_ask: number
  last_price: number
  volume: number
  implied_prob: number
  bt_probability: number
  ev: number
  bt_source: string
  share_prob: number
  sole_prob: number
}

interface BtStatus {
  tourney_teams: number
  conferences_scraped: string[]
  schedule_games: number
  last_scrape: number
}

interface ScheduleGame {
  time: string
  matchup: string
  line: string
}

interface BetsResponse {
  timestamp: string
  total_markets: number
  make_tournament: BetItem[]
  conference_markets: Record<string, BetItem[]>
  best_ev_bets: BetItem[]
  positive_ev_bets?: BetItem[]
  bt_status: BtStatus
  schedule: ScheduleGame[]
}

interface SummaryResponse {
  timestamp: string
  total_make_tournament: number
  total_conference: number
  conferences_tracked: string[]
  conference_counts: Record<string, number>
  best_ev_bets: BetItem[]
  positive_ev_bets?: BetItem[]
  positive_ev_count?: number
  worst_ev_bets: BetItem[]
  matched_teams: number
  total_markets: number
}

function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const resp = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password }),
      })
      if (!resp.ok) {
        setError('Invalid username or password')
        setLoading(false)
        return
      }
      const data = await resp.json()
      localStorage.setItem('token', data.access_token)
      onLogin(data.access_token)
    } catch {
      setError('Failed to connect to server')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4">
            <Trophy className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">BartTorvik Machine</h1>
          <p className="text-slate-400 mt-2">March Madness Best Bets Dashboard</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-8 space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter username"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter password"
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="bg-red-900/30 border border-red-700 text-red-300 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-semibold rounded-xl transition-colors"
          >
            <LogIn className="w-4 h-4" />
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}

function ProbBadge({ prob }: { prob: number }) {
  const pct = (prob * 100).toFixed(1)
  let color = 'bg-slate-700 text-slate-300'
  if (prob >= 0.8) color = 'bg-green-900/50 text-green-300 border border-green-700'
  else if (prob >= 0.5) color = 'bg-blue-900/50 text-blue-300 border border-blue-700'
  else if (prob >= 0.2) color = 'bg-yellow-900/50 text-yellow-300 border border-yellow-700'
  else if (prob > 0) color = 'bg-red-900/50 text-red-300 border border-red-700'
  return <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${color}`}>{pct}%</span>
}

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="p-2 rounded-xl bg-blue-600/20 text-blue-400">{icon}</div>
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )
}

function EvBadge({ ev }: { ev: number }) {
  const pct = (ev * 100).toFixed(1)
  let color = 'bg-slate-700 text-slate-300'
  if (ev > 0.15) color = 'bg-emerald-900/60 text-emerald-300 border border-emerald-600'
  else if (ev > 0.05) color = 'bg-green-900/50 text-green-300 border border-green-700'
  else if (ev > 0) color = 'bg-lime-900/40 text-lime-300 border border-lime-700'
  else if (ev < -0.15) color = 'bg-red-900/50 text-red-300 border border-red-700'
  else if (ev < 0) color = 'bg-orange-900/40 text-orange-300 border border-orange-700'
  return <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${color}`}>{ev > 0 ? '+' : ''}{pct}%</span>
}

type SortKey = 'ev' | 'bt_probability' | 'implied_prob' | 'yes_ask' | 'no_price' | 'volume'

function MarketTable({ items, title, showConf }: { items: BetItem[]; title: string; showConf?: boolean }) {
  const [sortCol, setSortCol] = useState<SortKey>('ev')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const sorted = [...items].sort((a, b) => {
    const diff = a[sortCol] - b[sortCol]
    return sortDir === 'desc' ? -diff : diff
  })

  const toggleSort = (col: SortKey) => {
    if (sortCol === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortCol(col); setSortDir('desc') }
  }

  const SortIcon = ({ col }: { col: string }) => {
    if (sortCol !== col) return null
    return <span className="ml-1 text-blue-400">{sortDir === 'desc' ? '\u2193' : '\u2191'}</span>
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <p className="text-xs text-slate-500">{items.length} markets</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs text-slate-400 border-b border-slate-700/50">
              <th className="px-4 py-3 font-medium">Team</th>
              {showConf && <th className="px-4 py-3 font-medium">Type</th>}
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('ev')}>
                EV<SortIcon col="ev" />
              </th>
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('bt_probability')}>
                BT Prob<SortIcon col="bt_probability" />
              </th>
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('implied_prob')}>
                Kalshi Prob<SortIcon col="implied_prob" />
              </th>
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('yes_ask')}>
                Yes Price<SortIcon col="yes_ask" />
              </th>
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('no_price')}>
                No Price<SortIcon col="no_price" />
              </th>
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('volume')}>
                Volume<SortIcon col="volume" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => (
              <tr key={item.ticker} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                <td className="px-4 py-3">
                  <div className="text-sm font-medium text-white">{item.team_name}</div>
                  <div className="text-xs text-slate-500 font-mono">{item.ticker}</div>
                </td>
                {showConf && <td className="px-4 py-3 text-xs text-slate-400">{item.market_type === 'Conference Champion' ? item.conference : 'Tournament'}</td>}
                <td className="px-4 py-3"><EvBadge ev={item.ev} /></td>
                <td className="px-4 py-3">
                  {item.bt_probability > 0
                    ? <ProbBadge prob={item.bt_probability} />
                    : <span className="text-xs text-slate-600">-</span>}
                </td>
                <td className="px-4 py-3"><ProbBadge prob={item.implied_prob} /></td>
                <td className="px-4 py-3 text-sm text-slate-300">${item.yes_ask.toFixed(2)}</td>
                <td className="px-4 py-3 text-sm text-slate-300">${item.no_price.toFixed(2)}</td>
                <td className="px-4 py-3 text-sm text-slate-400">{item.volume.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Dashboard({ token, onLogout }: { token: string; onLogout: () => void }) {
  const [bets, setBets] = useState<BetsResponse | null>(null)
  const [summary, setSummary] = useState<SummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'best_bets' | 'tournament' | 'conference' | 'schedule'>('best_bets')
  const [selectedConf, setSelectedConf] = useState<string>('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    const headers = { Authorization: `Bearer ${token}` }
    try {
      const [betsResp, summaryResp] = await Promise.all([
        fetch(`${API_URL}/api/bets`, { headers }),
        fetch(`${API_URL}/api/summary`, { headers }),
      ])
      if (betsResp.status === 401 || summaryResp.status === 401) {
        onLogout()
        return
      }
      const betsData = await betsResp.json()
      const summaryData = await summaryResp.json()
      setBets(betsData)
      setSummary(summaryData)
      setSelectedConf(prev => {
        if (!prev && summaryData.conferences_tracked?.length > 0) {
          return summaryData.conferences_tracked[0]
        }
        return prev
      })
    } catch {
      setError('Failed to fetch data')
    }
    setLoading(false)
  }, [token, onLogout])

  useEffect(() => { fetchData() }, [fetchData])

  const confList = summary?.conferences_tracked || []

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
      <header className="sticky top-0 z-10 bg-slate-900/80 backdrop-blur border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-xl bg-blue-600">
              <Trophy className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-white hidden sm:block">BartTorvik Machine</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 rounded-xl transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 rounded-xl transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {error && (
          <div className="bg-red-900/30 border border-red-700 text-red-300 px-4 py-3 rounded-xl">{error}</div>
        )}

        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <StatCard
              icon={<BarChart3 className="w-5 h-5" />}
              label="Total Markets"
              value={String(summary.total_markets || 0)}
              sub="Kalshi markets tracked"
            />
            <StatCard
              icon={<Target className="w-5 h-5" />}
              label="BT Matched"
              value={String(summary.matched_teams || 0)}
              sub="Teams with BT data"
            />
            <StatCard
              icon={<Users className="w-5 h-5" />}
              label="Conferences"
              value={String(confList.length)}
              sub={`${summary.total_conference || 0} markets`}
            />
            <StatCard
              icon={<Zap className="w-5 h-5" />}
              label="Best EV Bet"
              value={summary.best_ev_bets?.[0]?.team_name || '-'}
              sub={summary.best_ev_bets?.[0] ? `EV: +${(summary.best_ev_bets[0].ev * 100).toFixed(1)}%` : ''}
            />
            <StatCard
              icon={<TrendingUp className="w-5 h-5" />}
              label="Positive EV"
              value={String(summary.positive_ev_count ?? summary.positive_ev_bets?.length ?? summary.best_ev_bets?.length ?? 0)}
              sub="Value bets found"
            />
          </div>
        )}

        {bets?.bt_status && (
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl px-4 py-2 flex items-center gap-4 text-xs text-slate-500">
            <span>BartTorvik: {bets.bt_status.tourney_teams} tourney teams</span>
            <span>|</span>
            <span>{bets.bt_status.conferences_scraped.length} conferences</span>
            <span>|</span>
            <span>{bets.bt_status.schedule_games} games today</span>
            <span>|</span>
            <span>Last scraped: {bets.bt_status.last_scrape > 0 ? new Date(bets.bt_status.last_scrape * 1000).toLocaleTimeString() : 'never'}</span>
          </div>
        )}

        <div className="flex gap-1 bg-slate-800/50 p-1 rounded-xl border border-slate-700 w-fit">
          {([
            { key: 'best_bets' as const, label: 'Best Bets' },
            { key: 'tournament' as const, label: 'Tournament' },
            { key: 'conference' as const, label: 'Conference' },
            { key: 'schedule' as const, label: 'Schedule' },
          ]).map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && !bets ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
              <p className="text-sm text-slate-400">Scraping BartTorvik & fetching Kalshi data...</p>
              <p className="text-xs text-slate-600 mt-1">First load may take ~60s while scraping</p>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'best_bets' && bets && summary && (
              <div className="space-y-6">
                <MarketTable
                  items={bets.best_ev_bets || []}
                  title={bets.positive_ev_bets && bets.positive_ev_bets.length > 0
                    ? 'Best EV Bets (Positive Expected Value)'
                    : 'Best EV Bets (Top Edges, None Currently Positive)'}
                  showConf
                />

                {summary.best_ev_bets && summary.best_ev_bets.length > 0 && (
                  <div className="grid lg:grid-cols-2 gap-6">
                    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden">
                      <div className="px-6 py-4 border-b border-slate-700 flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-green-400" />
                        <h3 className="text-lg font-semibold text-white">Top +EV Bets</h3>
                      </div>
                      <div className="divide-y divide-slate-700/30">
                        {summary.best_ev_bets.map((item, i) => (
                          <div key={item.ticker} className="px-6 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                            <div className="flex items-center gap-3">
                              <span className="text-xs text-slate-500 w-5">{i + 1}</span>
                              <div>
                                <span className="text-sm font-medium text-white">{item.team_name}</span>
                                <span className="text-xs text-slate-500 ml-2">{item.market_type === 'Conference Champion' ? item.conference : 'Tournament'}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-400">BT: {(item.bt_probability * 100).toFixed(0)}%</span>
                              <span className="text-xs text-slate-500">vs</span>
                              <span className="text-xs text-slate-400">${item.yes_ask.toFixed(2)}</span>
                              <EvBadge ev={item.ev} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden">
                      <div className="px-6 py-4 border-b border-slate-700 flex items-center gap-2">
                        <TrendingDown className="w-4 h-4 text-red-400" />
                        <h3 className="text-lg font-semibold text-white">Worst -EV (Overpriced on Kalshi)</h3>
                      </div>
                      <div className="divide-y divide-slate-700/30">
                        {summary.worst_ev_bets?.map((item, i) => (
                          <div key={item.ticker} className="px-6 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                            <div className="flex items-center gap-3">
                              <span className="text-xs text-slate-500 w-5">{i + 1}</span>
                              <div>
                                <span className="text-sm font-medium text-white">{item.team_name}</span>
                                <span className="text-xs text-slate-500 ml-2">{item.market_type === 'Conference Champion' ? item.conference : 'Tournament'}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-400">BT: {(item.bt_probability * 100).toFixed(0)}%</span>
                              <span className="text-xs text-slate-500">vs</span>
                              <span className="text-xs text-slate-400">${item.yes_ask.toFixed(2)}</span>
                              <EvBadge ev={item.ev} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'tournament' && bets && (
              <MarketTable items={bets.make_tournament} title="Make Tournament Markets" />
            )}

            {activeTab === 'conference' && bets && (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {confList.map(conf => (
                    <button
                      key={conf}
                      onClick={() => setSelectedConf(conf)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        selectedConf === conf
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-800 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-700'
                      }`}
                    >
                      {conf}
                    </button>
                  ))}
                </div>
                {selectedConf && bets.conference_markets[selectedConf] && (
                  <MarketTable
                    items={bets.conference_markets[selectedConf]}
                    title={`${selectedConf} Championship Markets`}
                  />
                )}
              </div>
            )}

            {activeTab === 'schedule' && bets && (
              <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-700">
                  <h3 className="text-lg font-semibold text-white">Today's Games (BartTorvik)</h3>
                  <p className="text-xs text-slate-500">{bets.schedule?.length || 0} games</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs text-slate-400 border-b border-slate-700/50">
                        <th className="px-6 py-3 font-medium">Time</th>
                        <th className="px-6 py-3 font-medium">Matchup</th>
                        <th className="px-6 py-3 font-medium">T-Rank Line</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bets.schedule?.map((game, i) => (
                        <tr key={i} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                          <td className="px-6 py-3 text-sm text-slate-400 whitespace-nowrap">{game.time}</td>
                          <td className="px-6 py-3 text-sm text-white whitespace-pre-line">{game.matchup}</td>
                          <td className="px-6 py-3 text-sm text-slate-300 whitespace-pre-line">{game.line}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {bets && (
          <div className="text-center text-xs text-slate-600 py-4">
            Last updated: {new Date(bets.timestamp).toLocaleString()}
          </div>
        )}
      </main>
    </div>
  )
}

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
  }

  if (!token) {
    return <LoginPage onLogin={(t) => setToken(t)} />
  }

  return <Dashboard token={token} onLogout={handleLogout} />
}

export default App
