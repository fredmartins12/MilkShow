import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'

// ─── AUTO-UPDATE DO SERVICE WORKER ──────────────────────────────────────────
// Quando um novo SW ativa e assume o controle, recarrega a página automaticamente.
// Isso garante que o usuário sempre vê a versão mais recente sem tela branca.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    window.location.reload()
  })
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { erro: null }
  }
  static getDerivedStateFromError(err) {
    return { erro: err?.message || 'Erro inesperado' }
  }
  render() {
    if (this.state.erro) {
      return (
        <div style={{
          minHeight: '100dvh', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 16,
          background: '#020617', color: '#94a3b8', fontFamily: 'monospace', padding: 32,
        }}>
          <div style={{ fontSize: 13, color: '#ef4444', marginBottom: 4 }}>Erro na aplicação</div>
          <div style={{
            background: '#0b1510', border: '1px solid #1c2d1e', borderRadius: 8,
            padding: '12px 20px', maxWidth: 480, width: '100%', fontSize: 11, color: '#64748b',
          }}>
            {this.state.erro}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 8, padding: '8px 20px', background: '#16a34a', color: '#fff',
              border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontFamily: 'monospace',
            }}>
            Recarregar
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter basename="/app">
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
