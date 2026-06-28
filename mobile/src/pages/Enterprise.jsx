/**
 * MilkShow Enterprise — Shell v3
 * Estilo inspirado no Leigado: top bar verde + sidebar branca + conteúdo cinza claro
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  LayoutDashboard, Stethoscope, ShieldCheck, Milk, Activity,
  Settings, LogOut, Bell, CalendarDays, Wallet,
  MessageCircle, X, Package, Plus, ChevronLeft, ChevronRight,
  Check, ArrowUp, Cpu, Menu, Building2, ChevronDown, MoreVertical,
  Zap, PawPrint, FlaskConical, Trophy,
} from 'lucide-react'
import { IconBezerro } from '../components/IconBezerro.jsx'
import { IconRebanho } from '../components/IconRebanho.jsx'

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
import TabNutricao   from '../tabs/TabNutricao.jsx'
import TabRanking    from '../tabs/TabRanking.jsx'

import { api } from '../api.js'
import { Modal, Field, Input, Select, Btn, hoje } from '../ui.jsx'

// ─── CORES ────────────────────────────────────────────────────────────────────
const C = {
  brand:    '#22c55e',
  brand2:   '#16a34a',
  brandBg:  '#f0fdf4',
  brandLight: 'rgba(34,197,94,0.12)',
  sidebar:  '#ffffff',
  topbar:   '#22c55e',
  bg:       '#f1f4f1',
  border:   '#e8ede8',
  text:     '#1a2e1a',
  sub:      '#4a6741',
  muted:    '#8aaa85',
  surface:  '#ffffff',
  dark:     '#0f1f0f',
}

// ─── MÓDULOS ──────────────────────────────────────────────────────────────────
const ALL_MODULES = [
  { id: 'bi',         Icon: LayoutDashboard, label: 'Dashboard'    },
  { id: 'producao',   Icon: Activity,        label: 'Produção'     },
  { id: 'rebanho',    Icon: IconRebanho,     label: 'Rebanho'      },
  { id: 'financeiro', Icon: Wallet,          label: 'Financeiro',  perm: 'financeiro' },
  { id: 'calendario', Icon: CalendarDays,    label: 'Calendário'   },
  { id: 'armazem',    Icon: Package,         label: 'Armazém'      },
  { id: 'vet',        Icon: Stethoscope,     label: 'Veterinária'  },
  { id: 'sanidade',   Icon: ShieldCheck,     label: 'Sanidade'     },
  { id: 'bercario',   Icon: IconBezerro,     label: 'Bezerros'     },
  { id: 'nutricao',   Icon: FlaskConical,    label: 'Nutrição'     },
  { id: 'ranking',    Icon: Trophy,          label: 'Rankings'     },
  { id: 'config',     Icon: Settings,        label: 'Configurações', perm: 'admin' },
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

// ─── HOOK DRAG ────────────────────────────────────────────────────────────────
function useDraggable(storageKey, defaultPos) {
  const [pos, setPos] = useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey)) || defaultPos }
    catch { return defaultPos }
  })
  const dragging = useRef(false)
  const origin   = useRef({ mx: 0, my: 0, px: 0, py: 0 })

  const onMouseDown = useCallback((e) => {
    if (e.button !== 0) return
    dragging.current = true
    origin.current = { mx: e.clientX, my: e.clientY, px: pos.x, py: pos.y }
    e.preventDefault()
  }, [pos])

  const onTouchStart = useCallback((e) => {
    dragging.current = true
    const t = e.touches[0]
    origin.current = { mx: t.clientX, my: t.clientY, px: pos.x, py: pos.y }
  }, [pos])

  useEffect(() => {
    function move(mx, my) {
      if (!dragging.current) return
      const dx = mx - origin.current.mx
      const dy = my - origin.current.my
      const newPos = {
        x: Math.max(0, Math.min(window.innerWidth  - 60, origin.current.px + dx)),
        y: Math.max(0, Math.min(window.innerHeight - 60, origin.current.py + dy)),
      }
      setPos(newPos)
      localStorage.setItem(storageKey, JSON.stringify(newPos))
    }
    function end() { dragging.current = false }
    const mm = e => move(e.clientX, e.clientY)
    const tm = e => { const t = e.touches[0]; move(t.clientX, t.clientY) }
    window.addEventListener('mousemove', mm)
    window.addEventListener('mouseup',   end)
    window.addEventListener('touchmove', tm, { passive: true })
    window.addEventListener('touchend',  end)
    return () => {
      window.removeEventListener('mousemove', mm)
      window.removeEventListener('mouseup',   end)
      window.removeEventListener('touchmove', tm)
      window.removeEventListener('touchend',  end)
    }
  }, [storageKey])

  return { pos, onMouseDown, onTouchStart }
}

// ─── CHAT IA (estilo WhatsApp) ────────────────────────────────────────────────
function ChatWidget() {
  const [open, setOpen]       = useState(false)
  const [msgs, setMsgs]       = useState([
    { de: 'bot', texto: '👋 Olá! Sou o assistente MilkShow.\nDigite algo como "Joana 22L manhã" ou "qual meu saldo?"' }
  ])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)
  const inputRef  = useRef(null)

  const { pos, onMouseDown, onTouchStart } = useDraggable('chat-pos', {
    x: typeof window !== 'undefined' ? window.innerWidth - 72 : 300,
    y: typeof window !== 'undefined' ? window.innerHeight - 140 : 500,
  })

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [msgs, open])

  async function enviar(e) {
    e?.preventDefault()
    const texto = input.trim()
    if (!texto || loading) return
    setInput('')
    setMsgs(m => [...m, { de: 'user', texto }])
    setLoading(true)
    try {
      const { resposta } = await api.chat(texto)
      const textoFinal = resposta === '__botoes_enviados__'
        ? '✅ Ação processada! Recarregue o tab para ver as mudanças.'
        : resposta
      setMsgs(m => [...m, { de: 'bot', texto: textoFinal }])
    } catch(err) {
      setMsgs(m => [...m, { de: 'bot', texto: `Erro: ${err.message}` }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar() }
  }

  return (
    <>
      {/* Botão flutuante */}
      <button
        aria-label="Chat IA"
        onMouseDown={onMouseDown}
        onTouchStart={onTouchStart}
        onClick={() => setOpen(o => !o)}
        className="fixed z-40 w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-transform active:scale-95 select-none"
        style={{
          left: pos.x, top: pos.y,
          background: `linear-gradient(135deg, ${C.brand2}, ${C.brand})`,
          boxShadow: '0 4px 20px rgba(34,197,94,0.4)',
          cursor: 'grab',
        }}>
        <MessageCircle size={20} color="#fff" />
        {loading && (
          <span className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-white animate-pulse border-2 border-green-500" />
        )}
      </button>

      {/* Painel chat */}
      {open && (
        <div className="fixed z-50 flex flex-col rounded-2xl overflow-hidden shadow-2xl"
             style={{
               left: Math.min(pos.x, window.innerWidth - 360),
               top:  Math.max(8, pos.y - 460),
               width: 'min(340px, calc(100vw - 24px))',
               height: 440,
               background: '#fff',
               border: `1px solid ${C.border}`,
               boxShadow: '0 24px 64px rgba(0,0,0,0.15)',
             }}>

          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 shrink-0 cursor-grab active:cursor-grabbing"
            onMouseDown={onMouseDown} onTouchStart={onTouchStart}
            style={{ background: `linear-gradient(135deg, ${C.brand2}, ${C.brand})` }}>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Cpu size={15} color="#fff" />
              </div>
              <div>
                <p className="text-[13px] font-bold text-white leading-tight">MilkShow IA</p>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-white/80 animate-pulse" />
                  <span className="text-[10px] text-white/80">online</span>
                </div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white transition-colors">
              <X size={16} />
            </button>
          </div>

          {/* Mensagens */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2"
               style={{ background: '#f8faf8' }}>
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.de === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.de === 'bot' && (
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center shrink-0 mr-1.5 mt-auto">
                    <Milk size={12} className="text-green-600" />
                  </div>
                )}
                <div className={`max-w-[78%] px-3 py-2 rounded-2xl text-[12px] leading-relaxed whitespace-pre-wrap break-words ${
                  m.de === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
                }`}
                  style={{
                    background: m.de === 'user'
                      ? `linear-gradient(135deg, ${C.brand2}, ${C.brand})`
                      : '#ffffff',
                    color: m.de === 'user' ? '#fff' : '#374151',
                    border: m.de === 'bot' ? '1px solid #e5e7eb' : 'none',
                    boxShadow: m.de === 'bot' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                  }}>
                  {m.texto}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center shrink-0 mr-1.5">
                  <Milk size={12} className="text-green-600" />
                </div>
                <div className="px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1 bg-white border border-slate-100">
                  {[0,1,2].map(i => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce"
                          style={{ animationDelay: `${i*150}ms` }} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form onSubmit={enviar} className="flex items-end gap-2 px-3 py-3 shrink-0 bg-white"
                style={{ borderTop: '1px solid #f0f0f0' }}>
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ex: Joana 22L manhã..."
              className="flex-1 resize-none text-[13px] text-slate-700 placeholder-slate-400 bg-slate-50 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-200 border border-slate-200"
              style={{ minHeight: 36, maxHeight: 96, lineHeight: '1.5' }}
            />
            <button type="submit" disabled={!input.trim() || loading}
              className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all active:scale-90 disabled:opacity-40"
              style={{ background: `linear-gradient(135deg, ${C.brand2}, ${C.brand})` }}>
              <ArrowUp size={14} color="#fff" />
            </button>
          </form>
        </div>
      )}
    </>
  )
}

// ─── FAB ORDENHA RÁPIDA ───────────────────────────────────────────────────────
function FABOrdenha() {
  const [open, setOpen]       = useState(false)
  const [animais, setAnimais] = useState([])
  const [saving, setSaving]   = useState(false)
  const [toast, setToast]     = useState(null)
  const [form, setForm]       = useState({
    data: hoje(), id_animal: '', nome_animal: '', leite: '', racao: '', turno: 'manhã',
  })

  const { pos, onMouseDown, onTouchStart } = useDraggable('fab-pos', {
    x: typeof window !== 'undefined' ? window.innerWidth / 2 - 70 : 300,
    y: typeof window !== 'undefined' ? window.innerHeight - 110 : 500,
  })

  const downTime = useRef(0)

  function handleDown(e) {
    downTime.current = Date.now()
    onMouseDown(e)
  }
  function handleClick() {
    if (Date.now() - downTime.current < 200) setOpen(true)
  }

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
      <button
        aria-label="Nova Ordenha"
        onMouseDown={handleDown}
        onTouchStart={e => { downTime.current = Date.now(); onTouchStart(e) }}
        onClick={handleClick}
        className="fixed z-40 flex items-center gap-2 px-4 py-2.5 rounded-full text-[13px] font-bold shadow-lg transition-all active:scale-95 select-none"
        style={{
          left: pos.x, top: pos.y,
          background: `linear-gradient(135deg, ${C.brand2}, ${C.brand})`,
          color: '#fff',
          boxShadow: '0 4px 20px rgba(34,197,94,0.4)',
          cursor: 'grab',
        }}>
        <Plus size={16} strokeWidth={2.5} />
        <span>Nova Ordenha</span>
      </button>

      <Modal open={open} onClose={() => setOpen(false)} title="Registrar Ordenha"
             accentColor={`linear-gradient(135deg, ${C.brand2}, ${C.brand})`}>
        {toast ? (
          <div className="py-8 text-center">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-3">
              <Check size={20} className="text-green-600" />
            </div>
            <p className="text-[14px] font-semibold text-green-700">{toast}</p>
          </div>
        ) : (
          <form onSubmit={salvar} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
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
                <option value="">Selecione o animal...</option>
                {animais.map(a => <option key={a.id || a.nome} value={a.id || a.nome}>{a.nome}</option>)}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
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

// ─── SIDEBAR (desktop) ────────────────────────────────────────────────────────
function Sidebar({ active, setActive, collapsed, setCollapsed, onLogout, modulos }) {
  const user = (() => { try { return JSON.parse(localStorage.getItem('milkshow_user') || '{}') } catch { return {} } })()
  const initials = (user.nome || 'MS').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  return (
    <aside
      className="hidden md:flex flex-col shrink-0 transition-all duration-200"
      style={{
        width: collapsed ? 64 : 200,
        background: C.sidebar,
        borderRight: `1px solid ${C.border}`,
      }}>

      {/* Logo — mesma altura do top bar */}
      <div className="flex items-center justify-center"
           style={{ height: 56, borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2">
          <img src="/app/logo.png" alt="MilkShow"
               className="shrink-0 object-contain"
               style={{ width: collapsed ? 36 : 36, height: 36 }} />
          {!collapsed && (
            <div className="leading-tight min-w-0">
              <div className="text-[15px] font-extrabold tracking-tight truncate" style={{ color: C.text }}>MilkShow</div>
              <div className="text-[9px] font-bold uppercase tracking-widest" style={{ color: C.brand }}>Enterprise</div>
            </div>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-px px-2 overflow-y-auto">
        {modulos.map(({ id, Icon, label }) => {
          const isActive = active === id
          return (
            <button key={id} onClick={() => setActive(id)} aria-label={label}
              title={collapsed ? label : undefined}
              className="w-full flex items-center gap-3 px-2.5 rounded-lg text-left transition-all duration-150"
              style={{
                minHeight: 40,
                background: isActive ? C.brandBg : 'transparent',
                color: isActive ? C.brand2 : C.sub,
                fontWeight: isActive ? 600 : 400,
                borderLeft: isActive ? `3px solid ${C.brand}` : '3px solid transparent',
              }}>
              <Icon size={17} className="shrink-0" style={{ color: isActive ? C.brand : C.muted }} />
              {!collapsed && (
                <span className="text-[13px] truncate">{label}</span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-2 py-3 space-y-1" style={{ borderTop: `1px solid ${C.border}` }}>
        {!collapsed && (
          <div className="flex items-center gap-2 px-2.5 py-2 rounded-lg mb-1"
               style={{ background: '#f8faf8' }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold text-white"
                 style={{ background: C.brand }}>
              {initials}
            </div>
            <span className="text-[12px] font-medium truncate" style={{ color: C.text }}>{user.nome || 'Usuário'}</span>
          </div>
        )}
        <button onClick={() => setCollapsed(c => !c)}
          className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors hover:bg-slate-50"
          style={{ color: C.muted }}>
          {collapsed ? <ChevronRight size={15} /> : <><ChevronLeft size={15} /><span className="text-[12px]">Recolher</span></>}
        </button>
        <button onClick={onLogout}
          className="w-full flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors hover:bg-red-50 group"
          style={{ color: C.muted }}>
          <LogOut size={15} className="group-hover:text-red-500 transition-colors" />
          {!collapsed && <span className="text-[12px] group-hover:text-red-500 transition-colors">Sair</span>}
        </button>
      </div>
    </aside>
  )
}

// ─── TOP BAR ──────────────────────────────────────────────────────────────────
function TopBar({ active, modulos, fazenda, onFazendaClick, onOpenNav, onLogout }) {
  const modulo = modulos.find(m => m.id === active)
  const user = (() => { try { return JSON.parse(localStorage.getItem('milkshow_user') || '{}') } catch { return {} } })()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="flex items-center gap-3 px-4 shrink-0 z-20"
            style={{ height: 56, background: C.topbar, boxShadow: '0 2px 8px rgba(34,197,94,0.25)' }}>

      {/* Mobile: menu burger */}
      <button className="md:hidden text-white/90 hover:text-white" onClick={onOpenNav}>
        <Menu size={20} />
      </button>

      {/* Título do módulo atual */}
      <div className="flex-1 min-w-0">
        <span className="text-[16px] font-bold text-white tracking-tight">
          {modulo?.label || 'MilkShow'}
        </span>
      </div>

      {/* Seletor de fazenda */}
      <button onClick={onFazendaClick}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-semibold text-white/90 hover:text-white hover:bg-white/10 transition-colors">
        <Building2 size={14} />
        <span className="max-w-[120px] truncate">{fazenda || 'Minha Fazenda'}</span>
        <ChevronDown size={12} />
      </button>

      {/* Sino de notificações */}
      <button className="w-8 h-8 rounded-full flex items-center justify-center text-white/80 hover:text-white hover:bg-white/10 transition-colors">
        <Bell size={16} />
      </button>

      {/* Avatar + menu */}
      <div className="relative">
        <button onClick={() => setMenuOpen(o => !o)}
          className="w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-bold text-green-700 transition-all hover:ring-2 hover:ring-white/40"
          style={{ background: '#fff' }}>
          {(user.nome || 'MS').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
        </button>
        {menuOpen && (
          <div className="absolute right-0 top-10 rounded-xl shadow-xl bg-white border border-slate-100 py-1 min-w-[160px] z-50"
               style={{ boxShadow: '0 8px 32px rgba(0,0,0,0.12)' }}>
            <div className="px-3 py-2 border-b border-slate-50">
              <p className="text-[12px] font-semibold text-slate-700 truncate">{user.nome || 'Usuário'}</p>
              <p className="text-[11px] text-slate-400 truncate">{user.email || ''}</p>
            </div>
            <button onClick={() => { setMenuOpen(false); onLogout() }}
              className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-red-500 hover:bg-red-50 transition-colors">
              <LogOut size={14} /> Sair
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

// ─── BOTTOM NAV (mobile) ──────────────────────────────────────────────────────
function BottomNav({ active, setActive, modulos }) {
  const [maisOpen, setMaisOpen] = useState(false)
  const pinned   = modulos.filter(m => ['bi','producao','rebanho','calendario'].includes(m.id))
  const overflow = modulos.filter(m => !['bi','producao','rebanho','calendario'].includes(m.id))
  const hasOverflowActive = overflow.some(m => m.id === active)

  function select(id) { setActive(id); setMaisOpen(false) }

  return (
    <>
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 flex items-stretch bg-white"
           style={{ borderTop: `1px solid ${C.border}`, paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
        {pinned.map(({ id, Icon, label }) => {
          const isActive = active === id
          return (
            <button key={id} onClick={() => select(id)} aria-label={label}
              className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 relative transition-colors"
              style={{ minHeight: 58 }}>
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full"
                      style={{ background: C.brand }} />
              )}
              <Icon size={19} style={{ color: isActive ? C.brand : C.muted }} />
              <span className="text-[10px] font-medium" style={{ color: isActive ? C.brand : C.muted }}>
                {label}
              </span>
            </button>
          )
        })}

        {/* Mais */}
        {overflow.length > 0 && (
          <button onClick={() => setMaisOpen(o => !o)}
            className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 relative"
            style={{ minHeight: 58 }}>
            {hasOverflowActive && (
              <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full"
                    style={{ background: C.brand }} />
            )}
            <MoreVertical size={19} style={{ color: hasOverflowActive ? C.brand : C.muted }} />
            <span className="text-[10px] font-medium" style={{ color: hasOverflowActive ? C.brand : C.muted }}>Mais</span>
          </button>
        )}
      </nav>

      {/* Drawer overflow */}
      {maisOpen && (
        <div className="md:hidden fixed inset-0 z-40" onClick={() => setMaisOpen(false)}>
          <div className="absolute bottom-16 left-0 right-0 bg-white rounded-t-2xl shadow-2xl"
               style={{ border: `1px solid ${C.border}` }}
               onClick={e => e.stopPropagation()}>
            <div className="w-10 h-1 bg-slate-200 rounded-full mx-auto mt-3 mb-2" />
            <div className="grid grid-cols-3 gap-2 p-4">
              {overflow.map(({ id, Icon, label }) => {
                const isActive = active === id
                return (
                  <button key={id} onClick={() => select(id)}
                    className="flex flex-col items-center gap-2 p-3 rounded-xl transition-colors"
                    style={{ background: isActive ? C.brandBg : '#f8faf8' }}>
                    <Icon size={20} style={{ color: isActive ? C.brand : C.muted }} />
                    <span className="text-[11px] font-medium text-center leading-tight"
                          style={{ color: isActive ? C.brand2 : C.sub }}>
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

// ─── MOBILE NAV DRAWER ────────────────────────────────────────────────────────
function MobileDrawer({ open, onClose, active, setActive, onLogout, modulos }) {
  if (!open) return null
  const user = (() => { try { return JSON.parse(localStorage.getItem('milkshow_user') || '{}') } catch { return {} } })()
  return (
    <div className="md:hidden fixed inset-0 z-50" onClick={onClose}>
      <div className="absolute left-0 top-0 bottom-0 w-64 bg-white flex flex-col shadow-2xl"
           onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3"
             style={{ background: C.topbar }}>
          <div className="flex items-center gap-2">
            <img src="/app/logo.png" alt="MilkShow" className="w-8 h-8 object-contain" />
            <span className="text-[15px] font-bold text-white">MilkShow</span>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-2 px-2 overflow-y-auto space-y-px">
          {modulos.map(({ id, Icon, label }) => {
            const isActive = active === id
            return (
              <button key={id} onClick={() => { setActive(id); onClose() }}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors"
                style={{
                  background: isActive ? C.brandBg : 'transparent',
                  color: isActive ? C.brand2 : C.sub,
                  borderLeft: isActive ? `3px solid ${C.brand}` : '3px solid transparent',
                }}>
                <Icon size={18} style={{ color: isActive ? C.brand : C.muted }} />
                <span className="text-[14px] font-medium">{label}</span>
              </button>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-slate-100">
          <div className="flex items-center gap-2 px-2 py-2 rounded-lg bg-slate-50 mb-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-bold text-white"
                 style={{ background: C.brand }}>
              {(user.nome || 'MS').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
            </div>
            <div>
              <p className="text-[13px] font-semibold text-slate-700">{user.nome || 'Usuário'}</p>
              <p className="text-[11px] text-slate-400">{user.email || ''}</p>
            </div>
          </div>
          <button onClick={() => { onLogout(); onClose() }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-red-500 hover:bg-red-50 transition-colors">
            <LogOut size={15} />
            <span className="text-[13px] font-medium">Sair</span>
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── TAB CONTENT WRAPPER ──────────────────────────────────────────────────────
function TabContent({ active, fazendaId }) {
  const props = { fazendaId }
  switch (active) {
    case 'bi':         return <TabBI         {...props} />
    case 'producao':   return <TabProducao   {...props} />
    case 'rebanho':    return <TabRebanho    {...props} />
    case 'financeiro': return <TabFinanceiro {...props} />
    case 'calendario': return <TabCalendario {...props} />
    case 'armazem':    return <TabArmazem    {...props} />
    case 'vet':        return <TabVet        {...props} />
    case 'sanidade':   return <TabSanidade   {...props} />
    case 'bercario':   return <TabBercario   {...props} />
    case 'nutricao':   return <TabNutricao   {...props} />
    case 'ranking':    return <TabRanking    {...props} />
    case 'config':     return <TabConfig     {...props} />
    default:           return null
  }
}

// ─── APP SHELL ────────────────────────────────────────────────────────────────
export default function Enterprise({ user, fazendaId, fazendaNome, onLogout }) {
  const permissoes = getPermissoes()
  const modulos    = filtrarModulos(permissoes)

  const [active,    setActive]    = useState('bi')
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    function close(e) {
      if (!e.target.closest('[data-menu]')) {}
    }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [])

  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ background: C.bg }}>

      {/* Sidebar desktop */}
      <Sidebar
        active={active}
        setActive={setActive}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        onLogout={onLogout}
        modulos={modulos}
      />

      {/* Drawer mobile */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        active={active}
        setActive={setActive}
        onLogout={onLogout}
        modulos={modulos}
      />

      {/* Coluna principal */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Top bar */}
        <TopBar
          active={active}
          modulos={modulos}
          fazenda={fazendaNome}
          onFazendaClick={() => setActive('config')}
          onOpenNav={() => setDrawerOpen(true)}
          onLogout={onLogout}
        />

        {/* Conteúdo dos tabs */}
        <main className="flex-1 overflow-y-auto pb-16 md:pb-0"
              style={{ background: C.bg, width: '100%', minWidth: 0 }}>
          <TabContent active={active} fazendaId={fazendaId} />
        </main>

        {/* Bottom nav mobile */}
        <BottomNav active={active} setActive={setActive} modulos={modulos} />
      </div>

      {/* FAB Nova Ordenha */}
      <FABOrdenha />

      {/* Chat IA */}
      <ChatWidget />
    </div>
  )
}
