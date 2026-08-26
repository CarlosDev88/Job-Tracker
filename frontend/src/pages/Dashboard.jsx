import { useEffect, useState } from 'react'
import ScoreBadge from '../components/ScoreBadge'
import DecisionBadge from '../components/DecisionBadge'

const API = '/api'
const POR_PAGINA = 10
const ETIQUETAS_ESTADO = {
    pendiente: 'Guardada', aplicado: 'Aplicada', cv_enviado: 'CV enviado',
    hr_contacto: 'Contacto RR. HH.', prueba_tecnica: 'Prueba técnica',
    entrevista_rrhh: 'Entrevista RR. HH.', entrevista_tecnica: 'Entrevista técnica',
    oferta: 'Oferta recibida', rechazado: 'Rechazada', ghosted: 'Sin respuesta',
}

export default function Dashboard({ onNavigate }) {
    const [documento, setDocumento] = useState({ vacantes: [], feed: [], stats: {}, errores: [] })
    const [cargando, setCargando] = useState(true)
    const [procesando, setProcesando] = useState(false)
    const [error, setError] = useState('')
    const [detalle, setDetalle] = useState(null)
    const [guardando, setGuardando] = useState(false)
    const [pagina, setPagina] = useState(0)

    const cargar = async () => {
        try {
            const respuesta = await fetch(API + '/pipeline/filtradas')
            if (!respuesta.ok) throw new Error('No fue posible cargar el ranking')
            setDocumento(await respuesta.json())
        } catch (err) {
            setError(err.message)
        } finally {
            setCargando(false)
        }
    }

    useEffect(() => { cargar() }, [])

    const procesar = async () => {
        setProcesando(true)
        setError('')
        try {
            const respuesta = await fetch(API + '/pipeline/filtrar', { method: 'POST' })
            const data = await respuesta.json()
            if (!respuesta.ok) throw new Error(data.detail || 'No fue posible procesar los JSON')
            setPagina(0)
            await cargar()
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
                    score: vacante.score, score_detalle: vacante.detalle, estado_inicial: estadoInicial,
                }),
            })
            const data = await respuesta.json()
            if (!respuesta.ok) throw new Error(data.detail || 'No fue posible guardar la vacante')
            await cargar()
            setDetalle(current => current ? { ...current, tracking: data } : null)
        } catch (err) {
            setError(err.message)
        } finally {
            setGuardando(false)
        }
    }

    const vacantes = documento.vacantes || []
    const feed = documento.feed || []
    const totalPaginas = Math.max(1, Math.ceil(vacantes.length / POR_PAGINA))
    const paginaSegura = Math.min(pagina, totalPaginas - 1)
    const paginaItems = vacantes.slice(paginaSegura * POR_PAGINA, (paginaSegura + 1) * POR_PAGINA)

    return (
        <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between gap-4 mb-6">
                <div><h1 className="text-xl font-semibold">Dashboard</h1><p className="text-sm text-zinc-500">Procesa JSON y guarda solo las oportunidades que quieras seguir.</p></div>
                <button onClick={procesar} disabled={procesando} className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded disabled:opacity-50">{procesando ? 'Procesando...' : 'Procesar JSON'}</button>
            </div>
            {error && <Mensaje tipo="error">{error}</Mensaje>}
            {documento.errores?.length > 0 && <Mensaje tipo="warning">Se omitieron {documento.errores.length} archivo(s) inválidos.</Mensaje>}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <Stat label="Resultados" value={vacantes.length + feed.length} />
                <Stat label="Vacantes" value={vacantes.length} />
                <Stat label="Feed" value={feed.length} />
                <Stat label="Duplicadas" value={documento.stats?.duplicadas || 0} />
            </div>
            {cargando && <p className="text-zinc-400">Cargando ranking...</p>}
            {!cargando && !vacantes.length && !feed.length && <p className="text-zinc-500 text-center py-12">Aún no hay resultados. Deposita JSON y pulsa “Procesar JSON”.</p>}
            <Seccion titulo={'Vacantes estructuradas (' + vacantes.length + ')'}>{paginaItems.map(vacante => <Tarjeta key={vacante.dedupe_key} vacante={vacante} onOpen={setDetalle} />)}</Seccion>
            {totalPaginas > 1 && <div className="flex justify-center items-center gap-3 mt-4"><button onClick={() => setPagina(value => Math.max(0, value - 1))} disabled={paginaSegura === 0} className="px-3 py-1 bg-zinc-800 rounded disabled:opacity-40">← Anterior</button><span className="text-sm text-zinc-400">Página {paginaSegura + 1} de {totalPaginas}</span><button onClick={() => setPagina(value => Math.min(totalPaginas - 1, value + 1))} disabled={paginaSegura >= totalPaginas - 1} className="px-3 py-1 bg-zinc-800 rounded disabled:opacity-40">Siguiente →</button></div>}
            <Seccion titulo={'Publicaciones del feed (' + feed.length + ')'}><p className="text-sm text-zinc-500 mb-3">Estas publicaciones no usan la misma escala porcentual que las vacantes estructuradas.</p>{feed.map(vacante => <Tarjeta key={vacante.dedupe_key} vacante={vacante} onOpen={setDetalle} />)}</Seccion>
            {detalle && <Detalle vacante={detalle} guardando={guardando} onClose={() => setDetalle(null)} onGuardar={guardar} onTracking={() => onNavigate('ofertas')} />}
        </div>
    )
}

function Seccion({ titulo, children }) { return <section className="mb-8"><h2 className="text-sm font-medium text-zinc-400 mb-3">{titulo}</h2><div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div></section> }

function Tarjeta({ vacante, onOpen }) {
    return <button onClick={() => onOpen(vacante)} className="text-left bg-zinc-900 border border-zinc-800 hover:border-zinc-600 rounded p-4 transition-colors"><div className="flex gap-2 items-center mb-2">{vacante.tipo_resultado === 'feed_post' ? <DecisionBadge decision={vacante.detalle?.decision} /> : <ScoreBadge score={vacante.score} />}<span className="text-xs text-zinc-500 ml-auto truncate">{vacante.fuente}</span></div><div className="font-medium truncate">{vacante.titulo || '(sin título)'}</div>{vacante.empresa && <div className="text-sm text-zinc-500">{vacante.empresa}</div>}{vacante.tracking && <div className="text-xs text-blue-300 mt-2">✓ {ETIQUETAS_ESTADO[vacante.tracking.estado]}</div>}<p className="text-sm text-zinc-300 line-clamp-3 whitespace-pre-wrap mt-2">{vacante.descripcion}</p></button>
}

function Detalle({ vacante, guardando, onClose, onGuardar, onTracking }) {
    const tracking = vacante.tracking
    return <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-6" onClick={onClose}><div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-4xl max-h-[85vh] overflow-auto" onClick={event => event.stopPropagation()}><div className="flex justify-between gap-4 mb-2"><h3 className="text-xl font-semibold">{vacante.titulo || '(revisar manualmente)'}</h3>{vacante.tipo_resultado === 'feed_post' ? <DecisionBadge decision={vacante.detalle?.decision} /> : <ScoreBadge score={vacante.score} />}</div><p className="text-zinc-400 mb-4">{vacante.empresa} {vacante.ubicacion && '· ' + vacante.ubicacion}</p>{vacante.contactos?.emails?.length > 0 && <div className="mb-3 text-sm">{vacante.contactos.emails.map(email => <a key={email} href={'mailto:' + email} className="text-blue-400 block">{email}</a>)}</div>}{vacante.imagenes?.length > 0 && <div className="flex flex-wrap gap-3 mb-4">{vacante.imagenes.map(url => <img key={url} src={url} alt="" className="max-h-72 rounded border border-zinc-800" />)}</div>}<StackBreakdown detalle={vacante.detalle} /><p className="whitespace-pre-wrap text-zinc-200 leading-7 mb-6">{vacante.descripcion}</p><div className="flex flex-wrap justify-end gap-2"><button onClick={onClose} className="px-3 py-1.5 text-zinc-400">Cerrar</button><button onClick={() => navigator.clipboard.writeText(vacante.titulo + '\n\n' + vacante.descripcion)} className="px-3 py-1.5 bg-zinc-700 rounded">Copiar empleo</button>{vacante.link && <a href={vacante.link} target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-zinc-700 rounded">Ir a la vacante</a>}{tracking ? <button onClick={onTracking} className="px-3 py-1.5 bg-blue-600 rounded">Ver tracking: {ETIQUETAS_ESTADO[tracking.estado]}</button> : <><button disabled={guardando} onClick={() => onGuardar(vacante, 'pendiente')} className="px-3 py-1.5 bg-zinc-700 rounded disabled:opacity-50">Guardar</button><button disabled={guardando} onClick={() => onGuardar(vacante, 'aplicado')} className="px-3 py-1.5 bg-green-600 rounded disabled:opacity-50">Guardar como aplicada</button></>}</div></div></div>
}

function StackBreakdown({ detalle }) {
    const positivos = detalle?.positivos || []
    const gaps = detalle?.gaps_blandos || []
    if (!positivos.length && !gaps.length) return null
    return <div className="grid md:grid-cols-2 gap-3 mb-5 text-sm">{positivos.length > 0 && <div className="bg-green-950/40 border border-green-900 rounded p-3"><strong className="text-green-400">Coincidencias</strong><p className="mt-1 text-zinc-300">{positivos.map(item => item.keyword).join(', ')}</p></div>}{gaps.length > 0 && <div className="bg-yellow-950/40 border border-yellow-900 rounded p-3"><strong className="text-yellow-400">Deseables no cumplidos</strong><p className="mt-1 text-zinc-300">{gaps.map(item => item.keyword).join(', ')}</p></div>}</div>
}

function Stat({ label, value }) { return <div className="bg-zinc-900 border border-zinc-800 rounded p-3"><div className="text-xs text-zinc-400">{label}</div><div className="text-2xl font-semibold">{value}</div></div> }
function Mensaje({ tipo, children }) { return <div className={(tipo === 'error' ? 'bg-red-950 border-red-900 text-red-200' : 'bg-yellow-950 border-yellow-900 text-yellow-200') + ' border rounded p-3 text-sm mb-4'}>{children}</div> }
