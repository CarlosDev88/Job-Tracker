import { useEffect, useState } from 'react'

const API = '/api'

export default function Perfiles() {
    const [form, setForm] = useState(null)
    const [mensaje, setMensaje] = useState('')
    const [error, setError] = useState('')
    const [guardando, setGuardando] = useState(false)

    useEffect(() => {
        fetch(API + '/perfil').then(async respuesta => {
            if (!respuesta.ok) throw new Error('No fue posible cargar la configuración')
            return respuesta.json()
        }).then(data => setForm({
            nombre: data.nombre || '',
            keywords_incluir: JSON.parse(data.keywords_incluir || '[]').join(', '),
            keywords_excluir: JSON.parse(data.keywords_excluir || '[]').join(', '),
            cv_texto: data.cv_texto || '',
            ubicacion_base: data.ubicacion_base || 'Bucaramanga',
            empresas_bloqueadas: JSON.parse(data.empresas_bloqueadas || '[]').join(', '),
        })).catch(err => setError(err.message))
    }, [])

    const guardar = async () => {
        setGuardando(true)
        setMensaje('')
        setError('')
        const payload = { nombre: form.nombre.trim(), keywords_incluir: form.keywords_incluir.split(',').map(item => item.trim()).filter(Boolean), keywords_excluir: form.keywords_excluir.split(',').map(item => item.trim()).filter(Boolean), cv_texto: form.cv_texto, ubicacion_base: form.ubicacion_base.trim(), empresas_bloqueadas: form.empresas_bloqueadas.split(',').map(item => item.trim()).filter(Boolean) }
        try {
            const respuesta = await fetch(API + '/perfil', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
            const data = await respuesta.json().catch(() => ({}))
            if (!respuesta.ok) throw new Error(data.detail || 'No fue posible guardar')
            setMensaje('Configuración guardada. Se aplicará en el próximo procesamiento.')
        } catch (err) {
            setError(err.message)
        } finally {
            setGuardando(false)
        }
    }

    if (!form) {
        // Sin esto, un fallo al cargar dejaba "Cargando configuración…" fijo
        // para siempre: el mensaje de error se renderizaba mas abajo, en un
        // JSX al que nunca se llegaba.
        if (error) {
            return (
                <div className="max-w-2xl">
                    <p className="bg-negative-muted border border-negative/30 text-negative-text p-3.5 rounded text-[13px]">{error}</p>
                    <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 text-[13.5px] font-medium border border-hairline-strong hover:border-ink-muted rounded text-ink-primary transition-colors">
                        Reintentar
                    </button>
                </div>
            )
        }
        return <p className="text-ink-secondary text-[13.5px]">Cargando configuración…</p>
    }

    return (
        <div className="max-w-2xl">
            <h2 className="font-semibold text-[26px] tracking-tight text-ink-primary">Perfil de búsqueda</h2>
            <p className="text-[13.5px] text-ink-secondary mt-1 mb-8">La V1 usa un solo perfil activo para puntuar las vacantes.</p>

            {error && <p className="bg-negative-muted border border-negative/30 text-negative-text p-3.5 rounded text-[13px] mb-6">{error}</p>}
            {mensaje && <p className="bg-accent-muted border border-accent/30 text-accent-text p-3.5 rounded text-[13px] mb-6">{mensaje}</p>}

            <div className="space-y-6">
                <Campo label="Nombre" value={form.nombre} onChange={value => setForm({ ...form, nombre: value })} />
                <Campo label="Ubicación base" value={form.ubicacion_base} onChange={value => setForm({ ...form, ubicacion_base: value })} />
                <Campo label="Keywords a incluir (separadas por coma)" value={form.keywords_incluir} onChange={value => setForm({ ...form, keywords_incluir: value })} />
                <Campo label="Keywords a excluir (separadas por coma)" value={form.keywords_excluir} onChange={value => setForm({ ...form, keywords_excluir: value })} />
                <div>
                    <Campo
                        label="Empresas bloqueadas (separadas por coma)"
                        value={form.empresas_bloqueadas}
                        onChange={value => setForm({ ...form, empresas_bloqueadas: value })}
                    />
                    <p className="text-[12px] text-ink-muted mt-2 leading-relaxed">
                        Sus vacantes se descartan al procesar y las que ya estén guardadas se borran del histórico.
                        No hace falta escribir el nombre exacto: &quot;bairesdev&quot; también captura &quot;Baires Dev&quot; y &quot;BairesDev LLC&quot;.
                    </p>
                </div>
                <div>
                    <label htmlFor="cv-texto" className="text-[11px] font-mono uppercase tracking-wide text-ink-muted block mb-2">Resumen de experiencia</label>
                    <textarea
                        id="cv-texto"
                        value={form.cv_texto}
                        onChange={event => setForm({ ...form, cv_texto: event.target.value })}
                        rows={6}
                        className="w-full bg-surface border border-hairline-strong rounded p-3.5 text-[13.5px] text-ink-primary leading-relaxed focus:outline-none focus:border-accent transition-colors"
                    />
                </div>
                <div className="flex justify-end pt-2 border-t border-hairline">
                    <button onClick={guardar} disabled={guardando} className="mt-4 px-4 py-2 text-[13.5px] font-medium bg-accent hover:bg-accent-hover text-white rounded transition-colors disabled:opacity-50 disabled:pointer-events-none">
                        {guardando ? 'Guardando…' : 'Guardar configuración'}
                    </button>
                </div>
            </div>
        </div>
    )
}

function Campo({ label, value, onChange, id }) {
    const inputId = id || 'campo-' + label.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    return (
        <div>
            <label htmlFor={inputId} className="text-[11px] font-mono uppercase tracking-wide text-ink-muted block mb-2">{label}</label>
            <input
                id={inputId}
                value={value}
                onChange={event => onChange(event.target.value)}
                className="w-full bg-surface border border-hairline-strong rounded p-3 text-[13.5px] text-ink-primary focus:outline-none focus:border-accent transition-colors"
            />
        </div>
    )
}
