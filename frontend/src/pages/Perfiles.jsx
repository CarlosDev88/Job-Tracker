import { useEffect, useState } from 'react'

const API = '/api'

export default function Perfiles() {
    const [form, setForm] = useState(null)
    const [mensaje, setMensaje] = useState('')

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
        })).catch(error => setMensaje(error.message))
    }, [])

    const guardar = async () => {
        const payload = { nombre: form.nombre.trim(), keywords_incluir: form.keywords_incluir.split(',').map(item => item.trim()).filter(Boolean), keywords_excluir: form.keywords_excluir.split(',').map(item => item.trim()).filter(Boolean), cv_texto: form.cv_texto, ubicacion_base: form.ubicacion_base.trim() }
        const respuesta = await fetch(API + '/perfil', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        const data = await respuesta.json()
        setMensaje(respuesta.ok ? 'Configuración guardada. Se aplicará en el próximo procesamiento.' : (data.detail || 'No fue posible guardar'))
    }

    if (!form) return <p className="text-zinc-400">Cargando configuración...</p>
    return <div className="max-w-3xl"><h1 className="text-xl font-semibold">Configuración del perfil</h1><p className="text-sm text-zinc-500 mt-1 mb-5">La V1 usa un solo perfil activo para puntuar las vacantes.</p>{mensaje && <p className="bg-zinc-800 border border-zinc-700 text-zinc-200 p-3 rounded text-sm mb-4">{mensaje}</p>}<div className="space-y-4 bg-zinc-900 border border-zinc-800 rounded p-5"><Campo label="Nombre" value={form.nombre} onChange={value => setForm({ ...form, nombre: value })} /><Campo label="Ubicación base" value={form.ubicacion_base} onChange={value => setForm({ ...form, ubicacion_base: value })} /><Campo label="Keywords a incluir (separadas por coma)" value={form.keywords_incluir} onChange={value => setForm({ ...form, keywords_incluir: value })} /><Campo label="Keywords a excluir (separadas por coma)" value={form.keywords_excluir} onChange={value => setForm({ ...form, keywords_excluir: value })} /><div><label className="text-sm text-zinc-400 block mb-1">Resumen de experiencia</label><textarea value={form.cv_texto} onChange={event => setForm({ ...form, cv_texto: event.target.value })} rows={5} className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 text-sm" /></div><div className="flex justify-end"><button onClick={guardar} className="px-4 py-2 bg-blue-600 rounded">Guardar configuración</button></div></div></div>
}

function Campo({ label, value, onChange }) { return <div><label className="text-sm text-zinc-400 block mb-1">{label}</label><input value={value} onChange={event => onChange(event.target.value)} className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 text-sm" /></div> }
