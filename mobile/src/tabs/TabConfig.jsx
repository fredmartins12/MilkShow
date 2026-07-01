import { useEffect, useState } from 'react'
import { Save, RefreshCw, Plus, Trash2, MessageCircle, Shield, Eye, Stethoscope, Wrench } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, SectionHeader,
  Field, Input, Select, Btn, T,
} from '../ui.jsx'

const PERFIS = [
  { value: 'admin',       label: 'Administrador', icon: Shield,        cor: '#10b981', desc: 'Acesso total — registra, edita e vê tudo' },
  { value: 'operador',    label: 'Operador/Peão', icon: Wrench,        cor: '#22c55e', desc: 'Registra produção, ordena e alimenta animais' },
  { value: 'vet',         label: 'Veterinário',   icon: Stethoscope,   cor: '#f59e0b', desc: 'Registra protocolos sanitários e exames' },
  { value: 'visualizador',label: 'Visualizador',  icon: Eye,           cor: '#8b5cf6', desc: 'Só consulta dados — sem permissão de escrita' },
]

function PerfilBadge({ perfil }) {
  const p = PERFIS.find(x => x.value === perfil) || PERFIS[3]
  const Icon = p.icon
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium"
          style={{ background: p.cor + '18', border: `1px solid ${p.cor}30`, color: p.cor }}>
      <Icon size={10} />
      {p.label}
    </span>
  )
}

const CAMPOS = [
  { key: 'nome_fazenda',    label: 'Nome da Fazenda',         placeholder: 'Ex: Fazenda Santa Clara', type: 'text'   },
  { key: 'preco_leite',     label: 'Preço do Leite (R$/L)',   placeholder: 'Ex: 3.20',                type: 'number' },
  { key: 'custo_por_litro', label: 'Custo Operacional (R$/L)',placeholder: 'Ex: 1.18',                type: 'number' },
  { key: 'meta_producao',   label: 'Meta Diária (L)',         placeholder: 'Ex: 900',                 type: 'number' },
  { key: 'responsavel_vet', label: 'Veterinário Responsável', placeholder: 'Ex: Dr. Paulo Silva',     type: 'text'   },
  { key: 'cnpj',            label: 'CNPJ / CPF',              placeholder: 'Ex: 00.000.000/0001-00',  type: 'text'   },
  { key: 'municipio',       label: 'Município / Estado',      placeholder: 'Ex: Uberaba — MG',        type: 'text'   },
  { key: 'contato',         label: 'Contato / Telefone',      placeholder: 'Ex: (34) 99999-0000',     type: 'text'   },
]

export default function TabConfig() {
  const [config, setConfig]   = useState({})
  const [form, setForm]       = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [erro, setErro]       = useState('')
  const [toast, setToast]     = useState(null)
  const [dirty, setDirty]     = useState(false)

  // Usuários WhatsApp
  const [usuarios, setUsuarios]   = useState([])
  const [loadingUsr, setLoadUsr]  = useState(false)
  const [savingUsr, setSavingUsr] = useState(false)
  const [formUsr, setFormUsr]     = useState({ tel: '', nome: '', perfil: 'operador' })

  async function carregarUsuarios() {
    setLoadUsr(true)
    try { setUsuarios(await api.usuariosWpp()) }
    catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setLoadUsr(false) }
  }

  async function adicionarUsuario(e) {
    e.preventDefault()
    if (!formUsr.tel.trim() || !formUsr.nome.trim()) return
    setSavingUsr(true)
    try {
      await api.adicionarUsuarioWpp(formUsr)
      setToast({ msg: `${formUsr.nome} adicionado ao WhatsApp`, tipo: 'ok' })
      setFormUsr({ tel: '', nome: '', perfil: 'operador' })
      carregarUsuarios()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSavingUsr(false) }
  }

  async function removerUsuario(u) {
    if (!confirm(`Remover ${u.nome} do WhatsApp?`)) return
    try {
      await api.removerUsuarioWpp(u.tel)
      setToast({ msg: `${u.nome} removido`, tipo: 'ok' })
      carregarUsuarios()
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
  }

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const c = await api.config()
      setConfig(c)
      setForm(c)
      setDirty(false)
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar(); carregarUsuarios() }, [])

  useEffect(() => {
    const onRefresh = () => carregar()
    window.addEventListener('milkshow:refresh', onRefresh)
    return () => window.removeEventListener('milkshow:refresh', onRefresh)
  }, [])

  function handleChange(key, value) {
    setForm(f => ({ ...f, [key]: value }))
    setDirty(true)
  }

  async function salvar(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.salvarConfig(form)
      setConfig(form)
      setDirty(false)
      setToast({ msg: 'Configurações salvas com sucesso', tipo: 'ok' })
    } catch(e) { setToast({ msg: e.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  if (loading) return <Loading />

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      <SectionHeader
        title="CONFIGURAÇÕES DA FAZENDA"
        sub="Parâmetros operacionais e financeiros"
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11}/></Btn>
            {dirty && (
              <Btn variant="success" size="xs" disabled={saving} onClick={salvar}>
                <Save size={11}/>{saving ? 'Salvando...' : 'Salvar alterações'}
              </Btn>
            )}
          </div>
        }
      />

      <div className="overflow-auto flex-1 p-6">
        <form onSubmit={salvar}>
          {/* Dados da fazenda */}
          <div className="mb-8">
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-4 pb-2"
               style={{ borderBottom:`1px solid ${T.border}` }}>
              Identificação
            </p>
            <div className="grid grid-cols-2 gap-5">
              {CAMPOS.slice(0, 4).map(c => (
                <Field key={c.key} label={c.label}>
                  <Input
                    type={c.type}
                    step={c.type === 'number' ? '0.01' : undefined}
                    placeholder={c.placeholder}
                    value={form[c.key] || ''}
                    onChange={e => handleChange(c.key, e.target.value)}
                  />
                </Field>
              ))}
            </div>
          </div>

          {/* Contato e local */}
          <div className="mb-8">
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-4 pb-2"
               style={{ borderBottom:`1px solid ${T.border}` }}>
              Contato e Localização
            </p>
            <div className="grid grid-cols-2 gap-5">
              {CAMPOS.slice(4).map(c => (
                <Field key={c.key} label={c.label}>
                  <Input
                    type={c.type}
                    placeholder={c.placeholder}
                    value={form[c.key] || ''}
                    onChange={e => handleChange(c.key, e.target.value)}
                  />
                </Field>
              ))}
            </div>
          </div>

          {/* Preview financeiro */}
          <div className="mb-8">
            <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-4 pb-2"
               style={{ borderBottom:`1px solid ${T.border}` }}>
              Preview — Indicadores Calculados
            </p>
            <div className="grid grid-cols-3 gap-4">
              {[
                {
                  label: 'MARGEM BRUTA',
                  value: form.preco_leite && form.custo_por_litro
                    ? `${(((form.preco_leite - form.custo_por_litro) / form.preco_leite) * 100).toFixed(1)}%`
                    : '—',
                  accent: '#10b981',
                },
                {
                  label: 'RECEITA ESTIMADA (META)',
                  value: form.preco_leite && form.meta_producao
                    ? `R$ ${(form.preco_leite * form.meta_producao).toFixed(2)}/dia`
                    : '—',
                  accent: '#22c55e',
                },
                {
                  label: 'CUSTO ESTIMADO (META)',
                  value: form.custo_por_litro && form.meta_producao
                    ? `R$ ${(form.custo_por_litro * form.meta_producao).toFixed(2)}/dia`
                    : '—',
                  accent: '#64748b',
                },
              ].map(k => (
                <div key={k.label} className="p-4 rounded-xl flex flex-col gap-1"
                     style={{ background: T.s2, border:`1px solid ${T.border}`, borderTop: `2px solid ${k.accent}` }}>
                  <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">{k.label}</p>
                  <p className="text-xl font-mono font-semibold tabular-nums" style={{ color: k.accent === '#64748b' ? T.text : k.accent }}>{k.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2" style={{ borderTop:`1px solid ${T.border}` }}>
            <Btn variant="ghost" type="button" onClick={carregar}>Descartar</Btn>
            <Btn type="submit" variant="primary" disabled={saving || !dirty}>
              <Save size={12}/>{saving ? 'Salvando...' : 'Salvar configurações'}
            </Btn>
          </div>
        </form>

        {/* ── Usuários WhatsApp ── */}
        <div className="mt-8 pt-6" style={{ borderTop: `1px solid ${T.border}` }}>
          <div className="flex items-center gap-2.5 mb-5">
            <MessageCircle size={15} style={{ color: '#25d366' }} />
            <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: T.sub }}>
              Usuários WhatsApp
            </p>
          </div>
          <p className="text-[12px] mb-5" style={{ color: T.muted }}>
            Cadastre os números autorizados a interagir com o bot do MilkShow via WhatsApp.
            Cada usuário tem um perfil que define o que pode registrar ou consultar.
          </p>

          {/* Perfis disponíveis */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            {PERFIS.map(p => {
              const Icon = p.icon
              return (
                <div key={p.value} className="flex items-start gap-3 p-3 rounded-xl"
                     style={{ background: T.s2, border: `1px solid ${T.border}` }}>
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                       style={{ background: p.cor + '18' }}>
                    <Icon size={13} style={{ color: p.cor }} />
                  </div>
                  <div>
                    <p className="text-[12px] font-semibold" style={{ color: p.cor }}>{p.label}</p>
                    <p className="text-[11px] mt-0.5" style={{ color: T.muted }}>{p.desc}</p>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Form adicionar */}
          <form onSubmit={adicionarUsuario} className="flex flex-col sm:flex-row gap-3 mb-5 p-4 rounded-xl"
                style={{ background: T.s2, border: `1px solid ${T.border}` }}>
            <Field label="Nome" className="flex-1">
              <Input
                placeholder="Ex: João Peão"
                value={formUsr.nome}
                onChange={e => setFormUsr(f => ({ ...f, nome: e.target.value }))}
              />
            </Field>
            <Field label="WhatsApp (com DDD)" className="flex-1">
              <Input
                placeholder="Ex: (83) 99999-0000"
                value={formUsr.tel}
                onChange={e => setFormUsr(f => ({ ...f, tel: e.target.value }))}
                inputMode="tel"
              />
            </Field>
            <Field label="Perfil" className="min-w-[160px]">
              <Select value={formUsr.perfil} onChange={e => setFormUsr(f => ({ ...f, perfil: e.target.value }))}>
                {PERFIS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </Select>
            </Field>
            <div className="flex items-end">
              <Btn type="submit" variant="primary" size="sm" disabled={savingUsr}>
                <Plus size={13} />{savingUsr ? 'Adicionando...' : 'Adicionar'}
              </Btn>
            </div>
          </form>

          {/* Lista de usuários */}
          {loadingUsr ? (
            <p className="text-[12px] text-center py-4" style={{ color: T.muted }}>Carregando...</p>
          ) : usuarios.length === 0 ? (
            <div className="text-center py-8 rounded-xl" style={{ background: T.s2, border: `1px solid ${T.border}` }}>
              <MessageCircle size={24} className="mx-auto mb-2" style={{ color: T.muted }} />
              <p className="text-[12px]" style={{ color: T.muted }}>Nenhum usuário cadastrado ainda.</p>
            </div>
          ) : (
            <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${T.border}` }}>
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ background: T.s3, borderBottom: `1px solid ${T.border}` }}>
                    {['NOME', 'WHATSAPP', 'PERFIL', ''].map(h =>
                      <th key={h} className="text-left px-4 py-2.5 font-medium text-[11px] tracking-wider uppercase"
                          style={{ color: T.muted }}>{h}</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {usuarios.map(u => (
                    <tr key={u.tel} className="hover:bg-white/[0.02] transition-colors"
                        style={{ borderBottom: `1px solid ${T.border2}` }}>
                      <td className="px-4 py-3 text-slate-200 font-semibold">{u.nome}</td>
                      <td className="px-4 py-3 font-mono text-[12px]" style={{ color: T.sub }}>
                        +{u.tel}
                      </td>
                      <td className="px-4 py-3">
                        <PerfilBadge perfil={u.perfil} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => removerUsuario(u)}
                          className="p-1.5 rounded transition-colors text-slate-700 hover:text-red-400"
                          aria-label="Remover">
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
