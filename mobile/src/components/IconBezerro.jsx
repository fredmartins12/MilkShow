// Ícone customizado de bezerro — line-art, estilo Lucide
export function IconBezerro({ size = 17, color = 'currentColor', strokeWidth = 1.5, ...props }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round"
      {...props}
    >
      {/* Corpo */}
      <path d="M8.5 8 C9.5 6.5 12 6 15 6 C18 6 20.5 7 21 9.5 C21.5 11 21 13 20 14.5 C19 15.5 17 16 15 16 C12 16 9 16 8.5 16 C7.5 16 7 15 7 14 C7 12 7.5 9.5 8.5 8 Z" />
      {/* Pescoço + cabeça */}
      <path d="M7 10 C6 8.5 5 8 4 8.5 C3 9 2.5 10 2.5 11.5 C2.5 13 3.5 14 5 13.5 C6 13 7 12 7 11" />
      {/* Orelha pontuda */}
      <path d="M7.5 7.5 L6.5 5 L9 7" />
      {/* Olho */}
      <circle cx="4.5" cy="10.5" r="0.4" fill={color} stroke="none" />
      {/* Pernas dianteiras */}
      <line x1="9.5" y1="16" x2="9.5" y2="21.5" />
      <line x1="12" y1="16" x2="12" y2="21.5" />
      {/* Casco dianteiro */}
      <line x1="9" y1="21.5" x2="10" y2="21.5" />
      <line x1="11.5" y1="21.5" x2="12.5" y2="21.5" />
      {/* Pernas traseiras */}
      <line x1="16" y1="16" x2="16" y2="21.5" />
      <line x1="18.5" y1="16" x2="18.5" y2="21.5" />
      {/* Casco traseiro */}
      <line x1="15.5" y1="21.5" x2="16.5" y2="21.5" />
      <line x1="18" y1="21.5" x2="19" y2="21.5" />
      {/* Rabo curvado */}
      <path d="M21 10.5 C22.5 9 23 7 21.5 5.5" />
    </svg>
  )
}
