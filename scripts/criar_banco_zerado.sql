-- ==========================================
-- CRIAR BANCO ZERADO - MULTI-TENANT
-- ==========================================
-- Execute este script no SQL Editor do Supabase
-- para dropar tudo e recriar do zero.
--
-- ⚠️  ATENÇÃO: TODOS OS DADOS SERÃO PERDIDOS!
-- ==========================================

-- 0. Dropar policies RLS existentes (ignora se não existem)
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT policyname, tablename 
        FROM pg_policies 
        WHERE tablename IN ('transacoes','contas','categorias','limites_financeiros')
    ) LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', r.policyname, r.tablename);
    END LOOP;
END $$;

-- 1. Desativar RLS antes de dropar
ALTER TABLE IF EXISTS transacoes DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS contas DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS categorias DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS subcategorias DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS limites_financeiros DISABLE ROW LEVEL SECURITY;

-- 2. Dropar índices
DROP INDEX IF EXISTS ux_contas_nome_user;
DROP INDEX IF EXISTS ux_categorias_nome_user;
DROP INDEX IF EXISTS ux_subcategorias_nome_cat_user;
DROP INDEX IF EXISTS ux_limites_chave_user;
DROP INDEX IF EXISTS ux_transacoes_desc_val_data;

-- 3. Dropar tabelas na ordem correta (respeitar FKs)
DROP TABLE IF EXISTS transacoes CASCADE;
DROP TABLE IF EXISTS limites_financeiros CASCADE;
DROP TABLE IF EXISTS subcategorias CASCADE;
DROP TABLE IF EXISTS contas CASCADE;
DROP TABLE IF EXISTS categorias CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- ==========================================
-- 4. Criar tabelas do zero (schema final)
-- ==========================================

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT,
    email TEXT,
    auth_id UUID UNIQUE,
    aprovado BOOLEAN DEFAULT FALSE,
    onboarding_completo BOOLEAN DEFAULT FALSE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contas (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    user_id INTEGER REFERENCES usuarios(id)
);

CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    percentual_meta NUMERIC DEFAULT 0,
    icone TEXT DEFAULT '📁',
    ativa BOOLEAN DEFAULT TRUE,
    user_id INTEGER REFERENCES usuarios(id)
);

CREATE TABLE subcategorias (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    categoria_id INTEGER REFERENCES categorias(id),
    ativa BOOLEAN DEFAULT TRUE,
    user_id INTEGER REFERENCES usuarios(id)
);

CREATE TABLE transacoes (
    id SERIAL PRIMARY KEY,
    descricao TEXT,
    valor NUMERIC,
    data_vencimento DATE,
    conta_id INTEGER REFERENCES contas(id),
    categoria_id INTEGER REFERENCES categorias(id),
    subcategoria_id INTEGER REFERENCES subcategorias(id),
    tipo_fluxo TEXT,
    compensado BOOLEAN DEFAULT FALSE,
    data_compensacao DATE,
    user_id INTEGER REFERENCES usuarios(id)
);

CREATE TABLE limites_financeiros (
    id SERIAL PRIMARY KEY,
    chave TEXT NOT NULL,
    valor NUMERIC NOT NULL,
    descricao TEXT,
    user_id INTEGER REFERENCES usuarios(id)
);

-- ==========================================
-- 5. Criar índices únicos compostos
-- ==========================================

CREATE UNIQUE INDEX ux_contas_nome_user ON contas(nome, user_id);
CREATE UNIQUE INDEX ux_categorias_nome_user ON categorias(nome, user_id);
CREATE UNIQUE INDEX ux_subcategorias_nome_cat_user ON subcategorias(nome, categoria_id, user_id);
CREATE UNIQUE INDEX ux_limites_chave_user ON limites_financeiros(chave, user_id);
CREATE UNIQUE INDEX ux_transacoes_desc_val_data ON transacoes(user_id, lower(trim(descricao)), valor, data_vencimento);

-- ==========================================
-- 6. Ativar RLS + Criar policies
-- ==========================================

ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE contas ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE subcategorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE limites_financeiros ENABLE ROW LEVEL SECURITY;

-- TRANSACOES
CREATE POLICY "transacoes_select" ON transacoes FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "transacoes_insert" ON transacoes FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "transacoes_update" ON transacoes FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "transacoes_delete" ON transacoes FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

-- CONTAS
CREATE POLICY "contas_select" ON contas FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "contas_insert" ON contas FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "contas_update" ON contas FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "contas_delete" ON contas FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

-- CATEGORIAS
CREATE POLICY "categorias_select" ON categorias FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "categorias_insert" ON categorias FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "categorias_update" ON categorias FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "categorias_delete" ON categorias FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

-- SUBCATEGORIAS
CREATE POLICY "subcategorias_select" ON subcategorias FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "subcategorias_insert" ON subcategorias FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "subcategorias_update" ON subcategorias FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "subcategorias_delete" ON subcategorias FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

-- LIMITES_FINANCEIROS
CREATE POLICY "limites_select" ON limites_financeiros FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "limites_insert" ON limites_financeiros FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "limites_update" ON limites_financeiros FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "limites_delete" ON limites_financeiros FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

-- ==========================================
-- PRONTO! Banco zerado com schema multi-tenant.
-- Agora é só rodar o app e se cadastrar.
-- ==========================================
