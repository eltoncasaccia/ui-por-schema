// Regra 12: ADR-0018 — o Postgres é acessado só pela API.
const URL = 'postgresql://estoque:senha@db:5432/estoque'
export const view = () => <div>{URL}</div>
