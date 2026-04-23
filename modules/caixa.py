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
        st.header("Controle de Caixa Real")

        # 1. FILTROS NO TOPO
        mes_nome = st.segmented_control(
            "Mês:", MESES_LISTA,
            default=MESES_LISTA[datetime.now().month - 1]
        )
        col_ano, _ = st.columns([1, 5])
        ano_sel = col_ano.number_input(
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
        user_id = db.get_user_id()
        df_contas = db.buscar(
            f"SELECT * FROM contas WHERE user_id = {user_id} ORDER BY nome")
        df_cats = db.buscar(
            f"SELECT * FROM categorias WHERE user_id = {user_id} AND ativa = TRUE ORDER BY nome")

        # Carrega todas as subcategorias ativas
        df_subs = db.buscar(f"""
            SELECT s.id, s.nome, s.categoria_id, c.nome as categoria_nome,
                   COALESCE(c.tipo, 'saida') as categoria_tipo
            FROM subcategorias s
            JOIN categorias c ON s.categoria_id = c.id
            WHERE s.user_id = {user_id} AND s.ativa = TRUE
            ORDER BY c.nome, s.nome
        """)

        df_caixa = db.buscar(f"""
            SELECT t.id, t.data_vencimento as data, t.descricao, t.valor,
                   cat.nome as categoria, c.nome as banco,
                   COALESCE(sub.nome, '') as subcategoria,
                   COALESCE(t.compensado, FALSE) as compensado,
                   t.data_compensacao, t.fatura_id
            FROM transacoes t 
            LEFT JOIN categorias cat ON t.categoria_id = cat.id 
            LEFT JOIN contas c ON t.conta_id = c.id
            LEFT JOIN subcategorias sub ON t.subcategoria_id = sub.id
            WHERE t.user_id = {user_id}
            AND (t.tipo_fluxo = 'CAIXA' OR t.tipo_fluxo IS NULL) 
            AND t.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}' 
            ORDER BY t.data_vencimento DESC
        """)

        # DEBUG: Exibir todas as transações carregadas do banco antes de qualquer filtro
        # if st.checkbox('DEBUG: Exibir todas as transações do banco (sem filtro)', value=False, key='show_all_db_transacoes'):
        # st.dataframe(df_caixa)

        # Calcula resumo

        ent = df_caixa[df_caixa['valor'] >
                       0]['valor'].sum() if not df_caixa.empty else 0
        sai = abs(df_caixa[df_caixa['valor'] < 0]
                  ['valor'].sum()) if not df_caixa.empty else 0
        bal = ent - sai

        # Compensação stats
        compensados = 0
        pendentes = 0
        total_itens = 0
        if not df_caixa.empty:
            total_itens = len(df_caixa)
            compensados = df_caixa['compensado'].sum(
            ) if 'compensado' in df_caixa.columns else 0
            pendentes = total_itens - compensados

        # 2. CARDS DE RESUMO
        CaixaManager._renderizar_cards(ent, sai, bal, compensados, pendentes)

        # ALERTAS DO CONSULTOR
        ConsultorManager.widget_alertas(ano_sel, mes_num)

        # 3. DIVISÃO: EXTRATO | FORMULÁRIO
        col_extrato, col_espaco, col_form = st.columns(
            [COL_EXTRATO, COL_ESPACO, COL_FORM])

        # LADO DIREITO: FORMULÁRIO
        with col_form:
            CaixaManager._renderizar_formulario(df_contas, df_cats, df_subs)

        # LADO ESQUERDO: EXTRATO
        with col_extrato:
            CaixaManager._renderizar_extrato(df_caixa, df_contas, df_cats)

    @staticmethod
    def _renderizar_cards(ent, sai, bal, compensados=0, pendentes=0):
        """Renderiza os cards de resumo."""
        bg_bal = get_cor_saldo(bal)
        cor_pend = '#e74c3c' if pendentes > 0 else '#2ecc71'

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
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; flex:1; border-left:5px solid {cor_pend};">
                    <small>Compensação</small><br>
                    <strong style="font-size: 14px; color:#2ecc71;">{compensados}</strong>
                    <strong style="font-size: 14px; color:{cor_pend};"> | {pendentes}</strong>
                </div>
            </div>
        ''', unsafe_allow_html=True)

    @staticmethod
    def _renderizar_formulario(df_contas, df_cats, df_subs=None):
        """Renderiza formulário de novo lançamento com seleção por subcategoria."""
        st.markdown("**Novo Lançamento**")

        # Monta lista de subcategorias agrupadas: "Subcategoria (Categoria)"
        if df_subs is None:
            df_subs = pd.DataFrame()

        # Tipo FORA do form para permitir filtragem dinâmica de subcategorias
        c_tipo1, c_tipo2 = st.columns(2)
        tipo = c_tipo1.radio(
            "Tipo", ["Entrada", "Saída"], key="caixa_tipo_lancamento")
        data_pg = c_tipo2.date_input(
            "Data", datetime.now(), key="caixa_data_lancamento")

        # Filtra subcategorias pelo tipo selecionado
        tipo_filtro = "entrada" if tipo == "Entrada" else "saida"
        if not df_subs.empty and 'categoria_tipo' in df_subs.columns:
            df_subs_filtrado = df_subs[df_subs['categoria_tipo'] == tipo_filtro].reset_index(
                drop=True)
        else:
            df_subs_filtrado = df_subs
        tem_subs = not df_subs_filtrado.empty

        # Filtra categorias pelo tipo selecionado
        if not df_cats.empty and 'tipo' in df_cats.columns:
            df_cats_filtrado = df_cats[df_cats['tipo']
                                       == tipo_filtro].reset_index(drop=True)
        else:
            df_cats_filtrado = df_cats

        with st.form("form_caixa", clear_on_submit=True):
            desc_r = st.text_input("Descrição")
            val_r = st.number_input("Valor (R$)", min_value=0.0)

            conta_r = st.selectbox(
                "Conta / Banco",
                df_contas['nome'] if not df_contas.empty else [""]
            )

            # Seleção inteligente: subcategoria → auto-associa à categoria
            sub_id_sel = None
            cat_id_sel = None

            if tem_subs:
                opcoes_sub = df_subs_filtrado.apply(
                    lambda r: f"{r['nome']} ({r['categoria_nome']})", axis=1
                ).tolist()

                sel_sub = st.selectbox("Subcategoria", opcoes_sub,
                                       help="Escolha a subcategoria e a categoria será associada automaticamente.")

                if sel_sub:
                    idx = opcoes_sub.index(sel_sub)
                    sub_id_sel = int(df_subs_filtrado.iloc[idx]['id'])
                    cat_id_sel = int(
                        df_subs_filtrado.iloc[idx]['categoria_id'])
                    st.caption(
                        f"→ Categoria: **{df_subs_filtrado.iloc[idx]['categoria_nome']}**")

            # Fallback oculto: se não há subcategorias, usa primeira categoria disponível
            if cat_id_sel is None and not df_cats_filtrado.empty:
                cat_id_sel = int(df_cats_filtrado.iloc[0]['id'])

            compensado_r = st.checkbox("Já compensado", value=False)

            if st.form_submit_button("Lançar no Caixa", width='stretch'):
                if not desc_r or val_r <= 0:
                    st.error("Preencha descrição e valor!")
                else:
                    cid = int(
                        df_contas[df_contas.nome == conta_r].id.values[0])
                    ctid = cat_id_sel

                    valor_final = -val_r if "Saída" in tipo else val_r
                    data_comp = data_pg if compensado_r else None
                    user_id = db.get_user_id()

                    db.executar(
                        "INSERT INTO transacoes (descricao, valor, data_vencimento, conta_id, categoria_id, subcategoria_id, tipo_fluxo, compensado, data_compensacao, user_id) VALUES (?,?,?,?,?,?,'CAIXA',?,?,?)",
                        (desc_r, valor_final, data_pg, cid, ctid,
                         sub_id_sel, compensado_r, data_comp, user_id)
                    )
                    st.rerun()

    @staticmethod
    def _renderizar_extrato(df_caixa, df_contas, df_cats):
        """Renderiza lista de transações com edição inline."""
        st.markdown("**Extrato de Transações**")

        if df_caixa.empty:
            st.info("Nenhuma movimentação lançada neste mês.")
            return

        # Filtro de compensação
        filtro_comp = st.radio(
            "Filtrar:", ["Todos", "Pendentes", "Compensados"],
            horizontal=True, key="filtro_compensacao"
        )

        df_view = df_caixa.copy()
        if filtro_comp == "Pendentes":
            df_view = df_view[df_view['compensado'] == False]
        elif filtro_comp == "Compensados":
            df_view = df_view[df_view['compensado'] == True]

        if df_view.empty:
            st.info("Nenhum lançamento encontrado com esse filtro.")
            return

        # Separa faturas de transações normais
        df_faturas = df_view[df_view['fatura_id'].notna()].copy()
        df_normais = df_view[df_view['fatura_id'].isna()].copy()

        # Coleta IDs pendentes de transações normais para bulk
        ids_pendentes_normais = df_normais[df_normais['compensado'] == False]['id'].tolist(
        ) if not df_normais.empty and 'compensado' in df_normais.columns else []
        selected_comp_ids = [
            int(k.replace('comp_sel_', ''))
            for k in st.session_state
            if isinstance(k, str) and k.startswith('comp_sel_') and st.session_state[k]
            and int(k.replace('comp_sel_', '')) in [int(x) for x in ids_pendentes_normais]
        ]

        # Barra de compensação em massa (transações normais)
        if selected_comp_ids:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.info(
                    f"**{len(selected_comp_ids)}** lançamento(s) selecionado(s) para compensar")
            with col_btn:
                if st.button("Compensar selecionados", type="primary", width='stretch', key="btn_comp_bulk", icon=":material/check_circle:"):
                    hoje = datetime.now().date()
                    user_id = db.get_user_id()
                    for sid in selected_comp_ids:
                        db.executar(
                            "UPDATE transacoes SET compensado=TRUE, data_compensacao=? WHERE id=? AND user_id=?",
                            (hoje, sid, user_id)
                        )
                    for k in list(st.session_state.keys()):
                        if isinstance(k, str) and k.startswith('comp_sel_'):
                            del st.session_state[k]
                    st.rerun()

        # ========== SEÇÃO FATURAS ==========
        if not df_faturas.empty:
            st.markdown("#### Faturas")
            user_id = db.get_user_id()

            # Pré-carrega todos os itens de todas as faturas do mês (1 query só)
            fatura_ids_list = [int(x)
                               for x in df_faturas['fatura_id'].unique()]
            if fatura_ids_list:
                # Usa parâmetros para evitar SQL injection
                placeholders = ','.join(['%s'] * len(fatura_ids_list))
                query = f"""
                    SELECT i.id, i.fatura_id, i.descricao, i.valor, i.data_compra,
                           i.parcela_atual, i.parcela_total,
                           cat.nome as categoria, i.categoria_id, i.subcategoria_id,
                           COALESCE(sub.nome, '') as subcategoria
                    FROM itens_fatura i
                    LEFT JOIN categorias cat ON i.categoria_id = cat.id
                    LEFT JOIN subcategorias sub ON i.subcategoria_id = sub.id
                    WHERE i.fatura_id IN ({placeholders}) AND i.user_id = %s
                    ORDER BY i.descricao
                """
                params = tuple(fatura_ids_list) + (user_id,)
                df_all_itens = db.buscar(query, params)
            else:
                df_all_itens = pd.DataFrame()
            for fatura_id_val, grp in df_faturas.groupby('fatura_id'):
                fatura_id_val = int(fatura_id_val)
                row = grp.iloc[0]
                is_compensado = bool(row.get('compensado', False))
                rid = int(row['id'])

                badge = (
                    "<span style='background:#2ecc71; color:black; padding:2px 8px; border-radius:4px; font-size:11px;'>Paga</span>"
                    if is_compensado else
                    "<span style='background:#e74c3c; color:black; padding:2px 8px; border-radius:4px; font-size:11px;'>Pendente</span>"
                )
                cor_valor = get_cor_valor(row['valor'])
                data_venc = pd.to_datetime(row['data']).strftime('%d/%m/%Y')

                # Header da fatura
                st.markdown(
                    f"<div style='background:#f8f9fa; border-left:4px solid {'#2ecc71' if is_compensado else '#e74c3c'}; "
                    f"padding:12px 15px; border-radius:6px; margin:8px 0 4px 0;'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                    f"<div>"
                    f"<strong style='font-size:15px; color:#212529;'>{row['descricao']}</strong><br>"
                    f"<span style='color:gray; font-size:12px;'>Vencimento: {data_venc} | {row['banco']}</span>"
                    f"</div>"
                    f"<div style='text-align:right;'>"
                    f"<strong style='font-size:18px; color:{cor_valor};'>{moeda(row['valor'])}</strong><br>"
                    f"{badge}"
                    f"</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

                # Botões de ação da fatura
                c_pagar, c_excluir = st.columns([1, 1])
                with c_pagar:
                    if not is_compensado:
                        if st.button(f"Pagar Fatura", key=f"pagar_fat_{fatura_id_val}", width='stretch', icon=":material/check:"):
                            db.pagar_fatura(int(fatura_id_val),
                                            user_id, datetime.now().date())
                            st.rerun()
                    else:
                        if st.button(f"Reabrir Fatura", key=f"reabrir_fat_{fatura_id_val}", width='stretch', icon=":material/undo:"):
                            db.reabrir_fatura(fatura_id_val, user_id)
                            st.rerun()
                with c_excluir:
                    if st.button("Excluir Fatura", key=f"del_fat_{fatura_id_val}", width='stretch', icon=":material/delete:"):
                        st.session_state[f"confirm_del_fat_{fatura_id_val}"] = True
                        st.rerun()

                # Confirmação de exclusão de fatura
                if st.session_state.get(f"confirm_del_fat_{fatura_id_val}", False):
                    st.warning(
                        f"Excluir fatura **{row['descricao']}** e todos os seus itens?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("Sim, excluir", key=f"yes_del_fat_{fatura_id_val}", icon=":material/check:"):
                        db.excluir_fatura(int(fatura_id_val), user_id)
                        st.session_state.pop(
                            f"confirm_del_fat_{fatura_id_val}", None)
                        st.rerun()
                    if cc2.button("Não", key=f"no_del_fat_{fatura_id_val}", icon=":material/close:"):
                        st.session_state.pop(
                            f"confirm_del_fat_{fatura_id_val}", None)
                        st.rerun()

                # Expander com itens da fatura (usa dados pré-carregados)
                df_itens_fat = df_all_itens[df_all_itens['fatura_id'] == int(
                    fatura_id_val)] if not df_all_itens.empty else pd.DataFrame()
                n_itens = len(df_itens_fat)

                with st.expander(f"Ver itens da fatura ({n_itens} itens)", expanded=False):
                    if df_itens_fat.empty:
                        st.info("Nenhum item nesta fatura.")
                    else:
                        for _, item in df_itens_fat.iterrows():
                            item_id = int(item['id'])
                            editing_item_key = f"editing_fat_item_{item_id}"
                            is_editing_item = st.session_state.get(
                                editing_item_key, False)

                            parc_label = ""
                            if item.get('parcela_atual') and item.get('parcela_total'):
                                parc_label = f" ({int(item['parcela_atual']):02d}/{int(item['parcela_total']):02d})"

                            if not is_editing_item:
                                ci1, ci2, ci3, ci4, ci5 = st.columns(
                                    [1.3, 3.5, 2.0, 0.5, 0.5])
                                data_compra_str = pd.to_datetime(item['data_compra']).strftime(
                                    '%d/%m/%Y') if item.get('data_compra') and not pd.isnull(item['data_compra']) else ""
                                ci1.write(data_compra_str)
                                ci2.markdown(
                                    f"**{item['descricao']}**{parc_label}<br>"
                                    f"<span style='color:gray; font-size:12px;'>{item.get('categoria', '')}"
                                    f"{' → ' + item['subcategoria'] if item.get('subcategoria') else ''}"
                                    f"</span>",
                                    unsafe_allow_html=True
                                )
                                ci3.markdown(
                                    f"<div style='text-align:right; color:#c0392b; font-weight:bold;'>{moeda(abs(item['valor']))}</div>",
                                    unsafe_allow_html=True
                                )
                                with ci4:
                                    if st.button("\u200b", key=f"edit_fi_{item_id}", help="Editar item", icon=":material/edit:"):
                                        st.session_state[editing_item_key] = True
                                        st.rerun()
                                with ci5:
                                    if st.button("\u200b", key=f"del_fi_{item_id}", help="Excluir item", icon=":material/delete:"):
                                        st.session_state[f"confirm_del_fi_{item_id}"] = True
                                        st.rerun()

                                # Confirmação de exclusão do item
                                if st.session_state.get(f"confirm_del_fi_{item_id}", False):
                                    st.warning(
                                        f"Excluir **{item['descricao']}**?")
                                    cd1, cd2 = st.columns(2)
                                    if cd1.button("Sim", key=f"yes_del_fi_{item_id}", icon=":material/check:"):
                                        db.executar(
                                            "DELETE FROM itens_fatura WHERE id=? AND user_id=?", (item_id, user_id))
                                        db.atualizar_total_fatura(
                                            fatura_id_val)
                                        db.sincronizar_transacao_fatura(
                                            fatura_id_val, user_id)
                                        st.session_state.pop(
                                            f"confirm_del_fi_{item_id}", None)
                                        st.rerun()
                                    if cd2.button("Não", key=f"no_del_fi_{item_id}", icon=":material/close:"):
                                        st.session_state.pop(
                                            f"confirm_del_fi_{item_id}", None)
                                        st.rerun()
                            else:
                                # Edição inline do item da fatura
                                with st.form(f"form_edit_fi_{item_id}"):
                                    d_desc = st.text_input(
                                        "Descrição", value=item['descricao'], key=f"efi_desc_{item_id}")
                                    d_val = st.number_input("Valor (R$)", min_value=0.0, value=float(
                                        abs(item['valor'])), key=f"efi_val_{item_id}")
                                    cat_op = df_cats['nome'].tolist(
                                    ) if not df_cats.empty else []
                                    default_cat_idx = 0
                                    try:
                                        default_cat_idx = cat_op.index(item.get('categoria', '')) if item.get(
                                            'categoria', '') in cat_op else 0
                                    except Exception:
                                        default_cat_idx = 0
                                    sel_cat = st.selectbox(
                                        "Categoria", cat_op, index=default_cat_idx, key=f"efi_cat_{item_id}")

                                    save_clicked = st.form_submit_button(
                                        "Salvar")
                                    cancel_clicked = st.form_submit_button(
                                        "Cancelar")

                                    if cancel_clicked:
                                        st.session_state[editing_item_key] = False
                                        st.rerun()

                                    if save_clicked:
                                        try:
                                            ctid = int(
                                                df_cats[df_cats.nome == sel_cat].id.values[0])
                                            db.executar(
                                                "UPDATE itens_fatura SET descricao=?, valor=?, categoria_id=? WHERE id=? AND user_id=?",
                                                (d_desc, abs(float(d_val)),
                                                 ctid, item_id, user_id)
                                            )
                                            db.atualizar_total_fatura(
                                                int(fatura_id_val))
                                            db.sincronizar_transacao_fatura(
                                                int(fatura_id_val), user_id)
                                        except Exception as e:
                                            st.error(
                                                f"Erro ao atualizar item: {e}")
                                        st.session_state[editing_item_key] = False
                                        st.rerun()

                st.markdown(
                    "<hr style='margin: 5px 0 10px 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

        # ========== SEÇÃO TRANSAÇÕES NORMAIS ==========
        if not df_normais.empty:
            if not df_faturas.empty:
                st.markdown("#### Transações Avulsas")

            for _, row in df_normais.iterrows():
                rid = int(row['id'])
                editing_key = f"editing_caixa_{rid}"
                is_editing = st.session_state.get(editing_key, False)
                is_compensado = bool(row.get('compensado', False))

                if not is_editing:
                    # --- MODO LEITURA ---
                    if not is_compensado:
                        c_sel, c1, c2, c3, c_comp, c4, c5 = st.columns(
                            [0.3, 1.2, 3.0, 2.0, 0.7, 0.5, 0.5])
                        with c_sel:
                            st.checkbox(
                                "Selecionar", key=f"comp_sel_{rid}", label_visibility="collapsed")
                    else:
                        c1, c2, c3, c_comp, c4, c5 = st.columns(
                            [1.3, 3.0, 2.0, 0.7, 0.5, 0.5])

                    c1.write(pd.to_datetime(row['data']).strftime('%d/%m/%Y'))

                    badge_comp = (
                        "<span style='background:#2ecc71; color:gray; padding:1px 6px; border-radius:4px; font-size:10px;'>OK</span> "
                        if is_compensado else
                        "<span style='background:#f39c12; color:gray; padding:1px 6px; border-radius:4px; font-size:10px;'>Pend</span> "
                    )
                    c2.markdown(
                        f"{badge_comp}**{row['descricao']}**<br>"
                        f"<span style='color:gray; font-size:12px;'>{row['categoria']}"
                        f"{' → ' + row['subcategoria'] if row.get('subcategoria') else ''}"
                        f" | {row['banco']}</span>",
                        unsafe_allow_html=True
                    )

                    cor = get_cor_valor(row['valor'])
                    c3.markdown(
                        f"<div style='text-align: right; color: {cor}; font-weight: bold;'>{moeda(row['valor'])}</div>",
                        unsafe_allow_html=True
                    )

                    with c_comp:
                        if not is_compensado:
                            if st.button("\u200b", key=f"comp_caixa_{rid}", help="Compensar", icon=":material/check:"):
                                db.executar(
                                    "UPDATE transacoes SET compensado=TRUE, data_compensacao=? WHERE id=? AND user_id=?",
                                    (datetime.now().date(), rid, db.get_user_id())
                                )
                                st.rerun()
                        else:
                            if st.button("\u200b", key=f"uncomp_caixa_{rid}", help="Descompensar", icon=":material/undo:"):
                                db.executar(
                                    "UPDATE transacoes SET compensado=FALSE, data_compensacao=NULL WHERE id=? AND user_id=?",
                                    (rid, db.get_user_id())
                                )
                                st.rerun()

                    with c4:
                        if st.button("\u200b", key=f"edit_caixa_{rid}", help="Editar", icon=":material/edit:"):
                            st.session_state[editing_key] = True
                            st.rerun()

                    with c5:
                        if st.button("\u200b", key=f"del_caixa_{rid}", help="Excluir", icon=":material/delete:"):
                            st.session_state[f"confirm_del_caixa_{rid}"] = True
                            st.rerun()

                    if st.session_state.get(f"confirm_del_caixa_{rid}", False):
                        st.warning(f"Excluir **{row['descricao']}**?")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("Sim", key=f"yes_del_{rid}", icon=":material/check:"):
                            db.executar(
                                "DELETE FROM transacoes WHERE id=? AND user_id=?", (rid, db.get_user_id()))
                            st.session_state.pop(
                                f"confirm_del_caixa_{rid}", None)
                            st.rerun()
                        if cc2.button("Não", key=f"no_del_{rid}", icon=":material/close:"):
                            st.session_state.pop(
                                f"confirm_del_caixa_{rid}", None)
                            st.rerun()
                else:
                    # --- MODO EDIÇÃO INLINE ---
                    st.markdown(f"---\n**Editando: {row['descricao']}**")

                    n_desc = st.text_input(
                        "Descrição", value=row['descricao'], key=f"ec_desc_{rid}")

                    ec1, ec2 = st.columns(2)
                    n_val = ec1.number_input("Valor (R$)", value=abs(
                        float(row['valor'])), min_value=0.0, key=f"ec_val_{rid}")
                    n_tipo = ec2.radio("Tipo", [
                                       "Entrada", "Saída"], index=0 if row['valor'] >= 0 else 1, key=f"ec_tipo_{rid}")

                    try:
                        default_date = pd.to_datetime(row['data']).date() if not pd.isnull(
                            row['data']) else datetime.now().date()
                    except Exception:
                        default_date = datetime.now().date()

                    ec3, ec4, ec5 = st.columns(3)
                    n_data = ec3.date_input(
                        "Data", value=default_date, key=f"ec_data_{rid}")

                    lista_contas = df_contas['nome'].tolist()
                    idx_conta = lista_contas.index(row['banco']) if row.get(
                        'banco') in lista_contas else 0
                    n_conta = ec4.selectbox(
                        "Conta / Banco", lista_contas, index=idx_conta, key=f"ec_cnt_{rid}")

                    lista_cats = df_cats['nome'].tolist()
                    idx_cat = lista_cats.index(row['categoria']) if row.get(
                        'categoria') in lista_cats else 0
                    n_cat = ec5.selectbox(
                        "Categoria", lista_cats, index=idx_cat, key=f"ec_cat_{rid}")

                    n_compensado = st.checkbox(
                        "Compensado", value=is_compensado, key=f"ec_comp_{rid}")

                    btn1, btn2 = st.columns(2)
                    if btn1.button("Salvar", key=f"ec_save_{rid}", width='stretch', icon=":material/save:"):
                        cid = int(
                            df_contas[df_contas.nome == n_conta].id.values[0])
                        ctid = int(df_cats[df_cats.nome == n_cat].id.values[0])
                        v_final = -n_val if n_tipo == "Saída" else n_val
                        data_comp = datetime.now().date() if n_compensado and not is_compensado else (
                            row.get('data_compensacao') if n_compensado else None)

                        db.executar(
                            "UPDATE transacoes SET descricao=?, valor=?, data_vencimento=?, conta_id=?, categoria_id=?, compensado=?, data_compensacao=? WHERE id=? AND user_id=?",
                            (n_desc, v_final, n_data, cid, ctid,
                             n_compensado, data_comp, rid, db.get_user_id())
                        )
                        st.session_state.pop(editing_key, None)
                        st.rerun()

                    if btn2.button("Cancelar", key=f"ec_cancel_{rid}", width='stretch', icon=":material/close:"):
                        st.session_state.pop(editing_key, None)
                        st.rerun()

                    st.markdown("---")

                if not is_editing:
                    st.markdown(
                        "<hr style='margin: 0px 0px 10px 0px; padding: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

                # Expander com itens da fatura (se for pagamento de fatura)
                fatura_id_val = row.get('fatura_id')
                if fatura_id_val and not pd.isna(fatura_id_val):
                    with st.expander(f"Ver itens da fatura", expanded=False):
                        df_itens = db.buscar_itens_fatura(int(fatura_id_val))
                        if not df_itens.empty:
                            for _, item in df_itens.iterrows():
                                parc = f"({int(item['parcela_atual']):02d}/{int(item['parcela_total']):02d})"
                                st.markdown(
                                    f"&nbsp;&nbsp;• **{item['descricao']}** {parc} — "
                                    f"<span style='color:#c0392b;'>{moeda(abs(item['valor']))}</span>"
                                    f" <small style='color:gray;'>({item.get('categoria', '')})</small>",
                                    unsafe_allow_html=True
                                )
                        else:
                            st.caption("Nenhum item encontrado nesta fatura.")
