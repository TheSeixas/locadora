# Release Notes — V1.79.0

## Gestão administrativa do catálogo

Esta versão adiciona uma capacidade extra ao projeto: o ADMIN agora possui controle completo do catálogo.

### Incluído

- ADMIN pode adicionar filmes.
- ADMIN pode editar filmes.
- ADMIN pode excluir filmes.
- OPERACIONAL não pode alterar o catálogo.
- CUSTOMER não pode alterar o catálogo.
- Validação backend de título, categoria, ano, classificação e descrição.
- Categorias disponíveis para o frontend via `/api/catalog`.
- Interface administrativa para criar, editar e excluir títulos.
- Seed de demonstração não sobrescreve alterações do catálogo.
- Exclusões do catálogo não são restauradas no reinício do servidor.

### Testes

- **31/31 testes unitários passando.**
- Typecheck: PASS.
- Build: PASS.
- Visual smoke: PASS.
- Functional smoke: PASS.
- HTTP catalog smoke: PASS.

### Base

Construído sobre a V1.78.5, com o Bloco 1 de hardening preservado.

## Próximo

Deploy e configuração de produção pertencem ao antigo Bloco 2.
