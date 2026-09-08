/**
 * Ícones desenhados em SVG, grade de 20px, traço 1.5.
 *
 * Nunca emoji: emoji muda de forma entre plataformas, não recolore e não
 * escala junto do texto.
 */
type Props = { tamanho?: number; titulo?: string; preenchida?: boolean }

function Svg({ tamanho = 18, titulo, preenchida, children }: Props & { children: React.ReactNode }) {
  return (
    <svg
      width={tamanho} height={tamanho} viewBox="0 0 20 20"
      fill={preenchida ? 'currentColor' : 'none'}
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round"
      role={titulo ? 'img' : 'presentation'} aria-label={titulo} aria-hidden={titulo ? undefined : true}
    >
      {children}
    </svg>
  )
}

export const Icone = {
  Menu: (p: Props) => <Svg {...p}><path d="M3 6h14M3 10h14M3 14h14" /></Svg>,
  Estrela: (p: Props) => <Svg {...p}><path d="M10 2.6l2.3 4.7 5.2.8-3.8 3.6.9 5.1L10 14.4l-4.6 2.4.9-5.1L2.5 8.1l5.2-.8z" /></Svg>,
  Faisca: (p: Props) => <Svg {...p}><path d="M10 2.5l1.7 4.9 4.8 1.7-4.8 1.7L10 15.7l-1.7-4.9L3.5 9.1l4.8-1.7z" /></Svg>,
  Trace: (p: Props) => <Svg {...p}><path d="M3 15l4-6 3 3.5L17 5" /><path d="M3 17h14" /></Svg>,
  Sair: (p: Props) => <Svg {...p}><path d="M12 14v2a1 1 0 01-1 1H5a1 1 0 01-1-1V4a1 1 0 011-1h6a1 1 0 011 1v2" /><path d="M9 10h8m0 0l-2.5-2.5M17 10l-2.5 2.5" /></Svg>,
  Lote: (p: Props) => <Svg {...p}><path d="M10 2.5l6.5 3.5v8L10 17.5 3.5 14V6z" /><path d="M3.5 6L10 9.5 16.5 6M10 9.5v8" /></Svg>,
  Relogio: (p: Props) => <Svg {...p}><circle cx="10" cy="10" r="7.2" /><path d="M10 5.8V10l2.8 1.7" /></Svg>,
  Caixa: (p: Props) => <Svg {...p}><path d="M3 6.5h14v10H3z" /><path d="M3 6.5L5 3h10l2 3.5M8.5 10h3" /></Svg>,
  Seta: (p: Props) => <Svg {...p}><path d="M3.5 13.5L9 8l3 3 4.5-4.5" /><path d="M12.5 6.5h4v4" /></Svg>,
  Termometro: (p: Props) => <Svg {...p}><path d="M8.5 11.4V4.6a1.5 1.5 0 013 0v6.8a3.2 3.2 0 11-3 0z" /></Svg>,
  Lupa: (p: Props) => <Svg {...p}><circle cx="9" cy="9" r="5.2" /><path d="M12.8 12.8L17 17" /></Svg>,
  Compartilhar: (p: Props) => <Svg {...p}><circle cx="15" cy="5" r="2.3" /><circle cx="5" cy="10" r="2.3" /><circle cx="15" cy="15" r="2.3" /><path d="M7.1 8.9l5.8-2.8M7.1 11.1l5.8 2.8" /></Svg>,
  Enviar: (p: Props) => <Svg {...p}><path d="M4 10h11M10.5 5.5L15.5 10l-5 4.5" /></Svg>,
  Sol: (p: Props) => <Svg {...p}><circle cx="10" cy="10" r="3.6" /><path d="M10 2v1.6M10 16.4V18M18 10h-1.6M3.6 10H2M15.7 4.3l-1.1 1.1M5.4 14.6l-1.1 1.1M15.7 15.7l-1.1-1.1M5.4 5.4L4.3 4.3" /></Svg>,
  Lua: (p: Props) => <Svg {...p}><path d="M16.2 11.6A6.8 6.8 0 018.4 3.8a6.8 6.8 0 107.8 7.8z" /></Svg>,
  Sino: (p: Props) => <Svg {...p}><path d="M10 3a4.5 4.5 0 00-4.5 4.5c0 3.2-1 4.4-1.6 5a.6.6 0 00.4 1h11.4a.6.6 0 00.4-1c-.6-.6-1.6-1.8-1.6-5A4.5 4.5 0 0010 3z" /><path d="M8.4 16.2a1.8 1.8 0 003.2 0" /></Svg>,
  Fechar: (p: Props) => <Svg {...p}><path d="M5.5 5.5l9 9M14.5 5.5l-9 9" /></Svg>,
}
