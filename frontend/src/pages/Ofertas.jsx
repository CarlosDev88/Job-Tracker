import { useEffect, useRef, useState } from 'react'

const API = '/api'
const ESTADOS = ['pendiente', 'aplicado', 'cv_enviado', 'hr_contacto', 'prueba_tecnica', 'entrevista_rrhh', 'entrevista_tecnica', 'oferta', 'rechazado', 'ghosted']
const ETIQUETAS = { pendiente: 'Guardada', aplicado: 'Aplicada', cv_enviado: 'CV enviado', hr_contacto: 'Contacto RR. HH.', prueba_tecnica: 'Prueba técnica', entrevista_rrhh: 'Entrevista RR. HH.', entrevista_tecnica: 'Entrevista técnica', oferta: 'Oferta recibida', rechazado: 'Rechazada', ghosted: 'Sin respuesta' }

const inputClase = 'bg-surface border border-hairline-strong rounded px-3 py-1.5 text-[13px] text-ink-primary focus:outline-none focus:border-accent transition-colors'

export default function Ofertas() {
    const [ofertas, setOfertas] = useState([])
    const [estado, setEstado] = useState('')
    const [fuente, setFuente] = useState('')
    const [seleccionada, setSeleccionada] = useState(null)
    const [notas, setNotas] = useState('')
    const [error, setError] = useState('')
    const version = useRef(0)

    const cargar = async () => {
        // Guard de version: al cambiar dos filtros seguidos, una respuesta lenta
        // de la primera peticion podia llegar despues y pisar la lista correcta.
        const miVersion = ++version.current
        try {
            const params = new URLSearchParams()
            if (estado) params.set('estado', estado)
            if (fuente) params.set('fuente', fuente)
            const respuesta = await fetch(API + '/aplicaciones?' + params)
            if (!respuesta.ok) throw new Error('No fue posible cargar las vacantes')
            const data = await respuesta.json()
            if (miVersion !== version.current) return
            setOfertas(data)
            setError('')
        } catch (err) {
            if (miVersion === version.current) setError(err.message)
        }
    }

    useEffect(() => { cargar() }, [estado, fuente])

    // Envuelve una mutacion: sin esto, un fetch rechazado (red caida) o una
    // respuesta que no fuera JSON (un 502 de nginx devuelve HTML) reventaba
    // dentro del propio manejo de error y la accion fallaba en silencio.
    const mutar = async (peticion, mensajeError) => {
        setError('')
        try {
            const respuesta = await peticion()
            if (!respuesta.ok) {
                const data = await respuesta.json().catch(() => ({}))
                throw new Error(data.detail || mensajeError)
            }
            return true
        } catch (err) {
            setError(err.message || mensajeError)
            return false
        }
    }

    const cambiarEstado = async (id, nuevoEstado) => {
        await mutar(
            () => fetch(API + '/aplicaciones/' + id + '/estado', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ estado: nuevoEstado }) }),
            'No fue posible actualizar el estado',
        )
        await cargar()
    }

    const guardarNotas = async () => {
        const ok = await mutar(
            () => fetch(API + '/aplicaciones/' + seleccionada.id + '/notas', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ notas }) }),
            'No fue posible guardar las notas',
        )
        if (ok) setSeleccionada(null)
        await cargar()
    }

    const eliminar = async id => {
        if (!confirm('¿Eliminar esta vacante guardada?')) return
        await mutar(
            () => fetch(API + '/aplicaciones/' + id, { method: 'DELETE' }),
            'No fue posible eliminar la vacante',
        )
        await cargar()
    }

    const grupos = ESTADOS.map(id => ({ id, items: ofertas.filter(o => o.estado === id) })).filter(g => g.items.length > 0 || estado === g.id)

    return (
        <div>
            <h2 className="font-semibold text-[26px] tracking-tight text-ink-primary">Seguimiento</h2>
            <p className="text-[13.5px] text-ink-secondary mt-1 mb-6">Las vacantes guardadas y aplicadas permanecen aquí aunque vuelvas a procesar JSON.</p>

            {error && <p className="bg-negative-muted border border-negative/30 text-negative-text p-3.5 rounded text-[13px] mb-5">{error}</p>}

            <div className="flex flex-wrap gap-2 mb-8">
                <select value={estado} onChange={event => setEstado(event.target.value)} className={inputClase}>
                    <option value="">Todos los estados</option>
                    {ESTADOS.map(item => <option key={item} value={item}>{ETIQUETAS[item]}</option>)}
                </select>
                <select value={fuente} onChange={event => setFuente(event.target.value)} className={inputClase}>
                    <option value="">Todas las fuentes</option>
                    <option value="linkedin_extension">LinkedIn búsqueda</option>
                    <option value="linkedin_publicaciones">LinkedIn publicaciones</option>
                    <option value="linkedin_feed">LinkedIn feed</option>
                    <option value="getonbrd">GetOnBord</option>
                </select>
            </div>

            {ofertas.length === 0 && <p className="text-ink-muted text-[13.5px] text-center py-16">No hay vacantes en este filtro.</p>}

            <div className="space-y-8">
                {grupos.map(grupo => (
                    <section key={grupo.id}>
                        <h3 className="font-mono text-[11px] font-medium uppercase tracking-wide text-ink-muted mb-2 flex items-center gap-2">
                            {ETIQUETAS[grupo.id]}
                            <span className="text-ink-muted/70">· {grupo.items.length}</span>
                        </h3>
                        <div className="border-t border-hairline-strong">
                            {grupo.items.map(oferta => (
                                <article key={oferta.id} className="border-b border-hairline py-4 flex justify-between gap-4">
                                    <div className="min-w-0">
                                        <a href={oferta.link || undefined} target="_blank" rel="noopener noreferrer" className={'font-semibold text-[15px] text-ink-primary ' + (oferta.link ? 'hover:text-accent-text' : '')}>
                                            {oferta.titulo}
                                        </a>
                                        <p className="text-[12.5px] text-ink-secondary mt-0.5">{oferta.empresa} {oferta.ubicacion && '· ' + oferta.ubicacion}</p>
                                        <p className="text-[11px] font-mono text-ink-muted mt-1.5">
                                            Guardada {new Date(oferta.fecha_encontrada).toLocaleDateString()}
                                            {oferta.fecha_aplicacion && ' · Aplicada ' + new Date(oferta.fecha_aplicacion).toLocaleDateString()}
                                        </p>
                                        <p className="text-[13px] text-ink-secondary whitespace-pre-wrap leading-relaxed mt-3 line-clamp-3 max-w-2xl">{oferta.descripcion}</p>
                                        {oferta.notas && <p className="text-[13px] text-accent-text mt-3">Notas: {oferta.notas}</p>}
                                    </div>
                                    <div className="shrink-0 flex flex-col gap-2 items-end">
                                        <select value={oferta.estado} onChange={event => cambiarEstado(oferta.id, event.target.value)} className={inputClase + ' text-[12px]'}>
                                            {ESTADOS.map(item => <option key={item} value={item}>{ETIQUETAS[item]}</option>)}
                                        </select>
                                        <button onClick={() => { setSeleccionada(oferta); setNotas(oferta.notas || '') }} className="text-[12px] font-medium text-accent-text hover:text-accent transition-colors">Editar notas</button>
                                        <button onClick={() => eliminar(oferta.id)} className="text-[12px] font-medium text-negative-text hover:text-negative transition-colors">Eliminar</button>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                ))}
            </div>

            {seleccionada && (
                <div className="fixed inset-0 bg-ink-primary/30 backdrop-blur-[2px] flex items-center justify-center p-6" onClick={() => setSeleccionada(null)}>
                    <div className="bg-surface border border-hairline-strong rounded shadow-modal p-6 w-full max-w-lg" onClick={event => event.stopPropagation()}>
                        <h2 className="font-semibold text-[16px] text-ink-primary mb-4">{seleccionada.titulo}</h2>
                        <textarea
                            value={notas}
                            onChange={event => setNotas(event.target.value)}
                            rows={5}
                            className="w-full bg-paper border border-hairline-strong rounded p-3.5 text-[13px] text-ink-primary focus:outline-none focus:border-accent transition-colors"
                            placeholder="Notas de seguimiento…"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <button onClick={() => setSeleccionada(null)} className="px-3.5 py-2 text-[13px] font-medium text-ink-secondary hover:text-ink-primary transition-colors">Cancelar</button>
                            <button onClick={guardarNotas} className="px-3.5 py-2 text-[13px] font-medium bg-accent hover:bg-accent-hover text-white rounded transition-colors">Guardar</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
