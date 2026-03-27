# ==========================================
# MÓDULO: PROJEÇÃO DE GASTOS (EXEMPLO)
# ==========================================

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
import plotly.express as px
import plotly.graph_objects as go
from utils import moeda, processar_fatura, get_cor_valor, get_cor_saldo
from typing import Any, cast

class ParcelasManager:
    """Gerenciador de Projeção de Gastos (Parcelas)."""
    
    
    @staticmethod
    def renderizar():
        """Renderiza a página de projeção de gastos."""
        st.header("📉 Projeção de Gastos (Cartão/Parcelas)")
        
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")
        
        # 👇 Adicionamos a tab "Importar CSV" aqui
        tab1, tab2, tab3, tab4 = st.tabs(["Manual", "Importar PDF", "Importar CSV", "Previsão"])
        
        with tab1:
            ParcelasManager._tab_manual(df_contas, df_cats)
        
        with tab2:
            ParcelasManager._tab_importar_pdf(df_contas, df_cats)
            
        with tab3: # 👇 Nova aba
            ParcelasManager._tab_importar_csv(df_contas, df_cats)
        
        with tab4:
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
            cnt = c1.selectbox("Cartão/Banco", df_contas['nome'] if not df_contas.empty else [""])
            cat = c2.selectbox("Categoria", df_cats['nome'] if not df_cats.empty else [""])
            dt_ini = c3.date_input("Vencimento da 1ª parcela")
            
            if st.form_submit_button("Lançar Parcelas", width='stretch'):
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
    def _safe_rerun():
        """Tenta forçar um rerun de forma compatível com várias versões do Streamlit.

        Se a API pública `st.experimental_rerun` existir, usa-a. Caso contrário,
        tenta elevar a exceção interna `RerunException` em caminhos conhecidos.
        Se tudo falhar, mostra um aviso pedindo para atualizar a página manualmente.
        """
        try:
            exp_rerun = getattr(st, "experimental_rerun", None)
            if callable(exp_rerun):
                try:
                    exp_rerun()
                    return
                except Exception:
                    pass
        except Exception:
            pass

        # Fallback seguro: pare a execução atual e peça reload manual
        try:
            st.stop()
        except Exception:
            st.warning("Por favor, atualize a página manualmente para aplicar as mudanças.")
    
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
            st.dataframe(df_preview, width='stretch') 

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
                
                if st.form_submit_button("🚀 Salvar no Banco (Aplicar Trava Anti-Duplicidade)", width='stretch'):
                    ParcelasManager._importar_pdf_dados(
                        dados_salvos, banco_detectado, conta, cat, data_base, df_contas, df_cats
                    )
    @staticmethod
    @staticmethod
    def _tab_importar_csv(df_contas, df_cats):
        """Aba para importar faturas via arquivo CSV (Otimizada e com Conversor de Moeda)."""
        st.subheader("📊 Importador de Faturas via CSV")
        
        file_csv = st.file_uploader("Envie a fatura em formato CSV", type=["csv"])

        # Resetar estado se mudar de arquivo
        if file_csv and st.session_state.get("csv_file_name") != file_csv.name:
            st.session_state["csv_dados"] = []
            st.session_state["csv_file_name"] = file_csv.name

        if file_csv:
            try:
                # Tenta ler o CSV de forma flexível (suporta separador vírgula e ponto-e-vírgula)
                df_csv = pd.read_csv(file_csv, sep=None, engine='python')
                
                st.markdown("**1. Prévia do Arquivo:**")
                st.dataframe(df_csv.head(3), width='stretch')

                st.markdown("**2. Mapeamento de Colunas:**")
                c1, c2, c3 = st.columns(3)
                col_desc = c1.selectbox("Coluna da Descrição?", df_csv.columns)
                col_val = c2.selectbox("Coluna do Valor?", df_csv.columns)
                
                # Nova opção: Escolher coluna da parcela se existir
                opcoes_parc = ["Nenhuma (Extrair da Descrição)"] + list(df_csv.columns)
                col_parc = c3.selectbox("Coluna da Parcela? (Opcional)", opcoes_parc)

                if st.button("🔍 Extrair Dados do CSV", width='stretch'):
                    with st.spinner("Lendo linhas..."):
                        dados_extraidos = []
                        
                        for _, row in df_csv.iterrows():
                            # Define desc_original aqui, lendo a coluna escolhida
                            desc_original = str(row[col_desc])
                            
                            try:
                                # --- CONVERSOR DE MOEDA INTELIGENTE ---
                                val_raw = row[col_val]
                                
                                # Pula se a linha for nula/vazia
                                if pd.isna(val_raw):
                                    continue
                                    
                                # Se o Pandas já leu como número (int ou float)
                                if isinstance(val_raw, (int, float)):
                                    val = float(val_raw)
                                else:
                                    # Limpeza de texto de moeda
                                    val_str = str(val_raw).replace("R$", "").strip()
                                    
                                    # Resolve conflitos de ponto vs virgula
                                    if "." in val_str and "," in val_str:
                                        if val_str.rfind(",") > val_str.rfind("."):
                                            val_str = val_str.replace(".", "").replace(",", ".")
                                        else:
                                            val_str = val_str.replace(",", "")
                                    elif "," in val_str:
                                        val_str = val_str.replace(",", ".")
                                        
                                    val = float(val_str)
                                # ---------------------------------------
                                
                                # Ignora valores zerados
                                if abs(val) == 0:
                                    continue
                                
                                parc_formatada = "1/1"
                                desc_limpa = desc_original.strip()
                                
                                # CENÁRIO 1: O CSV já tem a coluna "Parcela"
                                if col_parc != "Nenhuma (Extrair da Descrição)":
                                    parc_val = str(row[col_parc]).strip()
                                    if "à vista" not in parc_val.lower():
                                        parc_match = re.search(r'(\d{1,2})/(\d{1,2})', parc_val)
                                        if parc_match:
                                            parc_formatada = f"{int(parc_match.group(1))}/{int(parc_match.group(2))}"
                                
                                # CENÁRIO 2: Extrair de textos
                                else:
                                    # Remove texto de data (Ex: Compra: 12/02) para não confundir com parcela
                                    texto_busca = re.sub(r'\(Compra:\s*\d{1,2}/\d{1,2}.*?\)', '', desc_original)
                                    texto_busca = re.sub(r'\(À vista\)', '', texto_busca, flags=re.IGNORECASE)
                                    
                                    parc_match = re.search(r'(\d{1,2})/(\d{1,2})', texto_busca)
                                    
                                    if parc_match:
                                        parc_formatada = f"{int(parc_match.group(1))}/{int(parc_match.group(2))}"
                                        desc_limpa = re.sub(r'\s*\d{1,2}/\d{1,2}\s*', '', desc_original).strip()
                                
                                dados_extraidos.append((desc_limpa, parc_formatada, abs(val)))
                                    
                            except Exception:
                                continue # Pula linhas inválidas
                                
                        st.session_state["csv_dados"] = dados_extraidos
                        st.success(f"✅ {len(dados_extraidos)} registros processados com sucesso!")

            except Exception as e:
                st.error(f"Erro ao ler o CSV. O arquivo pode estar corrompido: {e}")

        # 3. Exibição e Lançamento
        dados_salvos = st.session_state.get("csv_dados", [])
        
        if dados_salvos:
            st.markdown("---")
            st.markdown("### 📋 Conferência e Lançamento (CSV)")
            
            df_preview = pd.DataFrame(dados_salvos, columns=["Descrição", "Parcela", "Valor"])
            st.dataframe(df_preview, width='stretch')

            with st.form("confirmar_importacao_csv"):
                col1, col2 = st.columns(2)
                
                lista_contas = df_contas['nome'].tolist() if not df_contas.empty else ["Sem contas"]
                lista_cats = df_cats['nome'].tolist() if not df_cats.empty else ["Sem categorias"]
                
                conta = col1.selectbox("Cartão de Destino", lista_contas)
                data_base = col2.date_input("Vencimento da 1ª Parcela do Lote")
                cat = st.selectbox("Categoria Padrão", lista_cats)
                
                if st.form_submit_button("🚀 Salvar no Banco (Aplicar Trava Anti-Duplicidade)", width='stretch'):
                    
                    ParcelasManager._importar_pdf_dados(
                        dados=dados_salvos, 
                        banco="CSV IMPORT", 
                        conta=conta, 
                        cat=cat, 
                        data_base=data_base, 
                        df_contas=df_contas, 
                        df_cats=df_cats
                    )
                    
                    st.session_state["csv_dados"] = []               

    @staticmethod
    def _importar_pdf_dados(dados, banco, conta, cat, data_base, df_contas, df_cats):
        """Importa dados do PDF para o BD com trava de duplicidade."""
        try:
            cid = int(df_contas[df_contas.nome == conta].id.values[0])
            ctid = int(df_cats[df_cats.nome == cat].id.values[0])
            
            novos = 0
            duplicados = 0
            erros = 0
            
            for desc, parc, val in dados:
                try:
                    # Extrai os números da parcela "02/10"
                    atual, total = map(int, parc.split("/"))
                    
                    # Gerar todas as parcelas restantes a partir da atual
                    for i in range(atual - 1, total):
                        venc = data_base + relativedelta(months=i - (atual - 1))
                        num_parc_atual = i + 1
                        
                        desc_f = f"[{conta}] {desc} ({num_parc_atual:02d}/{total:02d})"
                        
                        # 🔒 TRAVA DE DUPLICIDADE (ignora prefixo [Cartão] via LIKE)
                        desc_busca = f"%] {desc} ({num_parc_atual:02d}/{total:02d})"
                        
                        query_check = """
                            SELECT id FROM transacoes 
                            WHERE descricao LIKE ?
                            AND ROUND(valor::numeric, 2) = ROUND(?::numeric, 2)
                            AND data_vencimento = ?
                        """
                        check = db.buscar_um(query_check, (desc_busca, -float(val), venc))
                        
                        if not check:
                            query_ins = """
                                INSERT INTO transacoes 
                                (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) 
                                VALUES (?, ?, ?, ?, ?, 'CARTAO')
                            """
                            resultado = db.executar(query_ins, (desc_f, -float(val), venc, cid, ctid))
                            if resultado:
                                novos += 1
                            else:
                                erros += 1
                        else:
                            duplicados += 1
                            
                except Exception as inner_e:
                    st.warning(f"Erro ao processar linha '{desc}': {inner_e}")
                    erros += 1
                    continue

            # Feedback
            if novos > 0:
                st.toast(f"✅ {novos} parcelas salvas!", icon="🎉")
            if duplicados > 0:
                st.toast(f"🛡️ {duplicados} ignoradas (já existiam).", icon="🛡️")
            if erros > 0:
                st.toast(f"⚠️ {erros} com erro.", icon="⚠️")
            if novos == 0 and duplicados > 0:
                st.warning(f"🛡️ Nenhuma parcela nova importada — {duplicados} já existiam no sistema.")
            
            ParcelasManager._resetar_estado_pdf()
            #st.rerun() # Descomente se quiser forçar a recarga imediata, mas o toast pode sumir rápido.

        except Exception as e:
            st.error(f"Erro fatal na importação: {e}")

    @staticmethod
    def _tab_previsao():
        """Aba com previsão de gastos - Dashboard completo."""
        st.subheader("📅 Dashboard de Previsão de Gastos")

        # Carrega contas e categorias (necessário para edição)
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")

        df_p = db.buscar("""
            SELECT t.id, t.data_vencimento, t.descricao, t.valor, c.nome as banco, cat.nome as categoria
            FROM transacoes t
            LEFT JOIN contas c ON t.conta_id = c.id
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            WHERE t.tipo_fluxo='CARTAO'
            ORDER BY t.data_vencimento ASC
        """)

        if df_p.empty:
            st.info("ℹ️ Nenhuma parcela lançada no cartão ainda.")
            return

        df_p['data_vencimento'] = pd.to_datetime(df_p['data_vencimento'])
        df_p['valor_abs'] = df_p['valor'].abs()

        # 1. MÉTRICAS DE TOPO
        total_divida = df_p['valor_abs'].sum()

        df_p['Mes_Ano'] = df_p['data_vencimento'].dt.to_period('M')
        agrupado_mes = df_p.groupby('Mes_Ano')['valor_abs'].sum().reset_index()
        agrupado_mes['Mes_Ano_Str'] = agrupado_mes['Mes_Ano'].astype(str)
        agrupado_mes = agrupado_mes.sort_values('Mes_Ano')

        if not agrupado_mes.empty:
            mes_mais_pesado = agrupado_mes.loc[agrupado_mes['valor_abs'].idxmax()]
        else:
            mes_mais_pesado = None

        c_met1, c_met2 = st.columns(2)
        c_met1.markdown(f"""
            <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; border-left:5px solid #e74c3c;">
                <small>Total Parcelado a Pagar (Geral)</small><br><strong style="font-size: 22px; color: #c0392b;">{moeda(total_divida)}</strong>
            </div>
        """, unsafe_allow_html=True)

        if mes_mais_pesado is not None:
            c_met2.markdown(f"""
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; border-left:5px solid #f39c12;">
                    <small>Mês mais pesado ({mes_mais_pesado['Mes_Ano_Str']})</small><br><strong style="font-size: 22px; color: #d35400;">{moeda(mes_mais_pesado['valor_abs'])}</strong>
                </div>
            """, unsafe_allow_html=True)
        else:
            c_met2.info("Sem dados por mês para calcular o mês mais pesado.")

        st.write("")

        # 2. GRÁFICO DE EVOLUÇÃO (Plotly: barras mensais + linha cumulativa)
        st.markdown("**📈 Evolução do Parcelamento nos Próximos Meses**")
        agrupado_mes['cumulativo'] = agrupado_mes['valor_abs'].cumsum()
        fig = go.Figure()
        fig.add_bar(x=agrupado_mes['Mes_Ano_Str'], y=agrupado_mes['valor_abs'], name='Mensal', marker_color='#e74c3c')
        fig.add_trace(go.Scatter(x=agrupado_mes['Mes_Ano_Str'], y=agrupado_mes['cumulativo'], mode='lines+markers', name='Cumulativo', line=dict(color='#1f77b4')))
        fig.update_layout(yaxis_title='Valor (R$)', xaxis_title='Mês/Ano', legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
        fig.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig, width='stretch')

        st.markdown("---")

        # 3. DISTRIBUIÇÃO POR CARTÃO / CATEGORIA
        st.markdown("**🧭 Distribuição por Cartão / Categoria (Próximos Meses)**")
        distrib_cartao = df_p.groupby('banco')['valor_abs'].sum().reset_index().sort_values('valor_abs', ascending=False)
        distrib_categoria = df_p.groupby('categoria')['valor_abs'].sum().reset_index().sort_values('valor_abs', ascending=False)

        d1, d2 = st.columns(2)
        with d1:
            if not distrib_cartao.empty:
                fig1 = px.pie(distrib_cartao, values='valor_abs', names='banco', title='Por Cartão', hole=0.4)
                st.plotly_chart(fig1, width='stretch')
            else:
                st.info("Sem dados por cartão.")
        with d2:
            if not distrib_categoria.empty:
                fig2 = px.pie(distrib_categoria, values='valor_abs', names='categoria', title='Por Categoria', hole=0.4)
                st.plotly_chart(fig2, width='stretch')
            else:
                st.info("Sem dados por categoria.")

        st.markdown("---")

        # 4. EXPORTAÇÃO / RELATÓRIO
        st.markdown("**📥 Exportar Relatório**")
        csv_rel = df_p[['id','data_vencimento','descricao','valor_abs','banco','categoria']].copy()
        csv_rel = csv_rel.rename(columns={
            'id': 'ID',
            'data_vencimento': 'Data Vencimento',
            'descricao': 'Descrição',
            'valor_abs': 'Valor (R$)',
            'banco': 'Cartão',
            'categoria': 'Categoria'
        })
        csv_bytes = csv_rel.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar CSV de Previsão", data=csv_bytes, file_name="previsao_parcelas.csv", mime="text/csv")

        st.markdown("---")

        # 5. LISTAGEM CASCATA COM EDIÇÃO/EXCLUSÃO
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
                total_mes = f_mes['valor_abs'].sum()

                with st.expander(f"📅 {mes_atual.strftime('%m/%Y')} — Total do Mês: {moeda(total_mes)}"):
                    cartoes_no_mes = f_mes['banco'].fillna("Desconhecido").unique()

                    for cartao in cartoes_no_mes:
                        f_cartao = f_mes[f_mes['banco'].fillna("Desconhecido") == cartao]
                        subtotal_cartao = f_cartao['valor_abs'].sum()
                        st.markdown(f"**💳 Fatura: {cartao}** — Subtotal: <span style='color:#c0392b;'>{moeda(subtotal_cartao)}</span>", unsafe_allow_html=True)

                        for _, r in f_cartao.iterrows():
                            # Colunas ajustadas para caber botões de editar/excluir
                            c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2.5, 0.8, 0.8])
                            clean_desc_row = re.sub(r'^\[.*?\]\s*', '', r['descricao'])
                            c1.write(pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y'))
                            c2.markdown(f"**{clean_desc_row}**<br><span style='color:gray; font-size:12px;'>{r.get('categoria','')}</span>", unsafe_allow_html=True)
                            c3.markdown(f"<div style='text-align: right; color:{'#27ae60' if r['valor']>0 else '#c0392b'}; font-weight:bold;'>{moeda(abs(r['valor']))}</div>", unsafe_allow_html=True)

                            # Edit toggle (most compatible UX): abre um formulário inline abaixo da linha
                            with c4:
                                if st.button("✏️", key=f"edit_toggle_{r['id']}"):
                                    key_ed = f"editing_{r['id']}"
                                    st.session_state[key_ed] = not st.session_state.get(key_ed, False)

                            # Delete small button alinhado à direita
                            with c5:
                                if st.button("🗑️", key=f"del_parc_{r['id']}"):
                                    st.session_state['del_id'] = int(r['id'])

                            # Se o usuário solicitou edição dessa linha, mostramos um formulário inline
                            if st.session_state.get(f"editing_{r['id']}"):
                                with st.form(f"form_edit_{r['id']}"):
                                    d_desc = st.text_input("Descrição", value=clean_desc_row, key=f"edit_desc_{r['id']}")
                                    d_val = st.number_input("Valor (R$)", min_value=0.0, value=float(abs(r['valor'])), key=f"edit_val_{r['id']}")
                                    d_date = st.date_input("Data de Vencimento", value=pd.to_datetime(r['data_vencimento']).date(), key=f"edit_date_{r['id']}")
                                    conta_op = df_contas['nome'].tolist() if not df_contas.empty else []
                                    cat_op = df_cats['nome'].tolist() if not df_cats.empty else []
                                    default_conta_idx = 0
                                    try:
                                        default_conta_idx = conta_op.index(cartao) if cartao in conta_op else 0
                                    except Exception:
                                        default_conta_idx = 0
                                    sel_conta = st.selectbox("Cartão", conta_op, index=default_conta_idx, key=f"edit_cnt_{r['id']}")
                                    default_cat_idx = 0
                                    try:
                                        default_cat_idx = cat_op.index(r.get('categoria', '')) if r.get('categoria', '') in cat_op else 0
                                    except Exception:
                                        default_cat_idx = 0
                                    sel_cat = st.selectbox("Categoria", cat_op, index=default_cat_idx, key=f"edit_cat_{r['id']}")

                                    save_clicked = st.form_submit_button("Salvar alterações", key=f"save_{r['id']}")
                                    cancel_clicked = st.form_submit_button("Voltar", key=f"cancel_{r['id']}")

                                    if cancel_clicked:
                                        st.session_state[f"editing_{r['id']}"] = False
                                        exp = getattr(st, "experimental_rerun", None)
                                        if callable(exp):
                                            try:
                                                exp()
                                            except Exception:
                                                ParcelasManager._safe_rerun()
                                        else:
                                            ParcelasManager._safe_rerun()

                                    if save_clicked:
                                        try:
                                            cid = int(df_contas[df_contas.nome == sel_conta].id.values[0])
                                            ctid = int(df_cats[df_cats.nome == sel_cat].id.values[0])
                                            db.executar("""
                                                UPDATE transacoes SET descricao=?, valor=?, data_vencimento=?, conta_id=?, categoria_id=? WHERE id=?
                                            """, (f"[{sel_conta}] {d_desc}", -abs(float(d_val)), d_date, cid, ctid, int(r['id'])))
                                            st.success("Parcela atualizada com sucesso.")
                                        except Exception as e:
                                            st.error(f"Erro ao atualizar parcela: {e}")
                                        # Fecha o formulário e tenta forçar rerun
                                        st.session_state[f"editing_{r['id']}"] = False
                                        exp = getattr(st, "experimental_rerun", None)
                                        if callable(exp):
                                            try:
                                                exp()
                                            except Exception:
                                                ParcelasManager._safe_rerun()
                                        else:
                                            ParcelasManager._safe_rerun()

        # Modal de confirmação para exclusão (fallback-friendly)
        if st.session_state.get('del_id'):
            del_id = st.session_state.get('del_id')
            modal_fn = getattr(st, "modal", None)
            if callable(modal_fn):
                modal_cm = cast(Any, modal_fn)("Confirmação de Exclusão")
                with modal_cm:
                    st.warning("Tem certeza que deseja excluir esta parcela? Esta ação é irreversível.")
                    col_ok, col_cancel = st.columns(2)
                    if col_ok.button("Sim, excluir"):
                        db.executar("DELETE FROM transacoes WHERE id=?", (del_id,))
                        st.success("Parcela excluída.")
                        st.session_state['del_id'] = None
                        ParcelasManager._safe_rerun()
                    if col_cancel.button("Cancelar"):
                        st.session_state['del_id'] = None
                        ParcelasManager._safe_rerun()
            else:
                with st.container():
                    st.markdown("### Confirmação de Exclusão")
                    st.warning("Tem certeza que deseja excluir esta parcela? Esta ação é irreversível.")
                    col_ok, col_cancel = st.columns(2)
                    if col_ok.button("Sim, excluir"):
                        db.executar("DELETE FROM transacoes WHERE id=?", (del_id,))
                        st.success("Parcela excluída.")
                        st.session_state['del_id'] = None
                        ParcelasManager._safe_rerun()
                    if col_cancel.button("Cancelar"):
                        st.session_state['del_id'] = None
                        ParcelasManager._safe_rerun()

        # (Edição agora é feita inline por formulário dentro da listagem por parcela)