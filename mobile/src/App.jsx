import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Enterprise from './pages/Enterprise.jsx'

function isLogado() {
  return !!localStorage.getItem('milkshow_token')
}

function Private({ children }) {
  return isLogado() ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<Private><Enterprise /></Private>} />
    </Routes>
  )
}
