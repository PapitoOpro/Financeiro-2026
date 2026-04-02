# Guia de Uso — Finanças Pro 2026

---

## Primeiro Acesso

1. Abra o sistema no navegador
2. Clique no botão **Cadastro** e preencha nome, e-mail e senha
3. O **primeiro usuário** cadastrado é aprovado automaticamente como administrador
4. Usuários seguintes precisam de aprovação do admin (menu **Admin → Usuários**)
5. Após o login, o **Assistente de Configuração** (onboarding) guiará você em 3 passos:
   - **Passo 1:** Escolha um perfil de orçamento (50/30/20, Estudante, Família, etc.)
   - **Passo 2:** Ajuste os percentuais das categorias (devem somar 100%)
   - **Passo 3:** Confirme e salve
6. Em seguida, o sistema pedirá para **cadastrar pelo menos um banco ou cartão** antes de liberar o acesso completo

> Você pode alterar categorias e adicionar mais bancos/cartões depois no menu **Cadastros**.

---

## Módulos do Sistema

### 1. Consultor Financeiro (Tela Inicial)
**Para quê:** Diagnóstico inteligente da sua saúde financeira. É a primeira tela exibida ao entrar no sistema.

**O que ele analisa automaticamente:**
- % da renda já consumida
- Categorias que estouraram o orçamento
- Previsão de saldo no fim do mês
- Se o saldo está abaixo do mínimo recomendado
- Comparação com a média dos últimos 3 meses
- Detecção de renda extra (sugere quanto guardar)

**3 abas:**
- **Alertas:** Cards coloridos por severidade (Seguro / Atenção / Crítico)
- **Diagnóstico:** Gráficos de distribuição, evolução mensal e previsão
- **Limites:** Ajuste os gatilhos de alerta (% máximo de gasto, saldo mínimo, etc.)

---

### 2. Controle de Caixa
**Para quê:** Registrar entradas e saídas do dia a dia.

**Como usar:**
- Selecione o **mês/ano** no topo
- No formulário à direita, preencha: descrição, valor, tipo (Entrada/Saída), data, banco e subcategoria
- Clique em **Lançar no Caixa**
- No extrato à esquerda, você pode:
  - **Compensar** transações (marcar como efetivadas)
  - **Editar** qualquer lançamento
  - **Excluir** com confirmação
  - Selecionar vários e **compensar em lote**

> Os cards no topo mostram Entradas, Saídas, Balanço e status de compensação do mês.

---

### 3. Projeção de Gastos
**Para quê:** Controlar parcelas de cartão e prever gastos futuros.

**3 abas disponíveis:**

| Aba | O que faz |
|-----|-----------|
| **Manual** | Cadastra parcelas manualmente (descrição, valor, nº parcelas, cartão, data) |
| **Importações** | Escolha entre importar via **PDF (OCR)** ou **CSV** — extraia, revise e confirme as parcelas |
| **Previsão** | Dashboard com gráficos: total de dívidas, mês mais pesado, distribuição por cartão/categoria, e previsão mês a mês |

> Na aba **Previsão**, você pode editar, excluir parcelas individualmente e exportar relatório em CSV.

---

### 4. Cadastros
**Para quê:** Gerenciar categorias, subcategorias e bancos/cartões.

**Aba Categorias:**
- Crie categorias com nome, ícone e % meta do orçamento
- Dentro de cada categoria, adicione subcategorias
- A **barra de distribuição** no topo mostra se seus percentuais somam 100%
- **Arquivar categorias:** Use o botão de arquivar para ocultar categorias que não usa mais. Categorias arquivadas não aparecem nos formulários de lançamento, mas os dados históricos são preservados. Para restaurar, marque "Mostrar categorias arquivadas" e clique em "Restaurar"
- O mesmo vale para subcategorias — podem ser arquivadas e restauradas individualmente

**Aba Bancos e Cartões:**
- Adicione, edite ou remova contas bancárias e cartões

---

### 5. Relatórios
**Para quê:** Analisar suas finanças e acompanhar o orçamento.

**2 abas principais:**

| Aba | O que contém |
|-----|-------------|
| **Relatórios Analíticos** | Filtros dinâmicos (período, colunas, categoria, banco, tipo), prévia do relatório, exportação em Excel e PDF, Curva ABC e Consultor Financeiro |
| **Acompanhamento Inteligente** | Visualização do progresso dos gastos por categoria com barras de progresso: verde (saudável), amarelo (atenção), vermelho (crítico). A linha vertical indica o ritmo ideal para o dia do mês |

**Relatórios Analíticos — Como usar:**
1. Defina o período (Data Início / Data Fim)
2. Escolha quais colunas exibir (Data, Descrição, Valor, Categoria, Cartão/Banco)
3. Use os filtros adicionais para refinar por categoria, banco ou tipo (Entradas/Saídas)
4. Visualize a prévia com métricas de Entradas, Saídas e Balanço
5. Exporte em **Excel** ou **PDF** com os botões de download

**Sub-abas dentro de Relatórios Analíticos:**
- **Prévia do Relatório:** Tabela filtrada com botões de exportação
- **Curva ABC:** Ranking dos maiores gastos (Classe A = 80% do total — foque neles!)
- **Consultor Financeiro:** Diagnóstico do período selecionado

---

### 6. Admin
**Para quê:** Administração do sistema (somente admin).

- **Estatísticas:** Visão geral de todos os usuários e dados
- **Resetar Dados:** Limpar dados ou resetar o banco completo
- **Usuários:** Aprovar novos cadastros ou remover usuários

---

## Fluxo Recomendado

```
1. Veja seu diagnóstico financeiro (Consultor Financeiro - tela inicial)
         |
2. Configure suas categorias e bancos (Cadastros)
         |
3. Lance suas receitas e despesas diárias (Controle de Caixa)
         |
4. Importe faturas de cartão (Projeção de Gastos → Importações)
         |
5. Acompanhe o orçamento ao longo do mês (Relatórios → Acompanhamento)
         |
6. No fim do período, analise os resultados (Relatórios → Relatórios Analíticos)
```

---

## Dicas Rápidas

- **Compensação** = marcar que o dinheiro efetivamente entrou/saiu da conta
- **Subcategorias** facilitam o detalhamento (ex: Moradia → Aluguel, Condomínio, IPTU)
- **Arquivar** categorias permite ocultá-las sem perder dados históricos — restaure a qualquer momento
- A **Curva ABC** nos relatórios mostra onde cortar gastos com maior impacto
- O **Consultor** roda automaticamente — alertas aparecem também no Controle de Caixa
- Use **Projeção de Gastos → Previsão** para saber qual mês será mais apertado
- Exporte relatórios em **Excel** ou **PDF** para análise externa ou arquivo
