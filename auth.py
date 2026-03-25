# ==========================================
# SISTEMA DE AUTENTICAÇÃO
# ==========================================

import streamlit as st
import bcrypt
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
    
    @staticmethod
    def fazer_login(username, senha):
        """Autentica um usuário."""
        res = db.buscar_um(
            "SELECT nome, senha FROM usuarios WHERE username = ?", 
            (username,)
        )
        
        if res and bcrypt.checkpw(senha.encode('utf-8'), res[1].encode('utf-8')):
            st.session_state.logado = True
            st.session_state.usuario_nome = res[0]
            return True
        return False
    
    @staticmethod
    def registrar_usuario(nome, username, senha):
        """Registra um novo usuário."""
        if len(senha) < 6:
            st.error("❌ Senha deve ter pelo menos 6 caracteres.")
            return False
        
        hash_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        sucesso = db.executar(
            "INSERT INTO usuarios (nome, username, senha) VALUES (?, ?, ?)",
            (nome, username, hash_senha)
        )
        
        if sucesso:
            st.success("✅ Usuário registrado com sucesso! Faça login agora.")
        else:
            st.error("❌ Erro ao registrar. Username pode estar duplicado.")
        
        return sucesso
    
    @staticmethod
    def fazer_logout():
        """Faz logout do usuário."""
        st.session_state.logado = False
        st.session_state.usuario_nome = None
        st.rerun()
    
    @staticmethod
    def tela_login():
        """Renderiza a tela de login/registro."""
        AuthManager.inicializar_sessao()
        
        if st.session_state.logado:
            return True
        
        st.title("🔐 Acesso ao Sistema 2026")
        
        tab1, tab2 = st.tabs(["Login", "Cadastrar Novo Usuário"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Entrar", use_container_width=True):
                    if username and senha:
                        if AuthManager.fazer_login(username, senha):
                            st.success("✅ Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Username ou senha incorretos.")
                    else:
                        st.error("❌ Preencha todos os campos.")
        
        with tab2:
            with st.form("registro_form"):
                nome = st.text_input("Nome completo")
                username = st.text_input("Username (login único)")
                senha = st.text_input("Senha", type="password")
                confirm_senha = st.text_input("Confirmar senha", type="password")
                
                if st.form_submit_button("Cadastrar", use_container_width=True):
                    if nome and username and senha and confirm_senha:
                        if senha != confirm_senha:
                            st.error("❌ As senhas não conferem.")
                        else:
                            AuthManager.registrar_usuario(nome, username, senha)
                    else:
                        st.error("❌ Preencha todos os campos.")
        
        st.stop()
