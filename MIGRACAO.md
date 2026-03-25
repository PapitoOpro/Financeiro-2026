# 📋 Guia de Migração para Arquitetura Modularizada

## 🎯 Objetivo
Migrar do arquivo `app.py` monolítico para uma arquitetura modularizada e escalável.

## ⚠️ Antes de Começar

1. **Faça backup** do seu código atual:
   ```bash
   git add .
   git commit -m "Backup antes da modularização"
   ```

2. **Verifique seu ambiente**:
   ```bash
   python --version  # Python 3.8+
   pip list | grep streamlit
   ```

## 📁 Passo 1: Estrutura de Diretórios

Crie a seguinte estrutura no seu projeto:

```
Financeiro-2026/
├── config.py           ← novos arquivos
├── database.py         ← novos arquivos
├── auth.py             ← novos arquivos
├── utils.py            ← novos arquivos
├── app_novo.py         ← novo arquivo principal
├── app.py              ← arquivo antigo (renomear depois)
├── pages/              ← nova pasta
│   ├── __init__.py
│   ├── caixa.py
│   └── cadastros.py
├── requirements.txt
└── .streamlit/
    └── secrets.toml
```

## 📝 Passo 2: Copiar Novos Arquivos

Copie os seguintes arquivos criados para seu projeto:

- ✅ `config.py`
- ✅ `database.py`
- ✅ `auth.py`
- ✅ `utils.py`
- ✅ `pages/caixa.py`
- ✅ `pages/cadastros.py`
- ✅ `pages/__init__.py`
- ✅ `app_novo.py`

## 🧪 Passo 3: Testar Nova Arquitetura

```bash
# Terminal 1: Sua máquina
streamlit run app_novo.py

# Testes
- [ ] Login funciona?
- [ ] Controle de Caixa carrega?
- [ ] Cadastros funcionam?
- [ ] Botões de edição/delete funcionam?
```

## ✨ Passo 4: Migrar dados (Opcional)

Se você tinha dados no `app.py` antigo, importe-os:

```python
# No terminal Python
from database import db
import pandas as pd

# Inicializar BD com tabelas novas
db.inicializar_banco()

# Seus dados continuarão lá (mesmo BD)
```

## 🔄 Passo 5: Substituir Arquivo Principal

```bash
# Opção 1: Simples (sem versionamento)
del app.py
rename app_novo.py app.py

# Opção 2: Seguro (com versionamento)
git mv app.py app_old_backup.py
git mv app_novo.py app.py
git commit -m "refactor: Migrar para arquitetura modularizada"
```

## 📦 Passo 6: Atualizar requirements.txt (se necessário)

Certifique-se de que tem todas as dependências:

```bash
pip freeze > requirements.txt
```

Ou verifique manualmente:

```
streamlit>=1.28.0
pandas>=1.5.0
psycopg2-binary>=2.9.0
bcrypt>=4.0.0
python-dateutil>=2.8.0
PyPDF2>=3.0.0
pytesseract>=0.3.10
Pillow>=9.0.0
plotly>=5.0.0
```

## 🚀 Passo 7: Deploy em Produção

### Streamlit Cloud

1. Faça push para GitHub:
   ```bash
   git add .
   git commit -m "Modularizar código"
   git push origin main
   ```

2. Vá para [Streamlit Cloud](https://share.streamlit.io)

3. Clique "New App" → Selecione seu repositório → Selecione `app.py`

4. Configure variáveis em Settings:
   ```
   db_host = seu-supabase.supabase.co
   db_name = postgres
   db_user = postgres
   db_password = sua_senha
   db_port = 5432
   ```

### Heroku

```bash
# 1. Login
heroku login

# 2. Criar app
heroku create seu-app-financeiro

# 3. Adicionar buildpack Python
heroku buildpacks:add heroku/python

# 4. Configurar secrets
heroku config:set db_host=... db_name=... etc

# 5. Deploy
git push heroku main
```

## 🐛 Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'pages'"
**Solução:**
```bash
# Certifique-se que existe pages/__init__.py
touch pages/__init__.py

# Se ainda não funcionar, reinicie:
streamlit run app.py --logger.level=debug
```

### ❌ "ImportError: cannot import name 'db'"
**Solução:** Verifique se os arquivos estão no mesmo diretório de `app.py`
```bash
ls -la  # Deve mostrar config.py, database.py, etc
```

### ❌ "Error connecting to database"
**Solução:** Verifique `.streamlit/secrets.toml`:
```bash
cat .streamlit/secrets.toml
# Deve ter: db_host, db_name, db_user, db_password, db_port
```

## 📚 Próximas Melhorias

Agora que você tem a arquitetura modularizada, você pode:

### 1. Adicionar testes
```bash
# Criar pasta tests/
mkdir tests

# Criar arquivo tests/test_utils.py
```

### 2. Adicionar logging
```python
# No app.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### 3. Criar CI/CD
```bash
# Criar .github/workflows/tests.yml para rodar testes
```

### 4. Adicionar nova página
```bash
# Criar pages/relatorios.py
# Adicionar ao menu em app.py
# Pronto!
```

## ✅ Checklist Final

- [ ] Todos os arquivos novos criados
- [ ] `app_novo.py` testado localmente
- [ ] Dados migrados corretamente
- [ ] Arquivo principal renomeado de `app_novo.py` para `app.py`
- [ ] Requirements.txt atualizado
- [ ] `.gitignore` configurado
- [ ] Push para GitHub
- [ ] Deploy em produção (opcional)
- [ ] Arquivo antigo `app_old_backup.py` removido depois confirmar tudo

## 🎉 Parabéns!

Sua aplicação agora é:

✅ **Modularizada** - Código organizado em responsabilidades  
✅ **Escalável** - Fácil adicionar novas funcionalidades  
✅ **Manutenível** - Simples encontrar e corrigir bugs  
✅ **Profissional** - Segue padrões de desenvolvimento  

---

**Próximo passo:** Leia [README_MODULARIZACAO.md](README_MODULARIZACAO.md) para entender toda a nova arquitetura!
