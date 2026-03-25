# ==========================================
# MÓDULO: PROJEÇÃO DE GASTOS (EXEMPLO)
# ==========================================
# Este é um exemplo de como adicionar um novo módulo
# Para usar: descomentar as importações em app.py

import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from config import MESES_LISTA, CORES
from database import db
from utils import moeda, extrair_texto_pdf, detectar_banco, extrair_parcelas, get_cor_valor

class ParcelasManager:
    """Gerenciador de Projeção de Gastos (Parcelas)."""
    
    @staticmethod
    def renderizar():
        """Renderiza a página de projeção de gastos."""
        st.header("📉 Projeção de Gastos (Cartão/Parcelas)")
        
        tab1, tab2, tab3 = st.tabs(["Manual", "Importar PDF", "Previsão"])
        
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")
        
        with tab1:
            ParcelasManager._tab_manual(df_contas, df_cats)
        
        with tab2:
            ParcelasManager._tab_importar_pdf(df_contas, df_cats)
        
        with tab3:
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
            cnt = c1.selectbox("Cartão", df_contas['nome'] if not df_contas.empty else [""])
            cat = c2.selectbox("Categoria", df_cats['nome'] if not df_cats.empty else [""])
            dt_ini = c3.date_input("Vencimento da 1ª parcela")
            
            if st.form_submit_button("Lançar Parcelas", use_container_width=True):
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
        """Lança parcelas no banco."""
        cid = int(df_contas[df_contas.nome == cnt].id.values[0])
        ctid = int(df_cats[df_cats.nome == cat].id.values[0])
        
        parcelas_lancar = (int(p_total) - int(p_atual)) + 1
        
        for i in range(parcelas_lancar):
            venc = dt_ini + relativedelta(months=i)
            num_parc = int(p_atual) + i
            d_final = f"[{cnt}] {desc} ({num_parc:02d}/{int(p_total):02d})"
            
            db.executar(
                "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CARTAO')",
                (d_final, -val, venc, cid, ctid)
            )
        
        st.success(f"✅ {parcelas_lancar} parcelas lançadas!")
        st.rerun()
    
    @staticmethod
    def _tab_importar_pdf(df_contas, df_cats):
        """Aba para importar faturas PDF."""
        st.subheader("📄 Importador de Faturas via OCR")
        
        senha_pdf = st.text_input("Senha do PDF (se houver)", type="password")
        file = st.file_uploader("Envie a fatura PDF", type="pdf")
        
        if file:
            with st.spinner("Lendo PDF com OCR..."):
                texto = extrair_texto_pdf(file, senha_pdf or None)
            
            if not texto or "Erro" in texto:
                st.error("❌ Falha ao extrair texto. Verifique a senha.")
            else:
                banco = detectar_banco(texto)
                
                if banco != "GENÉRICO":
                    st.success(f"✅ Banco detectado: **{banco}**")
                else:
                    st.warning("⚠️ Banco não identificado automaticamente")
                
                with st.expander("Ver texto extraído"):
                    st.text(texto[:1000] + "...")
                
                dados = extrair_parcelas(texto)
                
                if dados:
                    st.info(f"✅ {len(dados)} parcelas encontradas")
                    
                    with st.form("importar_pdf"):
                        conta = st.selectbox("Cartão destino", df_contas['nome'])
                        cat = st.selectbox("Categoria", df_cats['nome'])
                        data_base = st.date_input("Data da 1ª parcela")
                        
                        if st.form_submit_button("Importar", use_container_width=True):
                            ParcelasManager._importar_pdf_dados(
                                dados, banco, conta, cat, data_base, df_contas, df_cats
                            )
                else:
                    st.warning("⚠️ Nenhuma parcela encontrada")
    
    @staticmethod
    def _importar_pdf_dados(dados, banco, conta, cat, data_base, df_contas, df_cats):
        """Importa dados do PDF para o BD."""
        cid = int(df_contas[df_contas.nome == conta].id.values[0])
        ctid = int(df_cats[df_cats.nome == cat].id.values[0])
        novos = duplicados = 0
        
        for desc, parc, val in dados:
            atual, total = map(int, parc.split("/"))
            for i in range(atual-1, total):
                venc = data_base + relativedelta(months=i-(atual-1))
                desc_f = f"[{conta}] {desc} ({i+1:02d}/{total:02d})"
                desc_like = f"%] {desc} ({i+1:02d}/{total:02d})"
                
                check = db.buscar_um(
                    "SELECT id FROM transacoes WHERE descricao LIKE ? AND valor=? AND data_vencimento=?",
                    (desc_like, -val, venc)
                )
                
                if not check:
                    db.executar(
                        "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CARTAO')",
                        (desc_f, -val, venc, cid, ctid)
                    )
                    novos += 1
                else:
                    duplicados += 1
        
        if novos > 0:
            st.success(f"🚀 {novos} parcelas importadas!")
        if duplicados > 0:
            st.info(f"ℹ️ {duplicados} duplicadas (ignoradas)")
    
    @staticmethod
    def _tab_previsao():
        """Aba com previsão de gastos."""
        st.subheader("📅 Previsão de Gastos")
        
        df_p = db.buscar("""
            SELECT t.data_vencimento, t.descricao, t.valor, c.nome as banco
            FROM transacoes t
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.tipo_fluxo='CARTAO'
            ORDER BY t.data_vencimento ASC
        """)
        
        if df_p.empty:
            st.info("ℹ️ Nenhuma parcela lançada")
            return
        
        df_p['data_vencimento'] = pd.to_datetime(df_p['data_vencimento'])
        total_divida = abs(df_p['valor'].sum())
        
        # Cards de resumo
        col1, col2 = st.columns(2)
        col1.metric("Total Parcelado", moeda(total_divida), delta=None)
        col2.metric("Parcelas", len(df_p), delta=None)
        
        st.markdown("---")
        
        # Gráfico por mês
        df_mes = df_p.copy()
        df_mes['mes_ano'] = df_mes['data_vencimento'].dt.to_period('M')
        df_grafico = df_mes.groupby('mes_ano')['valor'].sum().abs()
        
        st.line_chart(df_grafico)
