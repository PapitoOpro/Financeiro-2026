# 🏗️ Estrutura Modularizada - Sistema Financeiro 2026

## 📋 Visão Geral

O código foi refatorado em uma arquitetura modularizada, separando responsabilidades e facilitando manutenção e expansão.

## 📁 Estrutura de Diretórios

```
Financeiro-2026/
├── app_novo.py              ← 🚀 NOVO arquivo principal (substituir app.py)
├── config.py                ← ⚙️  Configurações e constantes
├── database.py              ← 🗄️  Camada de banco de dados
├── auth.py                  ← 🔐 Autenticação e login
├── utils.py                 ← 🛠️  Funções utilitárias
├── requirements.txt         ← 📦 Dependências
├── .streamlit/
│   └── secrets.toml         ← 🔑 Credenciais do BD (não compartilhar)
└── pages/                   ← 📄 Módulos das páginas
    ├── __init__.py
    ├── caixa.py             ← 💰 Controle de Caixa
    ├── cadastros.py         ← 📝 Contas e Categorias
    ├── parcelas.py          ← 💳 Projeção de Gastos (criar)
    └── relatorios.py        ← 📊 Relatórios (criar)
```

## 🔍 Responsabilidades de Cada Módulo

### 1. **app.py** (Principal)
- Orquestra toda a aplicação
- Define rotas/menu
- Inicializa componentes globais
- Renderiza a interface baseado na navegação

**Quando adicionar:** Novo menu ou integração entre módulos

---

### 2. **config.py** (Configurações)
Contém constantes e configurações globais:
- Lista de meses
- Bancos conhecidos
- Cores da UI
- Tamanhos de coluna
- Tipos de fluxo

**Quando modificar:** Adicionar novas constantes ou mudar configurações globais

---

### 3. **database.py** (Banco de Dados)
Classe `DatabaseManager` centraliza todas operações:
- Conexão ao Supabase
- `conectar()` - Abre conexão
- `executar()` - INSERT, UPDATE, DELETE com commit
- `buscar()` - SELECT retorna DataFrame
- `buscar_um()` - SELECT retorna uma linha
- `inicializar_banco()` - Cria tabelas

**Quando modificar:** Alterar estrutura do BD ou adicionar novas queries

---

### 4. **auth.py** (Autenticação)
Classe `AuthManager` gerencia login/registro:
- `fazer_login()` - Autentica usuário
- `registrar_usuario()` - Cria novo usuário
- `tela_login()` - Renderiza página de login
- `fazer_logout()` - Faz logoff

**Quando modificar:** Mudar lógica de autenticação ou adicionar 2FA

---

### 5. **utils.py** (Utilitários)
Classe `UtilsManager` centraliza funções reutilizáveis:
- `formatar_moeda()` - Formata valores em BRL
- `remover_acentos()` - Remove acentuação
- `extrair_texto_pdf()` - OCR do PDF
- `detectar_banco()` - Identifica banco pelo texto
- `extrair_parcelas()` - Extrai parcelas do PDF
- `get_cor_saldo()` / `get_cor_valor()` - Cores dinamicamente

**Quando modificar:** Adicionar novas funções utilitárias reutilizáveis

---

### 6. **pages/caixa.py** (Controle de Caixa)
Classe `CaixaManager` renderiza a página de caixa:
- `renderizar()` - Inicializa a página
- `_renderizar_cards()` - Cards de resumo (entradas/saídas)
- `_renderizar_formulario()` - Formulário de novo lançamento
- `_renderizar_extrato()` - Lista de transações
- `_popover_editar()` - Modal de edição

**Quando modificar:** Alterar layout ou adicionar funcionalidades de caixa

---

### 7. **pages/cadastros.py** (Cadastros)
Classe `CadastrosManager` gerencia contas e categorias:
- `renderizar()` - Inicializa a página
- `_secao_contas()` - CRUD de bancos/cartões
- `_secao_categorias()` - CRUD de categorias

**Quando modificar:** Alterar interface de cadastros

---

## 🚀 Como Usar

### 1. **Substituir o arquivo principal**
```bash
# Renomear o arquivo antigo
mv app.py app_old.py

# Renomear o novo
mv app_novo.py app.py
```

### 2. **Rodar a aplicação**
```bash
streamlit run app.py
```

---

## 📝 Como Adicionar um Novo Módulo

### Exemplo: Adicionar página de "Exportar Dados"

**1. Criar novo arquivo `pages/exportar.py`:**
```python
import streamlit as st
from database import db
from utils import moeda

class ExportarManager:
    @staticmethod
    def renderizar():
        st.header("📥 Exportação de Dados")
        
        if st.button("Exportar para Excel"):
            df = db.buscar("SELECT * FROM transacoes")
            st.download_button(
                label="Baixar Excel",
                data=df.to_excel(),
                file_name="financeiro.xlsx"
            )
```

**2. Importar em `app.py`:**
```python
from pages.exportar import ExportarManager
```

**3. Adicionar ao menu:**
```python
menu = st.sidebar.radio("📍 Navegação:", [
    "1- Controle de Caixa",
    "2- Projeção de Gastos",
    "3- Cadastros",
    "4- Relatórios",
    "5- Exportar",  ← NOVO
])
```

**4. Adicionar rota:**
```python
elif menu == "5- Exportar":
    ExportarManager.renderizar()
```

---

## 🔄 Fluxo de Dados

```
app.py (Principal)
  ├─→ AuthManager (Login)
  ├─→ database.db (Inicializa tabelas)
  └─→ Renderiza Página Selecionada
      ├─→ CaixaManager.renderizar()
      │   ├─→ db.buscar()
      │   ├─→ moeda() [de utils]
      │   └─→ db.executar() [INSERT/UPDATE/DELETE]
      │
      ├─→ CadastrosManager.renderizar()
      │   ├─→ db.buscar()
      │   └─→ db.executar()
      │
      └─→ [Outros módulos...]
```

---

## ✅ Benefícios da Modularização

| Benefício | Descrição |
|-----------|-----------|
| 🎯 **Clareza** | Cada arquivo tem responsabilidade única |
| 🐛 **Manutenção** | Fácil localizar e corrigir bugs |
| ♻️ **Reutilização** | Funções reutilizáveis em múltiplos módulos |
| 📈 **Escalabilidade** | Adicionar novos módulos sem afetar existentes |
| 👥 **Colaboração** | Múltiplos devs podem trabalhar em paralelo |
| 🧪 **Testes** | Mais fácil testar módulos isolados |

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pages'"
**Solução:** Verifique se existe `pages/__init__.py`

### "Erro de conexão ao BD"
**Solução:** Verifique `.streamlit/secrets.toml` e credenciais

### "Função não encontrada"
**Solução:** Verifique se foi importada corretamente em `app.py`

---

## 📚 Próximas Melhorias

- [ ] Criar `pages/parcelas.py` (Projeção de Gastos)
- [ ] Criar `pages/relatorios.py` (Relatórios ABC)
- [ ] Adicionar testes unitários em `tests/`
- [ ] Implementar cache com `@st.cache_data`
- [ ] Adicionar logging com `logging` module
- [ ] Criar ficheiro `.env` para variáveis locais

---

**Desenvolvido com ❤️ | Streamlit + Modularização = 🚀**
