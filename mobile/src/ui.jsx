/**
 * MilkShow UI Primitives — Design System
 * Paleta: #020617 bg · #0f172a surface · #1e293b border
 * Primary: #16a34a (verde agro) · Data: #3b82f6 (azul charts)
 * Touch targets: mín 40px (sm), 44px (md/lg)
 * Fonte mínima: 11px para labels, 12px para conteúdo
 */

import { AlertTriangle, CheckCircle, Info, Loader2, X, Database,
         ArrowUpRight, ArrowDownRight } from 'lucide-react'

// ─── TOKENS ──────────────────────────────────────────────────────────────────
export const T = {
  bg:      '#020617',
  surface: '#0f172a',
  s2:      '#111827',
  border:  '#1e293b',
  border2: '#0f172a',
  accent:  '#3b82f6',   // azul — charts e dados
  brand:   '#16a34a',   // verde — ações primárias
  text:    '#f1f5f9',
  muted:   '#64748b',
  dim:     '#334155',
}

// ─── SECTION HEADER ──────────────────────────────────────────────────────────
export function SectionHeader({ title, sub, action }) {
  return (
    <div className="flex items-center justify-between px-5 py-3.5 shrink-0"
         style={{ borderBottom: `1px solid ${T.border}` }}>
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-slate-400 text-[11px] font-mono uppercase tracking-widest shrink-0">{title}</span>
        {sub && <span className="text-slate-600 text-[11px] font-mono truncate">{sub}</span>}
      </div>
      {action && <div className="shrink-0 ml-4">{action}</div>}
    </div>
  )
}

// ─── SPINNER ─────────────────────────────────────────────────────────────────
export function Spinner({ size = 14 }) {
  return <Loader2 size={size} className="text-emerald-500 animate-spin" />
}

// ─── FULL PAGE LOADER ────────────────────────────────────────────────────────
export function Loading() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3">
      <Loader2 size={20} className="animate-spin text-emerald-500" />
      <span className="text-slate-600 text-xs font-mono tracking-wider">carregando...</span>
    </div>
  )
}

// ─── ERRO INLINE ─────────────────────────────────────────────────────────────
export function ErrorMsg({ msg, onRetry }) {
  if (!msg) return null
  return (
    <div className="flex items-center gap-2.5 px-5 py-3.5"
         style={{ borderBottom: `1px solid ${T.border}`, background: 'rgba(239,68,68,0.05)' }}>
      <AlertTriangle size={13} className="text-red-400 shrink-0" />
      <span className="text-red-400 text-xs font-mono flex-1">{msg}</span>
      {onRetry && (
        <button onClick={onRetry}
          className="text-xs font-mono text-blue-400 hover:text-blue-300 underline shrink-0">
          tentar novamente
        </button>
      )}
    </div>
  )
}

// ─── TOAST ───────────────────────────────────────────────────────────────────
export function Toast({ msg, tipo = 'ok', onClose }) {
  if (!msg) return null
  const { icon: Icon, color } = {
    ok:   { icon: CheckCircle,   color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/8' },
    erro: { icon: AlertTriangle, color: 'text-red-400 border-red-500/30 bg-red-500/8' },
    info: { icon: Info,          color: 'text-blue-400 border-blue-500/30 bg-blue-500/8' },
  }[tipo] || { icon: Info, color: 'text-slate-400 border-slate-700' }

  return (
    <div className={`flex items-center gap-2.5 px-3.5 py-2 rounded text-xs font-mono border ${color}`}>
      <Icon size={13} className="shrink-0" />
      <span className="flex-1">{msg}</span>
      {onClose && (
        <button onClick={onClose}
          className="opacity-50 hover:opacity-100 ml-1 flex items-center"
          aria-label="Fechar notificação">
          <X size={12} />
        </button>
      )}
    </div>
  )
}

// ─── BADGE ───────────────────────────────────────────────────────────────────
export function Badge({ label, nivel = 'info' }) {
  const s = {
    critico: 'text-red-400 border-red-500/30 bg-red-500/6',
    atencao: 'text-amber-400 border-amber-500/30 bg-amber-500/6',
    ok:      'text-emerald-400 border-emerald-500/30 bg-emerald-500/6',
    info:    'text-slate-400 border-slate-700',
    azul:    'text-blue-400 border-blue-500/30 bg-blue-500/6',
  }[nivel] || 'text-slate-500 border-slate-700'
  return (
    <span className={`text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${s}`}>
      {label}
    </span>
  )
}

// ─── STATUS ANIMAL ───────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const map = {
    'Lactação': 'text-emerald-400',
    'Seca':     'text-amber-400',
    'Gestação': 'text-blue-400',
    'Novilha':  'text-violet-400',
    'Bezerro':  'text-orange-400',
    'Vendido':  'text-slate-600',
  }
  return (
    <span className={`text-xs font-mono ${map[status] || 'text-slate-500'}`}>
      {status}
    </span>
  )
}

// ─── BUTTON ──────────────────────────────────────────────────────────────────
export function Btn({ children, onClick, type = 'button', variant = 'primary', size = 'sm', disabled, className = '' }) {
  const base = 'inline-flex items-center justify-center gap-1.5 font-mono rounded transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed select-none active:scale-[0.97]'

  const sizes = {
    xs: 'text-[11px] px-2.5 py-1.5 min-h-[32px]',
    sm: 'text-xs px-3.5 py-2 min-h-[36px]',
    md: 'text-sm px-5 py-2.5 min-h-[44px]',
  }

  const vars = {
    primary: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm',
    ghost:   'border border-slate-700 hover:border-slate-500 text-slate-400 hover:text-slate-200',
    danger:  'border border-red-500/30 hover:border-red-400/60 text-red-400 hover:text-red-300',
    success: 'border border-emerald-500/30 hover:border-emerald-400/60 text-emerald-400 hover:text-emerald-300',
    outline: 'border border-emerald-600/40 hover:border-emerald-500/70 text-emerald-400 hover:text-emerald-300',
    blue:    'bg-blue-600 hover:bg-blue-500 text-white shadow-sm',
  }[variant] || ''

  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`${base} ${sizes[size] || sizes.sm} ${vars} ${className}`}>
      {children}
    </button>
  )
}

// ─── FIELD / INPUT / SELECT / TEXTAREA ───────────────────────────────────────
export function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-slate-500 text-[11px] font-mono uppercase tracking-widest mb-1.5">
          {label}
        </label>
      )}
      {children}
    </div>
  )
}

const inputBase = `w-full bg-transparent border rounded-md px-3 py-2.5 text-slate-200 text-sm font-mono
  min-h-[42px] focus:outline-none focus:border-emerald-600/60 focus:ring-1 focus:ring-emerald-600/20
  transition-colors placeholder-slate-700`

export function Input({ ...props }) {
  return (
    <input
      {...props}
      style={{ borderColor: T.border }}
      className={`${inputBase} ${props.className || ''}`}
    />
  )
}

export function Select({ children, ...props }) {
  return (
    <select
      {...props}
      style={{ background: T.surface, borderColor: T.border }}
      className={`${inputBase} ${props.className || ''}`}
    >
      {children}
    </select>
  )
}

export function Textarea({ ...props }) {
  return (
    <textarea
      {...props}
      rows={props.rows || 3}
      style={{ borderColor: T.border }}
      className={`${inputBase} resize-none min-h-[80px] ${props.className || ''}`}
    />
  )
}

// ─── TABELA ──────────────────────────────────────────────────────────────────
export function Th({ children, className = '' }) {
  return (
    <th className={`text-left text-slate-600 px-4 py-2.5 font-medium tracking-widest text-[11px] font-mono uppercase whitespace-nowrap ${className}`}>
      {children}
    </th>
  )
}

export function Td({ children, className = '' }) {
  return (
    <td className={`px-4 py-3 text-xs font-mono ${className}`}>
      {children}
    </td>
  )
}

export function TRow({ children, onClick, className = '' }) {
  return (
    <tr onClick={onClick}
      className={`transition-colors hover:bg-white/[0.025] ${onClick ? 'cursor-pointer' : ''} ${className}`}
      style={{ borderBottom: `1px solid ${T.border2}` }}>
      {children}
    </tr>
  )
}

// ─── MODAL ───────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, width = 440 }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4"
         style={{ background: 'rgba(2,6,23,0.88)', backdropFilter: 'blur(4px)' }}
         onClick={onClose}>
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, width, maxWidth: '95vw', maxHeight: '90vh' }}
           className="rounded-xl flex flex-col overflow-hidden shadow-2xl w-full md:w-auto"
           onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 shrink-0"
             style={{ borderBottom: `1px solid ${T.border}` }}>
          <span className="text-slate-300 text-sm font-semibold">{title}</span>
          <button onClick={onClose}
            className="text-slate-600 hover:text-slate-300 transition-colors p-1 -mr-1 rounded"
            aria-label="Fechar modal">
            <X size={16} />
          </button>
        </div>
        {/* Body */}
        <div className="overflow-y-auto p-5 space-y-4 flex-1">
          {children}
        </div>
      </div>
    </div>
  )
}

// ─── DELTA ───────────────────────────────────────────────────────────────────
export function Delta({ value }) {
  if (value === undefined || value === null) return null
  const pos = value >= 0
  return (
    <span className={`inline-flex items-center gap-0.5 text-[11px] font-mono
      ${pos ? 'text-emerald-400' : 'text-red-400'}`}>
      {pos ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
      {Math.abs(value).toFixed(1)}%
    </span>
  )
}

// ─── EMPTY STATE ─────────────────────────────────────────────────────────────
export function Empty({ msg = 'Nenhum dado encontrado.' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <div className="w-12 h-12 rounded-full flex items-center justify-center"
           style={{ background: T.s2, border: `1px solid ${T.border}` }}>
        <Database size={18} className="text-slate-700" />
      </div>
      <p className="text-slate-600 text-xs font-mono">{msg}</p>
    </div>
  )
}

// ─── SKELETON ────────────────────────────────────────────────────────────────
export function Skeleton({ className = '' }) {
  return (
    <div className={`rounded animate-pulse ${className}`}
         style={{ background: T.border }} />
  )
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────
export function fmtBRL(n) {
  return `R$ ${Number(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function fmtDate(str) {
  if (!str) return '—'
  return new Date(str + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

export function dataParto(insStr) {
  if (!insStr) return '—'
  const d = new Date(insStr)
  d.setDate(d.getDate() + 283)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

export function idadeDias(nascStr) {
  if (!nascStr) return null
  const d = new Date(nascStr)
  return Math.floor((Date.now() - d.getTime()) / 86400000)
}

export const hoje = () => new Date().toISOString().split('T')[0]

// ─── CSV DOWNLOAD ─────────────────────────────────────────────────────────────
export function csvDownload(rows, filename) {
  if (!rows?.length) return
  const cols = Object.keys(rows[0])
  const escape = v => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines  = [cols.join(','), ...rows.map(r => cols.map(c => escape(r[c])).join(','))]
  const blob   = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url    = URL.createObjectURL(blob)
  const a      = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ─── CHART CONTROLS ──────────────────────────────────────────────────────────
// Seletor de período (dias) + tipo de gráfico
export function ChartControls({
  periodo, setPeriodo,
  tipo, setTipo,
  periodos = [7, 14, 30, 60, 90],
  tipos = ['area', 'linha', 'barra'],
}) {
  const LABELS = { area: 'Área', linha: 'Linha', barra: 'Barras' }
  return (
    <div className="flex items-center justify-between gap-2 flex-wrap">
      {/* Período */}
      <div className="flex items-center gap-1">
        {periodos.map(p => (
          <button key={p} onClick={() => setPeriodo(p)}
            className="px-2.5 py-1 rounded-md text-[11px] font-mono transition-all min-w-[32px]"
            style={{
              background: periodo === p ? T.border  : 'transparent',
              border:     `1px solid ${periodo === p ? '#334155' : 'transparent'}`,
              color:       periodo === p ? '#cbd5e1' : '#475569',
            }}>
            {p}d
          </button>
        ))}
      </div>
      {/* Tipo */}
      <div className="flex items-center gap-0.5 rounded-lg p-0.5"
           style={{ background: T.surface, border: `1px solid ${T.border}` }}>
        {tipos.map(t => (
          <button key={t} onClick={() => setTipo(t)}
            className="px-2.5 py-1 rounded text-[11px] font-mono transition-all"
            style={{
              background: tipo === t ? T.border  : 'transparent',
              color:       tipo === t ? '#cbd5e1' : '#475569',
            }}>
            {LABELS[t] || t}
          </button>
        ))}
      </div>
    </div>
  )
}
