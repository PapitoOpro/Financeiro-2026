# ==========================================
# MÓDULO: RELATÓRIOS ANALÍTICOS
# ==========================================

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
from config import MESES_LISTA
from utils import moeda
from modules.consultor import ConsultorManager, ConsultorEngine
from modules.acompanhamento import AcompanhamentoManager
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class RelatoriosManager:
    """Renderiza relatórios analíticos dinâmicos com filtros, prévia e exportação."""

    # ─── Colunas disponíveis para seleção ─────────────────────
    COLUNAS_DISPONIVEIS = {
        "Data": "data_vencimento",
        "Descrição": "descricao",
        "Valor": "valor",
        "Categoria": "categoria",
        "Cartão / Banco": "banco",
    }

    # ─── Renderização principal ───────────────────────────────
    @staticmethod
    def renderizar():
        st.header("Relatórios")

        tab_analiticos, tab_acompanhamento = st.tabs([
            "Relatórios Analíticos",
            "Acompanhamento",
        ])

        with tab_analiticos:
            RelatoriosManager._renderizar_analiticos()

        with tab_acompanhamento:
            AcompanhamentoManager.renderizar_conteudo()

    # ─── Relatórios Analíticos ────────────────────────────────
    @staticmethod
    def _renderizar_analiticos():

        # ── 1. Filtros ──────────────────────────────────────
        st.subheader("Filtros")

        # Período
        col_d1, col_d2 = st.columns(2)
        hoje = datetime.now().date()
        primeiro_dia_mes = hoje.replace(day=1)
        d_ini = col_d1.date_input("Data Início", value=primeiro_dia_mes)
        d_fim = col_d2.date_input("Data Fim", value=hoje)

        if d_ini > d_fim:
            st.error("A data de início não pode ser maior que a data de fim.")
            return

        # Colunas a exibir
        todas_colunas = list(RelatoriosManager.COLUNAS_DISPONIVEIS.keys())
        colunas_selecionadas = st.multiselect(
            "Colunas do relatório",
            todas_colunas,
            default=todas_colunas,
            help="Escolha quais colunas deseja no relatório.",
        )

        if not colunas_selecionadas:
            st.warning("Selecione ao menos uma coluna.")
            return

        # ── 2. Buscar dados ─────────────────────────────────
        user_id = db.get_user_id()

        q_caixa = f"""
            SELECT t.data_vencimento, t.descricao, t.valor,
                   cat.nome AS categoria, c.nome AS banco
            FROM transacoes t
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.user_id = {user_id}
              AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
              AND t.fatura_id IS NULL
              AND t.data_vencimento BETWEEN '{d_ini}' AND '{d_fim}'
        """
        df = db.buscar(q_caixa)

        q_cartao = f"""
            SELECT f.data_vencimento, i.descricao, -ABS(i.valor) AS valor,
                   cat.nome AS categoria, c.nome AS banco
            FROM itens_fatura i
            JOIN faturas f ON i.fatura_id = f.id
            LEFT JOIN categorias cat ON i.categoria_id = cat.id
            LEFT JOIN contas c ON f.conta_id = c.id
            WHERE i.user_id = {user_id}
              AND f.data_vencimento BETWEEN '{d_ini}' AND '{d_fim}'
        """
        df_cartao = db.buscar(q_cartao)
        if not df_cartao.empty and not df_cartao.isna().all(axis=None):
            df = pd.concat([df, df_cartao.dropna(how='all')], ignore_index=True)

        if df.empty:
            st.info("Nenhuma movimentação registrada neste período.")
            return

        # Converte coluna de data
        df["data_vencimento"] = pd.to_datetime(df["data_vencimento"])

        # ── 3. Filtros Adicionais (Categoria / Banco) ───────
        with st.expander("Filtros adicionais", expanded=False):
            fc1, fc2, fc3 = st.columns(3)

            # Categoria
            categorias_unicas = sorted(df["categoria"].dropna().unique().tolist())
            filtro_categorias = fc1.multiselect(
                "Categorias", categorias_unicas, default=categorias_unicas
            )

            # Banco / Cartão
            bancos_unicos = sorted(df["banco"].dropna().unique().tolist())
            filtro_bancos = fc2.multiselect(
                "Cartão / Banco", bancos_unicos, default=bancos_unicos
            )

            # Tipo (Entrada / Saída)
            tipo_opcoes = ["Todos", "Somente Entradas", "Somente Saídas"]
            filtro_tipo = fc3.radio("Tipo", tipo_opcoes, horizontal=True)

        # Aplica filtros
        mask = pd.Series(True, index=df.index)
        if filtro_categorias:
            mask &= df["categoria"].isin(filtro_categorias) | df["categoria"].isna()
        if filtro_bancos:
            mask &= df["banco"].isin(filtro_bancos) | df["banco"].isna()
        if filtro_tipo == "Somente Entradas":
            mask &= df["valor"] > 0
        elif filtro_tipo == "Somente Saídas":
            mask &= df["valor"] < 0

        df_filtrado = df[mask].copy()

        if df_filtrado.empty:
            st.warning("Nenhum registro encontrado com os filtros selecionados.")
            return

        # ── 4. Métricas ─────────────────────────────────────
        ent = df_filtrado[df_filtrado["valor"] > 0]["valor"].sum()
        sai = abs(df_filtrado[df_filtrado["valor"] < 0]["valor"].sum())
        bal = ent - sai

        st.markdown(f'''
            <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #2ecc71;">
                    <small>Entradas</small><br><strong style="font-size: 22px; color: #27ae60;">{moeda(ent)}</strong>
                </div>
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #e74c3c;">
                    <small>Saídas</small><br><strong style="font-size: 22px; color: #c0392b;">-{moeda(sai)}</strong>
                </div>
                <div style="background:{'#2ecc71' if bal >= 0 else '#e74c3c'}; color:#ffffff; padding:15px; border-radius:10px; flex:1;">
                    <small>Balanço</small><br><strong style="font-size: 22px;">{moeda(bal)}</strong>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # ── 5. Abas: Prévia / Curva ABC / Consultor ─────────
        # Correção: O código original tinha tabs desbalanceadas
        t_previa, t_abc, t_consultor = st.tabs([
            "Prévia do Relatório",
            "Curva ABC",
            "Consultor IA"
        ])

        # Formata para exibição apenas as colunas selecionadas
        col_map = RelatoriosManager.COLUNAS_DISPONIVEIS
        colunas_essenciais = ["valor", "data_vencimento", "descricao"]
        colunas_internas = list({col_map[c] for c in colunas_selecionadas} | set(colunas_essenciais))
        colunas_internas = [c for c in colunas_internas if c in df_filtrado.columns]

        df_export = df_filtrado[colunas_internas].copy()
        colunas_exibicao = [col_map[c] for c in colunas_selecionadas if col_map[c] in df_export.columns]
        df_exibir = df_export[colunas_exibicao].copy()

        rename = {v: k for k, v in col_map.items() if k in colunas_selecionadas}

        if "data_vencimento" in df_exibir.columns:
            df_exibir["data_vencimento"] = df_exibir["data_vencimento"].dt.strftime("%d/%m/%Y")
        if "valor" in df_exibir.columns:
            df_exibir["valor_num"] = df_exibir["valor"]  # guarda numérico para export
            df_exibir["valor"] = df_exibir["valor"].apply(moeda)

        df_exibir_renomeado = df_exibir.rename(columns=rename)

        with t_previa:
            st.subheader("Prévia do Relatório")
            st.caption(f"{len(df_exibir_renomeado)} registros  |  Período: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}")
            st.dataframe(df_exibir_renomeado.drop(columns=["valor_num"], errors="ignore"), hide_index=True, width='stretch')

            # ── 6. Exportação ───────────────────────────────
            st.divider()
            st.subheader("Exportar Relatório")
            ec1, ec2 = st.columns(2)

            # --- Excel ---
            df_export_xlsx = df_exibir.copy()
            if "valor_num" in df_export_xlsx.columns:
                df_export_xlsx["valor"] = df_export_xlsx["valor_num"]
                df_export_xlsx.drop(columns=["valor_num"], inplace=True)
            df_export_xlsx = df_export_xlsx.rename(columns=rename)

            buf_xlsx = io.BytesIO()
            df_export_xlsx.to_excel(buf_xlsx, index=False, engine="openpyxl")
            ec1.download_button(
                "Baixar Excel",
                data=buf_xlsx.getvalue(),
                file_name=f"relatorio_{d_ini}_{d_fim}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
                icon=":material/download:",
            )

            # --- PDF ---
            # Passamos o df_export_xlsx porque ele é o que o usuário quer ver no PDF, 
            # mas nossa função interna agora sabe encontrar a coluna de valores com segurança
            pdf_bytes = RelatoriosManager._gerar_pdf(
                df_export_xlsx, d_ini, d_fim, ent, sai, bal
            )
            ec2.download_button(
                "Baixar PDF",
                data=pdf_bytes,
                file_name=f"relatorio_{d_ini}_{d_fim}.pdf",
                mime="application/pdf",
                width='stretch',
                icon=":material/picture_as_pdf:",
            )

        with t_abc:
            RelatoriosManager._render_curva_abc(df_filtrado)

        with t_consultor:
            mes_consultor = d_ini.month
            ano_consultor = d_ini.year
            diag = ConsultorEngine.diagnostico_completo(ano_consultor, mes_consultor)
            ConsultorManager._renderizar_status_geral(diag)
            ConsultorManager._renderizar_alertas(diag['alertas'])
            st.markdown("---")
            ConsultorManager._renderizar_diagnostico(diag)

    # ─── Curva ABC ────────────────────────────────────────────
    @staticmethod
    def _render_curva_abc(df):
        st.markdown("**Curva ABC: Descubra quais despesas consomem mais do seu orçamento.**")

        df_saidas = df[df["valor"] < 0].copy()
        if df_saidas.empty:
            st.warning("Nenhuma saída (despesa) registrada neste período para gerar a Curva ABC.")
            return

        # 1. Preparação dos Dados 
        # Tratamento para evitar os 'não identificados' no gráfico
        df_saidas["descricao"] = df_saidas["descricao"].fillna("Sem descrição")
        
        df_saidas["Valor Absoluto"] = df_saidas["valor"].abs()
        df_abc = df_saidas.sort_values(by="Valor Absoluto", ascending=False).reset_index(drop=True)
        df_abc["% Acumulada Num"] = (df_abc["Valor Absoluto"].cumsum() / df_abc["Valor Absoluto"].sum()) * 100

        def classificar_abc(pct):
            if pct <= 80: return "Classe A"
            if pct <= 95: return "Classe B"
            return "Classe C"

        df_abc["Classe"] = df_abc["% Acumulada Num"].apply(classificar_abc)

        # 2. Métricas Rápidas (Cards)
        resumo = df_abc.groupby('Classe').agg(
            Total=('Valor Absoluto', 'sum'),
            Qtd=('Valor Absoluto', 'count')
        ).reset_index()

        st.markdown("### Resumo Estratégico")
        c1, c2, c3 = st.columns(3)
        cores = {"Classe A": "#e74c3c", "Classe B": "#f39c12", "Classe C": "#2ecc71"}

        for _, row in resumo.iterrows():
            classe = row['Classe']
            texto_card = f"""
            <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid {cores.get(classe, '#ccc')};">
                <p style="margin:0; font-size:14px; color:#555;">{classe}</p>
                <h3 style="margin:0; color:#333;">{moeda(row['Total'])}</h3>
                <small style="color:#777;">{row['Qtd']} itens</small>
            </div>
            """
            if classe == "Classe A": c1.markdown(texto_card, unsafe_allow_html=True)
            elif classe == "Classe B": c2.markdown(texto_card, unsafe_allow_html=True)
            elif classe == "Classe C": c3.markdown(texto_card, unsafe_allow_html=True)

        st.write("") 

        # 3. Gráfico de Pareto 
        st.markdown("### Gráfico de Distribuição")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Bar(
                x=df_abc["descricao"].str[:20], 
                y=df_abc["Valor Absoluto"],
                name="Valor da Despesa",
                marker_color=[cores[c] for c in df_abc["Classe"]]
            ),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(
                x=df_abc["descricao"].str[:20], 
                y=df_abc["% Acumulada Num"],
                name="% Acumulada",
                mode="lines+markers",
                line=dict(color="#2c3e50", width=2)
            ),
            secondary_y=True,
        )

        fig.update_layout(
            height=400, 
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)"
        )
        fig.update_yaxes(title_text="Valor (R$)", secondary_y=False)
        fig.update_yaxes(title_text="% Acumulada", range=[0, 105], secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)

        # 4. Tabela de Detalhes
        with st.expander("Ver Tabela Detalhada"):
            df_table = df_abc.copy()
            df_table["data_vencimento"] = pd.to_datetime(df_table["data_vencimento"]).dt.strftime("%d/%m/%Y")
            df_table["Valor Absoluto"] = df_table["Valor Absoluto"].apply(moeda)
            df_table["% Acumulada"] = df_table["% Acumulada Num"].apply(lambda x: f"{x:.2f}%")
            
            cols_abc = ["Classe", "data_vencimento", "descricao", "Valor Absoluto", "% Acumulada"]
            rename_abc = {"data_vencimento": "Data", "descricao": "Descrição"}
            st.dataframe(df_table[cols_abc].rename(columns=rename_abc), hide_index=True, use_container_width=True)

        st.info("🎯 **DICA DE OURO:** Gaste 80% do seu tempo renegociando ou cortando os itens da **Classe A** (Vermelho). Eles são os que realmente movem o ponteiro financeiro.")

    # ─── Gerar PDF ────────────────────────────────────────────
    @staticmethod
    def _gerar_pdf(df, d_ini, d_fim, ent, sai, bal):
        """Gera PDF do relatório usando fpdf2."""
        from fpdf import FPDF

        pdf = FPDF(orientation="L", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Título
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Relatorio Financeiro", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Periodo: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.ln(4)

        # Resumo Financeiro
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(90, 8, f"Entradas: {moeda(ent)}")
        pdf.cell(90, 8, f"Saidas: -{moeda(sai)}")
        pdf.cell(0, 8, f"Balanco: {moeda(bal)}", ln=True)
        
        # --- NOVO: Cálculo Rápido da Classe A Blindado ---
        # 1. Identifica a coluna de valores baseada no que o usuário escolheu exportar
        col_valor = None
        for col_name in ["valor", "Valor", "Valor (R$)", "valor_num", "valor_total"]:
            if col_name in df.columns:
                col_valor = col_name
                break
                
        if col_valor is not None:
            df_temp = df.copy()
            # Se a coluna estiver como texto (ex: R$ 1.500,00), higieniza antes da matemática
            if df_temp[col_valor].dtype == object:
                df_temp[col_valor] = df_temp[col_valor].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                df_temp[col_valor] = pd.to_numeric(df_temp[col_valor], errors='coerce')
            
            df_saidas = df_temp[df_temp[col_valor] < 0].copy()
            if not df_saidas.empty:
                df_saidas["Valor Absoluto"] = df_saidas[col_valor].abs()
                df_abc = df_saidas.sort_values(by="Valor Absoluto", ascending=False).reset_index(drop=True)
                df_abc["% Acumulada Num"] = (df_abc["Valor Absoluto"].cumsum() / df_abc["Valor Absoluto"].sum()) * 100
                
                classe_a = df_abc[df_abc["% Acumulada Num"] <= 80]
                
                if not classe_a.empty:
                    total_a = classe_a["Valor Absoluto"].sum()
                    qtd_a = len(classe_a)
                    
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(200, 0, 0)
                    pdf.cell(0, 6, f"  * Atencao (Curva ABC): {qtd_a} despesas da Classe A representam o maior impacto do mes ({moeda(total_a)}).", ln=True)
                    pdf.set_text_color(0, 0, 0)
        # ---------------------------------------------------
        
        pdf.ln(4)

        # Tabela
        colunas = list(df.columns)
        n_cols = len(colunas)
        page_w = pdf.w - 20  # margens
        col_w = page_w / n_cols if n_cols else page_w

        # Cabeçalho
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        for col in colunas:
            pdf.cell(col_w, 7, str(col)[:25], border=1, fill=True, align="C")
        pdf.ln()

        # Dados
        pdf.set_font("Helvetica", "", 8)
        for _, row in df.iterrows():
            for col in colunas:
                val = str(row[col]) if pd.notna(row[col]) else ""
                pdf.cell(col_w, 6, val[:30], border=1, align="C")
            pdf.ln()

        return bytes(pdf.output())