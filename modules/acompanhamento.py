# ==========================================
# MÓDULO: ACOMPANHAMENTO DIÁRIO (Barras Horizontais)
# ==========================================

import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
from config import MESES_LISTA
from utils import moeda


class AcompanhamentoManager:
    """Renderiza o painel de acompanhamento diário com barras horizontais por categoria."""

    @staticmethod
    def renderizar():
        """Página de acompanhamento: Orçado vs Realizado por categoria."""
        st.header("📊 Acompanhamento Diário")
        st.caption("Visualize o progresso dos seus gastos por categoria com barras intuitivas.")

        # Filtros
        mes_nome = st.segmented_control(
            "Mês:", MESES_LISTA,
            default=MESES_LISTA[datetime.now().month - 1]
        )
        if mes_nome is None:
            mes_nome = MESES_LISTA[datetime.now().month - 1]

        col_ano, _ = st.columns([1, 5])
        ano_sel = col_ano.number_input("Ano:", min_value=2025, max_value=2030, value=2026,
                                        key="acomp_ano")

        mes_num = MESES_LISTA.index(mes_nome) + 1
        data_inicio = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = (
            datetime(ano_sel, mes_num, 1) +
            relativedelta(months=1) - relativedelta(days=1)
        ).strftime('%Y-%m-%d')

        user_id = db.get_user_id()

        # Carrega categorias ativas com percentual de meta
        df_cats = db.buscar(
            "SELECT * FROM categorias WHERE user_id = %s AND ativa = TRUE ORDER BY nome",
            (user_id,)
        )

        if df_cats.empty:
            st.info("ℹ️ Nenhuma categoria cadastrada. Acesse Cadastros para configurar.")
            return

        # Carrega entradas do mês para calcular orçado em R$
        entradas = db.buscar(f"""
            SELECT COALESCE(SUM(valor), 0) as total
            FROM transacoes
            WHERE user_id = {user_id}
            AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL)
            AND valor > 0
            AND data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
        """)
        renda_mes = float(entradas.iloc[0]['total']) if not entradas.empty else 0

        # Carrega gastos por categoria
        df_gastos = db.buscar(f"""
            SELECT t.categoria_id, cat.nome as categoria, cat.icone,
                   cat.percentual_meta,
                   ABS(SUM(t.valor)) as gasto_real
            FROM transacoes t
            JOIN categorias cat ON t.categoria_id = cat.id
            WHERE t.user_id = {user_id}
            AND t.valor < 0
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            GROUP BY t.categoria_id, cat.nome, cat.icone, cat.percentual_meta
            ORDER BY cat.nome
        """)

        # Carrega gastos por subcategoria (para detalhe)
        df_gastos_sub = db.buscar(f"""
            SELECT t.categoria_id, s.nome as subcategoria,
                   ABS(SUM(t.valor)) as gasto_sub
            FROM transacoes t
            JOIN subcategorias s ON t.subcategoria_id = s.id
            WHERE t.user_id = {user_id}
            AND t.valor < 0
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            GROUP BY t.categoria_id, s.nome
            ORDER BY gasto_sub DESC
        """)

        # Dia do mês e total de dias (para marcador de ritmo)
        hoje = datetime.now()
        if hoje.month == mes_num and hoje.year == ano_sel:
            dia_atual = hoje.day
        else:
            dia_atual = None  # Mês diferente do atual, sem marcador

        ultimo_dia = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).day

        # Resumo geral
        total_orcado = renda_mes
        total_gasto = float(df_gastos['gasto_real'].sum()) if not df_gastos.empty else 0
        pct_geral = (total_gasto / total_orcado * 100) if total_orcado > 0 else 0

        AcompanhamentoManager._renderizar_resumo(total_orcado, total_gasto, pct_geral)

        st.markdown("---")

        # ── Cards de Categorias ──
        for _, cat in df_cats.iterrows():
            cat_id = int(cat['id'])
            nome = cat['nome']
            icone = cat.get('icone', '📁') or '📁'
            pct_meta = float(cat.get('percentual_meta', 0) or 0)
            orcado = renda_mes * (pct_meta / 100) if renda_mes > 0 else 0

            # Gasto real desta categoria
            gasto_real = 0
            if not df_gastos.empty:
                match = df_gastos[df_gastos['categoria_id'] == cat_id]
                if not match.empty:
                    gasto_real = float(match.iloc[0]['gasto_real'])

            # Subcategorias desta categoria
            subs_desta = pd.DataFrame()
            if not df_gastos_sub.empty:
                subs_desta = df_gastos_sub[df_gastos_sub['categoria_id'] == cat_id]

            AcompanhamentoManager._renderizar_card_categoria(
                nome, icone, orcado, gasto_real, pct_meta,
                dia_atual, ultimo_dia, subs_desta
            )

    @staticmethod
    def _renderizar_resumo(total_orcado, total_gasto, pct_geral):
        """Resumo geral do mês."""
        restante = total_orcado - total_gasto
        cor_rest = "#2ecc71" if restante >= 0 else "#e74c3c"

        st.markdown(f"""
            <div style="display:flex; gap:10px; margin:10px 0 15px 0; flex-wrap:wrap;">
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1;
                            border-left:5px solid #3498db; min-width:150px;">
                    <small style="color:#666;">Renda do Mês</small><br>
                    <strong style="font-size:20px; color:#3498db;">{moeda(total_orcado)}</strong>
                </div>
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1;
                            border-left:5px solid #e74c3c; min-width:150px;">
                    <small style="color:#666;">Total Gasto</small><br>
                    <strong style="font-size:20px; color:#e74c3c;">{moeda(total_gasto)}</strong>
                </div>
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1;
                            border-left:5px solid {cor_rest}; min-width:150px;">
                    <small style="color:#666;">Restante</small><br>
                    <strong style="font-size:20px; color:{cor_rest};">{moeda(restante)}</strong>
                </div>
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1;
                            border-left:5px solid #9b59b6; min-width:150px;">
                    <small style="color:#666;">Consumido</small><br>
                    <strong style="font-size:20px; color:#9b59b6;">{pct_geral:.0f}%</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def _renderizar_card_categoria(nome, icone, orcado, gasto_real, pct_meta,
                                    dia_atual, ultimo_dia, subs_df):
        """Renderiza um card de categoria com barra horizontal + marcador de ritmo."""
        if orcado > 0:
            pct_gasto = (gasto_real / orcado) * 100
        else:
            pct_gasto = 100 if gasto_real > 0 else 0

        # Cores dinâmicas (verde → amarelo → vermelho)
        if pct_gasto <= 60:
            barra_cor = "#2ecc71"
            status_txt = "Saudável"
        elif pct_gasto <= 85:
            barra_cor = "#f39c12"
            status_txt = "Atenção"
        else:
            barra_cor = "#e74c3c"
            status_txt = "Crítico"

        barra_width = min(pct_gasto, 100)
        restante_cat = max(orcado - gasto_real, 0)

        # Marcador de ritmo (linha vertical no dia atual)
        marcador_html = ""
        if dia_atual and ultimo_dia > 0:
            pct_dia = (dia_atual / ultimo_dia) * 100
            marcador_html = (
                f"<div style='position:absolute; left:{pct_dia}%; top:0; width:2px; "
                f"height:100%; background:#333; opacity:0.5;'></div>"
                f"<div style='position:absolute; left:{pct_dia}%; top:-14px; "
                f"font-size:9px; color:#666; transform:translateX(-50%);'>Dia {dia_atual}</div>"
            )

        # Subcategorias breakdown
        subs_html = ""
        if not subs_df.empty:
            subs_items = []
            for _, s in subs_df.iterrows():
                subs_items.append(f"<span style='color:#666;'>{s['subcategoria']}: "
                                  f"<strong>{moeda(s['gasto_sub'])}</strong></span>")
            subs_html = (
                f"<div style='font-size:11px; margin-top:6px; color:#888;'>"
                f"{'  •  '.join(subs_items)}</div>"
            )

        st.markdown(f"""
            <div style="background:#f8f9fa; border-radius:10px; padding:14px 18px; margin-bottom:10px;
                        border-left:5px solid {barra_cor};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div>
                        <span style="font-size:18px;">{icone}</span>
                        <strong style="font-size:15px; margin-left:6px;">{nome}</strong>
                        <span style="font-size:11px; color:#999; margin-left:8px;">(Meta: {pct_meta:.0f}%)</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:13px; color:{barra_cor}; font-weight:bold;">{status_txt}</span>
                    </div>
                </div>
                <div style="position:relative; background:#e0e0e0; border-radius:6px; height:22px; margin:4px 0;">
                    <div style="background:{barra_cor}; width:{barra_width}%; height:22px; border-radius:6px;
                                text-align:center; color:white; font-size:11px; line-height:22px;
                                min-width:30px;">
                        {pct_gasto:.0f}%
                    </div>
                    {marcador_html}
                </div>
                <div style="display:flex; justify-content:space-between; font-size:12px; color:#666; margin-top:4px;">
                    <span>Gasto: <strong>{moeda(gasto_real)}</strong></span>
                    <span>Orçado: <strong>{moeda(orcado)}</strong></span>
                    <span>Restante: <strong style="color:{barra_cor};">{moeda(restante_cat)}</strong></span>
                </div>
                {subs_html}
            </div>
        """, unsafe_allow_html=True)
