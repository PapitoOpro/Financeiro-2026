# ==========================================
# MÓDULO: PROJEÇÃO DE GASTOS (EXEMPLO)
# ==========================================
# Este é um exemplo de como adicionar um novo módulo
# Para usar: descomentar as importações em app.py

import streamlit as st
import pandas as pd
import re
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
        """Aba para importar faturas PDF com debug melhorado."""
        st.subheader("📄 Importador Universal de Faturas via OCR")
        
        senha_pdf = st.text_input("Senha do PDF (se houver)", type="password")
        file = st.file_uploader("Envie a fatura PDF", type="pdf")

        if file:
            with st.spinner("🔄 Lendo a fatura com OCR... Processando texto..."):
                texto = extrair_texto_pdf(file, senha_pdf or None)
            
            if not texto or "Erro" in texto:
                st.error("❌ Falha ao extrair texto. Verifique a senha ou o arquivo.")
                return
            
            # Detecta banco
            banco = detectar_banco(texto)
            
            if banco != "GENÉRICO":
                st.success(f"✅ Banco detectado: **{banco}**")
            else:
                st.warning("⚠️ Banco não identificado automaticamente (continuando...)")
            
            # Mostra preview do texto extraído
            with st.expander("📋 Ver texto bruto extraído pelo OCR"):
                st.text_area("Texto do PDF:", texto, height=200, disabled=True)
            
            st.divider()
            
            # Extrai parcelas
            dados = extrair_parcelas(texto)
            
            if dados:
                st.success(f"✅ **{len(dados)} parcelas encontradas!**")
                
                with st.expander("👀 Pré-visualizar parcelas encontradas"):
                    df_preview = []
                    for desc, parc, val in dados[:10]:
                        df_preview.append({
                            "Descrição": desc[:50],
                            "Parcela": parc,
                            "Valor": f"R$ {val:,.2f}"
                        })
                    
                    if df_preview:
                        import pandas as pd
                        st.dataframe(pd.DataFrame(df_preview), use_container_width=True, hide_index=True)
                    
                    if len(dados) > 10:
                        st.caption(f"... e mais {len(dados) - 10} parcelas")
                
                st.divider()
                
                # Formulário de importação
                with st.form("importar_pdf_form"):
                    st.markdown("### Confirmar Importação")
                    
                    conta = st.selectbox("💳 Cartão destino", df_contas['nome'] if not df_contas.empty else [""])
                    cat = st.selectbox("🏷️ Categoria", df_cats['nome'] if not df_cats.empty else [""])
                    data_base = st.date_input("📅 Data da 1ª parcela")
                    
                    # Trava de segurança
                    if banco != "GENÉRICO" and banco not in conta.upper():
                        st.warning(
                            f"⚠️ **Aviso:** PDF detectado como **{banco}**, "
                            f"mas você selecionou **{conta}** como destino.\n\n"
                            "Se estiver correto, marque a caixa abaixo para confirmar."
                        )
                        confirmar = st.checkbox("✓ Confirmo que estou importando para a conta correta")
                    else:
                        confirmar = True
                    
                    if st.form_submit_button("📥 Importar Parcelas", use_container_width=True):
                        if not confirmar:
                            st.error("❌ Confirme que a conta está correta antes de importar.")
                        else:
                            ParcelasManager._importar_pdf_dados(
                                dados, banco, conta, cat, data_base, df_contas, df_cats
                            )
            else:
                st.error(
                    "❌ **Nenhuma parcela encontrada!**\n\n"
                    "Possíveis causas:\n"
                    "- O PDF não contém informações de parcelamento\n"
                    "- O formato das parcelas é diferente do esperado\n"
                    "- O texto não foi extraído corretamente\n\n"
                    "💡 Dica: Verifique o texto bruto acima para ver como o OCR leu o documento."
                )
    
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
        """Aba com previsão de gastos - Dashboard completo."""
        st.subheader("📅 Dashboard de Previsão de Gastos")
        
        df_p = db.buscar("""
            SELECT t.id, t.data_vencimento, t.descricao, t.valor, c.nome as banco
            FROM transacoes t
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.tipo_fluxo='CARTAO'
            ORDER BY t.data_vencimento ASC
        """)
        
        if df_p.empty:
            st.info("ℹ️ Nenhuma parcela lançada")
            return
        
        df_p['data_vencimento'] = pd.to_datetime(df_p['data_vencimento'])
        
        # ==============================
        # 🏆 1. MÉTRICAS DE TOPO
        # ==============================
        total_divida = abs(df_p['valor'].sum())
        
        # Agrupa os valores por Mês/Ano para o gráfico
        df_p['Mes_Ano'] = df_p['data_vencimento'].dt.to_period('M')
        agrupado_mes = df_p.groupby('Mes_Ano')['valor'].sum().abs().reset_index()
        agrupado_mes['Mes_Ano_Str'] = agrupado_mes['Mes_Ano'].astype(str)
        
        mes_mais_pesado = agrupado_mes.loc[agrupado_mes['valor'].idxmax()]
        
        col1, col2 = st.columns(2)
        col1.metric("💰 Total Parcelado", moeda(total_divida))
        col2.metric("⚠️ Mês Mais Pesado", f"{mes_mais_pesado['Mes_Ano_Str']} - {moeda(mes_mais_pesado['valor'])}")
        
        st.markdown("---")
        
        # ==============================
        # 📊 2. GRÁFICO DE EVOLUÇÃO
        # ==============================
        st.markdown("**📈 Evolução do Parcelamento nos Próximos Meses**")
        df_grafico = agrupado_mes[['Mes_Ano_Str', 'valor']].set_index('Mes_Ano_Str')
        st.bar_chart(df_grafico, color="#e74c3c", use_container_width=True)
        
        st.markdown("---")
        
        # ==============================
        # 📝 3. LISTAGEM CASCATA COM EDIÇÃO
        # ==============================
        st.markdown("**📋 Detalhamento por Mês**")
        meses_previsao = st.slider("Ver previsão detalhada para quantos meses?", 1, 24, 6)
        primeiro_mes = df_p['data_vencimento'].min().replace(day=1)
        
        for i in range(meses_previsao):
            mes_atual = primeiro_mes + relativedelta(months=i)
            f_mes = df_p[
                (df_p['data_vencimento'].dt.month == mes_atual.month) &
                (df_p['data_vencimento'].dt.year == mes_atual.year)
            ]
            
            if not f_mes.empty:
                total_mes = abs(f_mes['valor'].sum())
                
                with st.expander(f"📅 **{mes_atual.strftime('%B/%Y').upper()}** — Total: {moeda(total_mes)}", expanded=False):
                    cartoes_no_mes = f_mes['banco'].fillna("Desconhecido").unique()
                    
                    for cartao in cartoes_no_mes:
                        f_cartao = f_mes[f_mes['banco'].fillna("Desconhecido") == cartao]
                        subtotal_cartao = abs(f_cartao['valor'].sum())
                        
                        st.markdown(f"**💳 Fatura: {cartao}** — Subtotal: **{moeda(subtotal_cartao)}**")
                        
                        # Tabela com parcelas
                        for _, r in f_cartao.iterrows():
                            col1, col2, col3, col4 = st.columns([5, 2, 1, 1])
                            
                            desc_limpa = re.sub(r'^\[.*?\]\s*', '', r['descricao'])
                            
                            col1.write(f"↳ {desc_limpa}")
                            col2.write(f"**{moeda(abs(r['valor']))}**")
                            
                            # Button editar
                            with col3:
                                if st.button("✏️", key=f"edit_parc_{r['id']}", help="Editar parcela"):
                                    st.session_state[f"edit_parc_{r['id']}"] = True
                            
                            # Button deletar
                            if col4.button("🗑️", key=f"del_parc_{r['id']}", help="Deletar parcela"):
                                db.executar("DELETE FROM transacoes WHERE id=?", (r['id'],))
                                st.success("✅ Parcela deletada!")
                                st.rerun()
                            
                            # Popover de edição
                            if st.session_state.get(f"edit_parc_{r['id']}", False):
                                with st.popover(f"Editar {desc_limpa}", use_container_width=True):
                                    n_desc = st.text_input("Descrição", value=r['descricao'], key=f"ed_desc_{r['id']}")
                                    n_val = st.number_input("Valor (R$)", value=abs(float(r['valor'])), min_value=0.0, step=0.01, key=f"ed_val_{r['id']}")
                                    n_data = st.date_input("Data", value=pd.to_datetime(r['data_vencimento']).date(), key=f"ed_data_{r['id']}")
                                    
                                    if st.button("💾 Salvar", key=f"save_parc_{r['id']}", use_container_width=True):
                                        db.executar(
                                            "UPDATE transacoes SET descricao=?, valor=?, data_vencimento=? WHERE id=?",
                                            (n_desc, -n_val, n_data, r['id'])
                                        )
                                        st.success("✅ Parcela atualizada!")
                                        st.session_state[f"edit_parc_{r['id']}"] = False
                                        st.rerun()
                        
                        st.divider()
