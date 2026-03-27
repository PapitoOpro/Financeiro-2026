# ==========================================
# SISTEMA DE AUTENTICAÇÃO
# ==========================================

import streamlit as st
import bcrypt
import base64
import os
from database import db

class AuthManager:
    """Gerenciador de autenticação do sistema."""
    
    @staticmethod
    def inicializar_sessao():
        """Inicializa as variáveis de sessão."""
        if 'logado' not in st.session_state:
            st.session_state.logado = False
        if 'usuario_nome' not in st.session_state:
            st.session_state.usuario_nome = None
        if 'usuario_id' not in st.session_state:
            st.session_state.usuario_id = None
    
    @staticmethod
    def fazer_login(username, senha):
        """Autentica um usuário com verificação de aprovação."""
        res = db.buscar_um(
            "SELECT id, nome, senha, aprovado FROM usuarios WHERE username = ?", 
            (username,)
        )
        
        if not res:
            return False, "Usuário não encontrado"
        
        usuario_id, nome, senha_hash, aprovado = res
        
        # Valida a senha
        if not bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
            return False, "Senha incorreta"
        
        # Verifica se está aprovado
        if not aprovado:
            return False, "pendente"
        
        # Login bem-sucedido
        st.session_state.logado = True
        st.session_state.usuario_nome = nome
        st.session_state.usuario_id = usuario_id
        return True, "ok"
    
    @staticmethod
    def registrar_usuario(nome, username, senha):
        """Registra um novo usuário com status 'não aprovado' (ou aprovado se for o primeiro)."""
        if len(senha) < 6:
            st.error("❌ Senha deve ter pelo menos 6 caracteres.")
            return False
        
        hash_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Verifica se é o primeiro usuário
        count_usuarios = db.buscar_um("SELECT COUNT(*) FROM usuarios")
        eh_primeiro = count_usuarios[0] == 0
        
        # Auto-aprova o primeiro usuário
        aprovado = eh_primeiro
        
        sucesso = db.executar(
            "INSERT INTO usuarios (nome, username, senha, aprovado) VALUES (?, ?, ?, ?)",
            (nome, username, hash_senha, aprovado)
        )
        
        if sucesso:
            if eh_primeiro:
                st.success(
                    "✅ Primeiro usuário registrado com sucesso!\n\n"
                    "🎉 Você foi **automaticamente aprovado** como administrador.\n"
                    "Faça login agora com suas credenciais."
                )
            else:
                st.success(
                    "✅ Cadastro realizado com sucesso!\n\n"
                    "⏳ Seu usuário está **aguardando aprovação** do administrador.\n"
                    "Você receberá notificação quando for aprovado."
                )
        else:
            st.error("❌ Erro ao registrar. Username pode estar duplicado.")
        
        return sucesso
    
    @staticmethod
    def fazer_logout():
        """Faz logout do usuário."""
        st.session_state.logado = False
        st.session_state.usuario_nome = None
        st.session_state.usuario_id = None
        st.rerun()
    
    @staticmethod
    def tela_login():
        """Renderiza a tela de login/registro com design melhorado."""
        AuthManager.inicializar_sessao()
        
        if st.session_state.logado:
            return True
        
        # CSS customizado para melhor aparência (campos menores, topo mais leve)
        st.markdown("""
            <style>
            .login-container {
                max-width: 420px;
                margin: 10px auto 0;
                padding: 8px 10px;
            }
            .login-header {
                text-align: center;
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 6px;
                background: linear-gradient(120deg, #06b6d4 0%, #059669 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .login-welcome {
                text-align: center;
                font-size: 1rem;
                color: #444;
                margin-bottom: 12px;
            }
            .login-subtitle {
                text-align: center;
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 18px;
            }
            /* Restringe largura dos inputs dentro do container e reduz altura visual */ 
            .login-container input[type="text"], .login-container input[type="password"], .login-container .stTextInput>div>input {
                height: 36px !important;
                font-size: 0.95rem !important;
                padding: 6px 10px !important;
            }
            .login-container .stButton>button {
                padding: 8px 12px !important;
                font-size: 0.95rem !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Container centralizado e mais compacto (campos menores, alinhamento para o topo)
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)

            # Logo centralizada
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f:
                    logo_b64 = base64.b64encode(f.read()).decode()
                st.markdown(
                    f'<div style="text-align:center; margin-bottom:8px;">'
                    f'<img src="data:image/png;base64,{logo_b64}" style="max-width:220px; border-radius:12px;">'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown('<div class="login-header">📈 Finanças Pro 2026</div>', unsafe_allow_html=True)

            st.markdown('<div class="login-welcome">Seja bem-vindo.</div>', unsafe_allow_html=True)
            st.markdown('---')

            tab1, tab2 = st.tabs(["🔑 Login", "📝 Cadastro"])
            
            with tab1:
                st.subheader("Faça seu Login")
                
                with st.form("login_form"):
                    username = st.text_input(
                        "👤 Usuário",
                        placeholder="Digite seu usuário"
                    )
                    senha = st.text_input(
                        "🔐 Senha",
                        type="password",
                        placeholder="Digite sua senha"
                    )
                    
                    if st.form_submit_button("🔓 Entrar", width='stretch'):
                        if username and senha:
                            sucesso, status = AuthManager.fazer_login(username, senha)
                            
                            if sucesso:
                                st.success("✅ Login realizado com sucesso!")
                                st.rerun()
                            elif status == "pendente":
                                st.warning(
                                    "⏳ **Usuário Aguardando Aprovação**\n\n"
                                    "Seu cadastro foi recebido com sucesso, mas ainda está "
                                    "aguardando aprovação do administrador. Em breve você "
                                    "receberá acesso ao sistema."
                                )
                            else:
                                st.error(f"❌ {status}")
                        else:
                            st.error("❌ Preencha todos os campos.")
                
                st.markdown("---")
                st.markdown(
                    "<div style='text-align: center; font-size: 0.9em; color: #666;'>"
                    "Primeira vez aqui? Faça seu cadastro na aba ao lado →"
                    "</div>",
                    unsafe_allow_html=True
                )
            
            with tab2:
                st.subheader("Criar Nova Conta")
                
                with st.form("registro_form"):
                    nome = st.text_input(
                        "👤 Nome Completo",
                        placeholder="Seu nome completo"
                    )
                    username = st.text_input(
                        "🆔 Username",
                        placeholder="Escolha um usuário único (sem espaços)"
                    )
                    
                    col_pwd1, col_pwd2 = st.columns(2)
                    with col_pwd1:
                        senha = st.text_input(
                            "🔐 Senha",
                            type="password",
                            placeholder="Min. 6 caracteres"
                        )
                    with col_pwd2:
                        confirm_senha = st.text_input(
                            "🔒 Confirmar",
                            type="password",
                            placeholder="Digite novamente"
                        )
                    
                    st.info(
                        "ℹ️ Após cadastro, sua conta será **awaiting aprovação** "
                        "do administrador antes de poder fazer login."
                    )
                    
                    if st.form_submit_button("📝 Cadastrar", width='stretch'):
                        if nome and username and senha and confirm_senha:
                            if len(username) < 3:
                                st.error("❌ Username deve ter pelo menos 3 caracteres.")
                            elif senha != confirm_senha:
                                st.error("❌ As senhas não conferem.")
                            else:
                                AuthManager.registrar_usuario(nome, username, senha)
                        else:
                            st.error("❌ Preencha todos os campos.")
            
            st.markdown("---")
            st.markdown(
                "<div style='text-align: center; font-size: 0.85em; color: #999;'>"
                "Sistema Financeiro 2026 | Desenvolvido com Streamlit"
                "</div>",
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.stop()
