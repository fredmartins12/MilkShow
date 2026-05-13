import { useEffect, useState } from 'react'
import { Plus, RefreshCw, CheckCircle2 } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, Badge, T, hoje,
} from '../ui.jsx'

const TIPOS = ['Vacina','Exame','Medicamento','Protocolo','Secagem','Desmame']

function urgencia(s) {
  if (!s.executado) {
    if (s.data <= hoje()) return 'critico'
    const diff = (new Date(s.data) - new Date()) / 86400000
    if (diff <= 7)  return 'critico'
    if (diff <= 14) return 'atencao'
  }
  return s.executado ? 'ok' : 'info'
}

export default function TabSanidade() {
  const [registros, setRegistros] = useState([])
  const [animais, setAnimais]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [erro, setErro]           = useState('')
  const [toast, setToast]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [saving, setSaving]       = useState(false)
  const [executando, setExecutando] = useState(null)
  const [form, setForm]           = useState({
    tipo: 'Vacina', animal: '', protocolo: '', data: hoje(),
    responsavel: '', dose: '', via: '', obs: '',
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
      setModal(false)
      setForm(f => ({ ...f, animal:'', protocolo:'', dose:'', via:'', obs:'' }))
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  const pendentes  = registros.filter(r => !r.executado)
  const criticos   = pendentes.filter(r => urgencia(r) === 'critico')
  const atencao    = pendentes.filter(r => urgencia(r) === 'atencao')

  const ordenados = [...registros].sort((a, b) => {
    if (!a.executado && b.executado) return -1
    if (a.executado && !b.executado) return 1
    return (a.data || '').localeCompare(b.data || '')
  })

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* Contadores */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom:`1px solid ${T.border}` }}>
        {[
          { label:'TOTAL',     value: registros.length,  color:'text-slate-100' },
          { label:'PENDENTES', value: pendentes.length,  color:'text-slate-100' },
          { label:'CRÍTICOS',  value: criticos.length,   color:'text-red-400'   },
          { label:'ATENÇÃO',   value: atencao.length,    color:'text-amber-400' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4" style={{ borderRight: i<arr.length-1 ? `1px solid ${T.border}`:'' }}>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-2">{k.label}</p>
            <p className={`text-2xl font-mono font-semibold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <SectionHeader
        title="CALENDÁRIO SANITÁRIO"
        sub={`${pendentes.length} protocolos pendentes`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11}/></Btn>
            <Btn variant="primary" size="xs" onClick={() => setModal(true)}><Plus size={11}/>Protocolo</Btn>
          </div>
        }
      />

      <div className="overflow-auto flex-1">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr style={{ borderBottom:`1px solid ${T.border}` }}>
              {['DATA','TIPO','ANIMAL','PROTOCOLO','DOSE/VIA','RESPONSÁVEL','URGÊNCIA','AÇÃO'].map(h =>
                <th key={h} className="text-left text-slate-700 px-4 py-2 font-normal tracking-wider text-[10px]">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {ordenados.map((s, i) => {
              const urg = urgencia(s)
              const urgColor = {
                critico: 'text-red-400',
                atencao: 'text-amber-400',
                ok:      'text-emerald-400',
                info:    'text-slate-500',
              }[urg]
              return (
                <tr key={s.id||i} className="hover:bg-white/[0.02] transition-colors"
                    style={{ borderBottom:`1px solid ${T.border2}`, opacity: s.executado ? 0.5 : 1 }}>
                  <td className={`px-4 py-2.5 ${s.data <= hoje() && !s.executado ? 'text-red-400 font-semibold' : 'text-slate-500'}`}>
                    {s.data}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500">{s.tipo}</td>
                  <td className="px-4 py-2.5 text-slate-200 font-semibold">{s.animal}</td>
                  <td className="px-4 py-2.5 text-slate-400">{s.protocolo}</td>
                  <td className="px-4 py-2.5 text-slate-600">{[s.dose,s.via].filter(Boolean).join(' · ')||'—'}</td>
                  <td className="px-4 py-2.5 text-slate-600">{s.responsavel||'—'}</td>
                  <td className={`px-4 py-2.5 uppercase tracking-wider ${urgColor}`}>{urg}</td>
                  <td className="px-4 py-2.5">
                    {s.executado
                      ? <span className="flex items-center gap-1 text-emerald-500 text-[10px]"><CheckCircle2 size={11}/>Executado</span>
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
      </div>

      <Modal open={modal} onClose={() => setModal(false)} title="REGISTRAR PROTOCOLO SANITÁRIO">
        <form onSubmit={salvar} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo">
              <Select value={form.tipo} onChange={e=>setForm(f=>({...f,tipo:e.target.value}))}>
                {TIPOS.map(t=><option key={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Animal *">
              <Select value={form.animal} onChange={e=>setForm(f=>({...f,animal:e.target.value}))}>
                <option value="">Selecione...</option>
                {animais.map(a=><option key={a.nome} value={a.nome}>{a.nome}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Protocolo / Vacina *">
            <Input value={form.protocolo} onChange={e=>setForm(f=>({...f,protocolo:e.target.value}))} placeholder="Ex: Aftosa — Reforço Semestral"/>
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Data"><Input type="date" value={form.data} onChange={e=>setForm(f=>({...f,data:e.target.value}))}/></Field>
            <Field label="Responsável"><Input value={form.responsavel} onChange={e=>setForm(f=>({...f,responsavel:e.target.value}))} placeholder="Ex: Dr. Paulo"/></Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Dose"><Input value={form.dose} onChange={e=>setForm(f=>({...f,dose:e.target.value}))} placeholder="Ex: 2mL"/></Field>
            <Field label="Via"><Input value={form.via} onChange={e=>setForm(f=>({...f,via:e.target.value}))} placeholder="Ex: SC, IM"/></Field>
          </div>
          <Field label="Observações"><Textarea value={form.obs} onChange={e=>setForm(f=>({...f,obs:e.target.value}))}/></Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(false)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving?'Salvando...':'Registrar'}</Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
