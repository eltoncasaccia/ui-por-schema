// Regra 9: view falando com o cache de servidor.
import { useQuery } from '@tanstack/react-query'
export const view = () => <div>{String(useQuery)}</div>
