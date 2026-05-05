# Financeiro 2026

Sistema de gestão financeira pessoal construído com **Streamlit**, **Supabase** e **IA (Claude)**.

---

## Funcionalidades

- **Controle de Caixa** — lançamento diário de receitas e despesas com compensação e edição
- **Projeção de Gastos** — controle de parcelas de cartão com importação de faturas via PDF/texto
- **Orçamento por Categorias** — metas percentuais com acompanhamento de progresso em tempo real
- **Relatórios Analíticos** — filtros dinâmicos, Curva ABC, exportação em Excel e PDF
- **Consultor IA** — alertas financeiros contextuais powered by Claude Haiku
- **Onboarding** — wizard de primeiro acesso com perfis pré-configurados (50/30/20, Família, Estudante, etc.)
- **Multi-usuário** — isolamento completo de dados via Row Level Security (RLS) no Supabase

---

## Stack

| Camada       | Tecnologia                                    |
| ------------ | --------------------------------------------- |
| Frontend/UI  | Streamlit 1.30+                               |
| Backend/DB   | Supabase (PostgreSQL + Auth + RLS)            |
| IA           | Claude Haiku via SDK Anthropic                |
| Linguagem    | Python 3.11                                   |
| PDF/OCR      | pdfplumber, PyPDF2, pytesseract, pdf2image    |
| Dados        | pandas, plotly, openpyxl                      |
| Export       | fpdf2, openpyxl                               |

---

## Estrutura do Projeto

```text
app.py                    # Entrada principal, roteamento e autenticação
auth.py                   # Login e registro via Supabase Auth
database.py               # DatabaseManager — pool de conexões e CRUD
config.py                 # Constantes globais
utils.py                  # Extração de PDF/OCR, formatação de moeda
modules/
  caixa.py                # Lançamento de receitas e despesas
  parcelas_exemplo.py     # Projeção de parcelas e importação de faturas
  acompanhamento.py       # Dashboard de progresso vs. orçamento
  relatorios.py           # Relatórios, Curva ABC, exportação
  consultor.py            # Consultor IA com alertas contextuais
  cadastros.py            # Categorias, subcategorias, bancos e cartões
  onboarding.py           # Wizard de primeiro acesso
  admin.py                # Painel admin
scripts/                  # SQL de criação e migração do schema
```

---

## Como Rodar Localmente

### Pré-requisitos

- Python 3.11+
- Conta no [Supabase](https://supabase.com) com projeto criado
- Chave de API da [Anthropic](https://console.anthropic.com)
- (Opcional) Tesseract OCR instalado para extração de PDF por imagem

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/PapitoOpro/Financeiro-2026.git
cd Financeiro-2026

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure as credenciais
# Crie o arquivo .streamlit/secrets.toml com:
```

```toml
# .streamlit/secrets.toml
[supabase]
url = "https://xxxx.supabase.co"
key = "sua-anon-key"
db_host = "db.xxxx.supabase.co"
db_password = "sua-senha-db"

[anthropic]
api_key = "sk-ant-..."
```

```bash
# 4. Execute o schema do banco (pasta scripts/ — ordem: passo1 → passo4)

# 5. Rode o app
streamlit run app.py
```

---

## Banco de Dados

Todas as tabelas usam **RLS** — dados são isolados por usuário automaticamente.

| Tabela                | Descrição                              |
| --------------------- | -------------------------------------- |
| `usuarios`            | Perfis linkados ao Supabase Auth       |
| `contas`              | Contas bancárias e cartões             |
| `categorias`          | Categorias macro com % de orçamento    |
| `subcategorias`       | Categorias operacionais detalhadas     |
| `transacoes`          | Lançamentos diários (caixa)            |
| `limites_financeiros` | Limites personalizados por categoria   |
| `faturas`             | Faturas importadas via PDF             |
| `itens_fatura`        | Itens individuais de cada fatura       |

Para recriar o schema do zero: execute os scripts em `scripts/` na ordem `passo1 → passo4`.

---

## Variáveis de Ambiente

Todas as credenciais ficam em `.streamlit/secrets.toml` — **nunca commitar este arquivo**.
O `.gitignore` já está configurado para ignorá-lo.

---

## Licença

MIT
