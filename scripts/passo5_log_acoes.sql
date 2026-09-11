-- PASSO 5: Tabela de log de ações (auditoria)
-- Execute no SQL Editor do Supabase.
-- Registra toda mutação (INSERT/UPDATE/DELETE) feita pelo app, por usuário.

CREATE TABLE IF NOT EXISTS log_acoes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES usuarios(id),
    acao TEXT NOT NULL,
    tabela TEXT NOT NULL,
    query TEXT,
    parametros TEXT,
    criado_em TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_log_acoes_user_criado ON log_acoes(user_id, criado_em DESC);

ALTER TABLE log_acoes ENABLE ROW LEVEL SECURITY;

-- Cada usuário só vê e só cria os próprios registros de log.
-- Sem policy de UPDATE/DELETE de propósito: log é somente-leitura pela UI.
CREATE POLICY "log_acoes_select" ON log_acoes FOR SELECT
USING (user_id = current_setting('app.current_user_id', true)::integer);
CREATE POLICY "log_acoes_insert" ON log_acoes FOR INSERT
WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);
