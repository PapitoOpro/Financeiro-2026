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
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# PÁGINA DO GUIA DE USO (acesso público)
# ==========================================
if st.query_params.get("guia"):
    st.markdown(
        "<div style='max-width: 800px; margin: 0 auto;'>",
        unsafe_allow_html=True
    )
    try:
        with open("GUIA_USO.md", "r", encoding="utf-8") as f:
            st.markdown(f.read())
    except FileNotFoundError:
        st.error("Arquivo GUIA_USO.md não encontrado.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

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

# --- CSS do menu lateral moderno ---
st.markdown("""
<style>
    /* Esconder radio buttons padrão */
    section[data-testid="stSidebar"] .stRadio {display: none;}

    /* Título sidebar */
    .sidebar-title {
        font-size: 1.4rem;
        font-weight: 800;
        text-align: center;
        padding: 0.5rem 0 0.2rem;
        background: linear-gradient(120deg, #06b6d4, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 0.5px;
    }
    .sidebar-subtitle {
        text-align: center;
        font-size: 0.75rem;
        color: #888;
        margin-bottom: 0.8rem;
    }

    /* Botões do menu */
    section[data-testid="stSidebar"] div.menu-container button {
        width: 100%;
        text-align: left;
        padding: 0.55rem 0.9rem;
        margin-bottom: 2px;
        border: none;
        border-radius: 10px;
        background: transparent;
        color: #ccc;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] div.menu-container button:hover {
        background: rgba(6, 182, 212, 0.10);
        color: #fff;
    }
    section[data-testid="stSidebar"] div.menu-container button[kind="primary"] {
        background: linear-gradient(135deg, rgba(6,182,212,0.18), rgba(5,150,105,0.13));
        color: #06b6d4;
        font-weight: 700;
        border-left: 3px solid #06b6d4;
    }

    /* User footer */
    .sidebar-user {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0.5rem 0.8rem;
        border-radius: 10px;
        background: rgba(255,255,255,0.04);
        margin-top: 0.5rem;
    }
    .sidebar-user-name {
        font-size: 0.82rem;
        color: #aaa;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.sidebar.markdown('<div class="sidebar-title">FINANÇAS PRO</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-subtitle">Controle Financeiro</div>', unsafe_allow_html=True)
st.sidebar.markdown("---")

# --- Menu de navegação ---
MENU_ITEMS = [
    ("", "Consultor Financeiro"),
    ("", "Controle de Caixa"),
    ("", "Projeção de Gastos"),
    ("", "Cadastros"),
    ("", "Relatórios"),
    ("", "Admin"),
]

if "menu_selecionado" not in st.session_state:
    st.session_state.menu_selecionado = "Consultor Financeiro"

st.sidebar.markdown('<div class="menu-container">', unsafe_allow_html=True)
for icone, label in MENU_ITEMS:
    is_active = st.session_state.menu_selecionado == label
    if st.sidebar.button(
        f"{label}" if not icone else f"{icone}  {label}",
        key=f"menu_{label}",
        type="primary" if is_active else "secondary",
        use_container_width=True,
    ):
        st.session_state.menu_selecionado = label
        st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# --- Rodapé do sidebar ---
st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<div class="sidebar-user">👤 <span class="sidebar-user-name">{st.session_state.usuario_nome}</span></div>',
    unsafe_allow_html=True
)
if st.sidebar.button("🚪  Sair", use_container_width=True):
    AuthManager.fazer_logout()
st.sidebar.markdown(
    "<div style='text-align: center; margin-top: 8px;'>"
    "<a href='?guia=1' "
    "target='_blank' style='color: #3498db; font-size: 0.95em; text-decoration: none;'>"
    "Guia de Uso"
    "</a></div>",
    unsafe_allow_html=True
)
menu = st.session_state.menu_selecionado

# ==========================================
# ROTEAMENTO DE PÁGINAS
# ==========================================
if menu == "Controle de Caixa":
    CaixaManager.renderizar()

elif menu == "Projeção de Gastos":
    ParcelasManager.renderizar()

elif menu == "Cadastros":
    CadastrosManager.renderizar()

elif menu == "Relatórios":
    RelatoriosManager.renderizar()

elif menu == "Consultor Financeiro":
    ConsultorManager.renderizar()

elif menu == "Admin":
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
