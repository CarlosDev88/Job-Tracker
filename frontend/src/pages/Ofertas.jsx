import { useEffect, useState } from 'react'

const API = '/api'
const ESTADOS = ['pendiente', 'aplicado', 'cv_enviado', 'hr_contacto', 'prueba_tecnica', 'entrevista_rrhh', 'entrevista_tecnica', 'oferta', 'rechazado', 'ghosted']
const ETIQUETAS = { pendiente: 'Guardada', aplicado: 'Aplicada', cv_enviado: 'CV enviado', hr_contacto: 'Contacto RR. HH.', prueba_tecnica: 'Prueba técnica', entrevista_rrhh: 'Entrevista RR. HH.', entrevista_tecnica: 'Entrevista técnica', oferta: 'Oferta recibida', rechazado: 'Rechazada', ghosted: 'Sin respuesta' }

export default function Ofertas() {
    const [ofertas, setOfertas] = useState([])
    const [estado, setEstado] = useState('')
    const [fuente, setFuente] = useState('')
    const [seleccionada, setSeleccionada] = useState(null)
    const [notas, setNotas] = useState('')
    const [error, setError] = useState('')

    const cargar = async () => {
        try {
            const params = new URLSearchParams()
            if (estado) params.set('estado', estado)
            if (fuente) params.set('fuente', fuente)
            const respuesta = await fetch(API + '/aplicaciones?' + params)
            if (!respuesta.ok) throw new Error('No fue posible cargar las vacantes')
            setOfertas(await respuesta.json())
        } catch (err) { setError(err.message) }
    }

    useEffect(() => { cargar() }, [estado, fuente])

    const cambiarEstado = async (id, nuevoEstado) => {
        const respuesta = await fetch(API + '/aplicaciones/' + id + '/estado', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ estado: nuevoEstado }) })
        if (!respuesta.ok) setError((await respuesta.json()).detail || 'No fue posible actualizar el estado')
        await cargar()
    }

    const guardarNotas = async () => {
        const respuesta = await fetch(API + '/aplicaciones/' + seleccionada.id + '/notas', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ notas }) })
        if (!respuesta.ok) setError((await respuesta.json()).detail || 'No fue posible guardar las notas')
        setSeleccionada(null)
        await cargar()
    }

    const eliminar = async id => {
        if (!confirm('¿Eliminar esta vacante guardada?')) return
        const respuesta = await fetch(API + '/aplicaciones/' + id, { method: 'DELETE' })
        if (!respuesta.ok) setError((await respuesta.json()).detail || 'No fue posible eliminar la vacante')
        await cargar()
    }

    return <div className="max-w-5xl"><h1 className="text-xl font-semibold mb-1">Seguimiento de vacantes</h1><p className="text-sm text-zinc-500 mb-4">Las vacantes guardadas y aplicadas permanecen aquí aunque vuelvas a procesar JSON.</p>{error && <p className="bg-red-950 border border-red-900 text-red-200 p-3 rounded text-sm mb-4">{error}</p>}<div className="flex flex-wrap gap-2 mb-4"><select value={estado} onChange={event => setEstado(event.target.value)} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"><option value="">Todos los estados</option>{ESTADOS.map(item => <option key={item} value={item}>{ETIQUETAS[item]}</option>)}</select><select value={fuente} onChange={event => setFuente(event.target.value)} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"><option value="">Todas las fuentes</option><option value="linkedin_extension">LinkedIn búsqueda</option><option value="linkedin_publicaciones">LinkedIn publicaciones</option><option value="linkedin_feed">LinkedIn feed</option><option value="getonbrd">GetOnBord</option></select></div><div className="space-y-3">{ofertas.map(oferta => <article key={oferta.id} className="bg-zinc-900 border border-zinc-800 rounded p-4"><div className="flex justify-between gap-4"><div className="min-w-0"><a href={oferta.link || undefined} target="_blank" rel="noopener noreferrer" className={'font-medium ' + (oferta.link ? 'hover:text-blue-400' : '')}>{oferta.titulo}</a><p className="text-sm text-zinc-400">{oferta.empresa} {oferta.ubicacion && '· ' + oferta.ubicacion}</p><p className="text-xs text-zinc-500 mt-1">Guardada: {new Date(oferta.fecha_encontrada).toLocaleDateString()} {oferta.fecha_aplicacion && '· Aplicada: ' + new Date(oferta.fecha_aplicacion).toLocaleDateString()}</p><p className="text-sm text-zinc-300 whitespace-pre-wrap mt-3">{oferta.descripcion}</p>{oferta.notas && <p className="text-sm text-yellow-300 mt-3">Notas: {oferta.notas}</p>}</div><div className="shrink-0 flex flex-col gap-2"><select value={oferta.estado} onChange={event => cambiarEstado(oferta.id, event.target.value)} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-xs">{ESTADOS.map(item => <option key={item} value={item}>{ETIQUETAS[item]}</option>)}</select><button onClick={() => { setSeleccionada(oferta); setNotas(oferta.notas || '') }} className="text-xs text-blue-300">Editar notas</button><button onClick={() => eliminar(oferta.id)} className="text-xs text-red-300">Eliminar</button></div></div></article>)}{ofertas.length === 0 && <p className="text-zinc-500 text-center py-10">No hay vacantes en este filtro.</p>}</div>{seleccionada && <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-6"><div className="bg-zinc-900 border border-zinc-700 rounded p-5 w-full max-w-lg"><h2 className="font-medium mb-3">{seleccionada.titulo}</h2><textarea value={notas} onChange={event => setNotas(event.target.value)} rows={5} className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 text-sm" placeholder="Notas de seguimiento..." /><div className="flex justify-end gap-2 mt-3"><button onClick={() => setSeleccionada(null)} className="px-3 py-1.5 text-zinc-400">Cancelar</button><button onClick={guardarNotas} className="px-3 py-1.5 bg-blue-600 rounded">Guardar</button></div></div></div>}</div>
}
