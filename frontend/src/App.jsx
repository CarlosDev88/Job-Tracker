import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard'
import Ofertas from './pages/Ofertas'
import Perfiles from './pages/Perfiles'

const VISTAS = { dashboard: Dashboard, ofertas: Ofertas, perfil: Perfiles }
const ITEMS = [
    ['dashboard', 'Vacantes'],
    ['ofertas', 'Seguimiento'],
    ['perfil', 'Perfil'],
]

function useTema() {
    const [tema, setTema] = useState(() => document.documentElement.getAttribute('data-theme') || 'light')

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', tema)
        try { localStorage.setItem('jobtracker-theme', tema) } catch (err) { /* almacenamiento no disponible */ }
    }, [tema])

    return [tema, () => setTema(current => (current === 'dark' ? 'light' : 'dark'))]
}

export default function App() {
    const [vista, setVista] = useState('dashboard')
    const [tema, alternarTema] = useTema()
    const Vista = VISTAS[vista]

    return (
        <div className="min-h-screen bg-paper text-ink-primary">
            <header className="border-b border-hairline bg-surface">
                <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-wrap items-center h-auto sm:h-16 py-3 sm:py-0 gap-4 sm:gap-8">
                    <h1 className="font-semibold text-[19px] tracking-tight text-ink-primary shrink-0">
                        Job Tracker
                    </h1>
                    <nav className="flex items-center gap-1 h-full flex-wrap">
                        {ITEMS.map(([id, label]) => {
                            const activo = vista === id
                            return (
                                <button
                                    key={id}
                                    onClick={() => setVista(id)}
                                    className={
                                        'h-full px-1 mx-3 text-[13.5px] font-medium border-b-2 -mb-px transition-colors ' +
                                        (activo
                                            ? 'border-accent text-ink-primary'
                                            : 'border-transparent text-ink-muted hover:text-ink-secondary')
                                    }
                                >
                                    {label}
                                </button>
                            )
                        })}
                    </nav>
                    <button
                        onClick={alternarTema}
                        aria-label={tema === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
                        title={tema === 'dark' ? 'Tema oscuro' : 'Tema claro'}
                        className="ml-auto shrink-0 w-9 h-9 flex items-center justify-center rounded-full border border-hairline-strong text-ink-secondary hover:text-ink-primary hover:border-ink-muted transition-colors"
                    >
                        {tema === 'dark' ? (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="4" />
                                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
                            </svg>
                        ) : (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                            </svg>
                        )}
                    </button>
                </div>
            </header>
            <main className="max-w-6xl mx-auto px-6 py-8">
                <Vista onNavigate={setVista} />
            </main>
        </div>
    )
}
