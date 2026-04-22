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

        col_d1, col_d2 = st.columns(2)
        hoje = datetime.now().date()
        primeiro_dia_mes = hoje.replace(day=1)
        d_ini = col_d1.date_input("Data Início", value=primeiro_dia_mes)
        d_fim = col_d2.date_input("Data Fim", value=hoje)

        if d_ini > d_fim:
            st.error("A data de início não pode ser maior que a data de fim.")
            return

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

        # ── 2. Buscar dados — queries parametrizadas (sem SQL Injection) ─
        user_id = db.get_user_id()

        q_caixa = """
            SELECT t.data_vencimento, t.descricao, t.valor,
                   cat.nome AS categoria, c.nome AS banco
            FROM transacoes t
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.user_id = %s
              AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
              AND t.fatura_id IS NULL
              AND t.data_vencimento BETWEEN %s AND %s
        """
        df = db.buscar(q_caixa, (user_id, d_ini, d_fim))

        q_cartao = """
            SELECT f.data_vencimento, i.descricao, -ABS(i.valor) AS valor,
                   cat.nome AS categoria, c.nome AS banco
            FROM itens_fatura i
            JOIN faturas f ON i.fatura_id = f.id
            LEFT JOIN categorias cat ON i.categoria_id = cat.id
            LEFT JOIN contas c ON f.conta_id = c.id
            WHERE i.user_id = %s
              AND f.data_vencimento BETWEEN %s AND %s
        """
        df_cartao = db.buscar(q_cartao, (user_id, d_ini, d_fim))
        if not df_cartao.empty and not df_cartao.isna().all(axis=None):
            df = pd.concat([df, df_cartao.dropna(how='all')], ignore_index=True)

        if df.empty:
            st.info("Nenhuma movimentação registrada neste período.")
            return

        df["data_vencimento"] = pd.to_datetime(df["data_vencimento"])

        # ── 3. Filtros Adicionais ────────────────────────────
        with st.expander("Filtros adicionais", expanded=False):
            fc1, fc2, fc3 = st.columns(3)

            categorias_unicas = sorted(df["categoria"].dropna().unique().tolist())
            # CORRIGIDO: "Sem categoria" como opção explícita, sem incluir NaN silenciosamente
            opcoes_categorias = categorias_unicas + (["Sem categoria"] if df["categoria"].isna().any() else [])
            filtro_categorias = fc1.multiselect("Categorias", opcoes_categorias, default=opcoes_categorias)

            bancos_unicos = sorted(df["banco"].dropna().unique().tolist())
            filtro_bancos = fc2.multiselect("Cartão / Banco", bancos_unicos, default=bancos_unicos)

            tipo_opcoes = ["Todos", "Somente Entradas", "Somente Saídas"]
            filtro_tipo = fc3.radio("Tipo", tipo_opcoes, horizontal=True)

        # CORRIGIDO: NaN só incluso se "Sem categoria" estiver selecionado
        mask = pd.Series(True, index=df.index)
        if filtro_categorias:
            incluir_sem_cat = "Sem categoria" in filtro_categorias
            cats_reais = [c for c in filtro_categorias if c != "Sem categoria"]
            if incluir_sem_cat:
                mask &= df["categoria"].isin(cats_reais) | df["categoria"].isna()
            else:
                mask &= df["categoria"].isin(cats_reais)
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

        # ── 4. Métricas com comparativo do período anterior ──
        ent = df_filtrado[df_filtrado["valor"] > 0]["valor"].sum()
        sai = abs(df_filtrado[df_filtrado["valor"] < 0]["valor"].sum())
        bal = ent - sai

        # Busca período equivalente anterior para comparativo
        delta_dias = (d_fim - d_ini).days + 1
        d_ini_ant = d_ini - relativedelta(days=delta_dias)
        d_fim_ant = d_ini - relativedelta(days=1)

        df_ant = db.buscar(q_caixa, (user_id, d_ini_ant, d_fim_ant))
        df_ant_cartao = db.buscar(q_cartao, (user_id, d_ini_ant, d_fim_ant))
        if not df_ant_cartao.empty and not df_ant_cartao.isna().all(axis=None):
            df_ant = pd.concat([df_ant, df_ant_cartao.dropna(how='all')], ignore_index=True)

        def _delta_html(atual, anterior, inverter=False):
            if anterior == 0 or df_ant.empty:
                return ""
            pct = ((atual - anterior) / anterior) * 100
            positivo_bom = not inverter
            if pct > 0:
                cor = "#27ae60" if positivo_bom else "#c0392b"
                seta = "▲"
            elif pct < 0:
                cor = "#c0392b" if positivo_bom else "#27ae60"
                seta = "▼"
            else:
                return ""
            return f'<small style="color:{cor}; font-size:12px;"> {seta} {abs(pct):.1f}%</small>'

        ent_ant = df_ant[df_ant["valor"] > 0]["valor"].sum() if not df_ant.empty else 0
        sai_ant = abs(df_ant[df_ant["valor"] < 0]["valor"].sum()) if not df_ant.empty else 0
        bal_ant = ent_ant - sai_ant

        # HTML EM LINHA ÚNICA E SEM IDENTAÇÃO PARA EVITAR BUG DE RENDERIZAÇÃO
        html_metrics = f"""
<div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
    <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #2ecc71; min-width:150px;">
        <small>Entradas</small><br>
        <strong style="font-size: 20px; color: #27ae60;">{moeda(ent)}</strong>
        {_delta_html(ent, ent_ant, inverter=False)}
    </div>
    <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid #e74c3c; min-width:150px;">
        <small>Saídas</small><br>
        <strong style="font-size: 20px; color: #c0392b;">-{moeda(sai)}</strong>
        {_delta_html(sai, sai_ant, inverter=True)}
    </div>
    <div style="background:{'#2ecc71' if bal >= 0 else '#e74c3c'}; color:#ffffff; padding:15px; border-radius:10px; flex:1; min-width:150px;">
        <small>Balanço</small><br>
        <strong style="font-size: 20px;">{moeda(bal)}</strong>
        {_delta_html(bal, bal_ant, inverter=False)}
    </div>
</div>"""
        
        # O replace('\n', ' ') é vital aqui também
        st.markdown(html_metrics.replace('\n', ' '), unsafe_allow_html=True)

        # ── 5. Abas (nova aba Evolução adicionada) ───────────
        t_previa, t_abc, t_evolucao, t_consultor = st.tabs([
            "Prévia do Relatório",
            "Curva ABC",
            "Evolução",
            "Consultor IA",
        ])

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
            df_exibir["valor_num"] = df_exibir["valor"]
            df_exibir["valor"] = df_exibir["valor"].apply(moeda)

        df_exibir_renomeado = df_exibir.rename(columns=rename)

        # ── Tab Prévia ──────────────────────────────────────
        with t_previa:
            st.subheader("Prévia do Relatório")
            st.caption(f"{len(df_exibir_renomeado)} registros  |  Período: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}")
            st.dataframe(df_exibir_renomeado.drop(columns=["valor_num"], errors="ignore"), hide_index=True, use_container_width=True)

            st.divider()
            st.subheader("Exportar Relatório")
            ec1, ec2 = st.columns(2)

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
                use_container_width=True,
                icon=":material/download:",
            )

            # CORRIGIDO: passa df_filtrado com valores numéricos originais
            pdf_bytes = RelatoriosManager._gerar_pdf(df_filtrado, d_ini, d_fim, ent, sai, bal)
            ec2.download_button(
                "Baixar PDF",
                data=pdf_bytes,
                file_name=f"relatorio_{d_ini}_{d_fim}.pdf",
                mime="application/pdf",
                use_container_width=True,
                icon=":material/picture_as_pdf:",
            )

        # ── Tab Curva ABC ────────────────────────────────────
        with t_abc:
            RelatoriosManager._render_curva_abc(df_filtrado)

        # ── Tab Evolução Temporal ────────────────────────────
        with t_evolucao:
            RelatoriosManager._render_evolucao(df_filtrado, d_ini, d_fim)

        # ── Tab Consultor ────────────────────────────────────
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

        df_saidas["descricao"] = df_saidas["descricao"].fillna("Sem descrição")
        df_saidas["categoria"] = df_saidas["categoria"].fillna("Sem categoria") if "categoria" in df_saidas.columns else "Sem categoria"
        df_saidas["Valor Absoluto"] = df_saidas["valor"].abs()

        # NOVO: toggle para agrupar por descrição ou categoria
        agrupar_por = st.radio(
            "Agrupar por",
            ["Descrição", "Categoria"],
            horizontal=True,
            key="abc_agrupamento",
            help="Descrição mostra cada item individualmente; Categoria agrupa por tipo de gasto.",
        )
        col_grupo = "descricao" if agrupar_por == "Descrição" else "categoria"

        # CORRIGIDO: agrupa antes de plotar para eliminar barras duplicadas
        df_agrupado = (
            df_saidas.groupby(col_grupo, as_index=False)["Valor Absoluto"]
            .sum()
            .sort_values("Valor Absoluto", ascending=False)
            .reset_index(drop=True)
        )

        df_agrupado["% Acumulada Num"] = (
            df_agrupado["Valor Absoluto"].cumsum() / df_agrupado["Valor Absoluto"].sum()
        ) * 100

        def classificar_abc(pct):
            if pct <= 80: return "Classe A"
            if pct <= 95: return "Classe B"
            return "Classe C"

        df_agrupado["Classe"] = df_agrupado["% Acumulada Num"].apply(classificar_abc)

        resumo = df_agrupado.groupby("Classe").agg(
            Total=("Valor Absoluto", "sum"),
            Qtd=("Valor Absoluto", "count")
        ).reset_index()

        st.markdown("### Resumo Estratégico")
        c1, c2, c3 = st.columns(3)
        cores = {"Classe A": "#e74c3c", "Classe B": "#f39c12", "Classe C": "#2ecc71"}

        for _, row in resumo.iterrows():
            classe = row["Classe"]
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

        # CORRIGIDO: legenda ativa, eixo X rotacionado, linhas de referência A/B
        st.markdown("### Gráfico de Distribuição")
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(
                x=df_agrupado[col_grupo].str[:25],
                y=df_agrupado["Valor Absoluto"],
                name="Valor da Despesa",
                marker_color=[cores[c] for c in df_agrupado["Classe"]],
                hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=df_agrupado[col_grupo].str[:25],
                y=df_agrupado["% Acumulada Num"],
                name="% Acumulada",
                mode="lines+markers",
                line=dict(color="#2c3e50", width=2),
                hovertemplate="%{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.add_hline(y=80, line_dash="dot", line_color="#e74c3c",
                      annotation_text="80% — A", annotation_position="right",
                      secondary_y=True)
        fig.add_hline(y=95, line_dash="dot", line_color="#f39c12",
                      annotation_text="95% — B", annotation_position="right",
                      secondary_y=True)

        fig.update_layout(
            height=420,
            margin=dict(l=0, r=60, t=30, b=80),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_xaxes(tickangle=-40, tickfont=dict(size=11))
        fig.update_yaxes(title_text="Valor (R$)", secondary_y=False)
        fig.update_yaxes(title_text="% Acumulada", range=[0, 105], secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver Tabela Detalhada"):
            df_table = df_agrupado.copy()
            df_table["Valor"] = df_table["Valor Absoluto"].apply(moeda)
            df_table["% Acumulada"] = df_table["% Acumulada Num"].apply(lambda x: f"{x:.1f}%")
            cols_show = ["Classe", col_grupo, "Valor", "% Acumulada"]
            rename_show = {"descricao": "Descrição", "categoria": "Categoria"}
            st.dataframe(
                df_table[cols_show].rename(columns=rename_show),
                hide_index=True,
                use_container_width=True,
            )

        st.info("🎯 **DICA DE OURO:** Gaste 80% do seu tempo renegociando ou cortando os itens da **Classe A** (Vermelho). Eles são os que realmente movem o ponteiro financeiro.")

    # ─── Evolução Temporal ────────────────────────────────────
    # ─── Evolução Temporal ────────────────────────────────────
    @staticmethod
    def _render_evolucao(df, d_ini, d_fim):
        """Gráfico de linha com evolução de entradas e saídas ao longo do período."""
        st.markdown("**Evolução de entradas e saídas no período selecionado.**")

        if df.empty:
            st.info("Sem dados para exibir.")
            return

        # Granularidade automática pelo tamanho do período
        delta_dias = (d_fim - d_ini).days
        if delta_dias <= 35:
            freq, label_freq = "D", "dia"
        elif delta_dias <= 180:
            freq, label_freq = "W", "semana"
        else:
            freq, label_freq = "ME", "mês"

        df_ev = df.copy()
        df_ev["data_vencimento"] = pd.to_datetime(df_ev["data_vencimento"])
        
        # Criamos colunas separadas para facilitar o agrupamento único
        df_ev["ent_val"] = df_ev["valor"].apply(lambda x: x if x > 0 else 0)
        df_ev["sai_val"] = df_ev["valor"].apply(lambda x: abs(x) if x < 0 else 0)
        
        df_ev = df_ev.set_index("data_vencimento")

        # Agrupamos as duas colunas ao mesmo tempo para garantir o mesmo tamanho/índice
        df_resampled = df_ev[["ent_val", "sai_val"]].resample(freq).sum().fillna(0)

        if df_resampled.empty:
            st.info("Sem movimentações para exibir no gráfico.")
            return

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_resampled.index,
            y=df_resampled["ent_val"],
            name="Entradas",
            mode="lines+markers",
            line=dict(color="#27ae60", width=2),
            fill="tozeroy",
            fillcolor="rgba(39,174,96,0.08)",
            hovertemplate="R$ %{y:,.2f}<extra>Entradas</extra>",
        ))

        fig.add_trace(go.Scatter(
            x=df_resampled.index,
            y=df_resampled["sai_val"],
            name="Saídas",
            mode="lines+markers",
            line=dict(color="#e74c3c", width=2),
            fill="tozeroy",
            fillcolor="rgba(231,76,60,0.08)",
            hovertemplate="R$ %{y:,.2f}<extra>Saídas</extra>",
        ))

        fig.update_layout(
            height=380,
            margin=dict(l=0, r=0, t=30, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            yaxis=dict(title="Valor (R$)", tickprefix="R$ "),
        )
        fig.update_xaxes(tickangle=-30)

        st.caption(f"Agrupado por {label_freq} — período de {delta_dias} dias")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver tabela de evolução"):
            # Agora garantimos que todas as colunas venham do mesmo DataFrame resampled
            df_resumo_ev = pd.DataFrame({
                "Período": df_resampled.index.strftime("%d/%m/%Y"),
                "Entradas": df_resampled["ent_val"].values,
                "Saídas": df_resampled["sai_val"].values,
                "Balanço": (df_resampled["ent_val"] - df_resampled["sai_val"]).values,
            })
            
            # Formatação para exibição
            df_resumo_ev["Entradas"] = df_resumo_ev["Entradas"].apply(moeda)
            df_resumo_ev["Saídas"] = df_resumo_ev["Saídas"].apply(moeda)
            df_resumo_ev["Balanço"] = df_resumo_ev["Balanço"].apply(moeda)
            st.dataframe(df_resumo_ev, hide_index=True, use_container_width=True)

    # ─── Gerar PDF ────────────────────────────────────────────
    @staticmethod
    def _gerar_pdf(df, d_ini, d_fim, ent, sai, bal):
        """Gera PDF do relatório usando fpdf2.

        Recebe df_filtrado com 'valor' numérico — sem adivinhar nome de coluna.
        """
        from fpdf import FPDF

        pdf = FPDF(orientation="L", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Relatorio Financeiro", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Periodo: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.ln(4)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(90, 8, f"Entradas: {moeda(ent)}")
        pdf.cell(90, 8, f"Saidas: -{moeda(sai)}")
        pdf.cell(0, 8, f"Balanco: {moeda(bal)}", ln=True)

        # CORRIGIDO: ABC direto da coluna 'valor' numérica, agrupado por categoria
        df_saidas_pdf = df[df["valor"] < 0].copy()
        if not df_saidas_pdf.empty:
            df_saidas_pdf["_abs"] = df_saidas_pdf["valor"].abs()
            col_grupo_pdf = "categoria" if "categoria" in df_saidas_pdf.columns else "descricao"
            df_abc_pdf = (
                df_saidas_pdf.groupby(col_grupo_pdf, as_index=False)["_abs"]
                .sum()
                .sort_values("_abs", ascending=False)
                .reset_index(drop=True)
            )
            df_abc_pdf["pct_acum"] = (df_abc_pdf["_abs"].cumsum() / df_abc_pdf["_abs"].sum()) * 100
            classe_a = df_abc_pdf[df_abc_pdf["pct_acum"] <= 80]

            if not classe_a.empty:
                total_a = classe_a["_abs"].sum()
                qtd_a = len(classe_a)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(200, 0, 0)
                pdf.cell(0, 6, f"  * Atencao (Curva ABC): {qtd_a} categorias da Classe A representam o maior impacto ({moeda(total_a)}).", ln=True)
                pdf.set_text_color(0, 0, 0)

        pdf.ln(4)

        # Formata colunas para exibição no PDF
        df_pdf = df.copy()
        if "data_vencimento" in df_pdf.columns:
            df_pdf["data_vencimento"] = pd.to_datetime(df_pdf["data_vencimento"]).dt.strftime("%d/%m/%Y")
        if "valor" in df_pdf.columns:
            df_pdf["valor"] = df_pdf["valor"].apply(moeda)

        col_map = RelatoriosManager.COLUNAS_DISPONIVEIS
        rename_pdf = {v: k for k, v in col_map.items() if v in df_pdf.columns}
        df_pdf = df_pdf.rename(columns=rename_pdf)

        colunas = list(df_pdf.columns)
        n_cols = len(colunas)
        page_w = pdf.w - 20
        col_w = page_w / n_cols if n_cols else page_w

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        for col in colunas:
            pdf.cell(col_w, 7, str(col)[:25], border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for _, row in df_pdf.iterrows():
            for col in colunas:
                val = str(row[col]) if pd.notna(row[col]) else ""
                pdf.cell(col_w, 6, val[:30], border=1, align="C")
            pdf.ln()

        return bytes(pdf.output())
