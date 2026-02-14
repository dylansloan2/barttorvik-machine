import { useState, useEffect, useCallback } from 'react'
import { LogIn, LogOut, TrendingUp, TrendingDown, Trophy, RefreshCw, BarChart3, Users, Target } from 'lucide-react'

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
}

interface BetsResponse {
  timestamp: string
  total_markets: number
  make_tournament: BetItem[]
  conference_markets: Record<string, BetItem[]>
}

interface SummaryResponse {
  timestamp: string
  total_make_tournament: number
  total_conference: number
  conferences_tracked: string[]
  conference_counts: Record<string, number>
  top_favorites: BetItem[]
  top_underdogs: BetItem[]
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

function MarketTable({ items, title }: { items: BetItem[]; title: string }) {
  const [sortCol, setSortCol] = useState<'implied_prob' | 'yes_ask' | 'volume'>('implied_prob')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const sorted = [...items].sort((a, b) => {
    const diff = a[sortCol] - b[sortCol]
    return sortDir === 'desc' ? -diff : diff
  })

  const toggleSort = (col: 'implied_prob' | 'yes_ask' | 'volume') => {
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
              <th className="px-6 py-3 font-medium">Team</th>
              <th className="px-6 py-3 font-medium">Ticker</th>
              <th className="px-6 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('implied_prob')}>
                Implied Prob<SortIcon col="implied_prob" />
              </th>
              <th className="px-6 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('yes_ask')}>
                Yes Ask<SortIcon col="yes_ask" />
              </th>
              <th className="px-6 py-3 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('volume')}>
                Volume<SortIcon col="volume" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => (
              <tr key={item.ticker} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                <td className="px-6 py-3 text-sm font-medium text-white">{item.team_name}</td>
                <td className="px-6 py-3 text-xs text-slate-400 font-mono">{item.ticker}</td>
                <td className="px-6 py-3"><ProbBadge prob={item.implied_prob} /></td>
                <td className="px-6 py-3 text-sm text-slate-300">${item.yes_ask.toFixed(2)}</td>
                <td className="px-6 py-3 text-sm text-slate-400">{item.volume.toLocaleString()}</td>
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
  const [activeTab, setActiveTab] = useState<'overview' | 'tournament' | 'conference'>('overview')
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
      if (summaryData.conferences_tracked?.length > 0 && !selectedConf) {
        setSelectedConf(summaryData.conferences_tracked[0])
      }
    } catch {
      setError('Failed to fetch data')
    }
    setLoading(false)
  }, [token, onLogout, selectedConf])

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
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={<BarChart3 className="w-5 h-5" />}
              label="Total Markets"
              value={String((summary.total_make_tournament || 0) + (summary.total_conference || 0))}
              sub="Active Kalshi markets"
            />
            <StatCard
              icon={<Target className="w-5 h-5" />}
              label="Make Tournament"
              value={String(summary.total_make_tournament || 0)}
              sub="NCAA tournament markets"
            />
            <StatCard
              icon={<Users className="w-5 h-5" />}
              label="Conference Champs"
              value={String(summary.total_conference || 0)}
              sub={`${confList.length} conferences`}
            />
            <StatCard
              icon={<TrendingUp className="w-5 h-5" />}
              label="Top Favorite"
              value={summary.top_favorites?.[0]?.team_name || '-'}
              sub={summary.top_favorites?.[0] ? `${(summary.top_favorites[0].implied_prob * 100).toFixed(1)}% implied` : ''}
            />
          </div>
        )}

        <div className="flex gap-1 bg-slate-800/50 p-1 rounded-xl border border-slate-700 w-fit">
          {(['overview', 'tournament', 'conference'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {loading && !bets ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : (
          <>
            {activeTab === 'overview' && summary && (
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-700 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-green-400" />
                    <h3 className="text-lg font-semibold text-white">Top Favorites</h3>
                  </div>
                  <div className="divide-y divide-slate-700/30">
                    {summary.top_favorites?.map((item, i) => (
                      <div key={item.ticker} className="px-6 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500 w-5">{i + 1}</span>
                          <span className="text-sm font-medium text-white">{item.team_name}</span>
                        </div>
                        <ProbBadge prob={item.implied_prob} />
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-700 flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-red-400" />
                    <h3 className="text-lg font-semibold text-white">Top Underdogs</h3>
                  </div>
                  <div className="divide-y divide-slate-700/30">
                    {summary.top_underdogs?.map((item, i) => (
                      <div key={item.ticker} className="px-6 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500 w-5">{i + 1}</span>
                          <span className="text-sm font-medium text-white">{item.team_name}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-400">${item.yes_ask.toFixed(2)}</span>
                          <ProbBadge prob={item.implied_prob} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
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
