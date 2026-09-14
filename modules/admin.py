# ==========================================
# MÓDULO: PAINEL ADMINISTRATIVO
# ==========================================

import streamlit as st
import pandas as pd
from database import db

class AdminManager:
    @staticmethod
    def limpar_residuos_e_sincronizar():
        """Remove resíduos de transações e itens órfãos e sincroniza faturas."""
        user_id = db.get_user_id()
        # Remove transações do caixa que referenciam faturas inexistentes
        db.executar("""
            DELETE FROM transacoes
            WHERE fatura_id IS NOT NULL
            AND fatura_id NOT IN (SELECT id FROM faturas)
            AND user_id = %s
        """, (user_id,))
        # Remove itens de fatura órfãos
        db.executar("""
            DELETE FROM itens_fatura
            WHERE fatura_id NOT IN (SELECT id FROM faturas)
            AND user_id = %s
        """, (user_id,))
        # Recalcula totais e sincroniza transações para todas as faturas do usuário
        faturas = db.buscar("SELECT id FROM faturas WHERE user_id = %s", (user_id,))
        for _, row in faturas.iterrows():
            db.atualizar_total_fatura(row['id'])
            db.sincronizar_transacao_fatura(row['id'], user_id)
    """Gerenciador de funções administrativas."""
    
    @staticmethod
    def _senha_admin() -> str:
        try:
            return str(st.secrets["ADMIN_PASSWORD"])
        except (KeyError, AttributeError):
            return ""
    
    @staticmethod
    def autenticar_admin():
        """Autentica acesso ao painel admin."""
        if 'admin_autenticado' not in st.session_state:
            st.session_state.admin_autenticado = False
        
        if not st.session_state.admin_autenticado:
            st.warning(" Acesso restrito a administrador")
            
            senha = st.text_input("Senha de Administrador", type="password", placeholder="Digite a senha")
            
            if st.button("Acessar Painel Admin"):
                if senha == AdminManager._senha_admin():
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
        

        st.markdown("---")
        # Opção 3: Recalcular/Sincronizar Faturas
        st.markdown("### Opção 3: Recalcular/Sincronizar Faturas e Caixa")
        st.markdown(
            "Remove resíduos de exclusões e sincroniza totais de faturas e transações do caixa. "
            "Use se os valores do consultor ou caixa parecerem incorretos após muitos testes."
        )
        if st.button(
            "Recalcular/Sincronizar Faturas",
            key="btn_recalcular_faturas",
            width='stretch',
            icon=":material/refresh:"
        ):
            with st.spinner("Limpando resíduos e sincronizando faturas/caixa..."):
                AdminManager.limpar_residuos_e_sincronizar()
            st.success("Recalculo e sincronização concluídos!")
        # Seções do admin
        tab1, tab2, tab3, tab4 = st.tabs(["Estatísticas", "Resetar Dados", "Usuários", "Log de Ações"])

        with tab1:
            AdminManager._tab_estatisticas()

        with tab2:
            AdminManager._tab_resetar()

        with tab3:
            AdminManager._tab_usuarios()

        with tab4:
            AdminManager._tab_log_acoes()
    
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
        col1.metric(" Usuários", usuarios['total'].values[0] if 'total' in usuarios.columns and not usuarios.empty else 0)
        col2.metric(" Contas", contas['total'].values[0] if 'total' in contas.columns and not contas.empty else 0)
        col3.metric(" Categorias", categorias['total'].values[0] if 'total' in categorias.columns and not categorias.empty else 0)
        col4.metric(" Transações", transacoes['total'].values[0] if 'total' in transacoes.columns and not transacoes.empty else 0)
        
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
        """Deleta todos os DADOS FINANCEIROS do usuário logado, mantendo a
        estrutura das tabelas E a própria conta/login intactos.

        Sempre filtra por user_id: a tabela `usuarios` não tem Row Level
        Security (diferente de transacoes/contas/categorias/etc.), então um
        DELETE sem filtro apagaria a conta de TODOS os usuários do sistema,
        não só a de quem clicou no botão. A ordem respeita as chaves
        estrangeiras (tabelas filhas antes das tabelas-pai que elas referenciam).

        Não apaga `usuarios` nem `log_acoes`: a conta/login do usuário é
        preservada (senão ele perderia o acesso e precisaria recriar a conta
        para "recomeçar"), e o log de ações é auditoria histórica — além
        disso, log_acoes.user_id referencia usuarios sem CASCADE, então
        apagar o usuário sempre falharia enquanto houver log dele.
        """
        try:
            user_id = db.get_user_id()
            # transacoes referencia faturas (fatura_id) — precisa ser apagada
            # ANTES de faturas, não depois.
            tabelas_em_ordem = [
                "itens_fatura", "transacoes", "faturas",
                "subcategorias", "limites_financeiros", "contas", "categorias",
            ]
            falhas = [t for t in tabelas_em_ordem if not db.executar(f"DELETE FROM {t} WHERE user_id=?", (user_id,))]

            if falhas:
                st.error(f"⚠️ Falha ao limpar: {', '.join(falhas)}. Veja as mensagens de erro acima.")
            else:
                st.success(" Todos os seus dados foram deletados!")
                st.info(" As tabelas foram mantidas. Você pode começar a adicionar novos dados.")

        except Exception as e:
            st.error(f" Erro ao deletar: {e}")
    
    @staticmethod
    def _tab_log_acoes():
        """Exibe o log de ações (INSERT/UPDATE/DELETE) do usuário logado."""
        st.subheader("Log de Ações")
        st.caption(
            "Todo lançamento, edição ou exclusão feito no sistema fica registrado aqui, "
            "mais recente primeiro. O volume pode ficar grande — use os filtros abaixo."
        )

        user_id = db.get_user_id()
        limite = st.number_input(
            "Quantidade de registros", min_value=50, max_value=5000, value=500, step=50
        )
        df_log = db.buscar_logs(user_id, limite=int(limite))

        if df_log.empty:
            st.info("Nenhuma ação registrada ainda.")
            return

        acoes_disp = sorted(df_log["acao"].unique().tolist())
        tabelas_disp = sorted(df_log["tabela"].unique().tolist())

        col1, col2 = st.columns(2)
        acao_sel = col1.multiselect("Filtrar por ação", acoes_disp, default=acoes_disp)
        tabela_sel = col2.multiselect("Filtrar por tabela", tabelas_disp, default=tabelas_disp)

        df_filtrado = df_log[
            df_log["acao"].isin(acao_sel) & df_log["tabela"].isin(tabela_sel)
        ]

        st.caption(f"{len(df_filtrado)} de {len(df_log)} registro(s) carregado(s).")
        st.dataframe(
            df_filtrado.rename(columns={
                "criado_em": "Data/Hora",
                "acao": "Ação",
                "tabela": "Tabela",
                "query": "Query",
                "parametros": "Parâmetros",
            }),
            width="stretch",
            hide_index=True,
        )

    @staticmethod
    def _recriar_banco():
        """Recria o banco do zero (afeta TODOS os usuários — reset nuclear)."""
        try:
            from database import DatabaseManager

            # CASCADE evita ter que respeitar manualmente a ordem das chaves
            # estrangeiras — é um reset nuclear mesmo, então arrasta tudo.
            for tabela in [
                "log_acoes", "itens_fatura", "faturas", "transacoes",
                "subcategorias", "limites_financeiros", "contas", "categorias", "usuarios",
            ]:
                db.executar(f"DROP TABLE IF EXISTS {tabela} CASCADE")

            # inicializar_banco() só roda de verdade uma vez por processo
            # (trava _banco_inicializado, já ativada no start do app) — sem
            # resetar a flag aqui, as tabelas ficariam derrubadas para sempre
            # nesta sessão.
            DatabaseManager._banco_inicializado = False
            db.inicializar_banco()

            st.success(" Banco de dados foi completamente recriado!")
            st.info(
                " Lembre-se de reaplicar as políticas de RLS "
                "(scripts/passo4_rls_policies.sql) no SQL Editor do Supabase."
            )
            st.balloons()

        except Exception as e:
            st.error(f" Erro ao recriar: {e}")
