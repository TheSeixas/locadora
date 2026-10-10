# Locadora Fênix — V1.80.1 (candidata para teste local)

## Segurança e acesso
- Removidas as contas de demonstração fixas e as credenciais conhecidas do código/da interface. A migração elimina as contas legadas por IDs e nomes de usuário.
- Primeiro administrador provisionado por `BOOTSTRAP_ADMIN_USERNAME` e `BOOTSTRAP_ADMIN_PASSWORD`; senha inicial mínima de 12 caracteres. Não redefine o administrador após sua criação.
- Cadastro público de cliente com validação no backend, limite de tentativas por IP e papel `CUSTOMER` imposto no servidor, mesmo quando o payload tenta enviar `ADMIN`.
- A base de dados de testes agora é isolada e descartada ao terminar.

## Interface e marca
- Marca atualizada para Locadora Fênix.
- Cadastro público e cadastro administrativo usam formulários em diálogos, com rótulos acessíveis, validação e mensagens integradas.
- Removidos os diálogos `prompt()` e `alert()` da interface.
- Mantido o tema escuro com detalhes dourados e responsividade existente.

## Limites conhecidos
- O limitador de cadastro é em memória e reinicia junto com o processo; é proteção básica, não antifraude robusta.
- O armazenamento local do Render Free é efêmero; persistência real requer disco persistente ou banco gerenciado.
- Esta versão não implementa pagamentos nem um fluxo completo de aluguel.

## Verificações executadas
- Sintaxe JavaScript (`node --check`): aprovada.
- Suíte automatizada: 41 testes aprovados (36 de backend + 5 de contrato frontend).
- Typecheck/compilação Python: aprovado.
- Contrato visual: aprovado.
- Build: aprovado.
- Smoke HTTP integrado: aprovado, incluindo login administrativo, CRUD de catálogo, cadastro público, perfil CUSTOMER forçado, proteção contra duplicação, filtro por idade, bloqueio de escrita para cliente e revogação de sessão no logout.


## Correções de auditoria V1.80.1
- Corrigida a localização do diálogo de cadastro público: ele não fica mais dentro da seção inicialmente oculta após logout, permitindo abrir o modal na tela de login.
- Mensagem de erro do bootstrap administrativo explica os requisitos sem revelar senha.
- Corrigida validação de idade vazia no cadastro público para não ser convertida silenciosamente em zero.
- Endurecida a verificação de caminho de arquivos estáticos para evitar prefixos de diretório semelhantes.
- Documentação esclarece que o login usa as credenciais configuradas nas variáveis, não `admin` nem contas antigas.
