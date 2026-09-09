// Regra 8: view com ciclo de vida próprio.
import { useEffect, useState } from 'react'
export const view = () => {
  const [x, setX] = useState(0)
  useEffect(() => { setX(1) }, [])
  return <div>{x}</div>
}
