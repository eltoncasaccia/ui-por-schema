// ESLint do cliente. T-001 declarava este arquivo e ele nunca existiu — o
// `make check` parava aqui, na primeira etapa (achado A-13).
//
// **O que este arquivo NÃO faz, de propósito:**
//
// - Estilo. `tsc` em modo estrito máximo já recusa a maior parte do que um lint
//   de estilo pegaria, e discussão de formatação não sobrevive a seis meses.
// - Arquitetura. As fronteiras do cliente são de `scripts/arch-check.ts`, que
//   tem teste negativo por regra (T-005). Repetir aqui daria dois lugares para
//   a mesma regra divergir.
//
// Sobra o que só o ESLint vê: erro de uso de hook, promessa não aguardada,
// `any` que escapou do `tsc`, e variável morta.
import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import reactHooks from 'eslint-plugin-react-hooks'

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'src/generated/**'] },
  js.configs.recommended,
  // `recommendedTypeChecked`, e não `recommended`: as regras que valem a pena
  // — promessa flutuante, `any` que vaza — precisam do type checker. Custa
  // alguns segundos e é o motivo de o ESLint estar aqui.
  ...tseslint.configs.recommendedTypeChecked,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // O projeto proíbe `any` (CLAUDE.md §7). `tsc` pega o implícito; esta
      // regra pega o explícito, que passa pelo compilador.
      '@typescript-eslint/no-explicit-any': 'error',
      // Variável não usada com `_` na frente é intenção declarada, não descuido.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // `rules-of-hooks` é desligada em `views/` — e a razão é chata, não boa.
    //
    // A regra decide o que é componente pelo NOME: precisa começar com
    // maiúscula. O contrato deste projeto exporta `view` em minúscula
    // (CONTRATOS §6, congelado; ADR-0017), e o `views/indice.ts` gerado importa
    // por esse nome. Renomear quebraria contrato congelado e o teste de bijeção
    // para agradar uma heurística.
    //
    // **O que se perde, dito sem disfarce:** a regra também pega hook chamado
    // dentro de `if` ou de laço, e isso deixa de ser verificado nas views. Não
    // há hoje nada cobrindo esse caso — nem o `arch-check`, cujas seis regras a
    // T-005 fixa. É lacuna conhecida, não descuido.
    files: ['src/views/**/*.tsx'],
    rules: { 'react-hooks/rules-of-hooks': 'off' },
  },
  {
    // Fixtures existem para VIOLAR as regras. Lintá-las seria pedir que a
    // violação fosse bem escrita.
    ignores: ['scripts/fixtures-violacao/**'],
  },
)
