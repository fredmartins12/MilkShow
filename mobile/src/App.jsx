import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { signOut } from './firebase.js'
import Login from './pages/Login.jsx'
import Enterprise from './pages/Enterprise.jsx'

function isLogado() {
  return !!localStorage.getItem('milkshow_token')
}

function getUser() {
  try { return JSON.parse(localStorage.getItem('milkshow_user') || '{}') } catch { return {} }
}

function Private({ children }) {
  return isLogado() ? children : <Navigate to="/login" replace />
}

function EnterpriseWrapper() {
  const nav  = useNavigate()
  const user = getUser()

  function handleLogout() {
    localStorage.removeItem('milkshow_token')
    localStorage.removeItem('milkshow_user')
    signOut().catch(() => {})
    nav('/login', { replace: true })
  }

  return (
    <Enterprise
      user={user}
      fazendaId={user.fazenda_id || ''}
      fazendaNome={user.nome || 'Minha Fazenda'}
      onLogout={handleLogout}
    />
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<Private><EnterpriseWrapper /></Private>} />
    </Routes>
  )
}
