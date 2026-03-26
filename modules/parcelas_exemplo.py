# ==========================================
# MÓDULO: PROJEÇÃO DE GASTOS (EXEMPLO)
# ==========================================

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
from utils import moeda, processar_fatura

class ParcelasManager:
    """Gerenciador de Projeção de Gastos (Parcelas)."""
    
    @staticmethod
    def renderizar():
        """Renderiza a página de projeção de gastos."""
        st.header("📉 Projeção de Gastos (Cartão/Parcelas)")
        
        # Carrega dados essenciais no início para evitar erros de "não definido"
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")
        
        tab1, tab2, tab3 = st.tabs(["Manual", "Importar PDF", "Previsão"])
        
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
            # Proteção caso não existam contas/categorias cadastradas
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
        """Lança as parcelas manuais no banco de dados."""
        try:
            cid = int(df_contas[df_contas.nome == cnt].id.values[0])
            ctid = int(df_cats[df_cats.nome == cat].id.values[0])
            parcelas_lancar = (int(p_total) - int(p_atual)) + 1

            for i in range(parcelas_lancar):
                venc = dt_ini + relativedelta(months=i)
                num_parc = int(p_atual) + i
                d_final = f"[{cnt}] {desc} ({num_parc:02d}/{int(p_total):02d})"
                
                # Se usar PostgreSQL (Supabase), mude ? para %s
                query = """
                    INSERT INTO transacoes 
                    (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) 
                    VALUES (?, ?, ?, ?, ?, 'CARTAO')
                """
                db.executar(query, (d_final, -float(val), venc, cid, ctid))
            
            st.success(f"✅ {parcelas_lancar} parcelas lançadas com sucesso!")
            ParcelasManager._resetar_estado_pdf()
            # Pequeno delay antes do rerun ajuda a visualizar a mensagem de sucesso

        except Exception as e:
            st.error(f"Erro ao lançar parcelas: {e}")

    @staticmethod
    def _resetar_estado_pdf():
        """Limpa as variáveis de controle da interface de importação."""
        st.session_state["ocr_file_name"] = None
        st.session_state["ocr_banco"] = "GENÉRICO"
        st.session_state["ocr_texto"] = ""
        st.session_state["ocr_dados"] = []
    
    @staticmethod
    def _tab_importar_pdf(df_contas, df_cats):
        """Aba para importar faturas PDF via OCR."""
        st.subheader("📄 Importador de Faturas via OCR")
        
        senha_pdf = st.text_input("Senha do PDF (Se houver)", type="password")
        file = st.file_uploader("Envie a fatura PDF", type="pdf")

        # 1. Limpa o estado se o usuário enviar um arquivo diferente
        if file and st.session_state.get("ocr_file_name") != file.name:
            ParcelasManager._resetar_estado_pdf()
            st.session_state["ocr_file_name"] = file.name

        # 2. Botão de Processamento: Apenas extrai e salva no session_state
        if file and st.button("🔍 Analisar Fatura"):
            with st.spinner("Extraindo dados do PDF..."):
                banco, texto, dados = processar_fatura(file, senha_pdf)
                
                # Salva o resultado no estado para que sobreviva a recarregamentos da tela
                st.session_state["ocr_banco"] = banco
                st.session_state["ocr_texto"] = texto
                st.session_state["ocr_dados"] = dados
                
                if not dados:
                    st.warning("⚠️ Texto extraído, mas nenhuma parcela detectada pelo padrão (Regex).")
                else:
                    st.success(f"✅ {len(dados)} parcelas encontradas no {banco}!")

        # 3. Exibição e Confirmação: Lê os dados do session_state
        dados_salvos = st.session_state.get("ocr_dados", [])
        banco_detectado = st.session_state.get("ocr_banco", "Desconhecido")
        
        if dados_salvos:
            st.markdown(f"### 🏦 Banco Detectado: **{banco_detectado}**")
            
            df_preview = pd.DataFrame(dados_salvos, columns=["Descrição", "Parcela", "Valor"])
            st.dataframe(df_preview, use_container_width=True) 

            # Formulário para salvar no banco
            with st.form("confirmar_importacao"):
                st.markdown("#### Configurar Lançamento em Lote")
                col1, col2 = st.columns(2)
                
                # Previne erro se listas vazias
                lista_contas = df_contas['nome'].tolist() if not df_contas.empty else ["Sem contas"]
                lista_cats = df_cats['nome'].tolist() if not df_cats.empty else ["Sem categorias"]
                
                conta = col1.selectbox("Cartão de Destino", lista_contas)
                data_base = col2.date_input("Vencimento da 1ª Parcela do Lote")
                cat = st.selectbox("Categoria Padrão", lista_cats)
                
                if st.form_submit_button("🚀 Salvar no Banco (Aplicar Trava Anti-Duplicidade)", use_container_width=True):
                    ParcelasManager._importar_pdf_dados(
                        dados_salvos, banco_detectado, conta, cat, data_base, df_contas, df_cats
                    )

    @staticmethod
    def _importar_pdf_dados(dados, banco, conta, cat, data_base, df_contas, df_cats):
        """Importa dados do PDF para o BD com trava de duplicidade."""
        try:
            cid = int(df_contas[df_contas.nome == conta].id.values[0])
            ctid = int(df_cats[df_cats.nome == cat].id.values[0])
            
            novos = 0
            duplicados = 0
            
            for desc, parc, val in dados:
                try:
                    # Extrai os números da parcela "02/10"
                    atual, total = map(int, parc.split("/"))
                    
                    # Gerar todas as parcelas restantes a partir da atual
                    for i in range(atual - 1, total):
                        venc = data_base + relativedelta(months=i - (atual - 1))
                        num_parc_atual = i + 1
                        
                        desc_f = f"[{conta}] {desc} ({num_parc_atual:02d}/{total:02d})"
                        desc_busca = f"%{desc}%({num_parc_atual:02d}/{total:02d})%" 
                        
                        # TRAVA: Verifica se já existe (Ajuste ? para %s se Supabase/Postgres)
                        query_check = """
                            SELECT id FROM transacoes 
                            WHERE (descricao LIKE ? OR descricao = ?)
                            AND valor = ? 
                            AND data_vencimento = ?
                        """
                        check = db.buscar_um(query_check, (desc_busca, desc_f, -float(val), venc))
                        
                        if not check:
                            query_ins = """
                                INSERT INTO transacoes 
                                (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) 
                                VALUES (?, ?, ?, ?, ?, 'CARTAO')
                            """
                            db.executar(query_ins, (desc_f, -float(val), venc, cid, ctid))
                            novos += 1
                        else:
                            duplicados += 1
                            
                except Exception as inner_e:
                    st.warning(f"Erro ao processar linha '{desc}': {inner_e}")
                    continue

            # Feedback usando Toast para não sumir no Rerun
            if novos > 0:
                st.toast(f"✅ {novos} parcelas salvas!", icon="🎉")
            if duplicados > 0:
                st.toast(f"ℹ️ {duplicados} ignoradas (já existiam).", icon="🛡️")
            
            ParcelasManager._resetar_estado_pdf()
            #st.rerun() # Descomente se quiser forçar a recarga imediata, mas o toast pode sumir rápido.

        except Exception as e:
            st.error(f"Erro fatal na importação: {e}")

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
            st.info("ℹ️ Nenhuma parcela lançada no cartão ainda.")
            return
        
        df_p['data_vencimento'] = pd.to_datetime(df_p['data_vencimento'])
        
        # 1. MÉTRICAS DE TOPO
        total_divida = abs(df_p['valor'].sum())
        
        df_p['Mes_Ano'] = df_p['data_vencimento'].dt.to_period('M')
        agrupado_mes = df_p.groupby('Mes_Ano')['valor'].sum().abs().reset_index()
        agrupado_mes['Mes_Ano_Str'] = agrupado_mes['Mes_Ano'].astype(str)
        
        mes_mais_pesado = agrupado_mes.loc[agrupado_mes['valor'].idxmax()]
        
        col1, col2 = st.columns(2)
        col1.metric("💰 Total Parcelado a Pagar", moeda(total_divida))
        col2.metric("⚠️ Mês Mais Pesado", f"{mes_mais_pesado['Mes_Ano_Str']} - {moeda(mes_mais_pesado['valor'])}")
        
        st.markdown("---")
        
        # 2. GRÁFICO DE EVOLUÇÃO
        st.markdown("**📈 Evolução do Parcelamento nos Próximos Meses**")
        df_grafico = agrupado_mes[['Mes_Ano_Str', 'valor']].set_index('Mes_Ano_Str')
        st.bar_chart(df_grafico, color="#e74c3c", use_container_width=True)
        
        st.markdown("---")
        
        # 3. LISTAGEM CASCATA
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
                
                with st.expander(f"📅 **{mes_atual.strftime('%m/%Y')}** — Total: {moeda(total_mes)}", expanded=False):
                    cartoes_no_mes = f_mes['banco'].fillna("Desconhecido").unique()
                    
                    for cartao in cartoes_no_mes:
                        f_cartao = f_mes[f_mes['banco'].fillna("Desconhecido") == cartao]
                        subtotal_cartao = abs(f_cartao['valor'].sum())
                        
                        st.markdown(f"**💳 Fatura: {cartao}** — Subtotal: **{moeda(subtotal_cartao)}**")
                        
                        for _, r in f_cartao.iterrows():
                            c1, c2, c3 = st.columns([6, 2, 1])
                            desc_limpa = re.sub(r'^\[.*?\]\s*', '', r['descricao'])
                            
                            c1.write(f"↳ {desc_limpa}")
                            c2.write(f"**{moeda(abs(r['valor']))}**")
                            
                            # Simplificado o delete para evitar recargas complexas dentro do loop
                            if c3.button("🗑️", key=f"del_parc_{r['id']}", help="Deletar parcela"):
                                db.executar("DELETE FROM transacoes WHERE id=?", (r['id'],))
                                st.rerun()