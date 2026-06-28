/**
 * TabNutricao — Fábrica de Ração
 * Motor nutricional interativo: selecione ingredientes, ajuste kg, veja a tabela em tempo real.
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Plus, Trash2, Calculator, Save, ChevronDown, ChevronRight,
  AlertTriangle, CheckCircle, Info, Loader2, FlaskConical, FileDown,
} from 'lucide-react'
import { api } from '../api.js'
import { Loading, fmtBRL, Btn, Field, Input } from '../ui.jsx'

const C = {
  brand:  '#22c55e', brand2: '#16a34a',
  bg:     '#f1f4f1', white:  '#ffffff',
  border: '#e8ede8', text:   '#1a2e1a',
  sub:    '#4a6741', muted:  '#8aaa85',
}

// ─── BARRA NUTRICIONAL ────────────────────────────────────────────────────────
function NutBar({ label, value, max, color, unit = '%' }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] font-semibold text-slate-500">{label}</span>
        <span className="text-[12px] font-bold" style={{ color }}>{value.toFixed(2)}{unit}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

// ─── CARD DE INGREDIENTE NA PALETA ───────────────────────────────────────────
function InsumoCard({ item, onAdd }) {
  return (
    <button onClick={() => onAdd(item)}
      className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-left transition-all hover:shadow-sm active:scale-[0.98] group"
      style={{ background: '#f8faf8', border: '1px solid #e8ede8' }}>
      <span className="text-lg shrink-0">{item.emoji}</span>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-semibold text-slate-700 truncate">{item.nome}</p>
        <p className="text-[10px] text-slate-400">NDT {item.ndt}% · PB {item.pb}%</p>
      </div>
      <Plus size={13} className="shrink-0 text-green-400 opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  )
}

// ─── LINHA DA FÓRMULA ─────────────────────────────────────────────────────────
function FormulaRow({ item, index, onChange, onRemove }) {
  return (
    <div className="flex items-center gap-2 py-2 border-b last:border-0" style={{ borderColor: '#f0f4f0' }}>
      <span className="text-base shrink-0 w-6 text-center">{item.emoji}</span>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-semibold text-slate-700 truncate">{item.nome}</p>
        <p className="text-[10px] text-slate-400">MS {item.ms}% · NDT {item.ndt}% · PB {item.pb}%</p>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <input
          type="number" min="0" step="0.1"
          value={item.kg}
          onChange={e => onChange(index, parseFloat(e.target.value) || 0)}
          className="w-20 text-center text-[13px] font-bold rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200"
          style={{ padding: '5px 8px', border: '1px solid #d4e6d4', background: '#f8faf8', color: '#1a2e1a' }}
        />
        <span className="text-[11px] text-slate-400">kg</span>
      </div>
      <button onClick={() => onRemove(index)}
        className="w-7 h-7 rounded-lg flex items-center justify-center text-red-400 hover:bg-red-50 transition-colors shrink-0">
        <Trash2 size={13} />
      </button>
    </div>
  )
}

// ─── CARD NUTRICIONAL RESULTADO ───────────────────────────────────────────────
function ResultadoCard({ resultado }) {
  if (!resultado) return null
  const n   = resultado.nutrientes    || {}
  const nms = resultado.nutrientes_ms || {}
  const alertas = resultado.alertas   || []

  return (
    <div className="space-y-4">
      {/* Alertas */}
      {alertas.length > 0 && (
        <div className="space-y-2">
          {alertas.map((a, i) => {
            const cor = a.tipo === 'erro' ? '#dc2626' : a.tipo === 'warn' ? '#d97706' : '#2563eb'
            const bg  = a.tipo === 'erro' ? '#fef2f2' : a.tipo === 'warn' ? '#fffbeb' : '#eff6ff'
            const Icon = a.tipo === 'erro' ? AlertTriangle : a.tipo === 'warn' ? AlertTriangle : Info
            return (
              <div key={i} className="flex items-start gap-2 rounded-lg px-3 py-2 text-[12px]"
                   style={{ background: bg, color: cor, border: `1px solid ${cor}25` }}>
                <Icon size={13} className="shrink-0 mt-0.5" />
                <span>{a.msg}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Tabela nutricional */}
      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #e8ede8' }}>
        <div className="px-4 py-2.5 bg-slate-50" style={{ borderBottom: '1px solid #e8ede8' }}>
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Composição Nutricional</p>
        </div>
        <div className="divide-y" style={{ divideColor: '#f0f4f0' }}>
          {[
            { label: 'Matéria Seca (MS)',  val: n.ms,   ms: null,      unit: '%',  color: '#22c55e', max: 100 },
            { label: 'NDT (mat. natural)', val: n.ndt,  ms: nms.ndt,   unit: '%',  color: '#0d9488', max: 100 },
            { label: 'Proteína Bruta (PB)',val: n.pb,   ms: nms.pb,    unit: '%',  color: '#2563eb', max: 50  },
            { label: 'Cálcio (Ca)',        val: n.ca,   ms: nms.ca,    unit: '%',  color: '#d97706', max: 3   },
            { label: 'Fósforo (P)',        val: n.p,    ms: nms.p,     unit: '%',  color: '#7c3aed', max: 2   },
          ].map(({ label, val = 0, ms: valMs, unit, color, max }) => (
            <div key={label} className="px-4 py-2.5">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[12px] font-medium text-slate-600">{label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-bold" style={{ color }}>{(val || 0).toFixed(2)}{unit}</span>
                  {valMs != null && (
                    <span className="text-[10px] text-slate-400 font-mono">({valMs.toFixed(1)}% na MS)</span>
                  )}
                </div>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full rounded-full transition-all duration-700"
                     style={{ width: `${Math.min(100, (val / max) * 100)}%`, background: color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resumo */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-xl p-3 text-center" style={{ border: '1px solid #e8ede8' }}>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Total da Ração</p>
          <p className="text-[22px] font-black" style={{ color: C.brand }}>{resultado.total_kg?.toFixed(1)}</p>
          <p className="text-[10px] text-slate-400">kg (tal-qual)</p>
        </div>
        <div className="bg-white rounded-xl p-3 text-center" style={{ border: '1px solid #e8ede8' }}>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Matéria Seca</p>
          <p className="text-[22px] font-black text-slate-700">{resultado.ms_total_kg?.toFixed(1)}</p>
          <p className="text-[10px] text-slate-400">kg de MS</p>
        </div>
      </div>
    </div>
  )
}

// ─── TAB PRINCIPAL ────────────────────────────────────────────────────────────
export default function TabNutricao() {
  const [insumos,       setInsumos]       = useState([])
  const [formula,       setFormula]       = useState([])
  const [resultado,     setResultado]     = useState(null)
  const [loading,       setLoading]       = useState(true)
  const [calculando,    setCalculando]    = useState(false)
  const [salvando,      setSalvando]      = useState(false)
  const [racoesSalvas,  setRacoesSalvas]  = useState([])
  const [busca,         setBusca]         = useState('')
  const [catAberta,     setCatAberta]     = useState(null)
  const [nomeRacao,     setNomeRacao]     = useState('')
  const [abaAtiva,      setAbaAtiva]      = useState('fabrica') // 'fabrica' | 'salvas'
  const [toast,         setToast]         = useState(null)

  useEffect(() => {
    Promise.all([
      api.get('/nutricao/insumos'),
      api.get('/nutricao/racoes'),
    ]).then(([ins, rac]) => {
      setInsumos(ins)
      setRacoesSalvas(rac)
      if (ins.length > 0) setCatAberta(ins[0].categoria)
    }).catch(console.error)
    .finally(() => setLoading(false))
  }, [])

  // Recalcula sempre que a fórmula muda
  useEffect(() => {
    if (formula.length === 0) { setResultado(null); return }
    const timeout = setTimeout(async () => {
      setCalculando(true)
      try {
        const ingredientes = formula.map(f => ({ nome: f.nome, kg: f.kg }))
        const res = await api.post('/nutricao/calcular', { ingredientes })
        setResultado(res)
      } catch(e) { console.error(e) }
      finally { setCalculando(false) }
    }, 300) // debounce 300ms
    return () => clearTimeout(timeout)
  }, [formula])

  function adicionarInsumo(item) {
    // Se já existe na fórmula, soma 1kg
    const idx = formula.findIndex(f => f.nome === item.nome)
    if (idx >= 0) {
      const nova = [...formula]
      nova[idx] = { ...nova[idx], kg: nova[idx].kg + 1 }
      setFormula(nova)
    } else {
      setFormula(f => [...f, { ...item, kg: 1 }])
    }
  }

  function atualizarKg(index, kg) {
    const nova = [...formula]
    nova[index] = { ...nova[index], kg }
    setFormula(nova)
  }

  function removerInsumo(index) {
    setFormula(f => f.filter((_, i) => i !== index))
  }

  function limpar() {
    setFormula([]); setResultado(null); setNomeRacao('')
  }

  async function salvarRacao() {
    if (formula.length === 0 || !nomeRacao.trim()) return
    setSalvando(true)
    try {
      const ingredientes = formula.map(f => ({ nome: f.nome, kg: f.kg }))
      await api.post('/nutricao/racoes', { nome: nomeRacao.trim(), ingredientes })
      const rac = await api.get('/nutricao/racoes')
      setRacoesSalvas(rac)
      setToast('Ração salva com sucesso!')
      setTimeout(() => setToast(null), 3000)
    } catch(e) { setToast('Erro ao salvar: ' + e.message) }
    finally { setSalvando(false) }
  }

  async function carregarRacao(rac) {
    if (!rac.ingredientes) return
    const nova = rac.ingredientes.map(i => {
      const cat = insumos.find(c => c.itens?.some(it => it.nome === i.nome))
      const it  = cat?.itens?.find(it => it.nome === i.nome) || {}
      return { ...it, nome: i.nome, kg: i.kg }
    })
    setFormula(nova)
    setNomeRacao(rac.nome)
    setAbaAtiva('fabrica')
  }

  async function deletarRacao(id) {
    await api.delete(`/nutricao/racoes/${id}`)
    setRacoesSalvas(r => r.filter(x => x.id !== id))
  }

  // Filtra insumos pelo campo de busca
  const insumosFiltrados = insumos.map(cat => ({
    ...cat,
    itens: cat.itens.filter(it =>
      it.nome.toLowerCase().includes(busca.toLowerCase()) ||
      it.categoria.toLowerCase().includes(busca.toLowerCase())
    )
  })).filter(cat => cat.itens.length > 0)

  const totalKg = formula.reduce((s, f) => s + (f.kg || 0), 0)

  if (loading) return <Loading />

  return (
    <div className="flex h-full overflow-hidden" style={{ background: C.bg }}>

      {/* ── PAINEL ESQUERDO: Paleta de Ingredientes ── */}
      <div className="w-72 shrink-0 flex flex-col bg-white overflow-hidden"
           style={{ borderRight: '1px solid #e8ede8' }}>

        <div className="px-4 pt-4 pb-3 shrink-0" style={{ borderBottom: '1px solid #e8ede8' }}>
          <div className="flex items-center gap-2 mb-3">
            <FlaskConical size={16} style={{ color: C.brand }} />
            <h2 className="text-[14px] font-bold text-slate-700">Ingredientes</h2>
          </div>
          <input
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar insumo..."
            className="w-full text-[13px] rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200"
            style={{ padding: '7px 12px', border: '1px solid #d4e6d4', background: '#f8faf8', color: '#1a2e1a' }}
          />
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {insumosFiltrados.map(cat => (
            <div key={cat.categoria}>
              <button
                className="w-full flex items-center justify-between px-2 py-1.5 rounded text-[11px] font-bold uppercase tracking-wider transition-colors hover:bg-slate-50"
                style={{ color: C.muted }}
                onClick={() => setCatAberta(catAberta === cat.categoria ? null : cat.categoria)}>
                <span>{cat.categoria}</span>
                {catAberta === cat.categoria ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
              {catAberta === cat.categoria && (
                <div className="mt-1 space-y-1 ml-1">
                  {cat.itens.map(item => (
                    <InsumoCard key={item.nome} item={item} onAdd={adicionarInsumo} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── PAINEL DIREITO: Fórmula + Resultado ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Abas */}
        <div className="flex items-center gap-0 px-5 pt-4 shrink-0">
          {[['fabrica', '🏭 Fábrica de Ração'], ['salvas', '💾 Rações Salvas']].map(([id, label]) => (
            <button key={id} onClick={() => setAbaAtiva(id)}
              className="px-4 py-2 text-[13px] font-semibold rounded-t-lg transition-colors"
              style={{
                background: abaAtiva === id ? '#fff' : 'transparent',
                color: abaAtiva === id ? C.brand2 : C.muted,
                border: abaAtiva === id ? '1px solid #e8ede8' : '1px solid transparent',
                borderBottom: abaAtiva === id ? '1px solid #fff' : '1px solid transparent',
                marginBottom: abaAtiva === id ? -1 : 0,
              }}>
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto bg-white p-5"
             style={{ border: '1px solid #e8ede8', borderTop: 'none', borderRadius: '0 12px 12px 12px', margin: '0 20px 20px 20px' }}>

          {/* ── ABA FÁBRICA ── */}
          {abaAtiva === 'fabrica' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">

              {/* Coluna da fórmula */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-[14px] font-bold text-slate-700">
                    Composição da Ração
                    {totalKg > 0 && <span className="ml-2 text-[12px] font-normal text-slate-400">({totalKg.toFixed(1)} kg total)</span>}
                  </h3>
                  {formula.length > 0 && (
                    <button onClick={limpar} className="text-[12px] text-red-400 hover:text-red-600 transition-colors">
                      Limpar tudo
                    </button>
                  )}
                </div>

                {formula.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 gap-3 rounded-xl"
                       style={{ background: '#f8faf8', border: '2px dashed #d4e6d4' }}>
                    <FlaskConical size={28} style={{ color: C.muted }} />
                    <p className="text-[13px] text-slate-500 text-center">
                      Clique nos ingredientes ao lado<br />para adicionar à ração
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #e8ede8' }}>
                    {formula.map((item, i) => (
                      <FormulaRow key={i} item={item} index={i}
                                  onChange={atualizarKg} onRemove={removerInsumo} />
                    ))}
                  </div>
                )}

                {/* Salvar */}
                {formula.length > 0 && (
                  <div className="flex items-center gap-2">
                    <input
                      value={nomeRacao}
                      onChange={e => setNomeRacao(e.target.value)}
                      placeholder="Nome desta ração..."
                      className="flex-1 text-[13px] rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200"
                      style={{ padding: '7px 12px', border: '1px solid #d4e6d4', background: '#f8faf8', color: '#1a2e1a' }}
                    />
                    <Btn variant="primary" size="sm" onClick={salvarRacao} disabled={!nomeRacao.trim() || salvando}>
                      <Save size={13} />
                      {salvando ? 'Salvando...' : 'Salvar'}
                    </Btn>
                  </div>
                )}

                {toast && (
                  <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-[12px]"
                       style={{ background: '#f0fdf4', color: '#15803d', border: '1px solid #86efac' }}>
                    <CheckCircle size={13} />
                    {toast}
                  </div>
                )}
              </div>

              {/* Coluna resultado nutricional */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Calculator size={15} style={{ color: C.brand }} />
                  <h3 className="text-[14px] font-bold text-slate-700">
                    Resultado Nutricional
                    {calculando && <Loader2 size={13} className="ml-2 animate-spin inline" style={{ color: C.brand }} />}
                  </h3>
                </div>

                {resultado ? (
                  <ResultadoCard resultado={resultado} />
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 gap-3 rounded-xl"
                       style={{ background: '#f8faf8', border: '2px dashed #d4e6d4' }}>
                    <Calculator size={28} style={{ color: C.muted }} />
                    <p className="text-[13px] text-slate-400 text-center">
                      Adicione ingredientes para ver<br />o cálculo nutricional em tempo real
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── ABA RAÇÕES SALVAS ── */}
          {abaAtiva === 'salvas' && (
            <div className="space-y-3">
              {racoesSalvas.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 gap-3">
                  <Save size={28} style={{ color: C.muted }} />
                  <p className="text-[13px] text-slate-400">Nenhuma ração salva ainda.</p>
                </div>
              ) : racoesSalvas.map(r => (
                <div key={r.id} className="rounded-xl p-4" style={{ border: '1px solid #e8ede8', background: '#fafcfa' }}>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <p className="text-[14px] font-bold text-slate-700">{r.nome}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {r.ingredientes?.length || 0} ingredientes · {r.total_kg?.toFixed(1) || '?'} kg total
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Btn variant="outline" size="xs" onClick={() => carregarRacao(r)}>Carregar</Btn>
                      <button onClick={() => deletarRacao(r.id)}
                        className="text-red-400 hover:text-red-600 transition-colors p-1">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  {/* Mini tabela nutricional */}
                  {r.nutrientes && (
                    <div className="grid grid-cols-5 gap-2">
                      {[
                        { k: 'ms',  label: 'MS',  color: '#22c55e' },
                        { k: 'ndt', label: 'NDT', color: '#0d9488' },
                        { k: 'pb',  label: 'PB',  color: '#2563eb' },
                        { k: 'ca',  label: 'Ca',  color: '#d97706' },
                        { k: 'p',   label: 'P',   color: '#7c3aed' },
                      ].map(({ k, label, color }) => (
                        <div key={k} className="text-center rounded-lg py-1.5 px-1"
                             style={{ background: `${color}12`, border: `1px solid ${color}25` }}>
                          <p className="text-[9px] font-bold uppercase" style={{ color }}>{label}</p>
                          <p className="text-[12px] font-black" style={{ color }}>{(r.nutrientes[k] || 0).toFixed(1)}%</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
