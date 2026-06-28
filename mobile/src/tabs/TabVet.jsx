import { useEffect, useState } from 'react'
import { Plus, RefreshCw, ChevronDown, ChevronUp, Edit2, Check, X as XIcon, Search, Stethoscope } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, StatusBadge, Badge, Empty,
  T, hoje, fmtDate, dataParto,
} from '../ui.jsx'

const TIPOS       = ['Vacina', 'Exame', 'Medicamento', 'Protocolo']
const STATUS_LIST = ['Lactação', 'Seca', 'Gestação', 'Novilha', 'Bezerro', 'Vendido']

export default function TabVet() {
  const [animais,     setAnimais]     = useState([])
  const [sanitario,   setSanitario]   = useState([])
  const [loading,     setLoading]     = useState(true)
  const [erro,        setErro]        = useState('')
  const [toast,       setToast]       = useState(null)
  const [modal,       setModal]       = useState(null) // 'animal' | 'sanitario'
  const [saving,      setSaving]      = useState(false)
  const [expandido,   setExpandido]   = useState(null)
  const [filtroStatus, setFiltroStatus] = useState('todos')
  const [busca,       setBusca]       = useState('')
  const [editStatus,  setEditStatus]  = useState(null) // { nome, novoStatus }

  const [formA, setFormA] = useState({ nome: '', status: 'Lactação', raca: '', sexo: 'Fêmea', nascimento: '', ins: '', obs: '' })
  const [formS, setFormS] = useState({ tipo: 'Vacina', animal: '', protocolo: '', data: hoje(), responsavel: '', dose: '', via: '', obs: '' })

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

  useEffect(() => {
    const onRefresh = () => carregar()
    window.addEventListener('milkshow:refresh', onRefresh)
    return () => window.removeEventListener('milkshow:refresh', onRefresh)
  }, [])

  async function salvarAnimal(e) {
    e.preventDefault()
    if (!formA.nome.trim()) return
    setSaving(true)
    try {
      await api.adicionarAnimal(formA)
      setToast({ msg: `${formA.nome} cadastrado com sucesso`, tipo: 'ok' })
      setModal(null)
      setFormA({ nome: '', status: 'Lactação', raca: '', sexo: 'Fêmea', nascimento: '', ins: '', obs: '' })
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
      setFormS(f => ({ ...f, animal: '', protocolo: '', dose: '', via: '', obs: '' }))
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function confirmarStatus(a) {
    if (!editStatus || editStatus.novoStatus === a.status) { setEditStatus(null); return }
    try {
      await api.adicionarAnimal({ ...a, status: editStatus.novoStatus })
      setToast({ msg: `${a.nome} → ${editStatus.novoStatus}`, tipo: 'ok' })
      setEditStatus(null)
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
  }

  if (loading) return <Loading />

  const porAnimal = animais.reduce((acc, a) => {
    acc[a.nome] = sanitario.filter(s => s.animal === a.nome)
    return acc
  }, {})

  const animaisFiltrados = animais.filter(a => {
    const statusOk = filtroStatus === 'todos' || a.status === filtroStatus
    const buscaOk  = !busca || a.nome.toLowerCase().includes(busca.toLowerCase())
    return statusOk && buscaOk
  })

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* KPIs */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: 'TOTAL ANIMAIS',   value: animais.length,                                      accent: '#64748b' },
          { label: 'EM LACTAÇÃO',     value: animais.filter(a => a.status === 'Lactação').length,  accent: '#16a34a' },
          { label: 'EM GESTAÇÃO',     value: animais.filter(a => a.status === 'Gestação').length,  accent: '#22c55e' },
          { label: 'HIST. SANITÁRIO', value: sanitario.length,                                     accent: '#f59e0b' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4 pt-3 flex flex-col gap-1"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : '', borderTop: `2px solid ${k.accent}` }}>
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">{k.label}</p>
            <p className="text-2xl font-mono font-semibold tabular-nums" style={{ color: k.accent === '#64748b' ? '#f1f5f9' : k.accent }}>{k.value}</p>
          </div>
        ))}
      </div>

      <SectionHeader
        title="PRONTUÁRIO INDIVIDUAL"
        sub={`${animaisFiltrados.length} de ${animais.length} animais`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11} /></Btn>
            <Btn variant="ghost" size="xs" onClick={() => setModal('sanitario')}><Plus size={11} />Protocolo</Btn>
            <Btn variant="primary" size="xs" onClick={() => setModal('animal')}><Plus size={11} />Animal</Btn>
          </div>
        }
      />

      {/* Filtros */}
      <div className="flex items-center gap-3 px-4 py-3 shrink-0 overflow-x-auto bg-white"
           style={{ borderBottom: '1px solid #e8ede8' }}>
        <div className="relative shrink-0">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#8aaa85' }} />
          <input
            type="text"
            placeholder="Buscar animal..."
            value={busca}
            onChange={e => setBusca(e.target.value)}
            className="text-[13px] rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200"
            style={{
              paddingLeft: 32, paddingRight: 12, paddingTop: 7, paddingBottom: 7,
              background: '#f8faf8', border: '1px solid #d4e6d4',
              color: '#1a2e1a', width: 200,
            }}
          />
        </div>
        <div className="flex items-center gap-0.5 rounded-lg p-0.5" style={{ background: '#f8faf8', border: '1px solid #d4e6d4' }}>
          {[['todos', 'Todos'], ...STATUS_LIST.filter(s => s !== 'Vendido').map(s => [s, s])].map(([v, l]) => (
            <button key={v} onClick={() => setFiltroStatus(v)}
              className="px-2.5 py-1.5 rounded-md text-[11px] font-medium transition-all whitespace-nowrap"
              style={{ background: filtroStatus === v ? T.s3 : 'transparent', border: filtroStatus === v ? `1px solid ${T.border}` : '1px solid transparent', color: filtroStatus === v ? '#e2e8f0' : T.muted }}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Lista expansível */}
      <div className="overflow-auto flex-1">
        {animaisFiltrados.length === 0 && (
          animais.length === 0 ? (
            <Empty
              icon={Stethoscope}
              title="Sem animais cadastrados"
              msg="Cadastre animais para registrar prontuários veterinários."
              accentColor="#22c55e"
              action={<Btn variant="primary" size="sm" onClick={() => setModal('animal')}><Plus size={12} /> Cadastrar animal</Btn>}
            />
          ) : (
            <Empty
              icon={Search}
              title="Nenhum animal encontrado"
              msg="Tente ajustar o filtro ou a busca."
              action={<Btn variant="ghost" size="sm" onClick={() => { setBusca(''); setFiltroStatus('todos') }}>Limpar filtros</Btn>}
            />
          )
        )}
        {animaisFiltrados.map(a => {
          const hist   = porAnimal[a.nome] || []
          const aberto = expandido === a.nome
          const ins    = a.ins || a.inseminacao || ''
          const editando = editStatus?.nome === a.nome

          return (
            <div key={a.id || a.nome} style={{ borderBottom: `1px solid ${T.border}` }}>
              <button
                className="w-full flex items-center gap-4 px-4 py-3 hover:bg-white/[0.02] transition-colors text-left"
                onClick={() => { setExpandido(aberto ? null : a.nome); setEditStatus(null) }}
              >
                <div className="flex-1 grid grid-cols-5 gap-4 text-xs items-center">
                  <span className="text-slate-200 font-semibold">{a.nome}</span>
                  <span className="text-slate-500">{a.raca || '—'}</span>

                  {/* Status — clique para editar inline */}
                  <div onClick={e => e.stopPropagation()}>
                    {editando ? (
                      <div className="flex items-center gap-1">
                        <select
                          value={editStatus.novoStatus}
                          onChange={e => setEditStatus(es => ({ ...es, novoStatus: e.target.value }))}
                          onClick={e => e.stopPropagation()}
                          className="text-[11px] bg-transparent border rounded px-1 py-0.5 text-slate-300 focus:outline-none"
                          style={{ borderColor: T.border, background: T.surface }}>
                          {STATUS_LIST.map(s => <option key={s}>{s}</option>)}
                        </select>
                        <button onClick={() => confirmarStatus(a)} className="text-emerald-400 hover:text-emerald-300 p-0.5"><Check size={12} /></button>
                        <button onClick={() => setEditStatus(null)} className="text-slate-600 hover:text-slate-400 p-0.5"><XIcon size={12} /></button>
                      </div>
                    ) : (
                      <button
                        className="flex items-center gap-1 group"
                        onClick={e => { e.stopPropagation(); setEditStatus({ nome: a.nome, novoStatus: a.status }) }}>
                        <StatusBadge status={a.status} />
                        <Edit2 size={10} className="text-slate-700 group-hover:text-slate-500 transition-colors" />
                      </button>
                    )}
                  </div>

                  <span className="text-slate-500">{ins ? `IA: ${fmtDate(ins)}` : '—'}</span>
                  <span className="text-slate-500">{ins ? `Parto: ${dataParto(ins)}` : '—'}</span>
                </div>
                <Badge label={`${hist.length} proc.`} nivel="info" />
                {aberto ? <ChevronUp size={13} className="text-slate-600 shrink-0" /> : <ChevronDown size={13} className="text-slate-600 shrink-0" />}
              </button>

              {/* Histórico sanitário expandido */}
              {aberto && (
                <div style={{ background: T.s2, borderTop: `1px solid ${T.border2}` }}>
                  {hist.length === 0 ? (
                    <div className="px-8 py-4">
                      <p className="text-slate-600 text-xs mb-2">Nenhum registro sanitário.</p>
                      <Btn variant="ghost" size="xs"
                        onClick={() => { setFormS(f => ({ ...f, animal: a.nome })); setModal('sanitario') }}>
                        <Plus size={10} /> Adicionar protocolo
                      </Btn>
                    </div>
                  ) : (
                    <>
                      <table className="w-full text-xs">
                        <thead>
                          <tr style={{ borderBottom: `1px solid ${T.border}`, background: T.s3 }}>
                            {['DATA', 'TIPO', 'PROTOCOLO', 'DOSE/VIA', 'RESPONSÁVEL', 'STATUS'].map(h =>
                              <th key={h} className="text-left px-6 py-2.5 font-medium text-[11px] uppercase tracking-wider"
                                  style={{ color: T.muted }}>{h}</th>
                            )}
                          </tr>
                        </thead>
                        <tbody>
                          {hist.map((s, i) => (
                            <tr key={i} style={{ borderBottom: `1px solid ${T.border2}` }}>
                              <td className="px-6 py-2 text-slate-500">{s.data}</td>
                              <td className="px-6 py-2 text-slate-400">{s.tipo}</td>
                              <td className="px-6 py-2 text-slate-200">{s.protocolo}</td>
                              <td className="px-6 py-2 text-slate-500">{[s.dose, s.via].filter(Boolean).join(' · ') || '—'}</td>
                              <td className="px-6 py-2 text-slate-500">{s.responsavel || '—'}</td>
                              <td className="px-6 py-2">
                                <Badge label={s.executado ? 'EXECUTADO' : 'PENDENTE'} nivel={s.executado ? 'ok' : 'atencao'} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="px-6 py-2">
                        <Btn variant="ghost" size="xs"
                          onClick={() => { setFormS(f => ({ ...f, animal: a.nome })); setModal('sanitario') }}>
                          <Plus size={10} /> Adicionar protocolo
                        </Btn>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Modal: novo animal */}
      <Modal open={modal === 'animal'} onClose={() => setModal(null)} title="CADASTRAR ANIMAL">
        <form onSubmit={salvarAnimal} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nome *"><Input value={formA.nome} onChange={e => setFormA(f => ({ ...f, nome: e.target.value }))} placeholder="Ex: Joana" /></Field>
            <Field label="Status">
              <Select value={formA.status} onChange={e => setFormA(f => ({ ...f, status: e.target.value }))}>
                {STATUS_LIST.map(s => <option key={s}>{s}</option>)}
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Raça"><Input value={formA.raca} onChange={e => setFormA(f => ({ ...f, raca: e.target.value }))} placeholder="Ex: Holandesa" /></Field>
            <Field label="Sexo">
              <Select value={formA.sexo} onChange={e => setFormA(f => ({ ...f, sexo: e.target.value }))}>
                <option>Fêmea</option><option>Macho</option>
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nascimento"><Input type="date" value={formA.nascimento} onChange={e => setFormA(f => ({ ...f, nascimento: e.target.value }))} /></Field>
            <Field label="Última inseminação"><Input type="date" value={formA.ins} onChange={e => setFormA(f => ({ ...f, ins: e.target.value }))} /></Field>
          </div>
          <Field label="Observações"><Textarea value={formA.obs} onChange={e => setFormA(f => ({ ...f, obs: e.target.value }))} placeholder="Histórico, procedência..." /></Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving ? 'Salvando...' : 'Cadastrar animal'}</Btn>
          </div>
        </form>
      </Modal>

      {/* Modal: protocolo sanitário */}
      <Modal open={modal === 'sanitario'} onClose={() => setModal(null)} title="REGISTRAR PROTOCOLO SANITÁRIO">
        <form onSubmit={salvarSanitario} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tipo">
              <Select value={formS.tipo} onChange={e => setFormS(f => ({ ...f, tipo: e.target.value }))}>
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Animal *">
              <Select value={formS.animal} onChange={e => setFormS(f => ({ ...f, animal: e.target.value }))}>
                <option value="">Selecione...</option>
                {animais.map(a => <option key={a.nome} value={a.nome}>{a.nome}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Protocolo / Vacina *">
            <Input value={formS.protocolo} onChange={e => setFormS(f => ({ ...f, protocolo: e.target.value }))} placeholder="Ex: Aftosa — Reforço Semestral" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Data"><Input type="date" value={formS.data} onChange={e => setFormS(f => ({ ...f, data: e.target.value }))} /></Field>
            <Field label="Responsável"><Input value={formS.responsavel} onChange={e => setFormS(f => ({ ...f, responsavel: e.target.value }))} placeholder="Ex: Dr. Paulo" /></Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Dose"><Input value={formS.dose} onChange={e => setFormS(f => ({ ...f, dose: e.target.value }))} placeholder="Ex: 2mL" /></Field>
            <Field label="Via"><Input value={formS.via} onChange={e => setFormS(f => ({ ...f, via: e.target.value }))} placeholder="Ex: SC, IM" /></Field>
          </div>
          <Field label="Observações"><Textarea value={formS.obs} onChange={e => setFormS(f => ({ ...f, obs: e.target.value }))} /></Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving ? 'Salvando...' : 'Registrar protocolo'}</Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
