/**
 * TabArmazem — Controle de estoque (ração, medicamentos, insumos)
 * CRUD completo com alertas de estoque baixo
 */

import { useEffect, useState } from 'react'
import { Plus, Package, AlertTriangle, RefreshCw, Pencil, Trash2, X } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, Modal, SectionHeader,
  Field, Input, Select, Btn, T, hoje,
} from '../ui.jsx'

const UNIDADES   = ['kg', 'L', 'un', 'sc', 'cx', 'g', 'mL', 'dose']
const CATEGORIAS = ['Ração', 'Suplemento', 'Medicamento', 'Vacina', 'Desinfetante', 'Combustível', 'Outros']

const FORM_VAZIO = { item: '', qtd: '', un: 'kg', custo_unit: '', categoria: 'Ração', min_alerta: '', obs: '' }

function ItemCard({ item, onEdit, onDelete }) {
  const baixo = item.min_alerta && Number(item.qtd) <= Number(item.min_alerta)
  const zero  = Number(item.qtd) <= 0

  return (
    <div className="rounded-xl p-4 flex flex-col gap-3 transition-all hover:border-slate-600"
         style={{
           background: T.surface,
           border: `1px solid ${zero ? '#ef444440' : baixo ? '#f5940040' : T.border}`,
         }}>
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
               style={{ background: zero ? '#ef444415' : baixo ? '#f5940015' : '#16a34a15' }}>
            <Package size={14} className={zero ? 'text-red-500' : baixo ? 'text-amber-500' : 'text-emerald-500'} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-200 truncate">{item.item}</p>
            <p className="text-[11px] font-mono text-slate-600">{item.categoria || '—'}</p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => onEdit(item)}
            className="p-1.5 rounded text-slate-600 hover:text-slate-300 transition-colors"
            aria-label="Editar">
            <Pencil size={13} />
          </button>
          <button onClick={() => onDelete(item)}
            className="p-1.5 rounded text-slate-600 hover:text-red-400 transition-colors"
            aria-label="Remover">
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Quantidade */}
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[11px] font-mono text-slate-600 mb-0.5">Quantidade</p>
          <p className="text-2xl font-mono font-bold tabular-nums"
             style={{ color: zero ? '#ef4444' : baixo ? '#f59e0b' : '#f1f5f9' }}>
            {Number(item.qtd).toLocaleString('pt-BR')}
            <span className="text-slate-600 text-sm font-normal ml-1">{item.un}</span>
          </p>
        </div>
        {item.custo_unit > 0 && (
          <div className="text-right">
            <p className="text-[11px] font-mono text-slate-600 mb-0.5">Custo unit.</p>
            <p className="text-sm font-mono text-slate-400">
              R$ {Number(item.custo_unit).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </p>
          </div>
        )}
      </div>

      {/* Alertas */}
      {zero && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
             style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <AlertTriangle size={12} className="text-red-400 shrink-0" />
          <span className="text-red-400 text-[11px] font-mono">Estoque zerado</span>
        </div>
      )}
      {!zero && baixo && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
             style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <AlertTriangle size={12} className="text-amber-500 shrink-0" />
          <span className="text-amber-500 text-[11px] font-mono">
            Estoque baixo · mínimo {item.min_alerta} {item.un}
          </span>
        </div>
      )}
    </div>
  )
}

function FormEstoque({ form, onChange, onSubmit, onClose, saving, editando }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field label="Nome do item *">
        <Input value={form.item} onChange={e => onChange('item', e.target.value)}
          placeholder="Ex: Ração concentrada" autoFocus />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Categoria">
          <Select value={form.categoria} onChange={e => onChange('categoria', e.target.value)}>
            {CATEGORIAS.map(c => <option key={c}>{c}</option>)}
          </Select>
        </Field>
        <Field label="Unidade">
          <Select value={form.un} onChange={e => onChange('un', e.target.value)}>
            {UNIDADES.map(u => <option key={u}>{u}</option>)}
          </Select>
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label={`Quantidade (${form.un}) *`}>
          <Input type="number" step="0.01" min="0" inputMode="decimal"
            value={form.qtd} onChange={e => onChange('qtd', e.target.value)}
            placeholder="0" />
        </Field>
        <Field label={`Alerta mínimo (${form.un})`}>
          <Input type="number" step="0.01" min="0" inputMode="decimal"
            value={form.min_alerta} onChange={e => onChange('min_alerta', e.target.value)}
            placeholder="Ex: 50" />
        </Field>
      </div>
      <Field label="Custo unitário (R$)">
        <Input type="number" step="0.01" min="0" inputMode="decimal"
          value={form.custo_unit} onChange={e => onChange('custo_unit', e.target.value)}
          placeholder="0,00" />
      </Field>
      <div className="flex justify-end gap-2 pt-1">
        <Btn variant="ghost" onClick={onClose} type="button">Cancelar</Btn>
        <Btn type="submit" variant="primary" disabled={saving}>
          {saving ? 'Salvando...' : editando ? 'Salvar alterações' : 'Adicionar item'}
        </Btn>
      </div>
    </form>
  )
}

export default function TabArmazem() {
  const [itens, setItens]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [erro, setErro]         = useState('')
  const [toast, setToast]       = useState(null)
  const [modal, setModal]       = useState(false)
  const [editando, setEditando] = useState(null)
  const [confirmDel, setDel]    = useState(null)
  const [saving, setSaving]     = useState(false)
  const [form, setForm]         = useState(FORM_VAZIO)
  const [filtro, setFiltro]     = useState('Todos')

  async function carregar() {
    setLoading(true); setErro('')
    try { setItens(await api.estoque()) }
    catch (e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  function abrirNovo() {
    setEditando(null)
    setForm(FORM_VAZIO)
    setModal(true)
  }

  function abrirEditar(item) {
    setEditando(item)
    setForm({
      item:       item.item || '',
      qtd:        item.qtd != null ? String(item.qtd) : '',
      un:         item.un || 'kg',
      custo_unit: item.custo_unit != null ? String(item.custo_unit) : '',
      categoria:  item.categoria || 'Ração',
      min_alerta: item.min_alerta != null ? String(item.min_alerta) : '',
    })
    setModal(true)
  }

  function onChange(k, v) { setForm(f => ({ ...f, [k]: v })) }

  async function salvar(e) {
    e.preventDefault()
    if (!form.item.trim() || form.qtd === '') return
    setSaving(true)
    try {
      const body = {
        item:       form.item.trim(),
        qtd:        parseFloat(form.qtd) || 0,
        un:         form.un,
        custo_unit: parseFloat(form.custo_unit) || 0,
        categoria:  form.categoria,
        min_alerta: form.min_alerta !== '' ? parseFloat(form.min_alerta) : null,
      }
      if (editando) {
        await api.atualizarEstoque(editando.id, body)
        setToast({ msg: `${form.item} atualizado`, tipo: 'ok' })
      } else {
        await api.registrarEstoque(body)
        setToast({ msg: `${form.item} adicionado ao armazém`, tipo: 'ok' })
      }
      setModal(false)
      carregar()
    } catch (err) { setToast({ msg: err.message, tipo: 'erro' }) }
    finally { setSaving(false) }
  }

  async function remover(item) {
    try {
      await api.removerEstoque(item.id)
      setToast({ msg: `${item.item} removido`, tipo: 'ok' })
      carregar()
    } catch (err) { setToast({ msg: err.message, tipo: 'erro' }) }
    finally { setDel(null) }
  }

  if (loading) return <Loading />

  const categorias   = ['Todos', ...new Set(itens.map(i => i.categoria).filter(Boolean))]
  const alertas      = itens.filter(i => !i.min_alerta || Number(i.qtd) <= Number(i.min_alerta))
  const filtrados    = filtro === 'Todos' ? itens : itens.filter(i => i.categoria === filtro)

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* Resumo */}
      <div className="grid grid-cols-3 shrink-0" style={{ borderBottom: `1px solid ${T.border}` }}>
        {[
          { label: 'Itens em estoque', value: itens.length, cor: 'text-slate-100' },
          { label: 'Alertas',          value: alertas.length, cor: alertas.length > 0 ? 'text-amber-400' : 'text-slate-100' },
          { label: 'Categorias',       value: categorias.length - 1, cor: 'text-slate-100' },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-5"
               style={{ borderRight: i < arr.length - 1 ? `1px solid ${T.border}` : 'none' }}>
            <p className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-2">{k.label}</p>
            <p className={`text-2xl font-mono font-bold tabular-nums ${k.cor}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Header com filtros */}
      <SectionHeader
        title="Itens do Armazém"
        sub={`${filtrados.length} itens`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <Btn variant="ghost" size="xs" onClick={carregar}><RefreshCw size={11} /></Btn>
            <Btn variant="primary" size="xs" onClick={abrirNovo}><Plus size={11} />Novo item</Btn>
          </div>
        }
      />

      {/* Filtro por categoria */}
      <div className="flex items-center gap-2 px-5 py-3 overflow-x-auto shrink-0"
           style={{ borderBottom: `1px solid ${T.border}` }}>
        {categorias.map(cat => (
          <button key={cat} onClick={() => setFiltro(cat)}
            className="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all shrink-0"
            style={{
              background: filtro === cat ? '#1e293b' : 'transparent',
              border:     `1px solid ${filtro === cat ? '#334155' : 'transparent'}`,
              color:       filtro === cat ? '#cbd5e1' : '#64748b',
            }}>
            {cat}
          </button>
        ))}
      </div>

      {/* Grid de itens */}
      <div className="overflow-auto flex-1 p-5">
        {filtrados.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="w-12 h-12 rounded-full flex items-center justify-center"
                 style={{ background: T.surface, border: `1px solid ${T.border}` }}>
              <Package size={18} className="text-slate-700" />
            </div>
            <p className="text-slate-600 text-xs font-mono">nenhum item cadastrado</p>
            <Btn variant="outline" size="sm" onClick={abrirNovo}><Plus size={12} />Adicionar primeiro item</Btn>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtrados.map(item => (
              <ItemCard key={item.id} item={item}
                onEdit={abrirEditar}
                onDelete={setDel} />
            ))}
          </div>
        )}
      </div>

      {/* Modal form */}
      <Modal open={modal} onClose={() => setModal(false)}
        title={editando ? `Editar — ${editando.item}` : 'Novo Item do Armazém'}>
        <FormEstoque form={form} onChange={onChange} onSubmit={salvar}
          onClose={() => setModal(false)} saving={saving} editando={!!editando} />
      </Modal>

      {/* Confirmação remoção */}
      <Modal open={!!confirmDel} onClose={() => setDel(null)} title="Remover item">
        <p className="text-slate-400 text-sm">
          Remover <strong className="text-slate-200">{confirmDel?.item}</strong> do armazém?
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Btn variant="ghost" onClick={() => setDel(null)}>Cancelar</Btn>
          <Btn variant="danger" onClick={() => remover(confirmDel)}>
            <Trash2 size={12} /> Remover
          </Btn>
        </div>
      </Modal>
    </div>
  )
}
