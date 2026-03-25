# ==========================================
# CAMADA DE BANCO DE DADOS
# ==========================================

import streamlit as st
import pandas as pd
import psycopg2
from contextlib import contextmanager

class DatabaseManager:
    """Gerenciador centralizado de conexões e operações do banco."""
    
    def __init__(self):
        self.conn = None
    
    @st.cache_resource
    def conectar(_self):
        """Conecta ao banco de dados Supabase."""
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
        """Retorna a conexão atual."""
        if self.conn is None:
            self.conn = self.conectar()
        return self.conn
    
    def executar(self, query, params=()):
        """Executa uma query (INSERT, UPDATE, DELETE)."""
        try:
            conn = self.get_connection()
            q = query.replace('?', '%s')
            with conn.cursor() as cur:
                cur.execute(q, params)
            conn.commit()
            return True
        except Exception as e:
            st.error(f"❌ Erro na execução: {e}")
            if conn:
                conn.rollback()
            return False
    
    def buscar(self, query, params=()):
        """Retorna DataFrame com resultados."""
        try:
            conn = self.get_connection()
            q = query.replace('?', '%s')
            return pd.read_sql(q, conn, params=params)
        except Exception as e:
            st.error(f"❌ Erro na busca: {e}")
            return pd.DataFrame()
    
    def buscar_um(self, query, params=()):
        """Retorna primeira linha do resultado."""
        try:
            conn = self.get_connection()
            q = query.replace('?', '%s')
            with conn.cursor() as cur:
                cur.execute(q, params)
                return cur.fetchone()
        except Exception as e:
            st.error(f"❌ Erro na busca: {e}")
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
