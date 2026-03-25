# ==========================================
# APLICAÇÃO PRINCIPAL - SISTEMA FINANCEIRO 2026
# ==========================================
# Arquitetura modularizada com separação de responsabilidades

import streamlit as st
from auth import AuthManager
from database import db
from config import MESES_LISTA
from modules.caixa import CaixaManager
from modules.cadastros import CadastrosManager
from modules.admin import AdminManager
from modules.parcelas_exemplo import ParcelasManager

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema Financeiro 2026",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# INICIALIZAÇÃO
# ==========================================
# Inicializa banco de dados
db.inicializar_banco()

# Inicializa autenticação
AuthManager.tela_login()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.sidebar.title("SISTEMA 2026")
st.sidebar.markdown("---")

# Menu de navegação
menu = st.sidebar.radio(
    "📍 Navegação:",
    [
        "1- Controle de Caixa",
        "2- Projeção de Gastos",
        "3- Cadastros",
        "4- Relatórios",
        "5- Admin 🔧",
    ],
    key="main_menu"
)

# Space e botão logout
st.sidebar.markdown("---")
col_user, col_logout = st.sidebar.columns([1, 0.5])
col_user.caption(f"👤 {st.session_state.usuario_nome}")
if col_logout.button("Sair", use_container_width=True):
    AuthManager.fazer_logout()

# ==========================================
# ROTEAMENTO DE PÁGINAS
# ==========================================
if menu == "1- Controle de Caixa":
    CaixaManager.renderizar()

elif menu == "2- Projeção de Gastos":
    ParcelasManager.renderizar()

elif menu == "3- Cadastros":
    CadastrosManager.renderizar()

elif menu == "4- Relatórios":
    st.header("📊 Relatórios Analíticos")
    st.info("ℹ️ Módulo em desenvolvimento...")

elif menu == "5- Admin 🔧":
    AdminManager.renderizar()

# ==========================================
# RODAPÉ
# ==========================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "Sistema Financeiro 2026 | v1.0 | Desenvolvido com Streamlit"
    "</div>",
    unsafe_allow_html=True
)
