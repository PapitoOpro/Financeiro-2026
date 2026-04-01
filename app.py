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
from modules.relatorios import RelatoriosManager
from modules.consultor import ConsultorManager
from modules.acompanhamento import AcompanhamentoManager
from modules.onboarding import OnboardingManager

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Finanças Pro 2026",
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

# Inicializa dados do usuário logado (limites padrão, etc.)
if st.session_state.get('logado'):
    db.inicializar_dados_usuario(st.session_state.get('usuario_id'))

    # Verifica se precisa de onboarding
    if not db.usuario_completou_onboarding(st.session_state.get('usuario_id')):
        OnboardingManager.renderizar()
        st.stop()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.sidebar.title("FINANÇAS PRO 2026")
st.sidebar.markdown("---")

# Menu de navegação
menu = st.sidebar.radio(
    "📍 Módulos:",
    [
        "1- Controle de Caixa",
        "2- Acompanhamento",
        "3- Projeção de Gastos",
        "4- Cadastros",
        "5- Relatórios",
        "6- Consultor Financeiro",
        "7- Admin 🔧",
    ],
    key="main_menu"
)

# Space e botão logout
st.sidebar.markdown("---")
col_user, col_logout = st.sidebar.columns([1, 0.5])
col_user.caption(f"👤 {st.session_state.usuario_nome}")
if col_logout.button("Sair", width='stretch'):
    AuthManager.fazer_logout()

# ==========================================
# ROTEAMENTO DE PÁGINAS
# ==========================================
if menu == "1- Controle de Caixa":
    CaixaManager.renderizar()

elif menu == "2- Acompanhamento":
    AcompanhamentoManager.renderizar()

elif menu == "3- Projeção de Gastos":
    ParcelasManager.renderizar()

elif menu == "4- Cadastros":
    CadastrosManager.renderizar()

elif menu == "5- Relatórios":
    RelatoriosManager.renderizar()

elif menu == "6- Consultor Financeiro":
    ConsultorManager.renderizar()

elif menu == "7- Admin 🔧":
    AdminManager.renderizar()

# ==========================================
# RODAPÉ
# ==========================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "Finanças Pro 2026 | v1.0 | Desenvolvido com Streamlit"
    "</div>",
    unsafe_allow_html=True
)
