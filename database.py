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
                return self.conn
        except Exception:
            # Qualquer problema ao checar a conexão força reconexão
            pass

        # Tenta (re)criar a conexão
        self.conn = self.conectar()
        return self.conn

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
        self.executar('CREATE TABLE IF NOT EXISTS contas (id SERIAL PRIMARY KEY, nome TEXT UNIQUE)')
        self.executar('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT UNIQUE)')
        self.executar('''CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY, 
            descricao TEXT, 
            valor NUMERIC, 
            data_vencimento DATE, 
            conta_id INTEGER REFERENCES contas(id),
            categoria_id INTEGER REFERENCES categorias(id),
            tipo_fluxo TEXT)''')
        self.executar('''CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            username TEXT UNIQUE, 
            senha TEXT)''')
        
        # MIGRAÇÕES - Adiciona colunas se não existirem
        try:
            # Adiciona coluna 'aprovado' se não existir
            self.executar(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS aprovado BOOLEAN DEFAULT FALSE"
            )
        except:
            pass
        
        try:
            # Adiciona coluna 'data_criacao' se não existir
            self.executar(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
        except:
            pass

# Instância global
db = DatabaseManager()
