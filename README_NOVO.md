# 💰 Sistema Financeiro 2026

Aplicação web moderna para controle financeiro pessoal, desenvolvida com **Streamlit** e **PostgreSQL** (Supabase).

## ✨ Funcionalidades

- 📊 **Controle de Caixa** - Gerenciamento de entradas e saídas
- 💳 **Projeção de Gastos** - Acompanhamento de parcelados e faturas
- 🏷️ **Cadastros** - Gerenciamento de contas, cartões e categorias
- 📈 **Relatórios** - Análise inteligente com Curva ABC
- 🔐 **Autenticação** - Login seguro com hashing de senhas

## 🏗️ Arquitetura Modularizada

A aplicação foi refatorada em uma arquitetura **modularizada** para melhor manutenibilidade:

```
├── app.py              → Arquivo principal (orquestreur)
├── config.py           → Constantes e configurações
├── database.py         → Gerenciador de banco de dados
├── auth.py             → Sistema de autenticação
├── utils.py            → Funções utilitárias
└── pages/              → Módulos de cada página
    ├── caixa.py        → Controle de Caixa
    └── cadastros.py    → Cadastros de contas e categorias
```

📚 **Leia [README_MODULARIZACAO.md](README_MODULARIZACAO.md)** para entender toda a arquitetura.

## 🚀 Instalação Rápida

### 1. Clonar repositório
```bash
git clone https://github.com/seu-usuario/Financeiro-2026.git
cd Financeiro-2026
```

### 2. Criar ambiente virtual
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar banco de dados
Crie o arquivo `.streamlit/secrets.toml`:

```toml
db_host = "seu-supabase.supabase.co"
db_name = "postgres"
db_user = "postgres"
db_password = "sua-senha"
db_port = "5432"
```

### 5. Rodar a aplicação
```bash
streamlit run app.py
```

Acesse em: **http://localhost:8501**

## 📦 Dependências

- `streamlit` - Framework web
- `pandas` - Manipulação de dados
- `psycopg2-binary` - Driver PostgreSQL
- `bcrypt` - Hash de senhas
- `python-dateutil` - Calendário
- `PyPDF2` - Leitura de PDFs
- `pytesseract` - OCR
- `Pillow` - Processamento de imagens
- `plotly` - Gráficos interativos

## 🔐 Variáveis de Ambiente

Não compartilhe o arquivo `.streamlit/secrets.toml`! Adicione ao `.gitignore`:

```
.streamlit/secrets.toml
.env
*.pyc
__pycache__/
```

## 💡 Exemplos de Uso

### Adicionar novo lançamento (Caixa)
```python
from database import db

db.executar(
    "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CAIXA')",
    ("Salário", 5000.00, "2026-03-25", 1, 1)
)
```

### Buscar transações
```python
df = db.buscar("SELECT * FROM transacoes WHERE tipo_fluxo = ?", ("CAIXA",))
```

### Formatar moeda
```python
from utils import moeda

print(moeda(1234.56))  # R$ 1.234,56
```

## 📊 Estrutura do Banco

### Tabelas

**`usuarios`**
- id (PK)
- nome
- username (UNIQUE)
- senha

**`contas`**
- id (PK)
- nome

**`categorias`**
- id (PK)
- nome

**`transacoes`**
- id (PK)
- descricao
- valor
- data_vencimento
- conta_id (FK)
- categoria_id (FK)
- tipo_fluxo (CAIXA | CARTAO)

## 🛠️ Desenvolvimento

### Adicionar nova página

1. Criar arquivo `pages/nova_pagina.py`:
```python
import streamlit as st
from database import db

class NovaManager:
    @staticmethod
    def renderizar():
        st.header("Nova Página")
        # Sua implementação aqui
```

2. Importar em `app.py`:
```python
from pages.nova_pagina import NovaManager
```

3. Adicionar ao menu:
```python
menu = st.sidebar.radio("Navegação:", [..., "5- Nova Página"])
```

4. Renderizar:
```python
elif menu == "5- Nova Página":
    NovaManager.renderizar()
```

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| ModuleNotFoundError | Verifique se `pages/__init__.py` existe |
| Erro de conexão BD | Confira credenciais em `.streamlit/secrets.toml` |
| OCR não funciona | Instale tesseract: `choco install tesseract` (Windows) |

## 📝 Roadmap

- [ ] Dashboard com KPIs
- [ ] Exportação para Excel/PDF
- [ ] Integração com APIs de banco
- [ ] Gráficos avançados
- [ ] Testes automatizados
- [ ] Deploy em produção

## 📄 Licença

MIT License - veja LICENSE.md

## 👨‍💻 Autor

Desenvolvido com ❤️

---

**💬 Dúvidas?** Abra uma issue no repositório!
