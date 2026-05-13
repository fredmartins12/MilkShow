import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

/* ── KPI Card ── */
function KpiCard({ label, value, sub, icon, color = 'green', trend }) {
  const colors = {
    green:  { bg: 'bg-green-50',  text: 'text-green-700',  icon: 'bg-green-100',  val: 'text-green-800' },
    blue:   { bg: 'bg-blue-50',   text: 'text-blue-700',   icon: 'bg-blue-100',   val: 'text-blue-800'  },
    amber:  { bg: 'bg-amber-50',  text: 'text-amber-700',  icon: 'bg-amber-100',  val: 'text-amber-800' },
    red:    { bg: 'bg-red-50',    text: 'text-red-700',    icon: 'bg-red-100',    val: 'text-red-800'   },
    slate:  { bg: 'bg-slate-50',  text: 'text-slate-600',  icon: 'bg-slate-100',  val: 'text-slate-800' },
  }
  const c = colors[color] || colors.green
  return (
    <div className={`${c.bg} rounded-2xl p-4 md:p-5 flex flex-col gap-3`}>
      <div className="flex items-center justify-between">
        <span className={`w-9 h-9 rounded-xl ${c.icon} flex items-center justify-center text-lg`}>
          {icon}
        </span>
        {trend !== undefined && (
          <span className={`text-xs font-semibold ${trend >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div>
        <div className={`text-2xl md:text-3xl font-extrabold ${c.val} leading-none`}>{value}</div>
        <div className={`text-xs font-semibold ${c.text} mt-1 uppercase tracking-wide`}>{label}</div>
        {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

/* ── Tooltip do gráfico ── */
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg px-3 py-2 text-sm">
      <p className="text-slate-500 mb-1">{label}</p>
      <p className="font-bold text-green-700">{payload[0].value}L</p>
    </div>
  )
}

export default function Dashboard() {
  const [data, setData]       = useState(null)
  const [producao, setProducao] = useState([])
  const [erro, setErro]       = useState('')
  const [loading, setLoading] = useState(true)
  const nav = useNavigate()

  useEffect(() => { carregar() }, [])

  async function carregar() {
    setLoading(true)
    try {
      const [d, p] = await Promise.all([api.dashboard(), api.producao(14)])
      setData(d)
      // Agrupa produção por data para o gráfico
      const por_dia = {}
      p.forEach(r => {
        por_dia[r.data] = (por_dia[r.data] || 0) + (r.leite || 0)
      })
      const chartData = Object.entries(por_dia)
        .sort(([a], [b]) => a.localeCompare(b))
        .slice(-10)
        .map(([data, litros]) => ({
          data: data.slice(5),   // "MM-DD"
          litros: +litros.toFixed(1),
        }))
      setProducao(chartData)
    } catch (e) {
      setErro(e.message)
    } finally {
      setLoading(false)
    }
  }

  const fmt  = n => `R$ ${Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 0 })}`
  const fmtL = n => `${Number(n).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} L`

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-3 border-green-600 border-t-transparent animate-spin" />
        <span className="text-slate-400 text-sm">Carregando dados...</span>
      </div>
    </div>
  )

  if (erro) return (
    <div className="flex flex-col items-center gap-4 py-20">
      <div className="text-4xl">⚠️</div>
      <p className="text-slate-500 text-center">{erro}</p>
      <button onClick={carregar}
        className="bg-green-600 text-white px-6 py-2.5 rounded-xl font-semibold text-sm hover:bg-green-500 transition-colors">
        Tentar novamente
      </button>
    </div>
  )

  const { hoje, semana, mes, preco_leite } = data
  const pendentes = hoje.vacas_lact - hoje.vacas_ordenhadas

  return (
    <div className="space-y-6">

      {/* Cabeçalho */}
      <div>
        <h2 className="text-2xl font-extrabold text-slate-800">Bom dia! 👋</h2>
        <p className="text-slate-400 text-sm mt-0.5">
          {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </p>
      </div>

      {/* Alerta pendentes */}
      {pendentes > 0 && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3">
          <span className="text-xl">⚠️</span>
          <div>
            <p className="text-amber-800 font-semibold text-sm">
              {pendentes} animal{pendentes > 1 ? 'is' : ''} sem ordenha hoje
            </p>
            <button onClick={() => nav('/ordenha')}
              className="text-amber-600 text-xs font-semibold hover:text-amber-500 mt-0.5">
              Registrar agora →
            </button>
          </div>
        </div>
      )}

      {/* KPIs de hoje */}
      <div>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Hoje</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon="🥛" label="Produção" value={fmtL(hoje.litros)} color="green" />
          <KpiCard icon="💵" label="Receita est." value={fmt(hoje.receita_est)} color="blue" />
          <KpiCard icon="🐄" label="Ordenhas"
            value={`${hoje.vacas_ordenhadas}/${hoje.vacas_lact}`}
            sub={pendentes === 0 ? 'Todas completas ✅' : `${pendentes} pendente${pendentes > 1 ? 's' : ''}`}
            color={pendentes === 0 ? 'green' : 'amber'}
          />
          <KpiCard icon="📋" label="Preço/litro" value={`R$ ${Number(preco_leite).toFixed(2)}`} color="slate" />
        </div>
      </div>

      {/* Gráfico de produção */}
      {producao.length > 1 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-800 text-base">Produção — últimos 10 dias</h3>
              <p className="text-slate-400 text-xs mt-0.5">Litros por dia</p>
            </div>
            <div className="text-right">
              <div className="text-lg font-extrabold text-green-700">{fmtL(semana.litros_7d)}</div>
              <div className="text-xs text-slate-400">em 7 dias</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={producao} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gradLeite" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#16a34a" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="data" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone" dataKey="litros" stroke="#16a34a" strokeWidth={2.5}
                fill="url(#gradLeite)" dot={{ r: 3, fill: '#16a34a', strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#16a34a' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* KPIs do mês */}
      <div>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Mês atual</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KpiCard icon="📈" label="Receitas" value={fmt(mes.receitas)} color="green" />
          <KpiCard icon="📉" label="Despesas" value={fmt(mes.despesas)} color="red" />
          <div className="col-span-2 md:col-span-1">
            <KpiCard icon="💰" label="Saldo"
              value={fmt(mes.saldo)}
              sub={mes.saldo >= 0 ? 'No positivo 🎉' : 'No negativo ⚠️'}
              color={mes.saldo >= 0 ? 'green' : 'red'}
            />
          </div>
        </div>
      </div>

      {/* Ações rápidas */}
      <div>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Ações rápidas</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Registrar Ordenha', icon: '🥛', to: '/ordenha',    bg: 'bg-green-600 hover:bg-green-500' },
            { label: 'Lançar Despesa',    icon: '💸', to: '/financeiro',  bg: 'bg-slate-700 hover:bg-slate-600' },
            { label: 'Ver Rebanho',       icon: '🐄', to: '/rebanho',     bg: 'bg-blue-600 hover:bg-blue-500'  },
            { label: 'Financeiro',        icon: '📊', to: '/financeiro',  bg: 'bg-violet-600 hover:bg-violet-500' },
          ].map(({ label, icon, to, bg }) => (
            <button key={label} onClick={() => nav(to)}
              className={`${bg} text-white rounded-2xl py-4 px-3 font-bold text-sm
                          flex flex-col items-center gap-2 transition-colors shadow-sm`}>
              <span className="text-2xl">{icon}</span>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Semana resumo */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
        <h3 className="font-bold text-slate-800 text-base mb-4">Resumo — últimos 7 dias</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-slate-400 text-xs uppercase tracking-wide mb-1">Total produzido</div>
            <div className="text-2xl font-extrabold text-slate-800">{fmtL(semana.litros_7d)}</div>
          </div>
          <div>
            <div className="text-slate-400 text-xs uppercase tracking-wide mb-1">Média diária</div>
            <div className="text-2xl font-extrabold text-slate-800">{fmtL(semana.media_dia)}</div>
          </div>
        </div>
      </div>

      {/* Refresh */}
      <button onClick={carregar}
        className="w-full py-3 bg-slate-100 hover:bg-slate-200 text-slate-500 rounded-2xl
                   text-sm font-semibold transition-colors">
        🔄 Atualizar dados
      </button>
    </div>
  )
}
