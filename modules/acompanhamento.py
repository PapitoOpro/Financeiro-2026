# ==========================================
# MÓDULO: ACOMPANHAMENTO DIÁRIO
# ==========================================

import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
from config import MESES_LISTA
from utils import moeda

class AcompanhamentoManager:
    """Renderiza o painel de acompanhamento com barras horizontais."""

    @staticmethod
    def renderizar_conteudo():
        """Conteúdo do acompanhamento."""
        st.caption("Visualize o progresso dos seus gastos por categoria.")

        # 1. Filtros de Período
        hoje = datetime.now()
        mes_nome = st.segmented_control("Mês:", MESES_LISTA, default=MESES_LISTA[hoje.month - 1])
        if mes_nome is None: mes_nome = MESES_LISTA[hoje.month - 1]

        col_ano, _ = st.columns([1, 4])
        ano_sel = col_ano.number_input("Ano:", min_value=2024, max_value=2030, value=hoje.year, key="acomp_ano")

        mes_num = MESES_LISTA.index(mes_nome) + 1
        data_ini = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).strftime('%Y-%m-%d')

        user_id = db.get_user_id()

        # 2. Busca Categorias Ativas
        df_cats = db.buscar("SELECT id, nome, icone, percentual_meta FROM categorias WHERE user_id = ? AND ativa = TRUE ORDER BY nome", (user_id,))
        if df_cats.empty:
            st.info("Nenhuma categoria cadastrada ou ativa.")
            return

        # 3. Busca Renda (Entradas)
        renda_row = db.buscar("""
            SELECT COALESCE(SUM(valor), 0) as total 
            FROM transacoes 
            WHERE user_id = ? AND valor > 0 
            AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL) 
            AND data_vencimento BETWEEN ? AND ?
        """, (user_id, data_ini, data_fim))
        renda_mes = float(renda_row.iloc[0]['total']) if not renda_row.empty else 0

        # 4. Busca Gastos Caixa (Blindado contra nulos)
        df_gastos = db.buscar("""
            SELECT categoria_id, COALESCE(ABS(SUM(valor)), 0) as gasto_real 
            FROM transacoes 
            WHERE user_id = ? AND valor < 0 
            AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL) 
            AND categoria_id IS NOT NULL
            AND data_vencimento BETWEEN ? AND ? 
            GROUP BY categoria_id
        """, (user_id, data_ini, data_fim))
        
        # 5. Busca Gastos Cartão
        df_gastos_cartao = db.buscar_gastos_cartao_por_categoria(user_id, data_ini, data_fim)
        
        # 6. Consolidação dos Gastos
        gastos_map = {}

        # Processa gastos de Caixa
        if not df_gastos.empty:
            for _, r in df_gastos.iterrows():
                if pd.notna(r['categoria_id']):
                    cid = int(r['categoria_id'])
                    gastos_map[cid] = float(r['gasto_real'] or 0)
        
        # Soma gastos de Cartão
        if not df_gastos_cartao.empty:
            for _, r in df_gastos_cartao.iterrows():
                if pd.notna(r['categoria_id']):
                    cid = int(r['categoria_id'])
                    gastos_map[cid] = gastos_map.get(cid, 0) + float(r['gasto_real'] or 0)

        # 7. Busca Subcategorias
        df_sub = db.buscar("""
            SELECT t.categoria_id, s.nome as subcategoria, COALESCE(ABS(SUM(t.valor)), 0) as gasto_sub 
            FROM transacoes t 
            JOIN subcategorias s ON t.subcategoria_id = s.id 
            WHERE t.user_id = ? AND t.valor < 0 AND t.data_vencimento BETWEEN ? AND ? 
            GROUP BY t.categoria_id, s.nome
        """, (user_id, data_ini, data_fim))

        # 8. Renderização do Resumo Geral
        total_gasto = sum(gastos_map.values())
        pct_geral = (total_gasto / renda_mes * 100) if renda_mes > 0 else 0
        AcompanhamentoManager._render_resumo_html(renda_mes, total_gasto, pct_geral)

        # 9. Marcador de Ritmo
        dia_atual = hoje.day if (hoje.month == mes_num and hoje.year == ano_sel) else None
        ultimo_dia = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).day

        # 10. Loop de Cards de Categorias
        st.markdown("---")
        for _, cat in df_cats.iterrows():
            cid = int(cat['id'])
            gasto_cat = gastos_map.get(cid, 0)
            p_meta = float(cat.get('percentual_meta', 0) or 0)
            orcado = renda_mes * (p_meta / 100) if renda_mes > 0 else 0
            
            subs_desta = df_sub[df_sub['categoria_id'] == cid] if not df_sub.empty else pd.DataFrame()
            
            AcompanhamentoManager._render_card_html(
                cat['nome'], cat.get('icone', ''), orcado, gasto_cat, p_meta, dia_atual, ultimo_dia, subs_desta
            )

    @staticmethod
    def _render_resumo_html(renda, gasto, pct):
        rest = renda - gasto
        c_rest = "#2ecc71" if rest >= 0 else "#e74c3c"
        c_pct = "#2ecc71" if pct <= 75 else ("#f39c12" if pct <= 90 else "#e74c3c")
        
        html = f"""
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px;">
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid #3498db; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Renda</small><br><strong style="font-size:18px; color:#3498db;">{moeda(renda)}</strong>
            </div>
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid #e74c3c; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Gasto Total</small><br><strong style="font-size:18px; color:#e74c3c;">{moeda(gasto)}</strong>
            </div>
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid {c_rest}; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Disponível</small><br><strong style="font-size:18px; color:{c_rest};">{moeda(rest)}</strong>
            </div>
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid {c_pct}; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">% Uso</small><br><strong style="font-size:18px; color:{c_pct};">{pct:.0f}%</strong>
            </div>
        </div>"""
        st.markdown(html.replace('\n', ' '), unsafe_allow_html=True)

    @staticmethod
    def _render_card_html(nome, icone, orcado, gasto, meta, dia_atual, ultimo_dia, subs_df):
        pct = (gasto / orcado * 100) if orcado > 0 else (100 if gasto > 0 else 0)
        cor = "#2ecc71" if pct <= 65 else ("#f39c12" if pct <= 85 else "#e74c3c")
        status = "Saudável" if pct <= 65 else ("Atenção" if pct <= 85 else "Crítico")

        marcador = ""
        if dia_atual and ultimo_dia > 0:
            p_dia = (dia_atual / ultimo_dia) * 100
            marcador = f"<div style='position:absolute; left:{p_dia}%; top:0; width:2px; height:100%; background:var(--text-color); opacity:0.3; z-index:1;'></div>"

        subs_h = ""
        if not subs_df.empty:
            items = [f"{s['subcategoria']}: {moeda(s['gasto_sub'])}" for _, s in subs_df.iterrows()]
            subs_h = f"<div style='font-size:11px; margin-top:8px; opacity:0.7; border-top:1px solid rgba(128,128,128,0.2); padding-top:5px;'>{' • '.join(items)}</div>"

        # HTML ATUALIZADO COM white-space:nowrap E min-width AJUSTADO
        card_html = f"""
        <div style="background:var(--secondary-background-color); border-radius:10px; padding:15px; margin-bottom:10px; border-left:5px solid {cor};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div><span style="font-size:18px;">{icone or ''}</span> <strong style="color:var(--text-color);">{nome}</strong> <small style="opacity:0.6;">({meta:.0f}%)</small></div>
                <div style="color:{cor}; font-weight:bold; font-size:12px;">{status}</div>
            </div>
            <div style="position:relative; background:rgba(128,128,128,0.15); border-radius:5px; height:20px; margin-bottom:8px;">
                <div style="background:{cor}; width:{min(pct, 100)}%; height:100%; border-radius:5px; text-align:center; color:white; font-size:11px; line-height:20px; font-weight:bold; position:relative; z-index:2; min-width:30px; white-space:nowrap; padding: 0 5px;">
                    {pct:.0f}%
                </div>
                {marcador}
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-color);">
                <span>Gasto: <b>{moeda(gasto)}</b></span>
                <span>Alvo: <b>{moeda(orcado)}</b></span>
                <span style="color:{cor if orcado >= gasto else '#e74c3c'};">Sobrou: <b>{moeda(max(orcado-gasto, 0))}</b></span>
            </div>
            {subs_h}
        </div>"""
        st.markdown(card_html.replace('\n', ' '), unsafe_allow_html=True)