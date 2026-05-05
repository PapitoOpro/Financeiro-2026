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

### 1. Controle de Caixa

Registrar entradas e saídas do dia a dia.

- Selecione o **mês/ano** no topo.
- Preencha descrição, valor, tipo (Entrada/Saída), data, banco e subcategoria → **Lançar no Caixa**.
- No extrato: edite, exclua, **compense** individualmente ou em lote.

> Cards no topo mostram Entradas, Saídas, Balanço e status de compensação do mês.
> Alertas do Consultor aparecem no topo — indicam gastos excessivos, saldo baixo, etc.

---

### 2. Projeção de Gastos

Controlar parcelas de cartão e prever gastos futuros.

| Aba             | O que faz                                                             |
| --------------- | --------------------------------------------------------------------- |
| **Manual**      | Cadastra parcelas manualmente                                         |
| **Importações** | Importa faturas via texto colado ou arquivo                           |
| **Previsão**    | Dashboard com total de dívidas, mês mais pesado e previsão mês a mês |

#### Importação de Fatura — Método Preferido: Copiar e Colar

> **Prefira sempre colar o texto do PDF** ao invés de fazer upload do arquivo.
> O upload depende de OCR, que pode errar em valores, datas e descrições.
> Copiar direto do PDF garante extração exata sem perda de dados.

**Como fazer:**

1. Abra a fatura no seu leitor de PDF.
2. Selecione todo o conteúdo (`Ctrl+A`) e copie (`Ctrl+C`).
3. Na aba **Importações**, cole o texto no campo indicado.
4. Revise os itens extraídos, ajuste se necessário.
5. Confirme a importação.

As parcelas aparecem na aba **Previsão** e são consideradas nos relatórios.

---

### 3. Cadastros

Gerenciar categorias, subcategorias e bancos/cartões.

- **Categorias:** crie com nome, ícone e % meta. A barra de distribuição mostra se somam 100%.
- **Arquivar:** oculta a categoria dos formulários sem apagar dados históricos. Restaure a qualquer momento.
- **Bancos e Cartões:** adicione, edite ou remova contas.

---

### 4. Relatórios

| Aba                        | O que contém                                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| **Relatórios Analíticos**  | Filtros por período, categoria, banco e tipo. Exportação em Excel e PDF. Curva ABC.             |
| **Acompanhamento**         | Progresso de gastos por categoria (verde = ok, amarelo = atenção, vermelho = crítico)           |

> **Curva ABC:** Classe A = 80% do total — foque nesses itens para cortar gastos com maior impacto.

---

### 5. Admin *(somente admin)*

Aprovar usuários, ver estatísticas e resetar dados.

---

## Fluxo Recomendado

```text
Cadastros → Controle de Caixa → Importar Faturas → Acompanhamento → Relatórios
```

---

## Dicas Rápidas

- **Compensação** = confirmar que o dinheiro efetivamente entrou/saiu da conta
- **Copiar e colar do PDF** é mais confiável do que upload de arquivo para importação de faturas
- Use **Previsão** para saber qual mês será mais apertado
- Exporte em **Excel** ou **PDF** para análise externa
