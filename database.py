# ==========================================
# CAMADA DE BANCO DE DADOS
# ==========================================

import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.pool
import atexit
from contextlib import contextmanager
from supabase import create_client

# Optional SQLAlchemy import for pandas.read_sql engine-backed execution
try:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    from sqlalchemy.engine import URL
    SQLALCHEMY_AVAILABLE = True
except Exception:
    create_engine = None
    NullPool = None
    URL = None
    SQLALCHEMY_AVAILABLE = False

class DatabaseManager:
    """Gerenciador centralizado de conexões e operações do banco."""
    _banco_inicializado = False

    def __init__(self):
        self.conn = None
        self.engine = None
        self._supabase = None
        self._skip_rls = False
    
    def get_supabase(self):
        """Retorna o cliente Supabase (lazy init)."""
        if self._supabase is None:
            try:
                url = st.secrets["SUPABASE_URL"]
                key = st.secrets["SUPABASE_KEY"]
                self._supabase = create_client(url, key)
            except Exception as e:
                st.error(f" Erro ao criar cliente Supabase: {e}")
                return None
        return self._supabase
    
    @staticmethod
    def get_user_id():
        """Retorna o ID do usuário logado."""
        try:
            return st.session_state.get('usuario_id')
        except Exception:
            return None
    
    def conectar(self):
        """Cria uma conexão com o banco de dados.

        Usa keepalives TCP para detectar conexões mortas rapidamente
        e evitar que fiquem presas no pool do Supabase.
        """
        try:
            conn = psycopg2.connect(
                host=st.secrets["db_host"],
                database=st.secrets["db_name"],
                user=st.secrets["db_user"],
                password=st.secrets["db_password"],
                port=st.secrets["db_port"],
                connect_timeout=10,
                # TCP keepalives: detecta conexão morta em ~30s
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=3,
                # Fecha conexões ociosas no servidor após 5 min
                options="-c idle_in_transaction_session_timeout=300000"
            )
            return conn
        except Exception as e:
            st.error(f" Erro de conexão com BD: {e}")
            return None

    def get_connection(self):
        """Retorna a conexão atual, reconectando se necessário."""
        try:
            if self.conn is not None and getattr(self.conn, "closed", 1) == 0:
                # Testa se a conexão ainda está viva com query leve
                try:
                    with self.conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    self.conn.commit()
                except Exception:
                    # Conexão morta — fecha e reconecta
                    try:
                        self.conn.close()
                    except Exception:
                        pass
                    self.conn = None

                if self.conn is not None:
                    if not self._skip_rls:
                        self._set_rls_user(self.conn)
                    return self.conn
        except Exception:
            # Qualquer problema ao checar a conexão força reconexão
            pass

        # Tenta (re)criar a conexão
        self.conn = self.conectar()
        if self.conn is not None and not self._skip_rls:
            self._set_rls_user(self.conn)
        return self.conn

    def fechar(self):
        """Fecha a conexão e o engine, liberando recursos no pool do Supabase."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        if self.engine is not None:
            try:
                self.engine.dispose()
            except Exception:
                pass
            self.engine = None

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

        Usa NullPool para não manter conexões extras abertas — cada
        operação abre e fecha sua própria conexão, evitando esgotamento
        do pool do Supabase.
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
            self.engine = create_engine(url, poolclass=NullPool)
            return self.engine
            return self.engine
        except Exception as e:
            # Não é erro fatal — apenas retornamos None e deixamos o caller
            # tentar usar a conexão DB-API tradicional.
            try:
                st.warning(f" Falha ao criar SQLAlchemy engine: {e}")
            except Exception:
                pass
            return None
    
    def executar(self, query, params=()):
        """Executa uma query (INSERT, UPDATE, DELETE)."""
        conn = self.get_connection()
        if conn is None:
            st.error(" Sem conexão com o banco de dados.")
            return False

        q = query.replace('?', '%s')
        try:
            with conn.cursor() as cur:
                cur.execute(q, params)
            conn.commit()
            return True
        except Exception as e:
            st.error(f" Erro na execução: {e}")
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
            st.error(" Sem conexão com o banco de dados.")
            return pd.DataFrame()

        q = query.replace('?', '%s')
        try:
            # Tenta usar SQLAlchemy engine quando disponível (recomendado
            # pelo pandas). Se não houver engine, cai para a conexão DB-API.
            engine = self.get_engine()
            if engine is not None:
                return pd.read_sql(q, engine, params=params)
            df = pd.read_sql(q, conn, params=params)
            conn.commit()
            return df
        except Exception as e:
            st.error(f" Erro na busca: {e}")
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
            st.error(" Sem conexão com o banco de dados.")
            return None

        q = query.replace('?', '%s')
        try:
            with conn.cursor() as cur:
                cur.execute(q, params)
                result = cur.fetchone()
            conn.commit()
            return result
        except Exception as e:
            st.error(f" Erro na busca: {e}")
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None
            return None
    
    def inicializar_banco(self):
        """Cria as tabelas se não existirem e aplica migrações."""
        if DatabaseManager._banco_inicializado:
            return

        self._skip_rls = True

        # Timeout para DDL: não esperar mais de 5s por locks
        try:
            self.executar("SET lock_timeout = '5s'")
        except Exception:
            pass

        # Usuarios primeiro (referenciado por outras tabelas)
        self.executar('''CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            email TEXT,
            auth_id UUID UNIQUE)''')

        self.executar('CREATE TABLE IF NOT EXISTS contas (id SERIAL PRIMARY KEY, nome TEXT, user_id INTEGER REFERENCES usuarios(id))')
        self.executar('''CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            percentual_meta NUMERIC DEFAULT 0,
            icone TEXT DEFAULT '',
            ativa BOOLEAN DEFAULT TRUE,
            user_id INTEGER REFERENCES usuarios(id))''')
        self.executar('''CREATE TABLE IF NOT EXISTS subcategorias (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            categoria_id INTEGER REFERENCES categorias(id),
            ativa BOOLEAN DEFAULT TRUE,
            user_id INTEGER REFERENCES usuarios(id))''')
        self.executar('''CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY, 
            descricao TEXT, 
            valor NUMERIC, 
            data_vencimento DATE, 
            conta_id INTEGER REFERENCES contas(id),
            categoria_id INTEGER REFERENCES categorias(id),
            subcategoria_id INTEGER REFERENCES subcategorias(id),
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
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email TEXT"
            )
        except Exception:
            pass

        # Migração Supabase Auth: coluna auth_id para vincular ao Supabase Auth
        try:
            self.executar(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS auth_id UUID UNIQUE"
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
        for tabela in ['contas', 'categorias', 'transacoes', 'limites_financeiros', 'subcategorias']:
            try:
                self.executar(
                    f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id)"
                )
            except Exception:
                pass

        # ── MIGRAÇÃO: subcategorias + campos novos em categorias ──
        try:
            self.executar("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS percentual_meta NUMERIC DEFAULT 0")
        except Exception:
            pass
        try:
            self.executar("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS icone TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            self.executar("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS ativa BOOLEAN DEFAULT TRUE")
        except Exception:
            pass
        try:
            self.executar("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'saida'")
        except Exception:
            pass
        try:
            self.executar('''CREATE TABLE IF NOT EXISTS subcategorias (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                categoria_id INTEGER REFERENCES categorias(id),
                ativa BOOLEAN DEFAULT TRUE,
                user_id INTEGER REFERENCES usuarios(id))''')
        except Exception:
            pass
        try:
            self.executar("ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS subcategoria_id INTEGER REFERENCES subcategorias(id)")
        except Exception:
            pass
        try:
            self.executar("CREATE UNIQUE INDEX IF NOT EXISTS ux_subcategorias_nome_cat_user ON subcategorias(nome, categoria_id, user_id)")
        except Exception:
            pass
        # Flag de onboarding concluído
        try:
            self.executar("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS onboarding_completo BOOLEAN DEFAULT FALSE")
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
            self.executar("SET lock_timeout = '0'")
        except Exception:
            pass

        # ── MIGRAÇÃO: Tabelas de Faturas (container de fatura) ──
        try:
            self.executar('''CREATE TABLE IF NOT EXISTS faturas (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES usuarios(id),
                conta_id INTEGER REFERENCES contas(id),
                competencia TEXT NOT NULL,
                valor_total NUMERIC DEFAULT 0,
                data_vencimento DATE,
                status TEXT DEFAULT 'aberta',
                data_pagamento DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        except Exception:
            pass

        try:
            self.executar('''CREATE TABLE IF NOT EXISTS itens_fatura (
                id SERIAL PRIMARY KEY,
                fatura_id INTEGER REFERENCES faturas(id) ON DELETE CASCADE,
                descricao TEXT NOT NULL,
                valor NUMERIC NOT NULL,
                data_compra DATE,
                parcela_atual INTEGER DEFAULT 1,
                parcela_total INTEGER DEFAULT 1,
                categoria_id INTEGER REFERENCES categorias(id),
                subcategoria_id INTEGER REFERENCES subcategorias(id),
                user_id INTEGER REFERENCES usuarios(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        except Exception:
            pass

        # FK opcional de transacoes → faturas (pagamento da fatura)
        try:
            self.executar(
                "ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS fatura_id INTEGER REFERENCES faturas(id)"
            )
        except Exception:
            pass

        # Índices para faturas
        try:
            self.executar(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_faturas_conta_comp_user "
                "ON faturas(conta_id, competencia, user_id)"
            )
        except Exception:
            pass

        try:
            self.executar(
                "CREATE INDEX IF NOT EXISTS ix_itens_fatura_fatura ON itens_fatura(fatura_id)"
            )
        except Exception:
            pass

        # ── MIGRAÇÃO: Converter transacoes CARTAO existentes em faturas ──
        try:
            tem_cartao = self.buscar_um(
                "SELECT 1 FROM transacoes WHERE tipo_fluxo = 'CARTAO' "
                "AND NOT EXISTS (SELECT 1 FROM itens_fatura LIMIT 1) LIMIT 1"
            )
            if tem_cartao:
                self._migrar_cartao_para_faturas()
        except Exception:
            pass

        # ── Garante que toda fatura tem transação no caixa ──
        try:
            faturas_sem_transacao = self.buscar(
                "SELECT f.id, f.user_id FROM faturas f "
                "WHERE NOT EXISTS ("
                " SELECT 1 FROM transacoes t WHERE t.fatura_id = f.id"
                ")"
            )
            if not faturas_sem_transacao.empty:
                for _, f in faturas_sem_transacao.iterrows():
                    try:
                        self.sincronizar_transacao_fatura(f['id'], f['user_id'])
                    except Exception:
                        pass
        except Exception:
            pass

        self._skip_rls = False
        DatabaseManager._banco_inicializado = True

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
            ('pct_sugestao_guardar', 30, 'Sugestão de % a guardar de dinheiro extra'),
        ]
        for chave, valor, desc in defaults:
            self.executar(
                "INSERT INTO limites_financeiros (chave, valor, descricao, user_id) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (chave, user_id) DO NOTHING",
                (chave, valor, desc, user_id)
            )

    def usuario_completou_onboarding(self, user_id):
        """Verifica se o usuário já completou o onboarding."""
        if not user_id:
            return False
        row = self.buscar_um(
            "SELECT onboarding_completo FROM usuarios WHERE id = %s", (user_id,)
        )
        return bool(row and row[0])

    def marcar_onboarding_completo(self, user_id):
        """Marca o onboarding como concluído."""
        self.executar(
            "UPDATE usuarios SET onboarding_completo = TRUE WHERE id = %s", (user_id,)
        )

    def buscar_subcategorias_por_categoria(self, categoria_id, user_id):
        """Retorna subcategorias ativas de uma categoria."""
        return self.buscar(
            "SELECT * FROM subcategorias WHERE categoria_id = %s AND user_id = %s AND ativa = TRUE ORDER BY nome",
            (categoria_id, user_id)
        )

    def buscar_categoria_por_subcategoria(self, subcategoria_id):
        """Retorna a categoria macro dada uma subcategoria."""
        return self.buscar_um(
            "SELECT c.* FROM categorias c JOIN subcategorias s ON s.categoria_id = c.id WHERE s.id = %s",
            (subcategoria_id,)
        )

    # ══════════════════════════════════════════
    # FATURAS — CRUD
    # ══════════════════════════════════════════

    def criar_fatura(self, user_id, conta_id, competencia, data_vencimento, valor_total=0):
        """Cria uma fatura ou retorna a existente para o mesmo cartão/competência."""
        existente = self.buscar_um(
            "SELECT id FROM faturas WHERE conta_id = %s AND competencia = %s AND user_id = %s",
            (conta_id, competencia, user_id)
        )
        if existente:
            print(f"[DEBUG] criar_fatura: fatura já existe! id={existente[0]} user_id={user_id} conta_id={conta_id} competencia={competencia}")
            return existente[0]

        self.executar(
            "INSERT INTO faturas (user_id, conta_id, competencia, data_vencimento, valor_total) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user_id, conta_id, competencia, data_vencimento, valor_total)
        )
        row = self.buscar_um(
            "SELECT id FROM faturas WHERE conta_id = %s AND competencia = %s AND user_id = %s",
            (conta_id, competencia, user_id)
        )
        print(f"[DEBUG] criar_fatura: fatura criada id={row[0] if row else None} user_id={user_id} conta_id={conta_id} competencia={competencia}")
        return row[0] if row else None

    def adicionar_item_fatura(self, fatura_id, descricao, valor, data_compra,
                               parcela_atual, parcela_total, categoria_id, user_id,
                               subcategoria_id=None):
        """Adiciona um item a uma fatura."""
        return self.executar(
            "INSERT INTO itens_fatura "
            "(fatura_id, descricao, valor, data_compra, parcela_atual, parcela_total, "
            " categoria_id, subcategoria_id, user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (fatura_id, descricao, valor, data_compra, parcela_atual,
             parcela_total, categoria_id, subcategoria_id, user_id)
        )

    def atualizar_total_fatura(self, fatura_id):
        """Recalcula valor_total da fatura a partir dos itens."""
        self.executar(
            "UPDATE faturas SET valor_total = "
            "(SELECT COALESCE(SUM(valor), 0) FROM itens_fatura WHERE fatura_id = %s) "
            "WHERE id = %s",
            (fatura_id, fatura_id)
        )

    def buscar_faturas(self, user_id, competencia=None, conta_id=None):
        """Retorna faturas do usuário com filtros opcionais."""
        query = """
            SELECT f.id, f.competencia, f.valor_total, f.data_vencimento,
                   f.status, f.data_pagamento, c.nome as cartao,
                   f.conta_id, f.created_at
            FROM faturas f
            LEFT JOIN contas c ON f.conta_id = c.id
            WHERE f.user_id = %s
        """
        params = [user_id]
        if competencia:
            query += " AND f.competencia = %s"
            params.append(competencia)
        if conta_id:
            query += " AND f.conta_id = %s"
            params.append(conta_id)
        query += " ORDER BY f.data_vencimento DESC"
        return self.buscar(query, tuple(params))

    def buscar_itens_fatura(self, fatura_id):
        """Retorna itens de uma fatura específica."""
        return self.buscar(
            "SELECT i.id, i.descricao, i.valor, i.data_compra, "
            " i.parcela_atual, i.parcela_total, "
            " cat.nome as categoria, i.categoria_id, i.subcategoria_id, "
            " COALESCE(sub.nome, '') as subcategoria "
            "FROM itens_fatura i "
            "LEFT JOIN categorias cat ON i.categoria_id = cat.id "
            "LEFT JOIN subcategorias sub ON i.subcategoria_id = sub.id "
            "WHERE i.fatura_id = %s "
            "ORDER BY i.descricao",
            (fatura_id,)
        )

    def pagar_fatura(self, fatura_id, user_id, data_pagamento=None):
        """Marca fatura como paga (compensa a transação no caixa)."""
        from datetime import date
        data_pgto = data_pagamento or date.today()

        # Marca fatura como paga
        self.executar(
            "UPDATE faturas SET status = 'paga', data_pagamento = %s WHERE id = %s",
            (data_pgto, fatura_id)
        )

        # Compensa a transação correspondente no caixa
        self.executar(
            "UPDATE transacoes SET compensado = TRUE, data_compensacao = %s "
            "WHERE fatura_id = %s AND user_id = %s",
            (data_pgto, fatura_id, user_id)
        )
        return True

    def reabrir_fatura(self, fatura_id, user_id):
        """Reabre uma fatura paga (descompensa a transação no caixa)."""
        self.executar(
            "UPDATE faturas SET status = 'aberta', data_pagamento = NULL WHERE id = %s",
            (fatura_id,)
        )
        self.executar(
            "UPDATE transacoes SET compensado = FALSE, data_compensacao = NULL "
            "WHERE fatura_id = %s AND user_id = %s",
            (fatura_id, user_id)
        )

    def sincronizar_transacao_fatura(self, fatura_id, user_id):
        """Cria ou atualiza a transação única no caixa que representa a fatura.
        
        - Fatura aparece como 1 linha no extrato (pendente)
        - Ao compensar no caixa = fatura paga
        """
        print(f"[DEBUG] sincronizar_transacao_fatura: fatura_id={fatura_id}, user_id={user_id}")
        fatura = self.buscar_um(
            "SELECT f.valor_total, c.nome, f.competencia, f.data_vencimento, f.conta_id, f.status "
            "FROM faturas f JOIN contas c ON f.conta_id = c.id "
            "WHERE f.id = %s AND f.user_id = %s",
            (fatura_id, user_id)
        )
        print(f"[DEBUG] fatura encontrada: {fatura}")
        if not fatura:
            print("[DEBUG] fatura não encontrada, abortando.")
            return

        valor_total, cartao_nome, competencia, data_venc, conta_id, status = fatura
        descricao = f"Fatura {cartao_nome} - Ref {competencia}"
        is_paga = status == 'paga'

        # Se o valor_total for menor ou igual a zero, não cria/atualiza transação no caixa (ignora estornos ou faturas zeradas)
        if valor_total is None or valor_total <= 0:
            print(f"[DEBUG] valor_total inválido (None ou <= 0): {valor_total}. Removendo transação se existir.")
            self.executar(
                "DELETE FROM transacoes WHERE fatura_id = %s AND user_id = %s",
                (fatura_id, user_id)
            )
            return

        # Verifica se já existe transação para essa fatura
        existente = self.buscar_um(
            "SELECT id FROM transacoes WHERE fatura_id = %s AND user_id = %s",
            (fatura_id, user_id)
        )
        print(f"[DEBUG] transação existente: {existente}")

        # O valor da fatura deve ser sempre negativo (saída), exceto se for crédito puro
        valor_caixa = valor_total if valor_total > 0 else -abs(valor_total)
        print(f"[DEBUG] valor_caixa a lançar: {valor_caixa}")
        if existente:
            print("[DEBUG] Atualizando transação existente no caixa.")
            self.executar(
                "UPDATE transacoes SET descricao = %s, valor = %s, data_vencimento = %s, conta_id = %s "
                "WHERE fatura_id = %s AND user_id = %s",
                (descricao, valor_caixa, data_venc, conta_id, fatura_id, user_id)
            )
        else:
            print("[DEBUG] Criando nova transação no caixa.")
            self.executar(
                "INSERT INTO transacoes "
                "(descricao, valor, data_vencimento, conta_id, tipo_fluxo, user_id, "
                " compensado, data_compensacao, fatura_id) "
                "VALUES (%s, %s, %s, %s, 'CAIXA', %s, %s, %s, %s)",
                (descricao, valor_caixa, data_venc, conta_id, user_id, 
                 is_paga, data_venc if is_paga else None, fatura_id)
            )
        print("[DEBUG] Fim sincronizar_transacao_fatura.")

    def excluir_fatura(self, fatura_id, user_id):
        """Exclui fatura e todos os seus itens (CASCADE)."""
        self.executar(
            "DELETE FROM transacoes WHERE fatura_id = %s AND user_id = %s",
            (fatura_id, user_id)
        )
        self.executar(
            "DELETE FROM faturas WHERE id = %s AND user_id = %s",
            (fatura_id, user_id)
        )

    def buscar_itens_parcelas_futuras(self, user_id, a_partir_de=None):
        """Retorna todos os itens que ainda têm parcelas futuras (para previsão)."""
        from datetime import date
        data_ref = a_partir_de or date.today()
        return self.buscar(
            "SELECT i.id, i.descricao, i.valor, i.data_compra, "
            " i.parcela_atual, i.parcela_total, "
            " cat.nome as categoria, c.nome as cartao, "
            " f.competencia, f.data_vencimento as venc_fatura, "
            " i.fatura_id, i.categoria_id "
            "FROM itens_fatura i "
            "JOIN faturas f ON i.fatura_id = f.id "
            "LEFT JOIN categorias cat ON i.categoria_id = cat.id "
            "LEFT JOIN contas c ON f.conta_id = c.id "
            "WHERE i.user_id = %s AND i.parcela_atual < i.parcela_total "
            "ORDER BY f.data_vencimento, i.descricao",
            (user_id,)
        )

    def buscar_gastos_cartao_por_categoria(self, user_id, data_inicio, data_fim):
        """Retorna gastos de cartão agrupados por categoria (para acompanhamento/consultor)."""
        return self.buscar(
            "SELECT i.categoria_id, cat.nome as categoria, cat.icone, "
            " cat.percentual_meta, ABS(SUM(i.valor)) as gasto_real "
            "FROM itens_fatura i "
            "JOIN faturas f ON i.fatura_id = f.id "
            "JOIN categorias cat ON i.categoria_id = cat.id "
            "WHERE i.user_id = %s "
            " AND f.data_vencimento BETWEEN %s AND %s "
            "GROUP BY i.categoria_id, cat.nome, cat.icone, cat.percentual_meta "
            "ORDER BY cat.nome",
            (user_id, data_inicio, data_fim)
        )

    def _migrar_cartao_para_faturas(self):
        """Migra transacoes CARTAO existentes para o modelo faturas + itens."""
        import re
        from datetime import date

        rows = self.buscar(
            "SELECT t.id, t.descricao, t.valor, t.data_vencimento, "
            " t.conta_id, t.categoria_id, t.user_id "
            "FROM transacoes t "
            "WHERE t.tipo_fluxo = 'CARTAO'"
        )
        if rows.empty:
            return

        for _, r in rows.iterrows():
            try:
                user_id = r['user_id']
                conta_id = r['conta_id']
                data_venc = r['data_vencimento']
                if pd.isna(data_venc):
                    continue

                dt = pd.to_datetime(data_venc)
                competencia = dt.strftime('%m/%Y')

                # Cria ou reutiliza fatura
                fatura_id = self.criar_fatura(
                    user_id, conta_id, competencia,
                    dt.date() if hasattr(dt, 'date') else dt
                )
                if not fatura_id:
                    continue

                # Extrai parcela da descrição: [Cartao] Desc (02/10)
                desc_limpa = re.sub(r'^\[.*?\]\s*', '', str(r['descricao']))
                parc_match = re.search(r'\((\d+)/(\d+)\)$', desc_limpa)
                parcela_atual = int(parc_match.group(1)) if parc_match else 1
                parcela_total = int(parc_match.group(2)) if parc_match else 1
                if parc_match:
                    desc_limpa = desc_limpa[:parc_match.start()].strip()

                self.adicionar_item_fatura(
                    fatura_id, desc_limpa, abs(r['valor']),
                    dt.date() if hasattr(dt, 'date') else dt,
                    parcela_atual, parcela_total,
                    r['categoria_id'], user_id
                )
            except Exception:
                continue

        # Recalcula totais e sincroniza transações no caixa
        faturas_criadas = self.buscar("SELECT DISTINCT id, user_id FROM faturas")
        if not faturas_criadas.empty:
            for _, f in faturas_criadas.iterrows():
                self.atualizar_total_fatura(f['id'])
                self.sincronizar_transacao_fatura(f['id'], f['user_id'])

# Instância global
db = DatabaseManager()
# Garante que conexões sejam liberadas quando o processo encerrar
atexit.register(db.fechar)
