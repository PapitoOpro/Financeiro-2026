-- PASSO 3: Criar tabelas + índices
-- Execute SOZINHO no SQL Editor do Supabase
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT,
    email TEXT,
    auth_id UUID UNIQUE,
    aprovado BOOLEAN DEFAULT FALSE,
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
    user_id INTEGER REFERENCES usuarios(id)
);

CREATE TABLE transacoes (
    id SERIAL PRIMARY KEY,
    descricao TEXT,
    valor NUMERIC,
    data_vencimento DATE,
    conta_id INTEGER REFERENCES contas(id),
    categoria_id INTEGER REFERENCES categorias(id),
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

CREATE UNIQUE INDEX ux_contas_nome_user ON contas(nome, user_id);
CREATE UNIQUE INDEX ux_categorias_nome_user ON categorias(nome, user_id);
CREATE UNIQUE INDEX ux_limites_chave_user ON limites_financeiros(chave, user_id);
CREATE UNIQUE INDEX ux_transacoes_desc_val_data ON transacoes(user_id, lower(trim(descricao)), valor, data_vencimento);
