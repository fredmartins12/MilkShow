/**
 * TabRanking — Rankings de Inteligência de Negócios
 * 3 rankings: Produção, Rentabilidade e Alerta de Descarte
 */
import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Trophy, AlertTriangle, DollarSign, Droplets, RefreshCw } from 'lucide-react'
import { api } from '../api.js'
import { Loading, fmtBRL } from '../ui.jsx'

const C = {
  brand: '#22c55e', brand2: '#16a34a',
  bg:    '#f1f4f1', white: '#ffffff',
  border:'#e8ede8', text: '#1a2e1a',
  sub:   '#4a6741', muted: '#8aaa85',
}

const MEDALHAS = ['🥇', '🥈', '🥉']

function getMedalha(pos) {
  return MEDALHAS[pos] || `#${pos + 1}`
}

function PeriodBtn({ label, value, atual, onClick }) {
  return (
    <button onClick={onClick}
      className="px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all"
      style={{
        background: atual === value ? C.brand : '#f0f4f0',
        color: atual === value ? '#fff' : C.muted,
      }}>
      {label}
    </button>
  )
}

// ─── RANKING DE PRODUÇÃO ──────────────────────────────────────────────────────
function RankingProducao({ lista, periodo }) {
  const max = lista[0]?.litros || 1
  return (
    <div className="rounded-xl overflow-hidden bg-white" style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
      <div className="flex items-center gap-2 px-5 py-3.5" style={{ borderBottom: '1px solid #f0f4f0', background: '#f8faf8' }}>
        <Droplets size={15} style={{ color: '#0d9488' }} />
        <h3 className="text-[13px] font-bold text-slate-700">Ranking de Produção</h3>
        <span className="text-[11px] text-slate-400 ml-auto">{periodo} dias</span>
      </div>
      {lista.length === 0 ? (
        <div className="py-10 text-center text-[13px] text-slate-400">Sem dados de produção</div>
      ) : (
        <div className="divide-y" style={{ divideColor: '#f0f4f0' }}>
          {lista.map((a, i) => {
            const pct = (a.litros / max) * 100
            return (
              <div key={a.nome} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50/50 transition-colors">
                <span className="w-7 text-[16px] text-center shrink-0">{getMedalha(i)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[13px] font-semibold text-slate-700 truncate">{a.nome}</p>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                      <span className="text-[13px] font-black" style={{ color: '#0d9488' }}>{a.litros.toFixed(1)} L</span>
                      <span className="text-[10px] text-slate-400">({a.media_dia} L/dia)</span>
                    </div>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700"
                         style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #0d9488, #14b8a6)' }} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── RANKING DE RENTABILIDADE ─────────────────────────────────────────────────
function RankingRentabilidade({ lista, periodo, precoLeite }) {
  const minCusto = lista.length > 0 ? Math.min(...lista.map(a => a.custo_litro)) : 0
  const maxCusto = lista.length > 0 ? Math.max(...lista.map(a => a.custo_litro)) : 1
  const range    = maxCusto - minCusto || 1

  return (
    <div className="rounded-xl overflow-hidden bg-white" style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
      <div className="flex items-center gap-2 px-5 py-3.5" style={{ borderBottom: '1px solid #f0f4f0', background: '#f8faf8' }}>
        <DollarSign size={15} style={{ color: '#22c55e' }} />
        <h3 className="text-[13px] font-bold text-slate-700">Ranking de Rentabilidade</h3>
        <span className="text-[11px] text-slate-400 ml-auto">Preço: R$ {precoLeite?.toFixed(2)}/L</span>
      </div>
      {lista.length === 0 ? (
        <div className="py-10 text-center text-[13px] text-slate-400">Sem dados suficientes</div>
      ) : (
        <div className="divide-y" style={{ divideColor: '#f0f4f0' }}>
          {lista.map((a, i) => {
            const lucrativo = a.lucro >= 0
            const pct = Math.max(5, ((a.custo_litro - minCusto) / range) * 100)
            const corBarra = lucrativo ? '#22c55e' : '#ef4444'
            return (
              <div key={a.nome} className="px-5 py-3 hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="w-7 text-[16px] text-center shrink-0">{getMedalha(i)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[13px] font-semibold text-slate-700 truncate">{a.nome}</p>
                      <div className="flex items-center gap-2 shrink-0 ml-2 text-right">
                        <div>
                          <p className="text-[12px] font-black" style={{ color: lucrativo ? '#15803d' : '#dc2626' }}>
                            {lucrativo ? '+' : ''}{fmtBRL(a.lucro)}
                          </p>
                          <p className="text-[10px] text-slate-400">R$ {a.custo_litro.toFixed(3)}/L custo</p>
                        </div>
                        {lucrativo
                          ? <TrendingUp size={15} style={{ color: '#22c55e' }} />
                          : <TrendingDown size={15} style={{ color: '#ef4444' }} />}
                      </div>
                    </div>
                    {/* Barra custo vs preço */}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-700"
                             style={{ width: `${pct}%`, background: corBarra }} />
                      </div>
                      <span className="text-[10px] font-semibold shrink-0" style={{ color: lucrativo ? '#15803d' : '#dc2626' }}>
                        {a.margem_pct.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── RANKING DE ALERTA DE DESCARTE ────────────────────────────────────────────
function RankingDescarte({ lista }) {
  const problemáticos = lista.filter(a => a.margem_pct < 20 || a.lucro < 0)

  return (
    <div className="rounded-xl overflow-hidden bg-white" style={{ border: '1px solid #e8ede8', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
      <div className="flex items-center gap-2 px-5 py-3.5" style={{ borderBottom: '1px solid #f0f4f0', background: '#fff7ed' }}>
        <AlertTriangle size={15} style={{ color: '#d97706' }} />
        <h3 className="text-[13px] font-bold text-slate-700">Alerta de Descarte</h3>
        <span className="text-[11px]" style={{ color: '#d97706', marginLeft: 'auto' }}>
          {problemáticos.length} animais em atenção
        </span>
      </div>
      {lista.length === 0 ? (
        <div className="py-10 text-center text-[13px] text-slate-400">Sem dados suficientes</div>
      ) : problemáticos.length === 0 ? (
        <div className="flex flex-col items-center py-8 gap-2">
          <Trophy size={28} style={{ color: '#22c55e' }} />
          <p className="text-[13px] text-slate-500">Todos os animais com boa rentabilidade!</p>
        </div>
      ) : (
        <div className="divide-y" style={{ divideColor: '#f0f4f0' }}>
          {problemáticos.map((a, i) => {
            const critico   = a.lucro < 0
            const cor       = critico ? '#dc2626' : '#d97706'
            const bgAlert   = critico ? '#fef2f2' : '#fffbeb'
            const nivelText = critico ? '⛔ Prejuízo absoluto' : '⚠️ Margem baixa'
            return (
              <div key={a.nome} className="px-5 py-3 hover:bg-red-50/30 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                       style={{ background: `${cor}15` }}>
                    <AlertTriangle size={13} style={{ color: cor }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[13px] font-bold text-slate-700">{a.nome}</p>
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-full"
                            style={{ background: bgAlert, color: cor }}>
                        {a.margem_pct.toFixed(1)}% margem
                      </span>
                    </div>
                    <p className="text-[11px] mb-1.5" style={{ color: cor }}>{nivelText}</p>
                    <div className="grid grid-cols-3 gap-2 text-[10px]">
                      <div className="text-center rounded-lg py-1" style={{ background: '#f8faf8' }}>
                        <p className="text-slate-400">Produção</p>
                        <p className="font-bold text-slate-600">{a.litros.toFixed(1)} L</p>
                      </div>
                      <div className="text-center rounded-lg py-1" style={{ background: '#f8faf8' }}>
                        <p className="text-slate-400">Receita</p>
                        <p className="font-bold text-slate-600">{fmtBRL(a.receita)}</p>
                      </div>
                      <div className="text-center rounded-lg py-1" style={{ background: bgAlert }}>
                        <p style={{ color: cor }}>Resultado</p>
                        <p className="font-bold" style={{ color: cor }}>
                          {a.lucro >= 0 ? '+' : ''}{fmtBRL(a.lucro)}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── SUMMARY CARDS ────────────────────────────────────────────────────────────
function SummaryCards({ data }) {
  if (!data) return null
  const prod = data.producao || []
  const totalLitros   = prod.reduce((s, a) => s + a.litros, 0)
  const totalReceita  = prod.reduce((s, a) => s + a.receita, 0)
  const totalLucro    = prod.reduce((s, a) => s + a.lucro, 0)
  const lucrativosPct = prod.length > 0
    ? Math.round(prod.filter(a => a.lucro > 0).length / prod.length * 100) : 0

  const cards = [
    { label: 'Total Produzido',     value: `${totalLitros.toFixed(0)} L`,  sub: `${data.total_animais} animais`, color: '#0d9488', gradient: 'linear-gradient(135deg,#0d9488,#14b8a6)' },
    { label: 'Receita Total',       value: fmtBRL(totalReceita),            sub: `${data.dias} dias`,             color: '#22c55e', gradient: 'linear-gradient(135deg,#16a34a,#22c55e)' },
    { label: 'Lucro / Prejuízo',    value: fmtBRL(totalLucro),             sub: totalLucro >= 0 ? 'Positivo ✅' : 'Negativo ⚠️', color: totalLucro >= 0 ? '#22c55e' : '#ef4444', gradient: totalLucro >= 0 ? 'linear-gradient(135deg,#059669,#10b981)' : 'linear-gradient(135deg,#b91c1c,#ef4444)' },
    { label: 'Animais Lucrativos',  value: `${lucrativosPct}%`,            sub: `${prod.filter(a => a.lucro > 0).length} de ${prod.length}`, color: '#7c3aed', gradient: 'linear-gradient(135deg,#6d28d9,#8b5cf6)' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-px mb-4"
         style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 12, overflow: 'hidden', border: '1px solid #e8ede8' }}>
      {cards.map(c => (
        <div key={c.label} className="relative p-4 overflow-hidden"
             style={{ background: c.gradient, minHeight: 90 }}>
          <p className="text-[10px] font-bold uppercase tracking-wider text-white/70 mb-2">{c.label}</p>
          <p className="text-[20px] font-black text-white leading-none">{c.value}</p>
          <p className="text-[10px] text-white/60 mt-1">{c.sub}</p>
        </div>
      ))}
    </div>
  )
}

// ─── TAB PRINCIPAL ────────────────────────────────────────────────────────────
export default function TabRanking() {
  const [data,      setData]      = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [periodo,   setPeriodo]   = useState(30)
  const [atualizando, setAtual]   = useState(false)

  async function carregar(dias = periodo) {
    setAtual(true)
    try {
      const res = await api.get(`/rankings?dias=${dias}`)
      setData(res)
    } catch(e) { console.error(e) }
    finally { setLoading(false); setAtual(false) }
  }

  useEffect(() => { carregar(periodo) }, [periodo])

  if (loading) return <Loading />

  return (
    <div className="overflow-y-auto p-5 space-y-5" style={{ background: C.bg }}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[16px] font-bold text-slate-700">Rankings de Desempenho</h2>
          <p className="text-[12px] text-slate-400">Inteligência de negócios por animal</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30, 60, 90].map(d => (
            <PeriodBtn key={d} label={`${d}d`} value={d} atual={periodo} onClick={() => setPeriodo(d)} />
          ))}
          <button onClick={() => carregar(periodo)}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors hover:bg-white"
            style={{ border: '1px solid #d4e6d4', color: C.muted }}>
            <RefreshCw size={13} className={atualizando ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* KPI Cards topo */}
      <SummaryCards data={data} />

      {/* 3 rankings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <RankingProducao     lista={data?.producao || []}        periodo={periodo} />
        <RankingRentabilidade lista={data?.rentabilidade || []}  periodo={periodo} precoLeite={data?.preco_leite} />
        <RankingDescarte     lista={data?.alerta_descarte || []} />
      </div>

      {/* Rodapé informativo */}
      <div className="rounded-xl p-4 text-[11px] text-slate-500 leading-relaxed"
           style={{ background: '#fff', border: '1px solid #e8ede8' }}>
        <p className="font-semibold text-slate-600 mb-1">ℹ️ Metodologia do Cálculo</p>
        <p>
          Rentabilidade = Receita (litros × preço R$ {data?.preco_leite?.toFixed(2)}/L)
          − Custo Ração ({data?.custo_racao_kg?.toFixed(2)} R$/kg × kg consumidos)
          − Custos Veterinários do período.
          Período: últimos {periodo} dias.
        </p>
      </div>
    </div>
  )
}
