import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Ofertas from './pages/Ofertas'
import Perfiles from './pages/Perfiles'

export default function App() {
    return (
        <div className="min-h-screen flex">
            {/* Sidebar */}
            <nav className="w-52 bg-zinc-900 border-r border-zinc-800 p-4 flex flex-col gap-1">
                <div className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 px-2">
                    Job Tracker
                </div>
                {[
                    { to: '/', label: 'Dashboard' },
                    { to: '/ofertas', label: 'Ofertas' },
                    { to: '/perfiles', label: 'Perfiles' },
                ].map(({ to, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        className={({ isActive }) =>
                            `px-3 py-2 rounded text-sm transition-colors ${isActive
                                ? 'bg-zinc-700 text-white'
                                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                            }`
                        }
                    >
                        {label}
                    </NavLink>
                ))}
            </nav>

            {/* Main */}
            <main className="flex-1 p-6 overflow-auto">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/ofertas" element={<Ofertas />} />
                    <Route path="/perfiles" element={<Perfiles />} />
                </Routes>
            </main>
        </div>
    )
}