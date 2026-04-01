# ==========================================
# MÓDULO: RELATÓRIOS ANALÍTICOS
# ==========================================

import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
from config import MESES_LISTA
from utils import moeda
from modules.consultor import ConsultorManager, ConsultorEngine


class RelatoriosManager:
    """Renderiza relatórios analíticos (Curva ABC, Extrato do Período, Métricas)."""

    @staticmethod
    def renderizar():
        st.header("📊 Relatórios Analíticos")

        c1, c2 = st.columns(2)
        hoje = datetime.now().date()
        primeiro_dia_mes = hoje.replace(day=1)
        d_ini = c1.date_input("Data Início", value=primeiro_dia_mes)
        d_fim = c2.date_input("Data Fim", value=hoje)

        if d_ini > d_fim:
            st.error("❌ A data de início não pode ser maior que a data de fim.")
            return

        # Query base — transações CAIXA
        user_id = db.get_user_id()
        q = f"""
            SELECT t.data_vencimento, t.descricao, t.valor, cat.nome AS categoria, c.nome AS banco
            FROM transacoes t
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.user_id = {user_id}
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN '{d_ini}' AND '{d_fim}'
        """

        df_an = db.buscar(q)

        # Inclui itens de fatura (gastos cartão) no relatório
        q_cartao = f"""
            SELECT f.data_vencimento, i.descricao, -ABS(i.valor) as valor,
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
            df_an = pd.concat([df_an, df_cartao.dropna(how='all', axis=1)], ignore_index=True)

        if df_an.empty:
            st.info("ℹ️ Nenhuma movimentação registrada neste período.")
            return

        # Map lowercase column -> original to lidar com alias/case diferentes
        cols_map = {c.lower(): c for c in df_an.columns}

        # Detecta coluna de data de forma resiliente
        date_col = None
        for candidate in ('data_vencimento', 'data', 'date', 'data_venc'):
            if candidate in cols_map:
                date_col = cols_map[candidate]
                break
        if date_col is None:
            date_col = next((c for c in df_an.columns if 'data' in c.lower() or 'date' in c.lower()), None)

        if date_col is None:
            # Tenta inferir por conversão
            for c in df_an.columns:
                try:
                    pd.to_datetime(df_an[c].dropna().iloc[:5])
                    date_col = c
                    break
                except Exception:
                    continue

        if date_col is None:
            st.warning('Não foi possível identificar a coluna de data. Mostrando dados brutos.')
            st.dataframe(df_an, width='stretch')
            return

        # Converte coluna de data
        df_an[date_col] = pd.to_datetime(df_an[date_col])

        # Detecta demais colunas
        desc_col = cols_map.get('descricao') or next((v for k, v in cols_map.items() if 'descr' in k), None)
        valor_col = cols_map.get('valor') or next((v for k, v in cols_map.items() if 'valor' in k), None)
        banco_col = cols_map.get('banco') or next((v for k, v in cols_map.items() if 'banco' in k or 'conta' in k or 'cartao' in k), None)
        categoria_col = cols_map.get('categoria') or next((v for k, v in cols_map.items() if 'categoria' in k), None)

        if valor_col is None:
            st.warning('Não foi possível identificar a coluna de valores. Mostrando dados brutos.')
            st.dataframe(df_an, width='stretch')
            return

        # Métricas
        ent = df_an[df_an[valor_col] > 0][valor_col].sum() if not df_an.empty else 0
        sai = abs(df_an[df_an[valor_col] < 0][valor_col].sum()) if not df_an.empty else 0
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

        # Abas
        t_extrato, t_abc, t_consultor = st.tabs([
            "[+] Extrato do Período",
            "[>] Curva ABC (Data e Valor)",
            "[🧠] Consultor Financeiro",
        ])

        with t_extrato:
            df_extrato = df_an.copy()
            df_extrato[date_col] = pd.to_datetime(df_extrato[date_col]).dt.strftime('%d/%m/%Y')
            df_extrato[f'{valor_col}_fmt'] = df_extrato[valor_col].apply(moeda)

            visible_cols = [date_col]
            if desc_col:
                visible_cols.append(desc_col)
            if banco_col:
                visible_cols.append(banco_col)
            if categoria_col:
                visible_cols.append(categoria_col)
            visible_cols.append(f'{valor_col}_fmt')

            # Renomeia colunas para exibição amigável
            rename_map = {
                date_col: 'Data',
                f'{valor_col}_fmt': 'Valor',
            }
            if desc_col:
                rename_map[desc_col] = 'Descrição'
            if banco_col:
                rename_map[banco_col] = 'Cartão / Banco'
            if categoria_col:
                rename_map[categoria_col] = 'Categoria'

            st.dataframe(df_extrato[visible_cols].rename(columns=rename_map), hide_index=True, width='stretch')

        with t_abc:
            st.markdown("**Curva ABC: Descubra quais despesas consomem mais do seu orçamento.**")

            df_saidas = df_an[df_an[valor_col] < 0].copy()
            if df_saidas.empty:
                st.warning("Nenhuma saída (despesa) registrada neste período para gerar a Curva ABC.")
                return

            df_saidas['Valor Absoluto'] = df_saidas[valor_col].abs()
            df_abc = df_saidas.sort_values(by='Valor Absoluto', ascending=False).reset_index(drop=True)
            df_abc['% Acumulada'] = (df_abc['Valor Absoluto'].cumsum() / df_abc['Valor Absoluto'].sum()) * 100

            def classificar_abc(pct):
                if pct <= 80:
                    return '[ Classe A ] (Até 80%)'
                if pct <= 95:
                    return '[ Classe B ] (80% a 95%)'
                return '[ Classe C ] (95% a 100%)'

            df_abc['Classe'] = df_abc['% Acumulada'].apply(classificar_abc)
            if date_col in df_abc.columns:
                df_abc[date_col] = pd.to_datetime(df_abc[date_col]).dt.strftime('%d/%m/%Y')

            df_abc['Valor Absoluto'] = df_abc['Valor Absoluto'].apply(moeda)
            df_abc['% Acumulada'] = df_abc['% Acumulada'].apply(lambda x: f"{x:.2f}%")

            cols_abc = ['Classe']
            if date_col in df_abc.columns:
                cols_abc.append(date_col)
            if desc_col:
                cols_abc.append(desc_col)
            cols_abc.extend(['Valor Absoluto', '% Acumulada'])

            # Renomeia colunas para exibição amigável
            rename_abc = {}
            if date_col in df_abc.columns:
                rename_abc[date_col] = 'Data'
            if desc_col:
                rename_abc[desc_col] = 'Descrição'

            st.dataframe(df_abc[cols_abc].rename(columns=rename_abc), hide_index=True, width='stretch')
            st.info("[ DICA ] Focar na negociação dos itens da Classe A traz maior impacto na saúde financeira.")

        with t_consultor:
            # Usa o mês do filtro de data início para o diagnóstico
            mes_consultor = d_ini.month
            ano_consultor = d_ini.year
            diag = ConsultorEngine.diagnostico_completo(ano_consultor, mes_consultor)
            ConsultorManager._renderizar_status_geral(diag)
            ConsultorManager._renderizar_alertas(diag['alertas'])
            st.markdown("---")
            ConsultorManager._renderizar_diagnostico(diag)
