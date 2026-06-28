/**
 * TabRebanho — Gestão completa do rebanho
 * - Lista com busca + filtros por status e raça
 * - Clique no animal → painel lateral com perfil completo:
 *     ficha, edição completa (todos os campos), produção 30d, histórico sanitário
 */

import { useEffect, useState, useMemo } from 'react'
import {
  Search, X, RefreshCw, Trash2, Pencil, Check, Plus,
  Milk, CalendarDays, Clock, TrendingUp, ShieldCheck, ChevronRight, AlertTriangle,
} from 'lucide-react'
import { IconRebanho } from '../components/IconRebanho.jsx'
import {
  ComposedChart, AreaChart, Area, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, Empty,
  T, fmtDate, dataParto, idadeDias,
} from '../ui.jsx'

const ANIMAL_VAZIO = { nome: '', raca: 'Holandesa', status: 'Lactação', sexo: 'Fêmea', nascimento: '', mae: '', ins: '', obs: '' }

const STATUS_OPTS = ['Todos', 'Lactação', 'Seca', 'Gestação', 'Novilha', 'Bezerro']
const RACAS_OPTS  = ['Todas', 'Holandesa', 'Jersey', 'Girolando', 'Gir', 'Nelore Leiteiro', 'Pardo Suíço', 'Outra']
const STATUS_NEW  = ['Lactação', 'Seca', 'Gestação', 'Novilha', 'Bezerro']
const SEXOS       = ['Fêmea', 'Macho']

const STATUS_COLOR = {
  'Lactação': { bg: 'rgba(22,163,74,0.12)',  border: '#16a34a40', dot: '#16a34a' },
  'Seca':     { bg: 'rgba(234,179,8,0.10)',  border: '#ca8a0440', dot: '#ca8a04' },
  'Gestação': { bg: 'rgba(59,130,246,0.10)', border: '#22c55e40', dot: '#22c55e' },
  'Novilha':  { bg: 'rgba(167,139,250,0.10)',border: '#7c3aed40', dot: '#a78bfa' },
  'Bezerro':  { bg: 'rgba(251,146,60,0.10)', border: '#ea580c40', dot: '#fb923c' },
}

function StatusPill({ status }) {
  const c = STATUS_COLOR[status] || { bg: 'rgba(100,116,139,0.1)', border: '#47556940', dot: '#64748b' }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium"
          style={{ background: c.bg, border: `1px solid ${c.border}` }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.dot }} />
      <span style={{ color: c.dot }}>{status}</span>
    </span>
  )
}

// ─── PAINEL LATERAL DE PERFIL ─────────────────────────────────────────────────
function AnimalPanel({ animal, onClose, onSaved, onDelete, sanitario }) {
  const [prod, setProd]         = useState([])
  const [loadProd, setLoadProd] = useState(true)
  const isNovo = !animal.id
  const [editMode, setEditMode] = useState(isNovo)
  const [saving, setSaving]     = useState(false)
  const [form, setForm]         = useState({})

  useEffect(() => {
    setForm({
      nome:       animal.nome || '',
      raca:       animal.raca || 'Holandesa',
      status:     animal.status || 'Lactação',
      sexo:       animal.sexo || 'Fêmea',
      nascimento: animal.nascimento || '',
      mae:        animal.mae || '',
      ins:        animal.ins || animal.inseminacao || '',
      obs:        animal.obs || '',
    })
    setEditMode(!animal.id)
  }, [animal])

  const [lacInfo, setLacInfo] = useState(null)

  useEffect(() => {
    setLoadProd(true)
    setLacInfo(null)
    api.lactacao(animal.nome, 120)
      .then(data => {
        setLacInfo(data)
        setProd(
          (data.serie || []).map(r => ({
            dia:      r.data?.slice(5) || '',
            dim:      r.dim,
            litros:   r.litros != null ? +r.litros.toFixed(1) : null,
            esperado: r.esperado != null ? +r.esperado.toFixed(1) : null,
          }))
        )
      })
      .catch(() => {
        // fallback to simple 30-day view
        api.producaoPorAnimal(animal.nome, 30)
          .then(p => {
            const porDia = {}
            p.forEach(r => { porDia[r.data] = (porDia[r.data] || 0) + (r.leite || 0) })
            setProd(
              Object.entries(porDia)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([d, l]) => ({ dia: d.slice(5), litros: +l.toFixed(1), esperado: null }))
            )
          })
          .catch(() => setProd([]))
      })
      .finally(() => setLoadProd(false))
  }, [animal.nome])

  function f(k, v) { setForm(p => ({ ...p, [k]: v })) }

  async function salvar() {
    if (!form.nome.trim()) return
    setSaving(true)
    try {
      await api.adicionarAnimal({ ...form, id: animal.id || undefined })
      setSaving(false)
      if (isNovo) { onSaved(true); onClose() }
      else { setEditMode(false); onSaved(false) }
    } catch (e) {
      setSaving(false)
    }
  }

  const totalProd  = prod.reduce((s, r) => s + r.litros, 0)
  const mediaProd  = prod.length ? (totalProd / prod.length).toFixed(1) : '—'
  const idade      = idadeDias(animal.nascimento)
  const parto      = dataParto(form.ins || animal.ins || animal.inseminacao)
  const sanAnimal  = sanitario.filter(s =>
    (s.animal || '').toLowerCase() === animal.nome.toLowerCase()
  ).slice(0, 5)

  const tickStyle = { fill: '#475569', fontSize: 10, fontFamily: 'monospace' }

  return (
    <div className="fixed inset-0 z-50 flex justify-end"
         style={{ background: 'rgba(2,8,4,0.7)', backdropFilter: 'blur(4px)' }}
         onClick={onClose}>
      <div className="h-full overflow-y-auto flex flex-col"
           style={{
             width: 'min(520px, 100vw)',
             background: '#061209',
             borderLeft: `1px solid ${T.border}`,
           }}
           onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-start justify-between p-5 shrink-0"
             style={{ borderBottom: `1px solid ${T.border}` }}>
          <div>
            <h2 className="text-xl font-bold text-slate-100 leading-tight">
              {isNovo ? 'Novo Animal' : animal.nome}
            </h2>
            {!isNovo && (
              <div className="flex items-center gap-2 mt-1.5">
                <StatusPill status={animal.status} />
                {animal.raca && (
                  <span className="text-slate-500 text-xs">{animal.raca}</span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            {editMode ? (
              <>
                <Btn size="xs" variant="ghost" onClick={isNovo ? onClose : () => setEditMode(false)} disabled={saving}>
                  Cancelar
                </Btn>
                <Btn size="xs" variant="primary" onClick={salvar} disabled={saving}>
                  <Check size={12} />{saving ? 'Salvando...' : isNovo ? 'Adicionar' : 'Salvar'}
                </Btn>
              </>
            ) : (
              <>
                <button onClick={() => setEditMode(true)}
                  className="p-1.5 rounded text-slate-500 hover:text-slate-300 transition-colors"
                  aria-label="Editar">
                  <Pencil size={15} />
                </button>
                <button onClick={() => onDelete(animal)}
                  className="p-1.5 rounded text-slate-500 hover:text-red-400 transition-colors"
                  aria-label="Remover">
                  <Trash2 size={15} />
                </button>
                <button onClick={onClose}
                  className="p-1.5 rounded text-slate-500 hover:text-slate-300 transition-colors ml-1"
                  aria-label="Fechar">
                  <X size={18} />
                </button>
              </>
            )}
          </div>
        </div>

        <div className="flex-1 p-5 space-y-6">

          {/* Ficha — modo edição */}
          {editMode ? (
            <section>
              <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-4">{isNovo ? 'Ficha do Animal' : 'Editar Ficha'}</p>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Nome *">
                    <Input value={form.nome} onChange={e => f('nome', e.target.value)} autoFocus />
                  </Field>
                  <Field label="Sexo">
                    <Select value={form.sexo} onChange={e => f('sexo', e.target.value)}>
                      {SEXOS.map(s => <option key={s}>{s}</option>)}
                    </Select>
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Raça">
                    <Select value={form.raca} onChange={e => f('raca', e.target.value)}>
                      {RACAS_OPTS.filter(r => r !== 'Todas').map(r => <option key={r}>{r}</option>)}
                    </Select>
                  </Field>
                  <Field label="Status">
                    <Select value={form.status} onChange={e => f('status', e.target.value)}>
                      {STATUS_NEW.map(s => <option key={s}>{s}</option>)}
                    </Select>
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Data de Nascimento">
                    <Input type="date" value={form.nascimento} onChange={e => f('nascimento', e.target.value)} />
                  </Field>
                  <Field label="Mãe">
                    <Input value={form.mae} onChange={e => f('mae', e.target.value)} placeholder="Nome da mãe" />
                  </Field>
                </div>
                <Field label="Última Inseminação">
                  <Input type="date" value={form.ins} onChange={e => f('ins', e.target.value)} />
                </Field>
                <Field label="Observações">
                  <Textarea value={form.obs} onChange={e => f('obs', e.target.value)} rows={3}
                    placeholder="Histórico, particularidades..." />
                </Field>
              </div>
            </section>
          ) : (
            /* Ficha — modo visualização */
            <section>
              <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-3">Ficha</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Sexo',          value: animal.sexo || '—',                                                        Icon: null },
                  { label: 'Data de Nasc.', value: animal.nascimento ? fmtDate(animal.nascimento) : '—',                      Icon: CalendarDays },
                  { label: 'Idade',         value: idade != null ? `${idade} dias` : '—',                                     Icon: Clock },
                  { label: 'Mãe',           value: animal.mae || '—',                                                         Icon: null },
                  { label: 'DIL',           value: animal.dil != null ? `${animal.dil} dias` : '—',                          Icon: TrendingUp },
                  { label: 'Inseminação',   value: (animal.ins || animal.inseminacao) ? fmtDate(animal.ins || animal.inseminacao) : '—', Icon: CalendarDays },
                  { label: 'Parto Est.',    value: parto,                                                                      Icon: CalendarDays },
                  { label: 'Produção Hoje', value: animal.prod > 0 ? `${Number(animal.prod).toFixed(1)} L` : '—',             Icon: Milk },
                ].map(({ label, value, Icon }) => (
                  <div key={label} className="rounded-lg p-3"
                       style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                    <div className="flex items-center gap-1.5 mb-1">
                      {Icon && <Icon size={11} className="text-slate-600" />}
                      <span className="text-[10px] font-medium uppercase tracking-widest text-slate-500">{label}</span>
                    </div>
                    <span className="text-sm text-slate-200 font-medium">{value}</span>
                  </div>
                ))}
              </div>
              {animal.obs && (
                <div className="mt-3 rounded-lg p-3 text-xs text-slate-400"
                     style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                  <span className="text-slate-500 uppercase tracking-wider text-[10px] font-medium">Obs: </span>
                  {animal.obs}
                </div>
              )}
            </section>
          )}

          {/* Curva de Lactação */}
          {!editMode && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">Curva de Lactação</p>
                {!loadProd && lacInfo && (
                  <div className="flex items-center gap-3 text-[11px]">
                    {lacInfo.dim_atual != null && (
                      <span className="text-slate-600">DIM <span className="text-slate-300 tabular-nums">{lacInfo.dim_atual}d</span></span>
                    )}
                    {lacInfo.media_7d != null && (
                      <span className="text-slate-600">Média 7d <span className="text-emerald-400 tabular-nums">{lacInfo.media_7d.toFixed(1)} L</span></span>
                    )}
                  </div>
                )}
              </div>

              {/* Alerta de queda acelerada */}
              {!loadProd && lacInfo?.queda_pct != null && lacInfo.queda_pct >= 35 && (
                <div className="mb-3 px-3 py-2 rounded-lg text-[11px] flex items-center gap-2"
                     style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
                  <AlertTriangle size={12} className="shrink-0" />
                  <span>Queda acelerada: {lacInfo.queda_pct.toFixed(0)}% abaixo da curva esperada — candidata a secar</span>
                </div>
              )}

              {loadProd ? (
                <div className="h-[130px] flex items-center justify-center">
                  <span className="text-slate-600 text-xs animate-pulse">carregando...</span>
                </div>
              ) : prod.length === 0 ? (
                <div className="h-[130px] flex items-center justify-center rounded-lg"
                     style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                  <span className="text-slate-600 text-xs">sem registros de produção</span>
                </div>
              ) : (
                <div className="rounded-lg overflow-hidden"
                     style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                  <ResponsiveContainer width="100%" height={140}>
                    <ComposedChart data={prod} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                      <defs>
                        <linearGradient id="gAnimal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%"   stopColor="#16a34a" stopOpacity={0.25} />
                          <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 5" stroke="#1a2640" />
                      <XAxis dataKey="dia" tick={tickStyle} interval="preserveStartEnd" />
                      <YAxis tick={tickStyle} unit="L" />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (!active || !payload?.length) return null
                          const real = payload.find(p => p.dataKey === 'litros')
                          const esp  = payload.find(p => p.dataKey === 'esperado')
                          const dim  = payload[0]?.payload?.dim
                          return (
                            <div style={{ background: '#0b1510', border: `1px solid ${T.border}` }}
                                 className="rounded px-2.5 py-1.5 text-[11px] font-mono space-y-0.5">
                              <div className="text-slate-500">{label}{dim != null ? ` · DIM ${dim}` : ''}</div>
                              {real?.value != null && (
                                <div className="text-emerald-400">Real: <span className="tabular-nums">{real.value.toFixed(1)} L</span></div>
                              )}
                              {esp?.value != null && (
                                <div className="text-amber-400">Esperado: <span className="tabular-nums">{esp.value.toFixed(1)} L</span></div>
                              )}
                            </div>
                          )
                        }}
                      />
                      <Area type="monotone" dataKey="litros" name="Real"
                            stroke="#16a34a" strokeWidth={1.5} fill="url(#gAnimal)"
                            dot={false} connectNulls={false} />
                      {prod.some(p => p.esperado != null) && (
                        <Line type="monotone" dataKey="esperado" name="Esperado (Wood)"
                              stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="5 3"
                              dot={false} connectNulls />
                      )}
                    </ComposedChart>
                  </ResponsiveContainer>
                  <div className="flex items-center gap-4 px-4 pb-2.5 pt-1">
                    <div className="flex items-center gap-1.5">
                      <span className="w-4 h-px inline-block" style={{ background: '#16a34a', display: 'inline-block', verticalAlign: 'middle' }} />
                      <span className="text-[10px] text-slate-500">Real</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <svg width="16" height="2" className="inline-block" style={{ verticalAlign: 'middle' }}>
                        <line x1="0" y1="1" x2="5" y2="1" stroke="#f59e0b" strokeWidth="1.5" />
                        <line x1="8" y1="1" x2="13" y2="1" stroke="#f59e0b" strokeWidth="1.5" />
                      </svg>
                      <span className="text-[10px] text-slate-500">Esperado (Wood)</span>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Sanitário */}
          {!editMode && (
            <section>
              <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-3">Histórico Sanitário</p>
              {sanAnimal.length === 0 ? (
                <div className="rounded-lg p-4 text-center"
                     style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                  <span className="text-slate-600 text-xs">nenhum protocolo registrado</span>
                </div>
              ) : (
                <div className="space-y-2">
                  {sanAnimal.map((s, i) => (
                    <div key={i} className="flex items-start gap-3 rounded-lg p-3"
                         style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                      <ShieldCheck size={14} className={s.executado ? 'text-emerald-500 mt-0.5' : 'text-slate-600 mt-0.5'} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium text-slate-200 truncate">{s.protocolo || s.tipo}</span>
                          <span className="text-[10px] text-slate-500 font-mono tabular-nums shrink-0">{fmtDate(s.data)}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-slate-500">{s.tipo}</span>
                          {s.executado
                            ? <span className="text-[10px] text-emerald-500">executado</span>
                            : <span className="text-[10px] text-amber-500">pendente</span>
                          }
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

        </div>
      </div>
    </div>
  )
}

// ─── TAB PRINCIPAL ────────────────────────────────────────────────────────────
export default function TabRebanho() {
  const [animais, setAnimais]       = useState([])
  const [sanitario, setSanitario]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [erro, setErro]             = useState('')
  const [toast, setToast]           = useState(null)
  const [busca, setBusca]           = useState('')
  const [filtroStatus, setStatus]   = useState('Todos')
  const [filtroRaca, setRaca]       = useState('Todas')
  const [selecionado, setSel]       = useState(null)
  const [confirmDel, setConfirmDel] = useState(null)

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const [a, s] = await Promise.all([api.animais(), api.sanitario(180)])
      setAnimais(a)
      setSanitario(s)
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  useEffect(() => {
    const onRefresh = () => carregar()
    window.addEventListener('milkshow:refresh', onRefresh)
    return () => window.removeEventListener('milkshow:refresh', onRefresh)
  }, [])

  async function remover(animal) {
    try {
      await api.removerAnimal(animal.id)
      setToast({ msg: `${animal.nome} removido`, tipo: 'ok' })
      setSel(null)
      carregar()
    } catch (e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setConfirmDel(null) }
  }

  function handleSaved(isNovo = false) {
    setToast({ msg: isNovo ? 'Animal adicionado ao rebanho' : 'Animal atualizado', tipo: 'ok' })
    carregar()
  }

  const filtrados = useMemo(() => {
    return animais.filter(a => {
      const nome = (a.nome || '').toLowerCase()
      const ok1 = !busca || nome.includes(busca.toLowerCase())
      const ok2 = filtroStatus === 'Todos' || a.status === filtroStatus
      const ok3 = filtroRaca   === 'Todas' || a.raca === filtroRaca
      return ok1 && ok2 && ok3
    })
  }, [animais, busca, filtroStatus, filtroRaca])

  const contagem = useMemo(() => {
    const c = {}
    animais.forEach(a => { c[a.status] = (c[a.status] || 0) + 1 })
    return c
  }, [animais])

  if (loading) return <Loading />

  const racasPresentes = ['Todas', ...new Set(animais.map(a => a.raca).filter(Boolean))]

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* Barra de busca + atualizar */}
      <div className="flex items-center gap-2 px-4 py-3 shrink-0 bg-white"
           style={{ borderBottom: '1px solid #e8ede8' }}>
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#8aaa85' }} />
          <input
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar por nome..."
            className="w-full text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200"
            style={{
              paddingLeft: 36, paddingRight: busca ? 32 : 12, paddingTop: 9, paddingBottom: 9,
              border: '1px solid #d4e6d4', background: '#f8faf8', color: '#1a2e1a',
            }}
          />
          {busca && (
            <button onClick={() => setBusca('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 transition-colors"
              style={{ color: '#8aaa85' }}>
              <X size={13} />
            </button>
          )}
        </div>
        <select value={filtroRaca} onChange={e => setRaca(e.target.value)}
          className="text-xs rounded-lg px-3 py-2.5 text-slate-600 focus:outline-none shrink-0"
          style={{ background: '#fff', border: '1px solid #d4e6d4' }}>
          {racasPresentes.map(r => <option key={r}>{r}</option>)}
        </select>
        <button onClick={carregar} aria-label="Atualizar"
          className="p-2.5 rounded-lg transition-colors shrink-0 hover:bg-slate-50"
          style={{ border: '1px solid #d4e6d4', color: '#8aaa85' }}>
          <RefreshCw size={13} />
        </button>
        <Btn variant="primary" size="sm" onClick={() => setSel(ANIMAL_VAZIO)}>
          <Plus size={13} />
          <span className="hidden sm:inline">Novo Animal</span>
        </Btn>
      </div>

      {/* Filtros de status — pills */}
      <div className="flex items-center gap-2 px-4 py-2.5 shrink-0 overflow-x-auto bg-white"
           style={{ borderBottom: '1px solid #e8ede8' }}>
        {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}

        <button onClick={() => setStatus('Todos')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all shrink-0"
          style={{
            background: filtroStatus === 'Todos' ? '#22c55e' : '#f0f4f0',
            color: filtroStatus === 'Todos' ? '#fff' : '#4a6741',
          }}>
          Todos
          <span className="tabular-nums">{animais.length}</span>
        </button>

        {['Lactação', 'Seca', 'Gestação', 'Novilha', 'Bezerro'].map(s => {
          const c   = STATUS_COLOR[s]
          const n   = contagem[s] || 0
          const ativo = filtroStatus === s
          return (
            <button key={s} onClick={() => setStatus(ativo ? 'Todos' : s)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all shrink-0"
              style={{
                background: ativo ? c.bg : '#f0f4f0',
                border: `1px solid ${ativo ? c.border : 'transparent'}`,
                color: ativo ? c.dot : '#4a6741',
              }}>
              <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: c.dot }} />
              {s}
              <span className="tabular-nums" style={{ color: ativo ? c.dot : '#8aaa85' }}>{n}</span>
            </button>
          )
        })}

        {(busca || filtroStatus !== 'Todos' || filtroRaca !== 'Todas') && (
          <button onClick={() => { setBusca(''); setStatus('Todos'); setRaca('Todas') }}
            className="text-xs text-slate-500 hover:text-slate-300 whitespace-nowrap ml-auto shrink-0 transition-colors">
            limpar filtros
          </button>
        )}
      </div>

      {/* Contagem */}
      <div className="px-5 py-2 shrink-0" style={{ borderBottom: `1px solid ${T.border}`, background: T.s3 }}>
        <span className="text-[11px] font-medium" style={{ color: '#64748b' }}>
          {filtrados.length === animais.length
            ? `${animais.length} animais`
            : `${filtrados.length} de ${animais.length} animais`}
        </span>
      </div>

      {/* Lista de animais */}
      <div className="overflow-auto flex-1">
        {filtrados.length === 0 ? (
          animais.length === 0 ? (
            <Empty
              icon={IconRebanho}
              title="Rebanho vazio"
              msg="Cadastre o primeiro animal para começar a gestão do rebanho."
              accentColor="#16a34a"
              action={<Btn variant="primary" size="sm" onClick={() => setSel(ANIMAL_VAZIO)}><Plus size={12} /> Novo Animal</Btn>}
            />
          ) : (
            <Empty
              icon={Search}
              title="Nenhum animal encontrado"
              msg="Tente ajustar os filtros ou a busca."
              action={<Btn variant="ghost" size="sm" onClick={() => { setBusca(''); setStatus('Todos'); setRaca('Todas') }}>Limpar filtros</Btn>}
            />
          )
        ) : (
          <table className="w-full text-xs min-w-[500px]">
            <thead>
              <tr style={{ background: T.s3, borderBottom: `1px solid ${T.border}` }}>
                {['Nome', 'Raça', 'Status', 'Nasc.', 'DIL', 'Prod. Hoje', 'Parto Est.', ''].map(h =>
                  <th key={h}
                    className="text-left text-slate-500 px-4 py-3 font-medium tracking-wider text-[11px] uppercase whitespace-nowrap first:pl-5">
                    {h}
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {filtrados.map(a => (
                <tr key={a.id || a.nome}
                  className="cursor-pointer transition-colors hover:bg-white/[0.025] group"
                  style={{ borderBottom: `1px solid ${T.border2}` }}
                  onClick={() => setSel(a)}>
                  <td className="px-5 py-3 font-semibold text-slate-200">{a.nome}</td>
                  <td className="px-4 py-3 text-slate-500">{a.raca || '—'}</td>
                  <td className="px-4 py-3">
                    <StatusPill status={a.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500 tabular-nums">
                    {a.nascimento ? fmtDate(a.nascimento) : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 tabular-nums">
                    {a.dil != null ? `${a.dil}d` : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-200 tabular-nums">
                    {a.prod > 0 ? `${Number(a.prod).toFixed(1)} L` : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 tabular-nums">
                    {dataParto(a.ins || a.inseminacao)}
                  </td>
                  <td className="px-4 py-3 text-right pr-5">
                    <ChevronRight size={14}
                      className="text-slate-700 group-hover:text-slate-400 transition-colors inline-block" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Painel lateral de perfil */}
      {selecionado && (
        <AnimalPanel
          animal={selecionado}
          onClose={() => setSel(null)}
          onSaved={handleSaved}
          onDelete={a => { setSel(null); setConfirmDel(a) }}
          sanitario={sanitario}
        />
      )}

      {/* Confirmação de remoção */}
      <Modal open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Remover animal">
        <p className="text-slate-400 text-sm">
          Tem certeza que deseja remover <strong className="text-slate-200">{confirmDel?.nome}</strong>?
          Esta ação não pode ser desfeita.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Btn variant="ghost" onClick={() => setConfirmDel(null)}>Cancelar</Btn>
          <Btn variant="danger" onClick={() => remover(confirmDel)}>
            <Trash2 size={12} /> Remover
          </Btn>
        </div>
      </Modal>
    </div>
  )
}
