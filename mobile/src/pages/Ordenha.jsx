import { useEffect, useState } from 'react'
import { api } from '../api.js'

const hoje = new Date().toISOString().split('T')[0]

function Campo({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5">
        {label}
      </label>
      {children}
    </div>
  )
}

const inp = "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 text-sm focus:outline-none focus:border-green-500 focus:bg-white transition-all"

export default function Ordenha() {
  const [animais, setAnimais]   = useState([])
  const [form, setForm]         = useState({ data: hoje, id_animal: '', nome_animal: '', leite: '', racao: '', turno: 'manhã', obs: '' })
  const [loading, setLoading]   = useState(false)
  const [sucesso, setSucesso]   = useState('')
  const [erro, setErro]         = useState('')
  const [historico, setHistorico] = useState([])

  useEffect(() => {
    api.animais().then(a => setAnimais(a.filter(x => x.status === 'Lactação'))).catch(() => {})
    api.producao(3).then(setHistorico).catch(() => {})
  }, [])

  function setAnimal(id) {
    const a = animais.find(x => x.id === id || x.nome === id)
    setForm(f => ({ ...f, id_animal: a?.id || id, nome_animal: a?.nome || id }))
  }

  async function salvar(e) {
    e.preventDefault()
    if (!form.nome_animal) { setErro('Selecione um animal'); return }
    if (!form.leite || isNaN(form.leite)) { setErro('Informe os litros'); return }
    setLoading(true); setErro(''); setSucesso('')
    try {
      await api.registrarProducao({ ...form, leite: parseFloat(form.leite), racao: parseFloat(form.racao) || 0 })
      setSucesso(`${form.nome_animal} — ${form.leite}L registrado com sucesso!`)
      setForm(f => ({ ...f, id_animal: '', nome_animal: '', leite: '', racao: '', obs: '' }))
      api.producao(3).then(setHistorico).catch(() => {})
    } catch (err) {
      setErro(err.message)
    } finally {
      setLoading(false)
    }
  }

  const totalHoje = historico
    .filter(r => r.data === hoje)
    .reduce((s, r) => s + (r.leite || 0), 0)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-800">Registrar Ordenha</h2>
        <p className="text-slate-400 text-sm mt-0.5">Informe a produção de leite por animal</p>
      </div>

      {totalHoje > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-2xl px-5 py-4 flex items-center gap-4">
          <span className="text-3xl">🥛</span>
          <div>
            <div className="text-green-800 font-extrabold text-xl">{totalHoje.toFixed(1)} L</div>
            <div className="text-green-600 text-sm">produzidos hoje</div>
          </div>
        </div>
      )}

      <div className="bg-white border border-slate-100 rounded-2xl shadow-sm p-5 md:p-6 space-y-4">
        <h3 className="font-bold text-slate-700 text-base">Novo registro</h3>

        {sucesso && (
          <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 rounded-xl px-4 py-3 text-sm font-semibold">
            ✅ {sucesso}
          </div>
        )}

        <form onSubmit={salvar} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Campo label="Data">
              <input type="date" value={form.data} className={inp}
                     onChange={e => setForm(f => ({ ...f, data: e.target.value }))} />
            </Campo>
            <Campo label="Turno">
              <select value={form.turno} className={inp}
                      onChange={e => setForm(f => ({ ...f, turno: e.target.value }))}>
                {['manhã', 'tarde', 'noite'].map(t => <option key={t}>{t}</option>)}
              </select>
            </Campo>
          </div>

          <Campo label="Animal em lactação">
            <select value={form.id_animal} className={inp}
                    onChange={e => setAnimal(e.target.value)}>
              <option value="">Selecione o animal...</option>
              {animais.map(a => (
                <option key={a.id || a.nome} value={a.id || a.nome}>{a.nome}</option>
              ))}
            </select>
          </Campo>

          <div className="grid grid-cols-2 gap-4">
            <Campo label="Litros de leite">
              <input type="number" step="0.1" min="0" placeholder="0.0" inputMode="decimal"
                     value={form.leite} className={inp}
                     onChange={e => setForm(f => ({ ...f, leite: e.target.value }))} />
            </Campo>
            <Campo label="Ração (kg)">
              <input type="number" step="0.1" min="0" placeholder="0.0" inputMode="decimal"
                     value={form.racao} className={inp}
                     onChange={e => setForm(f => ({ ...f, racao: e.target.value }))} />
            </Campo>
          </div>

          <Campo label="Observação (opcional)">
            <input type="text" placeholder="Ex: mastite leve, comportamento diferente..."
                   value={form.obs} className={inp}
                   onChange={e => setForm(f => ({ ...f, obs: e.target.value }))} />
          </Campo>

          {erro && (
            <p className="text-red-500 text-sm bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-center">{erro}</p>
          )}

          <button type="submit" disabled={loading}
            className="w-full bg-green-600 hover:bg-green-500 active:bg-green-700 disabled:opacity-60 text-white font-bold py-3.5 rounded-xl transition-colors text-sm shadow-sm">
            {loading ? 'Salvando...' : '💾 Salvar Ordenha'}
          </button>
        </form>
      </div>

      {historico.length > 0 && (
        <div className="bg-white border border-slate-100 rounded-2xl shadow-sm p-5">
          <h3 className="font-bold text-slate-700 text-xs uppercase tracking-widest mb-4">Últimos registros</h3>
          <div className="space-y-2">
            {historico.slice(0, 8).map((r, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-3 bg-slate-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center text-sm">🐄</div>
                  <div>
                    <div className="font-semibold text-slate-800 text-sm">{r.nome_animal}</div>
                    <div className="text-slate-400 text-xs">{r.data} · {r.turno}</div>
                  </div>
                </div>
                <div className="text-green-700 font-extrabold text-sm">{r.leite} L</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
