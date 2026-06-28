// Ícone customizado de rebanho — silhueta de grupo de vacas, estilo line-art
export function IconRebanho({ size = 17, color = 'currentColor', strokeWidth = 1.5, ...props }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round"
      {...props}
    >
      {/* ── Vaca grande (centro/frente) ── */}
      {/* Corpo */}
      <path d="M5 10 C5 8.5 6.5 8 9 8 L14 8 C16.5 8 18 8.5 18 10 L18 14 C18 15 16.5 15.5 14 15.5 L9 15.5 C6.5 15.5 5 15 5 14 Z" />
      {/* Cabeça */}
      <path d="M5 11 C4 10 3 10 2.5 11.5 C2 13 3 14 4.5 13.5 C5 13.2 5.5 12.5 5 12" />
      {/* Chifre */}
      <path d="M4.5 10 L3.5 8.5" />
      <path d="M6 8.5 L6 7" />
      {/* Pernas dianteiras */}
      <line x1="8"  y1="15.5" x2="8"  y2="20.5" />
      <line x1="11" y1="15.5" x2="11" y2="20.5" />
      {/* Pernas traseiras */}
      <line x1="13" y1="15.5" x2="13" y2="20.5" />
      <line x1="16" y1="15.5" x2="16" y2="20.5" />
      {/* Rabo */}
      <path d="M18 10.5 C20 9.5 21 8 20 6.5" />
      {/* Úbere */}
      <path d="M10 15.5 Q11.5 17 13 15.5" />

      {/* ── Vaca pequena (atrás/direita) ── */}
      {/* Corpo */}
      <path d="M16 12 C16 11 17 10.5 19 10.5 L22 10.5 C23.5 10.5 24 11 24 12 L24 14.5 C24 15 23.5 15.5 22 15.5 L19 15.5 C17 15.5 16 15 16 14.5 Z" />
      {/* Cabeça pequena */}
      <path d="M16 12.5 C15 12 14.5 12.5 14.5 13.5 C14.5 14.5 15 14.8 16 14.5" />
      {/* Pernas traseiras pequenas */}
      <line x1="18" y1="15.5" x2="18" y2="20" />
      <line x1="20" y1="15.5" x2="20" y2="20" />
      <line x1="22" y1="15.5" x2="22" y2="20" />

      {/* ── Chão ── */}
      <path d="M1 21 C5 20.5 12 21 22 21" />
    </svg>
  )
}
