/**
 * MilkShow — Enterprise Shell
 * Layout: sidebar (md+) + bottom nav (mobile)
 * Touch targets: mín 44px · Primary brand: verde #16a34a
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  LayoutDashboard, Stethoscope, ShieldCheck, Milk, Activity,
  Settings, ChevronLeft, ChevronRight, LogOut, Bell,
  CalendarDays, Baby, Wallet, Terminal, CircleDot, MoreHorizontal,
  X, Beef, Package, Plus, RefreshCw,
} from 'lucide-react'

import TabBI         from '../tabs/TabBI.jsx'
import TabProducao   from '../tabs/TabProducao.jsx'
import TabVet        from '../tabs/TabVet.jsx'
import TabSanidade   from '../tabs/TabSanidade.jsx'
import TabBercario   from '../tabs/TabBercario.jsx'
import TabFinanceiro from '../tabs/TabFinanceiro.jsx'
import TabConfig     from '../tabs/TabConfig.jsx'
import TabRebanho    from '../tabs/TabRebanho.jsx'
import TabArmazem    from '../tabs/TabArmazem.jsx'
import TabCalendario from '../tabs/TabCalendario.jsx'

import { api } from '../api.js'
import { Modal, Field, Input, Select, Btn, T, hoje } from '../ui.jsx'

// ─── MÓDULOS ─────────────────────────────────────────────────────────────────
const ALL_MODULES = [
  { id: 'bi',         Icon: LayoutDashboard, label: 'Dashboard',    perm: null },
  { id: 'producao',   Icon: Activity,        label: 'Produção',     perm: null },
  { id: 'rebanho',    Icon: Beef,            label: 'Rebanho',      perm: null },
  { id: 'financeiro', Icon: Wallet,          label: 'Financeiro',   perm: 'financeiro' },
  { id: 'calendario', Icon: CalendarDays,    label: 'Calendário',   perm: null },
  { id: 'armazem',    Icon: Package,         label: 'Armazém',      perm: null },
  { id: 'vet',        Icon: Stethoscope,     label: 'Veterinária',  perm: null },
  { id: 'sanidade',   Icon: ShieldCheck,     label: 'Sanidade',     perm: null },
  { id: 'bercario',   Icon: Baby,            label: 'Berçário',     perm: null },
  { id: 'config',     Icon: Settings,        label: 'Configurações',perm: 'admin' },
]

function getPermissoes() {
  try {
    const token = localStorage.getItem('milkshow_token') || ''
    if (!token) return ['admin']
    const payload = JSON.parse(atob(token.split('.')[1] + '=='))
    return payload.permissoes || ['admin']
  } catch { return ['admin'] }
}

function filtrarModulos(permissoes) {
  const isAdmin = permissoes.includes('admin')
  return ALL_MODULES.filter(m => !m.perm || isAdmin || permissoes.includes(m.perm))
}

// ─── LOG TERMINAL ─────────────────────────────────────────────────────────────
const LOG_IA = [
  { ts: '14:21:00', tipo: 'SISTEMA',  msg: 'MilkShow AI v2.1 — Sessão iniciada' },
  { ts: '14:21:03', tipo: 'SISTEMA',  msg: 'Firebase Auth validado · Fazenda: Santa Clara' },
  { ts: '14:22:47', tipo: 'ENTRADA',  msg: '"Joana 22.5L tarde, Negrinha 24L, Pintada 15.2L"' },
  { ts: '14:22:47', tipo: 'ANÁLISE',  msg: 'Identificando 3 animais em produção...' },
  { ts: '14:22:48', tipo: 'REGISTRO', msg: 'PRODUÇÃO: Joana — 22.5L (Tarde)' },
  { ts: '14:22:48', tipo: 'REGISTRO', msg: 'PRODUÇÃO: Negrinha — 24.0L (Tarde)' },
  { ts: '14:22:48', tipo: 'REGISTRO', msg: 'PRODUÇÃO: Pintada — 15.2L (Tarde)' },
  { ts: '14:22:49', tipo: 'RESUMO',   msg: 'TOTAL SESSÃO: 61.7L · RECEITA EST.: R$ 197.44' },
  { ts: '14:22:49', tipo: 'SISTEMA',  msg: 'Firestore atualizado · 3 documentos gravados' },
]

const TIPO_COR = {
  SISTEMA: 'text-slate-500', ENTRADA: 'text-blue-400',
  ANÁLISE: 'text-amber-400', REGISTRO: 'text-emerald-400', RESUMO: 'text-slate-200',
}

// ─── AI TERMINAL ──────────────────────────────────────────────────────────────
function AITerminalWidget() {
  const [open, setOpen]       = useState(false)
  const [logs, setLogs]       = useState(LOG_IA.slice(0, 3))
  const [running, setRunning] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [logs])

  async function runDemo() {
    if (running) return
    setRunning(true)
    setLogs(LOG_IA.slice(0, 3))
    for (let i = 3; i < LOG_IA.length; i++) {
      await new Promise(r => setTimeout(r, 600))
      setLogs(prev => [...prev, LOG_IA[i]])
    }
    setRunning(false)
  }

  return (
    <>
      <button onClick={() => setOpen(o => !o)} aria-label="Abrir terminal IA"
        className="fixed right-4 z-40 flex items-center gap-2 px-3.5 py-2 rounded-lg text-[11px] font-mono transition-all"
        style={{
          bottom: 'calc(env(safe-area-inset-bottom, 0px) + 72px)',
          background: '#0f172a', border: '1px solid #1e293b', color: '#64748b',
        }}>
        <Terminal size={12} className="text-blue-400" />
        <span className="hidden sm:inline">IA Terminal</span>
        {running && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />}
      </button>

      {open && (
        <div className="fixed right-4 z-50 flex flex-col rounded-xl shadow-2xl"
             style={{
               bottom: 'calc(env(safe-area-inset-bottom, 0px) + 120px)',
               width: 'min(480px, calc(100vw - 32px))', maxHeight: 380,
               background: '#030712', border: '1px solid #1e293b',
             }}>
          <div className="flex items-center justify-between px-4 py-3 shrink-0"
               style={{ borderBottom: '1px solid #1e293b' }}>
            <div className="flex items-center gap-2">
              <Terminal size={12} className="text-blue-400" />
              <span className="text-slate-400 text-[11px] font-mono">MilkShow AI — log stream</span>
              {running && <span className="flex items-center gap-1 text-emerald-500 text-[10px] font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />processando
              </span>}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={runDemo} disabled={running}
                className="text-blue-400 hover:text-blue-300 text-[10px] font-mono px-2 py-0.5 rounded border border-blue-500/30 disabled:opacity-40">
                {running ? 'SIMULANDO...' : 'SIMULAR'}
              </button>
              <button onClick={() => setOpen(false)} className="text-slate-700 hover:text-slate-400 ml-1">
                <X size={13} />
              </button>
            </div>
          </div>
          <div ref={ref} className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-1">
            {logs.map((l, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-slate-700 shrink-0 tabular-nums">{l.ts}</span>
                <span className={`shrink-0 w-16 ${TIPO_COR[l.tipo] || 'text-slate-500'}`}>[{l.tipo}]</span>
                <span className="text-slate-400 break-all">{l.msg}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

// ─── FAB — REGISTRO RÁPIDO DE PRODUÇÃO ───────────────────────────────────────
function FABProducao() {
  const [open, setOpen]       = useState(false)
  const [animais, setAnimais] = useState([])
  const [saving, setSaving]   = useState(false)
  const [toast, setToast]     = useState(null)
  const [form, setForm]       = useState({
    data: hoje(), id_animal: '', nome_animal: '', leite: '', racao: '', turno: 'manhã',
  })

  useEffect(() => {
    if (open) {
      api.animais().then(a => setAnimais(a.filter(x => x.status === 'Lactação'))).catch(() => {})
    }
  }, [open])

  function setAnimal(id) {
    const a = animais.find(x => (x.id || x.nome) === id)
    setForm(f => ({ ...f, id_animal: a?.id || id, nome_animal: a?.nome || id }))
  }

  async function salvar(e) {
    e.preventDefault()
    if (!form.nome_animal || !form.leite) return
    setSaving(true)
    try {
      await api.registrarProducao({ ...form, leite: parseFloat(form.leite), racao: parseFloat(form.racao) || 0 })
      setToast(`${form.nome_animal} — ${form.leite}L registrado`)
      setForm(f => ({ ...f, id_animal: '', nome_animal: '', leite: '', racao: '' }))
      setTimeout(() => { setOpen(false); setToast(null) }, 1500)
    } catch(err) { setToast(`Erro: ${err.message}`) }
    finally { setSaving(false) }
  }

  return (
    <>
      {/* Botão FAB */}
      <button onClick={() => setOpen(true)} aria-label="Registrar produção rápida"
        className="fixed left-4 z-40 flex items-center gap-2 px-4 py-2.5 rounded-xl text-[12px] font-semibold transition-all active:scale-95 shadow-lg"
        style={{
          bottom: 'calc(env(safe-area-inset-bottom, 0px) + 72px)',
          background: '#16a34a', color: '#fff',
          boxShadow: '0 4px 20px rgba(22,163,74,0.35)',
        }}>
        <Plus size={15} />
        <span className="hidden sm:inline">Ordenha Rápida</span>
        <span className="sm:hidden">+</span>
      </button>

      {/* Modal */}
      <Modal open={open} onClose={() => setOpen(false)} title="Registrar Ordenha">
        {toast ? (
          <div className="py-6 text-center">
            <p className="text-emerald-400 font-mono text-sm">{toast}</p>
          </div>
        ) : (
          <form onSubmit={salvar} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Data">
                <Input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} />
              </Field>
              <Field label="Turno">
                <Select value={form.turno} onChange={e => setForm(f => ({ ...f, turno: e.target.value }))}>
                  {['manhã', 'tarde', 'noite'].map(t => <option key={t}>{t}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Animal">
              <Select value={form.id_animal} onChange={e => setAnimal(e.target.value)}>
                <option value="">Selecione...</option>
                {animais.map(a => <option key={a.id || a.nome} value={a.id || a.nome}>{a.nome}</option>)}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Litros *">
                <Input type="number" step="0.1" min="0" placeholder="0.0" inputMode="decimal"
                       value={form.leite} onChange={e => setForm(f => ({ ...f, leite: e.target.value }))} />
              </Field>
              <Field label="Ração (kg)">
                <Input type="number" step="0.1" min="0" placeholder="0.0" inputMode="decimal"
                       value={form.racao} onChange={e => setForm(f => ({ ...f, racao: e.target.value }))} />
              </Field>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Btn variant="ghost" onClick={() => setOpen(false)}>Cancelar</Btn>
              <Btn type="submit" variant="primary" disabled={saving}>
                {saving ? 'Salvando...' : 'Registrar'}
              </Btn>
            </div>
          </form>
        )}
      </Modal>
    </>
  )
}

// ─── SIDEBAR (desktop md+) ────────────────────────────────────────────────────
function Sidebar({ active, setActive, collapsed, setCollapsed, onLogout, modulos }) {
  const W = collapsed ? 64 : 224
  return (
    <aside className="hidden md:flex flex-col shrink-0 transition-all duration-200"
           style={{ width: W, background: '#080e1d', borderRight: '1px solid #1e293b' }}>
      <div className="flex items-center gap-3 px-3.5 py-0"
           style={{ borderBottom: '1px solid #1e293b', height: 60 }}>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
             style={{ background: '#0f172a', border: '1px solid #16a34a33' }}>
          <Milk size={14} className="text-emerald-500" />
        </div>
        {!collapsed && (
          <div className="min-w-0 leading-tight">
            <span className="text-slate-100 font-semibold text-sm tracking-tight">MilkShow</span>
            <span className="block text-emerald-600 text-[9px] font-mono tracking-widest uppercase">Enterprise</span>
          </div>
        )}
      </div>

      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
        {modulos.map(({ id, Icon, label }) => {
          const isActive = active === id
          return (
            <button key={id} onClick={() => setActive(id)} aria-label={label}
              title={collapsed ? label : undefined}
              className="w-full flex items-center gap-3 px-2.5 rounded-lg transition-all duration-100 text-left group"
              style={{
                minHeight: 44,
                background:  isActive ? 'rgba(22,163,74,0.12)' : 'transparent',
                borderLeft:  isActive ? '2px solid #16a34a' : '2px solid transparent',
              }}>
              <Icon size={15} className={isActive ? 'text-emerald-400 shrink-0' : 'text-slate-600 group-hover:text-slate-400 shrink-0'} />
              {!collapsed && (
                <span className={`text-[13px] font-medium truncate ${isActive ? 'text-emerald-300' : 'text-slate-500 group-hover:text-slate-300'}`}>
                  {label}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      <div className="px-2 py-2 space-y-0.5" style={{ borderTop: '1px solid #1e293b' }}>
        <button onClick={() => setCollapsed(c => !c)}
          className="w-full flex items-center gap-3 px-2.5 rounded-lg text-slate-600 hover:text-slate-400 transition-colors"
          style={{ minHeight: 40 }}>
          {collapsed ? <ChevronRight size={15} /> : <><ChevronLeft size={15} /><span className="text-[13px]">Recolher</span></>}
        </button>
        <button onClick={onLogout}
          className="w-full flex items-center gap-3 px-2.5 rounded-lg text-slate-600 hover:text-red-400 transition-colors"
          style={{ minHeight: 40 }}>
          <LogOut size={15} />
          {!collapsed && <span className="text-[13px]">Sair</span>}
        </button>
      </div>
    </aside>
  )
}

// ─── BOTTOM NAV (mobile < md) ─────────────────────────────────────────────────
function BottomNav({ active, setActive, modulos }) {
  const [maisOpen, setMaisOpen] = useState(false)
  const bottomNav = modulos.filter(m => ['bi', 'producao', 'rebanho', 'calendario'].includes(m.id))
  const overflow  = modulos.filter(m => !['bi', 'producao', 'rebanho', 'calendario'].includes(m.id))

  function selectModule(id) { setActive(id); setMaisOpen(false) }

  return (
    <>
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 flex items-stretch"
           style={{
             background: 'rgba(8,14,29,0.97)', borderTop: '1px solid #1e293b',
             backdropFilter: 'blur(12px)', paddingBottom: 'env(safe-area-inset-bottom, 0px)',
           }}>
        {bottomNav.map(({ id, Icon, label }) => {
          const isActive = active === id
          return (
            <button key={id} onClick={() => selectModule(id)} aria-label={label}
              className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-all relative"
              style={{ minHeight: 60 }}>
              <Icon size={20} className={isActive ? 'text-emerald-400' : 'text-slate-600'} />
              <span className={`text-[10px] font-medium ${isActive ? 'text-emerald-400' : 'text-slate-600'}`}>
                {label}
              </span>
              {isActive && <span className="absolute top-0 w-6 h-0.5 rounded-b-full bg-emerald-500" />}
            </button>
          )
        })}
        {overflow.length > 0 && (
          <button onClick={() => setMaisOpen(o => !o)} aria-label="Mais módulos"
            className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-all"
            style={{ minHeight: 60 }}>
            <MoreHorizontal size={20} className={overflow.some(m => m.id === active) ? 'text-emerald-400' : 'text-slate-600'} />
            <span className={`text-[10px] font-medium ${overflow.some(m => m.id === active) ? 'text-emerald-400' : 'text-slate-600'}`}>
              Mais
            </span>
          </button>
        )}
      </nav>

      {maisOpen && (
        <div className="md:hidden fixed inset-0 z-40" onClick={() => setMaisOpen(false)}>
          <div className="absolute bottom-0 left-0 right-0 rounded-t-2xl overflow-hidden"
               style={{ background: '#0f172a', border: '1px solid #1e293b',
                        paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 60px)' }}
               onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid #1e293b' }}>
              <span className="text-slate-400 text-sm font-semibold">Mais módulos</span>
              <button onClick={() => setMaisOpen(false)} className="text-slate-600 hover:text-slate-300 p-1">
                <X size={16} />
              </button>
            </div>
            <div className="p-4 space-y-1">
              {overflow.map(({ id, Icon, label }) => {
                const isActive = active === id
                return (
                  <button key={id} onClick={() => selectModule(id)}
                    className="w-full flex items-center gap-4 px-4 rounded-xl transition-all"
                    style={{ minHeight: 52, background: isActive ? 'rgba(22,163,74,0.12)' : 'transparent' }}>
                    <Icon size={18} className={isActive ? 'text-emerald-400' : 'text-slate-500'} />
                    <span className={`text-sm font-medium ${isActive ? 'text-emerald-300' : 'text-slate-400'}`}>
                      {label}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

// ─── HEADER ──────────────────────────────────────────────────────────────────
function Header({ modulo, modulos, onRefresh }) {
  const mod  = modulos.find(m => m.id === modulo)
  const user = (() => { try { return JSON.parse(localStorage.getItem('milkshow_user') || '{}') } catch { return {} } })()
  const initials = (user.nome || 'SC').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  const data = new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })

  return (
    <header className="flex items-center justify-between px-5 shrink-0"
      style={{ height: 60, borderBottom: '1px solid #1e293b', background: '#020617' }}>
      <div className="flex items-center gap-2.5 min-w-0">
        {mod?.Icon && <mod.Icon size={15} className="text-slate-500 shrink-0" />}
        <span className="text-slate-200 font-semibold text-sm">{mod?.label || 'Dashboard'}</span>
        <span className="text-slate-700 text-xs hidden sm:inline">/</span>
        <span className="text-slate-600 text-xs font-mono hidden sm:inline truncate">{user.nome || 'Fazenda'}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-slate-600 text-xs font-mono hidden md:inline">{data}</span>
        <button onClick={onRefresh} aria-label="Atualizar dados"
          className="p-1.5 rounded-lg text-slate-600 hover:text-slate-300 transition-colors">
          <RefreshCw size={14} />
        </button>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center"
             style={{ background: '#0f172a', border: '1px solid #1e293b' }}>
          <span className="text-slate-400 text-[10px] font-mono font-bold">{initials}</span>
        </div>
      </div>
    </header>
  )
}

// ─── MAIN ─────────────────────────────────────────────────────────────────────
export default function Enterprise() {
  const [modulo, setModulo]       = useState('bi')
  const [collapsed, setCollapsed] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const permissoes = getPermissoes()
  const modulos    = filtrarModulos(permissoes)

  // Garante que o módulo ativo seja acessível
  useEffect(() => {
    if (!modulos.find(m => m.id === modulo)) {
      setModulo(modulos[0]?.id || 'bi')
    }
  }, [modulos, modulo])

  function handleLogout() {
    localStorage.removeItem('milkshow_token')
    localStorage.removeItem('milkshow_user')
    window.location.href = '/app/login'
  }

  function forceRefresh() { setRefreshKey(k => k + 1) }

  // Auto-refresh a cada 90s — muda a key para forçar remount das tabs
  useEffect(() => {
    const id = setInterval(forceRefresh, 90000)
    return () => clearInterval(id)
  }, [])

  const TAB_MAP = {
    bi:         <TabBI         key={`bi-${refreshKey}`} />,
    producao:   <TabProducao   key={`producao-${refreshKey}`} />,
    rebanho:    <TabRebanho    key={`rebanho-${refreshKey}`} />,
    financeiro: <TabFinanceiro key={`financeiro-${refreshKey}`} />,
    calendario: <TabCalendario key={`calendario-${refreshKey}`} />,
    armazem:    <TabArmazem    key={`armazem-${refreshKey}`} />,
    vet:        <TabVet        key={`vet-${refreshKey}`} />,
    sanidade:   <TabSanidade   key={`sanidade-${refreshKey}`} />,
    bercario:   <TabBercario   key={`bercario-${refreshKey}`} />,
    config:     <TabConfig     key={`config-${refreshKey}`} />,
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden"
         style={{ background: '#020617', fontFamily: "'Inter', system-ui, sans-serif" }}>

      <Sidebar
        active={modulo} setActive={setModulo}
        collapsed={collapsed} setCollapsed={setCollapsed}
        onLogout={handleLogout} modulos={modulos}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header modulo={modulo} modulos={modulos} onRefresh={forceRefresh} />

        <main className="flex-1 overflow-hidden flex flex-col"
              style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
          <div className="flex-1 overflow-hidden flex flex-col md:pb-0 pb-[60px]">
            {TAB_MAP[modulo]}
          </div>
        </main>
      </div>

      <BottomNav active={modulo} setActive={setModulo} modulos={modulos} />
      <AITerminalWidget />
      <FABProducao />
    </div>
  )
}
