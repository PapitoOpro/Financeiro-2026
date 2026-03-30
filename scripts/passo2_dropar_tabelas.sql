-- PASSO 2: Dropar tudo
-- Execute CADA COMANDO SEPARADAMENTE no SQL Editor do Supabase
-- Selecione uma linha de cada vez e clique Run

-- 2a) Rode sozinho:
ALTER TABLE IF EXISTS transacoes DISABLE ROW LEVEL SECURITY;

-- 2b) Rode sozinho:
ALTER TABLE IF EXISTS contas DISABLE ROW LEVEL SECURITY;

-- 2c) Rode sozinho:
ALTER TABLE IF EXISTS categorias DISABLE ROW LEVEL SECURITY;

-- 2d) Rode sozinho:
ALTER TABLE IF EXISTS limites_financeiros DISABLE ROW LEVEL SECURITY;

-- 2e) Rode sozinho:
DROP TABLE IF EXISTS transacoes CASCADE;

-- 2f) Rode sozinho:
DROP TABLE IF EXISTS limites_financeiros CASCADE;

-- 2g) Rode sozinho:
DROP TABLE IF EXISTS contas CASCADE;

-- 2h) Rode sozinho:
DROP TABLE IF EXISTS categorias CASCADE;

-- 2i) Rode sozinho:
DROP TABLE IF EXISTS usuarios CASCADE;
