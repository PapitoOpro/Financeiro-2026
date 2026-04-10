# ==========================================
# MÓDULO: CONSULTOR FINANCEIRO INTELIGENTE
# ==========================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import db
from utils import moeda

# ==========================================
# MOTOR DE ANÁLISE (Cérebro)
# ==========================================
class ConsultorEngine:
    """Motor de regras que analisa dados e gera alertas, sugestões e insights."""

    # Níveis 
    CRITICO = "critico"
    ATENCAO = "atencao"
    SUGESTAO = "sugestao"
    INSIGHT = "insight"
    SEGURO = "seguro"

    ICONES = {
        "critico": "🚨",
        "atencao": "⚠️",
        "sugestao": "💡",
        "insight": "🔍",
        "seguro": "✅",
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
        "insight": "#f4ecf8",
        "seguro": "#eafaf1",
    }

    @staticmethod
    def diagnostico_completo(ano, mes):
        user_id = db.get_user_id()
        
        primeiro_dia = f"{ano}-{mes:02d}-01"
        if mes == 12:
            ultimo_dia = f"{ano}-12-31"
        else:
            ultimo_dia = (datetime(ano, mes + 1, 1) - timedelta(days=1)).strftime('%Y-%m-%d')

        # 1. BUSCA BLINDADA: Caixa
        # Separa exatamente o que é entrada e o que é saída, forçando valores positivos (ABS)
        q_caixa = f"""
            SELECT 
                SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as entradas,
                SUM(CASE WHEN valor < 0 THEN ABS(valor) ELSE 0 END) as saidas
            FROM transacoes
            WHERE user_id = {user_id}
              AND (tipo_fluxo = 'CAIXA' OR tipo_fluxo IS NULL)
              AND fatura_id IS NULL
              AND data_vencimento >= '{primeiro_dia}' AND data_vencimento <= '{ultimo_dia}'
        """
        df_caixa = db.buscar(q_caixa)
        entradas = float(df_caixa['entradas'].iloc[0] or 0) if not df_caixa.empty else 0.0
        saidas_caixa = float(df_caixa['saidas'].iloc[0] or 0) if not df_caixa.empty else 0.0

        # 2. BUSCA BLINDADA: Cartões (Faturas)
        q_cartao = f"""
            SELECT SUM(ABS(i.valor)) as total
            FROM itens_fatura i
            JOIN faturas f ON i.fatura_id = f.id
            WHERE i.user_id = {user_id}
              AND f.data_vencimento >= '{primeiro_dia}' AND f.data_vencimento <= '{ultimo_dia}'
        """
        df_cartao = db.buscar(q_cartao)
        faturas = float(df_cartao['total'].iloc[0] or 0) if not df_cartao.empty else 0.0

        # 3. MATEMÁTICA FINANCEIRA CORRIGIDA
        total_despesas = saidas_caixa + faturas
        sobra = entradas - total_despesas
        
        if entradas > 0:
            comprometimento = (total_despesas / entradas) * 100
        else:
            comprometimento = 100.0 if total_despesas > 0 else 0.0

        diag = {
            'entradas': entradas,
            'saidas_caixa': saidas_caixa,
            'faturas': faturas,
            'total_despesas': total_despesas,
            'sobra': sobra,
            'comprometimento': comprometimento,
            'alertas': []
        }

        # 4. MOTOR DE REGRAS E ALERTAS DA IA
        if comprometimento > 90:
            diag['alertas'].append({
                "nivel": ConsultorEngine.CRITICO,
                "titulo": "Risco de Insolvência",
                "msg": f"Suas despesas ({moeda(total_despesas)}) consomem {comprometimento:.0f}% das receitas. Risco de fechar no vermelho."
            })
        elif comprometimento > 75:
            diag['alertas'].append({
                "nivel": ConsultorEngine.ATENCAO,
                "titulo": "Orçamento Apertado",
                "msg": f"Comprometimento de {comprometimento:.0f}%. Evite novas dívidas parceladas este mês."
            })
        elif comprometimento > 0 and comprometimento <= 50:
            diag['alertas'].append({
                "nivel": ConsultorEngine.SEGURO,
                "titulo": "Saúde Financeira Excelente",
                "msg": f"Você gastou apenas {comprometimento:.0f}% da sua receita. Ótimo momento para investir."
            })

        if faturas > (entradas * 0.4) and entradas > 0:
            diag['alertas'].append({
                "nivel": ConsultorEngine.ATENCAO,
                "titulo": "Alerta de Cartão de Crédito",
                "msg": "Mais de 40% da sua receita está comprometida apenas com faturas de cartão."
            })

        if entradas == 0 and total_despesas > 0:
            diag['alertas'].append({
                "nivel": ConsultorEngine.CRITICO,
                "titulo": "Sem Receitas Registradas",
                "msg": "Você tem despesas este mês, mas nenhuma entrada registrada. O caixa ficará negativo."
            })
            
        if sobra > 0 and comprometimento < 75:
            diag['alertas'].append({
                "nivel": ConsultorEngine.SUGESTAO,
                "titulo": "Oportunidade de Reserva",
                "msg": f"O mês vai fechar com sobra de {moeda(sobra)}. Considere transferir parte desse valor para uma reserva de emergência."
            })

        return diag
# ==========================================
# INTERFACE DE USUÁRIO (Cards e Visuais)
# ==========================================
class ConsultorManager:
    """Gerencia a exibição do Consultor Financeiro na tela."""

    @staticmethod
    def widget_alertas(ano, mes):
        """Widget compacto de alertas para importar em outras telas (ex: Caixa)."""
        # Calcula o diagnóstico para o mês/ano solicitado
        diag = ConsultorEngine.diagnostico_completo(ano, mes)
        # Renderiza apenas os 2 alertas mais importantes para não poluir a tela
        ConsultorManager._renderizar_alertas(diag['alertas'], max_alertas=2)

    @staticmethod
    def _renderizar_status_geral(diag):
        st.markdown("### Resumo Estratégico do Mês")
        
        c1, c2, c3 = st.columns(3)
        
        # Sobra de Caixa
        cor_sobra = "#27ae60" if diag['sobra'] >= 0 else "#c0392b"
        c1.markdown(f"""
            <div style="background:#f1f2f6; padding:15px; border-radius:10px; border-left:5px solid {cor_sobra};">
                <small style="color:#555; font-weight:bold;">Sobra Prevista de Caixa</small><br>
                <strong style="font-size: 24px; color:{cor_sobra};">{moeda(diag['sobra'])}</strong>
            </div>
        """, unsafe_allow_html=True)
        
        # Comprometimento
        cor_comp = "#27ae60" if diag['comprometimento'] <= 60 else ("#f39c12" if diag['comprometimento'] <= 80 else "#c0392b")
        c2.markdown(f"""
            <div style="background:#f1f2f6; padding:15px; border-radius:10px; border-left:5px solid {cor_comp};">
                <small style="color:#555; font-weight:bold;">Comprometimento da Renda</small><br>
                <strong style="font-size: 24px; color:{cor_comp};">{diag['comprometimento']:.0f}%</strong>
            </div>
        """, unsafe_allow_html=True)
        
        # Faturas
        c3.markdown(f"""
            <div style="background:#f1f2f6; padding:15px; border-radius:10px; border-left:5px solid #3498db;">
                <small style="color:#555; font-weight:bold;">Faturas de Cartão</small><br>
                <strong style="font-size: 24px; color:#2980b9;">{moeda(diag['faturas'])}</strong>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("")

    @staticmethod
    def _renderizar_alertas(alertas, max_alertas=4):
        ordem = {
            ConsultorEngine.CRITICO: 1,
            ConsultorEngine.ATENCAO: 2,
            ConsultorEngine.SUGESTAO: 3,
            ConsultorEngine.INSIGHT: 4,
            ConsultorEngine.SEGURO: 5,
        }
        alertas_sorted = sorted(alertas, key=lambda a: ordem.get(a['nivel'], 6))
        alertas_top = alertas_sorted[:max_alertas]

        tem_destaque = any(a['nivel'] in (ConsultorEngine.CRITICO, ConsultorEngine.ATENCAO, ConsultorEngine.SUGESTAO) for a in alertas_top)

        if not tem_destaque:
            return

        st.markdown("#### Alertas da IA")
        for alerta in alertas_top:
            nivel = alerta['nivel']
            if nivel == ConsultorEngine.SEGURO:
                continue
            icone = ConsultorEngine.ICONES[nivel]
            cor = ConsultorEngine.CORES_NIVEL[nivel]
            bg = ConsultorEngine.BG_NIVEL[nivel]

            st.markdown(f"""
                <div style="background:{bg}; border-left:4px solid {cor}; padding:12px 15px; border-radius:6px; margin-bottom:10px;">
                    <div style="font-size:14px; font-weight:bold; color:{cor}; margin-bottom:4px;">
                        {icone} {alerta['titulo']}
                    </div>
                    <div style="font-size:13px; color:#333;">
                        {alerta['msg']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    @staticmethod
    def _renderizar_diagnostico(diag):
        st.markdown("#### Detalhamento")
        
        with st.expander("Ver cálculo completo da IA"):
            st.write(f"**(+) Entradas Recebidas:** {moeda(diag['entradas'])}")
            st.write(f"**(-) Despesas de Caixa:** {moeda(diag['saidas_caixa'])}")
            st.write(f"**(-) Faturas de Cartão:** {moeda(diag['faturas'])}")
            st.write("---")
            st.write(f"**(=) Sobra Real do Mês:** {moeda(diag['sobra'])}")