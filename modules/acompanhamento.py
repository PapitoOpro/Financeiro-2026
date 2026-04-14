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
import textwrap # Adicionado para limpar identação

class AcompanhamentoManager:
    """Renderiza o painel de acompanhamento diário com barras horizontais por categoria."""

    @staticmethod
    def renderizar():
        """Página de acompanhamento standalone (mantida por compatibilidade)."""
        st.header("Acompanhamento Inteligente")
        AcompanhamentoManager.renderizar_conteudo()

    @staticmethod
    def renderizar_conteudo():
        """Conteúdo do acompanhamento (sem header, para uso dentro de tabs)."""
        st.caption("Visualize o progresso dos seus gastos por categoria com barras intuitivas.")

        # Filtros
        mes_nome = st.segmented_control(
            "Mês:", MESES_LISTA,
            default=MESES_LISTA[datetime.now().month - 1]
        )
        if mes_nome is None:
            mes_nome = MESES_LISTA[datetime.now().month - 1]

        col_ano, _ = st.columns([1, 5])
        # Ajustado para valor padrão dinâmico do ano atual
        ano_atual = datetime.now().year
        ano_sel = col_ano.number_input("Ano:", min_value=2024, max_value=2030, value=ano_atual,
                                        key="acomp_ano")

        mes_num = MESES_LISTA.index(mes_nome) + 1
        data_inicio = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = (
            datetime(ano_sel, mes_num, 1) +
            relativedelta(months=1) - relativedelta(days=1)
        ).strftime('%Y-%m-%d')

        user_id = db.get_user_id()

        # Carrega categorias ativas
        df_cats = db.buscar(
            "SELECT * FROM categorias WHERE user_id = %s AND ativa = TRUE ORDER BY nome",
            (user_id,)
        )

        if df_cats.empty:
            st.info("ℹ Nenhuma categoria cadastrada. Acesse Cadastros para configurar.")
            return

        # Carrega entradas do mês
        entradas = db.buscar(f"""
            SELECT COALESCE(SUM(valor), 0) as total
            FROM transacoes
            WHERE user_id = %s
            AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL)
            AND valor > 0
            AND data_vencimento BETWEEN %s AND %s
        """, (user_id, data_inicio, data_fim))
        renda_mes = float(entradas.iloc[0]['total']) if not entradas.empty else 0

        # Carrega gastos por categoria (CAIXA)
        df_gastos = db.buscar(f"""
            SELECT t.categoria_id, cat.nome as categoria, cat.icone,
                   cat.percentual_meta,
                   ABS(SUM(t.valor)) as gasto_real
            FROM transacoes t
            JOIN categorias cat ON t.categoria_id = cat.id
            WHERE t.user_id = %s
            AND t.valor < 0
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN %s AND %s
            GROUP BY t.categoria_id, cat.nome, cat.icone, cat.percentual_meta
        """, (user_id, data_inicio, data_fim))

        # Inclui gastos de cartão
        df_gastos_cartao = db.buscar_gastos_cartao_por_categoria(user_id, data_inicio, data_fim)
        if not df_gastos_cartao.empty:
            if df_gastos.empty:
                df_gastos = df_gastos_cartao
            else:
                df_combined = pd.concat([df_gastos, df_gastos_cartao], ignore_index=True)
                df_gastos = df_combined.groupby(['categoria_id', 'categoria', 'icone', 'percentual_meta'], as_index=False).agg({'gasto_real': 'sum'})

        # Carrega gastos por subcategoria
        df_gastos_sub = db.buscar(f"""
            SELECT t.categoria_id, s.nome as subcategoria,
                   ABS(SUM(t.valor)) as gasto_sub
            FROM transacoes t
            JOIN subcategorias s ON t.subcategoria_id = s.id
            WHERE t.user_id = %s
            AND t.valor < 0
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN %s AND %s
            GROUP BY t.categoria_id, s.nome
        """, (user_id, data_inicio, data_fim))

        # Dia do mês para marcador de ritmo
        hoje = datetime.now()
        dia_atual = hoje.day if (hoje.month == mes_num and hoje.year == ano_sel) else None
        ultimo_dia = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).day

        # Resumo geral
        total_orcado = renda_mes
        total_gasto = float(df_gastos['gasto_real'].sum()) if not df_gastos.empty else 0
        pct_geral = (total_gasto / total_orcado * 100) if total_orcado > 0 else 0

        AcompanhamentoManager._renderizar_resumo(total_orcado, total_gasto, pct_geral)
        st.markdown("---")

        # Renderização dos Cards
        for _, cat in df_cats.iterrows():
            cat_id = int(cat['id'])
            pct_meta = float(cat.get('percentual_meta', 0) or 0)
            orcado = renda_mes * (pct_meta / 100) if renda_mes > 0 else 0

            gasto_real = 0
            if not df_gastos.empty:
                match = df_gastos[df_gastos['categoria_id'] == cat_id]
                if not match.empty:
                    gasto_real = float(match.iloc[0]['gasto_real'])

            subs_desta = df_gastos_sub[df_gastos_sub['categoria_id'] == cat_id] if not df_gastos_sub.empty else pd.DataFrame()

            AcompanhamentoManager._renderizar_card_categoria(
                cat['nome'], cat.get('icone', ''), orcado, gasto_real, pct_meta,
                dia_atual, ultimo_dia, subs_desta
            )

    @staticmethod
    def _renderizar_resumo(total_orcado, total_gasto, pct_geral):
        restante = total_orcado - total_gasto
        cor_rest = "#2ecc71" if restante >= 0 else "#e74c3c"
        cor_pct = "#2ecc71" if pct_geral <= 70 else ("#f39c12" if pct_geral <= 90 else "#e74c3c")

        # HTML sem identação lateral para evitar bug do Markdown
        html = f"""
<div style="display:flex; gap:10px; margin:10px 0 15px 0; flex-wrap:wrap;">
    <div style="background: var(--secondary-background-color); padding:15px; border-radius:10px; flex:1; border-left:5px solid #3498db; min-width:150px;">
        <small style="color: var(--text-color); opacity: 0.8;">Renda do Mês</small><br>
        <strong style="font-size:20px; color:#3498db;">{moeda(total_orcado)}</strong>
    </div>
    <div style="background: var(--secondary-background-color); padding:15px; border-radius:10px; flex:1; border-left:5px solid #e74c3c; min-width:150px;">
        <small style="color: var(--text-color); opacity: 0.8;">Total Gasto</small><br>
        <strong style="font-size:20px; color:#e74c3c;">{moeda(total_gasto)}</strong>
    </div>
    <div style="background: var(--secondary-background-color); padding:15px; border-radius:10px; flex:1; border-left:5px solid {cor_rest}; min-width:150px;">
        <small style="color: var(--text-color); opacity: 0.8;">Restante</small><br>
        <strong style="font-size:20px; color:{cor_rest};">{moeda(restante)}</strong>
    </div>
    <div style="background: var(--secondary-background-color); padding:15px; border-radius:10px; flex:1; border-left:5px solid {cor_pct}; min-width:150px;">
        <small style="color: var(--text-color); opacity: 0.8;">Consumido</small><br>
        <strong style="font-size:20px; color:{cor_pct};">{pct_geral:.0f}%</strong>
    </div>
</div>"""
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def _renderizar_card_categoria(nome, icone, orcado, gasto_real, pct_meta, dia_atual, ultimo_dia, subs_df):
        if orcado > 0:
            pct_gasto = (gasto_real / orcado) * 100
        else:
            pct_gasto = 100 if gasto_real > 0 else 0

        if pct_gasto <= 60: barra_cor, status_txt = "#2ecc71", "Saudável"
        elif pct_gasto <= 85: barra_cor, status_txt = "#f39c12", "Atenção"
        else: barra_cor, status_txt = "#e74c3c", "Crítico"

        barra_width = min(pct_gasto, 100)
        restante_cat = max(orcado - gasto_real, 0)

        marcador_html = ""
        if dia_atual and ultimo_dia > 0:
            pct_dia = (dia_atual / ultimo_dia) * 100
            marcador_html = f"""
<div style='position:absolute; left:{pct_dia}%; top:0; width:2px; height:100%; background:var(--text-color); opacity:0.4; z-index:1;'></div>
<div style='position:absolute; left:{pct_dia}%; top:-16px; font-size:10px; color:var(--text-color); opacity:0.8; transform:translateX(-50%);'>Dia {dia_atual}</div>"""

        subs_html = ""
        if not subs_df.empty:
            subs_items = [f"<span style='color:var(--text-color); opacity:0.8;'>{s['subcategoria']}: <strong>{moeda(s['gasto_sub'])}</strong></span>" for _, s in subs_df.iterrows()]
            subs_html = f"<div style='font-size:12px; margin-top:10px; border-top: 1px solid rgba(128,128,128,0.2); padding-top: 8px;'>{' &nbsp;•&nbsp; '.join(subs_items)}</div>"

        # HTML Colado à esquerda (sem espaços no início das linhas) para evitar erro de renderização
        card_html = f"""
<div style="background: var(--secondary-background-color); border-radius:10px; padding:16px 20px; margin-bottom:12px; border-left:5px solid {barra_cor}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <div>
            <span style="font-size:20px;">{icone or ''}</span>
            <strong style="font-size:16px; margin-left:6px; color:var(--text-color);">{nome}</strong>
            <span style="font-size:12px; color:var(--text-color); opacity:0.6; margin-left:8px;">(Meta: {pct_meta:.0f}%)</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:14px; color:{barra_cor}; font-weight:bold;">{status_txt}</span>
        </div>
    </div>
    <div style="position:relative; background:rgba(128,128,128,0.2); border-radius:6px; height:24px; margin:8px 0 12px 0;">
        <div style="background:{barra_cor}; width:{barra_width}%; height:24px; border-radius:6px; text-align:center; color:white; font-size:12px; font-weight:bold; line-height:24px; min-width:35px; position:relative; z-index:2;">
            {pct_gasto:.0f}%
        </div>
        {marcador_html}
    </div>
    <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-color); opacity:0.9;">
        <span>Gasto: <strong>{moeda(gasto_real)}</strong></span>
        <span>Orçado: <strong>{moeda(orcado)}</strong></span>
        <span>Restante: <strong style="color:{barra_cor if restante_cat > 0 else '#e74c3c'};">{moeda(restante_cat)}</strong></span>
    </div>
    {subs_html}
</div>"""
        st.markdown(card_html, unsafe_allow_html=True)