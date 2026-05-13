import { useEffect, useState } from 'react'
import { RefreshCw, AlertTriangle, Baby } from 'lucide-react'
import { api } from '../api.js'
import {
  Loading, ErrorMsg, Toast, SectionHeader, Badge, T, idadeDias, fmtDate,
} from '../ui.jsx'

function nivelDesmame(dias) {
  if (dias === null || dias === undefined) return 'info'
  if (dias > 90)  return 'critico'
  if (dias >= 75) return 'atencao'
  return 'ok'
}

export default function TabBercario() {
  const [animais, setAnimais] = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro]       = useState('')
  const [toast, setToast]     = useState(null)

  async function carregar() {
    setLoading(true); setErro('')
    try {
      const a = await api.animais()
      setAnimais(a.filter(x => x.status === 'Bezerro' || x.status === 'Novilha'))
    } catch(e) { setErro(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { carregar() }, [])

  if (loading) return <Loading />

  const bezerros = animais.filter(a => a.status === 'Bezerro')
  const novilhas = animais.filter(a => a.status === 'Novilha')
  const criticos = bezerros.filter(a => idadeDias(a.nascimento) > 90)
  const atencao  = bezerros.filter(a => { const d = idadeDias(a.nascimento); return d !== null && d >= 75 && d <= 90 })

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {erro && <ErrorMsg msg={erro} onRetry={carregar} />}

      {/* Contadores */}
      <div className="grid grid-cols-4 shrink-0" style={{ borderBottom:`1px solid ${T.border}` }}>
        {[
          { label:'BEZERROS',       value: bezerros.length, color:'text-slate-100'  },
          { label:'NOVILHAS',       value: novilhas.length, color:'text-slate-100'  },
          { label:'DESMAME VENCIDO',value: criticos.length, color:'text-red-400'    },
          { label:'PRÓX. DESMAME',  value: atencao.length,  color:'text-amber-400'  },
        ].map((k, i, arr) => (
          <div key={k.label} className="p-4" style={{ borderRight: i<arr.length-1 ? `1px solid ${T.border}`:'' }}>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-2">{k.label}</p>
            <p className={`text-2xl font-mono font-semibold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <SectionHeader
        title="GESTÃO DO BERÇÁRIO"
        sub={`${animais.length} animais jovens`}
        action={
          <div className="flex items-center gap-2">
            {toast && <Toast msg={toast.msg} tipo={toast.tipo} onClose={() => setToast(null)} />}
            <button onClick={carregar} className="flex items-center gap-1 text-slate-600 hover:text-slate-400 text-xs font-mono border border-slate-800 rounded px-2 py-1 transition-colors">
              <RefreshCw size={11}/> Atualizar
            </button>
          </div>
        }
      />

      {/* Alertas de desmame */}
      {criticos.length > 0 && (
        <div className="mx-5 mt-4 p-3 rounded flex items-start gap-3"
             style={{ background:'#ef444410', border:'1px solid #ef444430' }}>
          <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 text-xs font-mono font-semibold mb-1">DESMAME VENCIDO</p>
            <p className="text-red-400/70 text-xs font-mono">
              {criticos.map(a => `${a.nome} (${idadeDias(a.nascimento)}d)`).join(' · ')}
            </p>
          </div>
        </div>
      )}

      <div className="overflow-auto flex-1 mt-4">
        {/* Bezerros */}
        <div className="px-5 pb-2 text-[10px] font-mono uppercase tracking-widest text-slate-700 flex items-center gap-2">
          <Baby size={11}/> Bezerros — {bezerros.length}
        </div>
        <table className="w-full text-xs font-mono mb-6">
          <thead>
            <tr style={{ borderBottom:`1px solid ${T.border}` }}>
              {['NOME','MÃE','SEXO','NASCIMENTO','IDADE (DIAS)','DESMAME','STATUS'].map(h =>
                <th key={h} className="text-left text-slate-700 px-5 py-2 font-normal tracking-wider text-[10px]">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {bezerros.length === 0 && (
              <tr><td colSpan={7} className="px-5 py-6 text-slate-700 text-xs text-center">Nenhum bezerro cadastrado.</td></tr>
            )}
            {bezerros.map((a, i) => {
              const dias  = idadeDias(a.nascimento)
              const nivel = nivelDesmame(dias)
              const cor   = { critico:'text-red-400', atencao:'text-amber-400', ok:'text-emerald-400', info:'text-slate-500' }[nivel]
              return (
                <tr key={a.id||a.nome} className="hover:bg-white/[0.02] transition-colors"
                    style={{ borderBottom:`1px solid ${T.border2}` }}>
                  <td className="px-5 py-2.5 text-slate-200 font-semibold">{a.nome}</td>
                  <td className="px-5 py-2.5 text-slate-500">{a.mae||'—'}</td>
                  <td className="px-5 py-2.5 text-slate-500">{a.sexo||'—'}</td>
                  <td className="px-5 py-2.5 text-slate-500">{fmtDate(a.nascimento)}</td>
                  <td className={`px-5 py-2.5 font-semibold ${cor}`}>{dias !== null ? `${dias}d` : '—'}</td>
                  <td className="px-5 py-2.5">
                    {nivel === 'critico' && <Badge label="VENCIDO"    nivel="critico" />}
                    {nivel === 'atencao' && <Badge label="ESTA SEMANA" nivel="atencao" />}
                    {nivel === 'ok'      && <Badge label="EM DIA"      nivel="ok"      />}
                    {nivel === 'info'    && <span className="text-slate-700">—</span>}
                  </td>
                  <td className="px-5 py-2.5">
                    <span className={`text-xs font-mono ${cor}`}>{a.status}</span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {/* Novilhas */}
        <div className="px-5 pb-2 text-[10px] font-mono uppercase tracking-widest text-slate-700">
          Novilhas — {novilhas.length}
        </div>
        <table className="w-full text-xs font-mono">
          <thead>
            <tr style={{ borderBottom:`1px solid ${T.border}` }}>
              {['NOME','RAÇA','NASCIMENTO','IDADE (DIAS)','OBS'].map(h =>
                <th key={h} className="text-left text-slate-700 px-5 py-2 font-normal tracking-wider text-[10px]">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {novilhas.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-slate-700 text-xs text-center">Nenhuma novilha cadastrada.</td></tr>
            )}
            {novilhas.map((a) => {
              const dias = idadeDias(a.nascimento)
              return (
                <tr key={a.id||a.nome} className="hover:bg-white/[0.02] transition-colors"
                    style={{ borderBottom:`1px solid ${T.border2}` }}>
                  <td className="px-5 py-2.5 text-slate-200 font-semibold">{a.nome}</td>
                  <td className="px-5 py-2.5 text-slate-500">{a.raca||'—'}</td>
                  <td className="px-5 py-2.5 text-slate-500">{fmtDate(a.nascimento)}</td>
                  <td className="px-5 py-2.5 text-slate-400">{dias !== null ? `${dias}d` : '—'}</td>
                  <td className="px-5 py-2.5 text-slate-600">{a.obs||'—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
