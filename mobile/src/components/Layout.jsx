import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'

const links = [
  { to: '/',           icon: '📊', label: 'Dashboard'  },
  { to: '/ordenha',    icon: '🥛', label: 'Ordenha'    },
  { to: '/financeiro', icon: '💰', label: 'Financeiro' },
  { to: '/rebanho',    icon: '🐄', label: 'Rebanho'    },
]

export default function Layout() {
  const nav = useNavigate()
  const location = useLocation()

  function sair() {
    localStorage.removeItem('milkshow_token')
    localStorage.removeItem('milkshow_user')
    nav('/login')
  }

  const nome = JSON.parse(localStorage.getItem('milkshow_user') || '{}').nome || 'Produtor'
  const iniciais = nome.split(' ').slice(0, 2).map(p => p[0]).join('').toUpperCase()

  const paginaAtual = links.find(l =>
    l.to === '/' ? location.pathname === '/' : location.pathname.startsWith(l.to)
  )?.label || 'MilkShow'

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">

      {/* ── SIDEBAR (desktop) ── */}
      <aside className="hidden md:flex flex-col w-60 bg-white border-r border-slate-200 shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-100">
          <div className="w-9 h-9 rounded-xl bg-green-600 flex items-center justify-center text-white text-lg font-bold shadow">
            🐄
          </div>
          <div>
            <div className="font-bold text-slate-800 text-[1rem] leading-none">MilkShow</div>
            <div className="text-[0.65rem] text-green-600 font-semibold tracking-wide mt-0.5">GESTÃO LEITEIRA</div>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {links.map(({ to, icon, label }) => (
            <NavLink
              key={to} to={to} end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150
                 ${isActive
                   ? 'bg-green-50 text-green-700 shadow-sm'
                   : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`
              }
            >
              <span className="text-base">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-4 py-4 border-t border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-green-100 text-green-700 font-bold text-sm flex items-center justify-center shrink-0">
              {iniciais}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-slate-700 truncate">{nome}</div>
              <div className="text-xs text-slate-400">Produtor</div>
            </div>
            <button onClick={sair} title="Sair"
              className="text-slate-400 hover:text-red-500 transition-colors p-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* ── CONTEÚDO ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Topbar mobile + desktop header */}
        <header className="bg-white border-b border-slate-200 px-4 md:px-8 py-3 md:py-4 flex items-center justify-between shrink-0">
          {/* Mobile: logo | Desktop: título da página */}
          <div className="flex items-center gap-3">
            <div className="md:hidden flex items-center gap-2">
              <span className="text-xl">🐄</span>
              <span className="font-bold text-green-700 text-base">MilkShow</span>
            </div>
            <h1 className="hidden md:block text-lg font-bold text-slate-800">{paginaAtual}</h1>
          </div>

          {/* Mobile: botão sair */}
          <button onClick={sair}
            className="md:hidden text-slate-400 hover:text-red-500 text-sm transition-colors px-2 py-1">
            Sair
          </button>

          {/* Desktop: data atual */}
          <div className="hidden md:block text-sm text-slate-400">
            {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </div>
        </header>

        {/* Página */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-4 md:px-8 py-6 pb-28 md:pb-8">
            <Outlet />
          </div>
        </main>
      </div>

      {/* ── BOTTOM NAV (mobile) ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 flex
                      pb-[env(safe-area-inset-bottom,0px)] z-50">
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2.5 gap-0.5 text-[0.65rem] font-semibold transition-colors
               ${isActive ? 'text-green-600' : 'text-slate-400'}`
            }
          >
            <span className="text-xl leading-none">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
