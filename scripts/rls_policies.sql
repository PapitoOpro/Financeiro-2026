-- ==========================================
-- ROW LEVEL SECURITY (RLS) - SUPABASE
-- ==========================================
-- Execute este script no SQL Editor do Supabase
-- para ativar isolamento de dados por usuário.
--
-- IMPORTANTE: Execute APÓS a migração multi-tenant
-- (após o app rodar pelo menos uma vez com o novo código).
-- ==========================================

-- 1. Ativar RLS nas tabelas de dados
ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE contas ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE limites_financeiros ENABLE ROW LEVEL SECURITY;

-- 2. Políticas para TRANSACOES
CREATE POLICY "Usuário só vê suas transações"
ON transacoes FOR SELECT
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só insere suas transações"
ON transacoes FOR INSERT
WITH CHECK (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só atualiza suas transações"
ON transacoes FOR UPDATE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só deleta suas transações"
ON transacoes FOR DELETE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

-- 3. Políticas para CONTAS
CREATE POLICY "Usuário só vê suas contas"
ON contas FOR SELECT
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só insere suas contas"
ON contas FOR INSERT
WITH CHECK (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só atualiza suas contas"
ON contas FOR UPDATE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só deleta suas contas"
ON contas FOR DELETE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

-- 4. Políticas para CATEGORIAS
CREATE POLICY "Usuário só vê suas categorias"
ON categorias FOR SELECT
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só insere suas categorias"
ON categorias FOR INSERT
WITH CHECK (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só atualiza suas categorias"
ON categorias FOR UPDATE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só deleta suas categorias"
ON categorias FOR DELETE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

-- 5. Políticas para LIMITES_FINANCEIROS
CREATE POLICY "Usuário só vê seus limites"
ON limites_financeiros FOR SELECT
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só insere seus limites"
ON limites_financeiros FOR INSERT
WITH CHECK (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só atualiza seus limites"
ON limites_financeiros FOR UPDATE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

CREATE POLICY "Usuário só deleta seus limites"
ON limites_financeiros FOR DELETE
USING (user_id = (SELECT id FROM usuarios WHERE id = user_id));

-- ==========================================
-- NOTA: A tabela 'usuarios' NÃO tem RLS
-- porque o login/registro precisa acessar
-- todos os registros para autenticação.
-- ==========================================
