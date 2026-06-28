/**
 * Login MilkShow — estilo Leigado
 * Fundo verde sólido, logo centralizado, formulário limpo
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, AlertTriangle, CheckCircle, Milk } from 'lucide-react'
import { api } from '../api.js'
import { signInWithGoogle, signInWithEmail, createAccountWithEmail, resetPassword } from '../firebase.js'
import Termos from './Termos.jsx'
import Privacidade from './Privacidade.jsx'

const BRAND = '#22c55e'
const BRAND2 = '#16a34a'

function traduzirErro(code) {
  const map = {
    'auth/invalid-email':        'E-mail inválido.',
    'auth/user-not-found':       'Usuário não encontrado.',
    'auth/wrong-password':       'Senha incorreta.',
    'auth/invalid-credential':   'E-mail ou senha incorretos.',
    'auth/too-many-requests':    'Muitas tentativas. Tente mais tarde.',
    'auth/email-already-in-use': 'Este e-mail já está cadastrado.',
    'auth/weak-password':        'Senha fraca. Mínimo 6 caracteres.',
    'auth/network-request-failed': 'Sem conexão. Verifique sua internet.',
    'auth/popup-closed-by-user': 'Login cancelado.',
  }
  return map[code] || 'Erro inesperado. Tente novamente.'
}

function salvarSessao(data) {
  localStorage.setItem('milkshow_token', data.token)
  localStorage.setItem('milkshow_user', JSON.stringify({
    nome: data.nome,
    email: data.email,
    fazenda_id: data.fazenda_id,
  }))
}

export default function Login() {
  const [modo, setModo]           = useState('login')
  const [email, setEmail]         = useState('')
  const [senha, setSenha]         = useState('')
  const [confirmSenha, setConfirmSenha] = useState('')
  const [erro, setErro]           = useState('')
  const [info, setInfo]           = useState('')
  const [loading, setLoading]     = useState(false)
  const [showSenha, setShowSenha] = useState(false)
  const [aceitaTermos, setAceitaTermos] = useState(false)
  const [showTermos, setShowTermos]     = useState(false)
  const [showPriv, setShowPriv]         = useState(false)
  const nav = useNavigate()

  async function handleFirebaseAuth(getToken) {
    setLoading(true); setErro(''); setInfo('')
    try {
      const idToken = await getToken()
      const data    = await api.googleLogin(idToken)
      salvarSessao(data)
      nav('/', { replace: true })
    } catch(err) {
      setErro(traduzirErro(err.code) || err.message)
    } finally { setLoading(false) }
  }

  function handleEmail(e) {
    e.preventDefault()
    if (!email.trim()) { setErro('Informe seu e-mail.'); return }
    if (!senha)        { setErro('Informe sua senha.'); return }
    handleFirebaseAuth(() => signInWithEmail(email.trim(), senha))
  }

  function handleCadastro(e) {
    e.preventDefault()
    if (!email.trim())    { setErro('Informe seu e-mail.'); return }
    if (senha.length < 6) { setErro('Mínimo 6 caracteres.'); return }
    if (senha !== confirmSenha) { setErro('As senhas não coincidem.'); return }
    if (!aceitaTermos) { setErro('Aceite os Termos de Uso para continuar.'); return }
    handleFirebaseAuth(() => createAccountWithEmail(email.trim(), senha))
  }

  async function handleReset(e) {
    e.preventDefault()
    if (!email.trim()) { setErro('Informe seu e-mail.'); return }
    setLoading(true); setErro('')
    try {
      await resetPassword(email.trim())
      setInfo('Link enviado! Verifique seu e-mail.')
      setModo('login')
    } catch(err) { setErro(traduzirErro(err.code)) }
    finally { setLoading(false) }
  }

  function trocarModo(novo) {
    setModo(novo); setErro(''); setInfo(''); setSenha(''); setConfirmSenha('')
  }

  // Input estilo Leigado: borda branca translucida
  const inputStyle = {
    width: '100%',
    background: 'rgba(255,255,255,0.15)',
    border: '1.5px solid rgba(255,255,255,0.4)',
    borderRadius: 8,
    padding: '12px 14px',
    color: '#fff',
    fontSize: 14,
    outline: 'none',
  }

  const LABEL_STYLE = {
    fontSize: 12,
    fontWeight: 600,
    color: 'rgba(255,255,255,0.75)',
    display: 'block',
    marginBottom: 4,
  }

  return (
    <>
    <div className="min-h-screen flex flex-col items-center justify-between p-4"
         style={{ background: BRAND }}>

      {/* Espaço topo */}
      <div />

      {/* Centro */}
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="mb-3 rounded-3xl overflow-hidden shadow-2xl"
               style={{ width: 110, height: 110, border: '2px solid rgba(255,255,255,0.25)' }}>
            <img src="/app/logo.png" alt="MilkShow"
                 className="w-full h-full object-cover" />
          </div>
          <p className="text-white/70 text-[13px]">Inteligência para gestão leiteira</p>
        </div>

        {/* Mensagem sucesso */}
        {info && (
          <div className="mb-4 flex items-center gap-2 rounded-xl px-4 py-3 text-sm"
               style={{ background: 'rgba(255,255,255,0.15)', color: '#fff' }}>
            <CheckCircle size={14} className="shrink-0" /> {info}
          </div>
        )}

        {/* ── LOGIN ── */}
        {modo === 'login' && (
          <form onSubmit={handleEmail} className="space-y-3">
            <div>
              <label style={LABEL_STYLE}>E-mail *</label>
              <input
                type="email" autoComplete="email" placeholder="seu@email.com"
                value={email} onChange={e => setEmail(e.target.value)}
                autoFocus
                style={inputStyle}
                onFocus={e => e.target.style.borderColor = '#fff'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.4)'}
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label style={LABEL_STYLE}>Senha *</label>
                <button type="button" onClick={() => trocarModo('reset')}
                  className="text-[12px] text-white/70 hover:text-white transition-colors underline">
                  Esqueceu a senha?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showSenha ? 'text' : 'password'} autoComplete="current-password"
                  placeholder="••••••••"
                  value={senha} onChange={e => setSenha(e.target.value)}
                  style={{ ...inputStyle, paddingRight: 44 }}
                  onFocus={e => e.target.style.borderColor = '#fff'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.4)'}
                />
                <button type="button" onClick={() => setShowSenha(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white transition-colors">
                  {showSenha ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>

            {erro && (
              <div className="flex items-start gap-2 rounded-xl px-4 py-3 text-sm"
                   style={{ background: 'rgba(220,38,38,0.25)', color: '#fca5a5', border: '1px solid rgba(220,38,38,0.4)' }}>
                <AlertTriangle size={13} className="mt-0.5 shrink-0" /> <span>{erro}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 pt-1">
              <button type="submit" disabled={loading}
                className="py-3 rounded-xl font-bold text-sm transition-all active:scale-95 disabled:opacity-50"
                style={{ background: BRAND2, color: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
                {loading ? '...' : 'ENTRAR'}
              </button>
              <button type="button" onClick={() => trocarModo('cadastro')}
                className="py-3 rounded-xl font-bold text-sm transition-all active:scale-95"
                style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1.5px solid rgba(255,255,255,0.5)' }}>
                CADASTRAR
              </button>
            </div>

            {/* Divider */}
            <div className="flex items-center gap-3 my-1">
              <div className="flex-1 h-px bg-white/20" />
              <span className="text-white/50 text-xs">ou</span>
              <div className="flex-1 h-px bg-white/20" />
            </div>

            {/* Google */}
            <button type="button" disabled={loading}
              onClick={() => handleFirebaseAuth(signInWithGoogle)}
              className="w-full flex items-center justify-center gap-3 py-3 rounded-xl font-semibold text-sm transition-all active:scale-95 disabled:opacity-40"
              style={{ background: '#fff', color: '#374151', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Entrar com Google
            </button>
          </form>
        )}

        {/* ── CADASTRO ── */}
        {modo === 'cadastro' && (
          <form onSubmit={handleCadastro} className="space-y-3">
            <div>
              <label style={LABEL_STYLE}>E-mail *</label>
              <input type="email" autoComplete="email" placeholder="seu@email.com"
                     value={email} onChange={e => setEmail(e.target.value)} autoFocus style={inputStyle}
                     onFocus={e => e.target.style.borderColor = '#fff'}
                     onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.4)'} />
            </div>
            <div>
              <label style={LABEL_STYLE}>Senha *</label>
              <div className="relative">
                <input type={showSenha ? 'text' : 'password'} autoComplete="new-password"
                       placeholder="Mínimo 6 caracteres"
                       value={senha} onChange={e => setSenha(e.target.value)}
                       style={{ ...inputStyle, paddingRight: 44 }}
                       onFocus={e => e.target.style.borderColor = '#fff'}
                       onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.4)'} />
                <button type="button" onClick={() => setShowSenha(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white">
                  {showSenha ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>
            <div>
              <label style={LABEL_STYLE}>Confirmar senha *</label>
              <input type={showSenha ? 'text' : 'password'} autoComplete="new-password"
                     placeholder="Repita a senha"
                     value={confirmSenha} onChange={e => setConfirmSenha(e.target.value)}
                     style={inputStyle}
                     onFocus={e => e.target.style.borderColor = '#fff'}
                     onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.4)'} />
            </div>

            {/* Termos */}
            <label className="flex items-start gap-3 cursor-pointer mt-1">
              <div className="relative mt-0.5 shrink-0">
                <input type="checkbox" className="sr-only"
                       checked={aceitaTermos} onChange={e => setAceitaTermos(e.target.checked)} />
                <div className="w-5 h-5 rounded flex items-center justify-center border-2 transition-all"
                     style={{
                       background: aceitaTermos ? 'rgba(255,255,255,0.9)' : 'transparent',
                       borderColor: aceitaTermos ? '#fff' : 'rgba(255,255,255,0.5)',
                     }}>
                  {aceitaTermos && <svg width="11" height="9" viewBox="0 0 11 9" fill="none">
                    <path d="M1 4L4 7L10 1" stroke={BRAND} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>}
                </div>
              </div>
              <span className="text-[12px] text-white/75 leading-relaxed">
                Li e aceito os{' '}
                <button type="button" onClick={() => setShowTermos(true)}
                        className="underline text-white font-semibold">Termos de Uso</button>
                {' '}e a{' '}
                <button type="button" onClick={() => setShowPriv(true)}
                        className="underline text-white font-semibold">Política de Privacidade</button>
              </span>
            </label>

            {erro && (
              <div className="flex items-start gap-2 rounded-xl px-4 py-3 text-sm"
                   style={{ background: 'rgba(220,38,38,0.25)', color: '#fca5a5', border: '1px solid rgba(220,38,38,0.4)' }}>
                <AlertTriangle size={13} className="mt-0.5 shrink-0" /> <span>{erro}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 pt-1">
              <button type="submit" disabled={loading}
                className="py-3 rounded-xl font-bold text-sm transition-all active:scale-95 disabled:opacity-50"
                style={{ background: BRAND2, color: '#fff' }}>
                {loading ? '...' : 'CRIAR CONTA'}
              </button>
              <button type="button" onClick={() => trocarModo('login')}
                className="py-3 rounded-xl font-bold text-sm transition-all active:scale-95"
                style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1.5px solid rgba(255,255,255,0.5)' }}>
                VOLTAR
              </button>
            </div>
          </form>
        )}

        {/* ── RESET ── */}
        {modo === 'reset' && (
          <form onSubmit={handleReset} className="space-y-4">
            <p className="text-white/70 text-sm text-center">
              Informe seu e-mail e enviaremos um link para redefinir sua senha.
            </p>
            <div>
              <label style={LABEL_STYLE}>E-mail *</label>
              <input type="email" autoComplete="email" placeholder="seu@email.com"
                     value={email} onChange={e => setEmail(e.target.value)} autoFocus style={inputStyle}
                     onFocus={e => e.target.style.borderColor = '#fff'}
                     onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.4)'} />
            </div>
            {erro && (
              <div className="flex items-start gap-2 rounded-xl px-4 py-3 text-sm"
                   style={{ background: 'rgba(220,38,38,0.25)', color: '#fca5a5', border: '1px solid rgba(220,38,38,0.4)' }}>
                <AlertTriangle size={13} className="mt-0.5 shrink-0" /> <span>{erro}</span>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <button type="submit" disabled={loading}
                className="py-3 rounded-xl font-bold text-sm disabled:opacity-50"
                style={{ background: BRAND2, color: '#fff' }}>
                {loading ? '...' : 'ENVIAR LINK'}
              </button>
              <button type="button" onClick={() => trocarModo('login')}
                className="py-3 rounded-xl font-bold text-sm"
                style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1.5px solid rgba(255,255,255,0.5)' }}>
                VOLTAR
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Footer */}
      <p className="text-white/40 text-xs text-center pb-2">
        MilkShow · Inteligência para pecuária © 2026
      </p>
    </div>

    {showTermos && <Termos onClose={() => setShowTermos(false)} />}
    {showPriv   && <Privacidade onClose={() => setShowPriv(false)} />}
    </>
  )
}
