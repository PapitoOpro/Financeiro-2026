# ==========================================
# MÓDULO: PAINEL ADMINISTRATIVO
# ==========================================

import streamlit as st
from database import db

class AdminManager:
    """Gerenciador de funções administrativas."""
    
    SENHA_ADMIN = "05072019" # MUDE ISSO em produção!
    
    @staticmethod
    def autenticar_admin():
        """Autentica acesso ao painel admin."""
        if 'admin_autenticado' not in st.session_state:
            st.session_state.admin_autenticado = False
        
        if not st.session_state.admin_autenticado:
            st.warning(" Acesso restrito a administrador")
            
            senha = st.text_input("Senha de Administrador", type="password", placeholder="Digite a senha")
            
            if st.button("Acessar Painel Admin"):
                if senha == AdminManager.SENHA_ADMIN:
                    st.session_state.admin_autenticado = True
                    st.success(" Acesso concedido!")
                    st.rerun()
                else:
                    st.error(" Senha incorreta!")
            
            st.stop()
    
    @staticmethod
    def renderizar():
        """Renderiza o painel administrativo."""
        AdminManager.autenticar_admin()
        
        st.header("Painel Administrativo")
        st.markdown("---")
        
        # Botão para sair do admin
        if st.button("Sair do Painel Admin", icon=":material/logout:"):
            st.session_state.admin_autenticado = False
            st.rerun()
        
        st.markdown("---")
        
        # Seções do admin
        tab1, tab2, tab3 = st.tabs(["Estatísticas", "Resetar Dados", "Usuários"])
        
        with tab1:
            AdminManager._tab_estatisticas()
        
        with tab2:
            AdminManager._tab_resetar()
        
        with tab3:
            AdminManager._tab_usuarios()
    
    @staticmethod
    def _tab_estatisticas():
        """Mostra estatísticas do banco."""
        st.subheader(" Estatísticas do Banco")
        
        # Contar registros
        usuarios = db.buscar("SELECT COUNT(*) as total FROM usuarios")
        contas = db.buscar("SELECT COUNT(*) as total FROM contas")
        categorias = db.buscar("SELECT COUNT(*) as total FROM categorias")
        transacoes = db.buscar("SELECT COUNT(*) as total FROM transacoes")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(" Usuários", usuarios['total'].values[0])
        col2.metric(" Contas", contas['total'].values[0])
        col3.metric(" Categorias", categorias['total'].values[0])
        col4.metric(" Transações", transacoes['total'].values[0])
        
        st.markdown("---")
        
        # Valor total de transações
        df_valores = db.buscar("""
            SELECT 
                SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as entradas,
                ABS(SUM(CASE WHEN valor < 0 THEN valor ELSE 0 END)) as saidas
            FROM transacoes
        """)
        
        ent = df_valores['entradas'].values[0] or 0
        sai = df_valores['saidas'].values[0] or 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric(" Entradas", f"R$ {ent:,.2f}")
        col2.metric(" Saídas", f"R$ {sai:,.2f}")
        col3.metric(" Balanço", f"R$ {ent - sai:,.2f}")
    
    @staticmethod
    def _tab_resetar():
        """Opções para resetar o banco."""
        st.subheader(" Resetar Dados")
        
        st.warning(
            " CUIDADO!\n\n"
            "Estas operações NÃO podem ser desfeitas. "
            "Faça backup antes de prosseguir!"
        )
        
        st.markdown("---")
        
        # Opção 1: Deletar dados
        st.markdown("### Opção 1: Deletar Dados (Manter Estrutura)")
        st.markdown(
            "Deleta TODOS os dados mas mantém as tabelas. "
            "Você pode começar do zero."
        )
        
        if st.button(
            "Deletar Todos os Dados",
            key="btn_delete_dados",
            width='stretch',
            icon=":material/delete:"
        ):
            with st.spinner("Deletando dados..."):
                AdminManager._deletar_dados()
        
        st.markdown("---")
        
        # Opção 2: Recriar tudo
        st.markdown("### Opção 2: Recriar Tudo (Nuclear)")
        st.markdown(
            "Deleta TODAS as tabelas e as recria do zero. "
            "Use apenas em caso de problemas graves."
        )
        
        if st.button(
            "Deletar Tudo e Recriar",
            key="btn_nuclear",
            width='stretch',
            icon=":material/delete_forever:"
        ):
            with st.spinner("Recriando banco..."):
                AdminManager._recriar_banco()
    
    @staticmethod
    def _tab_usuarios():
        """Gerenciar usuários com aprovação."""
        st.subheader(" Gerenciar Usuários")
        
        # Subabas para usuários pendentes e aprovados
        subTab1, subTab2 = st.tabs([" Pendentes de Aprovação", " Usuários Aprovados"])
        
        with subTab1:
            st.markdown("### Usuários Aguardando Aprovação")
            
            df_pendentes = db.buscar("""
                SELECT id, nome, email, data_criacao 
                FROM usuarios 
                WHERE aprovado = FALSE 
                ORDER BY data_criacao DESC
            """)
            
            if df_pendentes.empty:
                st.info(" Nenhum usuário aguardando aprovação")
            else:
                st.warning(f" {len(df_pendentes)} usuário(s) aguardando sua aprovação")
                
                for idx, row in df_pendentes.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 1.5, 1, 1])
                    
                    email_info = f" | {row['email']}" if row.get('email') else ""
                    col1.markdown(f"**{row['nome']}**{email_info}")
                    col2.caption(f" {row['data_criacao']}")
                    
                    if col3.button(" Aprovar", key=f"aprova_{row['id']}", width='stretch'):
                        db.executar("UPDATE usuarios SET aprovado = TRUE WHERE id = ?", (row['id'],))
                        st.success(f" Usuário '{row['username']}' aprovado!")
                        st.rerun()
                    
                    if col4.button(" Rejeitar", key=f"rejeita_{row['id']}", width='stretch'):
                        db.executar("DELETE FROM usuarios WHERE id = ?", (row['id'],))
                        st.success(f" Usuário '{row['username']}' rejeitado e deletado!")
                        st.rerun()
                    
                    st.divider()
        
        with subTab2:
            st.markdown("### Usuários Aprovados")
            
            df_aprovados = db.buscar("""
                SELECT id, nome, email, data_criacao 
                FROM usuarios 
                WHERE aprovado = TRUE 
                ORDER BY nome
            """)
            
            if df_aprovados.empty:
                st.info("Nenhum usuário aprovado ainda")
            else:
                df_exibir = df_aprovados.rename(columns={
                    'id': 'ID',
                    'nome': 'Nome',
                    'email': 'E-mail',
                    'data_criacao': 'Data de Criação'
                })
                st.dataframe(df_exibir, width='stretch', hide_index=True)
                
                st.markdown("---")
                st.markdown("### Deletar Usuário Aprovado")
                
                opcoes = df_aprovados.apply(
                    lambda r: f"{r['nome']} ({r['email']})", axis=1
                ).tolist()
                ids = df_aprovados['id'].tolist()
                
                sel = st.selectbox(
                    "Selecione usuário para deletar",
                    range(len(opcoes)),
                    format_func=lambda i: opcoes[i],
                    key="delete_user_select"
                )
                
                if st.button("Deletar Usuário", width='stretch', icon=":material/delete:"):
                    uid_del = ids[sel]
                    db.executar("DELETE FROM usuarios WHERE id = ?", (uid_del,))
                    st.success(f" Usuário deletado!")
                    st.rerun()
    
    @staticmethod
    def _deletar_dados():
        """Deleta todos os dados."""
        try:
            db.executar("DELETE FROM transacoes")
            db.executar("DELETE FROM limites_financeiros")
            db.executar("DELETE FROM contas")
            db.executar("DELETE FROM categorias")
            db.executar("DELETE FROM usuarios")
            
            st.success(" Todos os dados foram deletados!")
            st.info(" As tabelas foram mantidas. Você pode começar a adicionar novos dados.")
            
        except Exception as e:
            st.error(f" Erro ao deletar: {e}")
    
    @staticmethod
    def _recriar_banco():
        """Recria o banco do zero."""
        try:
            db.executar("DROP TABLE IF EXISTS transacoes")
            db.executar("DROP TABLE IF EXISTS limites_financeiros")
            db.executar("DROP TABLE IF EXISTS contas")
            db.executar("DROP TABLE IF EXISTS categorias")
            db.executar("DROP TABLE IF EXISTS usuarios")
            
            db.inicializar_banco()
            
            st.success(" Banco de dados foi completamente recriado!")
            st.balloons()
            
        except Exception as e:
            st.error(f" Erro ao recriar: {e}")
