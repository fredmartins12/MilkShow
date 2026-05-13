import { useEffect, useState } from 'react'
import {
  ComposedChart, Area, Line, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Plus, RefreshCw, Trash2, Download } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Btn, T, hoje, ChartControls, csvDownload,
} from '../ui.jsx'

const TURNOS = ['manhã', 'tarde', 'noite']
const COLOR  = '#3b82f6'

function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}` }}
         className="rounded px-3 py-2 text-[11px]">
      <p className="text-slate-500 font-mono mb-1">{label}</p>
      <p className="font-mono font-semibold tabular-nums" style={{ color: COLOR }}>
        {payload[0]?.value} L
      </p>
    </div>
  )
}

function ProdChart({ data, tipo }) {
  const tick = { fill: '#475569', fontSize: 10, fontFamily: 'monospace' }
  const grid = <CartesianGrid strokeDasharray="2 4" stroke={T.border} />
  const x    = <XAxis dataKey="dia" tick={tick} />
  const y    = <YAxis tick={tick} />
  const tip  = <Tooltip content={<ChartTip />} />

  if (tipo === 'barra') return (
    <ComposedChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
      {grid}{x}{y}{tip}
      <Bar dataKey="litros" fill={COLOR} radius={[3, 3, 0, 0]} maxBarSize={20} />
    </ComposedChart>
  )
  if (tipo === 'linha') return (
    <ComposedChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
      {grid}{x}{y}{tip}
      <Line type="monotone" dataKey="litros" stroke={COLOR} strokeWidth={2} dot={false} />
    </ComposedChart>
  )
  return (
    <ComposedChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
      <defs>
        <linearGradient id="gProd2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={COLOR} stopOpacity={0.15} />
          <stop offset="100%" stopColor={COLOR} stopOpacity={0} />
        </linearGradient>
      </defs>
      {grid}{x}{y}{tip}
      <Area type="monotone" dataKey="litros" stroke={COLOR} strokeWidth={1.5}
            fill="url(#gProd2)" dot={false} />
    </ComposedChart>
  )
}

export default function TabProducao() {
  const [registros, setRegistros] = useState([])
  const [animais, setAnimais]     = useState([])
  const [chartData, setChartData] = useState([])
  const [loading, setLoading]     = useState(true)
  const [erro, setErro]           = useState('')
  const [toast, setToast]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [confirmDel, setDel]      = useState(null)
  const [saving, setSaving]       = useState(false)
  const [periodo, setPeriodo]     = useState(30)
  const [tipo, setTipo]           = useState('area')
  const [estoqueRacao, setEstRacao] = useState([])
  const [form, setForm]           = useState({
    data: hoje(), id_animal: '', nome_animal: '', leite: '', racao: '', turno: 'manhã', obs: '', estoqueId: '',
  })

  async function carregar(dias = periodo) {
    setLoading(true); setErro('')
    try {
      const [p, a] = await Promise.all([api.producao(dias), api.animais()])
      setRegistros(p)
      setAnimais(a.filter(x => x.status === 'Lactação'))
      buildChart(p)
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  function buildChart(data) {
    const porDia = {}
    data.forEach(r => { porDia[r.data] = (porDia[r.data] || 0) + (r.leite || 0) })
    setChartData(
      Object.entries(porDia)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([data, litros]) => ({ dia: data.slice(5), litros: +litros.toFixed(1) }))
    )
  }

  useEffect(() => { carregar(periodo) }, [periodo])

  function setAnimal(id) {
    const a = animais.find(x => (x.id || x.nome) === id)
    setForm(f => ({ ...f, id_animal: a?.id || id, nome_animal: a?.nome || id }))
  }

  async function abrirModal() {
    setModal(true)
    try {
      const est = await api.estoque()
      setEstRacao(est.filter(e => e.categoria === 'Ração' && (e.qtd || 0) > 0))
    } catch { setEstRacao([]) }
  }

  async function salvar(e) {
    e.preventDefault()
    if (!form.nome_animal || !form.leite || isNaN(form.leite)) return
    setSaving(true)
    try {
      const racaoKg = parseFloat(form.racao) || 0
      await api.registrarProducao({ ...form, leite: parseFloat(form.leite), racao: racaoKg })
      // Debitar ração do armazém se selecionado
      if (form.estoqueId && racaoKg > 0) {
        const item = estoqueRacao.find(e => e.id === form.estoqueId)
        if (item) {
          const novaQtd = Math.max(0, (item.qtd || 0) - racaoKg)
          await api.atualizarEstoque(item.id, { ...item, qtd: novaQtd })
        }
      }
      setToast({ msg: `${form.nome_animal} — ${form.leite}L registrado`, tipo: 'ok' })
      setModal(false)
      setForm(f => ({ ...f, id_animal: '', nome_animal: '', leite: '', racao: '', obs: '', estoqueId: '' }))
      carregar(periodo)
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function remover(r) {
    try {
      await api.removerProducao(r.id)
      setToast({ msg: `Registro de ${r.nome_animal} removido`, tipo: 'ok' })
      carregar(periodo)
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setDel(null) }
  }

  const totalPeriodo = registros.reduce((s, r) => s + (r.leite || 0), 0)
  const mediaDia     = chartData.length > 0 ? totalPeriodo / chartData.length : 0

  if (loading) return <Loading />

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={() => carregar(periodo)} />}

      {/* Sumário */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: `TOTAL ${periodo}D`,   value: `${totalPeriodo.toFixed(0)} L` },
          { label: 'MÉDIA DIÁRIA',        value: `${mediaDia.toFixed(1)} L` },
          { label: 'ANIMAIS LACT.',       value: `${animais.length}` },
          { label: 'REGISTROS',           value: `${registros.length}` },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : '' }}>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-2">{k.label}</p>
            <p className="text-2xl font-mono font-semibold tabular-nums text-slate-100">{k.value}</p>
          </div>
        ))}
      </div>

      {/* Gráfico */}
      <div className="px-5 pt-4 pb-3 shrink-0 space-y-3" style={{ borderBottom: `1px solid ${T.border}` }}>
        <ChartControls
          periodo={periodo} setPeriodo={setPeriodo}
          tipo={tipo}       setTipo={setTipo}
          periodos={[7, 14, 30, 60, 90]}
        />
        <ResponsiveContainer width="100%" height={130}>
          <ProdChart data={chartData} tipo={tipo} />
        </ResponsiveContainer>
      </div>

      {/* Header tabela */}
      <SectionHeader
        title="REGISTROS DE PRODUÇÃO"
        sub={`${registros.length} entradas · últimos ${periodo} dias`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={() => csvDownload(
              registros.map(r => ({ data: r.data, animal: r.nome_animal, turno: r.turno, litros: r.leite, racao_kg: r.racao || 0, obs: r.obs || '' })),
              `producao-${periodo}d.csv`
            )}>
              <Download size={11} /> CSV
            </Btn>
            <Btn variant="ghost" size="xs" onClick={() => carregar(periodo)}><RefreshCw size={11} /></Btn>
            <Btn variant="primary" size="xs" onClick={abrirModal}><Plus size={11} />Registrar</Btn>
          </div>
        }
      />

      {/* Tabela */}
      <div className="overflow-auto flex-1">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.border}` }}>
              {['DATA', 'ANIMAL', 'TURNO', 'LEITE', 'RAÇÃO', 'OBS', ''].map(h =>
                <th key={h} className="text-left text-slate-700 px-4 py-2 font-normal tracking-wider text-[10px]">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {registros.slice(0, 150).map((r, i) => (
              <tr key={r.id || i} className="hover:bg-white/[0.02] transition-colors"
                  style={{ borderBottom: `1px solid ${T.border2}` }}>
                <td className="px-4 py-2.5 text-slate-500">{r.data}</td>
                <td className="px-4 py-2.5 text-slate-200 font-semibold">{r.nome_animal}</td>
                <td className="px-4 py-2.5 text-slate-500 capitalize">{r.turno}</td>
                <td className="px-4 py-2.5 text-blue-400 font-semibold tabular-nums">{Number(r.leite).toFixed(1)} L</td>
                <td className="px-4 py-2.5 text-slate-500">{r.racao ? `${r.racao} kg` : '—'}</td>
                <td className="px-4 py-2.5 text-slate-600">{r.obs || '—'}</td>
                <td className="px-4 py-2.5">
                  {r.id && (
                    <button onClick={() => setDel(r)}
                      className="p-1.5 rounded text-slate-700 hover:text-red-400 transition-colors"
                      aria-label="Remover">
                      <Trash2 size={12} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Confirm delete */}
      <Modal open={!!confirmDel} onClose={() => setDel(null)} title="Remover registro">
        <p className="text-slate-400 text-sm">
          Remover o registro de{' '}
          <strong className="text-slate-200">{confirmDel?.nome_animal}</strong>{' '}
          em <strong className="text-slate-200">{confirmDel?.data}</strong> ({confirmDel?.leite}L)?
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Btn variant="ghost" onClick={() => setDel(null)}>Cancelar</Btn>
          <Btn variant="danger" onClick={() => remover(confirmDel)}>
            <Trash2 size={12} /> Remover
          </Btn>
        </div>
      </Modal>

      {/* Modal de registro */}
      <Modal open={modal} onClose={() => { setModal(false); setEstRacao([]) }} title="REGISTRAR ORDENHA">
        <form onSubmit={salvar} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Data">
              <Input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} />
            </Field>
            <Field label="Turno">
              <Select value={form.turno} onChange={e => setForm(f => ({ ...f, turno: e.target.value }))}>
                {TURNOS.map(t => <option key={t}>{t}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Animal">
            <Select value={form.id_animal} onChange={e => setAnimal(e.target.value)}>
              <option value="">Selecione...</option>
              {animais.map(a => <option key={a.id || a.nome} value={a.id || a.nome}>{a.nome}</option>)}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Litros de leite">
              <Input type="number" step="0.1" min="0" placeholder="0.0" inputMode="decimal"
                     value={form.leite} onChange={e => setForm(f => ({ ...f, leite: e.target.value }))} />
            </Field>
            <Field label="Ração (kg)">
              <Input type="number" step="0.1" min="0" placeholder="0.0" inputMode="decimal"
                     value={form.racao} onChange={e => setForm(f => ({ ...f, racao: e.target.value }))} />
            </Field>
          </div>
          <Field label="Observação">
            <Input type="text" placeholder="Opcional..." value={form.obs}
                   onChange={e => setForm(f => ({ ...f, obs: e.target.value }))} />
          </Field>
          {estoqueRacao.length > 0 && parseFloat(form.racao) > 0 && (
            <Field label="Debitar ração do armazém">
              <Select value={form.estoqueId} onChange={e => setForm(f => ({ ...f, estoqueId: e.target.value }))}>
                <option value="">Não debitar</option>
                {estoqueRacao.map(e => (
                  <option key={e.id} value={e.id}>{e.item} ({e.qtd} {e.un})</option>
                ))}
              </Select>
            </Field>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(false)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>
              {saving ? 'Salvando...' : 'Salvar registro'}
            </Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
