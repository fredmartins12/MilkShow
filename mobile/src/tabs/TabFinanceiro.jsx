import { useEffect, useState } from 'react'
import {
  ComposedChart, Area, Line, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Plus, RefreshCw, Trash2, Pencil, Download, Wallet } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, Empty, T, hoje, fmtBRL, ChartControls, csvDownload,
} from '../ui.jsx'

const CATEGORIAS_REC = ['Venda de Leite', 'Venda de Animal', 'Outros']
const CATEGORIAS_DES = ['Ração', 'Medicamentos', 'Mão de Obra', 'Energia', 'Manutenção', 'Outros']
const TIPOS          = ['receita', 'despesa']
const FORM_VAZIO     = { tipo: 'receita', categoria: 'Venda de Leite', valor: '', data: hoje(), descricao: '', obs: '' }

// ─── TOOLTIP ─────────────────────────────────────────────────────────────────
function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}` }}
         className="rounded-xl px-3 py-2.5 text-[11px] shadow-lg">
      <p className="text-slate-500 mb-1">{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ background: p.color }} />
          <span className="text-slate-400">{p.name}:</span>
          <span className="text-slate-100 font-semibold font-mono tabular-nums">{fmtBRL(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ─── GRÁFICO DUPLO (receita + despesa) ───────────────────────────────────────
function FinChart({ data, tipo }) {
  const tick = { fill: '#475569', fontSize: 10, fontFamily: 'var(--font-sans)' }
  const grid = <CartesianGrid strokeDasharray="2 4" stroke={T.border} />
  const x    = <XAxis dataKey="dia" tick={tick} />
  const y    = <YAxis tick={tick} />
  const tip  = <Tooltip content={<ChartTip />} />

  if (tipo === 'barra') return (
    <ComposedChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
      {grid}{x}{y}{tip}
      <Bar dataKey="despesa" name="Despesa" fill="#ef4444" radius={[3, 3, 0, 0]} maxBarSize={14} />
      <Bar dataKey="receita" name="Receita" fill="#10b981" radius={[3, 3, 0, 0]} maxBarSize={14} />
    </ComposedChart>
  )

  if (tipo === 'linha') return (
    <ComposedChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
      {grid}{x}{y}{tip}
      <Line type="monotone" dataKey="despesa" name="Despesa" stroke="#ef4444" strokeWidth={1.5} dot={false} />
      <Line type="monotone" dataKey="receita" name="Receita" stroke="#10b981" strokeWidth={2} dot={false} />
    </ComposedChart>
  )

  // área (padrão)
  return (
    <ComposedChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
      <defs>
        <linearGradient id="gRec2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#10b981" stopOpacity={0.15} />
          <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="gDes2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#ef4444" stopOpacity={0.12} />
          <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
        </linearGradient>
      </defs>
      {grid}{x}{y}{tip}
      <Area type="monotone" dataKey="despesa" name="Despesa" stroke="#ef4444" strokeWidth={1}
            fill="url(#gDes2)" dot={false} />
      <Area type="monotone" dataKey="receita" name="Receita" stroke="#10b981" strokeWidth={1.5}
            fill="url(#gRec2)" dot={false} />
    </ComposedChart>
  )
}

// ─── TAB ─────────────────────────────────────────────────────────────────────
export default function TabFinanceiro() {
  const [registros, setRegistros] = useState([])
  const [chartData, setChartData] = useState([])
  const [loading, setLoading]     = useState(true)
  const [erro, setErro]           = useState('')
  const [toast, setToast]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [editando, setEditando]   = useState(null)
  const [confirmDel, setDel]      = useState(null)
  const [saving, setSaving]       = useState(false)
  const [periodo, setPeriodo]     = useState(30)
  const [tipo, setTipo]           = useState('area')
  const [form, setForm]           = useState(FORM_VAZIO)

  function buildChart(data) {
    const porDia = {}
    data.forEach(r => {
      if (!porDia[r.data]) porDia[r.data] = { receita: 0, despesa: 0 }
      if (r.tipo === 'receita') porDia[r.data].receita += r.valor || 0
      else porDia[r.data].despesa += r.valor || 0
    })
    setChartData(
      Object.entries(porDia)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([data, v]) => ({
          dia: data.slice(5),
          receita: +v.receita.toFixed(2),
          despesa: +v.despesa.toFixed(2),
        }))
    )
  }

  async function carregar(dias = periodo) {
    setLoading(true); setErro('')
    try {
      const r = await api.financeiro(dias)
      setRegistros(r)
      buildChart(r)
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar(periodo) }, [periodo])

  useEffect(() => {
    const onRefresh = () => carregar(periodo)
    window.addEventListener('milkshow:refresh', onRefresh)
    return () => window.removeEventListener('milkshow:refresh', onRefresh)
  }, [periodo])

  function abrirNovo() {
    setEditando(null)
    setForm(FORM_VAZIO)
    setModal(true)
  }

  function abrirEditar(r) {
    setEditando(r)
    setForm({
      tipo:      r.tipo || 'receita',
      categoria: r.categoria || (r.tipo === 'receita' ? CATEGORIAS_REC[0] : CATEGORIAS_DES[0]),
      valor:     r.valor != null ? String(r.valor) : '',
      data:      r.data || hoje(),
      descricao: r.descricao || '',
      obs:       r.obs || '',
    })
    setModal(true)
  }

  async function salvar(e) {
    e.preventDefault()
    if (!form.valor || isNaN(form.valor)) return
    setSaving(true)
    try {
      const body = { ...form, valor: parseFloat(form.valor) }
      if (editando) {
        await api.atualizarFinanceiro(editando.id, body)
        setToast({ msg: 'Lançamento atualizado', tipo: 'ok' })
      } else {
        await api.registrarFinanceiro(body)
        setToast({ msg: `${form.tipo === 'receita' ? 'Receita' : 'Despesa'} registrada`, tipo: 'ok' })
      }
      setModal(false)
      carregar(periodo)
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function remover(r) {
    try {
      await api.removerFinanceiro(r.id)
      setToast({ msg: 'Lançamento removido', tipo: 'ok' })
      carregar(periodo)
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setDel(null) }
  }

  if (loading) return <Loading />

  const totalRec = registros.filter(r => r.tipo === 'receita').reduce((s, r) => s + (r.valor || 0), 0)
  const totalDes = registros.filter(r => r.tipo === 'despesa').reduce((s, r) => s + (r.valor || 0), 0)
  const saldo    = totalRec - totalDes
  const margem   = totalRec > 0 ? ((saldo / totalRec) * 100) : 0

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={() => carregar(periodo)} />}

      {/* Sumário */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: `RECEITAS ${periodo}D`, value: fmtBRL(totalRec), accent: '#10b981' },
          { label: `DESPESAS ${periodo}D`, value: fmtBRL(totalDes), accent: '#ef4444' },
          { label: 'SALDO',               value: fmtBRL(saldo),    accent: saldo >= 0 ? '#10b981' : '#ef4444' },
          { label: 'MARGEM',              value: `${margem.toFixed(1)}%`, accent: margem >= 0 ? '#22c55e' : '#ef4444' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4 pt-3 flex flex-col gap-1"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : '', borderTop: `2px solid ${k.accent}` }}>
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">{k.label}</p>
            <p className="text-xl font-mono font-semibold tabular-nums" style={{ color: k.accent }}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Filtro de período */}
      <div className="flex items-center gap-2 px-5 py-2 shrink-0" style={{ borderBottom: `1px solid ${T.border}`, background: T.surface }}>
        <span className="text-[11px] font-medium uppercase tracking-widest mr-1" style={{ color: T.muted }}>Período:</span>
        {[7, 14, 30, 60, 90].map(p => (
          <button key={p} onClick={() => setPeriodo(p)}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
            style={{
              background: periodo === p ? T.brand : T.s3,
              color: periodo === p ? '#fff' : T.sub,
              boxShadow: periodo === p ? '0 2px 8px rgba(34,197,94,0.35)' : 'none',
              border: `1px solid ${periodo === p ? T.brand2 : T.border}`,
            }}>
            {p}d
          </button>
        ))}
      </div>

      {/* Gráfico */}
      <div className="px-5 pt-4 pb-4 shrink-0 space-y-3" style={{ borderBottom: `1px solid ${T.border}`, background: T.s2 }}>
        <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">
          Receita vs. Despesa — {periodo} dias
        </p>
        <ChartControls
          periodo={periodo} setPeriodo={setPeriodo}
          tipo={tipo}       setTipo={setTipo}
          periodos={[7, 14, 30, 60, 90]}
        />
        <ResponsiveContainer width="100%" height={130}>
          <FinChart data={chartData} tipo={tipo} />
        </ResponsiveContainer>
      </div>

      <SectionHeader
        title="REGISTROS FINANCEIROS"
        sub={`${registros.length} lançamentos · últimos ${periodo} dias`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={() => csvDownload(
              registros.map(r => ({ data: r.data, tipo: r.tipo, categoria: r.categoria || '', descricao: r.descricao || '', valor: r.valor, obs: r.obs || '' })),
              `financeiro-${periodo}d.csv`
            )}>
              <Download size={11} /> CSV
            </Btn>
            <Btn variant="ghost" size="xs" onClick={() => carregar(periodo)}><RefreshCw size={11} /></Btn>
            <Btn variant="primary" size="xs" onClick={abrirNovo}><Plus size={11} />Lançamento</Btn>
          </div>
        }
      />

      <div className="overflow-auto flex-1">
        {registros.length === 0 ? (
          <Empty
            icon={Wallet}
            title="Nenhum lançamento"
            msg={`Sem registros nos últimos ${periodo} dias.`}
            accentColor="#10b981"
            action={<Btn variant="primary" size="sm" onClick={abrirNovo}><Plus size={12} /> Novo lançamento</Btn>}
          />
        ) : (
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: T.s3, borderBottom: `1px solid ${T.border}` }}>
              {['DATA', 'TIPO', 'CATEGORIA', 'DESCRIÇÃO', 'VALOR', ''].map(h =>
                <th key={h} className="text-left text-slate-500 px-4 py-2.5 font-medium text-[11px] tracking-wider uppercase">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {registros.slice(0, 150).map((r, i) => (
              <tr key={r.id || i} className="transition-colors hover:brightness-95"
                  style={{ borderBottom: `1px solid ${T.border2}`, background: i % 2 === 0 ? T.surface : T.s2 }}>
                <td className="px-4 py-2.5 text-slate-500">{r.data}</td>
                <td className="px-4 py-2.5 font-semibold uppercase tracking-wider text-[10px]"
                    style={{ color: r.tipo === 'receita' ? T.brand : T.red }}>
                  {r.tipo}
                </td>
                <td className="px-4 py-2.5 text-slate-400">{r.categoria || '—'}</td>
                <td className="px-4 py-2.5 text-slate-200 max-w-[180px] truncate">{r.descricao || '—'}</td>
                <td className="px-4 py-2.5 font-semibold tabular-nums"
                    style={{ color: r.tipo === 'receita' ? T.brand : T.red }}>
                  {r.tipo === 'despesa' ? '−' : '+'}{fmtBRL(r.valor)}
                </td>
                <td className="px-4 py-2.5">
                  {r.id && (
                    <div className="flex items-center gap-1">
                      <button onClick={() => abrirEditar(r)}
                        className="p-1.5 rounded text-slate-700 hover:text-slate-300 transition-colors"
                        aria-label="Editar">
                        <Pencil size={12} />
                      </button>
                      <button onClick={() => setDel(r)}
                        className="p-1.5 rounded text-slate-700 hover:text-red-400 transition-colors"
                        aria-label="Remover">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ background: T.s3, borderTop: `2px solid ${T.border}` }}>
              <td colSpan={4} className="px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Saldo do período
              </td>
              <td className="px-4 py-3 font-bold tabular-nums text-sm"
                  style={{ color: saldo >= 0 ? T.brand : T.red }}>
                {saldo >= 0 ? '+' : '−'}{fmtBRL(Math.abs(saldo))}
              </td>
              <td />
            </tr>
          </tfoot>
        </table>
        )}
      </div>

      {/* Confirm delete */}
      <Modal open={!!confirmDel} onClose={() => setDel(null)} title="Remover lançamento">
        <p className="text-slate-400 text-sm">
          Remover <strong className="text-slate-200">{confirmDel?.descricao || confirmDel?.categoria}</strong>{' '}
          de {confirmDel ? fmtBRL(confirmDel.valor) : ''}?
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Btn variant="ghost" onClick={() => setDel(null)}>Cancelar</Btn>
          <Btn variant="danger" onClick={() => remover(confirmDel)}>
            <Trash2 size={12} /> Remover
          </Btn>
        </div>
      </Modal>

      {/* Modal novo/editar */}
      <Modal open={modal} onClose={() => setModal(false)}
        title={editando ? 'Editar Lançamento' : (form.tipo === 'receita' ? 'Nova Receita' : 'Nova Despesa')}
        accentColor={form.tipo === 'receita' ? '#10b981' : '#ef4444'}>
        <form onSubmit={salvar} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo">
              <Select value={form.tipo}
                onChange={e => setForm(f => ({
                  ...f,
                  tipo: e.target.value,
                  categoria: e.target.value === 'receita' ? CATEGORIAS_REC[0] : CATEGORIAS_DES[0],
                }))}>
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Categoria">
              <Select value={form.categoria} onChange={e => setForm(f => ({ ...f, categoria: e.target.value }))}>
                {(form.tipo === 'receita' ? CATEGORIAS_REC : CATEGORIAS_DES).map(c => <option key={c}>{c}</option>)}
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Valor (R$) *">
              <Input type="number" step="0.01" min="0" placeholder="0,00" inputMode="decimal"
                     value={form.valor} onChange={e => setForm(f => ({ ...f, valor: e.target.value }))} />
            </Field>
            <Field label="Data">
              <Input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} />
            </Field>
          </div>
          <Field label="Descrição">
            <Input value={form.descricao} onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))}
              placeholder="Ex: Venda 150L — Laticínio Santa Fé" />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={e => setForm(f => ({ ...f, obs: e.target.value }))} rows={2} />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(false)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>
              {saving ? 'Salvando...' : editando ? 'Salvar alterações' : 'Registrar'}
            </Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
