import { useEffect, useState, useCallback } from 'react'
import {
  ComposedChart, Area, Line, Bar,
  BarChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { AlertTriangle, CheckCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { api } from '../api.js'
import { Loading, ErrorMsg, Delta, fmtBRL, T, SectionHeader, ChartControls } from '../ui.jsx'

// ─── TOOLTIP ─────────────────────────────────────────────────────────────────
function ChartTip({ active, payload, label, suffix = '' }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}` }}
         className="rounded-lg px-3 py-2.5 text-[11px] shadow-xl">
      <p className="text-slate-500 font-mono mb-1.5">{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ background: p.color }} />
          <span className="text-slate-400 font-mono">{p.name || p.dataKey}:</span>
          <span className="text-slate-100 font-mono font-semibold tabular-nums">{p.value}{suffix}</span>
        </div>
      ))}
    </div>
  )
}

// ─── KPI CARD ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, unit, delta, sub, accent, last }) {
  const DeltaIcon = delta == null ? null : delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus
  const deltaColor = delta == null ? '' : delta > 0 ? 'text-emerald-400' : delta < 0 ? 'text-red-400' : 'text-slate-500'
  return (
    <div className="flex flex-col justify-between p-4 min-w-0"
         style={{ borderRight: last ? 'none' : `1px solid ${T.border}` }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 leading-tight">{label}</span>
        {DeltaIcon && delta != null && (
          <div className={`flex items-center gap-0.5 text-[11px] font-mono ${deltaColor}`}>
            <DeltaIcon size={11} />
            <span>{Math.abs(delta).toFixed(1)}%</span>
          </div>
        )}
      </div>
      <div>
        <div className={`text-2xl font-mono font-semibold leading-none tabular-nums ${accent ? 'text-blue-400' : 'text-slate-100'}`}>
          {value}
          {unit && <span className="text-slate-600 text-sm font-normal ml-1">{unit}</span>}
        </div>
        {sub && <div className="text-[11px] font-mono text-slate-600 mt-1.5 leading-snug">{sub}</div>}
      </div>
    </div>
  )
}

// ─── BANNER DE ALERTAS ────────────────────────────────────────────────────────
function AlertasBanner({ animais, sanitario, estoque, pendentes }) {
  const hoje = new Date()

  const alertas = []

  // Vacas não ordenhadas hoje
  if (pendentes > 0)
    alertas.push({ tipo: 'warn', msg: `${pendentes} vaca${pendentes > 1 ? 's' : ''} ainda não ordenhada${pendentes > 1 ? 's' : ''} hoje` })

  // Partos nos próximos 7 dias
  animais.forEach(a => {
    const ins = a.ins || a.inseminacao
    if (!ins) return
    const parto = new Date(ins)
    parto.setDate(parto.getDate() + 283)
    const diasAte = Math.round((parto - hoje) / 86400000)
    if (diasAte >= 0 && diasAte <= 7)
      alertas.push({ tipo: 'info', msg: `Parto de ${a.nome} em ${diasAte === 0 ? 'hoje' : `${diasAte} dia${diasAte > 1 ? 's' : ''}`}` })
  })

  // Secagens nos próximos 7 dias (ins + 223d)
  animais.filter(a => a.status === 'Lactação').forEach(a => {
    const ins = a.ins || a.inseminacao
    if (!ins) return
    const seca = new Date(ins)
    seca.setDate(seca.getDate() + 223)
    const diasAte = Math.round((seca - hoje) / 86400000)
    if (diasAte >= 0 && diasAte <= 7)
      alertas.push({ tipo: 'warn', msg: `Secagem de ${a.nome} em ${diasAte === 0 ? 'hoje' : `${diasAte} dia${diasAte > 1 ? 's' : ''}`}` })
  })

  // Vacinas vencidas / a vencer
  sanitario.filter(s => !s.executado).forEach(s => {
    const data = new Date(s.data + 'T00:00:00')
    const diasAte = Math.round((data - hoje) / 86400000)
    if (diasAte < 0)
      alertas.push({ tipo: 'erro', msg: `${s.protocolo || s.tipo} — ${s.animal} venceu há ${Math.abs(diasAte)}d` })
    else if (diasAte <= 3)
      alertas.push({ tipo: 'warn', msg: `${s.protocolo || s.tipo} — ${s.animal} vence em ${diasAte === 0 ? 'hoje' : `${diasAte}d`}` })
  })

  // Estoque zerado / crítico
  estoque.forEach(item => {
    if (Number(item.qtd) <= 0)
      alertas.push({ tipo: 'erro', msg: `${item.item} — estoque zerado` })
    else if (item.min_alerta && Number(item.qtd) <= Number(item.min_alerta))
      alertas.push({ tipo: 'warn', msg: `${item.item} — estoque baixo (${item.qtd} ${item.un})` })
  })

  if (alertas.length === 0) return (
    <div className="flex items-center gap-2 px-5 py-2.5 shrink-0"
         style={{ background: 'rgba(22,163,74,0.06)', borderBottom: `1px solid ${T.border}` }}>
      <CheckCircle size={12} className="text-emerald-500 shrink-0" />
      <span className="text-emerald-600 text-[11px] font-mono">Tudo em ordem — sem alertas hoje</span>
    </div>
  )

  const cores = { erro: '#ef4444', warn: '#f59e0b', info: '#3b82f6' }

  return (
    <div className="shrink-0 px-5 py-2 flex items-center gap-3 overflow-x-auto"
         style={{ background: 'rgba(245,158,11,0.05)', borderBottom: `1px solid ${T.border}` }}>
      <div className="flex items-center gap-1.5 shrink-0">
        <AlertTriangle size={12} className="text-amber-500" />
        <span className="text-amber-500 text-[11px] font-mono font-semibold shrink-0">{alertas.length} alerta{alertas.length > 1 ? 's' : ''}</span>
      </div>
      <div className="flex items-center gap-2 overflow-x-auto">
        {alertas.slice(0, 6).map((a, i) => (
          <span key={i}
            className="shrink-0 text-[11px] font-mono px-2.5 py-1 rounded-full whitespace-nowrap"
            style={{ background: `${cores[a.tipo]}18`, color: cores[a.tipo], border: `1px solid ${cores[a.tipo]}30` }}>
            {a.msg}
          </span>
        ))}
        {alertas.length > 6 && (
          <span className="shrink-0 text-slate-600 text-[11px] font-mono">+{alertas.length - 6} mais</span>
        )}
      </div>
    </div>
  )
}

// ─── GRÁFICO DINÂMICO ─────────────────────────────────────────────────────────
function ProdChart({ data, tipo }) {
  const tick  = { fill: '#475569', fontSize: 11, fontFamily: 'monospace' }
  const grid  = <CartesianGrid strokeDasharray="3 5" stroke="#1a2640" />
  const x     = <XAxis dataKey="dia" tick={tick} />
  const y     = <YAxis tick={tick} />
  const tip   = <Tooltip content={<ChartTip suffix="L" />} />
  const color = '#3b82f6'

  if (tipo === 'barra') return (
    <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
      {grid}{x}{y}{tip}
      <Bar dataKey="litros" fill={color} radius={[3, 3, 0, 0]} maxBarSize={24} />
    </ComposedChart>
  )
  if (tipo === 'linha') return (
    <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
      {grid}{x}{y}{tip}
      <Line type="monotone" dataKey="litros" stroke={color} strokeWidth={2} dot={false} />
    </ComposedChart>
  )
  return (
    <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
      <defs>
        <linearGradient id="gBIProd" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity={0.18} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      {grid}{x}{y}{tip}
      <Area type="monotone" dataKey="litros" stroke={color} strokeWidth={1.5}
            fill="url(#gBIProd)" dot={false} />
    </ComposedChart>
  )
}

// ─── TAB ─────────────────────────────────────────────────────────────────────
export default function TabBI() {
  const [dash, setDash]           = useState(null)
  const [animais, setAnimais]     = useState([])
  const [sanitario, setSanitario] = useState([])
  const [estoque, setEstoque]     = useState([])
  const [prodRaw, setProdRaw]     = useState([])
  const [prodChart, setProdChart] = useState([])
  const [topProdutoras, setTop]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [erro, setErro]           = useState('')
  const [periodo, setPeriodo]     = useState(14)
  const [tipo, setTipo]           = useState('area')

  const buildProdChart = useCallback((raw, dias) => {
    const hj = new Date().toISOString().split('T')[0]
    const ini = new Date(Date.now() - dias * 86400000).toISOString().split('T')[0]
    const filtered = raw.filter(r => r.data >= ini)
    const porDia = {}
    filtered.forEach(r => { porDia[r.data] = (porDia[r.data] || 0) + (r.leite || 0) })
    setProdChart(
      Object.entries(porDia)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([data, litros]) => ({ dia: data.slice(5), litros: +litros.toFixed(1) }))
    )

    // Top do dia
    const porAnimal = {}
    raw.filter(r => r.data === hj).forEach(r => {
      const nome = r.nome_animal || '?'
      porAnimal[nome] = (porAnimal[nome] || 0) + (r.leite || 0)
    })
    setTop(
      Object.entries(porAnimal)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8)
        .map(([nome, litros]) => ({ nome: nome.slice(0, 10), litros: +litros.toFixed(1) }))
    )
  }, [])

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const [d, a, p, s, e] = await Promise.all([
        api.dashboard(),
        api.animais(),
        api.producao(90), // busca 90d para calcular rentabilidade
        api.sanitario(60),
        api.estoque(),
      ])
      setDash(d)
      setAnimais(a.filter(x => x.status !== 'Vendido'))
      setProdRaw(p)
      setSanitario(s)
      setEstoque(e)
      buildProdChart(p, 14)
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  // Auto-refresh a cada 60s
  useEffect(() => {
    const id = setInterval(() => { carregar() }, 60000)
    return () => clearInterval(id)
  }, [])

  // Re-calcula gráfico quando período muda (sem reload)
  useEffect(() => { buildProdChart(prodRaw, periodo) }, [periodo, prodRaw, buildProdChart])

  if (loading) return <Loading />
  if (erro)    return <ErrorMsg msg={erro} onRetry={carregar} />
  if (!dash)   return <ErrorMsg msg="Sem dados do servidor." onRetry={carregar} />

  const n = (v, d = 1) => Number(v || 0).toFixed(d)

  const h       = dash.hoje   || {}
  const semana  = dash.semana || {}
  const mes     = dash.mes    || {}
  const preco_leite     = Number(dash.preco_leite     || 2.50)
  const custo_por_litro = Number(dash.custo_por_litro || 1.18)
  const meta_producao   = Number(dash.meta_producao   || 0)

  const custo   = custo_por_litro || 1.18
  const margem  = preco_leite > 0 ? (((preco_leite - custo) / preco_leite) * 100) : 0
  const pendentes = (h.vacas_lact || 0) - (h.vacas_ordenhadas || 0)

  // Rentabilidade por animal (últimos 30 dias)
  const ini30 = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0]
  const rentab = {}
  prodRaw.filter(r => r.data >= ini30).forEach(r => {
    const nome = r.nome_animal || '?'
    if (!rentab[nome]) rentab[nome] = { nome, litros: 0, racao_kg: 0 }
    rentab[nome].litros   += Number(r.leite  || 0)
    rentab[nome].racao_kg += Number(r.racao  || 0)
  })
  const rentabList = Object.values(rentab)
    .map(r => ({
      ...r,
      litros:      +Number(r.litros   || 0).toFixed(1),
      racao_kg:    +Number(r.racao_kg || 0).toFixed(1),
      receita:     +Number((r.litros || 0) * preco_leite).toFixed(2),
      custo_racao: +Number((r.racao_kg || 0) * 1.20).toFixed(2),
      margem:      +Number((r.litros || 0) * preco_leite - (r.racao_kg || 0) * 1.20).toFixed(2),
    }))
    .sort((a, b) => b.margem - a.margem)
    .slice(0, 10)

  const KPIS = [
    {
      label: 'Produção Hoje', value: n(h.litros), unit: 'L',
      delta: h.delta_producao, accent: true,
      sub: `ontem: ${n(h.litros_ontem)}L · ${pendentes > 0 ? `${pendentes} pendentes` : 'completo'}`,
    },
    {
      label: 'Receita Estimada', value: fmtBRL(h.receita_est || 0),
      delta: h.delta_producao,
      sub: `R$ ${n(preco_leite, 2)}/L`,
    },
    {
      label: 'Custo/Litro', value: `R$ ${n(custo, 2)}`,
      sub: 'Operacional configurado',
    },
    {
      label: 'Margem Op.', value: n(margem), unit: '%',
      delta: semana.delta_semana,
      sub: `7d: ${n(semana.litros_7d, 0)}L · ${n(semana.media_dia)}L/dia`,
    },
    {
      label: 'Saldo do Mês',
      value: (mes.saldo || 0) >= 0 ? fmtBRL(mes.saldo || 0) : `-${fmtBRL(Math.abs(mes.saldo || 0))}`,
      delta: mes.delta_saldo,
      sub: `Rec ${fmtBRL(mes.receitas || 0)} · Des ${fmtBRL(mes.despesas || 0)}`,
      last: true,
    },
  ]

  const tickStyle = { fill: '#475569', fontSize: 11, fontFamily: 'monospace' }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 shrink-0"
           style={{ borderBottom: `1px solid ${T.border}` }}>
        {KPIS.map((k, i) => (
          <KpiCard key={k.label} {...k} last={i === KPIS.length - 1} />
        ))}
      </div>

      {/* Meta de produção */}
      {meta_producao > 0 && (
        <div className="px-5 py-3 shrink-0 flex items-center gap-4"
             style={{ borderBottom: `1px solid ${T.border}`, background: 'rgba(59,130,246,0.03)' }}>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] font-mono text-slate-500 uppercase tracking-widest">Meta dia</span>
            <span className="text-[11px] font-mono text-slate-300 tabular-nums">
              {n(h.litros, 0)} / {n(meta_producao, 0)} L
            </span>
            <span className={`text-[11px] font-mono font-semibold tabular-nums ${(h.litros || 0) >= meta_producao ? 'text-emerald-400' : 'text-slate-400'}`}>
              ({meta_producao > 0 ? (((h.litros || 0) / meta_producao) * 100).toFixed(0) : 0}%)
            </span>
          </div>
          <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: T.border }}>
            <div className="h-full rounded-full transition-all duration-500"
                 style={{
                   width: `${Math.min(100, (h.litros / meta_producao) * 100)}%`,
                   background: h.litros >= meta_producao ? '#16a34a' : '#3b82f6',
                 }} />
          </div>
        </div>
      )}

      {/* Alertas */}
      <AlertasBanner
        animais={animais}
        sanitario={sanitario}
        estoque={estoque}
        pendentes={pendentes}
      />

      {/* Gráficos */}
      <div className="grid grid-cols-1 md:grid-cols-2 shrink-0">
        <div className="p-5" style={{ borderRight: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
          <div className="mb-3 space-y-2">
            <p className="text-[11px] font-mono uppercase tracking-widest text-slate-500">
              Produção — {periodo} dias (L/dia)
            </p>
            <ChartControls
              periodo={periodo} setPeriodo={setPeriodo}
              tipo={tipo}       setTipo={setTipo}
              periodos={[7, 14, 30, 60, 90]}
            />
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <ProdChart data={prodChart} tipo={tipo} />
          </ResponsiveContainer>
        </div>

        <div className="p-5" style={{ borderBottom: `1px solid ${T.border}` }}>
          <p className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-3">
            Top produtoras — hoje (L)
          </p>
          {topProdutoras.length === 0
            ? <div className="flex items-center justify-center h-[170px] text-slate-700 text-xs font-mono">
                sem registros hoje
              </div>
            : (
              <ResponsiveContainer width="100%" height={170}>
                <BarChart data={topProdutoras} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 5" stroke="#1a2640" horizontal={false} />
                  <XAxis type="number" tick={tickStyle} unit="L" />
                  <YAxis type="category" dataKey="nome" tick={{ ...tickStyle, fill: '#94a3b8' }} width={72} />
                  <Tooltip content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    return (
                      <div style={{ background: T.surface, border: `1px solid ${T.border}` }}
                           className="rounded-lg px-3 py-2 text-[11px] shadow-xl">
                        <p className="text-slate-300 font-semibold">{payload[0]?.payload?.nome}</p>
                        <p className="text-emerald-400 font-mono tabular-nums">{payload[0]?.value?.toFixed(1)} L</p>
                      </div>
                    )
                  }} />
                  <Bar dataKey="litros" radius={[0, 4, 4, 0]}>
                    {topProdutoras.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? '#16a34a' : i === 1 ? '#22c55e' : '#334155'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          }
        </div>
      </div>

      {/* Rentabilidade por animal */}
      <div className="flex-1 overflow-auto">
        <SectionHeader title="Rentabilidade por Animal" sub="últimos 30 dias · leite vs ração" />

        {rentabList.length === 0 ? (
          <div className="p-5 text-center text-slate-700 text-xs font-mono">
            registre ração nas ordenhas para ver a rentabilidade por animal
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono min-w-[560px]">
              <thead>
                <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                  {['Animal', 'Litros 30d', 'Ração (kg)', 'Receita', 'Custo Ração', 'Margem'].map(h =>
                    <th key={h} className="text-left px-4 py-2.5 text-slate-600 font-medium text-[11px] tracking-wider first:pl-5">
                      {h}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rentabList.map((r, i) => (
                  <tr key={r.nome} className="hover:bg-white/[0.02]"
                      style={{ borderBottom: `1px solid ${T.border2}` }}>
                    <td className="px-5 py-2.5 text-slate-200 font-semibold">{r.nome}</td>
                    <td className="px-4 py-2.5 text-blue-400 tabular-nums">{r.litros} L</td>
                    <td className="px-4 py-2.5 text-slate-500 tabular-nums">{r.racao_kg} kg</td>
                    <td className="px-4 py-2.5 text-emerald-400 tabular-nums">{fmtBRL(r.receita)}</td>
                    <td className="px-4 py-2.5 text-slate-500 tabular-nums">{fmtBRL(r.custo_racao)}</td>
                    <td className="px-4 py-2.5 tabular-nums font-semibold"
                        style={{ color: r.margem >= 0 ? '#10b981' : '#ef4444' }}>
                      {r.margem >= 0 ? '+' : ''}{fmtBRL(r.margem)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Status do Rebanho */}
        <SectionHeader title="Rebanho" sub={`${animais.length} animais`} />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-5">
          {[
            { status: 'Lactação', cor: '#16a34a', descr: 'Em produção ativa' },
            { status: 'Gestação', cor: '#3b82f6', descr: 'Gestantes' },
            { status: 'Seca',     cor: '#ca8a04', descr: 'Em período seco' },
            { status: 'Novilha',  cor: '#a78bfa', descr: 'Ainda não paridas' },
            { status: 'Bezerro',  cor: '#fb923c', descr: 'Bezerros e bezerras' },
          ].map(({ status, cor, descr }) => {
            const lista = animais.filter(a => a.status === status)
            if (lista.length === 0) return null
            const prodTotal = lista.reduce((s, a) => s + (a.prod || 0), 0)
            return (
              <div key={status} className="rounded-xl p-4"
                   style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: cor }} />
                    <span className="text-sm font-semibold" style={{ color: cor }}>{status}</span>
                  </div>
                  <span className="text-2xl font-mono font-bold tabular-nums" style={{ color: cor }}>{lista.length}</span>
                </div>
                <p className="text-[11px] font-mono text-slate-600 mb-2">{descr}</p>
                {status === 'Lactação' && prodTotal > 0 && (
                  <div className="text-[11px] font-mono text-slate-500">
                    Prod. hoje: <span className="text-emerald-400 font-semibold">{prodTotal.toFixed(1)} L</span>
                  </div>
                )}
                <div className="mt-2 space-y-1 max-h-[72px] overflow-hidden">
                  {lista.slice(0, 3).map(a => (
                    <div key={a.nome} className="flex items-center justify-between">
                      <span className="text-[11px] font-mono text-slate-400 truncate">{a.nome}</span>
                      {a.prod > 0 && (
                        <span className="text-[11px] font-mono text-slate-500 tabular-nums shrink-0 ml-2">
                          {Number(a.prod).toFixed(1)}L
                        </span>
                      )}
                    </div>
                  ))}
                  {lista.length > 3 && <p className="text-[10px] font-mono text-slate-700">+{lista.length - 3} mais</p>}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
