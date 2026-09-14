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

        with st.container(border=True):
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
                    <span style="font-weight:600; font-size:1.05rem;">📊 Orçamento Distribuído</span>
                    <span style="font-weight:700; font-size:1.1rem; color:{barra_cor};">{total_pct:.0f}%
                        <span style="opacity:0.6; font-weight:400; font-size:0.85rem;">/ 100%</span></span>
                </div>
                <div style="background:rgba(128,128,128,0.25); border-radius:8px; height:10px;">
                    <div style="background:{barra_cor}; width:{barra_width}%; height:10px; border-radius:8px;"></div>
                </div>
            """, unsafe_allow_html=True)

        st.write("")

        # =========================
        # NOVA CATEGORIA MACRO
        # =========================
        with st.expander("➕ Nova categoria macro", expanded=False):
            with st.form("form_nova_cat_macro", clear_on_submit=True):
                c1, c2 = st.columns([3, 1.2])
                n_nome = c1.text_input("Nome", placeholder="Ex: Alimentação, Moradia...")
                n_tipo = c2.selectbox("Tipo", ["Saída", "Entrada"])

                c3, c4 = st.columns([3, 1.2])
                n_icone = c3.text_input("Ícone (emoji, opcional)", "", placeholder="Ex: 🍔")
                n_pct = c4.number_input("Meta do orçamento (%)", 0, 100, 0)

                if st.form_submit_button("Adicionar categoria", width="stretch", type="primary"):
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

        st.markdown("##### Categorias cadastradas")

        # =========================
        # LOOP PRINCIPAL (MACRO + SUB)
        # =========================
        for _, cat in df_cats.iterrows():
            cat_id = int(cat['id'])
            nome = cat['nome']
            icone = cat.get('icone', '') or '📁'
            pct = float(cat.get('percentual_meta', 0) or 0)
            tipo = cat.get('tipo', 'saida')

            tipo_label = "Entrada" if tipo == "entrada" else "Saída"
            tipo_cor = "#1e8e5a" if tipo == "entrada" else "#c0392b"

            edit_flag = f"edit_cat_{cat_id}"
            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            # Início do Container (Cartão) da Categoria
            with st.container(border=True):
                # HEADER DA CATEGORIA MACRO
                if not st.session_state[edit_flag]:
                    col_titulo, col_barra, col_edit, col_del = st.columns([2.8, 2.2, 0.45, 0.45])

                    col_titulo.markdown(
                        f"<div style='padding-top:2px;'>"
                        f"<span style='font-size:1.3rem; vertical-align:middle;'>{icone}</span> "
                        f"<strong style='font-size:1.02rem; vertical-align:middle;'>{nome}</strong><br>"
                        f"<span style='background:{tipo_cor}; color:#fff; padding:1px 9px; border-radius:10px; "
                        f"font-size:11px; font-weight:600;'>{tipo_label}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    col_barra.markdown(
                        f"<div style='padding-top:8px;'>"
                        f"<div style='display:flex; justify-content:space-between; font-size:12px; opacity:0.75; margin-bottom:3px;'>"
                        f"<span>Meta do orçamento</span><span style='font-weight:700; opacity:1;'>{pct:.0f}%</span></div>"
                        f"<div style='background:rgba(128,128,128,0.25); border-radius:6px; height:8px;'>"
                        f"<div style='background:#3498db; width:{max(pct, 2)}%; height:8px; border-radius:6px;'></div>"
                        f"</div></div>",
                        unsafe_allow_html=True
                    )

                    with col_edit:
                        st.write("")
                        if st.button("​", key=f"btn_edit_{cat_id}", icon=":material/edit:", help="Editar categoria"):
                            st.session_state[edit_flag] = True
                            st.rerun()

                    with col_del:
                        st.write("")
                        if st.button("​", key=f"btn_del_{cat_id}", icon=":material/delete:", help="Excluir categoria"):
                            db.executar(
                                "UPDATE categorias SET ativa = FALSE WHERE id=%s AND user_id=%s",
                                (cat_id, user_id)
                            )
                            st.rerun()

                else:
                    c1, c2 = st.columns([3, 1.2])
                    novo_nome = c1.text_input("Nome", value=nome, key=f"edit_nome_{cat_id}")
                    novo_tipo = c2.selectbox(
                        "Tipo", ["Saída", "Entrada"], index=0 if tipo == "saida" else 1, key=f"edit_tipo_{cat_id}"
                    )
                    c3, c4 = st.columns([3, 1.2])
                    novo_icone = c3.text_input("Ícone", value=icone, key=f"edit_icone_{cat_id}")
                    novo_pct = c4.number_input("Meta (%)", 0, 100, int(pct), key=f"edit_pct_{cat_id}")

                    b1, b2 = st.columns(2)
                    if b1.button("Salvar", key=f"save_{cat_id}", use_container_width=True, type="primary"):
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

                with st.expander(f"↳ Subcategorias de {nome}", expanded=deve_expandir):

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
                            edit_sub_flag = f"editing_sub_{sub_id}"

                            if st.session_state.get(edit_sub_flag, False):
                                c_nome, c_save, c_cancel = st.columns([4, 0.45, 0.45])
                                novo_sub_nome = c_nome.text_input(
                                    "Nome", value=sub['nome'], key=f"es_name_{sub_id}", label_visibility="collapsed"
                                )
                                if c_save.button("", key=f"save_sub_{sub_id}", icon=":material/check:", help="Salvar"):
                                    db.executar(
                                        "UPDATE subcategorias SET nome=%s WHERE id=%s AND user_id=%s",
                                        (novo_sub_nome.strip(), sub_id, user_id)
                                    )
                                    st.session_state[edit_sub_flag] = False
                                    st.session_state["expander_aberto"] = cat_id
                                    st.rerun()
                                if c_cancel.button("", key=f"cancel_sub_{sub_id}", icon=":material/close:", help="Cancelar"):
                                    st.session_state[edit_sub_flag] = False
                                    st.session_state["expander_aberto"] = cat_id
                                    st.rerun()
                            else:
                                c_nome, c_edit, c_archive = st.columns([4, 0.45, 0.45])
                                c_nome.markdown(
                                    f"<div style='padding-top:6px; font-size:0.92rem;'>🔸 {sub['nome']}</div>",
                                    unsafe_allow_html=True
                                )
                                with c_edit:
                                    if st.button("​", key=f"edit_sub_{sub_id}", help="Editar", icon=":material/edit:"):
                                        st.session_state[edit_sub_flag] = True
                                        st.session_state["expander_aberto"] = cat_id
                                        st.rerun()
                                with c_archive:
                                    if st.button("​", key=f"archive_sub_{sub_id}", help="Arquivar", icon=":material/archive:"):
                                        db.executar(
                                            "UPDATE subcategorias SET ativa = FALSE WHERE id=%s AND user_id=%s",
                                            (sub_id, user_id)
                                        )
                                        st.session_state["expander_aberto"] = cat_id
                                        st.rerun()
                    else:
                        st.caption("Nenhuma subcategoria cadastrada.")

                    st.markdown("<hr style='margin:8px 0; opacity:0.2;'>", unsafe_allow_html=True)

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

    # ================================================================
    # CONTAS / BANCOS
    # ================================================================
    @staticmethod
    def _secao_contas():
        """Seção de gerenciamento de contas/bancos."""
        user_id = db.get_user_id()

        with st.expander("➕ Novo banco/cartão", expanded=False):
            with st.form("form_novo_banco", clear_on_submit=True):
                col_input, col_digitos = st.columns([3, 1.4])
                n_banco = col_input.text_input(
                    "Nome do banco/cartão", placeholder="Ex: Nubank, Itaú Master..."
                )
                n_digitos = col_digitos.text_input(
                    "Últimos dígitos (opcional)",
                    placeholder="Ex: 4553",
                    help="Últimos dígitos impressos no cartão/fatura — usado para detectar "
                         "automaticamente esta conta ao importar um PDF.",
                )
                if st.form_submit_button("Adicionar", width="stretch", type="primary"):
                    if (n_banco or "").strip():
                        if db.executar(
                            "INSERT INTO contas (nome, ultimos_digitos, user_id) VALUES (%s, %s, %s)",
                            (n_banco.strip(), (n_digitos or "").strip() or None, user_id)
                        ):
                            st.success("✅ Banco adicionado!")
                            st.rerun()
                    else:
                        st.error("⚠️ Digite um nome!")

        st.write("")
        df_contas = db.buscar(
            "SELECT * FROM contas WHERE user_id = %s ORDER BY nome",
            (user_id,)
        )

        if df_contas.empty:
            st.info("ℹ️ Nenhuma conta cadastrada.")
            return

        st.markdown("##### Bancos e cartões cadastrados")

        for _, r in df_contas.iterrows():
            edit_flag = f"editing_conta_{r['id']}"
            input_key = f"input_conta_{r['id']}"
            save_key = f"save_conta_{r['id']}"
            cancel_key = f"cancel_conta_{r['id']}"
            digitos_key = f"input_digitos_{r['id']}"

            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            with st.container(border=True):
                col_nome, col_digitos, col_edit, col_del = st.columns([3, 1.4, 0.45, 0.45])

                if st.session_state[edit_flag]:
                    with col_nome:
                        novo_nome = st.text_input("Nome", value=r['nome'], key=input_key, label_visibility="collapsed")
                    with col_digitos:
                        novo_digitos = st.text_input(
                            "Últimos dígitos", value=r.get('ultimos_digitos') or "",
                            key=digitos_key, label_visibility="collapsed",
                            placeholder="Últimos dígitos",
                        )
                    with col_edit:
                        if st.button("​", key=save_key, icon=":material/check:", help="Salvar"):
                            novo_val = (st.session_state.get(input_key) or "").strip()
                            novo_digitos_val = (st.session_state.get(digitos_key) or "").strip()
                            if novo_val:
                                if db.executar(
                                    "UPDATE contas SET nome=%s, ultimos_digitos=%s WHERE id=%s AND user_id=%s",
                                    (novo_val, novo_digitos_val or None, r['id'], user_id)
                                ):
                                    st.session_state[edit_flag] = False
                                    st.rerun()
                    with col_del:
                        if st.button("​", key=cancel_key, icon=":material/close:", help="Cancelar"):
                            st.session_state[edit_flag] = False
                            st.rerun()
                else:
                    digitos_atual = r.get('ultimos_digitos') or ""
                    col_nome.markdown(
                        f"<div style='padding-top:6px; font-weight:600;'>🏦 {r['nome']}</div>",
                        unsafe_allow_html=True
                    )
                    col_digitos.markdown(
                        f"<div style='padding-top:6px; opacity:0.7; font-size:13px;'>"
                        f"{'•••• ' + digitos_atual if digitos_atual else '— sem dígitos —'}</div>",
                        unsafe_allow_html=True
                    )
                    with col_edit:
                        if st.button("​", key=f"edit_conta_{r['id']}", help="Editar", icon=":material/edit:"):
                            st.session_state[edit_flag] = True
                            st.rerun()
                    with col_del:
                        if st.button("​", key=f"del_conta_{r['id']}", help="Excluir", icon=":material/delete:"):
                            db.executar(
                                "DELETE FROM contas WHERE id=%s AND user_id=%s",
                                (r['id'], user_id)
                            )
                            st.rerun()
