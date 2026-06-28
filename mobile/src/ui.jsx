/**
 * MilkShow UI — Design System v3
 * Inspirado no Leigado mas com identidade própria: verde + MilkShow branding
 */

import { AlertTriangle, CheckCircle, Info, Loader2, X, Database,
         ArrowUpRight, ArrowDownRight } from 'lucide-react'

// ─── TOKENS ──────────────────────────────────────────────────────────────────
export const T = {
  // Fundo e superfícies (tema claro como Leigado)
  bg:       '#f0f4f0',   // fundo principal — verde muito claro
  surface:  '#ffffff',   // cards e paineis — branco
  s2:       '#f5f9f5',   // superfície levemente verde
  s3:       '#ebf3eb',   // superfície mais escura
  border:   '#d4e6d4',   // borda verde claro
  border2:  '#e8f0e8',   // borda muito sutil

  // Brand e acentos — verde vibrante
  brand:    '#22c55e',   // verde principal
  brand2:   '#16a34a',   // verde escuro
  brandGlow: 'rgba(34,197,94,0.15)',

  // Header e sidebar
  header:   '#22c55e',   // top bar verde
  sidebar:  '#ffffff',   // sidebar branca

  // Texto
  text:     '#1a2e1a',   // texto principal — verde escuro quase preto
  sub:      '#4a6741',   // texto secundário — verde médio
  muted:    '#7a9b77',   // texto muted — verde claro

  // Outros
  accent:   '#059669',   // esmeralda para destaques
  red:      '#dc2626',
  amber:    '#d97706',
  blue:     '#2563eb',
  purple:   '#7c3aed',
  green:    '#22c55e',
}

// ─── PALETA KPI — tiles coloridas como Leigado ───────────────────────────────
export const KPI_COLORS = {
  green:   { bg: 'linear-gradient(135deg, #16a34a, #22c55e)', icon: 'rgba(255,255,255,0.15)' },
  teal:    { bg: 'linear-gradient(135deg, #0d9488, #14b8a6)', icon: 'rgba(255,255,255,0.15)' },
  amber:   { bg: 'linear-gradient(135deg, #d97706, #f59e0b)', icon: 'rgba(255,255,255,0.15)' },
  emerald: { bg: 'linear-gradient(135deg, #059669, #10b981)', icon: 'rgba(255,255,255,0.15)' },
  blue:    { bg: 'linear-gradient(135deg, #1d4ed8, #3b82f6)', icon: 'rgba(255,255,255,0.15)' },
  red:     { bg: 'linear-gradient(135deg, #b91c1c, #ef4444)', icon: 'rgba(255,255,255,0.15)' },
  purple:  { bg: 'linear-gradient(135deg, #6d28d9, #8b5cf6)', icon: 'rgba(255,255,255,0.15)' },
  slate:   { bg: 'linear-gradient(135deg, #334155, #64748b)', icon: 'rgba(255,255,255,0.15)' },
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
  const d = new Date(insStr); d.setDate(d.getDate() + 283)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}
export function idadeDias(nascStr) {
  if (!nascStr) return null
  return Math.floor((Date.now() - new Date(nascStr).getTime()) / 86400000)
}
export const hoje = () => new Date().toISOString().split('T')[0]

export function csvDownload(rows, filename) {
  if (!rows?.length) return
  const cols = Object.keys(rows[0])
  const escape = v => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = [cols.join(','), ...rows.map(r => cols.map(c => escape(r[c])).join(','))]
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ─── LOADING ─────────────────────────────────────────────────────────────────
export function Loading() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3" style={{ background: T.bg }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center"
           style={{ background: T.brandGlow }}>
        <Loader2 size={18} className="animate-spin" style={{ color: T.brand }} />
      </div>
      <span className="text-sm font-medium" style={{ color: T.muted }}>Carregando...</span>
    </div>
  )
}

export function Spinner({ size = 14 }) {
  return <Loader2 size={size} className="animate-spin" style={{ color: T.brand }} />
}

// ─── ERROR ────────────────────────────────────────────────────────────────────
export function ErrorMsg({ msg, onRetry }) {
  if (!msg) return null
  return (
    <div className="flex items-center gap-3 px-5 py-3 bg-red-50 border-b border-red-100">
      <AlertTriangle size={14} className="text-red-500 shrink-0" />
      <span className="text-sm text-red-700 flex-1">{msg}</span>
      {onRetry && (
        <button onClick={onRetry} className="text-sm font-medium text-red-600 hover:text-red-800 underline transition-colors">
          Tentar novamente
        </button>
      )}
    </div>
  )
}

// ─── TOAST ───────────────────────────────────────────────────────────────────
export function Toast({ msg, tipo = 'ok', onClose }) {
  if (!msg) return null
  const configs = {
    ok:   { bg: '#f0fdf4', border: '#86efac', color: '#15803d', Icon: CheckCircle },
    erro: { bg: '#fef2f2', border: '#fca5a5', color: '#dc2626', Icon: AlertTriangle },
    info: { bg: '#eff6ff', border: '#93c5fd', color: '#1d4ed8', Icon: Info },
  }
  const { bg, border, color, Icon } = configs[tipo] || configs.info
  return (
    <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium"
         style={{ background: bg, border: `1px solid ${border}`, color }}>
      <Icon size={13} className="shrink-0" />
      <span className="flex-1">{msg}</span>
      {onClose && <button onClick={onClose} className="opacity-50 hover:opacity-100 ml-1"><X size={12} /></button>}
    </div>
  )
}

// ─── BADGE ───────────────────────────────────────────────────────────────────
export function Badge({ label, nivel = 'info' }) {
  const styles = {
    critico: { bg: '#fef2f2', border: '#fca5a5', color: '#b91c1c' },
    atencao: { bg: '#fffbeb', border: '#fcd34d', color: '#b45309' },
    ok:      { bg: '#f0fdf4', border: '#86efac', color: '#15803d' },
    info:    { bg: '#f8fafc', border: '#cbd5e1', color: '#64748b' },
    azul:    { bg: '#eff6ff', border: '#93c5fd', color: '#1d4ed8' },
  }[nivel] || { bg: '#f8fafc', border: '#cbd5e1', color: '#64748b' }
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ background: styles.bg, border: `1px solid ${styles.border}`, color: styles.color }}>
      {label}
    </span>
  )
}

// ─── STATUS ANIMAL ───────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const map = {
    'Lactação': { color: '#15803d', bg: '#f0fdf4', border: '#86efac' },
    'Seca':     { color: '#b45309', bg: '#fffbeb', border: '#fcd34d' },
    'Gestação': { color: '#1d4ed8', bg: '#eff6ff', border: '#93c5fd' },
    'Novilha':  { color: '#6d28d9', bg: '#f5f3ff', border: '#c4b5fd' },
    'Bezerro':  { color: '#c2410c', bg: '#fff7ed', border: '#fdba74' },
    'Vendido':  { color: '#64748b', bg: '#f8fafc', border: '#e2e8f0' },
  }
  const s = map[status] || map['Vendido']
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ color: s.color, background: s.bg, border: `1px solid ${s.border}` }}>
      {status}
    </span>
  )
}

// ─── BUTTON ──────────────────────────────────────────────────────────────────
export function Btn({ children, onClick, type = 'button', variant = 'primary', size = 'sm', disabled, className = '' }) {
  const base = 'inline-flex items-center justify-center gap-1.5 font-semibold rounded-lg transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed select-none active:scale-[0.97]'
  const sizes = { xs: 'text-xs px-2.5 py-1.5', sm: 'text-sm px-3.5 py-2', md: 'text-sm px-5 py-2.5' }
  const vars = {
    primary: { bg: T.brand, color: '#fff', hover: T.brand2 },
    ghost:   { bg: 'transparent', color: T.sub, hover: T.s3, border: T.border },
    danger:  { bg: '#fef2f2', color: '#dc2626', hover: '#fee2e2', border: '#fca5a5' },
    success: { bg: '#f0fdf4', color: '#15803d', hover: '#dcfce7', border: '#86efac' },
    outline: { bg: 'transparent', color: T.brand, hover: T.brandGlow, border: T.brand },
    blue:    { bg: '#2563eb', color: '#fff', hover: '#1d4ed8' },
  }
  const v = vars[variant] || vars.ghost
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`${base} ${sizes[size] || sizes.sm} ${className}`}
      style={{ background: v.bg, color: v.color, border: v.border ? `1px solid ${v.border}` : 'none', boxShadow: variant === 'primary' ? '0 1px 4px rgba(34,197,94,0.3)' : 'none' }}>
      {children}
    </button>
  )
}

// ─── FIELD / INPUT / SELECT / TEXTAREA ───────────────────────────────────────
export function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      {label && <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">{label}</label>}
      {children}
    </div>
  )
}
const inputBase = `w-full rounded-lg px-3 py-2.5 text-sm text-slate-800 bg-white
  border border-slate-200 focus:outline-none focus:border-green-400 focus:ring-2 focus:ring-green-100
  transition-all duration-150 placeholder-slate-400`
export function Input({ ...props }) {
  return <input {...props} className={`${inputBase} ${props.className || ''}`} style={props.style} />
}
export function Select({ children, ...props }) {
  return (
    <select {...props} className={`${inputBase} bg-white ${props.className || ''}`}>
      {children}
    </select>
  )
}
export function Textarea({ ...props }) {
  return <textarea {...props} rows={props.rows || 3} className={`${inputBase} resize-none ${props.className || ''}`} />
}

// ─── TABELA ──────────────────────────────────────────────────────────────────
export function Th({ children, className = '' }) {
  return (
    <th className={`text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500 whitespace-nowrap bg-slate-50 ${className}`}>
      {children}
    </th>
  )
}
export function Td({ children, className = '' }) {
  return <td className={`px-4 py-3 text-sm text-slate-700 ${className}`}>{children}</td>
}
export function TRow({ children, onClick, className = '' }) {
  return (
    <tr onClick={onClick}
      className={`border-b border-slate-50 transition-colors ${onClick ? 'cursor-pointer hover:bg-green-50/50' : 'hover:bg-slate-50/50'} ${className}`}>
      {children}
    </tr>
  )
}

// ─── MODAL ───────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, width = 480, accentColor }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4"
         style={{ background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)' }}
         onClick={onClose}>
      <div className="rounded-2xl flex flex-col overflow-hidden w-full bg-white"
           style={{ width, maxWidth: '95vw', maxHeight: '90vh', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 shrink-0"
             style={{ borderBottom: '1px solid #e5e7eb', background: accentColor ? accentColor : '#f9fafb' }}>
          <div className="flex items-center gap-2.5">
            {accentColor && <span className="w-3 h-3 rounded-full" style={{ background: accentColor === '#f0fdf4' ? T.brand : '#fff' }} />}
            <span className="text-[15px] font-bold" style={{ color: accentColor ? (accentColor === '#f0fdf4' ? T.text : '#fff') : T.text }}>{title}</span>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 transition-colors">
            <X size={15} />
          </button>
        </div>
        <div className="overflow-y-auto p-5 space-y-4 flex-1 bg-white">{children}</div>
      </div>
    </div>
  )
}

// ─── SECTION HEADER ──────────────────────────────────────────────────────────
export function SectionHeader({ title, sub, action }) {
  return (
    <div className="flex items-center justify-between px-5 py-3 shrink-0 bg-white"
         style={{ borderBottom: '1px solid #e5e7eb' }}>
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-1 h-4 rounded-full shrink-0" style={{ background: T.brand }} />
        <div className="min-w-0">
          <span className="text-[13px] font-bold text-slate-800 truncate">{title}</span>
          {sub && <span className="text-[11px] ml-2 text-slate-400">· {sub}</span>}
        </div>
      </div>
      {action && <div className="shrink-0 ml-4">{action}</div>}
    </div>
  )
}

// ─── EMPTY STATE ─────────────────────────────────────────────────────────────
export function Empty({ msg = 'Nenhum dado encontrado.', title, icon: Icon, action, accentColor }) {
  const color = accentColor || T.brand
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 px-6 bg-white">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
           style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
        {Icon ? <Icon size={22} style={{ color }} /> : <Database size={20} style={{ color: T.muted }} />}
      </div>
      <div className="text-center space-y-1">
        {title && <p className="text-[14px] font-bold text-slate-700">{title}</p>}
        <p className="text-[13px] leading-relaxed text-slate-500 max-w-[240px]">{msg}</p>
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}

// ─── SKELETON ────────────────────────────────────────────────────────────────
export function Skeleton({ className = '' }) {
  return <div className={`rounded-lg animate-pulse bg-slate-100 ${className}`} />
}

// ─── DELTA ───────────────────────────────────────────────────────────────────
export function Delta({ value }) {
  if (value === undefined || value === null) return null
  const pos = value >= 0
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold tabular-nums ${pos ? 'text-green-600' : 'text-red-500'}`}>
      {pos ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
      {Math.abs(value).toFixed(1)}%
    </span>
  )
}

// ─── CHART CONTROLS ──────────────────────────────────────────────────────────
export function ChartControls({ periodo, setPeriodo, tipo, setTipo, periodos = [7, 14, 30, 60, 90], tipos = ['area', 'linha', 'barra'] }) {
  const LABELS = { area: 'Área', linha: 'Linha', barra: 'Barras' }
  return (
    <div className="flex items-center justify-between gap-2 flex-wrap">
      <div className="flex items-center gap-1 rounded-lg p-0.5 bg-slate-100 border border-slate-200">
        {periodos.map(p => (
          <button key={p} onClick={() => setPeriodo(p)}
            className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all min-w-[36px]"
            style={{ background: periodo === p ? T.brand : 'transparent', color: periodo === p ? '#fff' : '#64748b' }}>
            {p}d
          </button>
        ))}
      </div>
      <div className="flex items-center gap-0.5 rounded-lg p-0.5 bg-slate-100 border border-slate-200">
        {tipos.map(t => (
          <button key={t} onClick={() => setTipo(t)}
            className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
            style={{ background: tipo === t ? '#fff' : 'transparent', color: tipo === t ? T.text : '#64748b', boxShadow: tipo === t ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}>
            {LABELS[t] || t}
          </button>
        ))}
      </div>
    </div>
  )
}
