# Guia de Uso — Financeiro 2026

---

## Primeiro Acesso

1. Clique em **Cadastro** → preencha nome, e-mail e senha.
2. O primeiro usuário é admin automaticamente. Usuários seguintes precisam de aprovação em **Admin → Usuários**.
3. O **Assistente de Configuração** será aberto: escolha um perfil de orçamento, ajuste os percentuais (devem somar 100%) e confirme.
4. Cadastre pelo menos um banco ou cartão para liberar o acesso completo.

> Categorias e bancos podem ser alterados depois em **Cadastros**.

---

## Módulos

### 1. Consultor Financeiro IA

Chat com IA (Claude Haiku) sobre seus dados financeiros e uso do sistema.

- Carrega automaticamente o contexto financeiro (saldos, gastos, alertas) 1x por dia — use **🔄 Atualizar dados** para forçar.
- Clique em uma das **perguntas frequentes** sugeridas ou digite sua própria pergunta no chat.
- **🗑️ Limpar chat** apaga o histórico da conversa.

> Requer `ANTHROPIC_API_KEY` configurada em `.streamlit/secrets.toml`.

---

### 2. Controle de Caixa

Registrar entradas e saídas do dia a dia.

- Selecione o **mês/ano** no topo.
- Preencha descrição, valor, tipo (Entrada/Saída), data, banco e subcategoria → **Lançar no Caixa**.
- No extrato: edite, exclua, **compense** individualmente ou em lote.

> Cards no topo mostram Entradas, Saídas, Balanço e status de compensação do mês.
> Alertas do Consultor aparecem no topo — indicam gastos excessivos, saldo baixo, etc.

---

### 3. Projeção de Gastos

Controlar parcelas de cartão e prever gastos futuros.

| Aba             | O que faz                                                             |
| --------------- | --------------------------------------------------------------------- |
| **Manual**      | Cadastra parcelas manualmente                                         |
| **Importações** | Importa faturas via upload de PDF, CSV ou texto colado                |
| **Previsão**    | Dashboard com total de dívidas, mês mais pesado e previsão mês a mês |

#### Importação de Fatura

##### Opção 1 — Upload do PDF (método preferido)

> Suporte automático a **Nubank, Itaú, Bradesco, Mercado Pago e Porto Bank**.
> O sistema detecta o banco, o cartão (pelos últimos dígitos) e sugere a categoria/subcategoria de cada item automaticamente.

1. Na aba **Importações**, envie o PDF da fatura.
2. Se o PDF tiver senha, informe-a no campo indicado.
3. Clique em **🔍 Extrair lançamentos**.
4. Revise os itens extraídos (banco, cartão e categorias sugeridas) e ajuste se necessário.
5. Confirme a importação.

##### Opção 2 — Copiar e colar *(use somente se o upload não funcionar)*

1. Abra o PDF, selecione os lançamentos (`Ctrl+A`) e copie (`Ctrl+C`).
2. Cole o texto no campo indicado e clique em **Processar texto colado**.

##### Opção 3 — Upload de CSV

1. Envie o arquivo `.csv` da fatura.
2. Mapeie as colunas (Descrição, Valor e, se houver, Parcela).
3. Clique em **Extrair Dados do CSV** e revise antes de confirmar.

As parcelas aparecem na aba **Previsão** e são consideradas nos relatórios.

---

### 4. Cadastros

Gerenciar categorias, subcategorias e bancos/cartões.

- **Categorias:** crie com nome, ícone e % meta. A barra de distribuição mostra se somam 100%.
- **Arquivar:** oculta a categoria dos formulários sem apagar dados históricos. Restaure a qualquer momento.
- **Bancos e Cartões:** adicione, edite ou remova contas.

---

### 5. Relatórios

| Aba                        | O que contém                                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| **Relatórios Analíticos**  | Filtros por período, categoria, banco e tipo. Exportação em Excel e PDF. Curva ABC.             |
| **Acompanhamento**         | Progresso de gastos por categoria (verde = ok, amarelo = atenção, vermelho = crítico)           |

> **Curva ABC:** Classe A = 80% do total — foque nesses itens para cortar gastos com maior impacto.

---

### 6. Admin *(somente admin)*

| Aba                | O que faz                                             |
| ------------------ | ------------------------------------------------------ |
| **Estatísticas**   | Visão geral do banco (usuários, lançamentos, etc.)    |
| **Resetar Dados**  | Reseta dados do sistema — ação irreversível           |
| **Usuários**       | Aprova cadastros pendentes e lista usuários aprovados |
| **Log de Ações**   | Histórico de ações realizadas no sistema              |

---

## Fluxo Recomendado

```text
Cadastros → Controle de Caixa → Importar Faturas → Acompanhamento → Relatórios → Consultor Financeiro
```

---

## Dicas Rápidas

- **Compensação** = confirmar que o dinheiro efetivamente entrou/saiu da conta
- **Upload do PDF** é o método preferido para importar faturas — detecta banco, cartão e categoria automaticamente
- Se o upload não detectar os itens, use **copiar e colar** como alternativa
- Use **Previsão** para saber qual mês será mais apertado
- Exporte em **Excel** ou **PDF** para análise externa
- Tire dúvidas sobre seus gastos direto no **Consultor Financeiro IA**
