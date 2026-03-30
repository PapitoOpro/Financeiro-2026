# ==========================================
# MÓDULO: CONTROLE DE CAIXA
# ==========================================

import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from config import MESES_LISTA, COL_EXTRATO, COL_ESPACO, COL_FORM, CORES
from database import db
from utils import moeda, get_cor_saldo, get_cor_valor
from modules.consultor import ConsultorManager

class CaixaManager:
    """Gerenciador do Controle de Caixa."""
    
    @staticmethod
    def renderizar():
        """Renderiza a página de controle de caixa."""
        st.header("[ $ ] Controle de Caixa Real")
        
        # 1. FILTROS NO TOPO
        col_m1, col_m2 = st.columns([1, 1])
        mes_nome = col_m1.selectbox(
            "Mês:", MESES_LISTA,
            index=datetime.now().month - 1
        )
        ano_sel = col_m2.number_input(
            "Ano:", min_value=2025, max_value=2030, value=2026
        )
        
        # Calcula período
        mes_num = MESES_LISTA.index(mes_nome) + 1
        data_inicio = f"{ano_sel}-{mes_num:02d}-01"
        data_fim = (
            datetime(ano_sel, mes_num, 1) +
            relativedelta(months=1) -
            relativedelta(days=1)
        ).strftime('%Y-%m-%d')
        
        # Carrega dados
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")
        
        df_caixa = db.buscar(f"""
            SELECT t.id, t.data_vencimento as data, t.descricao, t.valor,
                   cat.nome as categoria, c.nome as banco 
            FROM transacoes t 
            LEFT JOIN categorias cat ON t.categoria_id = cat.id 
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL) 
            AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}' 
            ORDER BY t.data_vencimento DESC
        """)
        
        # Calcula resumo
        ent = df_caixa[df_caixa['valor'] > 0]['valor'].sum() if not df_caixa.empty else 0
        sai = abs(df_caixa[df_caixa['valor'] < 0]['valor'].sum()) if not df_caixa.empty else 0
        bal = ent - sai
        
        # 2. CARDS DE RESUMO
        CaixaManager._renderizar_cards(ent, sai, bal)
        
        # ALERTAS DO CONSULTOR
        ConsultorManager.widget_alertas(ano_sel, mes_num)
        
        # 3. DIVISÃO: EXTRATO | FORMULÁRIO
        col_extrato, col_espaco, col_form = st.columns([COL_EXTRATO, COL_ESPACO, COL_FORM])
        
        # LADO DIREITO: FORMULÁRIO
        with col_form:
            CaixaManager._renderizar_formulario(df_contas, df_cats)
        
        # LADO ESQUERDO: EXTRATO
        with col_extrato:
            CaixaManager._renderizar_extrato(df_caixa, df_contas, df_cats)
    
    @staticmethod
    def _renderizar_cards(ent, sai, bal):
        """Renderiza os cards de resumo."""
        bg_bal = get_cor_saldo(bal)
        
        st.markdown(f'''
            <div style="display: flex; gap: 10px; margin-bottom: 25px; margin-top: 10px;">
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid {CORES['entrada']};">
                    <small>Entradas</small><br><strong style="font-size: 20px; color: {CORES['positivo']};">{moeda(ent)}</strong>
                </div>
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid {CORES['saida']};">
                    <small>Saídas</small><br><strong style="font-size: 20px; color: {CORES['negativo']};">-{moeda(sai)}</strong>
                </div>
                <div style="background:{bg_bal}; color:#ffffff; padding:15px; border-radius:10px; flex:1;">
                    <small>Balanço Final</small><br><strong style="font-size: 22px;">{moeda(bal)}</strong>
                </div>
            </div>
        ''', unsafe_allow_html=True)
    
    @staticmethod
    def _renderizar_formulario(df_contas, df_cats):
        """Renderiza formulário de novo lançamento."""
        st.markdown("**[ + ] Novo Lançamento**")
        
        with st.form("form_caixa", clear_on_submit=True):
            desc_r = st.text_input("Descrição")
            val_r = st.number_input("Valor (R$)", min_value=0.0)
            
            c_tipo1, c_tipo2 = st.columns(2)
            tipo = c_tipo1.radio("Tipo", ["Entrada", "Saída"])
            data_pg = c_tipo2.date_input("Data", datetime.now())
            
            conta_r = st.selectbox(
                "Conta / Banco",
                df_contas['nome'] if not df_contas.empty else [""]
            )
            cat_r = st.selectbox(
                "Categoria",
                df_cats['nome'] if not df_cats.empty else [""]
            )
            
            if st.form_submit_button("Lançar no Caixa", width='stretch'):
                if not desc_r or val_r <= 0:
                    st.error("❌ Preencha descrição e valor!")
                else:
                    cid = int(df_contas[df_contas.nome == conta_r].id.values[0])
                    ctid = int(df_cats[df_cats.nome == cat_r].id.values[0])
                    valor_final = -val_r if "Saída" in tipo else val_r
                    
                    db.executar(
                        "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, tipo_fluxo) VALUES (?,?,?,?,?,'CAIXA')",
                        (desc_r, valor_final, data_pg, cid, ctid)
                    )
                    st.rerun()
    
    @staticmethod
    def _renderizar_extrato(df_caixa, df_contas, df_cats):
        """Renderiza lista de transações com edição inline."""
        st.markdown("**[ = ] Extrato de Transações**")
        
        if df_caixa.empty:
            st.info("ℹ️ Nenhuma movimentação lançada neste mês.")
            return
        
        for _, row in df_caixa.iterrows():
            rid = int(row['id'])
            editing_key = f"editing_caixa_{rid}"
            is_editing = st.session_state.get(editing_key, False)
            
            if not is_editing:
                # --- MODO LEITURA ---
                c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2.5, 0.8, 0.8])
                
                c1.write(pd.to_datetime(row['data']).strftime('%d/%m/%Y'))
                
                c2.markdown(
                    f"**{row['descricao']}**<br>"
                    f"<span style='color:gray; font-size:12px;'>{row['categoria']} | {row['banco']}</span>",
                    unsafe_allow_html=True
                )
                
                cor = get_cor_valor(row['valor'])
                c3.markdown(
                    f"<div style='text-align: right; color: {cor}; font-weight: bold;'>{moeda(row['valor'])}</div>",
                    unsafe_allow_html=True
                )
                
                with c4:
                    if st.button("✏️", key=f"edit_caixa_{rid}", help="Editar"):
                        st.session_state[editing_key] = True
                        st.rerun()
                
                with c5:
                    if st.button("🗑️", key=f"del_caixa_{rid}", help="Excluir"):
                        st.session_state[f"confirm_del_caixa_{rid}"] = True
                        st.rerun()
                
                # Confirmação de exclusão
                if st.session_state.get(f"confirm_del_caixa_{rid}", False):
                    st.warning(f"Excluir **{row['descricao']}**?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Sim", key=f"yes_del_{rid}"):
                        db.executar("DELETE FROM transacoes WHERE id=?", (rid,))
                        st.session_state.pop(f"confirm_del_caixa_{rid}", None)
                        st.rerun()
                    if cc2.button("❌ Não", key=f"no_del_{rid}"):
                        st.session_state.pop(f"confirm_del_caixa_{rid}", None)
                        st.rerun()
            else:
                # --- MODO EDIÇÃO INLINE ---
                st.markdown(f"---\n**Editando: {row['descricao']}**")
                
                n_desc = st.text_input("Descrição", value=row['descricao'], key=f"ec_desc_{rid}")
                
                ec1, ec2 = st.columns(2)
                n_val = ec1.number_input("Valor (R$)", value=abs(float(row['valor'])), min_value=0.0, key=f"ec_val_{rid}")
                n_tipo = ec2.radio("Tipo", ["Entrada", "Saída"], index=0 if row['valor'] >= 0 else 1, key=f"ec_tipo_{rid}")
                
                try:
                    default_date = pd.to_datetime(row['data']).date() if not pd.isnull(row['data']) else datetime.now().date()
                except Exception:
                    default_date = datetime.now().date()
                
                ec3, ec4, ec5 = st.columns(3)
                n_data = ec3.date_input("Data", value=default_date, key=f"ec_data_{rid}")
                
                lista_contas = df_contas['nome'].tolist()
                idx_conta = lista_contas.index(row['banco']) if row.get('banco') in lista_contas else 0
                n_conta = ec4.selectbox("Conta / Banco", lista_contas, index=idx_conta, key=f"ec_cnt_{rid}")
                
                lista_cats = df_cats['nome'].tolist()
                idx_cat = lista_cats.index(row['categoria']) if row.get('categoria') in lista_cats else 0
                n_cat = ec5.selectbox("Categoria", lista_cats, index=idx_cat, key=f"ec_cat_{rid}")
                
                btn1, btn2 = st.columns(2)
                if btn1.button("💾 Salvar", key=f"ec_save_{rid}", use_container_width=True):
                    cid = int(df_contas[df_contas.nome == n_conta].id.values[0])
                    ctid = int(df_cats[df_cats.nome == n_cat].id.values[0])
                    v_final = -n_val if n_tipo == "Saída" else n_val
                    
                    db.executar(
                        "UPDATE transacoes SET descricao=?, valor=?, data_vencimento=?, conta_id=?, categoria_id=? WHERE id=?",
                        (n_desc, v_final, n_data, cid, ctid, rid)
                    )
                    st.session_state.pop(editing_key, None)
                    st.rerun()
                
                if btn2.button("❌ Cancelar", key=f"ec_cancel_{rid}", use_container_width=True):
                    st.session_state.pop(editing_key, None)
                    st.rerun()
                
                st.markdown("---")
            
            if not is_editing:
                st.markdown("<hr style='margin: 0px 0px 10px 0px; padding: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
