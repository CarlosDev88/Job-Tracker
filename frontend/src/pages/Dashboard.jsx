import { useEffect, useState } from 'react'
import ScoreBadge from '../components/ScoreBadge'
import DecisionBadge from '../components/DecisionBadge'

const API = '/api'
const POR_PAGINA = 10

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [filtrando, setFiltrando] = useState(false)
    const [filtroResult, setFiltroResult] = useState(null)
    const [ranking, setRanking] = useState([])
    const [detalle, setDetalle] = useState(null)
    const [pagina, setPagina] = useState(0)
    const [aplicando, setAplicando] = useState(false)
    const [aplicarResultado, setAplicarResultado] = useState(null)
    const [copiado, setCopiado] = useState(false)

    const cargarStats = () => {
        fetch(`${API}/stats`)
            .then(r => r.json())
            .then(data => { setStats(data); setLoading(false) })
            .catch(() => setLoading(false))
    }

    const cargarFiltradas = () => {
        fetch(`${API}/pipeline/filtradas`)
            .then(r => r.json())
            .then(data => setRanking(Array.isArray(data) ? data : []))
            .catch(() => {})
    }

    // El ranking se recarga desde el backend (filtradas.json), no solo desde la
    // respuesta del último click — así sobrevive a navegar a Ofertas/Perfiles y volver.
    useEffect(() => { cargarStats(); cargarFiltradas() }, [])

    const filtrar = async () => {
        setFiltrando(true)
        setFiltroResult(null)
        try {
            const res = await fetch(`${API}/pipeline/filtrar`, { method: 'POST' })
            const data = await res.json()
            setFiltroResult(data)
            setRanking(data.ranking || [])
            setPagina(0)
        } catch (e) {
            setFiltroResult({ error: e.message })
        }
        setFiltrando(false)
    }

    const convertirEnOferta = async (vacante) => {
        setAplicando(true)
        setAplicarResultado(null)
        try {
            const res = await fetch(`${API}/pipeline/aplicar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(vacante),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || 'Error al convertir en oferta')
            setAplicarResultado({ ok: true })
            cargarStats()
        } catch (e) {
            setAplicarResultado({ ok: false, error: e.message })
        }
        setAplicando(false)
    }

    const copiarEmpleo = (vacante) => {
        const texto = `${vacante.titulo}${vacante.empresa ? ' · ' + vacante.empresa : ''}\n\n${vacante.descripcion}`
        navigator.clipboard.writeText(texto)
        setCopiado(true)
        setTimeout(() => setCopiado(false), 2000)
    }

    const abrirDetalle = (v) => {
        setDetalle(v)
        setAplicarResultado(null)
        setCopiado(false)
    }

    const totalPaginas = Math.max(1, Math.ceil(ranking.length / POR_PAGINA))
    const paginaSegura = Math.min(pagina, totalPaginas - 1)
    const paginaItems = ranking.slice(paginaSegura * POR_PAGINA, paginaSegura * POR_PAGINA + POR_PAGINA)

    return (
        <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-xl font-semibold">Dashboard</h1>
                <div className="flex gap-2">
                    <button
                        onClick={filtrar}
                        disabled={filtrando}
                        className="px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 rounded transition-colors disabled:opacity-50"
                    >
                        {filtrando ? 'Filtrando...' : '🔍 1. Filtrar vacantes'}
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
                <div className="mb-4">
                    <h2 className="text-sm font-medium text-zinc-400 mb-3">
                        Ranking filtrado ({ranking.length})
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {paginaItems.map((v, i) => (
                            <div
                                key={i}
                                onClick={() => abrirDetalle(v)}
                                className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded p-4 cursor-pointer transition-colors"
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    {v.revisar_manual
                                        ? <DecisionBadge decision={v.detalle?.decision} />
                                        : <ScoreBadge score={v.score} />}
                                    {!v.revisar_manual && v.detalle?.decision && (
                                        <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                                            {v.detalle.decision}
                                        </span>
                                    )}
                                    <span className="text-xs text-zinc-500 ml-auto truncate">{v.fuente}</span>
                                </div>

                                {v.imagenes?.length > 0 && (
                                    <div className="flex gap-2 mb-2 overflow-x-auto">
                                        {v.imagenes.map((url, j) => (
                                            <img
                                                key={j}
                                                src={url}
                                                alt=""
                                                className="h-28 w-28 object-cover rounded shrink-0 bg-zinc-800"
                                            />
                                        ))}
                                    </div>
                                )}

                                <div className="flex items-baseline gap-2 mb-1">
                                    <span className="font-medium text-base truncate">{v.titulo}</span>
                                    {v.empresa && <span className="text-zinc-500 text-base shrink-0">· {v.empresa}</span>}
                                </div>

                                <p className="text-sm text-zinc-300 line-clamp-3 whitespace-pre-wrap">
                                    {v.descripcion}
                                </p>
                            </div>
                        ))}
                    </div>

                    {totalPaginas > 1 && (
                        <div className="flex items-center justify-center gap-3 mt-4">
                            <button
                                onClick={() => setPagina(p => Math.max(0, p - 1))}
                                disabled={paginaSegura === 0}
                                className="text-sm px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded disabled:opacity-40"
                            >
                                ← Anterior
                            </button>
                            <span className="text-sm text-zinc-400">
                                Página {paginaSegura + 1} de {totalPaginas}
                            </span>
                            <button
                                onClick={() => setPagina(p => Math.min(totalPaginas - 1, p + 1))}
                                disabled={paginaSegura >= totalPaginas - 1}
                                className="text-sm px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded disabled:opacity-40"
                            >
                                Siguiente →
                            </button>
                        </div>
                    )}
                </div>
            )}

            {detalle && (
                <div
                    className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-6"
                    onClick={() => setDetalle(null)}
                >
                    <div
                        className="bg-zinc-900 border border-zinc-700 rounded-lg p-8 w-full max-w-4xl max-h-[85vh] overflow-auto"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-start justify-between gap-4 mb-1">
                            <h3 className="text-xl font-semibold">{detalle.titulo}</h3>
                            {detalle.revisar_manual
                                ? <DecisionBadge decision={detalle.detalle?.decision} />
                                : <ScoreBadge score={detalle.score} />}
                        </div>
                        <p className="text-base text-zinc-400 mb-4">
                            {detalle.empresa} {detalle.ubicacion && `· ${detalle.ubicacion}`}
                            {!detalle.revisar_manual && detalle.detalle?.decision && ` · ${detalle.detalle.decision}`}
                        </p>

                        {detalle.revisar_manual && (
                            <div className="bg-zinc-800 border border-zinc-700 text-zinc-300 text-sm rounded p-3 mb-4">
                                🔎 Esto vino de un post del feed de LinkedIn sin tarjeta de empleo estructurada — no
                                se extrajo título/empresa automáticamente. Lee la descripción completa y decide si es
                                una vacante real.
                                {(detalle.detalle?.emails?.length > 0 || detalle.detalle?.links?.length > 0) && (
                                    <div className="mt-2 space-y-1">
                                        {detalle.detalle.emails?.map((e, i) => (
                                            <div key={i}>📧 <a href={`mailto:${e}`} className="text-blue-400 hover:underline">{e}</a></div>
                                        ))}
                                        {detalle.detalle.links?.map((l, i) => (
                                            <div key={i}>🔗 <a href={l} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{l}</a></div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        <StackBreakdown detalle={detalle.detalle} />

                        {detalle.imagenes?.length > 0 && (
                            <div className="flex gap-3 mb-5 flex-wrap">
                                {detalle.imagenes.map((url, j) => (
                                    <img
                                        key={j}
                                        src={url}
                                        alt=""
                                        className="max-h-96 rounded border border-zinc-800"
                                    />
                                ))}
                            </div>
                        )}

                        <p className="text-zinc-300 whitespace-pre-wrap mb-6" style={{ fontSize: '16px', lineHeight: 1.6 }}>
                            {detalle.descripcion}
                        </p>
                        {aplicarResultado?.error && (
                            <div className="bg-red-950 border border-red-900 text-red-300 text-sm rounded p-3 mb-3">
                                {aplicarResultado.error}
                            </div>
                        )}
                        {aplicarResultado?.ok && (
                            <div className="bg-green-950 border border-green-900 text-green-300 text-sm rounded p-3 mb-3">
                                ✅ Convertida en oferta con estado "aplicado" — ya la puedes trackear en Ofertas.
                            </div>
                        )}

                        <div className="flex flex-wrap justify-end gap-2">
                            <button
                                onClick={() => setDetalle(null)}
                                className="text-sm px-3 py-1.5 text-zinc-400 hover:text-white"
                            >
                                Cerrar
                            </button>
                            <button
                                onClick={() => copiarEmpleo(detalle)}
                                className="text-sm px-4 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded font-medium"
                            >
                                {copiado ? '✅ Copiado' : '📋 Copiar empleo'}
                            </button>
                            <button
                                title="Próximamente: generar un CV a la medida de esta vacante"
                                className="text-sm px-4 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded font-medium"
                            >
                                🤖 Hacer CV con IA
                            </button>
                            <a
                                href={detalle.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm px-4 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded font-medium"
                            >
                                🔗 Ir a la vacante
                            </a>
                            <button
                                onClick={() => convertirEnOferta(detalle)}
                                disabled={aplicando || aplicarResultado?.ok}
                                className="text-sm px-4 py-1.5 bg-green-600 hover:bg-green-500 rounded font-medium disabled:opacity-50"
                            >
                                {aplicando ? 'Guardando...' : aplicarResultado?.ok ? '✅ Aplicado' : '✅ Aplicar'}
                            </button>
                        </div>
                    </div>
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

// Agrupa por lo que ya calculó el filtro de keywords (positivos/gaps) en vez de
// parsear la descripción libre — ese dato ya existe y no cuesta ninguna llamada al LLM.
function StackBreakdown({ detalle }) {
    if (!detalle) return null
    const { positivos = [], gaps_duros = [], gaps_blandos = [], riesgo_ingles } = detalle

    if (!positivos.length && !gaps_duros.length && !gaps_blandos.length && !riesgo_ingles) return null

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
            {positivos.length > 0 && (
                <div className="bg-green-950/40 border border-green-900 rounded p-3">
                    <div className="text-xs font-medium text-green-400 mb-2">✅ Coincide con tu perfil</div>
                    <div className="flex flex-wrap gap-1">
                        {positivos.map((p, i) => (
                            <span key={i} className="text-xs bg-green-900/50 text-green-300 px-2 py-0.5 rounded">
                                {p.keyword}
                            </span>
                        ))}
                    </div>
                </div>
            )}
            {gaps_blandos.length > 0 && (
                <div className="bg-yellow-950/40 border border-yellow-900 rounded p-3">
                    <div className="text-xs font-medium text-yellow-400 mb-2">⚠️ Deseables que no cumples</div>
                    <div className="flex flex-wrap gap-1">
                        {gaps_blandos.map((g, i) => (
                            <span key={i} className="text-xs bg-yellow-900/50 text-yellow-300 px-2 py-0.5 rounded">
                                {g.keyword}
                            </span>
                        ))}
                    </div>
                </div>
            )}
            {(gaps_duros.length > 0 || riesgo_ingles) && (
                <div className="bg-red-950/40 border border-red-900 rounded p-3">
                    <div className="text-xs font-medium text-red-400 mb-2">❌ Riesgos</div>
                    <div className="flex flex-wrap gap-1">
                        {gaps_duros.map((g, i) => (
                            <span key={i} className="text-xs bg-red-900/50 text-red-300 px-2 py-0.5 rounded">
                                {g.keyword}
                            </span>
                        ))}
                        {riesgo_ingles && riesgo_ingles !== 'BAJO' && (
                            <span className="text-xs bg-red-900/50 text-red-300 px-2 py-0.5 rounded">
                                inglés {riesgo_ingles}
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
