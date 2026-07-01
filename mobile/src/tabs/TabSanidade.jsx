import { useEffect, useState } from 'react'
import { Plus, RefreshCw, CheckCircle2, Users, ShieldCheck } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, Badge, Empty, T, hoje,
} from '../ui.jsx'

const TIPOS = ['Vacina', 'Exame', 'Medicamento', 'Protocolo', 'Secagem', 'Desmame', 'Colostragem']

function urgencia(s) {
  if (s.executado) return 'ok'
  if (s.data <= hoje()) return 'critico'
  const diff = (new Date(s.data) - new Date()) / 86400000
  if (diff <= 7)  return 'critico'
  if (diff <= 14) return 'atencao'
  return 'info'
}

const URG_COR = {
  critico: 'text-red-400',
  atencao: 'text-amber-400',
  ok:      'text-emerald-400',
  info:    'text-slate-500',
}

export default function TabSanidade() {
  const [registros,   setRegistros]   = useState([])
  const [animais,     setAnimais]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [erro,        setErro]        = useState('')
  const [toast,       setToast]       = useState(null)
  const [modal,       setModal]       = useState(null) // 'individual' | 'lote'
  const [saving,      setSaving]      = useState(false)
  const [executando,  setExecutando]  = useState(null)
  const [filtro,      setFiltro]      = useState('pendentes') // 'todos' | 'pendentes' | 'executados'

  const [form, setForm] = useState({
    tipo: 'Vacina', animal: '', protocolo: '', data: hoje(),
    responsavel: '', dose: '', via: '', obs: '',
  })

  // Lote: animais selecionados (array de nomes)
  const [lote, setLote] = useState({
    tipo: 'Vacina', protocolo: '', data: hoje(),
    responsavel: '', dose: '', via: '', obs: '',
    animaisSel: [],
  })

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const [s, a] = await Promise.all([api.sanitario(90), api.animais()])
      setRegistros(s)
      setAnimais(a.filter(x => x.status !== 'Vendido'))
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  useEffect(() => {
    const onRefresh = () => carregar()
    window.addEventListener('milkshow:refresh', onRefresh)
    return () => window.removeEventListener('milkshow:refresh', onRefresh)
  }, [])

  async function executar(id) {
    setExecutando(id)
    try {
      await api.executarSanitario(id)
      setToast({ msg: 'Protocolo marcado como executado', tipo: 'ok' })
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setExecutando(null) }
  }

  async function salvar(e) {
    e.preventDefault()
    if (!form.animal || !form.protocolo) return
    setSaving(true)
    try {
      await api.registrarSanitario(form)
      setToast({ msg: `Protocolo registrado para ${form.animal}`, tipo: 'ok' })
      setModal(null)
      setForm(f => ({ ...f, animal: '', protocolo: '', dose: '', via: '', obs: '' }))
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function salvarLote(e) {
    e.preventDefault()
    if (!lote.protocolo || lote.animaisSel.length === 0) return
    setSaving(true)
    try {
      await api.registrarSanitarioLote(lote.animaisSel, {
        tipo: lote.tipo,
        protocolo: lote.protocolo,
        data: lote.data,
        responsavel: lote.responsavel,
        dose: lote.dose,
        via: lote.via,
        obs: lote.obs,
      })
      setToast({ msg: `Protocolo registrado para ${lote.animaisSel.length} animal(is)`, tipo: 'ok' })
      setModal(null)
      setLote(f => ({ ...f, animaisSel: [], protocolo: '', dose: '', via: '', obs: '' }))
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  function toggleAnimalLote(nome) {
    setLote(f => ({
      ...f,
      animaisSel: f.animaisSel.includes(nome)
        ? f.animaisSel.filter(n => n !== nome)
        : [...f.animaisSel, nome],
    }))
  }

  function selecionarTodos() {
    setLote(f => ({
      ...f,
      animaisSel: f.animaisSel.length === animais.length ? [] : animais.map(a => a.nome),
    }))
  }

  if (loading) return <Loading />

  const pendentes = registros.filter(r => !r.executado)
  const criticos  = pendentes.filter(r => urgencia(r) === 'critico')
  const atencao   = pendentes.filter(r => urgencia(r) === 'atencao')

  const filtrados = (() => {
    const base = [...registros].sort((a, b) => {
      if (!a.executado && b.executado) return -1
      if (a.executado && !b.executado) return 1
      return (a.data || '').localeCompare(b.data || '')
    })
    if (filtro === 'pendentes')  return base.filter(r => !r.executado)
    if (filtro === 'executados') return base.filter(r =>  r.executado)
    return base
  })()

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* KPIs */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: 'TOTAL',     value: registros.length, accent: '#64748b' },
          { label: 'PENDENTES', value: pendentes.length, accent: '#22c55e' },
          { label: 'CRÍTICOS',  value: criticos.length,  accent: '#ef4444' },
          { label: 'ATENÇÃO',   value: atencao.length,   accent: '#f59e0b' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4 pt-3 flex flex-col gap-1"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : '', borderTop: `2px solid ${k.accent}` }}>
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">{k.label}</p>
            <p className="text-2xl font-mono font-semibold tabular-nums" style={{ color: k.accent === '#64748b' ? T.text : k.accent }}>{k.value}</p>
          </div>
        ))}
      </div>

      <SectionHeader
        title="CALENDÁRIO SANITÁRIO"
        sub={`${pendentes.length} protocolos pendentes`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            {/* Filtro */}
            <div className="flex items-center gap-0.5 rounded p-0.5" style={{ background: T.surface, border: `1px solid ${T.border}` }}>
              {[['pendentes','Pendentes'],['todos','Todos'],['executados','Executados']].map(([v, l]) => (
                <button key={v} onClick={() => setFiltro(v)}
                  className="px-2 py-1 rounded text-[11px] font-medium transition-all"
                  style={{ background: filtro === v ? T.border : 'transparent', color: filtro === v ? T.brand2 : T.sub }}>
                  <span className="text-[11px] font-medium">{l}</span>
                </button>
              ))}
            </div>
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11} /></Btn>
            <Btn variant="ghost" size="xs" onClick={() => setModal('lote')}>
              <Users size={11} /> Lote
            </Btn>
            <Btn variant="primary" size="xs" onClick={() => setModal('individual')}>
              <Plus size={11} /> Protocolo
            </Btn>
          </div>
        }
      />

      <div className="overflow-auto flex-1">
        {filtrados.length === 0 ? (
          <Empty
            icon={ShieldCheck}
            title={filtro === 'pendentes' ? 'Sem protocolos pendentes' : 'Nenhum registro encontrado'}
            msg={filtro === 'pendentes' ? 'Todos os protocolos foram executados.' : 'Adicione o primeiro protocolo sanitário.'}
            accentColor="#f59e0b"
            action={<Btn variant="primary" size="sm" onClick={() => setModal('individual')}><Plus size={12} /> Novo protocolo</Btn>}
          />
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: T.s3, borderBottom: `1px solid ${T.border}` }}>
                {['DATA', 'TIPO', 'ANIMAL', 'PROTOCOLO', 'DOSE/VIA', 'RESPONSÁVEL', 'URGÊNCIA', 'AÇÃO'].map(h =>
                  <th key={h} className="text-left text-slate-500 px-4 py-2.5 font-medium text-[11px] tracking-wider uppercase">{h}</th>
                )}
              </tr>
            </thead>
            <tbody>
              {filtrados.map((s, i) => {
                const urg = urgencia(s)
                return (
                  <tr key={s.id || i} className="hover:bg-white/[0.02] transition-colors"
                      style={{ borderBottom: `1px solid ${T.border2}`, opacity: s.executado ? 0.5 : 1 }}>
                    <td className={`px-4 py-2.5 ${s.data <= hoje() && !s.executado ? 'text-red-400 font-semibold' : 'text-slate-500'}`}>
                      {s.data}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500">{s.tipo}</td>
                    <td className="px-4 py-2.5 text-slate-200 font-semibold">{s.animal}</td>
                    <td className="px-4 py-2.5 text-slate-400">{s.protocolo}</td>
                    <td className="px-4 py-2.5 text-slate-600">{[s.dose, s.via].filter(Boolean).join(' · ') || '—'}</td>
                    <td className="px-4 py-2.5 text-slate-600">{s.responsavel || '—'}</td>
                    <td className={`px-4 py-2.5 uppercase tracking-wider ${URG_COR[urg]}`}>{urg}</td>
                    <td className="px-4 py-2.5">
                      {s.executado
                        ? <span className="flex items-center gap-1 text-emerald-500 text-[10px]"><CheckCircle2 size={11} />Executado</span>
                        : <Btn variant="outline" size="xs"
                            disabled={executando === s.id}
                            onClick={() => executar(s.id)}>
                            {executando === s.id ? '...' : 'Executar'}
                          </Btn>
                      }
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal: individual */}
      <Modal open={modal === 'individual'} onClose={() => setModal(null)} title="REGISTRAR PROTOCOLO SANITÁRIO">
        <form onSubmit={salvar} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo">
              <Select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))}>
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Animal *">
              <Select value={form.animal} onChange={e => setForm(f => ({ ...f, animal: e.target.value }))}>
                <option value="">Selecione...</option>
                {animais.map(a => <option key={a.nome} value={a.nome}>{a.nome}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Protocolo / Vacina *">
            <Input value={form.protocolo} onChange={e => setForm(f => ({ ...f, protocolo: e.target.value }))} placeholder="Ex: Aftosa — Reforço Semestral" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Data"><Input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} /></Field>
            <Field label="Responsável"><Input value={form.responsavel} onChange={e => setForm(f => ({ ...f, responsavel: e.target.value }))} placeholder="Ex: Dr. Paulo" /></Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Dose"><Input value={form.dose} onChange={e => setForm(f => ({ ...f, dose: e.target.value }))} placeholder="Ex: 2mL" /></Field>
            <Field label="Via"><Input value={form.via} onChange={e => setForm(f => ({ ...f, via: e.target.value }))} placeholder="Ex: SC, IM" /></Field>
          </div>
          <Field label="Observações"><Textarea value={form.obs} onChange={e => setForm(f => ({ ...f, obs: e.target.value }))} /></Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving ? 'Salvando...' : 'Registrar'}</Btn>
          </div>
        </form>
      </Modal>

      {/* Modal: lote */}
      <Modal open={modal === 'lote'} onClose={() => setModal(null)} title="REGISTRAR EM LOTE" width={560}>
        <form onSubmit={salvarLote} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo">
              <Select value={lote.tipo} onChange={e => setLote(f => ({ ...f, tipo: e.target.value }))}>
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Data">
              <Input type="date" value={lote.data} onChange={e => setLote(f => ({ ...f, data: e.target.value }))} />
            </Field>
          </div>
          <Field label="Protocolo / Vacina *">
            <Input value={lote.protocolo} onChange={e => setLote(f => ({ ...f, protocolo: e.target.value }))} placeholder="Ex: Aftosa — Vacinação de Plantel" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Dose"><Input value={lote.dose} onChange={e => setLote(f => ({ ...f, dose: e.target.value }))} placeholder="Ex: 2mL" /></Field>
            <Field label="Via"><Input value={lote.via} onChange={e => setLote(f => ({ ...f, via: e.target.value }))} placeholder="Ex: SC, IM" /></Field>
          </div>
          <Field label="Responsável">
            <Input value={lote.responsavel} onChange={e => setLote(f => ({ ...f, responsavel: e.target.value }))} placeholder="Ex: Dr. Paulo" />
          </Field>

          {/* Seleção de animais */}
          <Field label={`Animais * — ${lote.animaisSel.length} selecionado(s)`}>
            <div className="rounded border overflow-hidden" style={{ borderColor: T.border, maxHeight: 200, overflowY: 'auto' }}>
              <button type="button" onClick={selecionarTodos}
                className="w-full px-3 py-2 text-[11px] font-medium text-left text-blue-400 hover:bg-white/[0.03] transition-colors"
                style={{ borderBottom: `1px solid ${T.border}` }}>
                {lote.animaisSel.length === animais.length ? 'Desmarcar todos' : 'Selecionar todos'}
              </button>
              {animais.map(a => (
                <label key={a.nome}
                  className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-white/[0.03] transition-colors"
                  style={{ borderBottom: `1px solid ${T.border2}` }}>
                  <input type="checkbox"
                    checked={lote.animaisSel.includes(a.nome)}
                    onChange={() => toggleAnimalLote(a.nome)}
                    className="accent-emerald-500 w-3.5 h-3.5" />
                  <span className="text-xs text-slate-300">{a.nome}</span>
                  <span className="text-[10px] text-slate-500 ml-auto">{a.status}</span>
                </label>
              ))}
            </div>
          </Field>

          <Field label="Observações">
            <Textarea value={lote.obs} onChange={e => setLote(f => ({ ...f, obs: e.target.value }))} />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving || lote.animaisSel.length === 0}>
              {saving ? 'Salvando...' : `Registrar para ${lote.animaisSel.length} animal(is)`}
            </Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
