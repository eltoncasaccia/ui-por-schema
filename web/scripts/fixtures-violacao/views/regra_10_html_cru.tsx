// Regra 10: HTML vindo de conteúdo que o ADR-0012 trata como hostil.
export const view = ({ vm }: { vm: { html: string } }) => (
  <div dangerouslySetInnerHTML={{ __html: vm.html }} />
)
