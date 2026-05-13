/**
 * TabCalendario — Agenda da fazenda
 * Agrega eventos de múltiplas fontes:
 *   - Partos esperados (animais com inseminação)
 *   - Protocolos sanitários pendentes
 *   - Secagens previstas
 * Exibe como timeline mensal com filtro por tipo
 */

import { useEffect, useState, useMemo } from 'react'
import { CalendarDays, Baby, ShieldCheck, Milk, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../api.js'
import { Loading, ErrorMsg, T } from '../ui.jsx'

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function addDays(dateStr, n) {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + n)
  return d.toISOString().split('T')[0]
}

function diffDias(targetStr) {
  const hoje = new Date(); hoje.setHours(0,0,0,0)
  const alvo = new Date(targetStr + 'T00:00:00')
  return Math.round((alvo - hoje) / 86400000)
}

function fmtData(str) {
  if (!str) return '—'
  const [y, m, d] = str.split('-')
  return `${d}/${m}/${y}`
}

function nomeMes(mes0) {
  return ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
          'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][mes0]
}

// ─── TIPOS DE EVENTO ─────────────────────────────────────────────────────────
const TIPOS = {
  parto:    { label: 'Parto esperado',  Icon: Baby,         cor: '#3b82f6', bg: 'rgba(59,130,246,0.10)', border: 'rgba(59,130,246,0.25)' },
  sanitario:{ label: 'Protocolo sanit.',Icon: ShieldCheck,  cor: '#f59e0b', bg: 'rgba(245,158,11,0.10)', border: 'rgba(245,158,11,0.25)' },
  secagem:  { label: 'Secagem prevista',Icon: Milk,         cor: '#a78bfa', bg: 'rgba(167,139,250,0.10)',border: 'rgba(167,139,250,0.25)' },
}

function urgenciaCor(diff) {
  if (diff < 0)  return '#ef4444' // vencido
  if (diff <= 3) return '#ef4444' // urgente
  if (diff <= 7) return '#f59e0b' // esta semana
  return '#64748b'                // futuro
}

function urgenciaLabel(diff) {
  if (diff < 0)  return `${Math.abs(diff)}d atrás`
  if (diff === 0) return 'Hoje'
  if (diff === 1) return 'Amanhã'
  if (diff <= 7) return `em ${diff} dias`
  return `em ${diff} dias`
}

// ─── CARD DE EVENTO ───────────────────────────────────────────────────────────
function EventoCard({ evento }) {
  const t    = TIPOS[evento.tipo] || TIPOS.sanitario
  const diff = diffDias(evento.data)
  const urgCor = urgenciaCor(diff)

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl transition-all"
         style={{ background: t.bg, border: `1px solid ${t.border}` }}>
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
           style={{ background: 'rgba(0,0,0,0.2)' }}>
        <t.Icon size={14} style={{ color: t.cor }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-200 truncate">{evento.titulo}</p>
            <p className="text-[11px] font-mono mt-0.5" style={{ color: t.cor }}>{t.label}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs font-mono text-slate-400 tabular-nums">{fmtData(evento.data)}</p>
            <p className="text-[11px] font-mono mt-0.5 tabular-nums" style={{ color: urgCor }}>
              {urgenciaLabel(diff)}
            </p>
          </div>
        </div>
        {evento.descricao && (
          <p className="text-[11px] font-mono text-slate-500 mt-1.5 truncate">{evento.descricao}</p>
        )}
      </div>
    </div>
  )
}

// ─── MINI CALENDÁRIO ─────────────────────────────────────────────────────────
function MiniCalendar({ ano, mes, eventos, onMes }) {
  const hoje     = new Date(); hoje.setHours(0,0,0,0)
  const primeiro = new Date(ano, mes, 1)
  const ultimo   = new Date(ano, mes + 1, 0).getDate()
  const inicioSem = primeiro.getDay() // 0=Dom

  const eventosDias = {}
  eventos.forEach(e => {
    const [y, m, d] = (e.data || '').split('-').map(Number)
    if (y === ano && m - 1 === mes) {
      eventosDias[d] = (eventosDias[d] || [])
      eventosDias[d].push(e)
    }
  })

  const celulas = []
  for (let i = 0; i < inicioSem; i++) celulas.push(null)
  for (let d = 1; d <= ultimo; d++)   celulas.push(d)

  const prev = () => onMes(mes === 0 ? [ano - 1, 11] : [ano, mes - 1])
  const next = () => onMes(mes === 11 ? [ano + 1, 0] : [ano, mes + 1])

  return (
    <div className="rounded-xl overflow-hidden"
         style={{ background: T.surface, border: `1px solid ${T.border}` }}>
      {/* Cabeçalho */}
      <div className="flex items-center justify-between px-4 py-3"
           style={{ borderBottom: `1px solid ${T.border}` }}>
        <button onClick={prev} className="p-1.5 text-slate-600 hover:text-slate-300 transition-colors rounded-lg">
          <ChevronLeft size={15} />
        </button>
        <span className="text-sm font-semibold text-slate-300">
          {nomeMes(mes)} {ano}
        </span>
        <button onClick={next} className="p-1.5 text-slate-600 hover:text-slate-300 transition-colors rounded-lg">
          <ChevronRight size={15} />
        </button>
      </div>

      {/* Dias da semana */}
      <div className="grid grid-cols-7 text-center"
           style={{ borderBottom: `1px solid ${T.border}` }}>
        {['D','S','T','Q','Q','S','S'].map((d, i) => (
          <div key={i} className="py-2 text-[10px] font-mono text-slate-700 uppercase">{d}</div>
        ))}
      </div>

      {/* Grade de dias */}
      <div className="grid grid-cols-7">
        {celulas.map((dia, i) => {
          if (!dia) return <div key={i} />
          const dataStr = `${ano}-${String(mes+1).padStart(2,'0')}-${String(dia).padStart(2,'0')}`
          const ehHoje  = new Date(dataStr + 'T00:00:00').getTime() === hoje.getTime()
          const evs     = eventosDias[dia] || []
          return (
            <div key={i} className="flex flex-col items-center py-2 gap-1">
              <span className="w-7 h-7 flex items-center justify-center rounded-full text-xs font-mono font-medium"
                    style={{
                      background: ehHoje ? '#16a34a' : 'transparent',
                      color:      ehHoje ? '#fff' : evs.length > 0 ? '#f1f5f9' : '#475569',
                    }}>
                {dia}
              </span>
              {evs.length > 0 && (
                <div className="flex gap-0.5">
                  {evs.slice(0, 3).map((e, j) => (
                    <span key={j} className="w-1 h-1 rounded-full"
                          style={{ background: TIPOS[e.tipo]?.cor || '#64748b' }} />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Legenda */}
      <div className="flex items-center gap-4 px-4 py-3" style={{ borderTop: `1px solid ${T.border}` }}>
        {Object.entries(TIPOS).map(([key, t]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: t.cor }} />
            <span className="text-[10px] font-mono text-slate-600">{t.label.split(' ')[0]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── PRINCIPAL ───────────────────────────────────────────────────────────────
export default function TabCalendario() {
  const [animais, setAnimais]   = useState([])
  const [sanit, setSanit]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [erro, setErro]         = useState('')
  const [filtroTipo, setFiltro] = useState('todos')
  const hoje = new Date()
  const [mesVis, setMesVis]     = useState([hoje.getFullYear(), hoje.getMonth()])

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const [a, s] = await Promise.all([api.animais(), api.sanitario(365)])
      setAnimais(a)
      setSanit(s)
    } catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  // Gera eventos a partir dos dados
  const eventos = useMemo(() => {
    const evs = []

    // Partos esperados (animais com inseminação)
    animais.forEach(a => {
      if (a.ins || a.inseminacao) {
        const dataParto = addDays(a.ins || a.inseminacao, 283)
        evs.push({
          tipo:      'parto',
          data:      dataParto,
          titulo:    a.nome,
          descricao: `${a.raca || ''} · Inseminação: ${fmtData(a.ins || a.inseminacao)}`.trim(),
        })
      }
      // Secagem prevista (vacas em lactação: seca ~60d antes do parto)
      if (a.status === 'Lactação' && (a.ins || a.inseminacao)) {
        const dataSecagem = addDays(a.ins || a.inseminacao, 223) // parto - 60d
        const diff = diffDias(dataSecagem)
        if (diff > -30 && diff < 120) {
          evs.push({
            tipo:      'secagem',
            data:      dataSecagem,
            titulo:    a.nome,
            descricao: 'Secagem recomendada 60 dias antes do parto',
          })
        }
      }
    })

    // Protocolos sanitários pendentes
    sanit.forEach(s => {
      if (!s.executado) {
        evs.push({
          tipo:      'sanitario',
          data:      s.data,
          titulo:    s.animal || 'Rebanho',
          descricao: `${s.tipo} · ${s.protocolo || ''}`.trim().replace(/· $/, ''),
        })
      }
    })

    return evs.sort((a, b) => a.data.localeCompare(b.data))
  }, [animais, sanit])

  const filtrados = useMemo(() => {
    if (filtroTipo === 'todos') return eventos
    return eventos.filter(e => e.tipo === filtroTipo)
  }, [eventos, filtroTipo])

  // Separa: próximos 30 dias vs futuros
  const hojeStr  = hoje.toISOString().split('T')[0]
  const em30     = new Date(); em30.setDate(em30.getDate() + 30)
  const em30Str  = em30.toISOString().split('T')[0]

  const proximos = filtrados.filter(e => e.data >= hojeStr && e.data <= em30Str)
  const futuros  = filtrados.filter(e => e.data > em30Str)
  const vencidos = filtrados.filter(e => e.data < hojeStr)

  if (loading) return <Loading />

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* Resumo */}
      <div className="grid grid-cols-3 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: 'Esta semana', value: filtrados.filter(e => diffDias(e.data) >= 0 && diffDias(e.data) <= 7).length, cor: 'text-emerald-400' },
          { label: 'Próx. 30 dias', value: proximos.length, cor: 'text-blue-400' },
          { label: 'Pendentes',    value: vencidos.length,  cor: vencidos.length > 0 ? 'text-red-400' : 'text-slate-500' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-5"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : 'none' }}>
            <p className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-2">{k.label}</p>
            <p className={`text-2xl font-mono font-bold tabular-nums ${k.cor}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* Coluna esquerda: calendário + filtros */}
        <div className="hidden lg:flex flex-col w-72 shrink-0 overflow-y-auto p-5 gap-5"
             style={{ borderRight: `1px solid ${T.border}` }}>
          <MiniCalendar
            ano={mesVis[0]} mes={mesVis[1]}
            eventos={filtrados}
            onMes={([a, m]) => setMesVis([a, m])}
          />

          {/* Filtros */}
          <div>
            <p className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-3">Filtrar por tipo</p>
            <div className="space-y-1">
              <button onClick={() => setFiltro('todos')}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all"
                style={{
                  background: filtroTipo === 'todos' ? '#1e293b' : 'transparent',
                  color: filtroTipo === 'todos' ? '#cbd5e1' : '#64748b',
                }}>
                <span>Todos os eventos</span>
                <span className="font-mono tabular-nums">{eventos.length}</span>
              </button>
              {Object.entries(TIPOS).map(([key, t]) => (
                <button key={key} onClick={() => setFiltro(filtroTipo === key ? 'todos' : key)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all"
                  style={{
                    background: filtroTipo === key ? t.bg : 'transparent',
                    color:      filtroTipo === key ? t.cor : '#64748b',
                  }}>
                  <t.Icon size={13} />
                  <span className="flex-1 text-left">{t.label}</span>
                  <span className="font-mono tabular-nums">
                    {eventos.filter(e => e.tipo === key).length}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <button onClick={carregar}
            className="flex items-center gap-2 text-xs font-mono text-slate-600 hover:text-slate-400 transition-colors">
            <RefreshCw size={12} /> Atualizar
          </button>
        </div>

        {/* Coluna direita: lista de eventos */}
        <div className="flex-1 overflow-y-auto">

          {/* Filtros mobile */}
          <div className="lg:hidden flex items-center gap-2 px-4 py-3 overflow-x-auto shrink-0"
               style={{ borderBottom: `1px solid ${T.border}` }}>
            {[{ key: 'todos', label: 'Todos' }, ...Object.entries(TIPOS).map(([k, t]) => ({ key: k, label: t.label.split(' ')[0] }))].map(f => (
              <button key={f.key} onClick={() => setFiltro(f.key)}
                className="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all shrink-0"
                style={{
                  background: filtroTipo === f.key ? '#1e293b' : 'transparent',
                  border: `1px solid ${filtroTipo === f.key ? '#334155' : 'transparent'}`,
                  color: filtroTipo === f.key ? '#cbd5e1' : '#64748b',
                }}>
                {f.label}
              </button>
            ))}
          </div>

          <div className="p-5 space-y-8">

            {vencidos.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs font-semibold text-red-400 uppercase tracking-widest">Pendentes / vencidos</span>
                  <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold bg-red-500/20 text-red-400">
                    {vencidos.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {vencidos.map((e, i) => <EventoCard key={i} evento={e} />)}
                </div>
              </section>
            )}

            {proximos.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Próximos 30 dias</span>
                  <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold"
                        style={{ background: '#1e293b', color: '#94a3b8' }}>
                    {proximos.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {proximos.map((e, i) => <EventoCard key={i} evento={e} />)}
                </div>
              </section>
            )}

            {futuros.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs font-semibold text-slate-600 uppercase tracking-widest">Mais à frente</span>
                </div>
                <div className="space-y-3">
                  {futuros.slice(0, 20).map((e, i) => <EventoCard key={i} evento={e} />)}
                  {futuros.length > 20 && (
                    <p className="text-center text-xs font-mono text-slate-700 py-2">
                      +{futuros.length - 20} eventos futuros
                    </p>
                  )}
                </div>
              </section>
            )}

            {filtrados.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 gap-3">
                <div className="w-12 h-12 rounded-full flex items-center justify-center"
                     style={{ background: T.surface, border: `1px solid ${T.border}` }}>
                  <CalendarDays size={18} className="text-slate-700" />
                </div>
                <p className="text-slate-600 text-xs font-mono">nenhum evento encontrado</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
