import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, AlertTriangle, CheckCircle, Milk } from 'lucide-react'
import { api } from '../api.js'
import { signInWithGoogle, signInWithEmail, createAccountWithEmail, resetPassword } from '../firebase.js'

// Traduz erros do Firebase para português
function traduzirErro(code) {
  const map = {
    'auth/invalid-email':            'E-mail inválido.',
    'auth/user-not-found':           'Usuário não encontrado.',
    'auth/wrong-password':           'Senha incorreta.',
    'auth/invalid-credential':       'E-mail ou senha incorretos.',
    'auth/too-many-requests':        'Muitas tentativas. Tente novamente em alguns minutos.',
    'auth/email-already-in-use':     'Este e-mail já está cadastrado.',
    'auth/weak-password':            'Senha fraca. Use no mínimo 6 caracteres.',
    'auth/network-request-failed':   'Sem conexão. Verifique sua internet.',
    'auth/popup-closed-by-user':     'Login cancelado.',
  }
  return map[code] || 'Erro inesperado. Tente novamente.'
}

function salvarSessao(data) {
  localStorage.setItem('milkshow_token', data.token)
  localStorage.setItem('milkshow_user', JSON.stringify({
    nome: data.nome,
    fazenda_id: data.fazenda_id,
  }))
}

export default function Login() {
  const [modo, setModo]         = useState('login')   // 'login' | 'cadastro' | 'reset'
  const [email, setEmail]       = useState('')
  const [senha, setSenha]       = useState('')
  const [confirmSenha, setConfirmSenha] = useState('')
  const [erro, setErro]         = useState('')
  const [info, setInfo]         = useState('')
  const [loading, setLoading]   = useState(false)
  const [showSenha, setShowSenha] = useState(false)
  const nav = useNavigate()

  async function handleFirebaseAuth(getToken) {
    setLoading(true); setErro(''); setInfo('')
    try {
      const idToken = await getToken()
      const data    = await api.googleLogin(idToken)   // endpoint aceita qualquer Firebase token
      salvarSessao(data)
      nav('/', { replace: true })
    } catch (err) {
      const code = err.code || ''
      setErro(traduzirErro(code) || err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleEmail(e) {
    e.preventDefault()
    if (!email.trim()) { setErro('Informe seu e-mail.'); return }
    if (!senha)        { setErro('Informe sua senha.'); return }
    handleFirebaseAuth(() => signInWithEmail(email.trim(), senha))
  }

  function handleCadastro(e) {
    e.preventDefault()
    if (!email.trim()) { setErro('Informe seu e-mail.'); return }
    if (senha.length < 6) { setErro('A senha deve ter no mínimo 6 caracteres.'); return }
    if (senha !== confirmSenha) { setErro('As senhas não coincidem.'); return }
    handleFirebaseAuth(() => createAccountWithEmail(email.trim(), senha))
  }

  async function handleReset(e) {
    e.preventDefault()
    if (!email.trim()) { setErro('Informe seu e-mail para continuar.'); return }
    setLoading(true); setErro('')
    try {
      await resetPassword(email.trim())
      setInfo('E-mail de redefinição enviado! Verifique sua caixa de entrada.')
      setModo('login')
    } catch (err) {
      setErro(traduzirErro(err.code))
    } finally {
      setLoading(false)
    }
  }

  function trocarModo(novoModo) {
    setModo(novoModo)
    setErro(''); setInfo(''); setSenha(''); setConfirmSenha('')
  }

  const inputCls = `
    w-full bg-white/[0.06] border border-white/15 rounded-xl px-4 py-3.5
    text-white placeholder-white/25 text-sm
    focus:outline-none focus:border-emerald-500/70 focus:bg-white/10
    transition-all duration-200
  `

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #0d2318 50%, #0f172a 100%)' }}
    >
      {/* Orbes decorativos */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full opacity-10 blur-3xl"
             style={{ background: 'radial-gradient(circle, #22c55e, transparent)' }} />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full opacity-8 blur-3xl"
             style={{ background: 'radial-gradient(circle, #3b82f6, transparent)' }} />
      </div>

      <div className="relative w-full max-w-md">

        {/* Card principal */}
        <div className="rounded-3xl border border-white/10 p-8 shadow-2xl backdrop-blur-xl"
             style={{ background: 'rgba(255,255,255,0.04)' }}>

          {/* Logo */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-lg mb-4"
                 style={{ background: '#0f172a', border: '1px solid #1e293b' }}>
              <Milk size={26} className="text-blue-500" />
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight">MilkShow</h1>
            <p className="text-white/35 text-sm mt-1">
              {modo === 'login'    && 'Gestão leiteira inteligente'}
              {modo === 'cadastro' && 'Criar sua conta'}
              {modo === 'reset'    && 'Redefinir senha'}
            </p>
          </div>

          {/* Mensagem de sucesso */}
          {info && (
            <div className="mb-4 flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20
                            text-emerald-400 rounded-xl px-4 py-3 text-sm">
              <CheckCircle size={14} className="shrink-0" /> {info}
            </div>
          )}

          {/* ── FORMULÁRIO LOGIN ── */}
          {modo === 'login' && (
            <form onSubmit={handleEmail} className="space-y-3">
              <div>
                <label className="block text-white/40 text-xs font-semibold uppercase tracking-widest mb-1.5">
                  E-mail
                </label>
                <input
                  type="email"
                  autoComplete="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoFocus
                  className={inputCls}
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-white/40 text-xs font-semibold uppercase tracking-widest">
                    Senha
                  </label>
                  <button type="button" onClick={() => trocarModo('reset')}
                    className="text-emerald-400/70 text-xs hover:text-emerald-400 transition-colors">
                    Esqueci a senha
                  </button>
                </div>
                <div className="relative">
                  <input
                    type={showSenha ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={senha}
                    onChange={e => setSenha(e.target.value)}
                    className={inputCls + ' pr-11'}
                  />
                  <button type="button" onClick={() => setShowSenha(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors text-sm">
                    {showSenha ? <EyeOff size={14}/> : <Eye size={14}/>}
                  </button>
                </div>
              </div>

              {erro && (
                <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20
                                text-red-400 rounded-xl px-4 py-3 text-sm">
                  <AlertTriangle size={13} className="mt-0.5 shrink-0" />
                  <span>{erro}</span>
                </div>
              )}

              <button type="submit" disabled={loading}
                className="w-full py-3.5 rounded-xl font-bold text-sm text-white
                           transition-all duration-200 shadow-lg disabled:opacity-50
                           hover:brightness-110 active:scale-[0.98]"
                style={{ background: 'linear-gradient(135deg, #16a34a, #15803d)',
                         boxShadow: '0 0 24px rgba(22,163,74,0.25)' }}>
                {loading ? 'Entrando...' : 'Entrar'}
              </button>

              {/* Divider */}
              <div className="flex items-center gap-3 my-1">
                <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.08)' }} />
                <span className="text-white/20 text-xs">ou continue com</span>
                <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.08)' }} />
              </div>

              {/* Google */}
              <button
                type="button"
                disabled={loading}
                onClick={() => handleFirebaseAuth(signInWithGoogle)}
                className="w-full flex items-center justify-center gap-3 py-3 rounded-xl
                           border border-white/10 bg-white/5 hover:bg-white/10
                           text-white/70 hover:text-white text-sm font-semibold
                           transition-all duration-200 disabled:opacity-40">
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Entrar com Google
              </button>

              <p className="text-center text-white/25 text-xs pt-1">
                Não tem conta?{' '}
                <button type="button" onClick={() => trocarModo('cadastro')}
                  className="text-emerald-400 hover:text-emerald-300 font-semibold transition-colors">
                  Criar agora
                </button>
              </p>
            </form>
          )}

          {/* ── FORMULÁRIO CADASTRO ── */}
          {modo === 'cadastro' && (
            <form onSubmit={handleCadastro} className="space-y-3">
              <div>
                <label className="block text-white/40 text-xs font-semibold uppercase tracking-widest mb-1.5">E-mail</label>
                <input type="email" autoComplete="email" placeholder="seu@email.com"
                       value={email} onChange={e => setEmail(e.target.value)}
                       autoFocus className={inputCls} />
              </div>

              <div>
                <label className="block text-white/40 text-xs font-semibold uppercase tracking-widest mb-1.5">Senha</label>
                <div className="relative">
                  <input type={showSenha ? 'text' : 'password'} autoComplete="new-password"
                         placeholder="Mínimo 6 caracteres"
                         value={senha} onChange={e => setSenha(e.target.value)}
                         className={inputCls + ' pr-11'} />
                  <button type="button" onClick={() => setShowSenha(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 text-sm">
                    {showSenha ? <EyeOff size={14}/> : <Eye size={14}/>}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-white/40 text-xs font-semibold uppercase tracking-widest mb-1.5">Confirmar senha</label>
                <input type={showSenha ? 'text' : 'password'} autoComplete="new-password"
                       placeholder="Repita a senha"
                       value={confirmSenha} onChange={e => setConfirmSenha(e.target.value)}
                       className={inputCls} />
              </div>

              {erro && (
                <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20
                                text-red-400 rounded-xl px-4 py-3 text-sm">
                  <AlertTriangle size={13} className="shrink-0" /> <span>{erro}</span>
                </div>
              )}

              <button type="submit" disabled={loading}
                className="w-full py-3.5 rounded-xl font-bold text-sm text-white
                           transition-all duration-200 disabled:opacity-50 hover:brightness-110"
                style={{ background: 'linear-gradient(135deg, #16a34a, #15803d)',
                         boxShadow: '0 0 24px rgba(22,163,74,0.25)' }}>
                {loading ? 'Criando conta...' : 'Criar conta'}
              </button>

              <p className="text-center text-white/25 text-xs">
                Já tem conta?{' '}
                <button type="button" onClick={() => trocarModo('login')}
                  className="text-emerald-400 hover:text-emerald-300 font-semibold transition-colors">
                  Entrar
                </button>
              </p>
            </form>
          )}

          {/* ── FORMULÁRIO RESET ── */}
          {modo === 'reset' && (
            <form onSubmit={handleReset} className="space-y-4">
              <p className="text-white/40 text-sm text-center">
                Informe seu e-mail e enviaremos um link para redefinir sua senha.
              </p>
              <div>
                <label className="block text-white/40 text-xs font-semibold uppercase tracking-widest mb-1.5">E-mail</label>
                <input type="email" autoComplete="email" placeholder="seu@email.com"
                       value={email} onChange={e => setEmail(e.target.value)}
                       autoFocus className={inputCls} />
              </div>

              {erro && (
                <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20
                                text-red-400 rounded-xl px-4 py-3 text-sm">
                  <AlertTriangle size={13} className="shrink-0" /> <span>{erro}</span>
                </div>
              )}

              <button type="submit" disabled={loading}
                className="w-full py-3.5 rounded-xl font-bold text-sm text-white
                           transition-all duration-200 disabled:opacity-50 hover:brightness-110"
                style={{ background: 'linear-gradient(135deg, #16a34a, #15803d)' }}>
                {loading ? 'Enviando...' : 'Enviar link de redefinição'}
              </button>

              <p className="text-center text-white/25 text-xs">
                <button type="button" onClick={() => trocarModo('login')}
                  className="text-emerald-400 hover:text-emerald-300 font-semibold transition-colors">
                  ← Voltar para o login
                </button>
              </p>
            </form>
          )}
        </div>

        <p className="text-center text-white/15 text-xs mt-5">
          MilkShow · Tecnologia para o agronegócio leiteiro
        </p>
      </div>
    </div>
  )
}
