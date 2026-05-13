import { useEffect, useState } from 'react'
import { Plus, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, StatusBadge, Badge,
  T, hoje, fmtDate, dataParto,
} from '../ui.jsx'

const TIPOS = ['Vacina','Exame','Medicamento','Protocolo']
const STATUS_LIST = ['Lactação','Seca','Gestação','Novilha','Bezerro']

export default function TabVet() {
  const [animais, setAnimais]     = useState([])
  const [sanitario, setSanitario] = useState([])
  const [loading, setLoading]     = useState(true)
  const [erro, setErro]           = useState('')
  const [toast, setToast]         = useState(null)
  const [modal, setModal]         = useState(null) // 'animal' | 'sanitario'
  const [saving, setSaving]       = useState(false)
  const [expandido, setExpandido] = useState(null)

  const [formA, setFormA] = useState({ nome:'', status:'Lactação', raca:'', sexo:'Fêmea', nascimento:'', ins:'', obs:'' })
  const [formS, setFormS] = useState({ tipo:'Vacina', animal:'', protocolo:'', data:hoje(), responsavel:'', dose:'', via:'', obs:'' })

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const [a, s] = await Promise.all([api.animais(), api.sanitario(90)])
      setAnimais(a.filter(x => x.status !== 'Vendido'))
      setSanitario(s)
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  async function salvarAnimal(e) {
    e.preventDefault()
    if (!formA.nome.trim()) return
    setSaving(true)
    try {
      await api.adicionarAnimal(formA)
      setToast({ msg: `${formA.nome} cadastrado com sucesso`, tipo: 'ok' })
      setModal(null)
      setFormA({ nome:'', status:'Lactação', raca:'', sexo:'Fêmea', nascimento:'', ins:'', obs:'' })
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function salvarSanitario(e) {
    e.preventDefault()
    if (!formS.animal || !formS.protocolo) return
    setSaving(true)
    try {
      await api.registrarSanitario(formS)
      setToast({ msg: `Protocolo registrado para ${formS.animal}`, tipo: 'ok' })
      setModal(null)
      setFormS(f => ({ ...f, animal:'', protocolo:'', dose:'', via:'', obs:'' }))
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  const porAnimal = animais.reduce((acc, a) => {
    acc[a.nome] = sanitario.filter(s => s.animal === a.nome)
    return acc
  }, {})

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* Contadores */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom:`1px solid ${T.border}` }}>
        {[
          { label:'TOTAL ANIMAIS',  value: animais.length },
          { label:'EM LACTAÇÃO',    value: animais.filter(a=>a.status==='Lactação').length },
          { label:'EM GESTAÇÃO',    value: animais.filter(a=>a.status==='Gestação').length },
          { label:'HIST. SANITÁRIO',value: sanitario.length },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4" style={{ borderRight: i<arr.length-1 ? `1px solid ${T.border}`:'' }}>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-2">{k.label}</p>
            <p className="text-2xl font-mono font-semibold text-slate-100">{k.value}</p>
          </div>
        ))}
      </div>

      <SectionHeader
        title="PRONTUÁRIO INDIVIDUAL"
        sub={`${animais.length} animais ativos`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11}/></Btn>
            <Btn variant="ghost" size="xs" onClick={() => setModal('sanitario')}><Plus size={11}/>Protocolo</Btn>
            <Btn variant="primary" size="xs" onClick={() => setModal('animal')}><Plus size={11}/>Animal</Btn>
          </div>
        }
      />

      {/* Lista expansível por animal */}
      <div className="overflow-auto flex-1">
        {animais.map(a => {
          const hist   = porAnimal[a.nome] || []
          const aberto = expandido === a.nome
          const ins    = a.ins || a.inseminacao || ''
          return (
            <div key={a.id||a.nome} style={{ borderBottom:`1px solid ${T.border}` }}>
              {/* Linha do animal */}
              <button
                className="w-full flex items-center gap-4 px-4 py-3 hover:bg-white/[0.02] transition-colors text-left"
                onClick={() => setExpandido(aberto ? null : a.nome)}
              >
                <div className="flex-1 grid grid-cols-5 gap-4 text-xs font-mono">
                  <span className="text-slate-200 font-semibold">{a.nome}</span>
                  <span className="text-slate-500">{a.raca||'—'}</span>
                  <StatusBadge status={a.status} />
                  <span className="text-slate-500">{ins ? `IA: ${fmtDate(ins)}` : '—'}</span>
                  <span className="text-slate-500">{ins ? `Parto: ${dataParto(ins)}` : '—'}</span>
                </div>
                <Badge label={`${hist.length} proc.`} nivel="info" />
                {aberto ? <ChevronUp size={13} className="text-slate-600 shrink-0"/> : <ChevronDown size={13} className="text-slate-600 shrink-0"/>}
              </button>

              {/* Histórico sanitário expandido */}
              {aberto && (
                <div style={{ background: T.s2, borderTop:`1px solid ${T.border2}` }}>
                  {hist.length === 0 ? (
                    <p className="px-8 py-3 text-slate-700 text-xs font-mono">Nenhum registro sanitário.</p>
                  ) : (
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr style={{ borderBottom:`1px solid ${T.border}` }}>
                          {['DATA','TIPO','PROTOCOLO','DOSE/VIA','RESPONSÁVEL','STATUS'].map(h =>
                            <th key={h} className="text-left text-slate-700 px-6 py-1.5 font-normal tracking-wider text-[10px]">{h}</th>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {hist.map((s, i) => (
                          <tr key={i} style={{ borderBottom:`1px solid ${T.border2}` }}>
                            <td className="px-6 py-2 text-slate-500">{s.data}</td>
                            <td className="px-6 py-2 text-slate-400">{s.tipo}</td>
                            <td className="px-6 py-2 text-slate-200">{s.protocolo}</td>
                            <td className="px-6 py-2 text-slate-500">{[s.dose, s.via].filter(Boolean).join(' · ')||'—'}</td>
                            <td className="px-6 py-2 text-slate-500">{s.responsavel||'—'}</td>
                            <td className="px-6 py-2">
                              <Badge label={s.executado ? 'EXECUTADO' : 'PENDENTE'} nivel={s.executado ? 'ok' : 'atencao'} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Modal: novo animal */}
      <Modal open={modal==='animal'} onClose={() => setModal(null)} title="CADASTRAR ANIMAL">
        <form onSubmit={salvarAnimal} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nome *"><Input value={formA.nome} onChange={e=>setFormA(f=>({...f,nome:e.target.value}))} placeholder="Ex: Joana"/></Field>
            <Field label="Status">
              <Select value={formA.status} onChange={e=>setFormA(f=>({...f,status:e.target.value}))}>
                {STATUS_LIST.map(s=><option key={s}>{s}</option>)}
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Raça"><Input value={formA.raca} onChange={e=>setFormA(f=>({...f,raca:e.target.value}))} placeholder="Ex: Holandesa"/></Field>
            <Field label="Sexo">
              <Select value={formA.sexo} onChange={e=>setFormA(f=>({...f,sexo:e.target.value}))}>
                {['Fêmea','Macho'].map(s=><option key={s}>{s}</option>)}
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nascimento"><Input type="date" value={formA.nascimento} onChange={e=>setFormA(f=>({...f,nascimento:e.target.value}))}/></Field>
            <Field label="Última inseminação"><Input type="date" value={formA.ins} onChange={e=>setFormA(f=>({...f,ins:e.target.value}))}/></Field>
          </div>
          <Field label="Observações"><Textarea value={formA.obs} onChange={e=>setFormA(f=>({...f,obs:e.target.value}))} placeholder="Histórico, procedência..."/></Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving?'Salvando...':'Cadastrar animal'}</Btn>
          </div>
        </form>
      </Modal>

      {/* Modal: protocolo sanitário */}
      <Modal open={modal==='sanitario'} onClose={() => setModal(null)} title="REGISTRAR PROTOCOLO SANITÁRIO">
        <form onSubmit={salvarSanitario} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo">
              <Select value={formS.tipo} onChange={e=>setFormS(f=>({...f,tipo:e.target.value}))}>
                {TIPOS.map(t=><option key={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Animal *">
              <Select value={formS.animal} onChange={e=>setFormS(f=>({...f,animal:e.target.value}))}>
                <option value="">Selecione...</option>
                {animais.map(a=><option key={a.nome} value={a.nome}>{a.nome}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Protocolo / Vacina *">
            <Input value={formS.protocolo} onChange={e=>setFormS(f=>({...f,protocolo:e.target.value}))} placeholder="Ex: Aftosa — Reforço Semestral"/>
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Data"><Input type="date" value={formS.data} onChange={e=>setFormS(f=>({...f,data:e.target.value}))}/></Field>
            <Field label="Responsável"><Input value={formS.responsavel} onChange={e=>setFormS(f=>({...f,responsavel:e.target.value}))} placeholder="Ex: Dr. Paulo"/></Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Dose"><Input value={formS.dose} onChange={e=>setFormS(f=>({...f,dose:e.target.value}))} placeholder="Ex: 2mL"/></Field>
            <Field label="Via"><Input value={formS.via} onChange={e=>setFormS(f=>({...f,via:e.target.value}))} placeholder="Ex: SC, IM"/></Field>
          </div>
          <Field label="Observações"><Textarea value={formS.obs} onChange={e=>setFormS(f=>({...f,obs:e.target.value}))}/></Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving?'Salvando...':'Registrar protocolo'}</Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
