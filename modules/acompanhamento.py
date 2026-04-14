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

        # 1. Filtros
        hoje = datetime.now()
        mes_nome = st.segmented_control("Mês:", MESES_LISTA, default=MESES_LISTA[hoje.month - 1])
        if mes_nome is None: mes_nome = MESES_LISTA[hoje.month - 1]

        col_ano, _ = st.columns([1, 5])
        ano_sel = col_ano.number_input("Ano:", min_value=2024, max_value=2030, value=hoje.year, key="acomp_ano")

        mes_num = MESES_LISTA.index(mes_nome) + 1
        data_ini = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).strftime('%Y-%m-%d')

        user_id = db.get_user_id()

        # 2. Busca de Dados (Queries parametrizadas)
        df_cats = db.buscar("SELECT * FROM categorias WHERE user_id = %s AND ativa = TRUE ORDER BY nome", (user_id,))
        if df_cats.empty:
            st.info("Nenhuma categoria cadastrada.")
            return

        renda_row = db.buscar("SELECT COALESCE(SUM(valor), 0) as total FROM transacoes WHERE user_id = %s AND valor > 0 AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL) AND data_vencimento BETWEEN %s AND %s", (user_id, data_ini, data_fim))
        renda_mes = float(renda_row.iloc[0]['total']) if not renda_row.empty else 0

        # Gastos Caixa
        df_gastos = db.buscar("SELECT t.categoria_id, ABS(SUM(t.valor)) as gasto_real FROM transacoes t WHERE t.user_id = %s AND t.valor < 0 AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL) AND t.data_vencimento BETWEEN %s AND %s GROUP BY t.categoria_id", (user_id, data_ini, data_fim))
        
        # Gastos Cartão
        df_gastos_cartao = db.buscar_gastos_cartao_por_categoria(user_id, data_ini, data_fim)
        
        # Consolidação de Gastos
        gastos_map = {}
        if not df_gastos.empty:
            for _, r in df_gastos.iterrows(): gastos_map[int(r['categoria_id'])] = float(r['gasto_real'])
        
        if not df_gastos_cartao.empty:
            for _, r in df_gastos_cartao.iterrows():
                cid = int(r['categoria_id'])
                gastos_map[cid] = gastos_map.get(cid, 0) + float(r['gasto_real'])

        # Subcategorias
        df_sub = db.buscar("SELECT t.categoria_id, s.nome as subcategoria, ABS(SUM(t.valor)) as gasto_sub FROM transacoes t JOIN subcategorias s ON t.subcategoria_id = s.id WHERE t.user_id = %s AND t.valor < 0 AND t.data_vencimento BETWEEN %s AND %s GROUP BY t.categoria_id, s.nome", (user_id, data_ini, data_fim))

        # 3. Resumo Geral
        total_gasto = sum(gastos_map.values())
        pct_geral = (total_gasto / renda_mes * 100) if renda_mes > 0 else 0
        AcompanhamentoManager._renderizar_resumo(renda_mes, total_gasto, pct_geral)

        # 4. Marcador de Ritmo
        dia_atual = hoje.day if (hoje.month == mes_num and hoje.year == ano_sel) else None
        ultimo_dia = (datetime(ano_sel, mes_num, 1) + relativedelta(months=1) - relativedelta(days=1)).day

        # 5. Renderização dos Cards
        st.markdown("---")
        for _, cat in df_cats.iterrows():
            cid = int(cat['id'])
            gasto_cat = gastos_map.get(cid, 0)
            pct_meta = float(cat.get('percentual_meta', 0) or 0)
            orcado = renda_mes * (pct_meta / 100) if renda_mes > 0 else 0
            
            subs_desta = df_sub[df_sub['categoria_id'] == cid] if not df_sub.empty else pd.DataFrame()
            
            AcompanhamentoManager._renderizar_card_categoria(
                cat['nome'], cat.get('icone', ''), orcado, gasto_cat, pct_meta, dia_atual, ultimo_dia, subs_desta
            )

    @staticmethod
    def _renderizar_resumo(renda, gasto, pct):
        rest = renda - gasto
        c_rest = "#2ecc71" if rest >= 0 else "#e74c3c"
        c_pct = "#2ecc71" if pct <= 70 else ("#f39c12" if pct <= 90 else "#e74c3c")
        
        html = f"""
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px;">
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid #3498db; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Renda</small><br><strong style="font-size:18px; color:#3498db;">{moeda(renda)}</strong>
            </div>
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid #e74c3c; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Gasto</small><br><strong style="font-size:18px; color:#e74c3c;">{moeda(gasto)}</strong>
            </div>
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid {c_rest}; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Restante</small><br><strong style="font-size:18px; color:{c_rest};">{moeda(rest)}</strong>
            </div>
            <div style="background:var(--secondary-background-color); padding:12px; border-radius:10px; flex:1; border-left:5px solid {c_pct}; min-width:120px;">
                <small style="color:var(--text-color); opacity:0.7;">Uso</small><br><strong style="font-size:18px; color:{c_pct};">{pct:.0f}%</strong>
            </div>
        </div>"""
        st.markdown(html.replace('\n', ' '), unsafe_allow_html=True)

    @staticmethod
    def _renderizar_card_categoria(nome, icone, orcado, gasto, meta, dia_atual, ultimo_dia, subs_df):
        pct = (gasto / orcado * 100) if orcado > 0 else (100 if gasto > 0 else 0)
        
        if pct <= 60: cor, status = "#2ecc71", "Saudável"
        elif pct <= 85: cor, status = "#f39c12", "Atenção"
        else: cor, status = "#e74c3c", "Crítico"

        # Marcador de Ritmo
        marcador = ""
        if dia_atual and ultimo_dia > 0:
            p_dia = (dia_atual / ultimo_dia) * 100
            marcador = f"<div style='position:absolute; left:{p_dia}%; top:0; width:2px; height:100%; background:var(--text-color); opacity:0.3; z-index:1;'></div>"

        # Subcategorias
        subs_h = ""
        if not subs_df.empty:
            items = [f"{s['subcategoria']}: {moeda(s['gasto_sub'])}" for _, s in subs_df.iterrows()]
            subs_h = f"<div style='font-size:11px; margin-top:8px; opacity:0.7; border-top:1px solid rgba(128,128,128,0.2); padding-top:5px;'>{' • '.join(items)}</div>"

        # HTML em LINHA ÚNICA para evitar quebra do parser do Streamlit
        card_html = f"""
        <div style="background:var(--secondary-background-color); border-radius:10px; padding:15px; margin-bottom:10px; border-left:5px solid {cor};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div><span style="font-size:18px;">{icone or ''}</span> <strong style="color:var(--text-color);">{nome}</strong> <small style="opacity:0.6;">({meta:.0f}%)</small></div>
                <div style="color:{cor}; font-weight:bold; font-size:12px;">{status}</div>
            </div>
            <div style="position:relative; background:rgba(128,128,128,0.15); border-radius:5px; height:20px; margin-bottom:8px;">
                <div style="background:{cor}; width:{min(pct, 100)}%; height:100%; border-radius:5px; text-align:center; color:white; font-size:11px; line-height:20px; font-weight:bold; position:relative; z-index:2;">{pct:.0f}%</div>
                {marcador}
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-color);">
                <span>Gasto: <b>{moeda(gasto)}</b></span>
                <span>Alvo: <b>{moeda(orcado)}</b></span>
                <span style="color:{cor if orcado >= gasto else '#e74c3c'};">Sobrou: <b>{moeda(max(orcado-gasto, 0))}</b></span>
            </div>
            {subs_h}
        </div>"""
        
        # O SEGREDO: .replace('\n', ' ') remove todas as quebras de linha
        st.markdown(card_html.replace('\n', ' '), unsafe_allow_html=True)