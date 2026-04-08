# ==========================================
# MÓDULO: CONSULTOR FINANCEIRO INTELIGENTE
# ==========================================
# Motor de análise + Interface de alertas, sugestões e insights

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from database import db
from config import MESES_LISTA, CORES
from utils import moeda

# ==========================================
# MOTOR DE ANÁLISE (cérebro)
# ==========================================

class ConsultorEngine:
    """Motor de regras que analisa dados e gera alertas/sugestões/insights."""

    # Níveis 
    CRITICO = "critico"
    ATENCAO = "atencao"
    SUGESTAO = "sugestao"
    INSIGHT = "insight"
    SEGURO = "seguro"

    ICONES = {
        "critico": "",
        "atencao": "",
        "sugestao": "",
        "insight": "",
        "seguro": "",
    }

    CORES_NIVEL = {
        "critico": "#e74c3c",
        "atencao": "#f39c12",
        "sugestao": "#3498db",
        "insight": "#9b59b6",
        "seguro": "#2ecc71",
    }

    BG_NIVEL = {
        "critico": "#fdedec",
        "atencao": "#fef9e7",
        "sugestao": "#ebf5fb",
        "insight": "#f4ecf7",
        "seguro": "#eafaf1",
    }

    @staticmethod
    def carregar_limites():
        """Carrega limites configurados do banco."""
        user_id = db.get_user_id()
        df = db.buscar(f"SELECT chave, valor FROM limites_financeiros WHERE user_id = {user_id}")
        if df.empty:
            return {}
        return dict(zip(df['chave'], df['valor'].astype(float)))

    @staticmethod
    def dados_mes(ano, mes):
        """Carrega transações do caixa para um mês específico."""
        user_id = db.get_user_id()
        data_inicio = f"{ano}-{mes:02d}-01"
        data_fim = (
            datetime(ano, mes, 1) + relativedelta(months=1) - relativedelta(days=1)
        ).strftime('%Y-%m-%d')

        df = db.buscar(f"""
            SELECT t.id, t.data_vencimento as data, t.descricao, t.valor,
                   cat.nome as categoria, c.nome as banco,
                   cat.id as categoria_id, cat.percentual_meta,
                   COALESCE(sub.nome, '') as subcategoria
            FROM transacoes t
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            LEFT JOIN contas c ON t.conta_id = c.id
            LEFT JOIN subcategorias sub ON t.subcategoria_id = sub.id
            WHERE t.user_id = {user_id}
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            ORDER BY t.data_vencimento
        """)

        # Inclui itens de fatura (gastos cartão) na análise
        df_cartao = db.buscar(f"""
            SELECT i.id, f.data_vencimento as data, i.descricao,
                   -ABS(i.valor) as valor,
                   cat.nome as categoria, c.nome as banco,
                   i.categoria_id, cat.percentual_meta,
                   COALESCE(sub.nome, '') as subcategoria
            FROM itens_fatura i
            JOIN faturas f ON i.fatura_id = f.id
            LEFT JOIN categorias cat ON i.categoria_id = cat.id
            LEFT JOIN contas c ON f.conta_id = c.id
            LEFT JOIN subcategorias sub ON i.subcategoria_id = sub.id
            WHERE i.user_id = {user_id}
            AND f.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            ORDER BY f.data_vencimento
        """)
        # Corrige FutureWarning: concat apenas se df_cartao tem dados válidos
        df_cartao_clean = df_cartao.dropna(how='all') if not df_cartao.empty else pd.DataFrame()
        if not df_cartao_clean.empty:
            df = pd.concat([df, df_cartao_clean], ignore_index=True)

        return df

    @staticmethod
    def dados_ultimos_meses(n_meses=3):
        """Carrega transações dos últimos N meses."""
        user_id = db.get_user_id()
        hoje = datetime.now()
        data_inicio = (hoje - relativedelta(months=n_meses)).replace(day=1).strftime('%Y-%m-%d')
        data_fim = hoje.strftime('%Y-%m-%d')

        df = db.buscar(f"""
            SELECT t.id, t.data_vencimento as data, t.descricao, t.valor,
                   cat.nome as categoria, c.nome as banco
            FROM transacoes t
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.user_id = {user_id}
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL)
            AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            ORDER BY t.data_vencimento
        """)

        # Inclui itens de fatura no histórico
        df_cartao = db.buscar(f"""
            SELECT i.id, f.data_vencimento as data, i.descricao,
                   -ABS(i.valor) as valor,
                   cat.nome as categoria, c.nome as banco
            FROM itens_fatura i
            JOIN faturas f ON i.fatura_id = f.id
            LEFT JOIN categorias cat ON i.categoria_id = cat.id
            LEFT JOIN contas c ON f.conta_id = c.id
            WHERE i.user_id = {user_id}
            AND f.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            ORDER BY f.data_vencimento
        """)
        # Corrige FutureWarning: concat apenas se df_cartao tem dados válidos
        df_cartao_clean = df_cartao.dropna(how='all') if not df_cartao.empty else pd.DataFrame()
        if not df_cartao_clean.empty:
            df = pd.concat([df, df_cartao_clean], ignore_index=True)

        return df

    @staticmethod
    def saldo_acumulado():
        """Calcula saldo acumulado de todas as transações do caixa (ledger contínuo)."""
        user_id = db.get_user_id()
        df = db.buscar(f"""
            SELECT COALESCE(SUM(valor), 0) as saldo
            FROM transacoes
            WHERE user_id = {user_id}
            AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL)
        """)
        if df.empty:
            return 0.0
        return float(df.iloc[0]['saldo'])

    @classmethod
    def analisar(cls, ano, mes):
        """Executa todas as regras e retorna lista de alertas/sugestões."""
        alertas = []
        limites = cls.carregar_limites()
        df_mes = cls.dados_mes(ano, mes)

        if df_mes.empty:
            return alertas

        entradas = df_mes[df_mes['valor'] > 0]['valor'].sum()
        saidas = abs(df_mes[df_mes['valor'] < 0]['valor'].sum())
        saldo_mes = entradas - saidas
        saldo_acum = cls.saldo_acumulado()

        # Regra 1: % de gasto sobre a renda 
        if entradas > 0:
            pct_gasto = (saidas / entradas) * 100
            limite_critico = limites.get('pct_alerta_critico', 90)
            limite_atencao = limites.get('pct_alerta_preventivo', 70)
            limite_max = limites.get('pct_gasto_maximo', 80)

            if pct_gasto >= limite_critico:
                alertas.append({
                    'nivel': cls.CRITICO,
                    'titulo': f'Você já gastou {pct_gasto:.0f}% da sua renda!',
                    'mensagem': f'Seus gastos ({moeda(saidas)}) atingiram {pct_gasto:.0f}% das entradas ({moeda(entradas)}). '
                                f'Limite crítico: {limite_critico:.0f}%.',
                    'frase': f'Calma lá… você já gastou {pct_gasto:.0f}% da sua renda ',
                })
            elif pct_gasto >= limite_max:
                alertas.append({
                    'nivel': cls.ATENCAO,
                    'titulo': f'Gastos em {pct_gasto:.0f}% da renda',
                    'mensagem': f'Seus gastos ({moeda(saidas)}) estão em {pct_gasto:.0f}% das entradas ({moeda(entradas)}). '
                                f'Limite recomendado: {limite_max:.0f}%.',
                    'frase': f'Atenção! Você já usou {pct_gasto:.0f}% do orçamento ',
                })
            elif pct_gasto >= limite_atencao:
                alertas.append({
                    'nivel': cls.ATENCAO,
                    'titulo': f'Gastos chegando a {pct_gasto:.0f}% da renda',
                    'mensagem': f'Você gastou {moeda(saidas)} de {moeda(entradas)} em entradas. Fique atento.',
                    'frase': f'Fique de olho… já foi {pct_gasto:.0f}% do orçamento ',
                })
            else:
                alertas.append({
                    'nivel': cls.SEGURO,
                    'titulo': f'Gastos em {pct_gasto:.0f}% da renda',
                    'mensagem': f'Você gastou {moeda(saidas)} de {moeda(entradas)}. Tudo dentro do planejado!',
                    'frase': f'Mandou bem! Seus gastos estão controlados em {pct_gasto:.0f}% ',
                })

        # Regra 2: Categorias acima do limite (usa percentual_meta da categoria) 
        if entradas > 0:
            df_saidas = df_mes[df_mes['valor'] < 0].copy()
            if not df_saidas.empty:
                df_saidas['valor_abs'] = df_saidas['valor'].abs()
                por_cat = df_saidas.groupby('categoria')['valor_abs'].sum()

                # Carrega percentual_meta das categorias
                cat_metas = {}
                if 'percentual_meta' in df_saidas.columns:
                    for _, row in df_saidas.drop_duplicates('categoria').iterrows():
                        if row.get('categoria'):
                            cat_metas[row['categoria']] = float(row.get('percentual_meta') or 0)

                for cat, total_cat in por_cat.items():
                    pct_cat = (total_cat / entradas) * 100
                    cat_str = str(cat)

                    # Usa percentual_meta da categoria; fallback para limites_financeiros
                    limite_cat = cat_metas.get(cat_str, 0)
                    if limite_cat == 0:
                        chave_limite = f'pct_cat_{cat_str.lower().replace(" ", "_")}' if cat else None
                        limite_cat = limites.get(chave_limite, 30) if chave_limite else 30

                    if pct_cat >= limite_cat and limite_cat > 0:
                        # Inteligência via Micro: detalha subcategorias responsáveis
                        detalhe_sub = ""
                        df_cat_saidas = df_saidas[df_saidas['categoria'] == cat]
                        if 'subcategoria' in df_cat_saidas.columns:
                            subs = df_cat_saidas[df_cat_saidas['subcategoria'] != '']
                            if not subs.empty:
                                por_sub = subs.groupby('subcategoria')['valor_abs'].sum().sort_values(ascending=False)
                                top_sub = por_sub.head(3)
                                sub_details = [f"{s}: {moeda(v)}" for s, v in top_sub.items()]
                                detalhe_sub = f" Principais subcategorias: {', '.join(sub_details)}."

                        alertas.append({
                            'nivel': cls.ATENCAO,
                            'titulo': f'Categoria "{cat}" acima do limite',
                            'mensagem': f'{cat} consumiu {pct_cat:.1f}% da renda ({moeda(total_cat)}). '
                                        f'Meta configurada: {limite_cat:.0f}%.{detalhe_sub}',
                            'frase': f'A categoria {cat} está puxando pesado: {pct_cat:.1f}% da renda ',
                        })

        # Regra 3: Dias restantes no mês vs saldo 
        hoje = datetime.now()
        if hoje.month == mes and hoje.year == ano:
            ultimo_dia = (datetime(ano, mes, 1) + relativedelta(months=1) - relativedelta(days=1)).day
            dias_restantes = ultimo_dia - hoje.day
            saldo_minimo = limites.get('saldo_minimo', 500)

            if dias_restantes > 0 and saldo_mes > 0:
                gasto_diario_medio = saidas / max(hoje.day, 1)
                gasto_previsto_restante = gasto_diario_medio * dias_restantes
                saldo_previsto = saldo_mes - gasto_previsto_restante

                if saldo_previsto < 0:
                    dias_ate_zero = int(saldo_mes / gasto_diario_medio) if gasto_diario_medio > 0 else 999
                    alertas.append({
                        'nivel': cls.CRITICO,
                        'titulo': f'Previsão: saldo negativo em {dias_ate_zero} dias',
                        'mensagem': f'Se continuar nesse ritmo ({moeda(gasto_diario_medio)}/dia), '
                                    f'seu saldo acaba antes do fim do mês!',
                        'frase': f'Alerta! Nesse ritmo você fica no vermelho em {dias_ate_zero} dias ',
                    })
                elif saldo_previsto < saldo_minimo:
                    alertas.append({
                        'nivel': cls.ATENCAO,
                        'titulo': 'Saldo previsto abaixo do mínimo',
                        'mensagem': f'Previsão de saldo no fim do mês: {moeda(saldo_previsto)}. '
                                    f'Mínimo recomendado: {moeda(saldo_minimo)}.',
                        'frase': f'Cuidado! No fim do mês pode sobrar apenas {moeda(saldo_previsto)} ',
                    })

            if saldo_mes < saldo_minimo and saldo_mes >= 0:
                alertas.append({
                    'nivel': cls.ATENCAO,
                    'titulo': 'Saldo abaixo do mínimo recomendado',
                    'mensagem': f'Saldo atual do mês: {moeda(saldo_mes)}. '
                                f'Mínimo recomendado: {moeda(saldo_minimo)}.',
                    'frase': f'Seu saldo ({moeda(saldo_mes)}) está abaixo do mínimo de {moeda(saldo_minimo)} ',
                })

        # Regra 4: Dinheiro extra → sugestão de guardar 
        df_hist = cls.dados_ultimos_meses(3)
        if not df_hist.empty and entradas > 0:
            df_hist['data'] = pd.to_datetime(df_hist['data'])
            hist_mensal = df_hist[df_hist['valor'] > 0].groupby(
                df_hist['data'].dt.to_period('M')
            )['valor'].sum()

            if len(hist_mensal) >= 2:
                media_entradas = hist_mensal.iloc[:-1].mean() if len(hist_mensal) > 1 else hist_mensal.mean()
                if entradas > media_entradas * 1.1:
                    extra = entradas - media_entradas
                    pct_guardar = limites.get('pct_sugestao_guardar', 30)
                    sugestao_guardar = extra * (pct_guardar / 100)
                    alertas.append({
                        'nivel': cls.SUGESTAO,
                        'titulo': f'Renda extra de {moeda(extra)} detectada!',
                        'mensagem': f'Você recebeu {moeda(extra)} a mais que a média. '
                                    f'Que tal guardar {pct_guardar:.0f}% ({moeda(sugestao_guardar)})?',
                        'frase': f'Boa notícia! Entrou {moeda(extra)} a mais. Guardar {moeda(sugestao_guardar)}? ',
                    })

        # Insight: Maior categoria de gasto 
        if entradas > 0 and not df_mes[df_mes['valor'] < 0].empty:
            df_saidas = df_mes[df_mes['valor'] < 0].copy()
            df_saidas['valor_abs'] = df_saidas['valor'].abs()
            top_cat = df_saidas.groupby('categoria')['valor_abs'].sum().sort_values(ascending=False)

            if not top_cat.empty:
                maior_cat = top_cat.index[0]
                maior_val = top_cat.iloc[0]
                pct_maior = (maior_val / saidas) * 100 if saidas > 0 else 0
                alertas.append({
                    'nivel': cls.INSIGHT,
                    'titulo': f'Maior gasto: {maior_cat} ({pct_maior:.0f}%)',
                    'mensagem': f'A categoria "{maior_cat}" representa {pct_maior:.0f}% dos gastos '
                                f'do mês ({moeda(maior_val)} de {moeda(saidas)}).',
                    'frase': f'Seu maior gasto é {maior_cat}: {pct_maior:.0f}% das saídas ',
                })

        # Insight: Média dos últimos 3 meses 
        if not df_hist.empty:
            df_hist['data'] = pd.to_datetime(df_hist['data'])
            hist_saidas = df_hist[df_hist['valor'] < 0].copy()
            if not hist_saidas.empty:
                hist_saidas['valor_abs'] = hist_saidas['valor'].abs()
                media_mensal = hist_saidas.groupby(
                    hist_saidas['data'].dt.to_period('M')
                )['valor_abs'].sum()

                if len(media_mensal) >= 2:
                    media_3m = media_mensal.mean()
                    if saidas > media_3m * 1.15:
                        alertas.append({
                            'nivel': cls.ATENCAO,
                            'titulo': 'Gastos acima da média recente',
                            'mensagem': f'Seus gastos este mês ({moeda(saidas)}) estão acima da média '
                                        f'dos últimos {len(media_mensal)} meses ({moeda(media_3m)}).',
                            'frase': f'Você está gastando mais que o normal: {moeda(saidas)} vs média {moeda(media_3m)} ',
                        })
                    else:
                        alertas.append({
                            'nivel': cls.INSIGHT,
                            'titulo': 'Gastos dentro da média',
                            'mensagem': f'Seus gastos ({moeda(saidas)}) estão alinhados com a média '
                                        f'recente ({moeda(media_3m)}).',
                            'frase': f'Seus gastos estão alinhados com sua média: {moeda(media_3m)} ',
                        })

        # Insight: Saldo acumulado (visão ledger) 
        alertas.append({
            'nivel': cls.INSIGHT,
            'titulo': f'Saldo acumulado geral: {moeda(saldo_acum)}',
            'mensagem': f'Saldo contínuo de todas as transações do caixa desde o início.',
            'frase': f'Seu saldo acumulado total é {moeda(saldo_acum)} {"" if saldo_acum >= 0 else ""}',
        })

        return alertas

    @classmethod
    def diagnostico_completo(cls, ano, mes):
        """Retorna análise completa: alertas + métricas + distribuição."""
        limites = cls.carregar_limites()
        df_mes = cls.dados_mes(ano, mes)
        alertas = cls.analisar(ano, mes)
        saldo_acum = cls.saldo_acumulado()
        df_hist = cls.dados_ultimos_meses(3)

        entradas = df_mes[df_mes['valor'] > 0]['valor'].sum() if not df_mes.empty else 0
        saidas = abs(df_mes[df_mes['valor'] < 0]['valor'].sum()) if not df_mes.empty else 0
        saldo_mes = entradas - saidas

        # Distribuição por categoria
        dist_cat = pd.DataFrame()
        if not df_mes.empty:
            df_saidas = df_mes[df_mes['valor'] < 0].copy()
            if not df_saidas.empty:
                df_saidas['valor_abs'] = df_saidas['valor'].abs()
                dist_cat = df_saidas.groupby('categoria')['valor_abs'].sum().reset_index()
                dist_cat = dist_cat.sort_values('valor_abs', ascending=False)
                dist_cat['pct'] = (dist_cat['valor_abs'] / dist_cat['valor_abs'].sum() * 100).round(1)

        # Evolução mensal (últimos meses)
        evolucao = pd.DataFrame()
        if not df_hist.empty:
            df_hist['data'] = pd.to_datetime(df_hist['data'])
            df_hist['mes'] = df_hist['data'].dt.to_period('M')
            ent_m = df_hist[df_hist['valor'] > 0].groupby('mes')['valor'].sum().rename('entradas')
            sai_m = df_hist[df_hist['valor'] < 0].groupby('mes')['valor'].sum().abs().rename('saidas')
            evolucao = pd.concat([ent_m, sai_m], axis=1).fillna(0).reset_index()
            evolucao['mes'] = evolucao['mes'].astype(str)
            evolucao['saldo'] = evolucao['entradas'] - evolucao['saidas']

        # Status geral
        if entradas > 0:
            pct = (saidas / entradas) * 100
            if pct >= limites.get('pct_alerta_critico', 90):
                status = cls.CRITICO
            elif pct >= limites.get('pct_gasto_maximo', 80):
                status = cls.ATENCAO
            elif pct >= limites.get('pct_alerta_preventivo', 70):
                status = cls.ATENCAO
            else:
                status = cls.SEGURO
        else:
            status = cls.INSIGHT

        return {
            'alertas': alertas,
            'entradas': entradas,
            'saidas': saidas,
            'saldo_mes': saldo_mes,
            'saldo_acumulado': saldo_acum,
            'pct_gasto': (saidas / entradas * 100) if entradas > 0 else 0,
            'dist_categorias': dist_cat,
            'evolucao': evolucao,
            'status': status,
            'limites': limites,
        }


# ==========================================
# INTERFACE DO CONSULTOR
# ==========================================

class ConsultorManager:
    """Renderiza a interface do Consultor Financeiro."""

    @staticmethod
    def renderizar():
        """Página completa do consultor financeiro."""
        st.header(" Consultor Financeiro")
        st.caption("Seu assistente inteligente de finanças — alertas, sugestões e insights personalizados.")

        # Filtros
        col_m, col_a = st.columns(2)
        mes_nome = col_m.selectbox("Mês:", MESES_LISTA, index=datetime.now().month - 1, key="consultor_mes")
        ano = col_a.number_input("Ano:", min_value=2025, max_value=2030, value=datetime.now().year, key="consultor_ano")
        mes_num = MESES_LISTA.index(mes_nome) + 1

        diag = ConsultorEngine.diagnostico_completo(ano, mes_num)

        # Status Geral 
        ConsultorManager._renderizar_status_geral(diag)

        # Tabs principais 
        tab_alertas, tab_insights, tab_config = st.tabs([
            " Alertas e Sugestões",
            " Diagnóstico Completo",
            " Configurar Limites",
        ])

        with tab_alertas:
            ConsultorManager._renderizar_alertas(diag['alertas'])

        with tab_insights:
            ConsultorManager._renderizar_diagnostico(diag)

        with tab_config:
            ConsultorManager._renderizar_config(diag['limites'])

    @staticmethod
    def _renderizar_status_geral(diag):
        """Renderiza o card de status geral com semáforo."""
        status = diag['status']
        pct = diag['pct_gasto']
        entradas = diag['entradas']
        saidas = diag['saidas']
        saldo_acum = diag['saldo_acumulado']

        cor_status = ConsultorEngine.CORES_NIVEL[status]
        icone_status = ConsultorEngine.ICONES[status]

        labels = {
            ConsultorEngine.CRITICO: "PERIGO",
            ConsultorEngine.ATENCAO: "ATENÇÃO",
            ConsultorEngine.SEGURO: "SEGURO",
            ConsultorEngine.INSIGHT: "SEM DADOS",
        }
        label = labels.get(status, "—")

        # Barra de progresso visual
        barra_cor = cor_status
        barra_pct = min(pct, 100)

        st.markdown(f"""
            <div style="display:flex; gap:12px; margin:10px 0 20px 0; flex-wrap:wrap;">
                <div style="background:{ConsultorEngine.BG_NIVEL[status]}; border:2px solid {cor_status};
                            padding:18px 24px; border-radius:12px; flex:2; min-width:280px;">
                    <div style="font-size:14px; color:#666;">Status Financeiro do Mês</div>
                    <div style="font-size:28px; font-weight:bold; color:{cor_status}; margin:4px 0;">
                        {icone_status} {label}
                    </div>
                    <div style="background:#e0e0e0; border-radius:6px; height:10px; margin:8px 0;">
                        <div style="background:{barra_cor}; width:{barra_pct}%; height:10px; border-radius:6px;"></div>
                    </div>
                    <div style="font-size:12px; color:#888;">{pct:.0f}% da renda consumida</div>
                </div>
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1; min-width:140px;
                            border-left:5px solid {CORES['entrada']};">
                    <small style="color:#666;">Entradas</small><br>
                    <strong style="font-size:20px; color:{CORES['positivo']};">{moeda(entradas)}</strong>
                </div>
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1; min-width:140px;
                            border-left:5px solid {CORES['saida']};">
                    <small style="color:#666;">Saídas</small><br>
                    <strong style="font-size:20px; color:{CORES['negativo']};">-{moeda(saidas)}</strong>
                </div>
                <div style="background:#f1f2f6; padding:15px; border-radius:10px; flex:1; min-width:140px;
                            border-left:5px solid #3498db;">
                    <small style="color:#666;">Saldo Acumulado</small><br>
                    <strong style="font-size:20px; color:{'#27ae60' if saldo_acum >= 0 else '#c0392b'};">
                        {moeda(saldo_acum)}
                    </strong>
                </div>
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def _renderizar_alertas(alertas):
        """Renderiza lista de alertas com cards coloridos."""
        if not alertas:
            st.info("Nenhum alerta para exibir. Cadastre transações no Caixa para começar a análise.")
            return

        # Ordena: críticos primeiro, depois atenção, sugestão, insight, seguro
        ordem = {
            ConsultorEngine.CRITICO: 0,
            ConsultorEngine.ATENCAO: 1,
            ConsultorEngine.SUGESTAO: 2,
            ConsultorEngine.INSIGHT: 3,
            ConsultorEngine.SEGURO: 4,
        }
        alertas_sorted = sorted(alertas, key=lambda a: ordem.get(a['nivel'], 5))

        for alerta in alertas_sorted:
            nivel = alerta['nivel']
            icone = ConsultorEngine.ICONES[nivel]
            cor = ConsultorEngine.CORES_NIVEL[nivel]
            bg = ConsultorEngine.BG_NIVEL[nivel]

            st.markdown(f"""
                <div style="background:{bg}; border-left:5px solid {cor}; padding:14px 18px;
                            border-radius:8px; margin-bottom:10px;">
                    <div style="font-size:15px; font-weight:bold; color:{cor};">
                        {icone} {alerta['titulo']}
                    </div>
                    <div style="font-size:13px; color:#555; margin-top:4px;">
                        {alerta['mensagem']}
                    </div>
                    <div style="font-size:14px; color:#333; margin-top:8px; font-style:italic;">
                        "{alerta['frase']}"
                    </div>
                </div>
            """, unsafe_allow_html=True)

    @staticmethod
    def _renderizar_diagnostico(diag):
        """Renderiza diagnóstico completo com gráficos."""
        st.markdown("#### Distribuição de Gastos por Categoria")

        dist_cat = diag['dist_categorias']
        if not dist_cat.empty:
            import plotly.express as px

            fig = px.pie(
                dist_cat, values='valor_abs', names='categoria',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=True, margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

            # Tabela detalhada
            limites = diag['limites']
            st.markdown("**Detalhe por Categoria:**")
            for _, row in dist_cat.iterrows():
                cat = row['categoria']
                val = row['valor_abs']
                pct = row['pct']
                cat_str = str(cat)
                chave = f'pct_cat_{cat_str.lower().replace(" ", "_")}' if cat else None
                limite = limites.get(chave, None) if chave else None

                barra_cor = '#2ecc71'
                if limite and pct > limite:
                    barra_cor = '#e74c3c'
                elif limite and pct > limite * 0.8:
                    barra_cor = '#f39c12'

                limite_text = f" (limite: {limite:.0f}%)" if limite else ""
                st.markdown(f"""
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                        <div style="width:120px; font-size:13px; font-weight:bold;">{cat}</div>
                        <div style="flex:1; background:#e0e0e0; border-radius:4px; height:16px;">
                            <div style="background:{barra_cor}; width:{min(pct, 100)}%; height:16px;
                                        border-radius:4px; text-align:center; color:white; font-size:11px; line-height:16px;">
                                {pct:.1f}%
                            </div>
                        </div>
                        <div style="width:120px; text-align:right; font-size:13px;">{moeda(val)}{limite_text}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhum gasto registrado para mostrar distribuição.")

        st.markdown("---")

        # Evolução mensal
        st.markdown("#### Evolução Mensal (Últimos Meses)")
        evolucao = diag['evolucao']
        if not evolucao.empty:
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_bar(
                x=evolucao['mes'], y=evolucao['entradas'],
                name='Entradas', marker_color='#2ecc71',
            )
            fig.add_bar(
                x=evolucao['mes'], y=evolucao['saidas'],
                name='Saídas', marker_color='#e74c3c',
            )
            fig.add_trace(go.Scatter(
                x=evolucao['mes'], y=evolucao['saldo'],
                name='Saldo', mode='lines+markers',
                line=dict(color='#3498db', width=2),
            ))
            fig.update_layout(
                barmode='group',
                yaxis_title='Valor (R$)',
                yaxis_tickprefix='R$ ',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(t=40, b=20),
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Dados insuficientes para evolução mensal.")

        st.markdown("---")

        # Previsão de gasto até o fim do mês
        st.markdown("#### Previsão até o Fim do Mês")
        hoje = datetime.now()
        if diag['saidas'] > 0 and hoje.day > 1:
            gasto_diario = diag['saidas'] / hoje.day
            dias_restantes = (datetime(hoje.year, hoje.month, 1) +
                              relativedelta(months=1) - relativedelta(days=1)).day - hoje.day
            gasto_previsto = diag['saidas'] + (gasto_diario * dias_restantes)
            saldo_previsto = diag['entradas'] - gasto_previsto

            c1, c2, c3 = st.columns(3)
            c1.metric("Gasto médio/dia", moeda(gasto_diario))
            c2.metric("Gasto previsto total", moeda(gasto_previsto))
            c3.metric("Saldo previsto fim do mês", moeda(saldo_previsto),
                       delta=f"{'+' if saldo_previsto >= 0 else ''}{moeda(saldo_previsto)}")
        else:
            st.info("Dados insuficientes para previsão.")

    @staticmethod
    def _renderizar_config(limites_atuais):
        """Permite ao usuário configurar limites do consultor."""
        st.markdown("#### Ajuste seus limites financeiros")
        st.caption("Esses valores definem quando o consultor emite alertas.")

        with st.form("form_limites"):
            st.markdown("** Limites Gerais**")
            c1, c2 = st.columns(2)

            pct_max = c1.number_input(
                "% máximo de gastos sobre renda",
                min_value=0.0, max_value=100.0, step=5.0,
                value=float(limites_atuais.get('pct_gasto_maximo', 80)),
                help="Acima desse %, o consultor emite alerta de atenção."
            )
            pct_critico = c2.number_input(
                "% alerta crítico",
                min_value=0.0, max_value=100.0, step=5.0,
                value=float(limites_atuais.get('pct_alerta_critico', 90)),
                help="Acima desse %, entra no nível PERIGO."
            )
            pct_prev = c1.number_input(
                "% alerta preventivo",
                min_value=0.0, max_value=100.0, step=5.0,
                value=float(limites_atuais.get('pct_alerta_preventivo', 70)),
                help="A partir desse %, o consultor começa a avisar."
            )
            saldo_min = c2.number_input(
                "Saldo mínimo recomendado (R$)",
                min_value=0.0, step=100.0,
                value=float(limites_atuais.get('saldo_minimo', 500)),
            )
            pct_guardar = c1.number_input(
                "% sugestão de guardar (renda extra)",
                min_value=0.0, max_value=100.0, step=5.0,
                value=float(limites_atuais.get('pct_sugestao_guardar', 30)),
            )

            st.markdown("** Metas por Categoria (%)**")
            st.caption("As metas por categoria agora são configuradas em Cadastros → Categorias. "
                       "Cada categoria tem seu percentual de meta definido diretamente.")

            # Mostra resumo das categorias e suas metas
            user_id = db.get_user_id()
            df_cats = db.buscar(
                f"SELECT nome, percentual_meta, icone FROM categorias "
                f"WHERE user_id = {user_id} AND ativa = TRUE ORDER BY nome"
            )
            if not df_cats.empty:
                for _, cat in df_cats.iterrows():
                    icone = cat.get('icone', '') or ''
                    pct = float(cat.get('percentual_meta', 0) or 0)
                    st.markdown(f"{icone} **{cat['nome']}**: {pct:.0f}%")

            if st.form_submit_button(" Salvar Limites", width='stretch'):
                # Salva limites gerais
                updates = {
                    'pct_gasto_maximo': pct_max,
                    'pct_alerta_critico': pct_critico,
                    'pct_alerta_preventivo': pct_prev,
                    'saldo_minimo': saldo_min,
                    'pct_sugestao_guardar': pct_guardar,
                }

                for chave, valor in updates.items():
                    db.executar(
                        "INSERT INTO limites_financeiros (chave, valor, descricao, user_id) "
                        "VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (chave, user_id) DO UPDATE SET valor = EXCLUDED.valor",
                        (chave, valor, '', db.get_user_id())
                    )

                st.success(" Limites atualizados com sucesso!")
                st.rerun()

    # Widget compacto para usar em outras páginas 

    @staticmethod
    def widget_alertas(ano, mes, max_alertas=3):
        """Renderiza um widget compacto de alertas para inserir em outras páginas."""
        alertas = ConsultorEngine.analisar(ano, mes)
        if not alertas:
            return

        # Pega apenas os mais relevantes
        ordem = {
            ConsultorEngine.CRITICO: 0,
            ConsultorEngine.ATENCAO: 1,
            ConsultorEngine.SUGESTAO: 2,
            ConsultorEngine.INSIGHT: 3,
            ConsultorEngine.SEGURO: 4,
        }
        alertas_sorted = sorted(alertas, key=lambda a: ordem.get(a['nivel'], 5))
        alertas_top = alertas_sorted[:max_alertas]

        # Filtra: só mostra se tiver algo além de SEGURO/INSIGHT
        tem_destaque = any(a['nivel'] in (ConsultorEngine.CRITICO, ConsultorEngine.ATENCAO, ConsultorEngine.SUGESTAO)
                          for a in alertas_top)

        if not tem_destaque:
            return

        st.markdown("#### Consultor Financeiro")
        for alerta in alertas_top:
            nivel = alerta['nivel']
            if nivel == ConsultorEngine.SEGURO:
                continue
            icone = ConsultorEngine.ICONES[nivel]
            cor = ConsultorEngine.CORES_NIVEL[nivel]
            bg = ConsultorEngine.BG_NIVEL[nivel]

            st.markdown(f"""
                <div style="background:{bg}; border-left:4px solid {cor}; padding:10px 14px;
                            border-radius:6px; margin-bottom:8px;">
                    <div style="font-size:13px; font-weight:bold; color:{cor};">
                        {icone} {alerta['titulo']}
                    </div>
                    <div style="font-size:12px; color:#555; margin-top:2px; font-style:italic;">
                        "{alerta['frase']}"
                    </div>
                </div>
            """, unsafe_allow_html=True)
