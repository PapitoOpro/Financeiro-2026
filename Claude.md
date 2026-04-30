# Financeiro 2026

## 1. Visão Geral

Sistema de gestão financeira pessoal construído com Streamlit, Supabase e IA (Claude).

Funcionalidades principais:

- Lançamento diário de receitas e despesas (caixa)
- Orçamento por categorias com percentuais-alvo
- Importação de faturas via PDF com OCR
- Projeção de parcelas e fluxo de caixa futuro
- Relatórios analíticos com curva ABC e exportação Excel/PDF
- Consultor IA (Claude Haiku) com alertas contextuais
- Onboarding com perfis de orçamento pré-configurados
- Multi-usuário com isolamento de dados via RLS

## 2. Stack

- **Frontend/UI**: Streamlit 1.55+
- **Backend/DB**: Supabase (PostgreSQL + Auth)
- **IA**: Claude Haiku via SDK Anthropic
- **Linguagem**: Python 3.11
- **PDF/OCR**: pdfplumber, PyPDF2, pytesseract, pdf2image
- **Dados**: pandas, plotly, openpyxl

## 3. Arquitetura

```text
app.py          # Entrada principal, roteamento de páginas, autenticação
auth.py         # Login/registro via Supabase Auth
database.py     # DatabaseManager — pool de conexões, CRUD, RLS
config.py       # Constantes globais (meses, bancos, esquema de cores)
utils.py        # Extração de PDF/OCR, formatação de moeda (R$)
modules/
  cadastros.py         # Categorias macro/sub, contas bancárias, cartões
  caixa.py             # Lançamento diário de receitas e despesas
  parcelas_exemplo.py  # Projeção de parcelas, importação de faturas (PDF/CSV)
  acompanhamento.py    # Dashboard de progresso diário vs. orçamento
  relatorios.py        # Relatórios, curva ABC, exportação Excel/PDF
  consultor.py         # Consultor IA (Claude Haiku) com alertas contextuais
  onboarding.py        # Wizard de primeiro acesso com perfis de orçamento
  admin.py             # Painel admin — usuários, reset de banco
scripts/        # SQL de criação/migração do schema
```

## 4. Regras da IA 🔥

Você está atuando como um engenheiro de software sênior neste projeto.

Regras obrigatórias:

- Sempre respeitar a arquitetura existente.
- Nunca criar código fora dos padrões definidos.
- Sempre reutilizar funções existentes antes de criar novas.
- Nunca acessar o banco diretamente — usar `DatabaseManager`.
- Sempre considerar RLS (filtro por `user_id`).
- Código deve ser claro, tipado e modular.
- Evitar soluções complexas desnecessárias.

Para o módulo `consultor.py` especificamente:

- Sempre usar linguagem clara e objetiva.
- Priorizar recomendações práticas.
- Nunca inventar dados financeiros.
- Sempre considerar o contexto financeiro real do usuário.
- Evitar respostas genéricas.

Formato de resposta esperado do consultor: Diagnóstico → Problema identificado → Sugestão prática.

## 5. Anti-padrões 🔥

- Não criar conexões diretas com o banco (sempre usar `DatabaseManager`)
- Não usar `st.experimental_*` — APIs deprecadas
- Não ignorar RLS — toda query deve filtrar por `user_id`
- Não hardcodar valores sensíveis (secrets, senhas, URLs de banco)
- Não criar lógica duplicada — verificar se já existe função similar
- Não alterar estrutura do banco sem script de migração em `scripts/`
- Não usar f-string com input do usuário em queries SQL

## 6. Padrões de Código 🔥

- Funções pequenas com responsabilidade única
- Sempre usar type hints
- Sempre tratar exceções críticas
- Nomes de funções em `snake_case`
- Evitar lógica de negócio dentro de arquivos de UI (Streamlit)
- Todo texto de UI em **português brasileiro**
- Datas no formato `DD/MM/AAAA`; valores monetários formatados com `moeda()`
- `st.session_state` é o único estado compartilhado entre componentes
- Novos módulos devem ser registrados no menu em `app.py` e exportados em `modules/__init__.py`

## 7. Banco de Dados

Todas as tabelas usam **Row Level Security (RLS)** — dados são isolados por usuário.

| Tabela | Descrição |
| -- | -- |
| `usuarios` | Perfis linkados ao Supabase Auth |
| `contas` | Contas bancárias e cartões |
| `categorias` | Categorias macro com % de orçamento |
| `subcategorias` | Categorias operacionais detalhadas |
| `transacoes` | Lançamentos diários (caixa) |
| `limites_financeiros` | Limites personalizados por categoria |
| `faturas` | Faturas importadas via PDF |
| `itens_fatura` | Itens individuais de cada fatura |

Para recriar o schema do zero: executar os scripts em `scripts/` na ordem `passo1` → `passo4`.

## 8. Módulos — Comportamentos Importantes

**`database.py`**

- Usar sempre `DatabaseManager` para queries; não abrir conexões diretas.
- `get_user_id()` retorna o `id` do usuário logado — obrigatório para filtros RLS.
- TCP keepalive configurado para evitar drops em conexões ociosas.

**`utils.py`**

- `extrair_texto_pdf()` tenta extração direta primeiro; cai para OCR (tesseract) se necessário.
- `moeda(valor)` formata para `R$ 1.234,56` — usar em toda exibição de valores.

**`consultor.py`**

- Usa `claude-haiku` para manter custo ~$0,01/conversa.
- Passa contexto financeiro do usuário (saldos, alertas, categorias) no system prompt.

**`onboarding.py`**

- Executado automaticamente para novos usuários sem conta bancária cadastrada.
- Perfis disponíveis: 50/30/20, Estudante, Família, Freelancer, etc.

**`admin.py`**

- Senha admin hardcoded — não expor em logs.
- Reset de banco é irreversível; pedir confirmação antes de chamar.

## 9. Fluxo de Decisão 🔥

Antes de implementar qualquer coisa:

1. Verificar se já existe função similar no projeto
2. Verificar impacto em outros módulos
3. Garantir compatibilidade com RLS (filtro por `user_id`)
4. Validar consistência com a UI atual
5. Priorizar simplicidade

Se houver dúvida, prefira soluções conservadoras.

## 10. Segurança

- Nunca commitar `.streamlit/secrets.toml`.
- Queries devem usar parâmetros (`%s`) — nunca f-string com input do usuário.
- Nunca expor secrets em logs ou mensagens de erro.
- Nunca retornar dados de outro usuário — RLS deve estar sempre ativo.
- Sempre validar inputs antes de persistir no banco.
- Nunca executar comandos destrutivos (reset, drop) sem confirmação explícita.
- Toda tabela nova precisa de políticas RLS equivalentes às de `scripts/passo4_rls_policies.sql`.

## 11. Exemplos 🔥

### ✔️ Correto

```python
db = DatabaseManager()
user_id = db.get_user_id()
transacoes = db.buscar("SELECT * FROM transacoes WHERE user_id = %s", (user_id,))
st.write(moeda(transacoes[0]["valor"]))
```

### ❌ Incorreto

```python
conn = psycopg2.connect(...)
cursor.execute(f"SELECT * FROM transacoes WHERE user_id = '{user_id}'")
st.write(f"R$ {valor}")
```

## 12. Comandos

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar localmente
streamlit run app.py

# Resetar banco (cuidado: apaga todos os dados)
python reset_db.py
```

Credenciais do Supabase ficam em `.streamlit/secrets.toml` (não versionar).
