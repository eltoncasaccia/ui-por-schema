/**
 * Sugestões do assistente: frases de gente, uma por componente, e só dos
 * componentes que respondem sem id.
 *
 * Não são os `examples` do registry. Aqueles são escritos para o PROMPT, e
 * vários pressupõem contexto — "quem liberou esse lote", clicada solta, não
 * tem lote nenhum e não traz nada.
 *
 * Cada frase foi conferida contra o modelo em uso (`qwen2.5:7b`, 2026-09-14):
 * compôs o componente certo e o dado chegou. As que erraram ficaram de fora —
 * "panorama do estoque", "listar todos os lotes", "trilha de auditoria
 * recente". Trocar o modelo pede reconferir a lista.
 */
const SUGESTOES: readonly (readonly [componente: string, frase: string])[] = [
  ['quarentena_fila', 'lotes aguardando liberação'],
  ['recebimento_registrar', 'registrar recebimento'],
  ['vencimento_grafico', 'gráfico de vencimentos por mês'],
  ['relatorio_movimentacao', 'relatório de movimentação por unidade'],
  ['temperatura_excursoes', 'houve excursão de temperatura?'],
]

/** Só o que está no catálogo DESTE ator: sugerir porta fechada conta que ela existe. */
export function sugestoesPara(idsDoCatalogo: ReadonlySet<string>, limite = 4): string[] {
  return SUGESTOES.filter(([c]) => idsDoCatalogo.has(c)).map(([, frase]) => frase).slice(0, limite)
}
