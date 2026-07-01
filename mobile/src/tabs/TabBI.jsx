/**
 * TabBI — Dashboard MilkShow
 * Layout inspirado no Leigado: 4 KPI tiles + gauges + donuts + task lists
 * Verde (#22c55e) no lugar do azul (#1877f2)
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import {
  AlertTriangle, CheckCircle, FileDown, Droplets, DollarSign,
  TrendingUp, TrendingDown, Minus, Activity, Stethoscope,
  Clock, AlertCircle, Milk, Users, Wallet,
} from 'lucide-react'
import { api } from '../api.js'
import { Loading, Skeleton, fmtBRL, T } from '../ui.jsx'

// ─── CORES — aliases locais dos tokens do design system ──────────────────────
const C = {
  brand:  T.brand,
  brand2: T.brand2,
  bg:     T.bg,
  white:  T.surface,
  border: T.border,
  text:   T.text,
  sub:    T.sub,
  muted:  T.muted,
}

// ─── KPI TILE — estilo Leigado (tooltip integrado) ───────────────────────────
function KpiTile({ label, value, unit, sub, gradient, Icon, delta, tooltip }) {
  const [showTip, setShowTip] = useState(false)
  const isPos = delta > 0
  const isNeg = delta < 0
  const DIcon = delta == null ? null : isPos ? TrendingUp : isNeg ? TrendingDown : Minus

  return (
    <div className="relative overflow-hidden flex flex-col flex-1 transition-transform duration-150 hover:brightness-105 active:scale-[0.98]"
         role="region"
         aria-label={`${label}: ${value}${unit ? ' ' + unit : ''}`}
         style={{ background: gradient, minHeight: 180, padding: '22px 22px 20px', cursor: 'default' }}
         onMouseEnter={() => setShowTip(true)}
         onMouseLeave={() => setShowTip(false)}>

      {/* Label + delta */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/75 leading-tight">
          {label}
        </span>
        {DIcon && (
          <div className="flex items-center gap-0.5 text-[10px] font-bold text-white/80 shrink-0">
            <DIcon size={11} />
            <span>{Math.abs(delta).toFixed(1)}%</span>
          </div>
        )}
      </div>

      {/* Valor grande */}
      <div className="mt-auto pt-4">
        <div className="font-black text-white tabular-nums leading-none"
             style={{ fontSize: 'clamp(2.2rem, 3.2vw, 3.5rem)', textShadow: '0 2px 12px rgba(0,0,0,0.3)', letterSpacing: '-0.02em' }}>
          {value}
          {unit && <span className="font-semibold ml-1 text-white/65" style={{ fontSize: '1.1rem', letterSpacing: 0 }}>{unit}</span>}
        </div>
        {sub && <p className="text-[11px] mt-2 text-white/60 leading-tight">{sub}</p>}
      </div>

      {/* Ícone decorativo */}
      {Icon && (
        <Icon size={80} aria-hidden="true" className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: 'rgba(255,255,255,0.12)', strokeWidth: 1.1 }} />
      )}

      {/* Tooltip abaixo da tile */}
      {showTip && tooltip && (
        <div className="absolute left-1/2 -translate-x-1/2 z-50 pointer-events-none"
             style={{ top: 'calc(100% + 6px)', width: 240 }}>
          <div className="w-3 h-3 mx-auto -mb-1.5 rotate-45"
               style={{ background: 'rgba(20,20,20,0.95)' }} />
          <div className="rounded-xl px-4 py-3 text-[12px] text-white text-center leading-relaxed shadow-2xl"
               style={{ background: 'rgba(20,20,20,0.95)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.08)' }}>
            {tooltip}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── GAUGE SEMICÍRCULO ────────────────────────────────────────────────────────
function Gauge({ value = 0, max = 100, label, color = '#22c55e', tooltip }) {
  const pct     = Math.min(100, Math.max(0, (value / max) * 100))
  const R       = 54
  const cx      = 70
  const cy      = 70
  const sweep   = Math.PI          // semicírculo (180°)
  const start   = Math.PI          // começa à esquerda
  const angle   = start + (pct / 100) * sweep
  const x1      = cx + R * Math.cos(start)
  const y1      = cy + R * Math.sin(start)
  const x2      = cx + R * Math.cos(angle)
  const y2      = cy + R * Math.sin(angle)
  const large   = pct > 50 ? 1 : 0
  const trackPath = `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`
  const fillPath  = pct >= 100
    ? trackPath
    : `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`

  return (
    <div className="flex flex-col items-center gap-1 relative group">
      <span className="text-[11px] font-semibold text-center cursor-default" style={{ color: T.sub }}>{label}</span>
      {/* Tooltip do gauge */}
      {tooltip && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 z-50 hidden group-hover:block pointer-events-none"
             style={{ width: 200 }}>
          <div className="w-3 h-3 mx-auto -mb-1.5 rotate-45"
               style={{ background: 'rgba(15,20,15,0.92)' }} />
          <div className="rounded-xl px-4 py-3 text-[11px] text-white text-center leading-relaxed shadow-2xl"
               style={{ background: 'rgba(15,20,15,0.92)', backdropFilter: 'blur(8px)' }}>
            {tooltip}
          </div>
        </div>
      )}
      <svg width="140" height="80" viewBox="0 0 140 80">
        {/* Track */}
        <path d={trackPath} fill="none" stroke="#e8ede8" strokeWidth={10} strokeLinecap="round" />
        {/* Fill */}
        {pct > 0 && (
          <path d={fillPath} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round" />
        )}
        {/* Texto central */}
        <text x={cx} y={cy + 6} textAnchor="middle"
              style={{ fontSize: 18, fontWeight: 900, fill: T.text, fontFamily: 'Inter,sans-serif' }}>
          {value.toFixed(1)}%
        </text>
        <text x={cx - R - 2} y={cy + 20}
              style={{ fontSize: 9, fill: T.muted, fontFamily: 'Inter,sans-serif' }}>0</text>
        <text x={cx + R - 10} y={cy + 20}
              style={{ fontSize: 9, fill: T.muted, fontFamily: 'Inter,sans-serif' }}>{max}</text>
      </svg>
    </div>
  )
}

// ─── DONUT CHART ──────────────────────────────────────────────────────────────
const RADIAN = Math.PI / 180
function DonutLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent < 0.07) return null
  const r = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + r * Math.cos(-midAngle * RADIAN)
  const y = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central"
          style={{ fontSize: 10, fontWeight: 700 }}>
      {(percent * 100).toFixed(1)}%
    </text>
  )
}

function Donut({ title, data, colors }) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0)
  if (total === 0) return (
    <div className="flex flex-col items-center gap-2 p-4">
      <span className="text-[12px] font-semibold text-slate-500">{title}</span>
      <div className="w-24 h-24 rounded-full border-8 border-slate-100 flex items-center justify-center">
        <span className="text-[11px] text-slate-400">sem dados</span>
      </div>
    </div>
  )

  return (
    <div className="flex flex-col items-center gap-2">
      <span className="text-[12px] font-semibold text-slate-600">{title}</span>
      <PieChart width={160} height={130}>
        <Pie
          data={data}
          cx={78} cy={65}
          innerRadius={38} outerRadius={58}
          paddingAngle={2}
          dataKey="value"
          labelLine={false}
          label={DonutLabel}
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={colors[i % colors.length]} />
          ))}
        </Pie>
      </PieChart>
      {/* Legenda */}
      <div className="flex flex-wrap justify-center gap-x-3 gap-y-1">
        {data.filter(d => d.value > 0).map((d, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: colors[i % colors.length] }} />
            <span className="text-[10px] text-slate-500">{d.name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── GRÁFICO DE LINHA (média de produção) ────────────────────────────────────
function ProdLineChart({ data, totalHoje, delta }) {
  const isPos = delta >= 0
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-end justify-between mb-2">
        <div>
          <p className="text-[11px] text-slate-400 font-medium">Produção — últimos dias</p>
          <p className="text-[28px] font-black tabular-nums leading-none mt-0.5" style={{ color: C.text }}>
            {Number(totalHoje || 0).toFixed(1)}
            <span className="text-[14px] font-semibold ml-1 text-slate-400">Litros</span>
          </p>
        </div>
        {delta != null && (
          <div className={`flex items-center gap-1 text-[13px] font-bold ${isPos ? 'text-green-500' : 'text-red-500'}`}>
            {isPos ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {isPos ? '+' : ''}{delta.toFixed(1)}%
          </div>
        )}
      </div>
      <div className="flex-1" style={{ minHeight: 80 }}>
        <ResponsiveContainer width="100%" height={90}>
          <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -32 }}>
            <defs>
              <linearGradient id="biLineGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={C.brand} stopOpacity={0.25} />
                <stop offset="100%" stopColor={C.brand} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 5" stroke="#e8ede8" />
            <XAxis dataKey="dia" tick={{ fill: '#8aaa85', fontSize: 9 }} />
            <YAxis tick={{ fill: '#8aaa85', fontSize: 9 }} />
            <Tooltip
              contentStyle={{ background: '#fff', border: '1px solid #e8ede8', borderRadius: 8, fontSize: 11 }}
              itemStyle={{ color: C.text }}
            />
            <Area type="monotone" dataKey="litros" stroke={C.brand} strokeWidth={2}
                  fill="url(#biLineGrad)" dot={false} activeDot={{ r: 4, fill: C.brand }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ─── CARD TAREFA ─────────────────────────────────────────────────────────────
function TarefaItem({ icon: Icon, iconBg, iconColor, title, sub, date, badge, badgeColor }) {
  const diasAte = date ? Math.round((new Date(date + 'T00:00:00') - new Date()) / 86400000) : null
  const atrasada = diasAte !== null && diasAte < 0

  return (
    <div role="listitem" className="flex items-start gap-3 py-3 border-b last:border-0" style={{ borderColor: T.s2 }}>
      <div className="w-11 h-11 rounded-full flex items-center justify-center shrink-0"
           style={{ background: iconBg }}>
        <Icon size={17} style={{ color: iconColor }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-semibold text-slate-700 truncate">{title}</p>
        <p className="text-[11px] text-slate-400 truncate">{sub}</p>
      </div>
      <div className="flex flex-col items-end gap-1 shrink-0">
        {date && (
          <span className="text-[10px] text-slate-400 flex items-center gap-1">
            <Clock size={9} />
            {new Date(date + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })}
          </span>
        )}
        {(badge || atrasada) && (
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full"
                style={{
                  background: atrasada ? '#fef2f2' : `${badgeColor}15`,
                  color: atrasada ? '#dc2626' : badgeColor,
                  border: `1px solid ${atrasada ? '#fca5a5' : `${badgeColor}30`}`,
                }}>
            {atrasada ? 'Atrasada' : badge}
          </span>
        )}
      </div>
    </div>
  )
}

// ─── BANNER ALERTAS ───────────────────────────────────────────────────────────
function AlertaBanner({ animais, sanitario, estoque, pendentes }) {
  const alertas = useMemo(() => {
    const list = []
    const hoje = new Date()
    if (pendentes > 0)
      list.push({ tipo: 'warn', msg: `${pendentes} vaca${pendentes > 1 ? 's' : ''} não ordenhada${pendentes > 1 ? 's' : ''} hoje` })
    animais.forEach(a => {
      const ins = a.ins || a.inseminacao
      if (!ins) return
      const parto = new Date(ins); parto.setDate(parto.getDate() + 283)
      const d = Math.round((parto - hoje) / 86400000)
      if (d >= 0 && d <= 7) list.push({ tipo: 'info', msg: `Parto de ${a.nome} em ${d === 0 ? 'hoje' : `${d}d`}` })
    })
    sanitario.filter(s => !s.executado).forEach(s => {
      const d = Math.round((new Date(s.data + 'T00:00:00') - hoje) / 86400000)
      if (d < 0) list.push({ tipo: 'erro', msg: `${s.protocolo || s.tipo} — ${s.animal} venceu` })
      else if (d <= 3) list.push({ tipo: 'warn', msg: `${s.protocolo || s.tipo} — ${s.animal} vence em ${d}d` })
    })
    estoque.forEach(item => {
      if (Number(item.qtd) <= 0) list.push({ tipo: 'erro', msg: `${item.item} — estoque zerado` })
    })
    return list
  }, [animais, sanitario, estoque, pendentes])

  if (alertas.length === 0) return (
    <div className="flex items-center gap-2 flex-1" role="status" aria-label="Sem alertas hoje">
      <CheckCircle size={13} aria-hidden="true" style={{ color: T.brand }} className="shrink-0" />
      <span className="text-[12px] font-medium" style={{ color: T.brand2 }}>Tudo em ordem — sem alertas hoje</span>
    </div>
  )

  const cores = { erro: '#dc2626', warn: '#d97706', info: '#2563eb' }

  return (
    <div className="flex items-center gap-3 px-5 py-2 bg-amber-50 shrink-0 overflow-x-auto"
         role="status" aria-live="polite" aria-label={`${alertas.length} alerta${alertas.length > 1 ? 's' : ''} ativo${alertas.length > 1 ? 's' : ''}`}
         style={{ borderBottom: '1px solid #fde68a' }}>
      <div className="flex items-center gap-1.5 shrink-0">
        <AlertTriangle size={13} aria-hidden="true" className="text-amber-500" />
        <span className="text-[11px] font-bold text-amber-600">{alertas.length} alerta{alertas.length > 1 ? 's' : ''}</span>
      </div>
      <div className="flex gap-2 overflow-x-auto">
        {alertas.slice(0, 5).map((a, i) => (
          <span key={i} className="shrink-0 text-[11px] px-2.5 py-0.5 rounded-full font-medium"
                style={{ background: `${cores[a.tipo]}12`, color: cores[a.tipo], border: `1px solid ${cores[a.tipo]}25` }}>
            {a.msg}
          </span>
        ))}
      </div>
    </div>
  )
}

// ─── SECTION CARD ─────────────────────────────────────────────────────────────
function Card({ title, children, action, className = '' }) {
  return (
    <div className={`bg-white rounded-xl overflow-hidden ${className}`}
         style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
      {(title || action) && (
        <div className="flex items-center justify-between px-4 py-3"
             style={{ borderBottom: '1px solid #f0f4f0' }}>
          <span className="text-[13px] font-bold text-slate-700">{title}</span>
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}

// ─── TAB ──────────────────────────────────────────────────────────────────────
export default function TabBI() {
  const [dash,      setDash]      = useState(null)
  const [animais,   setAnimais]   = useState([])
  const [sanitario, setSanitario] = useState([])
  const [estoque,   setEstoque]   = useState([])
  const [prodRaw,   setProdRaw]   = useState([])
  const [prodChart, setProdChart] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [erro,      setErro]      = useState('')
  const [pdfLoad,   setPdfLoad]   = useState(false)
  const [periodo,   setPeriodo]   = useState(14)
  const [refreshing, setRefreshing] = useState(false)

  async function baixarPDF() {
    setPdfLoad(true)
    try {
      const blob = await api.relatorioMensal()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url
      const d = new Date()
      a.download = `MilkShow_${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch(e) { alert('Erro: ' + e.message) }
    finally { setPdfLoad(false) }
  }

  const buildChart = useCallback((raw, dias) => {
    const ini = new Date(Date.now() - dias * 86400000).toISOString().split('T')[0]
    const porDia = {}
    raw.filter(r => r.data >= ini).forEach(r => {
      porDia[r.data] = (porDia[r.data] || 0) + (r.leite || 0)
    })
    setProdChart(
      Object.entries(porDia)
        .sort(([a],[b]) => a.localeCompare(b))
        .map(([data, litros]) => ({ dia: data.slice(5), litros: +litros.toFixed(1) }))
    )
  }, [])

  const carregar = useCallback(async (silente = false) => {
    if (!silente) { setLoading(true); setErro('') }
    else setRefreshing(true)
    try {
      const [d, a, p, s, e] = await Promise.all([
        api.dashboard(),
        api.animais(),
        api.producao(90),
        api.sanitario(60),
        api.estoque(),
      ])
      setDash(d)
      setAnimais(a.filter(x => x.status !== 'Vendido'))
      setProdRaw(p)
      setSanitario(s)
      setEstoque(e)
      buildChart(p, periodo)
    } catch(e) { if (!silente) setErro(e.message) }
    finally    { if (!silente) setLoading(false); else setRefreshing(false) }
  }, [buildChart, periodo])

  useEffect(() => { carregar() }, [])
  useEffect(() => { buildChart(prodRaw, periodo) }, [periodo, prodRaw, buildChart])

  // SSE + auto-refresh
  useEffect(() => {
    let es
    try {
      es = api.openEventSource()
      es.onmessage = ev => {
        try { const d = JSON.parse(ev.data); if (d.type === 'update') carregar(true) } catch {}
      }
      es.onerror = () => es?.close()
    } catch {}
    return () => es?.close()
  }, [carregar])
  useEffect(() => {
    const id = setInterval(() => carregar(true), 120000)
    return () => clearInterval(id)
  }, [carregar])

  if (loading) return <Loading />
  if (erro)    return (
    <div className="flex items-center justify-center h-full" role="alert" aria-live="assertive">
      <div className="text-center px-6">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
             style={{ background: '#fef2f2', border: '1px solid #fca5a5' }}>
          <AlertCircle size={24} style={{ color: T.red }} aria-hidden="true" />
        </div>
        <p className="font-semibold mb-1" style={{ color: T.text }}>Falha ao carregar</p>
        <p className="text-sm mb-4" style={{ color: T.muted }}>{erro}</p>
        <button onClick={() => carregar()}
                className="px-5 py-2.5 rounded-lg text-white text-sm font-semibold transition-all duration-150 hover:brightness-90 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2"
                style={{ background: T.brand, minHeight: 44 }}>
          Tentar novamente
        </button>
      </div>
    </div>
  )
  if (!dash) return null

  // ─── Métricas derivadas ───────────────────────────────────────────────────
  const h   = dash.hoje   || {}
  const sem = dash.semana || {}
  const mes = dash.mes    || {}
  const preco       = Number(dash.preco_leite     || 2.50)
  const custo       = Number(dash.custo_por_litro || 1.18)
  const margem      = preco > 0 ? ((preco - custo) / preco * 100) : 0
  const pendentes   = (h.vacas_lact || 0) - (h.vacas_ordenhadas || 0)
  const n = (v, d = 1) => Number(v || 0).toFixed(d)
  const totalHoje   = Number(h.litros || 0)

  // KPI TILES
  const TILES = [
    {
      label: 'Animais Ativos',
      value: String(animais.filter(a => a.status !== 'Vendido').length),
      sub: `Em lactação: ${animais.filter(a => a.status === 'Lactação').length}`,
      gradient: 'linear-gradient(135deg, #16a34a 0%, #22c55e 100%)',
      Icon: Users,
      tooltip: 'Total de animais cadastrados e ativos na fazenda, excluindo animais vendidos ou descartados.',
    },
    {
      label: 'Produção Hoje',
      value: n(totalHoje, 1),
      unit: 'L',
      delta: h.delta_producao,
      sub: `Ontem: ${n(h.litros_ontem)}L${pendentes > 0 ? ` · ${pendentes} pendentes` : ' · completo'}`,
      gradient: 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
      Icon: Droplets,
      tooltip: 'Total de litros de leite coletados em todas as ordenhas do dia de hoje.',
    },
    {
      label: 'Receita Estimada',
      value: fmtBRL(h.receita_est || (totalHoje * preco)),
      sub: `R$ ${n(preco, 2)}/L`,
      gradient: 'linear-gradient(135deg, #d97706 0%, #f59e0b 100%)',
      Icon: DollarSign,
      tooltip: `Receita bruta estimada com base na produção de hoje multiplicada pelo preço configurado de R$ ${n(preco, 2)}/L.`,
    },
    {
      label: 'Saldo do Mês',
      value: fmtBRL(Math.abs(mes.saldo || 0)),
      sub: `Rec ${fmtBRL(mes.receitas || 0)} · Des ${fmtBRL(mes.despesas || 0)}`,
      gradient: (mes.saldo || 0) >= 0
        ? 'linear-gradient(135deg, #059669 0%, #10b981 100%)'
        : 'linear-gradient(135deg, #b91c1c 0%, #ef4444 100%)',
      Icon: Wallet,
      tooltip: 'Resultado financeiro do mês atual: total de receitas menos total de despesas registradas.',
    },
  ]

  // GAUGES (taxa de lactação, meta de produção, margem op)
  const meta = Number(dash.meta_producao || 0)
  const pctMeta   = meta > 0 ? Math.min(100, (totalHoje / meta) * 100) : 0
  const pctLact   = animais.length > 0
    ? (animais.filter(a => a.status === 'Lactação').length / animais.length * 100)
    : 0
  const margemVal = Math.max(0, Math.min(100, margem))

  // DONUTS
  const rebanhoStatus = [
    { name: 'Lactação', value: animais.filter(a => a.status === 'Lactação').length },
    { name: 'Seca',     value: animais.filter(a => a.status === 'Seca').length },
    { name: 'Gestação', value: animais.filter(a => a.status === 'Gestação').length },
    { name: 'Novilha',  value: animais.filter(a => a.status === 'Novilha').length },
  ].filter(d => d.value > 0)

  const donutColors = {
    rebanho:   ['#22c55e', '#d97706', '#2563eb', '#8b5cf6'],
    reprodut:  ['#8b5cf6', '#2563eb', '#22c55e', '#dc2626'],
    produtivo: ['#2563eb', '#d97706', '#22c55e'],
  }

  // TAREFAS — partos e sanitário
  const tarefasGerais = (() => {
    const list = []
    const hoje = new Date()
    animais.forEach(a => {
      const ins = a.ins || a.inseminacao
      if (!ins) return
      const parto = new Date(ins); parto.setDate(parto.getDate() + 283)
      const d = Math.round((parto - hoje) / 86400000)
      if (d >= -7 && d <= 30)
        list.push({ type: 'parto', nome: a.nome, date: parto.toISOString().split('T')[0], dias: d })
    })
    animais.filter(a => a.status === 'Lactação').forEach(a => {
      const ins = a.ins || a.inseminacao
      if (!ins) return
      const seca = new Date(ins); seca.setDate(seca.getDate() + 223)
      const d = Math.round((seca - hoje) / 86400000)
      if (d >= 0 && d <= 14)
        list.push({ type: 'seca', nome: a.nome, date: seca.toISOString().split('T')[0], dias: d })
    })
    return list.sort((a, b) => a.dias - b.dias).slice(0, 6)
  })()

  const tarefasSan = sanitario
    .filter(s => !s.executado)
    .sort((a, b) => a.data.localeCompare(b.data))
    .slice(0, 6)

  return (
    <div style={{ background: C.bg, width: '100%' }}>

      {/* ─── ROW 1: 4 KPI TILES ────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 w-full gap-px"
           style={{ background: 'rgba(255,255,255,0.2)', borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
        {TILES.map((t, i) => (
          <div key={i} className="flex flex-col">
            <KpiTile {...t} />
          </div>
        ))}
      </div>

      {/* Botão PDF + alerta */}
      <div className="flex items-center justify-between px-5 py-2 bg-white mb-0.5"
           style={{ borderBottom: '1px solid #e8ede8' }}>
        <AlertaBanner
          animais={animais} sanitario={sanitario}
          estoque={estoque} pendentes={pendentes}
        />
        <button onClick={baixarPDF} disabled={pdfLoad}
          aria-label="Baixar relatório mensal em PDF"
          aria-busy={pdfLoad}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold shrink-0 ml-3 transition-all duration-150 hover:brightness-95 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2"
          style={{
            background: pdfLoad ? T.s3 : '#f0fdf4',
            color: pdfLoad ? T.muted : T.brand2,
            border: `1px solid ${pdfLoad ? T.border : '#86efac'}`,
          }}>
          <FileDown size={12} aria-hidden="true" />
          {pdfLoad ? 'Gerando...' : 'Relatório PDF'}
        </button>
      </div>

      {/* ─── ROW 2: GAUGES + GRÁFICO LINHA ─────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 px-4 py-4">

        {/* 3 gauges */}
        <div className="md:col-span-3 bg-white rounded-xl p-4"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <p className="text-[12px] font-bold text-slate-500 mb-3 uppercase tracking-wider">Índices Operacionais</p>
          <div className="grid grid-cols-3 gap-2">
            <Gauge
              label="Taxa de Lactação"
              value={pctLact}
              color="#22c55e"
              tooltip="Percentual de vacas em lactação sobre o total do rebanho ativo. Quanto maior, melhor o aproveitamento do rebanho."
            />
            <Gauge
              label="Meta de Produção"
              value={pctMeta}
              color="#0d9488"
              tooltip={meta > 0 ? `Percentual atingido da meta diária de ${meta.toFixed(0)}L. Configurado em Configurações → Produção.` : 'Configure uma meta de produção diária em Configurações para acompanhar o progresso aqui.'}
            />
            <Gauge
              label="Margem Operacional"
              value={margemVal}
              color={margem >= 30 ? '#22c55e' : margem >= 15 ? '#d97706' : '#dc2626'}
              tooltip={`Percentual de lucro por litro vendido: (R$ ${n(preco,2)} - R$ ${n(custo,2)}) / R$ ${n(preco,2)}. Acima de 30% é saudável.`}
            />
          </div>
        </div>

        {/* Linha chart */}
        <div className="bg-white rounded-xl p-4 flex flex-col"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div className="flex items-center gap-1 mb-2" role="group" aria-label="Período do gráfico">
            {[7,14,30].map(d => (
              <button key={d} onClick={() => setPeriodo(d)}
                aria-pressed={periodo === d}
                aria-label={`${d} dias`}
                className="px-2.5 py-1 rounded-md text-[10px] font-bold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 active:scale-[0.95]"
                style={{
                  background: periodo === d ? T.brand : T.s3,
                  color: periodo === d ? '#fff' : T.muted,
                  minHeight: 28,
                }}>
                {d}d
              </button>
            ))}
          </div>
          <ProdLineChart
            data={prodChart}
            totalHoje={totalHoje}
            delta={h.delta_producao}
          />
        </div>
      </div>

      {/* ─── ROW 3: NÚMEROS + DONUTS ────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 px-4 pb-4">

        {/* Litros summary */}
        <div className="flex flex-col gap-3">
          <div className="bg-white rounded-xl p-4 flex-1 transition-opacity duration-300"
               style={{ border: `1px solid ${T.border}`, boxShadow: '0 1px 4px rgba(0,0,0,0.04)', opacity: refreshing ? 0.6 : 1 }}>
            <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: T.muted }}>Litros Hoje</p>
            {refreshing
              ? <Skeleton className="h-8 w-20 mt-1" />
              : <p className="text-[28px] font-black tabular-nums leading-none" style={{ color: T.brand }}>{n(totalHoje, 1)}</p>
            }
            <p className="text-[10px] mt-1" style={{ color: T.muted }}>última ordenha</p>
          </div>
          <div className="bg-white rounded-xl p-4 flex-1 transition-opacity duration-300"
               style={{ border: `1px solid ${T.border}`, boxShadow: '0 1px 4px rgba(0,0,0,0.04)', opacity: refreshing ? 0.6 : 1 }}>
            <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: T.muted }}>Litros no Mês</p>
            {refreshing
              ? <Skeleton className="h-8 w-20 mt-1" />
              : <p className="text-[28px] font-black tabular-nums leading-none" style={{ color: '#0d9488' }}>{n(mes.litros_mes || 0, 0)}</p>
            }
            <p className="text-[10px] mt-1" style={{ color: T.muted }}>acumulado</p>
          </div>
        </div>

        {/* 3 donuts */}
        <div className="bg-white rounded-xl flex items-center justify-center"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '8px 0' }}>
          <Donut
            title="Composição do Rebanho"
            data={rebanhoStatus}
            colors={donutColors.rebanho}
          />
        </div>
        <div className="bg-white rounded-xl flex items-center justify-center"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '8px 0' }}>
          <Donut
            title="Status Reprodutivo"
            data={[
              { name: 'Inseminada', value: animais.filter(a => a.ins && a.status !== 'Seca').length },
              { name: 'Em Aberto',  value: animais.filter(a => !a.ins && a.status === 'Lactação').length },
              { name: 'Gestação',   value: animais.filter(a => a.status === 'Gestação').length },
            ].filter(d => d.value > 0)}
            colors={donutColors.reprodut}
          />
        </div>
        <div className="bg-white rounded-xl flex items-center justify-center"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: '8px 0' }}>
          <Donut
            title="Composição Produtiva"
            data={[
              { name: 'Lactação', value: animais.filter(a => a.status === 'Lactação').length },
              { name: 'Seca',     value: animais.filter(a => a.status === 'Seca').length },
              { name: 'Novilha',  value: animais.filter(a => a.status === 'Novilha').length },
            ].filter(d => d.value > 0)}
            colors={donutColors.produtivo}
          />
        </div>
      </div>

      {/* ─── ROW 4: TASK LISTS ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 px-4 pb-6">

        {/* Tarefas gerais */}
        <div className="bg-white rounded-xl overflow-hidden"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div className="flex items-center justify-between px-4 py-3"
               style={{ borderBottom: '1px solid #f0f4f0' }}>
            <span className="text-[13px] font-bold text-slate-700">Lista de Tarefas</span>
          </div>
          <div className="px-4" role="list" aria-label="Tarefas de parto e secagem">
            {tarefasGerais.length === 0 ? (
              <div className="py-8 flex flex-col items-center gap-2 text-center">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                     style={{ background: T.brandGlow, border: `1px solid ${T.brand}30` }}>
                  <CheckCircle size={20} style={{ color: T.brand }} />
                </div>
                <p className="text-[13px] font-semibold" style={{ color: T.text }}>Tudo em dia</p>
                <p className="text-[12px]" style={{ color: T.muted }}>Nenhum parto ou secagem nos próximos 30 dias</p>
              </div>
            ) : tarefasGerais.map((t, i) => (
              <TarefaItem key={i}
                icon={t.type === 'parto' ? Milk : Activity}
                iconBg={t.type === 'parto' ? '#f0fdf4' : '#fff7ed'}
                iconColor={t.type === 'parto' ? '#16a34a' : '#d97706'}
                title={`${t.type === 'parto' ? 'Parto' : 'Secagem'} — ${t.nome}`}
                sub={`Previsão de ${t.type === 'parto' ? 'parto' : 'secagem'} para ${t.nome}`}
                date={t.date}
                badge={t.dias === 0 ? 'Hoje' : t.dias > 0 ? `Em ${t.dias}d` : undefined}
                badgeColor={t.type === 'parto' ? '#16a34a' : '#d97706'}
              />
            ))}
          </div>
        </div>

        {/* Tarefas sanitárias */}
        <div className="bg-white rounded-xl overflow-hidden"
             style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div className="flex items-center justify-between px-4 py-3"
               style={{ borderBottom: '1px solid #f0f4f0' }}>
            <span className="text-[13px] font-bold text-slate-700">Lista de Tarefas Sanitárias</span>
          </div>
          <div className="px-4" role="list" aria-label="Tarefas sanitárias pendentes">
            {tarefasSan.length === 0 ? (
              <div className="py-8 flex flex-col items-center gap-2 text-center">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                     style={{ background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                  <Stethoscope size={20} style={{ color: T.blue }} />
                </div>
                <p className="text-[13px] font-semibold" style={{ color: T.text }}>Sem pendências sanitárias</p>
                <p className="text-[12px]" style={{ color: T.muted }}>Nenhuma atividade agendada nos próximos dias</p>
              </div>
            ) : tarefasSan.map((s, i) => (
              <TarefaItem key={i}
                icon={Stethoscope}
                iconBg="#eff6ff"
                iconColor="#2563eb"
                title={`${s.protocolo || s.tipo} — ${s.animal}`}
                sub={`Atividade sanitária agendada`}
                date={s.data}
                badge="Sanitário"
                badgeColor="#2563eb"
              />
            ))}
          </div>
        </div>
      </div>

    </div>
  )
}
