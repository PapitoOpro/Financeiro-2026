# ==========================================
# MÓDULO: PROJEÇÃO DE GASTOS (EXEMPLO)
# ==========================================


import streamlit as st
import pandas as pd
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from config import MESES_LISTA, CORES
from database import db
from utils import moeda, extrair_texto_pdf, detectar_banco, extrair_parcelas, get_cor_valor

class ParcelasManager:
    """Gerenciador de Projeção de Gastos (Parcelas)."""
    
    @staticmethod
    def renderizar():
        """Renderiza a página de projeção de gastos."""
        st.header("📉 Projeção de Gastos (Cartão/Parcelas)")
        
        tab1, tab2, tab3 = st.tabs(["Manual", "Importar PDF", "Previsão"])
        
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")
        
        with tab1:
            ParcelasManager._tab_manual(df_contas, df_cats)
        
        with tab2:
            ParcelasManager._tab_importar_pdf(df_contas, df_cats)
        
        with tab3:
            ParcelasManager._tab_previsao()
    
    @staticmethod
    def _tab_manual(df_contas, df_cats):
        """Aba para lançamento manual de parcelas."""
        st.subheader("Lançamento Manual de Parcelas")
        
        with st.form("parcelas_manual"):
            desc = st.text_input("Descrição (Ex: Compra Mercado Livre)")
            
            c_val, c_p_atual, c_p_total = st.columns(3)
            v_parcela = c_val.number_input("Valor da Parcela (R$)", min_value=0.0)
            p_atual = c_p_atual.number_input("Parcela Atual", min_value=1, value=1)
            p_total = c_p_total.number_input("Total de Parcelas", min_value=1, value=1)
            
            c1, c2, c3 = st.columns(3)
            cnt = c1.selectbox("Cartão", df_contas['nome'] if not df_contas.empty else [""])
            cat = c2.selectbox("Categoria", df_cats['nome'] if not df_cats.empty else [""])
            dt_ini = c3.date_input("Vencimento da 1ª parcela")
            
            if st.form_submit_button("Lançar Parcelas", use_container_width=True):
                if not desc or v_parcela <= 0:
                    st.error("❌ Preencha descrição e valor!")
                elif p_atual > p_total:
                    st.error("❌ Parcela atual não pode ser maior que total!")
                else:
                    ParcelasManager._lancar_parcelas(
                        desc, v_parcela, p_atual, p_total, cnt, cat, dt_ini,
                        df_contas, df_cats
                    )
    
    @staticmethod
    def _lancar_parcelas(desc, val, p_atual, p_total, cnt, cat, dt_ini, df_contas, df_cats):
        """Lança parcelas no banco."""
        cid = int(df_contas[df_contas.nome == cnt].id.values[0])
        ctid = int(df_cats[df_cats.nome == cat].id.values[0])
        
        parcelas_lancar = (int(p_total) - int(p_atual)) + 1
        
        for i in range(parcelas_lancar):
            venc = dt_ini + relativedelta(months=i)
            num_parc = int(p_atual) + i
            d_final = f"[{cnt}] {desc} ({num_parc:02d}/{int(p_total):02d})"
            
            db.executar(
                "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CARTAO')",
                (d_final, -val, venc, cid, ctid)
            )
        
        st.success(f"✅ {parcelas_lancar} parcelas lançadas!")
        st.rerun()
    
    @staticmethod
    def _tab_importar_pdf(df_contas, df_cats):
        """Aba para importar faturas PDF com debug melhorado."""
        st.subheader("📄 Importador Universal de Faturas via OCR")
        
        senha_pdf = st.text_input("Senha do PDF (geralmente CPF ou primeiros dígitos)", type="password")
        file = st.file_uploader("Envie a fatura PDF", type="pdf")

        if file:
            with st.spinner("Lendo a fatura com inteligência artificial... Isso pode demorar uns segundos."):
                texto = extrair_texto_pdf(file, senha_pdf if senha_pdf else None)

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
                    for d in dados[:5]:  # Mostra só as 5 primeiras para não poluir muito a tela
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
                            st.error(f"⛔ **BLOQUEADO:** O PDF é do **{banco}**, mas você tentou importar no cartão **{conta}**.\nSe estiver correto, marque a caixa 'Forçar importação' acima.")
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

                                    check = db.buscar_um("""
                                        SELECT id FROM transacoes 
                                        WHERE descricao LIKE ? AND valor=? AND data_vencimento=?
                                    """, (desc_like, -val, venc))

                                    if not check:
                                        db.executar(
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
    
    @staticmethod
    def _importar_pdf_dados(dados, banco, conta, cat, data_base, df_contas, df_cats):
        """Importa dados do PDF para o BD."""
        cid = int(df_contas[df_contas.nome == conta].id.values[0])
        ctid = int(df_cats[df_cats.nome == cat].id.values[0])
        novos = duplicados = 0
        
        for desc, parc, val in dados:
            atual, total = map(int, parc.split("/"))
            for i in range(atual-1, total):
                venc = data_base + relativedelta(months=i-(atual-1))
                desc_f = f"[{conta}] {desc} ({i+1:02d}/{total:02d})"
                desc_like = f"%] {desc} ({i+1:02d}/{total:02d})"
                
                check = db.buscar_um(
                    "SELECT id FROM transacoes WHERE descricao LIKE ? AND valor=? AND data_vencimento=?",
                    (desc_like, -val, venc)
                )
                
                if not check:
                    db.executar(
                        "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CARTAO')",
                        (desc_f, -val, venc, cid, ctid)
                    )
                    novos += 1
                else:
                    duplicados += 1
        
        if novos > 0:
            st.success(f"🚀 {novos} parcelas importadas!")
        if duplicados > 0:
            st.info(f"ℹ️ {duplicados} duplicadas (ignoradas)")
    
    @staticmethod
    def _tab_previsao():
        """Aba com previsão de gastos - Dashboard completo."""
        st.subheader("📅 Dashboard de Previsão de Gastos")
        
        df_p = db.buscar("""
            SELECT t.id, t.data_vencimento, t.descricao, t.valor, c.nome as banco
            FROM transacoes t
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.tipo_fluxo='CARTAO'
            ORDER BY t.data_vencimento ASC
        """)
        
        if df_p.empty:
            st.info("ℹ️ Nenhuma parcela lançada")
            return
        
        df_p['data_vencimento'] = pd.to_datetime(df_p['data_vencimento'])
        
        # ==============================
        # 🏆 1. MÉTRICAS DE TOPO
        # ==============================
        total_divida = abs(df_p['valor'].sum())
        
        # Agrupa os valores por Mês/Ano para o gráfico
        df_p['Mes_Ano'] = df_p['data_vencimento'].dt.to_period('M')
        agrupado_mes = df_p.groupby('Mes_Ano')['valor'].sum().abs().reset_index()
        agrupado_mes['Mes_Ano_Str'] = agrupado_mes['Mes_Ano'].astype(str)
        
        mes_mais_pesado = agrupado_mes.loc[agrupado_mes['valor'].idxmax()]
        
        col1, col2 = st.columns(2)
        col1.metric("💰 Total Parcelado", moeda(total_divida))
        col2.metric("⚠️ Mês Mais Pesado", f"{mes_mais_pesado['Mes_Ano_Str']} - {moeda(mes_mais_pesado['valor'])}")
        
        st.markdown("---")
        
        # ==============================
        # 📊 2. GRÁFICO DE EVOLUÇÃO
        # ==============================
        st.markdown("**📈 Evolução do Parcelamento nos Próximos Meses**")
        df_grafico = agrupado_mes[['Mes_Ano_Str', 'valor']].set_index('Mes_Ano_Str')
        st.bar_chart(df_grafico, color="#e74c3c", use_container_width=True)
        
        st.markdown("---")
        
        # ==============================
        # 📝 3. LISTAGEM CASCATA COM EDIÇÃO
        # ==============================
        st.markdown("**📋 Detalhamento por Mês**")
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
                
                with st.expander(f"📅 **{mes_atual.strftime('%B/%Y').upper()}** — Total: {moeda(total_mes)}", expanded=False):
                    cartoes_no_mes = f_mes['banco'].fillna("Desconhecido").unique()
                    
                    for cartao in cartoes_no_mes:
                        f_cartao = f_mes[f_mes['banco'].fillna("Desconhecido") == cartao]
                        subtotal_cartao = abs(f_cartao['valor'].sum())
                        
                        st.markdown(f"**💳 Fatura: {cartao}** — Subtotal: **{moeda(subtotal_cartao)}**")
                        
                        # Tabela com parcelas
                        for _, r in f_cartao.iterrows():
                            col1, col2, col3, col4 = st.columns([5, 2, 1, 1])
                            
                            desc_limpa = re.sub(r'^\[.*?\]\s*', '', r['descricao'])
                            
                            col1.write(f"↳ {desc_limpa}")
                            col2.write(f"**{moeda(abs(r['valor']))}**")
                            
                            # Button editar
                            with col3:
                                if st.button("✏️", key=f"edit_parc_{r['id']}", help="Editar parcela"):
                                    st.session_state[f"edit_parc_{r['id']}"] = True
                            
                            # Button deletar
                            if col4.button("🗑️", key=f"del_parc_{r['id']}", help="Deletar parcela"):
                                db.executar("DELETE FROM transacoes WHERE id=?", (r['id'],))
                                st.success("✅ Parcela deletada!")
                                st.rerun()
                            
                            # Popover de edição
                            if st.session_state.get(f"edit_parc_{r['id']}", False):
                                with st.popover(f"Editar {desc_limpa}", use_container_width=True):
                                    n_desc = st.text_input("Descrição", value=r['descricao'], key=f"ed_desc_{r['id']}")
                                    n_val = st.number_input("Valor (R$)", value=abs(float(r['valor'])), min_value=0.0, step=0.01, key=f"ed_val_{r['id']}")
                                    n_data = st.date_input("Data", value=pd.to_datetime(r['data_vencimento']).date(), key=f"ed_data_{r['id']}")
                                    
                                    if st.button("💾 Salvar", key=f"save_parc_{r['id']}", use_container_width=True):
                                        db.executar(
                                            "UPDATE transacoes SET descricao=?, valor=?, data_vencimento=? WHERE id=?",
                                            (n_desc, -n_val, n_data, r['id'])
                                        )
                                        st.success("✅ Parcela atualizada!")
                                        st.session_state[f"edit_parc_{r['id']}"] = False
                                        st.rerun()
                        
                        st.divider()
