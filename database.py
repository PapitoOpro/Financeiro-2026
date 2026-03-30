# ==========================================
# CAMADA DE BANCO DE DADOS
# ==========================================

import streamlit as st
import pandas as pd
import psycopg2
from contextlib import contextmanager

# Optional SQLAlchemy import for pandas.read_sql engine-backed execution
try:
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
    SQLALCHEMY_AVAILABLE = True
except Exception:
    create_engine = None
    URL = None
    SQLALCHEMY_AVAILABLE = False

class DatabaseManager:
    """Gerenciador centralizado de conexões e operações do banco."""
    
    def __init__(self):
        self.conn = None
        self.engine = None
    
    @staticmethod
    def get_user_id():
        """Retorna o ID do usuário logado."""
        return st.session_state.get('usuario_id')
    
    def conectar(self):
        """Cria uma conexão com o banco de dados (não cacheada).

        Observação: não cacheamos o objeto de conexão para permitir que
        reconexões sejam feitas quando o servidor encerrar a sessão.
        """
        try:
            conn = psycopg2.connect(
                host=st.secrets["db_host"],
                database=st.secrets["db_name"],
                user=st.secrets["db_user"],
                password=st.secrets["db_password"],
                port=st.secrets["db_port"]
            )
            return conn
        except Exception as e:
            st.error(f"❌ Erro de conexão com BD: {e}")
            return None

    def get_connection(self):
        """Retorna a conexão atual, reconectando se necessário."""
        try:
            if self.conn is not None and getattr(self.conn, "closed", 1) == 0:
                # Atualiza variável de sessão RLS com usuário atual
                self._set_rls_user(self.conn)
                return self.conn
        except Exception:
            # Qualquer problema ao checar a conexão força reconexão
            pass

        # Tenta (re)criar a conexão
        self.conn = self.conectar()
        if self.conn is not None:
            self._set_rls_user(self.conn)
        return self.conn

    def _set_rls_user(self, conn):
        """Define app.current_user_id na sessão do PostgreSQL para RLS."""
        uid = self.get_user_id()
        if uid is not None:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT set_config('app.current_user_id', %s, false)", (str(uid),))
                conn.commit()
            except Exception:
                pass

    def get_engine(self):
        """Retorna um SQLAlchemy Engine criado a partir de `st.secrets`.

        Retorna `None` se o SQLAlchemy não estiver disponível ou ocorrer erro
        na criação do engine. A criação é feita de forma preguiçosa e o
        engine é cacheado em `self.engine`.
        """
        if getattr(self, "engine", None) is not None:
            return self.engine

        if not SQLALCHEMY_AVAILABLE:
            return None

        try:
            url = URL.create(
                "postgresql+psycopg2",
                username=st.secrets["db_user"],
                password=st.secrets["db_password"],
                host=st.secrets["db_host"],
                port=st.secrets["db_port"],
                database=st.secrets["db_name"],
            )
            self.engine = create_engine(url)
            return self.engine
        except Exception as e:
            # Não é erro fatal — apenas retornamos None e deixamos o caller
            # tentar usar a conexão DB-API tradicional.
            try:
                st.warning(f"⚠️ Falha ao criar SQLAlchemy engine: {e}")
            except Exception:
                pass
            return None
    
    def executar(self, query, params=()):
        """Executa uma query (INSERT, UPDATE, DELETE)."""
        conn = self.get_connection()
        if conn is None:
            st.error("❌ Sem conexão com o banco de dados.")
            return False

        q = query.replace('?', '%s')
        try:
            with conn.cursor() as cur:
                cur.execute(q, params)
            conn.commit()
            return True
        except Exception as e:
            st.error(f"❌ Erro na execução: {e}")
            # Tenta rollback somente se a conexão ainda estiver aberta
            try:
                if getattr(conn, 'closed', 1) == 0:
                    conn.rollback()
            except Exception:
                pass
            # Reinicializa conexão para forçar reconexão na próxima chamada
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None
            return False
    
    def buscar(self, query, params=()):
        """Retorna DataFrame com resultados."""
        conn = self.get_connection()
        if conn is None:
            st.error("❌ Sem conexão com o banco de dados.")
            return pd.DataFrame()

        q = query.replace('?', '%s')
        try:
            # Tenta usar SQLAlchemy engine quando disponível (recomendado
            # pelo pandas). Se não houver engine, cai para a conexão DB-API.
            engine = self.get_engine()
            if engine is not None:
                return pd.read_sql(q, engine, params=params)
            return pd.read_sql(q, conn, params=params)
        except Exception as e:
            st.error(f"❌ Erro na busca: {e}")
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None
            return pd.DataFrame()
    
    def buscar_um(self, query, params=()):
        """Retorna primeira linha do resultado."""
        conn = self.get_connection()
        if conn is None:
            st.error("❌ Sem conexão com o banco de dados.")
            return None

        q = query.replace('?', '%s')
        try:
            with conn.cursor() as cur:
                cur.execute(q, params)
                return cur.fetchone()
        except Exception as e:
            st.error(f"❌ Erro na busca: {e}")
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None
            return None
    
    def inicializar_banco(self):
        """Cria as tabelas se não existirem e aplica migrações."""
        # Usuarios primeiro (referenciado por outras tabelas)
        self.executar('''CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            username TEXT UNIQUE, 
            senha TEXT)''')

        self.executar('CREATE TABLE IF NOT EXISTS contas (id SERIAL PRIMARY KEY, nome TEXT, user_id INTEGER REFERENCES usuarios(id))')
        self.executar('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT, user_id INTEGER REFERENCES usuarios(id))')
        self.executar('''CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY, 
            descricao TEXT, 
            valor NUMERIC, 
            data_vencimento DATE, 
            conta_id INTEGER REFERENCES contas(id),
            categoria_id INTEGER REFERENCES categorias(id),
            tipo_fluxo TEXT,
            user_id INTEGER REFERENCES usuarios(id))''')

        # Tabela de configuração de limites do consultor financeiro
        self.executar('''CREATE TABLE IF NOT EXISTS limites_financeiros (
            id SERIAL PRIMARY KEY,
            chave TEXT NOT NULL,
            valor NUMERIC NOT NULL,
            descricao TEXT,
            user_id INTEGER REFERENCES usuarios(id))''')

        # MIGRAÇÕES - Aumenta timeout para operações pesadas
        try:
            self.executar("SET statement_timeout = '600s'")
        except Exception:
            pass

        # MIGRAÇÕES - Adiciona colunas se não existirem
        try:
            self.executar(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS aprovado BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            pass
        
        try:
            self.executar(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
        except Exception:
            pass

        try:
            self.executar(
                "ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS compensado BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            pass

        try:
            self.executar(
                "ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS data_compensacao DATE"
            )
        except Exception:
            pass

        # ── MIGRAÇÃO MULTI-TENANT: Adicionar user_id às tabelas existentes ──
        for tabela in ['contas', 'categorias', 'transacoes', 'limites_financeiros']:
            try:
                self.executar(
                    f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id)"
                )
            except Exception:
                pass

        # Popula user_id para dados existentes (atribui ao primeiro usuário)
        try:
            primeiro_usuario = self.buscar_um("SELECT id FROM usuarios ORDER BY id LIMIT 1")
            if primeiro_usuario:
                uid = primeiro_usuario[0]
                for tabela in ['contas', 'categorias', 'transacoes', 'limites_financeiros']:
                    self.executar(f"UPDATE {tabela} SET user_id = %s WHERE user_id IS NULL", (uid,))
        except Exception:
            pass

        # ── MIGRAÇÃO: Remover duplicatas antes de criar índices únicos ──
        # Primeiro, reatribuir FKs de transacoes para o registro sobrevivente (menor id)
        for fk_col, tabela, coluna in [('conta_id', 'contas', 'nome'), ('categoria_id', 'categorias', 'nome')]:
            try:
                self.executar(f"""
                    UPDATE transacoes t
                    SET {fk_col} = sub.min_id
                    FROM (
                        SELECT id AS dup_id, MIN(id) OVER (PARTITION BY {coluna}, user_id) AS min_id
                        FROM {tabela}
                    ) sub
                    WHERE t.{fk_col} = sub.dup_id AND sub.dup_id != sub.min_id
                """)
            except Exception:
                pass

        for tabela, coluna in [('contas', 'nome'), ('categorias', 'nome'), ('limites_financeiros', 'chave')]:
            try:
                self.executar(f"""
                    DELETE FROM {tabela}
                    WHERE id NOT IN (
                        SELECT MIN(id) FROM {tabela} GROUP BY {coluna}, user_id
                    )
                """)
            except Exception:
                pass

        # ── MIGRAÇÃO: Atualizar constraints únicas para multi-tenant ──
        try:
            self.executar("ALTER TABLE contas DROP CONSTRAINT IF EXISTS contas_nome_key")
            self.executar("CREATE UNIQUE INDEX IF NOT EXISTS ux_contas_nome_user ON contas(nome, user_id)")
        except Exception:
            pass

        try:
            self.executar("ALTER TABLE categorias DROP CONSTRAINT IF EXISTS categorias_nome_key")
            self.executar("CREATE UNIQUE INDEX IF NOT EXISTS ux_categorias_nome_user ON categorias(nome, user_id)")
        except Exception:
            pass

        try:
            self.executar("ALTER TABLE limites_financeiros DROP CONSTRAINT IF EXISTS limites_financeiros_chave_key")
            self.executar("CREATE UNIQUE INDEX IF NOT EXISTS ux_limites_chave_user ON limites_financeiros(chave, user_id)")
        except Exception:
            pass

        # ── MIGRAÇÃO: Índice único anti-duplicidade em transacoes (multi-tenant) ──
        try:
            idx_check = self.buscar_um(
                "SELECT indexdef FROM pg_indexes WHERE indexname = 'ux_transacoes_desc_val_data'"
            )
            needs_rebuild = not idx_check or 'user_id' not in str(idx_check[0])

            if needs_rebuild:
                self.executar("DROP INDEX IF EXISTS ux_transacoes_desc_val_data")
                # Remove duplicatas existentes por usuário
                self.executar('''
                    DELETE FROM transacoes
                    WHERE id IN (
                        SELECT id FROM (
                            SELECT id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY user_id, lower(trim(descricao)), valor, data_vencimento
                                       ORDER BY id
                                   ) AS rn
                            FROM transacoes
                        ) sub
                        WHERE rn > 1
                    )
                ''')
                self.executar('''
                    CREATE UNIQUE INDEX ux_transacoes_desc_val_data
                    ON transacoes (user_id, lower(trim(descricao)), valor, data_vencimento)
                ''')
        except Exception:
            pass

        # Restaura timeout padrão após migrações
        try:
            self.executar("SET statement_timeout = '0'")
        except Exception:
            pass

    def inicializar_dados_usuario(self, user_id):
        """Insere limites padrão para um usuário se ainda não existirem."""
        if not user_id:
            return
        existe = self.buscar_um(
            "SELECT 1 FROM limites_financeiros WHERE user_id = %s LIMIT 1",
            (user_id,)
        )
        if existe:
            return
        defaults = [
            ('pct_gasto_maximo', 80, 'Percentual máximo de gastos sobre a renda (%)'),
            ('pct_alerta_critico', 90, 'Percentual de gasto que dispara alerta crítico (%)'),
            ('pct_alerta_preventivo', 70, 'Percentual de gasto que dispara alerta preventivo (%)'),
            ('saldo_minimo', 500, 'Saldo mínimo recomendado (R$)'),
            ('pct_cat_alimentacao', 30, 'Limite % para categoria Alimentação'),
            ('pct_cat_lazer', 15, 'Limite % para categoria Lazer'),
            ('pct_cat_transporte', 15, 'Limite % para categoria Transporte'),
            ('pct_sugestao_guardar', 30, 'Sugestão de % a guardar de dinheiro extra'),
        ]
        for chave, valor, desc in defaults:
            self.executar(
                "INSERT INTO limites_financeiros (chave, valor, descricao, user_id) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (chave, user_id) DO NOTHING",
                (chave, valor, desc, user_id)
            )

# Instância global
db = DatabaseManager()
