-- PASSO 7: RLS completo (cobre tabelas que ficaram de fora dos scripts anteriores)
-- Execute no SQL Editor do Supabase.
--
-- rls_policies.sql / passo4 só cobriam transacoes, contas, categorias e
-- limites_financeiros. subcategorias, faturas e itens_fatura nunca tiveram
-- RLS aplicado, apesar de guardarem dados por usuário como as demais.
-- Este script cobre todas elas de uma vez (idempotente — pode rodar de novo
-- a qualquer momento, inclusive depois de um "Recriar Tudo" no Painel Admin).

DO $$
DECLARE
    tabela TEXT;
BEGIN
    FOREACH tabela IN ARRAY ARRAY[
        'transacoes', 'contas', 'categorias', 'limites_financeiros',
        'subcategorias', 'faturas', 'itens_fatura'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tabela);

        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', tabela || '_select', tabela);
        EXECUTE format(
            'CREATE POLICY %I ON %I FOR SELECT USING (user_id = current_setting(''app.current_user_id'', true)::integer)',
            tabela || '_select', tabela
        );

        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', tabela || '_insert', tabela);
        EXECUTE format(
            'CREATE POLICY %I ON %I FOR INSERT WITH CHECK (user_id = current_setting(''app.current_user_id'', true)::integer)',
            tabela || '_insert', tabela
        );

        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', tabela || '_update', tabela);
        EXECUTE format(
            'CREATE POLICY %I ON %I FOR UPDATE USING (user_id = current_setting(''app.current_user_id'', true)::integer)',
            tabela || '_update', tabela
        );

        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', tabela || '_delete', tabela);
        EXECUTE format(
            'CREATE POLICY %I ON %I FOR DELETE USING (user_id = current_setting(''app.current_user_id'', true)::integer)',
            tabela || '_delete', tabela
        );
    END LOOP;
END $$;

-- log_acoes: somente-leitura pela UI (sem policy de UPDATE/DELETE de propósito)
ALTER TABLE log_acoes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "log_acoes_select" ON log_acoes;
CREATE POLICY "log_acoes_select" ON log_acoes FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
DROP POLICY IF EXISTS "log_acoes_insert" ON log_acoes;
CREATE POLICY "log_acoes_insert" ON log_acoes FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);

-- NOTA: 'usuarios' continua sem RLS de propósito — login/registro precisa
-- consultar todos os registros para autenticação.
