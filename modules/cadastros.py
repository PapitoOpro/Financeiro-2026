# ==========================================
# MÓDULO: CADASTROS (Categorias Macro/Micro + Contas)
# ==========================================

import streamlit as st
import pandas as pd
from database import db

class CadastrosManager:
    """Gerenciador de cadastros (contas, categorias macro e subcategorias)."""

    @staticmethod
    def renderizar():
        """Renderiza a página de cadastros."""
        st.header("Cadastros do Sistema")
        st.markdown("Gerencie contas bancárias, categorias macro (orçamento) e subcategorias (operacional).")

        tab_cats, tab_contas = st.tabs(["📋 Categorias e Subcategorias", "🏦 Bancos e Cartões"])

        with tab_cats:
            CadastrosManager._secao_categorias_completa()

        with tab_contas:
            CadastrosManager._secao_contas()

    # ================================================================
    # CATEGORIAS MACRO + SUBCATEGORIAS
    # ================================================================
    @staticmethod
    def _secao_categorias_completa():
        """Seção unificada: categorias macro com porcentagem + subcategorias."""
        user_id = db.get_user_id()

        # =========================
        # BUSCA CATEGORIAS MACRO
        # =========================
        df_cats = db.buscar(
            "SELECT * FROM categorias WHERE user_id = %s AND ativa = TRUE ORDER BY nome",
            (user_id,)
        )

        total_pct = 0
        if not df_cats.empty and 'percentual_meta' in df_cats.columns:
            total_pct = df_cats['percentual_meta'].fillna(0).sum()

        barra_cor = "#2ecc71" if total_pct == 100 else ("#f39c12" if total_pct < 100 else "#e74c3c")
        barra_width = min(float(total_pct), 100)

        st.markdown(f"""
            <div style="background:#f1f2f6; border-radius:10px; padding:12px 15px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <strong>Orçamento Distribuído</strong>
                    <strong style="color:{barra_cor};">{total_pct:.0f}% / 100%</strong>
                </div>
                <div style="background:#e0e0e0; border-radius:6px; height:14px;">
                    <div style="background:{barra_cor}; width:{barra_width}%; height:14px; border-radius:6px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # =========================
        # NOVA CATEGORIA MACRO
        # =========================
        st.markdown("### Categorias Macro (Orçamento)")
        with st.form("form_nova_cat_macro", clear_on_submit=True):
            c1, c2, c3, c_tipo, c4 = st.columns([3, 1, 1, 1.2, 1])
            n_nome = c1.text_input("Nome", label_visibility="collapsed")
            n_pct = c2.number_input("Meta %", 0, 100, 0, label_visibility="collapsed")
            n_icone = c3.text_input("Ícone", "", label_visibility="collapsed")
            n_tipo = c_tipo.selectbox("Tipo", ["Saída", "Entrada"], label_visibility="collapsed")

            if c4.form_submit_button("Adicionar"):
                if (n_nome or "").strip():
                    tipo_val = "entrada" if n_tipo == "Entrada" else "saida"
                    db.executar(
                        "INSERT INTO categorias (nome, percentual_meta, icone, tipo, ativa, user_id) "
                        "VALUES (%s, %s, %s, %s, TRUE, %s) "
                        "ON CONFLICT (nome, user_id) DO UPDATE "
                        "SET percentual_meta = EXCLUDED.percentual_meta, icone = EXCLUDED.icone, tipo = EXCLUDED.tipo",
                        (n_nome.strip(), n_pct, n_icone.strip(), tipo_val, user_id)
                    )
                    st.rerun()
                else:
                    st.error("Digite um nome!")

        if df_cats.empty:
            st.info("Nenhuma categoria cadastrada.")
            return

        # =========================
        # CONTROLE EXPANDER
        # =========================
        if "expander_aberto" not in st.session_state:
            st.session_state["expander_aberto"] = None

        st.markdown("---")

        # =========================
        # LOOP PRINCIPAL (MACRO + SUB)
        # =========================
        for _, cat in df_cats.iterrows():
            cat_id = int(cat['id'])
            nome = cat['nome']
            icone = cat.get('icone', '') or ''
            pct = float(cat.get('percentual_meta', 0) or 0)
            tipo = cat.get('tipo', 'saida')

            tipo_label = "Entrada" if tipo == "entrada" else "Saída"
            tipo_cor = "#2ecc71" if tipo == "entrada" else "#e74c3c"

            edit_flag = f"edit_cat_{cat_id}"
            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            # Início do Container (Cartão) da Categoria
            with st.container():
                # HEADER DA CATEGORIA MACRO
                if not st.session_state[edit_flag]:
                    col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2.5, 1, 1.5, 0.5, 0.5])

                    col1.markdown(f"<div style='font-size:22px'>{icone}</div>", unsafe_allow_html=True)
                    col2.markdown(f"<div style='padding-top: 4px;'><strong>{nome}</strong></div>", unsafe_allow_html=True)
                    col3.markdown(
                        f"<div style='padding-top: 4px;'><span style='background:{tipo_cor}; color:gray; padding:2px 8px; border-radius:4px; font-size:14px;'>{tipo_label}</span></div>",
                        unsafe_allow_html=True
                    )
                    col4.markdown(
                        f"<div style='margin-top: 6px; background:#e0e0e0; border-radius:6px; position:relative; min-height: 20px;'>"
                        f"<div style='background:#3498db; width:{pct}%; min-width: 30px; height: 100%; border-radius:6px; color:gray; text-align:center; font-weight:bold; white-space:nowrap; position:absolute; top:0; left:0; display:flex; align-items:center; justify-content:center; font-size:12px;'>"
                        f"{pct:.0f}%</div></div>",
                        unsafe_allow_html=True
                    )

                    with col5:
                        if st.button("\u200b", key=f"btn_edit_{cat_id}", icon=":material/edit:", help="Editar categoria"):
                            st.session_state[edit_flag] = True
                            st.rerun()

                    with col6:
                        if st.button("\u200b", key=f"btn_del_{cat_id}", icon=":material/delete:", help="Excluir categoria"):
                            db.executar(
                                "UPDATE categorias SET ativa = FALSE WHERE id=%s AND user_id=%s",
                                (cat_id, user_id)
                            )
                            st.rerun()

                else:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1.2])
                    novo_nome = c1.text_input("Nome", value=nome, label_visibility="collapsed")
                    novo_pct = c2.number_input("Meta %", 0, 100, int(pct), label_visibility="collapsed")
                    novo_icone = c3.text_input("Ícone", value=icone, label_visibility="collapsed")
                    novo_tipo = c4.selectbox("Tipo", ["Saída", "Entrada"], index=0 if tipo == "saida" else 1, label_visibility="collapsed")

                    b1, b2 = st.columns([1, 1])
                    if b1.button("Salvar", key=f"save_{cat_id}", use_container_width=True):
                        db.executar(
                            "UPDATE categorias SET nome=%s, percentual_meta=%s, icone=%s, tipo=%s WHERE id=%s AND user_id=%s",
                            (novo_nome.strip(), novo_pct, novo_icone.strip(),
                             "entrada" if novo_tipo == "Entrada" else "saida",
                             cat_id, user_id)
                        )
                        st.session_state[edit_flag] = False
                        st.rerun()

                    if b2.button("Cancelar", key=f"cancel_{cat_id}", use_container_width=True):
                        st.session_state[edit_flag] = False
                        st.rerun()

                # SUBCATEGORIAS (Dentro do Container)
                deve_expandir = (st.session_state.get("expander_aberto") == cat_id)
                
                with st.expander(f"↳ Gerenciar subcategorias de {nome}", expanded=deve_expandir):
                    
                    df_subs = db.buscar(
                        """
                        SELECT MIN(id) as id, nome
                        FROM subcategorias
                        WHERE categoria_id = %s AND user_id = %s AND ativa = TRUE
                        GROUP BY nome
                        ORDER BY nome
                        """,
                        (cat_id, user_id)
                    )
                    
                    if not df_subs.empty:
                        for _, sub in df_subs.iterrows():
                            sub_id = int(sub['id'])
                            c_nome, c_edit, c_archive = st.columns([4, 0.5, 0.5])
                            c_nome.markdown(f"<div style='padding-top: 6px;'>🔸 {sub['nome']}</div>", unsafe_allow_html=True)
                            edit_sub_flag = f"editing_sub_{sub_id}"

                            if st.session_state.get(edit_sub_flag, False):
                                novo_sub_nome = st.text_input(
                                    "Nome", value=sub['nome'], key=f"es_name_{sub_id}", label_visibility="collapsed"
                                )
                                bs1, bs2 = st.columns(2)
                                if bs1.button("", key=f"save_sub_{sub_id}", icon=":material/check:", help="Salvar"):
                                    db.executar(
                                        "UPDATE subcategorias SET nome=%s WHERE id=%s AND user_id=%s",
                                        (novo_sub_nome.strip(), sub_id, user_id)
                                    )
                                    st.session_state[edit_sub_flag] = False
                                    st.session_state["expander_aberto"] = cat_id
                                    st.rerun()
                                if bs2.button("", key=f"cancel_sub_{sub_id}", icon=":material/close:", help="Cancelar"):
                                    st.session_state[edit_sub_flag] = False
                                    st.session_state["expander_aberto"] = cat_id
                                    st.rerun()
                            else:
                                with c_edit:
                                    if st.button("\u200b", key=f"edit_sub_{sub_id}", help="Editar", icon=":material/edit:"):
                                        st.session_state[edit_sub_flag] = True
                                        st.session_state["expander_aberto"] = cat_id
                                        st.rerun()
                                with c_archive:
                                    if st.button("\u200b", key=f"archive_sub_{sub_id}", help="Arquivar", icon=":material/archive:"):
                                        db.executar(
                                            "UPDATE subcategorias SET ativa = FALSE WHERE id=%s AND user_id=%s",
                                            (sub_id, user_id)
                                        )
                                        st.session_state["expander_aberto"] = cat_id
                                        st.rerun()
                    else:
                        st.caption("Nenhuma subcategoria cadastrada.")
                    
                    st.markdown("---") 
                    
                    with st.form(f"form_add_sub_{cat_id}", clear_on_submit=True, border=False):
                        col_sub_input, col_sub_btn = st.columns([4, 1])
                        
                        nova_sub = col_sub_input.text_input(
                            "Nova subcategoria", 
                            placeholder="Ex: Padaria, Uber, Netflix...",
                            label_visibility="collapsed"
                        )
                        
                        if col_sub_btn.form_submit_button("", icon=":material/add:", help="Inserir subcategoria", use_container_width=True):
                            if (nova_sub or "").strip():
                                db.executar(
                                    "INSERT INTO subcategorias (nome, categoria_id, ativa, user_id) "
                                    "VALUES (%s, %s, TRUE, %s) ON CONFLICT (nome, categoria_id, user_id) DO NOTHING",
                                    (nova_sub.strip(), cat_id, user_id)
                                )
                                st.session_state["expander_aberto"] = cat_id
                                st.rerun()

            # Divisor visual entre os "cartões" das categorias macro
            st.divider()

    # ================================================================
    # CONTAS / BANCOS
    # ================================================================
    @staticmethod
    def _secao_contas():
        """Seção de gerenciamento de contas/bancos."""
        st.markdown("### Bancos e Cartões")
        user_id = db.get_user_id()

        with st.form("form_novo_banco", clear_on_submit=True):
            col_input, col_btn = st.columns([3, 1])
            n_banco = col_input.text_input(
                "Novo Banco/Cartão", label_visibility="collapsed",
                placeholder="Ex: Nubank, Itaú..."
            )
            if col_btn.form_submit_button("Adicionar", use_container_width=True):
                if (n_banco or "").strip():
                    if db.executar(
                        "INSERT INTO contas (nome, user_id) VALUES (%s, %s)",
                        (n_banco.strip(), user_id)
                    ):
                        st.success("✅ Banco adicionado!")
                        st.rerun()
                else:
                    st.error("⚠️ Digite um nome!")

        st.markdown("**Cadastrados:**")

        df_contas = db.buscar(
            "SELECT * FROM contas WHERE user_id = %s ORDER BY nome",
            (user_id,)
        )

        if df_contas.empty:
            st.info("ℹ Nenhuma conta cadastrada.")
            return

        for _, r in df_contas.iterrows():
            edit_flag = f"editing_conta_{r['id']}"
            input_key = f"input_conta_{r['id']}"
            save_key = f"save_conta_{r['id']}"
            cancel_key = f"cancel_conta_{r['id']}"

            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            col_nome, col_edit, col_del = st.columns([4, 0.5, 0.5])

            if st.session_state[edit_flag]:
                with col_nome:
                    novo_nome = st.text_input("Nome", value=r['nome'], key=input_key, label_visibility="collapsed")
                with col_edit:
                    if st.button("Salvar", key=save_key, use_container_width=True):
                        novo_val = (st.session_state.get(input_key) or "").strip()
                        if novo_val:
                            if db.executar(
                                "UPDATE contas SET nome=%s WHERE id=%s AND user_id=%s",
                                (novo_val, r['id'], user_id)
                            ):
                                st.session_state[edit_flag] = False
                                st.rerun()
                with col_del:
                    if st.button("Cancelar", key=cancel_key, use_container_width=True):
                        st.session_state[edit_flag] = False
                        st.rerun()
            else:
                col_nome.markdown(
                    f"<div style='line-height: 1.8; font-weight: 500;'>{r['nome']}</div>",
                    unsafe_allow_html=True
                )
                with col_edit:
                    if st.button("\u200b", key=f"edit_conta_{r['id']}", help="Editar", icon=":material/edit:"):
                        st.session_state[edit_flag] = True
                        st.rerun()
                with col_del:
                    if st.button("\u200b", key=f"del_conta_{r['id']}", help="Excluir", icon=":material/delete:"):
                        db.executar(
                            "DELETE FROM contas WHERE id=%s AND user_id=%s",
                            (r['id'], user_id)
                        )
                        st.rerun()