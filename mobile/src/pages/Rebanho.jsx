import { useEffect, useState } from 'react'
import { api } from '../api.js'

const STATUS = {
  'Lactação':  { bg: 'bg-green-100',  text: 'text-green-700'  },
  'Seca':      { bg: 'bg-amber-100',  text: 'text-amber-700'  },
  'Gestação':  { bg: 'bg-blue-100',   text: 'text-blue-700'   },
  'Novilha':   { bg: 'bg-violet-100', text: 'text-violet-700' },
  'Bezerro':   { bg: 'bg-orange-100', text: 'text-orange-700' },
}
const DEFAULT = { bg: 'bg-slate-100', text: 'text-slate-600' }

export default function Rebanho() {
  const [animais, setAnimais]           = useState([])
  const [loading, setLoading]           = useState(true)
  const [filtro, setFiltro]             = useState('')
  const [statusFiltro, setStatusFiltro] = useState('Todos')

  useEffect(() => {
    api.animais().then(a => { setAnimais(a); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const statuses = ['Todos', ...new Set(animais.map(a => a.status).filter(Boolean))]

  const filtrados = animais.filter(a => {
    const ok_s = statusFiltro === 'Todos' || a.status === statusFiltro
    const ok_n = !filtro || a.nome?.toLowerCase().includes(filtro.toLowerCase())
    return ok_s && ok_n
  })

  const contagem = statuses.slice(1).reduce((acc, s) => {
    acc[s] = animais.filter(a => a.status === s).length
    return acc
  }, {})

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="w-8 h-8 rounded-full border-4 border-green-600 border-t-transparent animate-spin" />
    </div>
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-800">Rebanho</h2>
        <p className="text-slate-400 text-sm mt-0.5">{animais.length} animais cadastrados</p>
      </div>

      {/* Chips por status */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setStatusFiltro('Todos')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all
            ${statusFiltro === 'Todos' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}>
          Todos ({animais.length})
        </button>
        {statuses.slice(1).map(s => {
          const c = STATUS[s] || DEFAULT
          const ativo = statusFiltro === s
          return (
            <button key={s} onClick={() => setStatusFiltro(ativo ? 'Todos' : s)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all
                ${ativo ? `${c.bg} ${c.text}` : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}>
              {s} ({contagem[s]})
            </button>
          )
        })}
      </div>

      {/* Busca */}
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">🔍</span>
        <input
          className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-3 text-sm text-slate-800 focus:outline-none focus:border-green-500 transition-all"
          placeholder="Buscar por nome..."
          value={filtro}
          onChange={e => setFiltro(e.target.value)}
        />
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filtrados.map((a, i) => {
          const c = STATUS[a.status] || DEFAULT
          return (
            <div key={a.id || i}
              className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-10 h-10 rounded-xl ${c.bg} flex items-center justify-center shrink-0 text-lg`}>
                    🐄
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-slate-800 text-sm truncate">{a.nome}</div>
                    {a.id && a.id !== a.nome && (
                      <div className="text-slate-400 text-xs">#{a.id}</div>
                    )}
                  </div>
                </div>
                <span className={`shrink-0 ${c.bg} ${c.text} text-xs font-bold px-2.5 py-1 rounded-lg`}>
                  {a.status || '—'}
                </span>
              </div>

              {(a.raca || a.sexo || a.nascimento) && (
                <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-x-3 gap-y-1">
                  {a.raca      && <span className="text-xs text-slate-400">{a.raca}</span>}
                  {a.sexo      && <span className="text-xs text-slate-400">{a.sexo}</span>}
                  {a.nascimento && <span className="text-xs text-slate-400">Nasc: {a.nascimento}</span>}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {filtrados.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
          <span className="text-4xl">🐄</span>
          <p className="text-sm">Nenhum animal encontrado</p>
        </div>
      )}
    </div>
  )
}
