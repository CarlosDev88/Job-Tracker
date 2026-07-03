import { useEffect, useState } from 'react'

const API = '/api'

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [running, setRunning] = useState(false)
    const [pipelineResult, setPipelineResult] = useState(null)

    useEffect(() => {
        fetch(`${API}/stats`)
            .then(r => r.json())
            .then(data => { setStats(data); setLoading(false) })
            .catch(() => setLoading(false))
    }, [])

    const importRaw = async () => {
        setRunning(true)
        setPipelineResult(null)
        try {
            const res = await fetch(`${API}/pipeline/importar-raw`, { method: 'POST' })
            const data = await res.json()
            setPipelineResult(data)
            const s = await fetch(`${API}/stats`).then(r => r.json())
            setStats(s)
        } catch (e) {
            setPipelineResult({ error: e.message })
        }
        setRunning(false)
    }

    return (
        <div className="max-w-4xl">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-xl font-semibold">Dashboard</h1>
                <button
                    onClick={importRaw}
                    disabled={running}
                    className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 rounded transition-colors disabled:opacity-50"
                >
                    {running ? 'Importando...' : '📂 Importar extensión'}
                </button>
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

            {pipelineResult && (
                <div className="bg-zinc-900 border border-zinc-800 rounded p-4">
                    <h2 className="text-sm font-medium text-zinc-400 mb-2">Resultado importación</h2>
                    <pre className="text-xs text-green-400 overflow-auto">
                        {JSON.stringify(pipelineResult, null, 2)}
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