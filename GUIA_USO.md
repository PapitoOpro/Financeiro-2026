# Exemplos Práticos de Uso

---

## Exemplo 1: Lançando uma Despesa no Caixa

1. Selecione o mês/ano desejado no topo da tela.
2. No formulário à direita, preencha:
  - **Descrição:** Supermercado
  - **Valor:** 250
  - **Tipo:** Saída
  - **Data:** 10/04/2026
  - **Banco:** Nubank
  - **Subcategoria:** Alimentação
3. Clique em **Lançar no Caixa**.
4. Veja o lançamento aparecer no extrato à esquerda.

---

## Exemplo 2: Importando Fatura de Cartão

1. Acesse o menu **Projeção de Gastos**.
2. Vá até a aba **Importações**.
3. Clique em **Importar PDF** ou **Importar CSV** e selecione o arquivo da fatura.
4. Revise os itens extraídos, ajuste valores ou datas se necessário.
5. Clique em **Confirmar Importação**.
6. As parcelas aparecerão na aba **Previsão** e serão consideradas nos relatórios.

---

## Exemplo 3: Exportando Relatório em PDF

1. Acesse o menu **Relatórios**.
2. Na aba **Relatórios Analíticos**, defina o período e os filtros desejados.
3. Clique em **Baixar PDF** para exportar o relatório filtrado.
4. O arquivo será baixado pronto para impressão ou envio.

---

## Dicas Visuais

- Cards coloridos no topo do Caixa mostram Entradas (verde), Saídas (vermelho) e Balanço (cinza ou verde/vermelho).
- Alertas do Consultor aparecem em destaque acima do formulário do Caixa.
- Barras de progresso no Acompanhamento mudam de cor conforme o gasto: verde (ok), amarelo (atenção), vermelho (crítico).
- Ícones ajudam a identificar categorias e bancos rapidamente.

---
# Guia de Uso — Financeiro 2026

---


## Primeiro Acesso

1. Abra o sistema no navegador.
2. Clique em **Cadastro** e preencha nome, e-mail e senha.
3. O primeiro usuário cadastrado é aprovado automaticamente como administrador.
4. Usuários seguintes precisam de aprovação do admin (menu **Admin → Usuários**).
5. Após login, o **Assistente de Configuração** (onboarding) guiará você:
  - Escolha um perfil de orçamento (ex: 50/30/20, Estudante, Família, etc.)
  - Ajuste os percentuais das categorias (devem somar 100%)
  - Confirme e salve
6. Cadastre pelo menos um banco ou cartão para liberar o acesso completo.

> Você pode alterar categorias e adicionar bancos/cartões depois em **Cadastros**.

---

## Módulos do Sistema


### 1. Controle de Caixa (Tela Inicial)
**Para quê:** Registrar entradas e saídas do dia a dia.

**Como usar:**
- Selecione o **mês/ano** no topo.
- No formulário à direita, preencha: descrição, valor, tipo (Entrada/Saída), data, banco e subcategoria.
- Clique em **Lançar no Caixa**.
- No extrato à esquerda, você pode:
  - **Compensar** transações (marcar como efetivadas)
  - **Editar** qualquer lançamento
  - **Excluir** com confirmação
  - Selecionar vários e **compensar em lote**

> Os cards no topo mostram Entradas, Saídas, Balanço e status de compensação do mês.

**Consultor Financeiro:**
Alertas inteligentes sobre sua saúde financeira aparecem no topo do Caixa, indicando gastos excessivos, saldo baixo, previsão de orçamento, etc.

---


### 2. Projeção de Gastos
**Para quê:** Controlar parcelas de cartão e prever gastos futuros.

**Abas disponíveis:**

| Aba | O que faz |
|-----|-----------|
| **Manual** | Cadastra parcelas manualmente (descrição, valor, nº parcelas, cartão, data) |
| **Importações** | Importa faturas via PDF (OCR) ou CSV — revise e confirme as parcelas |
| **Previsão** | Dashboard com gráficos: total de dívidas, mês mais pesado, distribuição por cartão/categoria, e previsão mês a mês |

> Na aba **Previsão**, você pode editar, excluir parcelas individualmente e exportar relatório em CSV.

---


### 3. Cadastros
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


### 4. Relatórios
**Para quê:** Analisar suas finanças e acompanhar o orçamento.

**2 abas principais:**

| Aba | O que contém |
|-----|-------------|
| **Relatórios Analíticos** | Filtros dinâmicos (período, colunas, categoria, banco, tipo), prévia do relatório, exportação em Excel e PDF, Curva ABC |
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

---


### 5. Admin
**Para quê:** Administração do sistema (somente admin).

- **Estatísticas:** Visão geral de todos os usuários e dados
- **Resetar Dados:** Limpar dados ou resetar o banco completo
- **Usuários:** Aprovar novos cadastros ou remover usuários

---


## Fluxo Recomendado

```
1. Cadastre suas categorias e bancos (Cadastros)
         |
2. Lance receitas e despesas diárias (Controle de Caixa)
         |
3. Veja alertas do Consultor Financeiro no topo do Caixa
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
- O **Consultor** roda automaticamente — alertas aparecem no topo do Caixa
- Use **Projeção de Gastos → Previsão** para saber qual mês será mais apertado
- Exporte relatórios em **Excel** ou **PDF** para análise externa ou arquivo
