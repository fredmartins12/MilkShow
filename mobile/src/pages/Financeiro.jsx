import { useEffect, useState } from 'react'
import { api } from '../api.js'

const hoje = new Date().toISOString().split('T')[0]

const CATS_DESPESA = ['Ração / Nutrição','Medicamento / Sanitário','Mão de Obra',
                      'Infraestrutura','Energia','Compra de Animais','Outros']
const CATS_RECEITA = ['Venda de Leite','Venda de Animais','Serviços','Outras Receitas']

function Campo({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5">{label}</label>
      {children}
    </div>
  )
}

const inp = "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 text-sm focus:outline-none focus:border-green-500 focus:bg-white transition-all"

export default function Financeiro() {
  const [tipo, setTipo]           = useState('despesa')
  const [form, setForm]           = useState({ data: hoje, descricao: '', cat: '', valor: '' })
  const [loading, setLoading]     = useState(false)
  const [sucesso, setSucesso]     = useState('')
  const [erro, setErro]           = useState('')
  const [historico, setHistorico] = useState([])

  useEffect(() => { api.financeiro(14).then(setHistorico).catch(() => {}) }, [])

  const cats = tipo === 'despesa' ? CATS_DESPESA : CATS_RECEITA

  async function salvar(e) {
    e.preventDefault()
    if (!form.cat)    { setErro('Selecione uma categoria'); return }
    if (!form.valor || isNaN(form.valor)) { setErro('Informe o valor'); return }
    if (!form.descricao) { setErro('Informe a descrição'); return }
    setLoading(true); setErro(''); setSucesso('')
    try {
      await api.registrarFinanceiro({ ...form, valor: parseFloat(form.valor), tipo })
      setSucesso(`${tipo === 'despesa' ? 'Despesa' : 'Receita'} de R$ ${form.valor} registrada!`)
      setForm({ data: hoje, descricao: '', cat: '', valor: '' })
      api.financeiro(14).then(setHistorico).catch(() => {})
    } catch (err) {
      setErro(err.message)
    } finally {
      setLoading(false)
    }
  }

  const totalRec  = historico.filter(r => CATS_RECEITA.includes(r.cat)).reduce((s, r) => s + r.valor, 0)
  const totalDesp = historico.filter(r => !CATS_RECEITA.includes(r.cat)).reduce((s, r) => s + r.valor, 0)
  const fmt = n => `R$ ${Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-800">Financeiro</h2>
        <p className="text-slate-400 text-sm mt-0.5">Lançamentos dos últimos 14 dias</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-green-50 border border-green-100 rounded-2xl p-4">
          <div className="text-xs font-bold text-green-600 uppercase tracking-wide mb-1">Receitas</div>
          <div className="text-lg font-extrabold text-green-800">{fmt(totalRec)}</div>
        </div>
        <div className="bg-red-50 border border-red-100 rounded-2xl p-4">
          <div className="text-xs font-bold text-red-600 uppercase tracking-wide mb-1">Despesas</div>
          <div className="text-lg font-extrabold text-red-800">{fmt(totalDesp)}</div>
        </div>
        <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Saldo</div>
          <div className={`text-lg font-extrabold ${totalRec - totalDesp >= 0 ? 'text-blue-800' : 'text-red-700'}`}>
            {fmt(totalRec - totalDesp)}
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-100 rounded-2xl shadow-sm p-5 space-y-4">
        <h3 className="font-bold text-slate-700 text-base">Novo lançamento</h3>

        <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
          {[['despesa','Despesa'],['receita','Receita']].map(([v, l]) => (
            <button key={v} type="button"
              onClick={() => { setTipo(v); setForm(f => ({ ...f, cat: '' })) }}
              className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all
                ${tipo === v
                  ? v === 'despesa' ? 'bg-red-600 text-white shadow-sm' : 'bg-green-600 text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'}`}>
              {l}
            </button>
          ))}
        </div>

        {sucesso && (
          <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl px-4 py-3 text-sm font-semibold">
            {sucesso}
          </div>
        )}

        <form onSubmit={salvar} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Campo label="Data">
              <input type="date" value={form.data} className={inp}
                     onChange={e => setForm(f => ({ ...f, data: e.target.value }))} />
            </Campo>
            <Campo label="Categoria">
              <select value={form.cat} className={inp}
                      onChange={e => setForm(f => ({ ...f, cat: e.target.value }))}>
                <option value="">Selecione...</option>
                {cats.map(c => <option key={c}>{c}</option>)}
              </select>
            </Campo>
          </div>

          <Campo label="Descrição">
            <input type="text" placeholder="Ex: Compra de ração..." value={form.descricao} className={inp}
                   onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))} />
          </Campo>

          <Campo label="Valor (R$)">
            <input type="number" step="0.01" min="0" placeholder="0,00" inputMode="decimal"
                   value={form.valor}
                   className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-4 text-slate-800 text-2xl font-extrabold focus:outline-none focus:border-green-500 transition-all text-center"
                   onChange={e => setForm(f => ({ ...f, valor: e.target.value }))} />
          </Campo>

          {erro && <p className="text-red-500 text-sm bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-center">{erro}</p>}

          <button type="submit" disabled={loading}
            className={`w-full font-bold py-3.5 rounded-xl text-white text-sm disabled:opacity-60
              ${tipo === 'despesa' ? 'bg-red-600 hover:bg-red-500' : 'bg-green-600 hover:bg-green-500'}`}>
            {loading ? 'Salvando...' : `Registrar ${tipo === 'despesa' ? 'Despesa' : 'Receita'}`}
          </button>
        </form>
      </div>

      {historico.length > 0 && (
        <div className="bg-white border border-slate-100 rounded-2xl shadow-sm p-5">
          <h3 className="font-bold text-slate-700 text-xs uppercase tracking-widest mb-4">Últimos lançamentos</h3>
          <div className="space-y-2">
            {historico.slice(0, 12).map((r, i) => {
              const isRec = CATS_RECEITA.includes(r.cat)
              return (
                <div key={i} className="flex items-center justify-between px-4 py-3 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${isRec ? 'bg-green-100' : 'bg-red-100'}`}>
                      {isRec ? '💰' : '💸'}
                    </div>
                    <div>
                      <div className="font-semibold text-slate-800 text-sm">{r.descricao || r.cat}</div>
                      <div className="text-slate-400 text-xs">{r.data} · {r.cat}</div>
                    </div>
                  </div>
                  <div className={`font-extrabold text-sm ${isRec ? 'text-green-700' : 'text-red-600'}`}>
                    {isRec ? '+' : '-'}{fmt(r.valor)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
