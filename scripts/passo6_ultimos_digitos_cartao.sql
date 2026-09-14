-- PASSO 6: Últimos dígitos do cartão em `contas`
-- Execute no SQL Editor do Supabase.
-- Permite detectar automaticamente qual conta/cartão corresponde a uma
-- fatura importada (casando com os últimos dígitos impressos no PDF).

ALTER TABLE contas ADD COLUMN IF NOT EXISTS ultimos_digitos TEXT;
