-- PASSO 1: Dropar policies RLS existentes
-- Execute SOZINHO no SQL Editor do Supabase
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
