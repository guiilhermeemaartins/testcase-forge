# Acesso ao sistema por perfil

Como gestor, quero que cada usuário veja apenas os módulos do seu perfil.

## Critérios de aceite

- O login é feito com e-mail e senha.
- Após três tentativas com senha incorreta, a conta é bloqueada por 15 minutos e
  exibe a mensagem "Conta temporariamente bloqueada".
- O perfil Operador vê somente o módulo Atendimento.
- O perfil Supervisor vê os módulos Atendimento e Relatórios.
- O perfil Administrador vê todos os módulos, incluindo Configurações.
- Usuário inativo não consegue entrar e recebe a mensagem "Usuário inativo".
- A sessão expira após 30 minutos sem interação e redireciona para a tela de login.
