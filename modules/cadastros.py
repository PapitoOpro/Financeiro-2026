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

        tab_cats, tab_contas = st.tabs([" Categorias e Subcategorias", " Bancos e Cartões"])

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

        # Barra global de orçamento 
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
                    <strong> Orçamento Distribuído</strong>
                    <strong style="color:{barra_cor};">{total_pct:.0f}% / 100%</strong>
                </div>
                <div style="background:#e0e0e0; border-radius:6px; height:14px;">
                    <div style="background:{barra_cor}; width:{barra_width}%; height:14px; border-radius:6px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Nova Categoria Macro 
        st.markdown("### Categorias Macro (Orçamento)")
        with st.form("form_nova_cat_macro", clear_on_submit=True):
            c1, c2, c3, c_tipo, c4 = st.columns([3, 1, 1, 1.2, 1])
            n_nome = c1.text_input("Nome da Categoria", placeholder="Ex: Moradia, Lazer...",
                                   label_visibility="collapsed")
            n_pct = c2.number_input("Meta %", min_value=0, max_value=100, value=0,
                                    label_visibility="collapsed")
            n_icone = c3.text_input("Ícone", value="", label_visibility="collapsed")
            n_tipo = c_tipo.selectbox("Tipo", ["Saída", "Entrada"], label_visibility="collapsed")

            if c4.form_submit_button("Adicionar"):
                if (n_nome or "").strip():
                    tipo_val = "entrada" if n_tipo == "Entrada" else "saida"
                    db.executar(
                        "INSERT INTO categorias (nome, percentual_meta, icone, tipo, ativa, user_id) "
                        "VALUES (%s, %s, %s, %s, TRUE, %s) ON CONFLICT (nome, user_id) DO UPDATE "
                        "SET percentual_meta = EXCLUDED.percentual_meta, icone = EXCLUDED.icone, tipo = EXCLUDED.tipo",
                        (n_nome.strip(), n_pct, n_icone.strip(), tipo_val, user_id)
                    )
                    st.rerun()
                else:
                    st.error(" Digite um nome!")

        # Lista de Categorias Macro com suas Subcategorias 
        if df_cats.empty:
            st.info("ℹ Nenhuma categoria cadastrada. Crie uma ou execute o Onboarding.")
            return

        # Mostrar/ocultar arquivadas
        mostrar_arquivadas = st.checkbox("Mostrar categorias arquivadas", value=False)
        if mostrar_arquivadas:
            df_arquivadas = db.buscar(
                "SELECT * FROM categorias WHERE user_id = %s AND ativa = FALSE ORDER BY nome",
                (user_id,)
            )
            if not df_arquivadas.empty:
                st.markdown("##### Categorias Arquivadas")
                for _, r in df_arquivadas.iterrows():
                    col_nome, col_restore = st.columns([4, 1])
                    icone = r.get('icone', '') or ''
                    col_nome.markdown(f"~~{icone} {r['nome']}~~")
                    if col_restore.button(" Restaurar", key=f"restore_cat_{r['id']}"):
                        db.executar(
                            "UPDATE categorias SET ativa = TRUE WHERE id = %s AND user_id = %s",
                            (r['id'], user_id)
                        )
                        st.rerun()

        st.markdown("---")

        for _, cat in df_cats.iterrows():
            cat_id = int(cat['id'])
            icone = cat.get('icone', '') or ''
            pct_meta = float(cat.get('percentual_meta', 0) or 0)
            edit_flag = f"editing_cat_macro_{cat_id}"

            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            tipo_cat = cat.get('tipo', 'saida') or 'saida'
            tipo_label = "Entrada" if tipo_cat == 'entrada' else "Saída"
            tipo_cor = "#2ecc71" if tipo_cat == 'entrada' else "#e74c3c"

            # Header da Categoria 
            if not st.session_state[edit_flag]:
                col_icon, col_nome, col_tipo_badge, col_pct, col_edit, col_archive = st.columns([0.5, 2.5, 1, 1.5, 0.5, 0.5])

                col_icon.markdown(f"<div style='font-size:22px; padding-top:5px;'>{icone}</div>",
                                  unsafe_allow_html=True)
                col_nome.markdown(f"**{cat['nome']}**")
                col_tipo_badge.markdown(
                    f"<span style='background:{tipo_cor}; color:white; padding:2px 8px; "
                    f"border-radius:4px; font-size:11px;'>{tipo_label}</span>",
                    unsafe_allow_html=True
                )
                col_pct.markdown(
                    f"<div style='background:#e0e0e0; border-radius:6px; height:20px; margin-top:5px;'>"
                    f"<div style='background:#3498db; width:{min(pct_meta, 100)}%; height:20px; "
                    f"border-radius:6px; text-align:center; color:white; font-size:11px; "
                    f"line-height:20px;'>{pct_meta:.0f}%</div></div>",
                    unsafe_allow_html=True
                )
                with col_edit:
                    if st.button("\u200b", key=f"edit_cat_{cat_id}", help="Editar", icon=":material/edit:"):
                        st.session_state[edit_flag] = True
                        st.rerun()
                with col_archive:
                    if st.button("\u200b", key=f"archive_cat_{cat_id}", help="Arquivar", icon=":material/archive:"):
                        db.executar(
                            "UPDATE categorias SET ativa = FALSE WHERE id = %s AND user_id = %s",
                            (cat_id, user_id)
                        )
                        st.rerun()
            else:
                # Modo edição da Categoria 
                c1, c2, c3, c_tipo_edit = st.columns([3, 1, 1, 1.2])
                novo_nome = c1.text_input("Nome", value=cat['nome'], key=f"ec_cname_{cat_id}")
                novo_pct = c2.number_input("Meta %", value=int(pct_meta), min_value=0,
                                           max_value=100, key=f"ec_cpct_{cat_id}")
                novo_icone = c3.text_input("Ícone", value=icone, key=f"ec_cicon_{cat_id}")
                idx_tipo = 0 if tipo_cat == 'saida' else 1
                novo_tipo = c_tipo_edit.selectbox("Tipo", ["Saída", "Entrada"], index=idx_tipo, key=f"ec_ctipo_{cat_id}")

                bc1, bc2 = st.columns(2)
                if bc1.button(" Salvar", key=f"save_cat_{cat_id}", width='stretch'):
                    tipo_val_edit = "entrada" if novo_tipo == "Entrada" else "saida"
                    db.executar(
                        "UPDATE categorias SET nome=%s, percentual_meta=%s, icone=%s, tipo=%s "
                        "WHERE id=%s AND user_id=%s",
                        (novo_nome.strip(), novo_pct, novo_icone.strip(), tipo_val_edit, cat_id, user_id)
                    )
                    st.session_state[edit_flag] = False
                    st.rerun()
                if bc2.button(" Cancelar", key=f"cancel_cat_{cat_id}", width='stretch'):
                    st.session_state[edit_flag] = False
                    st.rerun()

            # Subcategorias desta Categoria 
            df_subs = db.buscar(
                "SELECT * FROM subcategorias WHERE categoria_id = %s AND user_id = %s AND ativa = TRUE ORDER BY nome",
                (cat_id, user_id)
            )

            with st.expander(f"Subcategorias de {cat['nome']} ({len(df_subs) if not df_subs.empty else 0})", expanded=False):
                # Variável no session_state para lembrar qual expander deve ficar aberto
                if "expander_aberto" not in st.session_state:
                    st.session_state["expander_aberto"] = None

        # Loop passando por cada categoria macro
        for idx, row in df_cats.iterrows():
            cat_id = row['id']
            cat_nome = row['nome']
            
            # Verifica se ESTA categoria é a que deve começar expandida
            deve_expandir = (st.session_state["expander_aberto"] == cat_id)
            
            # 1. O Expander com o estado de abertura dinâmico
            with st.expander(f"📂 {cat_nome}", expanded=deve_expandir):
                
                # 2. Busca e lista as subcategorias que JÁ EXISTEM
                # 2. Busca e lista as subcategorias que JÁ EXISTEM (com filtro anti-duplicidade)
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
                        c_nome.markdown(f" ↳ {sub['nome']}")
                        edit_sub_flag = f"editing_sub_{sub_id}"

                        # Lógica de Edição Inline
                        if st.session_state.get(edit_sub_flag, False):
                            novo_sub_nome = st.text_input(
                                "Nome", value=sub['nome'], key=f"es_name_{sub_id}"
                            )
                            bs1, bs2 = st.columns(2)
                            if bs1.button("", key=f"save_sub_{sub_id}", icon=":material/check:", help="Salvar"):
                                db.executar(
                                    "UPDATE subcategorias SET nome=%s WHERE id=%s AND user_id=%s",
                                    (novo_sub_nome.strip(), sub_id, user_id)
                                )
                                st.session_state[edit_sub_flag] = False
                                st.session_state["expander_aberto"] = cat_id # Mantém aberto
                                st.rerun()
                            if bs2.button("", key=f"cancel_sub_{sub_id}", icon=":material/close:", help="Cancelar"):
                                st.session_state[edit_sub_flag] = False
                                st.session_state["expander_aberto"] = cat_id # Mantém aberto
                                st.rerun()
                        else:
                            with c_edit:
                                if st.button("\u200b", key=f"edit_sub_{sub_id}", help="Editar", icon=":material/edit:"):
                                    st.session_state[edit_sub_flag] = True
                                    st.session_state["expander_aberto"] = cat_id # Mantém aberto
                                    st.rerun()
                            with c_archive:
                                if st.button("\u200b", key=f"archive_sub_{sub_id}", help="Arquivar", icon=":material/archive:"):
                                    db.executar(
                                        "UPDATE subcategorias SET ativa = FALSE WHERE id=%s AND user_id=%s",
                                        (sub_id, user_id)
                                    )
                                    st.session_state["expander_aberto"] = cat_id # Mantém aberto
                                    st.rerun()
                else:
                    st.caption("Nenhuma subcategoria cadastrada.")
                
                st.markdown("---") 
                
                # 3. Formulário SEGURO para nova subcategoria
                with st.form(f"form_add_sub_{cat_id}", clear_on_submit=True, border=False):
                    col_sub_input, col_sub_btn = st.columns([4, 1])
                    
                    nova_sub = col_sub_input.text_input(
                        "Nova subcategoria", 
                        placeholder="Ex: Padaria, Uber, Netflix...",
                        label_visibility="collapsed"
                    )
                    
                    # Usamos form_submit_button para aproveitar a limpeza automática
                    if col_sub_btn.form_submit_button("", icon=":material/add:", help="Inserir subcategoria", use_container_width=True):
                        if (nova_sub or "").strip():
                            db.executar(
                                "INSERT INTO subcategorias (nome, categoria_id, ativa, user_id) "
                                "VALUES (%s, %s, TRUE, %s) ON CONFLICT (nome, categoria_id, user_id) DO NOTHING",
                                (nova_sub.strip(), cat_id, user_id)
                            )
                            # Define que esta categoria deve ficar aberta na próxima recarga
                            st.session_state["expander_aberto"] = cat_id
                            st.rerun()

            st.markdown("<hr style='margin:5px 0 10px 0;'>", unsafe_allow_html=True)

    # ================================================================
    # CONTAS / BANCOS (mantido do original)
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
            if col_btn.form_submit_button("Adicionar", width='stretch'):
                if (n_banco or "").strip():
                    if db.executar(
                        "INSERT INTO contas (nome, user_id) VALUES (?, ?)",
                        (n_banco.strip(), user_id)
                    ):
                        st.success(" Banco adicionado!")
                        st.rerun()
                else:
                    st.error(" Digite um nome!")

        st.markdown("**Cadastrados:**")

        df_contas = db.buscar(
            f"SELECT * FROM contas WHERE user_id = {user_id} ORDER BY nome"
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
                    novo_nome = st.text_input("Nome", value=r['nome'], key=input_key)
                with col_edit:
                    if st.button("Salvar", key=save_key, width='stretch'):
                        novo_val = (st.session_state.get(input_key) or "").strip()
                        if novo_val:
                            if db.executar(
                                "UPDATE contas SET nome=? WHERE id=? AND user_id=?",
                                (novo_val, r['id'], user_id)
                            ):
                                st.session_state[edit_flag] = False
                                st.rerun()
                    if st.button("Cancelar", key=cancel_key, width='stretch'):
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
                            "DELETE FROM contas WHERE id=? AND user_id=?",
                            (r['id'], user_id)
                        )
                        st.rerun()
