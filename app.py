# ==========================================
# APLICAÇÃO PRINCIPAL - SISTEMA FINANCEIRO 2026
# ==========================================
# Arquitetura modularizada com separação de responsabilidades

import streamlit as st
import requests
import random
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
    page_title="Finanças IA Pro",
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    "<style>.block-container{padding-top:4rem!important}.stMainBlockContainer{padding-top:4rem!important}</style>",
    unsafe_allow_html=True,
)

# ==========================================
# FUNÇÃO DA API BÍBLICA (COM CACHE)
# ==========================================
# O ttl=3600 faz com que o versículo mude apenas de hora em hora.
# Isso evita lentidão no sistema a cada clique no menu.


@st.cache_data(ttl=3600)
def buscar_versiculo_financeiro():
    referencias = [
        "Proverbs+22:7",
        "Luke+14:28",
        "Proverbs+21:20",
        "Proverbs+13:11",
        "Romans+13:8",
        "Matthew+6:24",
        "Proverbs+10:4",
        "Proverbs+27:23"
    ]
    ref_escolhida = random.choice(referencias)
    url = f"https://bible-api.com/{ref_escolhida}?translation=almeida"

    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            dados = response.json()
            # Limpa quebras de linha para ficar bonito no layout
            texto = dados['text'].strip().replace("\n", " ")
            ref_formatada = dados['reference']
            return f'"{texto}" — {ref_formatada}'
        else:
            return '"Os planos bem elaborados levam à fartura; mas o apressado sempre acaba na miséria." — Provérbios 21:5'
    except:
        return '"Os planos bem elaborados levam à fartura; mas o apressado sempre acaba na miséria." — Provérbios 21:5'


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
    # Só força a tela padrão na primeira execução após login
    if 'just_logged_in' not in st.session_state:
        st.session_state.menu_selecionado = "Controle de Caixa"
        st.session_state.just_logged_in = True
    db.inicializar_dados_usuario(st.session_state.get('usuario_id'))

    # Verifica se precisa de onboarding
    if not db.usuario_completou_onboarding(st.session_state.get('usuario_id')):
        OnboardingManager.renderizar()
        st.stop()

    # Verifica se o usuário tem pelo menos uma conta/cartão cadastrada
    user_id = st.session_state.get('usuario_id')
    df_contas_check = db.buscar(
        "SELECT id FROM contas WHERE user_id = %s LIMIT 1",
        (user_id,)
    )
    if df_contas_check.empty:
        st.markdown("---")
        st.header("Cadastre seu primeiro Banco ou Cartão")
        st.info(
            "Para utilizar o sistema, é necessário cadastrar pelo menos "
            "um banco ou cartão. Você poderá adicionar mais depois em **Cadastros**."
        )
        with st.form("form_primeira_conta", clear_on_submit=True):
            nome_conta = st.text_input(
                "Nome do Banco/Cartão",
                placeholder="Ex: Nubank, Itaú, Bradesco..."
            )
            if st.form_submit_button("Cadastrar e Continuar", type="primary", width='stretch'):
                if (nome_conta or "").strip():
                    db.executar(
                        "INSERT INTO contas (nome, user_id) VALUES (%s, %s)",
                        (nome_conta.strip(), user_id)
                    )
                    st.success("Banco/Cartão cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Digite o nome do banco ou cartão.")
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
    /* Botões do menu lateral — alinhamento à esquerda */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        justify-content: flex-start !important;
        text-align: left !important;
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
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stButton > button div {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(6, 182, 212, 0.10);
        color: #fff;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
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

    /* ── TEMA COMPACTO / MINIMALISTA ── */

    /* Container principal: remove excesso de padding */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 1.8rem !important;
        padding-right: 1.8rem !important;
    }

    /* Reduz gap vertical entre todos os elementos */
    [data-testid="stVerticalBlock"] {
        gap: 0.45rem !important;
    }

    /* Botões menores e sem excesso de altura */
    .stButton > button {
        padding: 0.28rem 0.75rem !important;
        font-size: 0.82rem !important;
        border-radius: 6px !important;
        min-height: 1.9rem !important;
        height: auto !important;
        line-height: 1.3 !important;
    }

    /* Inputs de texto e número compactos */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        padding: 0.28rem 0.6rem !important;
        font-size: 0.84rem !important;
        min-height: 1.9rem !important;
    }

    /* Selectbox compacto */
    .stSelectbox > div > div > div {
        padding: 0.28rem 0.6rem !important;
        font-size: 0.84rem !important;
        min-height: 1.9rem !important;
    }

    /* Labels menores */
    .stTextInput label, .stSelectbox label, .stNumberInput label,
    .stDateInput label, .stRadio > label, .stCheckbox > label {
        font-size: 0.78rem !important;
        margin-bottom: 0.05rem !important;
        color: #aaa !important;
    }

    /* Tabs mais compactas */
    .stTabs [data-baseweb="tab"] {
        padding: 0.35rem 0.9rem !important;
        font-size: 0.83rem !important;
    }

    /* Expanders mais compactos */
    [data-testid="stExpander"] summary {
        padding: 0.4rem 0.7rem !important;
        font-size: 0.86rem !important;
    }

    /* Métricas menores */
    [data-testid="stMetric"] {
        padding: 0.5rem 0.7rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }

    /* Formulários com menos padding interno */
    [data-testid="stForm"] {
        padding: 0.8rem 1rem !important;
        border-radius: 8px !important;
    }

    /* Dividers mais finos */
    hr {
        margin: 0.4rem 0 !important;
    }

    /* Markdown: remove margem excessiva embaixo */
    .stMarkdown p {
        margin-bottom: 0.2rem !important;
    }

    /* Cabeçalhos de seção menores */
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.15rem !important; }
    h3 { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.sidebar.markdown(
    '<div class="sidebar-title">FINANÇAS PRO</div>', unsafe_allow_html=True)

# Chamada da API para gerar o versículo dinâmico
versiculo_do_momento = buscar_versiculo_financeiro()
st.sidebar.markdown(
    f'<div class="sidebar-subtitle">{versiculo_do_momento}</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")

# --- Menu de navegação ---
MENU_ITEMS = [
    ("🤖", "Consultor Financeiro"),
    ("💰", "Controle de Caixa"),
    ("📅", "Projeção de Gastos"),
    ("📋", "Cadastros"),
    ("📊", "Relatórios"),
    ("⚙️", "Admin"),
]

if "menu_selecionado" not in st.session_state:
    st.session_state.menu_selecionado = "Controle de Caixa"

st.sidebar.markdown('<div class="menu-container">', unsafe_allow_html=True)
for icone, label in MENU_ITEMS:
    is_active = st.session_state.menu_selecionado == label
    if st.sidebar.button(
        f"{label}" if not icone else f"{icone}  {label}",
        key=f"menu_{label}",
        type="primary" if is_active else "secondary",
        width='stretch',
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
if st.sidebar.button("🚪  Sair", width='stretch'):
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
