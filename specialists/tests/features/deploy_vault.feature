Feature: Usar Vault manualmente ou pelo agente
  Scenario: Preservar a senha digitada no terminal
    Then o deploy manual usa entrada oculta mesmo com uma fonte externa

  Scenario: Preparar a máquina sem versionar a senha
    Then o configurador grava fora do projeto e pede confirmação para substituir

  Scenario: Automatizar a descriptografia sem perguntas
    Then o deploy aceita arquivo, script, configuração nativa e identidade

  Scenario: Recusar senha incorreta antes das conexões
    Then uma senha incorreta ou identidade com prompt interrompe o deploy
