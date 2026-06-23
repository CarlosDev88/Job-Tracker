import { useEffect, useState } from 'react'

const API = '/api'

const ESTADOS = [
    'pendiente', 'aplicado', 'cv_enviado', 'hr_contacto',
    'prueba_tecnica', 'entrevista_rrhh', 'entrevista_tecnica',
    'oferta', 'rechazado', 'ghosted'
]

const ESTADO_COLORS = {
    pendiente: 'bg-zinc-700 text-zinc-300',
    aplicado: 'bg-blue-900 text-blue-300',
    cv_enviado: 'bg-blue-800 text-blue-200',
    hr_contacto: 'bg-purple-900 text-purple-300',
    prueba_tecnica: 'bg-yellow-900 text-yellow-300',
    entrevista_rrhh: 'bg-orange-900 text-orange-300',
    entrevista_tecnica: 'bg-orange-800 text-orange-200',
    oferta: 'bg-green-900 text-green-300',
    rechazado: 'bg-red-900 text-red-300',
    ghosted: 'bg-zinc-800 text-zinc-500',
}

export default function Ofertas() {
    const [ofertas, setOfertas] = useState([])
    const [filtroEstado, setFiltroEstado] = useState('')
    const [filtroFuente, setFiltroFuente] = useState('')
    const [selected, setSelected] = useState(null)
    const [notas, setNotas] = useState('')

    const load = () => {
        const params = new URLSearchParams()
        if (filtroEstado) params.set('estado', filtroEstado)
        if (filtroFuente) params.set('fuente', filtroFuente)
        fetch(`${API}/aplicaciones?${params}`)
            .then(r => r.json())
            .then(setOfertas)
    }

    useEffect(() => { load() }, [filtroEstado, filtroFuente])

    const cambiarEstado = async (id, estado) => {
        await fetch(`${API}/aplicaciones/${id}/estado`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado }),
        })
        load()
    }

    const guardarNotas = async (id) => {
        await fetch(`${API}/aplicaciones/${id}/notas`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notas }),
        })
        load()
        setSelected(null)
    }

    const eliminar = async (id) => {
        if (!confirm('¿Eliminar esta oferta?')) return
        await fetch(`${API}/aplicaciones/${id}`, { method: 'DELETE' })
        load()
    }

    return (
        <div className="max-w-5xl">
            <div className="flex items-center justify-between mb-4">
                <h1 className="text-xl font-semibold">Ofertas ({ofertas.length})</h1>
                <div className="flex gap-2">
                    <select
                        value={filtroEstado}
                        onChange={e => setFiltroEstado(e.target.value)}
                        className="text-sm bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300"
                    >
                        <option value="">Todos los estados</option>
                        {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
                    </select>
                    <select
                        value={filtroFuente}
                        onChange={e => setFiltroFuente(e.target.value)}
                        className="text-sm bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300"
                    >
                        <option value="">Todas las fuentes</option>
                        <option value="linkedin_extension">LinkedIn extensión</option>
                        <option value="linkedin_playwright">LinkedIn bot</option>
                        <option value="getonbord">GetOnBord</option>
                    </select>
                </div>
            </div>

            <div className="space-y-2">
                {ofertas.map(oferta => (
                    <div
                        key={oferta.id}
                        className="bg-zinc-900 border border-zinc-800 rounded p-3 hover:border-zinc-700 transition-colors"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-xs font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                                        {oferta.score}%
                                    </span>
                                    <a
                                        href={oferta.link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="font-medium text-white hover:text-blue-400 truncate"
                                    >
                                        {oferta.titulo}
                                    </a>
                                </div>
                                <div className="text-sm text-zinc-400">
                                    {oferta.empresa} {oferta.ubicacion && `· ${oferta.ubicacion}`}
                                </div>
                                {oferta.gemini_razon && (
                                    <div className="text-xs text-zinc-500 mt-1">{oferta.gemini_razon}</div>
                                )}
                                {oferta.notas && (
                                    <div className="text-xs text-yellow-600 mt-1">📝 {oferta.notas}</div>
                                )}
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                                <span className={`text-xs px-2 py-0.5 rounded ${ESTADO_COLORS[oferta.estado] || 'bg-zinc-700'}`}>
                                    {oferta.estado}
                                </span>
                                <select
                                    value={oferta.estado}
                                    onChange={e => cambiarEstado(oferta.id, e.target.value)}
                                    className="text-xs bg-zinc-800 border border-zinc-700 rounded px-1 py-0.5 text-zinc-300"
                                >
                                    {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
                                </select>
                                <button
                                    onClick={() => { setSelected(oferta); setNotas(oferta.notas || '') }}
                                    className="text-xs text-zinc-500 hover:text-white"
                                >
                                    📝
                                </button>
                                <button
                                    onClick={() => eliminar(oferta.id)}
                                    className="text-xs text-zinc-600 hover:text-red-400"
                                >
                                    ✕
                                </button>
                            </div>
                        </div>
                    </div>
                ))}

                {ofertas.length === 0 && (
                    <p className="text-zinc-500 text-sm py-8 text-center">
                        No hay ofertas. Corre el pipeline desde Dashboard.
                    </p>
                )}
            </div>

            {/* Modal notas */}
            {selected && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
                    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-5 w-full max-w-md">
                        <h3 className="font-medium mb-1">{selected.titulo}</h3>
                        <p className="text-sm text-zinc-400 mb-3">{selected.empresa}</p>
                        <textarea
                            value={notas}
                            onChange={e => setNotas(e.target.value)}
                            placeholder="Notas sobre esta oferta..."
                            rows={4}
                            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-zinc-500"
                        />
                        <div className="flex justify-end gap-2 mt-3">
                            <button
                                onClick={() => setSelected(null)}
                                className="text-sm px-3 py-1.5 text-zinc-400 hover:text-white"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={() => guardarNotas(selected.id)}
                                className="text-sm px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded"
                            >
                                Guardar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}