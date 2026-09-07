import { classeEtiqueta, type Tom } from './estados'

export function Etiqueta({ tom = 'neutro', children }: { tom?: Tom; children: React.ReactNode }) {
  return <span className={classeEtiqueta(tom)}>{children}</span>
}
