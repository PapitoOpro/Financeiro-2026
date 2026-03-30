-- PASSO 4: Ativar RLS + Criar policies
-- Execute SOZINHO no SQL Editor do Supabase
ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE contas ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE limites_financeiros ENABLE ROW LEVEL SECURITY;

CREATE POLICY "transacoes_select" ON transacoes FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "transacoes_insert" ON transacoes FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "transacoes_update" ON transacoes FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "transacoes_delete" ON transacoes FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

CREATE POLICY "contas_select" ON contas FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "contas_insert" ON contas FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "contas_update" ON contas FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "contas_delete" ON contas FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

CREATE POLICY "categorias_select" ON categorias FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "categorias_insert" ON categorias FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "categorias_update" ON categorias FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "categorias_delete" ON categorias FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);

CREATE POLICY "limites_select" ON limites_financeiros FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "limites_insert" ON limites_financeiros FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "limites_update" ON limites_financeiros FOR UPDATE
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "limites_delete" ON limites_financeiros FOR DELETE
USING (user_id = current_setting('app.current_user_id', true)::integer);
