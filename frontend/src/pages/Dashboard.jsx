import { useEffect, useState } from 'react'

const API = '/api'

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [running, setRunning] = useState(false)
    const [filtroResult, setFiltroResult] = useState(null)
    const [analisisResult, setAnalisisResult] = useState(null)

    const cargarStats = () => {
        fetch(`${API}/stats`)
            .then(r => r.json())
            .then(data => { setStats(data); setLoading(false) })
            .catch(() => setLoading(false))
    }

    useEffect(() => { cargarStats() }, [])

    const filtrar = async () => {
        setRunning(true)
        setFiltroResult(null)
        setAnalisisResult(null)
        try {
            const res = await fetch(`${API}/pipeline/filtrar`, { method: 'POST' })
            setFiltroResult(await res.json())
        } catch (e) {
            setFiltroResult({ error: e.message })
        }
        setRunning(false)
    }

    const analizar = async () => {
        setRunning(true)
        setAnalisisResult(null)
        try {
            const res = await fetch(`${API}/pipeline/analizar`, { method: 'POST' })
            setAnalisisResult(await res.json())
            cargarStats()
        } catch (e) {
            setAnalisisResult({ error: e.message })
        }
        setRunning(false)
    }

    const ranking = filtroResult?.ranking || []

    return (
        <div className="max-w-4xl">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-xl font-semibold">Dashboard</h1>
                <div className="flex gap-2">
                    <button
                        onClick={filtrar}
                        disabled={running}
                        className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 rounded transition-colors disabled:opacity-50"
                    >
                        {running ? 'Filtrando...' : '🔍 1. Filtrar vacantes'}
                    </button>
                    <button
                        onClick={analizar}
                        disabled={running || ranking.length === 0}
                        className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded transition-colors disabled:opacity-50"
                    >
                        {running ? 'Analizando...' : '🤖 2. Analizar con IA'}
                    </button>
                </div>
            </div>

            {loading && <p className="text-zinc-400">Cargando...</p>}

            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                    <StatCard label="Total" value={stats.total} />
                    {stats.por_estado?.map(s => (
                        <StatCard key={s.estado} label={s.estado} value={s.count} />
                    ))}
                </div>
            )}

            {stats?.por_fuente?.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded p-4 mb-4">
                    <h2 className="text-sm font-medium text-zinc-400 mb-3">Por fuente</h2>
                    <div className="flex gap-4">
                        {stats.por_fuente.map(f => (
                            <div key={f.fuente} className="text-sm">
                                <span className="text-zinc-400">{f.fuente}: </span>
                                <span className="font-medium">{f.count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {filtroResult?.error && (
                <div className="bg-red-950 border border-red-900 text-red-300 text-sm rounded p-3 mb-4">
                    {filtroResult.error}
                </div>
            )}

            {ranking.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded p-4 mb-4">
                    <h2 className="text-sm font-medium text-zinc-400 mb-3">
                        Ranking filtrado ({ranking.length})
                    </h2>
                    <div className="space-y-1 max-h-96 overflow-auto">
                        {ranking.map((v, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm py-1 border-b border-zinc-800 last:border-0">
                                <span className="text-xs font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded shrink-0">
                                    {v.score}%
                                </span>
                                <span className="truncate">{v.titulo}</span>
                                <span className="text-zinc-500 shrink-0">· {v.empresa}</span>
                                <span className="text-xs text-zinc-500 ml-auto shrink-0">{v.detalle?.decision}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {analisisResult && (
                <div className="bg-zinc-900 border border-zinc-800 rounded p-4">
                    <h2 className="text-sm font-medium text-zinc-400 mb-2">Resultado análisis IA</h2>
                    <pre className="text-xs text-green-400 overflow-auto">
                        {JSON.stringify(analisisResult, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    )
}

function StatCard({ label, value }) {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
            <div className="text-xs text-zinc-400 capitalize">{label}</div>
            <div className="text-2xl font-semibold mt-1">{value}</div>
        </div>
    )
}
