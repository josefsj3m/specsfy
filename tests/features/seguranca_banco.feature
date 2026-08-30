@seguranca-banco
Feature: Preservar o banco de desenvolvimento
  Para executar implementação e testes sem perder informações locais
  Como pessoa que aplica o Specsfy em um projeto Laravel
  Quero uma separação obrigatória entre os bancos de desenvolvimento e teste

  Scenario: Verificar o banco durante o setup e antes da suíte
    Given os contratos de setup, testes, tarefas e implementação do Specsfy
    When a proteção do banco é inspecionada
    Then o Laravel exige um env de teste com banco separado do desenvolvimento
    And a verificação é repetida antes de toda suíte de testes
    And comandos que zeram ou apagam o banco são ignorados
    And RefreshDatabase e DatabaseMigrations não são usados
