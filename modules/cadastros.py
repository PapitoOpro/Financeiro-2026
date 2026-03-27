# ==========================================
# MÓDULO: CADASTROS
# ==========================================

import streamlit as st
import pandas as pd
from database import db

class CadastrosManager:
    """Gerenciador de cadastros (contas e categorias)."""
    
    @staticmethod
    def renderizar():
        """Renderiza a página de cadastros."""
        st.header("[ ⚙️ ] Cadastros do Sistema")
        st.markdown("Gerencie suas contas bancárias, cartões e categorias de despesas.")
        
        c1, c_space, c2 = st.columns([1, 0.1, 1])
        
        # COLUNA ESQUERDA: BANCOS E CARTÕES
        with c1:
            CadastrosManager._secao_contas()
        
        # COLUNA DIREITA: CATEGORIAS
        with c2:
            CadastrosManager._secao_categorias()
    
    @staticmethod
    def _secao_contas():
        """Seção de gerenciamento de contas/bancos."""
        st.markdown("### [ 💳 ] Bancos e Cartões")
        
        # Formulário para adicionar
        with st.form("form_novo_banco", clear_on_submit=True):
            col_input, col_btn = st.columns([3, 1])
            n_banco = col_input.text_input(
                "Novo Banco/Cartão",
                label_visibility="collapsed",
                placeholder="Ex: Nubank, Itaú..."
            )
            
            if col_btn.form_submit_button("Adicionar", width='stretch'):
                if (n_banco or "").strip():
                    if db.executar(
                        "INSERT INTO contas (nome) VALUES (?)",
                        (n_banco.strip(),)
                    ):
                        st.success("✅ Banco adicionado!")
                        st.rerun()
                else:
                    st.error("❌ Digite um nome!")
        
        st.markdown("**Cadastrados:**")
        
        df_contas = db.buscar("SELECT * FROM contas ORDER BY nome")
        
        if df_contas.empty:
            st.info("ℹ️ Nenhuma conta cadastrada.")
            return
        
        for _, r in df_contas.iterrows():
            edit_flag = f"editing_conta_{r['id']}"
            input_key = f"input_conta_{r['id']}"
            save_key = f"save_conta_{r['id']}"
            cancel_key = f"cancel_conta_{r['id']}"

            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            col_nome, col_edit, col_del = st.columns([4, 1, 1])

            # If in edit mode, show inline input + save/cancel
            if st.session_state[edit_flag]:
                with col_nome:
                    novo_nome = st.text_input("Nome", value=r['nome'], key=input_key)
                with col_edit:
                    if st.button("Salvar", key=save_key, width='stretch'):
                        novo_val = (st.session_state.get(input_key) or "").strip()
                        if novo_val:
                            if db.executar(
                                "UPDATE contas SET nome=? WHERE id=?",
                                (novo_val, r['id'])
                            ):
                                st.session_state[edit_flag] = False
                                st.rerun()
                            else:
                                st.error("Erro ao salvar.")
                    if st.button("Cancelar", key=cancel_key, width='stretch'):
                        st.session_state[edit_flag] = False
                        st.rerun()
            else:
                col_nome.markdown(
                    f"<div style='padding-top: 5px; font-weight: 500;'>{r['nome']}</div>",
                    unsafe_allow_html=True
                )
                # Botão editar ativa o modo de edição
                with col_edit:
                    if st.button("✏️", key=f"edit_conta_{r['id']}", help="Editar"):
                        st.session_state[edit_flag] = True
                        st.rerun()

                # Botão deletar
                with col_del:
                    if st.button("🗑️", key=f"del_conta_{r['id']}", help="Excluir"):
                        db.executar("DELETE FROM contas WHERE id=?", (r['id'],))
                        st.rerun()

            st.markdown("<hr style='margin: 0px 0px 5px 0px;'>", unsafe_allow_html=True)
    
    @staticmethod
    def _secao_categorias():
        """Seção de gerenciamento de categorias."""
        st.markdown("### [ 🏷️ ] Categorias")
        
        # Formulário para adicionar
        with st.form("form_nova_cat", clear_on_submit=True):
            col_input, col_btn = st.columns([3, 1])
            n_cat = col_input.text_input(
                "Nova Categoria",
                label_visibility="collapsed",
                placeholder="Ex: Alimentação, Lazer..."
            )
            
            if col_btn.form_submit_button("Adicionar", width='stretch'):
                if (n_cat or "").strip():
                    if db.executar(
                        "INSERT INTO categorias (nome) VALUES (?)",
                        (n_cat.strip(),)
                    ):
                        st.success("✅ Categoria adicionada!")
                        st.rerun()
                else:
                    st.error("❌ Digite um nome!")
        
        st.markdown("**Cadastradas:**")
        
        df_cats = db.buscar("SELECT * FROM categorias ORDER BY nome")
        
        if df_cats.empty:
            st.info("ℹ️ Nenhuma categoria cadastrada.")
            return
        
        for _, r in df_cats.iterrows():
            edit_flag = f"editing_cat_{r['id']}"
            input_key = f"input_cat_{r['id']}"
            save_key = f"save_cat_{r['id']}"
            cancel_key = f"cancel_cat_{r['id']}"

            if edit_flag not in st.session_state:
                st.session_state[edit_flag] = False

            col_nome, col_edit, col_del = st.columns([4, 1, 1])

            if st.session_state[edit_flag]:
                with col_nome:
                    novo_nome = st.text_input("Nome", value=r['nome'], key=input_key)
                with col_edit:
                    if st.button("Salvar", key=save_key, width='stretch'):
                        novo_val = (st.session_state.get(input_key) or "").strip()
                        if novo_val:
                            if db.executar(
                                "UPDATE categorias SET nome=? WHERE id=?",
                                (novo_val, r['id'])
                            ):
                                st.session_state[edit_flag] = False
                                st.rerun()
                            else:
                                st.error("Erro ao salvar.")
                    if st.button("Cancelar", key=cancel_key, width='stretch'):
                        st.session_state[edit_flag] = False
                        st.rerun()
            else:
                col_nome.markdown(
                    f"<div style='padding-top: 5px; font-weight: 500;'>{r['nome']}</div>",
                    unsafe_allow_html=True
                )
                with col_edit:
                    if st.button("✏️", key=f"edit_cat_{r['id']}", help="Editar"):
                        st.session_state[edit_flag] = True
                        st.rerun()

                # Botão deletar
                with col_del:
                    if st.button("🗑️", key=f"del_cat_{r['id']}", help="Excluir"):
                        db.executar("DELETE FROM categorias WHERE id=?", (r['id'],))
                        st.rerun()

            st.markdown("<hr style='margin: 0px 0px 5px 0px;'>", unsafe_allow_html=True)
