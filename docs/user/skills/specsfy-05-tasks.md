# Planejar tarefas com `specsfy-05-tasks`

Esta skill transforma uma definição aprovada em tarefas pequenas, ordenadas e
verificáveis. As tarefas ficam na seção 14 da própria `spec.md`.

## Quando usar

Use depois do Definition Gate ou quando uma alteração exigir replanejamento.
Não use para escrever código nem para marcar uma tarefa como concluída.

Se houver mais de um recorte, ordem ou próximo passo possível, a skill reúne a
consulta em uma pergunta numerada. Ela oferece três ou mais sugestões,
`Escrever outra resposta`, `Gere outras opções` e `Avançar` desde a primeira
rodada.

## Como descrever a tarefa

```text
Use $specsfy-05-tasks em
specs/<estado>/0004-recuperar-senha/spec.md.
```

Se a spec contiver mais de uma entrega observável, indique a fatia vertical que
deve ser planejada primeiro:

```text
Prepare as tarefas da primeira fatia vertical da spec 0004.
```

## Exemplo passo a passo

1. A skill lê a spec e o código existente.
2. Identifica a menor entrega observável: solicitar o link.
3. Liga cada tarefa aos requisitos e às condições de aceite correspondentes.
4. Faz cada tarefa de produção depender de um teste com RED registrado.
5. Registra:

```text
T001 [ ] Criar caso TDD para solicitação válida — cobre AC-001
T002 [ ] Criar caso TDD para e-mail desconhecido — cobre AC-002
T003 [ ] Implementar solicitação sem revelar existência do cadastro
```

Quando a spec declara uma interface, o plano inclui tarefas para telas,
menus, navegação, formulário, ações e seus testes de navegação, validação e recuperação de erro.
Uma tarefa de API ou persistência não substitui essas tarefas.

Essas tarefas ficam em uma `Fase de interface` dedicada. Há uma tarefa por tela
registrada, usando os componentes e a stack já existentes no projeto.
Em projetos React, o `PREP` de cada tarefa carrega
`$specsfy-specialist-react-ui-components` antes da escrita de JSX ou TSX. Se o
especialista estiver ausente, o fluxo retorna ao setup para instalar a skill
detectada antes de liberar o código da tela.

Depois de registrar as tarefas, a skill chama `specsfy-06-tdd-bdd` para
materializar os testes. O Plan Gate só pode ser aprovado quando todos os
predecessores exigidos possuem RED válido.

## O que esperar

- tarefas pequenas e com resultado verificável.
- ordem explícita de dependência.
- testes com RED como predecessores do código.
- caminhos e comandos reais do projeto.
- tarefas mantidas dentro da fonte única.

## Erros comuns

- criar `tasks.md`.
- escrever tarefas vagas como “fazer backend”.
- colocar várias mudanças independentes em uma tarefa.
- planejar sem inspecionar a stack real.
- marcar uma tarefa pronta sem evidência.

## Próximo passo

Use [`specsfy-06-tdd-bdd`](specsfy-06-tdd-bdd.md) em modo `prepare` para
materializar o próximo teste e observar RED.
