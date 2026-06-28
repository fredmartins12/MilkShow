import { useEffect, useState } from 'react'
import { RefreshCw, AlertTriangle, Milk, Plus, Droplets, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Textarea, Btn, Badge, Empty, T, idadeDias, fmtDate, hoje,
} from '../ui.jsx'

const STATUS_LIST = ['Bezerro', 'Novilha', 'Lactação', 'Gestação', 'Seca']

function nivelDesmame(dias) {
  if (dias === null || dias === undefined) return 'info'
  if (dias > 90)  return 'critico'
  if (dias >= 75) return 'atencao'
  return 'ok'
}

// Colostragem recomendada: 10% do peso vivo nas primeiras 6h, mín 4L
function statusColostragem(registros = []) {
  if (!registros.length) return { label: 'SEM REGISTRO', nivel: 'critico' }
  const total = registros.reduce((s, r) => s + (r.litros || 0), 0)
  if (total >= 4) return { label: `${total.toFixed(1)}L ✓`, nivel: 'ok' }
  return { label: `${total.toFixed(1)}L`, nivel: 'atencao' }
}

export default function TabBercario() {
  const [animais,      setAnimais]      = useState([])
  const [sanitario,    setSanitario]    = useState([])
  const [loading,      setLoading]      = useState(true)
  const [erro,         setErro]         = useState('')
  const [toast,        setToast]        = useState(null)
  const [expandido,    setExpandido]    = useState(null)
  const [modal,        setModal]        = useState(null) // 'bezerro' | 'colostragem'
  const [animalSel,    setAnimalSel]    = useState(null) // para modal colostragem
  const [saving,       setSaving]       = useState(false)

  const [formB, setFormB] = useState({
    nome: '', status: 'Bezerro', sexo: 'Fêmea', nascimento: hoje(),
    mae: '', raca: '', obs: '',
  })
  const [formC, setFormC] = useState({ data: hoje(), litros: '', turno: 'manhã', obs: '' })

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const [a, s] = await Promise.all([api.animais(), api.sanitario(180)])
      setAnimais(a.filter(x => x.status === 'Bezerro' || x.status === 'Novilha'))
      setSanitario(s.filter(x => x.tipo === 'Colostragem'))
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  useEffect(() => {
    const onRefresh = () => carregar()
    window.addEventListener('milkshow:refresh', onRefresh)
    return () => window.removeEventListener('milkshow:refresh', onRefresh)
  }, [])

  async function salvarBezerro(e) {
    e.preventDefault()
    if (!formB.nome.trim()) return
    setSaving(true)
    try {
      await api.adicionarAnimal(formB)
      setToast({ msg: `${formB.nome} cadastrado no berçário`, tipo: 'ok' })
      setModal(null)
      setFormB({ nome: '', status: 'Bezerro', sexo: 'Fêmea', nascimento: hoje(), mae: '', raca: '', obs: '' })
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function salvarColostragem(e) {
    e.preventDefault()
    if (!formC.litros || !animalSel) return
    setSaving(true)
    try {
      await api.registrarSanitario({
        tipo: 'Colostragem',
        animal: animalSel.nome,
        protocolo: `Colostragem ${formC.turno} — ${formC.litros}L`,
        data: formC.data,
        dose: `${formC.litros}L`,
        via: formC.turno,
        obs: formC.obs,
        executado: true,
        litros: parseFloat(formC.litros),
      })
      setToast({ msg: `Colostragem de ${formC.litros}L registrada para ${animalSel.nome}`, tipo: 'ok' })
      setModal(null)
      setFormC({ data: hoje(), litros: '', turno: 'manhã', obs: '' })
      carregar()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  function abrirColostragem(animal) {
    setAnimalSel(animal)
    setFormC({ data: animal.nascimento || hoje(), litros: '', turno: 'manhã', obs: '' })
    setModal('colostragem')
  }

  if (loading) return <Loading />

  const bezerros = animais.filter(a => a.status === 'Bezerro')
  const novilhas = animais.filter(a => a.status === 'Novilha')
  const criticos = bezerros.filter(a => idadeDias(a.nascimento) > 90)
  const atencao  = bezerros.filter(a => { const d = idadeDias(a.nascimento); return d !== null && d >= 75 && d <= 90 })

  // Agrupa colostragens por animal
  const colPorAnimal = sanitario.reduce((acc, s) => {
    acc[s.animal] = acc[s.animal] || []
    acc[s.animal].push(s)
    return acc
  }, {})

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* KPIs */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: 'BEZERROS',        value: bezerros.length, accent: '#fb923c' },
          { label: 'NOVILHAS',        value: novilhas.length, accent: '#a78bfa' },
          { label: 'DESMAME VENCIDO', value: criticos.length, accent: '#ef4444' },
          { label: 'PRÓX. DESMAME',   value: atencao.length,  accent: '#f59e0b' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4 pt-3 flex flex-col gap-1"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : '', borderTop: `2px solid ${k.accent}` }}>
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">{k.label}</p>
            <p className="text-2xl font-mono font-semibold tabular-nums" style={{ color: k.accent }}>{k.value}</p>
          </div>
        ))}
      </div>

      <SectionHeader
        title="GESTÃO DE BEZERROS"
        sub={`${animais.length} animais jovens`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11} /></Btn>
            <Btn variant="primary" size="xs" onClick={() => setModal('bezerro')}>
              <Plus size={11} /> Cadastrar
            </Btn>
          </div>
        }
      />

      {/* Alerta desmame */}
      {criticos.length > 0 && (
        <div className="mx-5 mt-4 p-3 rounded flex items-start gap-3"
             style={{ background: '#ef444410', border: '1px solid #ef444430' }}>
          <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 text-xs font-semibold mb-1">DESMAME VENCIDO</p>
            <p className="text-red-400/70 text-xs">
              {criticos.map(a => `${a.nome} (${idadeDias(a.nascimento)}d)`).join(' · ')}
            </p>
          </div>
        </div>
      )}

      <div className="overflow-auto flex-1 mt-4">
        {/* ── Bezerros ── */}
        <div className="flex items-center gap-2.5 px-5 py-2.5"
             style={{ background: T.s2, borderBottom: `1px solid ${T.border}` }}>
          <div className="w-1 h-3.5 rounded-full" style={{ background: '#fb923c' }} />
          <Milk size={12} style={{ color: '#fb923c' }} />
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#fb923c' }}>
            Bezerros
          </span>
          <span className="text-[11px] font-mono tabular-nums" style={{ color: T.muted }}>
            {bezerros.length}
          </span>
        </div>

        {bezerros.length === 0 ? (
          <Empty
            icon={Milk}
            title="Nenhum bezerro cadastrado"
            msg="Cadastre o primeiro bezerro para acompanhar o desmame e a colostragem."
            accentColor="#fb923c"
            action={<Btn variant="primary" size="sm" onClick={() => setModal('bezerro')}><Plus size={12} /> Cadastrar</Btn>}
          />
        ) : (
          <div className="mb-6">
            {bezerros.map((a) => {
              const dias    = idadeDias(a.nascimento)
              const nivel   = nivelDesmame(dias)
              const cor     = { critico: 'text-red-400', atencao: 'text-amber-400', ok: 'text-emerald-400', info: 'text-slate-500' }[nivel]
              const cols    = colPorAnimal[a.nome] || []
              const colSt   = statusColostragem(cols)
              const aberto  = expandido === a.nome

              return (
                <div key={a.id || a.nome} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <button
                    className="w-full flex items-center gap-3 px-5 py-3 hover:bg-white/[0.02] text-left transition-colors"
                    onClick={() => setExpandido(aberto ? null : a.nome)}
                  >
                    <div className="flex-1 grid grid-cols-6 gap-3 text-xs items-center">
                      <span className="text-slate-200 font-semibold">{a.nome}</span>
                      <span className="text-slate-500">{a.mae ? `Mãe: ${a.mae}` : '—'}</span>
                      <span className="text-slate-500">{a.sexo || '—'}</span>
                      <span className="text-slate-500">{fmtDate(a.nascimento)}</span>
                      <span className={`font-semibold ${cor}`}>{dias !== null ? `${dias}d` : '—'}</span>
                      <span>
                        {nivel === 'critico' && <Badge label="DESMAME VENCIDO" nivel="critico" />}
                        {nivel === 'atencao' && <Badge label="PRÓX. DESMAME"   nivel="atencao" />}
                        {nivel === 'ok'      && <Badge label="EM DIA"          nivel="ok"      />}
                      </span>
                    </div>
                    {/* Colostragem status */}
                    <div className="flex items-center gap-2 shrink-0">
                      <Droplets size={12} className="text-slate-600" />
                      <Badge label={colSt.label} nivel={colSt.nivel} />
                      <button
                        onClick={ev => { ev.stopPropagation(); abrirColostragem(a) }}
                        className="text-blue-400 hover:text-blue-300 text-[10px] font-medium border border-blue-500/30 rounded px-1.5 py-0.5 transition-colors">
                        + Col.
                      </button>
                    </div>
                    {aberto ? <ChevronUp size={13} className="text-slate-600 shrink-0" /> : <ChevronDown size={13} className="text-slate-600 shrink-0" />}
                  </button>

                  {/* Histórico colostragem expandido */}
                  {aberto && (
                    <div style={{ background: T.s2, borderTop: `1px solid ${T.border2}` }} className="px-8 py-3">
                      {cols.length === 0 ? (
                        <p className="text-slate-600 text-xs">Nenhuma colostragem registrada. Recomendado: ≥ 4L nas primeiras 6 horas de vida.</p>
                      ) : (
                        <table className="w-full text-xs">
                          <thead>
                            <tr style={{ background: T.s3, borderBottom: `1px solid ${T.border}` }}>
                              {['DATA', 'TURNO', 'LITROS', 'OBS'].map(h =>
                                <th key={h} className="text-left text-slate-500 px-3 py-2 font-medium text-[11px] tracking-wider uppercase">{h}</th>
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {cols.map((c, i) => (
                              <tr key={i} style={{ borderBottom: `1px solid ${T.border2}` }}>
                                <td className="px-3 py-2 text-slate-500">{c.data}</td>
                                <td className="px-3 py-2 text-slate-400">{c.via || '—'}</td>
                                <td className="px-3 py-2 text-emerald-400 font-semibold">{c.litros ? `${c.litros}L` : '—'}</td>
                                <td className="px-3 py-2 text-slate-600">{c.obs || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                      {cols.length > 0 && (
                        <p className="text-slate-500 text-[10px] mt-2">
                          Total: {cols.reduce((s, r) => s + (r.litros || 0), 0).toFixed(1)}L
                          {cols.reduce((s, r) => s + (r.litros || 0), 0) >= 4
                            ? ' — Colostragem adequada ✓'
                            : ' — Abaixo do recomendado (4L mín.)'}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* ── Novilhas ── */}
        <div className="flex items-center gap-2.5 px-5 py-2.5 mt-2"
             style={{ background: T.s2, borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
          <div className="w-1 h-3.5 rounded-full" style={{ background: '#a78bfa' }} />
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#a78bfa' }}>
            Novilhas
          </span>
          <span className="text-[11px] font-mono tabular-nums" style={{ color: T.muted }}>
            {novilhas.length}
          </span>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: T.s3, borderBottom: `1px solid ${T.border}` }}>
              {['NOME', 'RAÇA', 'NASCIMENTO', 'IDADE', 'OBS'].map(h =>
                <th key={h} className="text-left text-slate-500 px-5 py-2.5 font-medium text-[11px] tracking-wider uppercase">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {novilhas.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-slate-700 text-xs text-center">Nenhuma novilha cadastrada.</td></tr>
            )}
            {novilhas.map((a) => {
              const dias = idadeDias(a.nascimento)
              return (
                <tr key={a.id || a.nome} className="hover:bg-white/[0.02] transition-colors"
                    style={{ borderBottom: `1px solid ${T.border2}` }}>
                  <td className="px-5 py-2.5 text-slate-200 font-semibold">{a.nome}</td>
                  <td className="px-5 py-2.5 text-slate-500">{a.raca || '—'}</td>
                  <td className="px-5 py-2.5 text-slate-500">{fmtDate(a.nascimento)}</td>
                  <td className="px-5 py-2.5 text-slate-400">{dias !== null ? `${dias}d` : '—'}</td>
                  <td className="px-5 py-2.5 text-slate-600">{a.obs || '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Modal: cadastrar bezerro */}
      <Modal open={modal === 'bezerro'} onClose={() => setModal(null)} title="CADASTRAR BEZERRO / NOVILHA">
        <form onSubmit={salvarBezerro} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nome *">
              <Input value={formB.nome} onChange={e => setFormB(f => ({ ...f, nome: e.target.value }))} placeholder="Ex: Pintadinha" />
            </Field>
            <Field label="Status">
              <Select value={formB.status} onChange={e => setFormB(f => ({ ...f, status: e.target.value }))}>
                {STATUS_LIST.map(s => <option key={s}>{s}</option>)}
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Sexo">
              <Select value={formB.sexo} onChange={e => setFormB(f => ({ ...f, sexo: e.target.value }))}>
                <option>Fêmea</option>
                <option>Macho</option>
              </Select>
            </Field>
            <Field label="Data de nascimento">
              <Input type="date" value={formB.nascimento} onChange={e => setFormB(f => ({ ...f, nascimento: e.target.value }))} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nome da mãe">
              <Input value={formB.mae} onChange={e => setFormB(f => ({ ...f, mae: e.target.value }))} placeholder="Ex: Joana" />
            </Field>
            <Field label="Raça">
              <Input value={formB.raca} onChange={e => setFormB(f => ({ ...f, raca: e.target.value }))} placeholder="Ex: Holandesa" />
            </Field>
          </div>
          <Field label="Observações">
            <Textarea value={formB.obs} onChange={e => setFormB(f => ({ ...f, obs: e.target.value }))} placeholder="Procedência, histórico..." />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving ? 'Salvando...' : 'Cadastrar'}</Btn>
          </div>
        </form>
      </Modal>

      {/* Modal: registrar colostragem */}
      <Modal open={modal === 'colostragem'} onClose={() => setModal(null)} title={`COLOSTRAGEM — ${animalSel?.nome || ''}`}>
        <div className="p-3 rounded-lg mb-4 text-[11px] text-blue-400/80"
             style={{ background: '#22c55e08', border: '1px solid #22c55e20' }}>
          Recomendado: ≥ 4L nas primeiras 6h de vida. Registre cada fornecimento separadamente.
        </div>
        <form onSubmit={salvarColostragem} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Data">
              <Input type="date" value={formC.data} onChange={e => setFormC(f => ({ ...f, data: e.target.value }))} />
            </Field>
            <Field label="Turno">
              <Select value={formC.turno} onChange={e => setFormC(f => ({ ...f, turno: e.target.value }))}>
                {['manhã', 'tarde', 'noite', '1ª ordenha', '2ª ordenha'].map(t => <option key={t}>{t}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Litros fornecidos *">
            <Input type="number" step="0.1" min="0" placeholder="Ex: 2.0" inputMode="decimal"
                   value={formC.litros} onChange={e => setFormC(f => ({ ...f, litros: e.target.value }))} />
          </Field>
          <Field label="Observações">
            <Textarea value={formC.obs} onChange={e => setFormC(f => ({ ...f, obs: e.target.value }))}
                      placeholder="Ex: colostro da própria mãe, banco de colostro..." />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Btn variant="ghost" onClick={() => setModal(null)}>Cancelar</Btn>
            <Btn type="submit" variant="primary" disabled={saving}>{saving ? 'Salvando...' : 'Registrar'}</Btn>
          </div>
        </form>
      </Modal>
    </div>
  )
}
