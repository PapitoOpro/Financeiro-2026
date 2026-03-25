import os
import re
import unicodedata
import bcrypt
import psycopg2
import pandas as pd
import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px
import PyPDF2
import pytesseract
from PIL import Image
import io

# ==========================================
# 1. FUNÇÕES AUXILIARES (DO SEU CÓDIGO ORIGINAL)
# ==========================================
def moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def remover_acentos(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()
def extrair_texto_pdf(file, senha):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()), password=senha if senha else None)
        texto = ""
        for page in pdf_reader.pages:
            texto += page.extract_text()
        return texto
    except Exception as e:
        return ""

def detectar_banco(texto):
    # Lógica simples para detectar banco pelo texto
    if "nubank" in texto.lower():
        return "NUBANK"
    elif "itau" in texto.lower():
        return "ITAU"
    # Adicione mais bancos
    return "GENÉRICO"

def extrair_parcelas(texto):
    # Use regex para extrair parcelas
    import re
    parcelas = []
    # Exemplo: procure por padrões como "Compra X (1/12) R$ 100,00"
    # Implemente a lógica de extração
    return parcelas
# ==========================================
# 2. CONFIGURAÇÃO DO BANCO (SUPABASE)
# ==========================================
@st.cache_resource
def conectar():
    try:
        return psycopg2.connect(
            host=st.secrets["db_host"],
            database=st.secrets["db_name"],
            user=st.secrets["db_user"],
            password=st.secrets["db_password"],
            port=st.secrets["db_port"]
        )
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

conn = conectar()

def executar(query, params=()):
    try:
        q = query.replace('?', '%s')
        with conn.cursor() as cur:
            cur.execute(q, params)
        conn.commit()
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        conn.rollback()

def buscar(query, params=()):
    q = query.replace('?', '%s')
    return pd.read_sql(q, conn, params=params)

def buscar_um(query, params=()):
    q = query.replace('?', '%s')
    with conn.cursor() as cur:
        cur.execute(q, params)
        return cur.fetchone()

# Garante que as tabelas existam
def inicializar_banco():
    executar('CREATE TABLE IF NOT EXISTS contas (id SERIAL PRIMARY KEY, nome TEXT)')
    executar('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT)')
    executar('''CREATE TABLE IF NOT EXISTS transacoes (
                id SERIAL PRIMARY KEY, descricao TEXT, valor NUMERIC, 
                data_vencimento DATE, conta_id INTEGER, categoria_id INTEGER, tipo_fluxo TEXT)''')
    executar('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT, username TEXT UNIQUE, senha TEXT)')

inicializar_banco()

# ==========================================
# 3. CONTROLE DE ACESSO (LOGIN)
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso ao Sistema 2026")
    tab1, tab2 = st.tabs(["Login", "Cadastrar Novo Usuário"])
    
    with tab1:
        with st.form("l"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = buscar_um("SELECT nome, senha FROM usuarios WHERE username = ?", (u,))
                if res and bcrypt.checkpw(p.encode('utf-8'), res[1].encode('utf-8')):
                    st.session_state.logado = True
                    st.session_state.usuario_nome = res[0]
                    st.rerun()
                else: st.error("Incorreto")
    
    with tab2:
        with st.form("c"):
            n = st.text_input("Nome")
            user = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                h = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                executar("INSERT INTO usuarios (nome, username, senha) VALUES (?, ?, ?)", (n, user, h))
                st.success("Pronto! Faça login.")
    st.stop()

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================

def moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

meses_lista = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

st.sidebar.title("SISTEMA 2026")
menu = st.sidebar.radio("Navegação:", [
    "1- Controle de Caixa",
    "2- Projeção de Gastos (Cartão/Parcelas)",
    "3- Cadastros",
    "4- Relatórios Analíticos"
])

# =======================
# 1- CONTROLE DE CAIXA (LAYOUT DASHBOARD COM EDIÇÃO)
# =======================
if menu == "1- Controle de Caixa":
    st.header("[ $ ] Controle de Caixa Real")
    
    # 1. FILTROS NO TOPO
    col_m1, col_m2 = st.columns([1, 1])
    mes_nome = col_m1.selectbox("Mês:", meses_lista, index=datetime.now().month - 1)
    ano_sel = col_m2.number_input("Ano:", min_value=2025, max_value=2030, value=2026)
    
    mes_num = meses_lista.index(mes_nome) + 1
    data_inicio = f"{ano_sel}-{mes_num:02d}-01"
    data_fim = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).strftime('%Y-%m-%d')

    df_contas = pd.read_sql("SELECT * FROM contas", conn)
    df_cats = pd.read_sql("SELECT * FROM categorias", conn)

    # BUSCAMOS OS DADOS PRIMEIRO PARA ALIMENTAR OS CARDS
    df_caixa = pd.read_sql(f"""
        SELECT t.id, t.data_vencimento as Data, t.descricao, t.valor, cat.nome as Categoria, c.nome as Banco 
        FROM transacoes t 
        LEFT JOIN categorias cat ON t.categoria_id = cat.id 
        LEFT JOIN contas c ON t.conta_id = c.id
        WHERE (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL) 
        AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}' 
        ORDER BY t.data_vencimento DESC
    """, conn)

    ent = df_caixa[df_caixa['valor'] > 0]['valor'].sum() if not df_caixa.empty else 0
    sai = abs(df_caixa[df_caixa['valor'] < 0]['valor'].sum()) if not df_caixa.empty else 0
    bal = ent - sai
    bg_bal = "#2ecc71" if bal >= 0 else "#e74c3c"

    # 2. CARDS DE RESUMO LOGO ABAIXO DOS FILTROS (Com Dark Mode Fix)
    st.markdown(f'''
        <div style="display: flex; gap: 10px; margin-bottom: 25px; margin-top: 10px;">
            <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #2ecc71;">
                <small>Entradas</small><br><strong style="font-size: 20px; color: #27ae60;">{moeda(ent)}</strong>
            </div>
            <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #e74c3c;">
                <small>Saídas</small><br><strong style="font-size: 20px; color: #c0392b;">-{moeda(sai)}</strong>
            </div>
            <div style="background:{bg_bal}; color:#ffffff; padding:15px; border-radius:10px; flex:1;">
                <small>Balanço Final</small><br><strong style="font-size: 22px;">{moeda(bal)}</strong>
            </div>
        </div>
    ''', unsafe_allow_html=True)

    # 3. DIVISÃO DA TELA: EXTRATO (Esquerda) | FORMULÁRIO (Direita)
    col_extrato, col_espaco, col_form = st.columns([5, 0.2, 3])

    # LADO DIREITO: FORMULÁRIO COMPACTO
    with col_form:
        st.markdown("**[ + ] Novo Lançamento**")
        with st.form("form_caixa", clear_on_submit=True):
            desc_r = st.text_input("Descrição")
            val_r = st.number_input("Valor (R$)", min_value=0.0)
            
            c_tipo1, c_tipo2 = st.columns(2)
            tipo = c_tipo1.radio("Tipo", ["Entrada", "Saída"])
            data_pg = c_tipo2.date_input("Data", datetime.now())
            
            conta_r = st.selectbox("Conta/Banco", df_contas['nome'] if not df_contas.empty else [""])
            cat_r = st.selectbox("Categoria", df_cats['nome'] if not df_cats.empty else [""])
            
            if st.form_submit_button("Lançar no Caixa", use_container_width=True):
                if not desc_r or val_r <= 0:
                    st.error("Preencha descrição e valor!")
                else:
                    cid = int(df_contas[df_contas.nome == conta_r].id.values[0])
                    ctid = int(df_cats[df_cats.nome == cat_r].id.values[0])
                    valor_final = -val_r if "Saída" in tipo else val_r
                    executar("INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CAIXA')", 
                             (desc_r, valor_final, data_pg, cid, ctid))
                    st.rerun()

    # LADO ESQUERDO: LISTA DE TRANSAÇÕES ESTILO EXTRATO COM EDIÇÃO
    with col_extrato:
        st.markdown("**[ = ] Extrato de Transações**")
        if not df_caixa.empty:
            for _, row in df_caixa.iterrows():
                # Colunas ajustadas para caber 2 botões pequenos no final
                c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2.5, 0.8, 0.8])
                
                c1.write(pd.to_datetime(row['Data']).strftime('%d/%m/%Y'))
                
                c2.markdown(f"**{row['descricao']}**<br><span style='color:gray; font-size:12px;'>{row['Categoria']} | {row['Banco']}</span>", unsafe_allow_html=True)
                
                c3.markdown(f"<div style='text-align: right; color:{'#27ae60' if row['valor']>0 else '#c0392b'}; font-weight:bold;'>{moeda(row['valor'])}</div>", unsafe_allow_html=True)
                
                # BOTÃO EDITAR (✏️)
                with c4:
                    with st.popover("✏️"):
                        st.markdown("**Editar Lançamento**")
                        
                        n_desc = st.text_input("Descrição", value=row['descricao'], key=f"ec_desc_{row['id']}")
                        n_val = st.number_input("Valor (R$)", value=abs(float(row['valor'])), min_value=0.0, step=1.0, key=f"ec_val_{row['id']}")
                        
                        n_tipo = st.radio("Tipo", ["Entrada", "Saída"], index=0 if row['valor'] >= 0 else 1, horizontal=True, key=f"ec_tipo_{row['id']}")
                        n_data = st.date_input("Data", pd.to_datetime(row['Data']), key=f"ec_data_{row['id']}")
                        
                        # Pegando as listas para encontrar qual era a opção selecionada
                        lista_contas = df_contas['nome'].tolist()
                        idx_conta = lista_contas.index(row['Banco']) if row['Banco'] in lista_contas else 0
                        n_conta = st.selectbox("Conta/Banco", lista_contas, index=idx_conta, key=f"ec_cnt_{row['id']}")
                        
                        lista_cats = df_cats['nome'].tolist()
                        idx_cat = lista_cats.index(row['Categoria']) if row['Categoria'] in lista_cats else 0
                        n_cat = st.selectbox("Categoria", lista_cats, index=idx_cat, key=f"ec_cat_{row['id']}")
                        
                        if st.button("Salvar Correção", key=f"ec_save_{row['id']}", use_container_width=True):
                            cid = int(df_contas[df_contas.nome == n_conta].id.values[0])
                            ctid = int(df_cats[df_cats.nome == n_cat].id.values[0])
                            v_final = -n_val if n_tipo == "Saída" else n_val
                            
                            executar("""
                                UPDATE transacoes 
                                SET descricao=?, valor=?, data_vencimento=?, conta_id=?, categoria_id=?
                                WHERE id=?
                            """, (n_desc, v_final, n_data, cid, ctid, row['id']))
                            st.rerun()

                # BOTÃO DELETAR (🗑️)
                with c5:
                    if st.button("🗑️", key=f"del_c_{row['id']}", help="Excluir lançamento"):
                        executar("DELETE FROM transacoes WHERE id=?", (row['id'],))
                        st.rerun()
                
                # Linha divisória fina
                st.markdown("<hr style='margin: 0px 0px 10px 0px; padding: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma movimentação lançada neste mês.")

# =======================
# 2- PROJEÇÃO DE GASTOS
# =======================
elif menu == "2- Projeção de Gastos (Cartão/Parcelas)":

    st.header("📉 Parcelamentos Inteligentes")

    t1, t2, t3 = st.tabs(["Manual", "Importar PDF", "Relatório de Previsão"])

    df_contas = pd.read_sql("SELECT * FROM contas", conn)
    df_cats = pd.read_sql("SELECT * FROM categorias", conn)

    # =========================
    # T1 - MANUAL (OTIMIZADO)
    # =========================
    with t1:
        with st.form("p_man", clear_on_submit=True):
            st.markdown("**Lançamento Manual de Parcelas**")
            
            desc = st.text_input("Descrição (Ex: Compra Mercado Livre) *")
            
            # Trocamos "Valor Total" por "Valor da Parcela" e separamos as parcelas
            c_val, c_p_atual, c_p_total = st.columns(3)
            v_parcela = c_val.number_input("Valor da Parcela (R$) *", min_value=0.0)
            p_atual = c_p_atual.number_input("Parcela Atual (Começa na)", min_value=1, step=1, value=1)
            p_total = c_p_total.number_input("Total de Parcelas", min_value=1, step=1, value=1)
            
            c1, c2, c3 = st.columns(3)
            cnt = c1.selectbox("Cartão", df_contas['nome'] if not df_contas.empty else [""])
            cat = c2.selectbox("Categoria", df_cats['nome'] if not df_cats.empty else [""])
            dt_ini = c3.date_input("Vencimento desta parcela")

            if st.form_submit_button("Lançar Parcelas"):
                if not desc or v_parcela <= 0:
                    st.error("Preencha a descrição e o valor da parcela!")
                elif p_atual > p_total:
                    st.error("A parcela atual não pode ser maior que o total de parcelas!")
                else:
                    cid = int(df_contas[df_contas.nome == cnt].id.values[0])
                    ctid = int(df_cats[df_cats.nome == cat].id.values[0])

                    # Calcula quantas parcelas faltam lançar a partir da atual
                    parcelas_a_lancar = (int(p_total) - int(p_atual)) + 1

                    for i in range(parcelas_a_lancar):
                        venc = dt_ini + relativedelta(months=i)
                        num_parcela_atual = int(p_atual) + i
                        
                        d_final = f"[{cnt}] {desc} ({num_parcela_atual:02d}/{int(p_total):02d})"
                        
                        executar(
                            "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CARTAO')",
                            (d_final, -v_parcela, venc, cid, ctid)
                        )
                    st.success(f"{parcelas_a_lancar} parcelas lançadas com sucesso!")

   # =========================
    # T2 - IMPORTAR PDF (COM TRAVA DE SEGURANÇA DUPLA)
    # =========================
    with t2:
        st.subheader("📄 Importador Universal de Faturas via OCR")
        
        senha_pdf = st.text_input("Senha do PDF (geralmente CPF ou primeiros dígitos)", type="password")
        file = st.file_uploader("Envie a fatura PDF", type="pdf")

        if file:
            with st.spinner("Lendo a fatura com inteligência artificial... Isso pode demorar uns segundos."):
                texto = extrair_texto_pdf(file, senha_pdf)

            if texto.strip() == "":
                st.error("Falha ao extrair o texto. Verifique se a senha está correta.")
            else:
                banco = detectar_banco(texto)
                
                # Feedback visual de qual banco a IA detectou
                if banco != "GENÉRICO":
                    st.success(f"🏦 Banco detectado na fatura: **{banco}**")
                else:
                    st.warning("⚠️ Não foi possível identificar o banco automaticamente pelo texto.")

                with st.expander("Ver texto bruto lido pelo OCR"):
                    st.text(texto)

                dados = extrair_parcelas(texto)

                if dados:
                    st.info(f"✅ {len(dados)} parcelas encontradas no documento.")
                    for d in dados[:5]: # Mostra só as 5 primeiras para não poluir muito a tela
                        st.write(d)
                    if len(dados) > 5:
                        st.caption(f"... e mais {len(dados) - 5} parcelas.")

                    with st.form("importar_pdf_form"):
                        conta = st.selectbox("Cartão destino", df_contas['nome'])
                        cat = st.selectbox("Categoria principal", df_cats['nome'])
                        data_base = st.date_input("Data base da 1ª parcela da fatura")
                        
                        # 🔒 CAMADA 1: Checkbox de liberação manual
                        ignorar_trava = st.checkbox("Forçar importação (Marque apenas se o nome da sua conta no sistema for muito diferente do banco real)")

                        submit_import = st.form_submit_button("Importar no sistema")

                    if submit_import:
                        # Verifica se o banco detectado está no nome da conta que o usuário selecionou
                        if banco != "GENÉRICO" and banco not in conta.upper() and not ignorar_trava:
                            st.error(f"⛔ **BLOQUEADO:** O PDF é do **{banco}**, mas você tentou importar no cartão **{conta}**. \nSe estiver correto, marque a caixa 'Forçar importação' acima.")
                        else:
                            cid = int(df_contas[df_contas.nome == conta].id.values[0])
                            ctid = int(df_cats[df_cats.nome == cat].id.values[0])
                            novos = 0
                            duplicados = 0

                            for desc, parc, val in dados:
                                atual, total = map(int, parc.split("/"))
                                for i in range(atual-1, total):
                                    venc = data_base + relativedelta(months=i-(atual-1))
                                    desc_f = f"[{conta}] {desc} ({i+1:02d}/{total:02d})"

                                    # 🔒 CAMADA 2: Trava Universal de Duplicidade (Ignora o prefixo do cartão)
                                    # O LIKE "%]" faz ele ignorar se está escrito [Itaú] ou [Nubank] na hora de checar
                                    desc_like = f"%] {desc} ({i+1:02d}/{total:02d})"

                                    check = buscar_um("""
                                        SELECT id FROM transacoes 
                                        WHERE descricao LIKE ? AND valor=? AND data_vencimento=?
                                    """, (desc_like, -val, venc))

                                    if not check:
                                        executar(
                                            "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CARTAO')",
                                            (desc_f, -val, venc, cid, ctid)
                                        )
                                        novos += 1
                                    else:
                                        duplicados += 1
                            
                            if novos > 0:
                                st.success(f"🚀 {novos} novas parcelas importadas com sucesso!")
                            if duplicados > 0:
                                st.warning(f"🛡️ {duplicados} parcelas ignoradas porque já existiam no sistema (Prevenção de Duplicidade ativada).")
                else:
                    st.warning("Nenhuma parcela encontrada pelo Regex 😕. Abra o texto bruto acima para ver como o OCR leu o arquivo e ajustar o padrão.")

    # =========================
    # T3 - RELATÓRIO (MÉTRICAS, GRÁFICO E EDIÇÃO)
    # =========================
    with t3:
        st.subheader("📅 Dashboard de Previsão de Gastos")

        df_p = pd.read_sql("""
            SELECT t.id, t.data_vencimento, t.descricao, t.valor, c.nome as banco
            FROM transacoes t
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.tipo_fluxo='CARTAO'
            ORDER BY t.data_vencimento ASC
        """, conn)

        if not df_p.empty:
            df_p['data_vencimento'] = pd.to_datetime(df_p['data_vencimento'])
            
            # ==============================
            # 🏆 1. MÉTRICAS DE TOPO
            # ==============================
            total_divida = abs(df_p['valor'].sum())
            
            # Agrupa os valores por Mês/Ano para o gráfico e para achar o mês mais caro
            df_p['Mes_Ano'] = df_p['data_vencimento'].dt.to_period('M')
            agrupado_mes = df_p.groupby('Mes_Ano')['valor'].sum().abs().reset_index()
            agrupado_mes['Mes_Ano_Str'] = agrupado_mes['Mes_Ano'].astype(str)
            
            mes_mais_pesado = agrupado_mes.loc[agrupado_mes['valor'].idxmax()]
            
            c_met1, c_met2 = st.columns(2)
            c_met1.markdown(f'''
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; border-left:5px solid #e74c3c;">
                    <small>Total Parcelado a Pagar (Geral)</small><br><strong style="font-size: 22px; color: #c0392b;">{moeda(total_divida)}</strong>
                </div>
            ''', unsafe_allow_html=True)
            
            c_met2.markdown(f'''
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; border-left:5px solid #f39c12;">
                    <small>Mês mais pesado ({mes_mais_pesado["Mes_Ano"].strftime('%m/%Y')})</small><br><strong style="font-size: 22px; color: #d35400;">{moeda(mes_mais_pesado["valor"])}</strong>
                </div>
            ''', unsafe_allow_html=True)
            
            st.write("") # Espaço em branco
            
            # ==============================
            # 📊 2. GRÁFICO DE EVOLUÇÃO
            # ==============================
            st.markdown("**📉 Evolução do Parcelamento nos Próximos Meses**")
            df_grafico = agrupado_mes[['Mes_Ano_Str', 'valor']].set_index('Mes_Ano_Str')
            st.bar_chart(df_grafico, color="#e74c3c")
            
            st.divider()

            # ==============================
            # 📝 3. LISTAGEM CASCATA COM EDIÇÃO
            # ==============================
            meses_previsao = st.slider("Ver previsão detalhada para quantos meses?", 1, 24, 6)
            primeiro_mes = df_p['data_vencimento'].min().replace(day=1)

            for i in range(meses_previsao):
                mes_atual = primeiro_mes + relativedelta(months=i)
                f_mes = df_p[
                    (df_p['data_vencimento'].dt.month == mes_atual.month) &
                    (df_p['data_vencimento'].dt.year == mes_atual.year)
                ]

                if not f_mes.empty:
                    total_mes = abs(f_mes['valor'].sum())

                    with st.expander(f"📅 {mes_atual.strftime('%m/%Y')} — Total do Mês: {moeda(total_mes)}"):
                        cartoes_no_mes = f_mes['banco'].fillna("Desconhecido").unique()

                        for cartao in cartoes_no_mes:
                            f_cartao = f_mes[f_mes['banco'].fillna("Desconhecido") == cartao]
                            subtotal_cartao = abs(f_cartao['valor'].sum())
                            
                            st.markdown(f"**💳 Fatura: {cartao}** — Subtotal: <span style='color:#c0392b;'>{moeda(subtotal_cartao)}</span>", unsafe_allow_html=True)
                            
                            for _, r in f_cartao.iterrows():
                                # Adicionamos uma coluna a mais para caber os 2 botões
                                c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
                                
                                desc_limpa = re.sub(r'^\[.*?\]\s*', '', r['descricao'])

                                c1.write(f"↳ {desc_limpa}")
                                c2.write(f"{moeda(abs(r['valor']))}")

                                # BOTÃO ✏️ EDITAR (Abre um Pop-up)
                                with c3:
                                    with st.popover("✏️"):
                                        st.markdown("**Corrigir Parcela**")
                                        n_desc = st.text_input("Descrição", value=r['descricao'], key=f"e_desc_{r['id']}")
                                        n_val = st.number_input("Valor (R$)", value=abs(float(r['valor'])), min_value=0.0, step=1.0, key=f"e_val_{r['id']}")
                                        
                                        if st.button("Salvar Correção", key=f"save_{r['id']}"):
                                            # Salva o valor negativo no banco, igual foi lançado
                                            executar("UPDATE transacoes SET descricao=?, valor=? WHERE id=?", (n_desc, -n_val, r['id']))
                                            st.rerun()

                                # BOTÃO 🗑️ DELETAR
                                if c4.button("🗑️", key=f"del_t3_{r['id']}"):
                                    executar("DELETE FROM transacoes WHERE id=?", (r['id'],))
                                    st.rerun()
                            
                            st.divider()
        else:
            st.info("Nenhuma previsão de cartão encontrada! Quando você importar faturas, elas aparecerão aqui.")  
                                    
# =======================
# 3- CADASTROS (LAYOUT PROFISSIONAL COM EDIÇÃO)
# =======================
elif menu == "3- Cadastros":
    st.header("[ ⚙ ] Cadastros do Sistema")
    st.markdown("Gerencie suas contas bancárias, cartões e categorias de despesas.")

    # Divide a tela em 2 colunas principais, com um pequeno espaço (0.1) no meio
    c1, c_space, c2 = st.columns([1, 0.1, 1])

    # ----------------------------------------
    # COLUNA ESQUERDA: BANCOS E CARTÕES
    # ----------------------------------------
    with c1:
        st.markdown("### [ 💳 ] Bancos e Cartões")
        
        # Formulário Compacto para adicionar
        with st.form("form_novo_banco", clear_on_submit=True):
            col_input, col_btn = st.columns([3, 1])
            n_banco = col_input.text_input("Novo Banco/Cartão", label_visibility="collapsed", placeholder="Ex: Nubank, Itaú...")
            
            if col_btn.form_submit_button("Adicionar", use_container_width=True):
                if n_banco.strip():
                    executar("INSERT INTO contas (nome) VALUES (?)", (n_banco.strip(),))
                    st.rerun()
                else:
                    st.error("Digite um nome!")

        st.markdown("**Cadastrados:**")
        
        # Puxando do banco em ordem alfabética
        df_contas = pd.read_sql("SELECT * FROM contas ORDER BY nome", conn)
        
        for _, r in df_contas.iterrows():
            col_nome, col_edit, col_del = st.columns([4, 1, 1])
            col_nome.markdown(f"<div style='padding-top: 5px; font-weight: 500;'>{r['nome']}</div>", unsafe_allow_html=True)

            # Botão de Edição (Pop-up)
            with col_edit:
                with st.popover("✏️"):
                    st.markdown("**Renomear Conta**")
                    novo_nome = st.text_input("Nome", value=r['nome'], key=f"edit_c_nome_{r['id']}")
                    if st.button("Salvar", key=f"save_c_{r['id']}", use_container_width=True):
                        if novo_nome.strip():
                            executar("UPDATE contas SET nome=? WHERE id=?", (novo_nome.strip(), r['id']))
                            st.rerun()

            # Botão de Exclusão
            with col_del:
                if st.button("🗑️", key=f"del_c_{r['id']}", help="Excluir Conta"):
                    executar("DELETE FROM contas WHERE id=?", (r['id'],))
                    st.rerun()
            
            # Linha divisória fina
            st.markdown("<hr style='margin: 0px 0px 5px 0px; padding: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)


    # ----------------------------------------
    # COLUNA DIREITA: CATEGORIAS
    # ----------------------------------------
    with c2:
        st.markdown("### [ 🏷️ ] Categorias")
        
        # Formulário Compacto para adicionar
        with st.form("form_nova_cat", clear_on_submit=True):
            col_input, col_btn = st.columns([3, 1])
            n_cat = col_input.text_input("Nova Categoria", label_visibility="collapsed", placeholder="Ex: Alimentação, Lazer...")
            
            if col_btn.form_submit_button("Adicionar", use_container_width=True):
                if n_cat.strip():
                    executar("INSERT INTO categorias (nome) VALUES (?)", (n_cat.strip(),))
                    st.rerun()
                else:
                    st.error("Digite um nome!")

        st.markdown("**Cadastradas:**")
        
        # Puxando do banco em ordem alfabética
        df_cats = pd.read_sql("SELECT * FROM categorias ORDER BY nome", conn)
        
        for _, r in df_cats.iterrows():
            col_nome, col_edit, col_del = st.columns([4, 1, 1])
            col_nome.markdown(f"<div style='padding-top: 5px; font-weight: 500;'>{r['nome']}</div>", unsafe_allow_html=True)

            # Botão de Edição (Pop-up)
            with col_edit:
                with st.popover("✏️"):
                    st.markdown("**Renomear Categoria**")
                    novo_nome_cat = st.text_input("Nome", value=r['nome'], key=f"edit_cat_nome_{r['id']}")
                    if st.button("Salvar", key=f"save_cat_{r['id']}", use_container_width=True):
                        if novo_nome_cat.strip():
                            executar("UPDATE categorias SET nome=? WHERE id=?", (novo_nome_cat.strip(), r['id']))
                            st.rerun()

            # Botão de Exclusão
            with col_del:
                if st.button("🗑️", key=f"del_cat_{r['id']}", help="Excluir Categoria"):
                    executar("DELETE FROM categorias WHERE id=?", (r['id'],))
                    st.rerun()
            
            # Linha divisória fina
            st.markdown("<hr style='margin: 0px 0px 5px 0px; padding: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

# =======================
# 4- RELATÓRIOS ANALÍTICOS (COM CURVA ABC SEM EMOJIS)
# =======================
elif menu == "4- Relatórios Analíticos":
    st.header("Inteligência Financeira e Curva ABC")
    
    c1, c2 = st.columns(2)
    mes_sel = c1.selectbox("Mês de Análise:", meses_lista, index=datetime.now().month - 1)
    ano_sel = c2.number_input("Ano:", 2025, 2030, 2026)
    m_num = meses_lista.index(mes_sel) + 1
    d_ini, d_fim = f"{ano_sel}-{m_num:02d}-01", (datetime(ano_sel, m_num, 1) + relativedelta(months=1) - relativedelta(days=1)).strftime('%Y-%m-%d')
    
    df_an = pd.read_sql(f"""
        SELECT t.data_vencimento as Data, t.descricao as Descricao, t.valor, cat.nome as Categoria, c.nome as Banco 
        FROM transacoes t 
        LEFT JOIN categorias cat ON t.categoria_id = cat.id 
        LEFT JOIN contas c ON t.conta_id = c.id
        WHERE (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL) 
        AND t.data_vencimento BETWEEN '{d_ini}' AND '{d_fim}'
    """, conn)
    
    if not df_an.empty:
        ent = df_an[df_an['valor'] > 0]['valor'].sum()
        sai = abs(df_an[df_an['valor'] < 0]['valor'].sum())
        bal = ent - sai
        
        st.markdown(f'''
            <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #2ecc71;">
                    <small>Entradas</small><br><strong style="font-size: 22px; color: #27ae60;">{moeda(ent)}</strong>
                </div>
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #e74c3c;">
                    <small>Saídas</small><br><strong style="font-size: 22px; color: #c0392b;">-{moeda(sai)}</strong>
                </div>
                <div style="background:{'#2ecc71' if bal >=0 else '#e74c3c'}; color:#ffffff; padding:15px; border-radius:10px; flex:1;">
                    <small>Balanço</small><br><strong style="font-size: 22px;">{moeda(bal)}</strong>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        t_extrato, t_abc = st.tabs(["[+] Extrato do Mês", "[>] Curva ABC (Data e Valor)"])
        
        with t_extrato:
            df_extrato = df_an.copy()
            df_extrato['Data'] = pd.to_datetime(df_extrato['Data']).dt.strftime('%d/%m/%Y')
            df_extrato['valor'] = df_extrato['valor'].apply(moeda)
            
            cols_extrato = ['Data', 'Descricao', 'Banco', 'Categoria', 'valor']
            cols_extrato = [c for c in cols_extrato if c in df_extrato.columns]
            st.dataframe(df_extrato[cols_extrato], hide_index=True, use_container_width=True)
            
        with t_abc:
            st.markdown("**Curva ABC: Descubra quais despesas (e em quais datas) consomem o maior volume do seu dinheiro.**")
            
            df_saidas = df_an[df_an['valor'] < 0].copy()
            
            if not df_saidas.empty:
                df_saidas['Valor Absoluto'] = df_saidas['valor'].abs()
                df_abc = df_saidas.sort_values(by='Valor Absoluto', ascending=False).reset_index(drop=True)
                df_abc['% Acumulada'] = (df_abc['Valor Absoluto'].cumsum() / df_abc['Valor Absoluto'].sum()) * 100
                
                def classificar_abc(pct):
                    if pct <= 80: return '[ Classe A ] (Até 80%)'
                    elif pct <= 95: return '[ Classe B ] (80% a 95%)'
                    else: return '[ Classe C ] (95% a 100%)'
                    
                df_abc['Classe'] = df_abc['% Acumulada'].apply(classificar_abc)
                
                df_abc['Data'] = pd.to_datetime(df_abc['Data']).dt.strftime('%d/%m/%Y')
                df_abc['Valor Absoluto'] = df_abc['Valor Absoluto'].apply(moeda)
                df_abc['% Acumulada'] = df_abc['% Acumulada'].apply(lambda x: f"{x:.2f}%")
                
                cols_abc = ['Classe', 'Data', 'Descricao', 'Valor Absoluto', '% Acumulada']
                st.dataframe(df_abc[cols_abc], hide_index=True, use_container_width=True)
                
                st.info("[ DICA ] **Gestão:** Focar em renegociar, adiar ou cortar os itens da **Classe A** traz um impacto muito maior para a sua saúde financeira do que se preocupar com os gastos pulverizados da Classe C!")
            else:
                st.warning("Nenhuma saída (despesa) registrada neste mês para gerar a Curva ABC.")                                        
