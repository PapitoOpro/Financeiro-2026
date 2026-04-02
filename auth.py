# ==========================================
# SISTEMA DE AUTENTICAÇÃO (Supabase Auth)
# ==========================================

import streamlit as st
import base64
import os
from database import db


class AuthManager:
    """Gerenciador de autenticação via Supabase Auth."""

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
    def fazer_login(email, senha):
        """Autentica via Supabase Auth e verifica aprovação no perfil local."""
        supa = db.get_supabase()
        if not supa:
            return False, "Erro de conexão com Supabase"

        try:
            res = supa.auth.sign_in_with_password({"email": email, "password": senha})
        except Exception as e:
            msg = str(e)
            if "Invalid login" in msg or "invalid" in msg.lower():
                return False, "E-mail ou senha incorretos"
            if "Email not confirmed" in msg:
                return False, "confirmar_email"
            return False, f"Erro: {msg}"

        if not res.user:
            return False, "Erro de autenticação"

        auth_uid = res.user.id

        # Busca perfil local na tabela usuarios
        perfil = db.buscar_um(
            "SELECT id, nome, aprovado FROM usuarios WHERE auth_id = %s",
            (auth_uid,)
        )

        if not perfil:
            return False, "Perfil não encontrado. Contacte o administrador."

        usuario_id, nome, aprovado = perfil

        # Auto-aprova se ainda não estava aprovado
        if not aprovado:
            db.executar("UPDATE usuarios SET aprovado = TRUE WHERE id = %s", (usuario_id,))

        # Login bem-sucedido
        st.session_state.logado = True
        st.session_state.usuario_nome = nome
        st.session_state.usuario_id = usuario_id
        db.inicializar_dados_usuario(usuario_id)
        return True, "ok"

    @staticmethod
    def registrar_usuario(nome, email, senha):
        """Registra via Supabase Auth e cria perfil local."""
        if len(senha) < 6:
            st.error(" Senha deve ter pelo menos 6 caracteres.")
            return False

        supa = db.get_supabase()
        if not supa:
            st.error(" Erro de conexão com Supabase.")
            return False

        # 1. Cria usuário no Supabase Auth
        try:
            res = supa.auth.sign_up({"email": email, "password": senha})
        except Exception as e:
            msg = str(e)
            if "already registered" in msg.lower() or "already been registered" in msg.lower():
                st.error(" Este e-mail já está cadastrado. Tente fazer login.")
            else:
                st.error(f" Erro no cadastro: {msg}")
            return False

        if not res.user:
            st.error(" Erro ao criar conta. Tente novamente.")
            return False

        auth_uid = res.user.id

        # 2. Cria perfil local na tabela usuarios (auto-aprovado)
        sucesso = db.executar(
            "INSERT INTO usuarios (nome, email, auth_id, aprovado) VALUES (%s, %s, %s, %s)",
            (nome, email, auth_uid, True)
        )

        if sucesso:
            st.success(
                " Cadastro realizado com sucesso!\n\n"
                " Faça login agora com seu e-mail e senha."
            )
        else:
            st.error(" Erro ao criar perfil. E-mail pode estar duplicado.")

        return sucesso

    @staticmethod
    def fazer_logout():
        """Faz logout do Supabase Auth e limpa sessão."""
        try:
            supa = db.get_supabase()
            if supa:
                supa.auth.sign_out()
        except Exception:
            pass
        st.session_state.logado = False
        st.session_state.usuario_nome = None
        st.session_state.usuario_id = None
        st.rerun()

    @staticmethod
    def tela_login():
        """Renderiza a tela de login/registro."""
        AuthManager.inicializar_sessao()

        if st.session_state.logado:
            return True

        # CSS customizado
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
                font-size: 1.3rem;
                color: #ffffff;
                margin-bottom: 12px;
            }
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

        col1, col2, col3 = st.columns([1.5, 1, 1.5])

        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)

            # Logo
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
                st.markdown('<div class="login-header"> Finanças Pro 2026</div>', unsafe_allow_html=True)

            st.markdown('<div class="login-welcome">Seja bem-vindo.</div>', unsafe_allow_html=True)
            st.markdown(
                "<div style='text-align: center; margin: 2px 0 16px 0;'>"
                "<a href='?guia=1' "
                "target='_blank' style='color: #3498db; font-size: 0.85em; text-decoration: none;'>"
                "Guia de Uso do Sistema"
                "</a></div>",
                unsafe_allow_html=True
            )

            # Botões Login / Cadastro
            if "login_modo" not in st.session_state:
                st.session_state.login_modo = "login"

            bl, br = st.columns(2)
            if bl.button("Login", width='stretch',
                         type="primary" if st.session_state.login_modo == "login" else "secondary"):
                st.session_state.login_modo = "login"
                st.rerun()
            if br.button("Cadastro", width='stretch',
                         type="primary" if st.session_state.login_modo == "cadastro" else "secondary"):
                st.session_state.login_modo = "cadastro"
                st.rerun()

            if st.session_state.login_modo == "login":

                with st.form("login_form"):
                    email = st.text_input(
                        "E-mail",
                        placeholder="Digite seu e-mail"
                    )
                    senha = st.text_input(
                        "Senha",
                        type="password",
                        placeholder="Digite sua senha"
                    )

                    if st.form_submit_button("Entrar", width='stretch'):
                        if email and senha:
                            sucesso, status = AuthManager.fazer_login(email, senha)

                            if sucesso:
                                st.success("Login realizado com sucesso!")
                                st.rerun()
                            elif status == "pendente":
                                st.warning(
                                    "**Usuário Aguardando Aprovação**\n\n"
                                    "Seu cadastro foi recebido com sucesso, mas ainda está "
                                    "aguardando aprovação do administrador. Em breve você "
                                    "receberá acesso ao sistema."
                                )
                            elif status == "confirmar_email":
                                st.warning(
                                    "**Confirme seu e-mail**\n\n"
                                    "Verifique sua caixa de entrada e clique no link de "
                                    "confirmação enviado pelo Supabase."
                                )
                            else:
                                st.error(f"{status}")
                        else:
                            st.error("Preencha todos os campos.")

            else:

                with st.form("registro_form"):
                    nome = st.text_input(
                        "Nome Completo",
                        placeholder="Seu nome completo"
                    )
                    email = st.text_input(
                        "E-mail",
                        placeholder="seu@email.com"
                    )

                    col_pwd1, col_pwd2 = st.columns(2)
                    with col_pwd1:
                        senha = st.text_input(
                            "Senha",
                            type="password",
                            placeholder="Min. 6 caracteres"
                        )
                    with col_pwd2:
                        confirm_senha = st.text_input(
                            "Confirmar",
                            type="password",
                            placeholder="Digite novamente"
                        )

                    if st.form_submit_button("Cadastrar", width='stretch'):
                        if nome and email and senha and confirm_senha:
                            if '@' not in email or '.' not in email:
                                st.error("E-mail inválido.")
                            elif senha != confirm_senha:
                                st.error("As senhas não conferem.")
                            else:
                                AuthManager.registrar_usuario(nome, email, senha)
                        else:
                            st.error("Preencha todos os campos.")

            st.markdown(
                "<div style='text-align: center; font-size: 0.85em; color: #999; margin-top: 16px;'>"
                "Sistema Financeiro 2026 | Desenvolvido com Streamlit"
                "</div>",
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.stop()
