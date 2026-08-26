import { useCallback, useEffect, useRef, useState } from 'react'
import ScoreBadge from '../components/ScoreBadge'
import DecisionBadge from '../components/DecisionBadge'
import RevisarBadge from '../components/RevisarBadge'

const API = '/api'
const POR_PAGINA = 15
const ETIQUETAS_ESTADO = {
    pendiente: 'Guardada', aplicado: 'Aplicada', cv_enviado: 'CV enviado',
    hr_contacto: 'Contacto RR. HH.', prueba_tecnica: 'Prueba técnica',
    entrevista_rrhh: 'Entrevista RR. HH.', entrevista_tecnica: 'Entrevista técnica',
    oferta: 'Oferta recibida', rechazado: 'Rechazada', ghosted: 'Sin respuesta',
}
const FUENTES_VACANTES = ['linkedin_extension', 'linkedin_publicaciones', 'getonbrd']
// Nombres legibles por fuente: linkedin_extension = resultados de búsqueda de empleos en LinkedIn,
// linkedin_publicaciones = posts sueltos de LinkedIn que anuncian una vacante,
// linkedin_feed = feed general de LinkedIn (se clasifica aparte, pestaña Publicaciones),
// getonbrd = vacantes estructuradas de GetOnBrd.
const ETIQUETAS_FUENTE = {
    linkedin_extension: 'Búsqueda de empleos (LinkedIn)',
    linkedin_publicaciones: 'Publicaciones de vacantes (LinkedIn)',
    linkedin_feed: 'Feed de LinkedIn',
    getonbrd: 'GetOnBrd',
}
const nombreFuente = valor => ETIQUETAS_FUENTE[valor] || valor

const inputClase = 'bg-surface border border-hairline-strong rounded px-3 py-1.5 text-[13px] text-ink-primary focus:outline-none focus:border-accent transition-colors'

const FILTROS_VACANTES_INICIAL = { busqueda: '', fuente: '', rangoScore: [0, 100], soloRevisar: false, pagina: 0 }
const FILTROS_FEED_INICIAL = { busqueda: '', decision: '', pagina: 0 }

// Hook: mantiene el estado de filtros de UNA pestaña y trae sus resultados
// del backend (/resultados) de forma totalmente independiente de la otra
// pestaña. La búsqueda se debounce para no golpear el backend en cada tecla.
function useResultados(tipoResultado, filtros, extraParams, activo) {
    const [datos, setDatos] = useState({ items: [], total: 0 })
    const [cargando, setCargando] = useState(true)
    const [error, setError] = useState('')
    const version = useRef(0)

    const recargar = useCallback(async () => {
        const miVersion = ++version.current
        setCargando(true)
        try {
            const params = new URLSearchParams({
                tipo_resultado: tipoResultado,
                pagina: String(filtros.pagina + 1),
                por_pagina: String(POR_PAGINA),
                ...extraParams,
            })
            if (filtros.busqueda) params.set('busqueda', filtros.busqueda)
            const respuesta = await fetch(API + '/resultados?' + params.toString())
            if (!respuesta.ok) throw new Error('No fue posible cargar los resultados')
            const data = await respuesta.json()
            if (miVersion === version.current) {
                setDatos(data)
                setError('')
            }
        } catch (err) {
            if (miVersion === version.current) setError(err.message)
        } finally {
            if (miVersion === version.current) setCargando(false)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tipoResultado, filtros.pagina, filtros.busqueda, JSON.stringify(extraParams)])

    useEffect(() => {
        if (!activo) return
        const demora = filtros.busqueda ? 300 : 0
        const temporizador = setTimeout(recargar, demora)
        return () => clearTimeout(temporizador)
    }, [activo, recargar])

    return { ...datos, cargando, error, recargar }
}

export default function Dashboard({ onNavigate }) {
    const [conteos, setConteos] = useState({ vacantes: 0, feed: 0, pendientes_revisar: 0 })
    const [erroresPipeline, setErroresPipeline] = useState(0)
    const [procesando, setProcesando] = useState(false)
    const [error, setError] = useState('')
    const [detalle, setDetalle] = useState(null)
    const [guardando, setGuardando] = useState(false)
    const [tab, setTab] = useState('vacantes')

    const [filtrosVacantes, setFiltrosVacantes] = useState(FILTROS_VACANTES_INICIAL)
    const [filtrosFeed, setFiltrosFeed] = useState(FILTROS_FEED_INICIAL)

    const cargarConteos = async () => {
        try {
            const respuesta = await fetch(API + '/resultados/conteos')
            if (respuesta.ok) setConteos(await respuesta.json())
        } catch { /* silencioso: no bloquea el resto del dashboard */ }
    }

    const cargarErroresPipeline = async () => {
        try {
            const respuesta = await fetch(API + '/pipeline/filtradas')
            if (respuesta.ok) {
                const data = await respuesta.json()
                setErroresPipeline(data.errores?.length || 0)
            }
        } catch { /* silencioso */ }
    }

    useEffect(() => { cargarConteos(); cargarErroresPipeline() }, [])

    const vacantesQuery = useResultados(
        'vacante', filtrosVacantes,
        {
            ...(filtrosVacantes.fuente ? { fuente: filtrosVacantes.fuente } : {}),
            score_min: String(filtrosVacantes.rangoScore[0]),
            score_max: String(filtrosVacantes.rangoScore[1]),
            ...(filtrosVacantes.soloRevisar ? { solo_revisar: 'true' } : {}),
        },
        tab === 'vacantes',
    )
    const feedQuery = useResultados(
        'feed_post', filtrosFeed,
        { ...(filtrosFeed.decision ? { decision: filtrosFeed.decision } : {}) },
        tab === 'feed',
    )

    const recargarTodo = async () => {
        await Promise.all([cargarConteos(), cargarErroresPipeline(), vacantesQuery.recargar(), feedQuery.recargar()])
    }

    const procesar = async () => {
        setProcesando(true)
        setError('')
        try {
            const respuesta = await fetch(API + '/pipeline/filtrar', { method: 'POST' })
            const data = await respuesta.json()
            if (!respuesta.ok) throw new Error(data.detail || 'No fue posible procesar los JSON')
            await recargarTodo()
        } catch (err) {
            setError(err.message)
        } finally {
            setProcesando(false)
        }
    }

    const guardar = async (vacante, estadoInicial) => {
        setGuardando(true)
        setError('')
        try {
            const respuesta = await fetch(API + '/aplicaciones', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dedupe_key: vacante.dedupe_key,
                    titulo: vacante.titulo, empresa: vacante.empresa, ubicacion: vacante.ubicacion,
                    descripcion: vacante.descripcion, link: vacante.link, fuente: vacante.fuente,
                    score: vacante.score ?? 0, score_detalle: vacante.detalle, estado_inicial: estadoInicial,
                }),
            })
            const data = await respuesta.json()
            if (!respuesta.ok) throw new Error(data.detail || 'No fue posible guardar la vacante')
            if (tab === 'vacantes') await vacantesQuery.recargar()
            else await feedQuery.recargar()
            setDetalle(current => current ? { ...current, tracking: data } : null)
        } catch (err) {
            setError(err.message)
        } finally {
            setGuardando(false)
        }
    }

    const query = tab === 'vacantes' ? vacantesQuery : feedQuery
    const filtros = tab === 'vacantes' ? filtrosVacantes : filtrosFeed
    const setFiltros = tab === 'vacantes' ? setFiltrosVacantes : setFiltrosFeed

    const cambiarPagina = fn => setFiltros(current => ({ ...current, pagina: fn(current.pagina) }))
    const totalPaginas = Math.max(1, Math.ceil(query.total / POR_PAGINA))

    const hayFiltrosActivosVacantes = filtrosVacantes.busqueda || filtrosVacantes.fuente
        || filtrosVacantes.rangoScore[0] > 0 || filtrosVacantes.rangoScore[1] < 100 || filtrosVacantes.soloRevisar
    const hayFiltrosActivosFeed = filtrosFeed.busqueda || filtrosFeed.decision
    const hayFiltrosActivos = tab === 'vacantes' ? hayFiltrosActivosVacantes : hayFiltrosActivosFeed

    const limpiarFiltros = () => {
        if (tab === 'vacantes') setFiltrosVacantes(FILTROS_VACANTES_INICIAL)
        else setFiltrosFeed(FILTROS_FEED_INICIAL)
    }

    return (
        <div>
            <div className="flex items-start justify-between gap-6 mb-1">
                <div>
                    <h2 className="font-semibold text-[26px] tracking-tight text-ink-primary">Vacantes procesadas</h2>
                    <p className="text-[13.5px] text-ink-secondary mt-1">Procesa los JSON del scraper y decide qué oportunidades seguir.</p>
                </div>
                <button
                    onClick={procesar}
                    disabled={procesando}
                    className="shrink-0 inline-flex items-center gap-2 px-4 py-2 text-[13.5px] font-medium bg-accent text-white rounded hover:bg-accent-hover transition disabled:opacity-50 disabled:pointer-events-none"
                >
                    Procesar JSON
                </button>
            </div>

            {error && <Mensaje tipo="error">{error}</Mensaje>}
            {query.error && <Mensaje tipo="error">{query.error}</Mensaje>}
            {erroresPipeline > 0 && <Mensaje tipo="warning">Se omitieron {erroresPipeline} archivo(s) inválidos.</Mensaje>}

            <div className="grid grid-cols-3 sm:flex sm:items-stretch mt-6 mb-8 border border-hairline rounded overflow-hidden bg-surface">
                <Stat label="Resultados" value={conteos.vacantes + conteos.feed} />
                <Stat label="Vacantes" value={conteos.vacantes} />
                <Stat label="Publicaciones" value={conteos.feed} ultimo />
            </div>

            <div className="flex items-center gap-1 border-b border-hairline-strong mb-4">
                <TabButton activo={tab === 'vacantes'} onClick={() => setTab('vacantes')}>
                    Vacantes <span className="font-mono text-[11px] text-ink-muted ml-1">{conteos.vacantes}</span>
                </TabButton>
                <TabButton activo={tab === 'feed'} onClick={() => setTab('feed')}>
                    Publicaciones <span className="font-mono text-[11px] text-ink-muted ml-1">{conteos.feed}</span>
                </TabButton>
            </div>

            {tab === 'feed' && (
                <p className="text-[12.5px] text-ink-muted mb-4">
                    Estas publicaciones no usan la misma escala porcentual que las vacantes.
                </p>
            )}

            <div className="flex flex-wrap items-end gap-3 mb-2">
                <label className="flex flex-col gap-1">
                    <span className="text-[10.5px] font-mono uppercase tracking-wide text-ink-muted">Buscar</span>
                    <input
                        value={filtros.busqueda}
                        onChange={event => setFiltros(current => ({ ...current, busqueda: event.target.value, pagina: 0 }))}
                        placeholder="Título, empresa o palabra clave…"
                        className={inputClase + ' w-64'}
                    />
                </label>
                {tab === 'vacantes' && (
                    <label className="flex flex-col gap-1">
                        <span className="text-[10.5px] font-mono uppercase tracking-wide text-ink-muted">Fuente</span>
                        <select
                            value={filtrosVacantes.fuente}
                            onChange={event => setFiltrosVacantes(current => ({ ...current, fuente: event.target.value, pagina: 0 }))}
                            className={inputClase}
                        >
                            <option value="">Cualquiera</option>
                            {FUENTES_VACANTES.map(item => <option key={item} value={item}>{nombreFuente(item)}</option>)}
                        </select>
                    </label>
                )}
                {tab === 'vacantes' && (
                    <div className="flex flex-col gap-1">
                        <span className="text-[10.5px] font-mono uppercase tracking-wide text-ink-muted">
                            Coincidencia: {filtrosVacantes.rangoScore[0]}% – {filtrosVacantes.rangoScore[1]}%
                        </span>
                        <RangoScore
                            valor={filtrosVacantes.rangoScore}
                            onChange={rango => setFiltrosVacantes(current => ({ ...current, rangoScore: rango, pagina: 0 }))}
                        />
                    </div>
                )}
                {tab === 'feed' && (
                    <label className="flex flex-col gap-1">
                        <span className="text-[10.5px] font-mono uppercase tracking-wide text-ink-muted">Estado</span>
                        <select
                            value={filtrosFeed.decision}
                            onChange={event => setFiltrosFeed(current => ({ ...current, decision: event.target.value, pagina: 0 }))}
                            className={inputClase}
                        >
                            <option value="">Cualquiera</option>
                            <option value="REVISAR">Revisar</option>
                            <option value="TAL_VEZ">Tal vez</option>
                        </select>
                    </label>
                )}
                {tab === 'vacantes' && conteos.pendientes_revisar > 0 && (
                    <label className="flex items-center gap-2 pb-1.5 cursor-pointer select-none">
                        <input
                            type="checkbox"
                            checked={filtrosVacantes.soloRevisar}
                            onChange={event => setFiltrosVacantes(current => ({ ...current, soloRevisar: event.target.checked, pagina: 0 }))}
                            className="accent-accent w-3.5 h-3.5"
                        />
                        <span className="text-[12.5px] text-ink-secondary">
                            Solo por revisar <span className="font-mono text-ink-muted">({conteos.pendientes_revisar})</span>
                        </span>
                    </label>
                )}
                {hayFiltrosActivos && (
                    <button onClick={limpiarFiltros} className="text-[12.5px] font-medium text-accent-text hover:text-accent transition-colors px-1 pb-1.5">
                        Limpiar filtros
                    </button>
                )}
                <span className="text-[12px] font-mono text-ink-muted ml-auto pb-1.5">{query.total} resultado(s)</span>
            </div>

            {query.cargando && <p className="text-ink-secondary text-[13.5px] py-8">Cargando ranking…</p>}
            {!query.cargando && query.items.length === 0 && (
                <p className="text-ink-muted text-[13.5px] text-center py-16">
                    {hayFiltrosActivos ? 'Ningún resultado coincide con los filtros.' : 'Aún no hay resultados. Deposita JSON y pulsa "Procesar JSON".'}
                </p>
            )}

            {query.items.length > 0 && (
                <div className="border-t border-hairline-strong">
                    {query.items.map(vacante => (
                        <Fila key={vacante.dedupe_key} vacante={vacante} esFeed={tab === 'feed'} onOpen={setDetalle} />
                    ))}
                </div>
            )}

            {totalPaginas > 1 && (
                <div className="flex justify-center items-center gap-3 mt-6">
                    <button
                        onClick={() => cambiarPagina(value => Math.max(0, value - 1))}
                        disabled={filtros.pagina === 0}
                        className="px-3 py-1.5 text-[12.5px] font-medium border border-hairline-strong rounded text-ink-secondary hover:text-ink-primary hover:border-ink-muted disabled:opacity-30 disabled:pointer-events-none transition-colors"
                    >
                        ← Anterior
                    </button>
                    <span className="text-[12.5px] font-mono text-ink-muted">{filtros.pagina + 1} / {totalPaginas}</span>
                    <button
                        onClick={() => cambiarPagina(value => Math.min(totalPaginas - 1, value + 1))}
                        disabled={filtros.pagina >= totalPaginas - 1}
                        className="px-3 py-1.5 text-[12.5px] font-medium border border-hairline-strong rounded text-ink-secondary hover:text-ink-primary hover:border-ink-muted disabled:opacity-30 disabled:pointer-events-none transition-colors"
                    >
                        Siguiente →
                    </button>
                </div>
            )}

            {detalle && (
                <Detalle
                    vacante={detalle}
                    guardando={guardando}
                    onClose={() => setDetalle(null)}
                    onGuardar={guardar}
                    onTracking={() => onNavigate('ofertas')}
                />
            )}

            {procesando && <OverlayProcesando />}
        </div>
    )
}

function OverlayProcesando() {
    return (
        <div className="fixed inset-0 bg-paper/80 backdrop-blur-sm flex flex-col items-center justify-center z-[60] gap-4">
            <span className="w-10 h-10 border-2 border-hairline-strong border-t-accent rounded-full animate-spin" />
            <div className="text-center">
                <p className="text-[14px] font-medium text-ink-primary">Procesando JSON…</p>
                <p className="text-[12.5px] text-ink-muted mt-1">Leyendo, normalizando y puntuando las vacantes nuevas.</p>
            </div>
        </div>
    )
}

function RangoScore({ valor, onChange }) {
    const [desde, hasta] = valor

    const cambiarDesde = event => {
        const nuevo = Math.min(Number(event.target.value), hasta - 1)
        onChange([nuevo, hasta])
    }
    const cambiarHasta = event => {
        const nuevo = Math.max(Number(event.target.value), desde + 1)
        onChange([desde, nuevo])
    }

    return (
        <div className="relative h-6 w-56 flex items-center">
            <div className="absolute inset-x-0 h-1 rounded-full bg-hairline-strong" />
            <div
                className="absolute h-1 rounded-full bg-accent"
                style={{ left: desde + '%', right: (100 - hasta) + '%' }}
            />
            <input
                type="range"
                min={0}
                max={100}
                value={desde}
                onChange={cambiarDesde}
                className="range-doble"
                aria-label="Coincidencia mínima"
            />
            <input
                type="range"
                min={0}
                max={100}
                value={hasta}
                onChange={cambiarHasta}
                className="range-doble"
                aria-label="Coincidencia máxima"
            />
        </div>
    )
}

function TabButton({ activo, onClick, children }) {
    return (
        <button
            onClick={onClick}
            className={
                'px-1 mr-6 py-2.5 text-[13.5px] font-medium border-b-2 -mb-px transition-colors ' +
                (activo ? 'border-accent text-ink-primary' : 'border-transparent text-ink-muted hover:text-ink-secondary')
            }
        >
            {children}
        </button>
    )
}

function Fila({ vacante, esFeed, onOpen }) {
    return (
        <button
            onClick={() => onOpen(vacante)}
            className="w-full text-left border-b border-hairline hover:bg-accent-muted/40 transition-colors px-2 py-3.5 flex flex-col sm:flex-row gap-2 sm:gap-4 sm:items-start group"
        >
            <div className="sm:w-24 pt-0.5 shrink-0">
                {esFeed ? <DecisionBadge decision={vacante.detalle?.decision} /> : vacante.score === null ? <RevisarBadge /> : <ScoreBadge score={vacante.score} />}
            </div>
            <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="font-medium text-[15.5px] text-ink-primary group-hover:text-accent-text transition-colors">
                        {vacante.titulo || '(sin título)'}
                    </span>
                    {vacante.empresa && <span className="text-[12.5px] text-ink-secondary shrink-0">— {vacante.empresa}</span>}
                </div>
                <p className="text-[13px] text-ink-secondary line-clamp-2 leading-relaxed mt-1 max-w-3xl">{vacante.descripcion}</p>
                <div className="flex items-center gap-3 mt-2">
                    {vacante.tracking && (
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-accent-text">
                            ✓ {ETIQUETAS_ESTADO[vacante.tracking.estado]}
                        </span>
                    )}
                    <span className="font-mono text-[10.5px] text-ink-muted uppercase tracking-wide sm:hidden">{vacante.fuente}</span>
                </div>
            </div>
            <span className="hidden sm:block font-mono text-[10.5px] text-ink-muted uppercase tracking-wide shrink-0 pt-0.5 w-32 text-right">{vacante.fuente}</span>
        </button>
    )
}

function Detalle({ vacante, guardando, onClose, onGuardar, onTracking }) {
    const tracking = vacante.tracking
    return (
        <div className="fixed inset-0 bg-ink-primary/30 backdrop-blur-[2px] flex items-center justify-center z-50 p-6" onClick={onClose}>
            <div
                className="bg-surface border border-hairline-strong rounded shadow-modal p-8 w-full max-w-3xl max-h-[85vh] overflow-auto"
                onClick={event => event.stopPropagation()}
            >
                <div className="flex justify-between gap-4 mb-1">
                    <h3 className="font-semibold text-[22px] text-ink-primary leading-snug">{vacante.titulo || '(revisar manualmente)'}</h3>
                    <button onClick={onClose} className="shrink-0 w-8 h-8 flex items-center justify-center rounded text-ink-muted hover:text-ink-primary hover:bg-paper transition-colors text-lg">✕</button>
                </div>
                <div className="flex items-center gap-3 mb-5">
                    {vacante.tipo_resultado === 'feed_post' ? <DecisionBadge decision={vacante.detalle?.decision} /> : vacante.score === null ? <RevisarBadge /> : <ScoreBadge score={vacante.score} />}
                    <p className="text-[13px] text-ink-secondary">{vacante.empresa} {vacante.ubicacion && '· ' + vacante.ubicacion}</p>
                </div>
                {vacante.contactos?.emails?.length > 0 && (
                    <div className="mb-4 text-[13px] space-y-0.5">
                        {vacante.contactos.emails.map(email => (
                            <a key={email} href={'mailto:' + email} className="text-accent-text hover:text-accent block">{email}</a>
                        ))}
                    </div>
                )}
                {vacante.imagenes?.length > 0 && (
                    <div className="flex flex-wrap gap-3 mb-5">
                        {vacante.imagenes.map(url => <img key={url} src={url} alt="" className="max-h-72 rounded border border-hairline" />)}
                    </div>
                )}
                <StackBreakdown detalle={vacante.detalle} />
                <p className="whitespace-pre-wrap text-[13.5px] text-ink-secondary leading-7 mb-7 border-t border-hairline pt-5">{vacante.descripcion}</p>
                <div className="flex flex-wrap justify-end gap-2 pt-5 border-t border-hairline-strong">
                    <button onClick={onClose} className="px-3.5 py-2 text-[13px] font-medium text-ink-secondary hover:text-ink-primary transition-colors">Cerrar</button>
                    <button
                        onClick={() => navigator.clipboard.writeText(vacante.titulo + '\n\n' + vacante.descripcion)}
                        className="px-3.5 py-2 text-[13px] font-medium border border-hairline-strong hover:border-ink-muted rounded text-ink-primary transition-colors"
                    >
                        Copiar empleo
                    </button>
                    {vacante.link && (
                        <a href={vacante.link} target="_blank" rel="noopener noreferrer" className="px-3.5 py-2 text-[13px] font-medium border border-hairline-strong hover:border-ink-muted rounded text-ink-primary transition-colors">
                            Ir a la vacante
                        </a>
                    )}
                    {tracking ? (
                        <button onClick={onTracking} className="px-3.5 py-2 text-[13px] font-medium bg-accent text-white hover:bg-accent-hover rounded transition-colors">
                            Ver tracking: {ETIQUETAS_ESTADO[tracking.estado]}
                        </button>
                    ) : (
                        <>
                            <button disabled={guardando} onClick={() => onGuardar(vacante, 'pendiente')} className="px-3.5 py-2 text-[13px] font-medium border border-hairline-strong hover:border-ink-muted rounded text-ink-primary transition-colors disabled:opacity-50">
                                Guardar
                            </button>
                            <button disabled={guardando} onClick={() => onGuardar(vacante, 'aplicado')} className="px-3.5 py-2 text-[13px] font-medium bg-positive hover:bg-positive-text text-white rounded transition-colors disabled:opacity-50">
                                Guardar como aplicada
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

function StackBreakdown({ detalle }) {
    const positivos = detalle?.positivos || []
    const gaps = detalle?.gaps_blandos || []
    if (!positivos.length && !gaps.length) return null
    return (
        <div className="grid md:grid-cols-2 gap-x-8 gap-y-3 mb-6 text-[13px] border-t border-hairline pt-5">
            {positivos.length > 0 && (
                <div>
                    <strong className="text-positive-text text-[11px] font-mono font-medium uppercase tracking-wide">Coincidencias</strong>
                    <p className="mt-1.5 text-ink-secondary leading-relaxed">{positivos.map(item => item.keyword).join(', ')}</p>
                </div>
            )}
            {gaps.length > 0 && (
                <div>
                    <strong className="text-accent-text text-[11px] font-mono font-medium uppercase tracking-wide">Deseables no cumplidos</strong>
                    <p className="mt-1.5 text-ink-secondary leading-relaxed">{gaps.map(item => item.keyword).join(', ')}</p>
                </div>
            )}
        </div>
    )
}

function Stat({ label, value, ultimo }) {
    return (
        <div className={'sm:flex-1 px-5 py-3.5 border-b sm:border-b-0 border-hairline' + (ultimo ? ' sm:border-r-0' : ' sm:border-r')}>
            <div className="text-[10.5px] font-mono uppercase tracking-wide text-ink-muted">{label}</div>
            <div className="font-semibold text-[24px] tabular text-ink-primary mt-0.5">{value}</div>
        </div>
    )
}

function Mensaje({ tipo, children }) {
    const estilo = tipo === 'error'
        ? 'bg-negative-muted border-negative/30 text-negative-text'
        : 'bg-accent-muted border-accent/30 text-accent-text'
    return <div className={estilo + ' border rounded p-3.5 text-[13px] mb-5 mt-4'}>{children}</div>
}
