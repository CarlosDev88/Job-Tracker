import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Ofertas from './pages/Ofertas'
import Perfiles from './pages/Perfiles'

const VISTAS = { dashboard: Dashboard, ofertas: Ofertas, perfil: Perfiles }

export default function App() {
    const [vista, setVista] = useState('dashboard')
    const Vista = VISTAS[vista]

    return (
        <div className="min-h-screen flex">
            <nav className="w-52 bg-zinc-900 border-r border-zinc-800 p-4 flex flex-col gap-1">
                <div className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 px-2">Job Tracker</div>
                {[['dashboard', 'Dashboard'], ['ofertas', 'Ofertas'], ['perfil', 'Configuración']].map(([id, label]) => (
                    <button key={id} onClick={() => setVista(id)}
                        className={'px-3 py-2 rounded text-left text-sm transition-colors ' + (vista === id ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800')}>
                        {label}
                    </button>
                ))}
            </nav>
            <main className="flex-1 p-6 overflow-auto"><Vista onNavigate={setVista} /></main>
        </div>
    )
}
