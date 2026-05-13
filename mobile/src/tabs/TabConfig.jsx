import { useEffect, useState } from 'react'
import { Save, RefreshCw } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, SectionHeader,
  Field, Input, Btn, T,
} from '../ui.jsx'

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

  useEffect(() => { carregar() }, [])

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
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-700 mb-4 pb-2"
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
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-700 mb-4 pb-2"
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
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-700 mb-4 pb-2"
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
                  color: 'text-emerald-400',
                },
                {
                  label: 'RECEITA ESTIMADA (META)',
                  value: form.preco_leite && form.meta_producao
                    ? `R$ ${(form.preco_leite * form.meta_producao).toFixed(2)}/dia`
                    : '—',
                  color: 'text-blue-400',
                },
                {
                  label: 'CUSTO ESTIMADO (META)',
                  value: form.custo_por_litro && form.meta_producao
                    ? `R$ ${(form.custo_por_litro * form.meta_producao).toFixed(2)}/dia`
                    : '—',
                  color: 'text-slate-400',
                },
              ].map(k => (
                <div key={k.label} className="p-4 rounded" style={{ background: T.s2, border:`1px solid ${T.border}` }}>
                  <p className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-2">{k.label}</p>
                  <p className={`text-lg font-mono font-semibold ${k.color}`}>{k.value}</p>
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
      </div>
    </div>
  )
}
