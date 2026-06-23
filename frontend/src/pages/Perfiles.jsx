import { useEffect, useState } from 'react'

const API = '/api'

const DEFAULT_FORM = {
    nombre: '',
    keywords_incluir: '',
    keywords_excluir: '',
    cv_texto: '',
    linkedin_search_string: '',
    getonbord_tags: '',
}

export default function Perfiles() {
    const [perfiles, setPerfiles] = useState([])
    const [form, setForm] = useState(DEFAULT_FORM)
    const [editing, setEditing] = useState(null)
    const [showForm, setShowForm] = useState(false)

    const load = () => {
        fetch(`${API}/perfiles`).then(r => r.json()).then(setPerfiles)
    }

    useEffect(() => { load() }, [])

    const activar = async (id) => {
        await fetch(`${API}/perfiles/${id}/activar`, { method: 'PUT' })
        load()
    }

    const handleSubmit = async () => {
        const payload = {
            nombre: form.nombre,
            keywords_incluir: form.keywords_incluir.split(',').map(k => k.trim()).filter(Boolean),
            keywords_excluir: form.keywords_excluir.split(',').map(k => k.trim()).filter(Boolean),
            cv_texto: form.cv_texto,
            linkedin_search_string: form.linkedin_search_string,
            getonbord_tags: form.getonbord_tags.split(',').map(k => k.trim()).filter(Boolean),
        }

        if (editing) {
            await fetch(`${API}/perfiles/${editing}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
        } else {
            await fetch(`${API}/perfiles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
        }
        setForm(DEFAULT_FORM)
        setEditing(null)
        setShowForm(false)
        load()
    }

    const editarPerfil = (p) => {
        setForm({
            nombre: p.nombre,
            keywords_incluir: JSON.parse(p.keywords_incluir || '[]').join(', '),
            keywords_excluir: JSON.parse(p.keywords_excluir || '[]').join(', '),
            cv_texto: p.cv_texto,
            linkedin_search_string: p.linkedin_search_string || '',
            getonbord_tags: JSON.parse(p.getonbord_tags || '[]').join(', '),
        })
        setEditing(p.id)
        setShowForm(true)
    }

    return (
        <div className="max-w-3xl">
            <div className="flex items-center justify-between mb-4">
                <h1 className="text-xl font-semibold">Perfiles</h1>
                <button
                    onClick={() => { setForm(DEFAULT_FORM); setEditing(null); setShowForm(true) }}
                    className="text-sm px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded"
                >
                    + Nuevo perfil
                </button>
            </div>

            <div className="space-y-3 mb-6">
                {perfiles.map(p => (
                    <div
                        key={p.id}
                        className={`bg-zinc-900 border rounded p-4 ${p.activo ? 'border-blue-600' : 'border-zinc-800'}`}
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                {p.activo && <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded">ACTIVO</span>}
                                <span className="font-medium">{p.nombre}</span>
                            </div>
                            <div className="flex gap-2">
                                {!p.activo && (
                                    <button
                                        onClick={() => activar(p.id)}
                                        className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 rounded"
                                    >
                                        Activar
                                    </button>
                                )}
                                <button
                                    onClick={() => editarPerfil(p)}
                                    className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 rounded"
                                >
                                    Editar
                                </button>
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-zinc-500">
                            <div>LinkedIn: <span className="text-zinc-400 font-mono">{p.linkedin_search_string || '—'}</span></div>
                            <div>GetOnBord tags: <span className="text-zinc-400">{JSON.parse(p.getonbord_tags || '[]').join(', ') || '—'}</span></div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Form */}
            {showForm && (
                <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-5">
                    <h2 className="font-medium mb-4">{editing ? 'Editar perfil' : 'Nuevo perfil'}</h2>
                    <div className="space-y-3">
                        <Field label="Nombre" value={form.nombre} onChange={v => setForm({ ...form, nombre: v })} />
                        <Field
                            label="Keywords incluir (separadas por coma)"
                            value={form.keywords_incluir}
                            onChange={v => setForm({ ...form, keywords_incluir: v })}
                            placeholder="react, typescript, next.js"
                        />
                        <Field
                            label="Keywords excluir (separadas por coma)"
                            value={form.keywords_excluir}
                            onChange={v => setForm({ ...form, keywords_excluir: v })}
                            placeholder="angular, java, .net"
                        />
                        <div>
                            <label className="text-xs text-zinc-400 block mb-1">Texto CV / descripción perfil</label>
                            <textarea
                                value={form.cv_texto}
                                onChange={e => setForm({ ...form, cv_texto: e.target.value })}
                                rows={3}
                                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-zinc-500"
                            />
                        </div>
                        <Field
                            label="LinkedIn search string"
                            value={form.linkedin_search_string}
                            onChange={v => setForm({ ...form, linkedin_search_string: v })}
                            placeholder='"Frontend" "React" Colombia -"Full Stack"'
                        />
                        <Field
                            label="GetOnBord tags (separadas por coma)"
                            value={form.getonbord_tags}
                            onChange={v => setForm({ ...form, getonbord_tags: v })}
                            placeholder="react-js, typescript"
                        />
                    </div>
                    <div className="flex justify-end gap-2 mt-4">
                        <button
                            onClick={() => { setShowForm(false); setEditing(null) }}
                            className="text-sm px-3 py-1.5 text-zinc-400 hover:text-white"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleSubmit}
                            className="text-sm px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded"
                        >
                            {editing ? 'Guardar cambios' : 'Crear perfil'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

function Field({ label, value, onChange, placeholder }) {
    return (
        <div>
            <label className="text-xs text-zinc-400 block mb-1">{label}</label>
            <input
                type="text"
                value={value}
                onChange={e => onChange(e.target.value)}
                placeholder={placeholder}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-500"
            />
        </div>
    )
}