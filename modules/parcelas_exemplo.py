# ==========================================
# MÓDULO: PROJEÇÃO DE GASTOS (EXEMPLO)
# ==========================================

import streamlit as st
import pandas as pd
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import db
import plotly.express as px
import plotly.graph_objects as go
from utils import moeda, processar_fatura, processar_texto_colado, get_cor_valor, get_cor_saldo
from typing import Any, cast

def normalizar_valor_fatura(valor):
    return -abs(valor)

@st.dialog("Confirmar Exclusão")
def _confirmar_exclusao_dialog():
    """Modal de confirmação de exclusão de parcelas."""
    ids = st.session_state.get('ids_para_excluir', [])
    descs = st.session_state.get('descs_para_excluir', [])

    if not ids:
        st.rerun()
        return

    if len(ids) == 1:
        st.warning(f" Excluir **{descs[0]}**?\n\nEsta ação é irreversível.")
    else:
        st.warning(f" Excluir **{len(ids)} item(ns)**? Esta ação é irreversível.")
        for desc in descs:
            st.markdown(f"- {desc}")

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sim, excluir", width='stretch', type="primary", icon=":material/check:"):
            user_id = db.get_user_id()
            tipo = st.session_state.get('excluir_tipo', 'item_fatura')
            fatura_ids_afetadas = set()

            for rid in ids:
                rid = int(rid)
                if tipo == 'item_fatura':
                    # Busca fatura_id antes de excluir
                    row = db.buscar_um("SELECT fatura_id FROM itens_fatura WHERE id=? AND user_id=?", (rid, user_id))
                    if row:
                        fatura_ids_afetadas.add(int(row[0]))
                    db.executar("DELETE FROM itens_fatura WHERE id=? AND user_id=?", (rid, user_id))
                else:
                    db.executar("DELETE FROM transacoes WHERE id=? AND user_id=?", (rid, user_id))

            # Recalcula totais das faturas afetadas
            for fid in fatura_ids_afetadas:
                db.atualizar_total_fatura(int(fid))

            st.session_state['parcela_msg_sucesso'] = f" {len(ids)} item(ns) excluído(s) com sucesso!"
            st.session_state.pop('ids_para_excluir', None)
            st.session_state.pop('descs_para_excluir', None)
            st.session_state.pop('excluir_tipo', None)
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and k.startswith('sel_item_'):
                    del st.session_state[k]
            st.rerun()
    with col2:
        if st.button("Cancelar", width='stretch', icon=":material/close:"):
            st.session_state.pop('ids_para_excluir', None)
            st.session_state.pop('descs_para_excluir', None)
            st.rerun()


class ParcelasManager:
    """Gerenciador de Projeção de Gastos (Parcelas)."""
    
    
    @staticmethod
    def renderizar():
        """Renderiza a página de projeção de gastos."""
        st.header(" Projeção de Gastos (Cartão/Parcelas)")

        @st.cache_data(ttl=60, show_spinner=False)
        def get_contas(user_id):
            return db.buscar(f"SELECT * FROM contas WHERE user_id = {user_id} ORDER BY nome")

        @st.cache_data(ttl=60, show_spinner=False)
        def get_categorias(user_id):
            return db.buscar(f"SELECT * FROM categorias WHERE user_id = {user_id} ORDER BY nome")

        user_id = db.get_user_id()
        df_contas = get_contas(user_id)
        df_cats = get_categorias(user_id)

        tab1, tab2, tab3 = st.tabs(["Manual", "Importações", "Previsão"])

        with tab1:
            ParcelasManager._tab_manual(df_contas, df_cats)

        with tab2:
            ParcelasManager._tab_importacoes(df_contas, df_cats)

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
            # Proteção caso não existam contas/categorias cadastradas
            cnt = c1.selectbox("Cartão/Banco", df_contas['nome'] if not df_contas.empty else [""])
            cat = c2.selectbox("Categoria", df_cats['nome'] if not df_cats.empty else [""])
            dt_ini = c3.date_input("Vencimento da 1ª parcela")
            
            if st.form_submit_button("Lançar Parcelas", width='stretch'):
                if not desc or v_parcela <= 0:
                    st.error(" Preencha descrição e valor!")
                elif p_atual > p_total:
                    st.error(" Parcela atual não pode ser maior que total!")
                else:
                    ParcelasManager._lancar_parcelas(
                        desc, v_parcela, p_atual, p_total, cnt, cat, dt_ini,
                        df_contas, df_cats
                    )
    
    @staticmethod
    def _lancar_parcelas(desc, val, p_atual, p_total, cnt, cat, dt_ini, df_contas, df_cats):
        """Lança parcelas manuais criando faturas + itens."""
        try:
            cid = int(df_contas[df_contas.nome == cnt].id.values[0])
            ctid = int(df_cats[df_cats.nome == cat].id.values[0])
            user_id = db.get_user_id()
            parcelas_lancar = (int(p_total) - int(p_atual)) + 1

            for i in range(parcelas_lancar):
                venc = dt_ini + relativedelta(months=i)
                num_parc = int(p_atual) + i
                competencia = venc.strftime('%m/%Y')

                fatura_id = db.criar_fatura(user_id, cid, competencia, venc)
                db.adicionar_item_fatura(
                    fatura_id, desc, float(val), dt_ini,
                    num_parc, int(p_total), ctid, user_id
                )
                db.atualizar_total_fatura(int(fatura_id))
                db.sincronizar_transacao_fatura(int(fatura_id), user_id)

            st.success(f" {parcelas_lancar} parcelas lançadas com sucesso!")
            ParcelasManager._resetar_estado_pdf()

        except Exception as e:
            st.error(f"Erro ao lançar parcelas: {e}")

    @staticmethod
    def _resetar_estado_pdf():
        """Limpa as variáveis de controle da interface de importação."""
        st.session_state["ocr_file_name"] = None
        st.session_state["ocr_banco"] = "GENÉRICO"
        st.session_state["ocr_texto"] = ""
        st.session_state["ocr_dados"] = []
        st.session_state.pop("ocr_dados_editaveis", None)
        st.session_state.pop("ocr_manual_itens", None)
        st.session_state.pop("ocr_metodo", None)
        # Incrementa versão para invalidar widgets antigos
        st.session_state["ocr_version"] = st.session_state.get("ocr_version", 0) + 1

    @staticmethod
    def _safe_rerun():
        """Tenta forçar um rerun de forma compatível com várias versões do Streamlit."""
        # Streamlit >= 1.27: st.rerun()
        rerun_fn = getattr(st, "rerun", None)
        if callable(rerun_fn):
            rerun_fn()
            return

        # Streamlit < 1.27: st.experimental_rerun()
        exp_rerun = getattr(st, "experimental_rerun", None)
        if callable(exp_rerun):
            try:
                exp_rerun()
                return
            except Exception:
                pass

        # Fallback seguro
        st.warning("Por favor, atualize a página manualmente (F5) para aplicar as mudanças.")
    
    @staticmethod
    def _tab_importacoes(df_contas, df_cats):
        """Aba unificada de importações — o usuário escolhe PDF ou CSV."""
        tipo = st.radio(
            "Selecione o tipo de importação:",
            ["Importar PDF (OCR)", "Importar CSV"],
            horizontal=True,
            key="import_tipo"
        )
        st.divider()
        if tipo == "Importar PDF (OCR)":
            ParcelasManager._tab_importar_pdf(df_contas, df_cats)
        else:
            ParcelasManager._tab_importar_csv(df_contas, df_cats)

    @staticmethod
    def _tab_importar_pdf(df_contas, df_cats):
        """Aba para importar faturas via upload de PDF ou texto colado (fallback)."""
        st.subheader("?? Importador de Faturas PDF")

        # -- OPÇÃO 1: UPLOAD DIRETO DO PDF (caminho principal) --------------
        st.markdown("##### Opção 1 — Upload do PDF da fatura")
        st.caption("Suporte automático a: Nubank, Itaú, Bradesco, Mercado Pago, Porto Bank.")

        pdf_file = st.file_uploader(
            "Selecione o PDF da fatura do cartão",
            type=["pdf"],
            key="pdf_uploader",
            help="Faça upload do PDF da fatura. O sistema detecta o banco e extrai os lançamentos automaticamente.",
        )

        # Detecta troca de arquivo para limpar estado anterior
        if pdf_file and st.session_state.get("ocr_file_name") != pdf_file.name:
            ParcelasManager._resetar_estado_pdf()
            st.session_state["ocr_file_name"] = pdf_file.name

        if pdf_file:
            senha_pdf = None
            col_senha, col_btn = st.columns([2, 1])
            with col_senha:
                senha_input = st.text_input(
                    "Senha do PDF (se houver)",
                    type="password",
                    key="pdf_senha",
                    placeholder="Deixe em branco se não tiver senha",
                )
                if senha_input:
                    senha_pdf = senha_input

            with col_btn:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                processar_btn = st.button(
                    "?? Extrair lançamentos",
                    key="btn_processar_pdf",
                    type="primary",
                    use_container_width=True,
                )

            if processar_btn:
                with st.spinner("Lendo PDF e extraindo lançamentos... aguarde."):
                    try:
                        banco_p, texto_p, dados_p, metodo_p = processar_fatura(
                            pdf_file, senha_pdf=senha_pdf, incluir_avista=True
                        )

                        if texto_p == "__PDF_PROTEGIDO__" or banco_p == "__PDF_PROTEGIDO__":
                            st.error(
                                "?? **PDF protegido por senha.**\n\n"
                                "Digite a senha do PDF no campo acima e tente novamente."
                            )
                        elif not dados_p:
                            st.warning(
                                "?? Nenhum lançamento detectado automaticamente.\n\n"
                                "Tente a **Opção 2** abaixo: copie o texto do PDF e cole manualmente."
                            )
                        else:
                            st.session_state["ocr_banco"] = banco_p
                            st.session_state["ocr_texto"] = texto_p
                            st.session_state["ocr_dados"] = dados_p
                            st.session_state["ocr_metodo"] = metodo_p
                            st.session_state.pop("ocr_dados_editaveis", None)
                            st.session_state["ocr_version"] = (
                                st.session_state.get("ocr_version", 0) + 1
                            )
                            n_av = sum(1 for _, p, _ in dados_p if p == "1/1")
                            n_pc = len(dados_p) - n_av
                            st.success(
                                f"? **{len(dados_p)} itens extraídos!** "
                                f"({n_pc} parcelado(s), {n_av} à vista) "
                                f"— Banco: **{banco_p}** · Método: `{metodo_p}`"
                            )
                            ParcelasManager._safe_rerun()

                    except Exception as e:
                        st.error(f"? Erro ao processar PDF: {e}")

        st.divider()

        # -- OPÇÃO 2: TEXTO COLADO (fallback para PDFs problemáticos) -------
        with st.expander("Opção 2 — Colar texto manualmente (para PDFs que não abriram)", expanded=False):
            st.caption(
                "Use somente se o upload não funcionar. "
                "Abra o PDF, selecione os lançamentos, copie (Ctrl+C) e cole abaixo."
            )
            texto_colado = st.text_area(
                "Cole o texto dos lançamentos aqui:",
                height=180,
                key="ocr_texto_colado",
            )
            if texto_colado:
                if st.button("Processar texto colado", icon=":material/refresh:", key="btn_processar_texto"):
                    banco_c, texto_c, dados_c, metodo_c = processar_texto_colado(texto_colado)
                    if dados_c:
                        st.session_state["ocr_banco"] = banco_c
                        st.session_state["ocr_texto"] = texto_c
                        st.session_state["ocr_dados"] = dados_c
                        st.session_state["ocr_metodo"] = metodo_c
                        st.session_state.pop("ocr_dados_editaveis", None)
                        st.session_state["ocr_version"] = (
                            st.session_state.get("ocr_version", 0) + 1
                        )
                        n_av = sum(1 for _, p, _ in dados_c if p == "1/1")
                        n_pc = len(dados_c) - n_av
                        st.success(
                            f"? {len(dados_c)} itens encontrados! "
                            f"({n_pc} parcelado(s), {n_av} à vista)"
                        )
                        ParcelasManager._safe_rerun()
                    else:
                        st.warning("Nenhum item detectado no texto colado.")

        st.divider()

        dados_salvos = st.session_state.get("ocr_dados", [])
        banco_detectado = st.session_state.get("ocr_banco", "Desconhecido")
        if dados_salvos:
            st.markdown(f"### Banco Detectado: **{banco_detectado}**")
            st.markdown("#### Auditoria — Revise antes de importar")
            st.caption("Edite descrições, corrija parcelas ou desmarque itens que não deseja importar.")

            def _excluir_item(idx_to_del):
                eds = st.session_state.get("ocr_dados_editaveis", [])
                svd = list(st.session_state.get("ocr_dados", []))
                if 0 <= idx_to_del < len(eds):
                    eds.pop(idx_to_del)
                if 0 <= idx_to_del < len(svd):
                    svd.pop(idx_to_del)
                st.session_state["ocr_dados_editaveis"] = eds
                st.session_state["ocr_dados"] = svd
                # Incrementa versão ? todos os widgets são recriados com chaves novas
                st.session_state["ocr_version"] = st.session_state.get("ocr_version", 0) + 1

            # Inicializa dados editáveis no session_state (só na primeira vez)
            if "ocr_dados_editaveis" not in st.session_state or len(st.session_state["ocr_dados_editaveis"]) != len(dados_salvos):
                st.session_state["ocr_dados_editaveis"] = [
                    {"desc": d[0], "parc": d[1], "valor": d[2], "importar": True}
                    for d in dados_salvos
                ]

            dados_editaveis = st.session_state["ocr_dados_editaveis"]
            _v = st.session_state.get("ocr_version", 0)  # versão para chaves únicas

            # Cabeçalho da tabela
            hdr1, hdr2, hdr3, hdr4, hdr5, hdr6 = st.columns([0.4, 2.8, 1.0, 1.2, 1.5, 1.0])
            hdr1.markdown("****")
            hdr2.markdown("**Descrição**")
            hdr3.markdown("**Tipo**")
            hdr4.markdown("**Parcela**")
            hdr5.markdown("**Valor (R$)**")
            hdr6.markdown("**Ação**")

            for idx, item in enumerate(dados_editaveis):
                c_check, c_desc, c_tipo, c_parc, c_val, c_del = st.columns([0.4, 2.8, 1.0, 1.2, 1.5, 1.0])

                # Determina tipo (à vista ou parcelado)
                # Só é "à vista" se parcela == 1/1. Ex: 02/02 é a última parcela, não à vista.
                try:
                    _at, _tot = map(int, item["parc"].split("/"))
                    is_avista = (_at == _tot and _tot == 1)
                except (ValueError, AttributeError):
                    is_avista = True

                with c_check:
                    item["importar"] = st.checkbox(
                        "Importar", value=item["importar"],
                        key=f"audit_check_{_v}_{idx}", label_visibility="collapsed"
                    )
                with c_desc:
                    item["desc"] = st.text_input(
                        "Desc", value=item["desc"],
                        key=f"audit_desc_{_v}_{idx}", label_visibility="collapsed"
                    )
                with c_tipo:
                    if is_avista:
                        st.markdown(
                            "<span style='background:#3498db; color:gray; padding:2px 8px; "
                            "border-radius:4px; font-size:11px;'>À vista</span>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            "<span style='background:#e67e22; color:gray; padding:2px 8px; "
                            "border-radius:4px; font-size:11px;'>Parcelado</span>",
                            unsafe_allow_html=True
                        )
                with c_parc:
                    item["parc"] = st.text_input(
                        "Parcela", value=item["parc"],
                        key=f"audit_parc_{_v}_{idx}", label_visibility="collapsed"
                    )
                with c_val:
                    item["valor"] = st.number_input(
                        "Valor", value=float(item["valor"]),
                        key=f"audit_val_{_v}_{idx}", label_visibility="collapsed",
                        format="%.2f"
                    )
                with c_del:
                    st.button(
                        "Excluir", key=f"audit_del_{_v}_{idx}",
                        icon=":material/delete:",
                        on_click=_excluir_item, args=(idx,),
                    )

            # ============================================================
            # ADICIONAR COMPRAS MANUAIS (não capturadas pelo OCR)
            # ============================================================
            with st.expander("? Adicionar compras não detectadas pelo OCR", expanded=False):
                st.caption("Insira compras que não apareceram na leitura automática para acertar o valor total da fatura.")
                
                # Inicializa lista de itens manuais pendentes no session_state
                if "ocr_manual_itens" not in st.session_state:
                    st.session_state["ocr_manual_itens"] = []

                m_c1, m_c2, m_c3 = st.columns([3, 1.2, 1.5])
                manual_desc = m_c1.text_input("Descrição da compra", key="manual_desc_input", placeholder="Ex: Farmácia Droga Raia")
                manual_parc = m_c2.text_input("Parcela (Ex: 1/1 ou 2/6)", key="manual_parc_input", value="1/1")
                manual_valor = m_c3.number_input("Valor (R$)", min_value=0.01, value=0.01, format="%.2f", key="manual_valor_input")

                if st.button("Adicionar à lista", icon=":material/add:", key="btn_add_manual"):
                    if not manual_desc.strip():
                        st.error("Informe a descrição da compra.")
                    elif not re.match(r'^\d{1,2}/\d{1,2}$', manual_parc.strip()):
                        st.error("Parcela deve estar no formato X/Y (ex: 1/1, 3/10).")
                    else:
                        novo_item = {"desc": manual_desc.strip(), "parc": manual_parc.strip(), "valor": manual_valor, "importar": True}
                        dados_editaveis.append(novo_item)
                        st.session_state["ocr_dados_editaveis"] = dados_editaveis
                        # Sincroniza ocr_dados também
                        dados_salvos_list = list(st.session_state.get("ocr_dados", []))
                        dados_salvos_list.append((novo_item["desc"], novo_item["parc"], novo_item["valor"]))
                        st.session_state["ocr_dados"] = dados_salvos_list
                        # Incrementa versão para widgets serem recriados
                        st.session_state["ocr_version"] = st.session_state.get("ocr_version", 0) + 1
                        st.toast(f"? \"{manual_desc.strip()}\" adicionado!")
                        ParcelasManager._safe_rerun()

                # Mostra itens manuais já adicionados que não vieram do OCR original
                itens_manuais = [d for d in dados_editaveis if d.get("manual")]
                if itens_manuais:
                    st.markdown("**Itens adicionados manualmente:**")
                    for mi in itens_manuais:
                        st.markdown(f"- {mi['desc']} | {mi['parc']} | {moeda(mi['valor'])}")

            # Resumo
            selecionados = [d for d in dados_editaveis if d["importar"]]
            total_sel = sum(d["valor"] for d in selecionados)
            n_parc_sel = sum(1 for d in selecionados if d["parc"] != "1/1")
            n_avista_sel = len(selecionados) - n_parc_sel
            st.markdown(
                f"**{len(selecionados)}** de **{len(dados_editaveis)}** itens selecionados "
                f"({n_parc_sel} parcelado(s), {n_avista_sel} à vista) "
                f"— Total: **{moeda(total_sel)}**"
            )

            st.markdown("---")

            # Formulário para salvar no banco
            with st.form("confirmar_importacao"):
                st.markdown("#### Configurar Lançamento em Lote")
                col1, col2 = st.columns(2)

                # Previne erro se listas vazias
                lista_contas = df_contas['nome'].tolist() if not df_contas.empty else []
                lista_cats = df_cats['nome'].tolist() if not df_cats.empty else []

                if not lista_contas:
                    st.error("?? Nenhuma conta/cartão cadastrada. Cadastre em Cadastros antes de importar.")
                if not lista_cats:
                    st.error("?? Nenhuma categoria cadastrada. Cadastre em Cadastros antes de importar.")

                conta = col1.selectbox("Cartão de Destino", lista_contas if lista_contas else ["Sem contas"])
                data_base = col2.date_input("Vencimento da 1ª Parcela do Lote")
                cat = st.selectbox("Categoria Padrão", lista_cats if lista_cats else ["Sem categorias"])

                if st.form_submit_button("Salvar no Banco (Aplicar Trava Anti-Duplicidade)", width='stretch'):
                    # Monta lista final apenas com itens marcados para importar
                    dados_finais = [
                        (d["desc"], d["parc"], d["valor"])
                        for d in dados_editaveis if d["importar"]
                    ]
                    if not dados_finais:
                        st.warning("?? Nenhuma parcela selecionada para importar.")
                    elif not lista_contas or conta == "Sem contas":
                        st.error("?? Selecione um cartão de destino válido.")
                    elif not lista_cats or cat == "Sem categorias":
                        st.error("?? Selecione uma categoria válida.")
                    elif not data_base:
                        st.error("?? Selecione a data de vencimento da 1ª parcela.")
                    else:
                        ParcelasManager._importar_pdf_dados(
                            dados_finais, banco_detectado, conta, cat, data_base, df_contas, df_cats
                        )
    @staticmethod
    def _tab_importar_csv(df_contas, df_cats):
        """Aba para importar faturas via arquivo CSV (Otimizada e com Conversor de Moeda)."""
        st.subheader(" Importador de Faturas via CSV")
        
        file_csv = st.file_uploader("Envie a fatura em formato CSV", type=["csv"])

        # Resetar estado se mudar de arquivo
        if file_csv and st.session_state.get("csv_file_name") != file_csv.name:
            st.session_state["csv_dados"] = []
            st.session_state["csv_file_name"] = file_csv.name

        if file_csv:
            try:
                # Tenta ler o CSV de forma flexível (suporta separador vírgula e ponto-e-vírgula)
                df_csv = pd.read_csv(file_csv, sep=None, engine='python')
                
                st.markdown("**1. Prévia do Arquivo:**")
                st.dataframe(df_csv.head(3), width='stretch')

                st.markdown("**2. Mapeamento de Colunas:**")
                c1, c2, c3 = st.columns(3)
                col_desc = c1.selectbox("Coluna da Descrição?", df_csv.columns)
                col_val = c2.selectbox("Coluna do Valor?", df_csv.columns)
                
                # Nova opção: Escolher coluna da parcela se existir
                opcoes_parc = ["Nenhuma (Extrair da Descrição)"] + list(df_csv.columns)
                col_parc = c3.selectbox("Coluna da Parcela? (Opcional)", opcoes_parc)

                if st.button("Extrair Dados do CSV", width='stretch', icon=":material/search:"):
                    with st.spinner("Lendo linhas..."):
                        dados_extraidos = []
                        
                        for _, row in df_csv.iterrows():
                            # Define desc_original aqui, lendo a coluna escolhida
                            desc_original = str(row[col_desc])
                            
                            try:
                                # --- CONVERSOR DE MOEDA INTELIGENTE ---
                                val_raw = row[col_val]
                                
                                # Pula se a linha for nula/vazia
                                if pd.isna(val_raw):
                                    continue
                                    
                                # Se o Pandas já leu como número (int ou float)
                                if isinstance(val_raw, (int, float)):
                                    val = float(val_raw)
                                else:
                                    # Limpeza de texto de moeda
                                    val_str = str(val_raw).replace("R$", "").strip()
                                    
                                    # Resolve conflitos de ponto vs virgula
                                    if "." in val_str and "," in val_str:
                                        if val_str.rfind(",") > val_str.rfind("."):
                                            val_str = val_str.replace(".", "").replace(",", ".")
                                        else:
                                            val_str = val_str.replace(",", "")
                                    elif "," in val_str:
                                        val_str = val_str.replace(",", ".")
                                        
                                    val = float(val_str)
                                # ---------------------------------------
                                
                                # Ignora valores zerados
                                if abs(val) == 0:
                                    continue
                                
                                parc_formatada = "1/1"
                                desc_limpa = desc_original.strip()
                                
                                # CENÁRIO 1: O CSV já tem a coluna "Parcela"
                                if col_parc != "Nenhuma (Extrair da Descrição)":
                                    parc_val = str(row[col_parc]).strip()
                                    if "à vista" not in parc_val.lower():
                                        parc_match = re.search(r'(\d{1,2})/(\d{1,2})', parc_val)
                                        if parc_match:
                                            g1, g2 = parc_match.group(1), parc_match.group(2)
                                            if g1.isdigit() and g2.isdigit():
                                                parc_formatada = f"{int(g1)}/{int(g2)}"
                                            else:
                                                continue  # Ignora se não for dígito
                                
                                # CENÁRIO 2: Extrair de textos
                                else:
                                    # Remove texto de data (Ex: Compra: 12/02) para não confundir com parcela
                                    texto_busca = re.sub(r'\(Compra:\s*\d{1,2}/\d{1,2}.*?\)', '', desc_original)
                                    texto_busca = re.sub(r'\(À vista\)', '', texto_busca, flags=re.IGNORECASE)
                                    parc_match = re.search(r'(\d{1,2})/(\d{1,2})', texto_busca)
                                    if parc_match:
                                        g1, g2 = parc_match.group(1), parc_match.group(2)
                                        if g1.isdigit() and g2.isdigit():
                                            parc_formatada = f"{int(g1)}/{int(g2)}"
                                            desc_limpa = re.sub(r'\s*\d{1,2}/\d{1,2}\s*', '', desc_original).strip()
                                        else:
                                            continue  # Ignora se não for dígito
                                
                                # Valida formato da parcela
                                try:
                                    p_atual, p_total = map(int, parc_formatada.split("/"))
                                except (ValueError, AttributeError):
                                    continue
                                
                                dados_extraidos.append((desc_limpa, parc_formatada, val))
                                    
                            except Exception:
                                continue # Pula linhas inválidas
                                
                        st.session_state["csv_dados"] = dados_extraidos
                        st.success(f" {len(dados_extraidos)} registros processados com sucesso!")

            except Exception as e:
                st.error(f"Erro ao ler o CSV. O arquivo pode estar corrompido: {e}")

        # 3. Exibição e Lançamento
        dados_salvos = st.session_state.get("csv_dados", [])
        
        if dados_salvos:
            st.markdown("---")
            st.markdown("### Conferência e Lançamento (CSV)")
            
            df_preview = pd.DataFrame(dados_salvos, columns=["Descrição", "Parcela", "Valor"])
            st.dataframe(df_preview, width='stretch')

            with st.form("confirmar_importacao_csv"):
                col1, col2 = st.columns(2)
                
                lista_contas = df_contas['nome'].tolist() if not df_contas.empty else ["Sem contas"]
                lista_cats = df_cats['nome'].tolist() if not df_cats.empty else ["Sem categorias"]
                
                conta = col1.selectbox("Cartão de Destino", lista_contas)
                data_base = col2.date_input("Vencimento da 1ª Parcela do Lote")
                cat = st.selectbox("Categoria Padrão", lista_cats)
                
                if st.form_submit_button("Salvar no Banco (Aplicar Trava Anti-Duplicidade)", width='stretch'):
                    
                    ParcelasManager._importar_pdf_dados(
                        dados=dados_salvos, 
                        banco="CSV IMPORT", 
                        conta=conta, 
                        cat=cat, 
                        data_base=data_base, 
                        df_contas=df_contas, 
                        df_cats=df_cats
                    )
                    
                    st.session_state["csv_dados"] = [] 

    @staticmethod
    def _importar_pdf_dados(dados, banco, conta, cat, data_base, df_contas, df_cats):
        """Importa dados do PDF/CSV criando faturas + itens (modelo novo)."""
        try:
            contas_match = df_contas[df_contas.nome == conta]
            cats_match = df_cats[df_cats.nome == cat]

            if contas_match.empty:
                st.error(" Conta/Cartão não encontrado. Cadastre um cartão em **Cadastros** antes de importar.")
                return
            if cats_match.empty:
                st.error(" Categoria não encontrada. Cadastre uma categoria em **Cadastros** antes de importar.")
                return

            cid = int(contas_match.id.values[0])
            ctid = int(cats_match.id.values[0])
            user_id = db.get_user_id()

            novos = 0
            duplicados = 0
            erros = 0

            print(f"[IMPORT] Iniciando importação de {len(dados)} itens...")

            for desc, parc, val in dados:
                try:
                    val = normalizar_valor_fatura(val)
                    val = abs(val)  # Garante que o valor do item de fatura é sempre positivo

                    atual, total = map(int, parc.split("/"))
                except Exception as inner_e:
                    st.warning(f"Erro ao processar linha '{desc}': {inner_e}")
                    erros += 1
                    continue

                print(f"[IMPORT] Item: desc={desc!r}, parc={parc}, val={val}")
                try:
                    atual, total = map(int, parc.split("/"))

                    for i in range(atual - 1, total):
                        venc = data_base + relativedelta(months=i - (atual - 1))
                        num_parc_atual = i + 1
                        competencia = venc.strftime('%m/%Y')

                        fatura_id = db.criar_fatura(user_id, cid, competencia, venc)
                        if not fatura_id:
                            st.warning(f"Erro ao criar/buscar fatura para competência {competencia}. Item ignorado.")
                            erros += 1
                            continue


                        # Desabilitado: trava anti-duplicidade (importa todos os itens)
                        db.adicionar_item_fatura(
                            fatura_id, desc, val, data_base,
                            num_parc_atual, total, ctid, user_id
                        )
                        novos += 1
                        print(f"[IMPORT]   ? NOVO: parc {num_parc_atual}/{total} comp={competencia} fatura_id={fatura_id}")

                        db.atualizar_total_fatura(int(fatura_id))
                        db.sincronizar_transacao_fatura(int(fatura_id), user_id)

                except Exception as inner_e:
                    st.warning(f"Erro ao processar linha '{desc}': {inner_e}")
                    erros += 1
                    continue

            if novos > 0:
                st.session_state['parcela_msg_sucesso'] = f"? {novos} itens salvos!"
            if duplicados > 0:
                st.session_state['parcela_msg_sucesso'] = st.session_state.get('parcela_msg_sucesso', '') + f" | {duplicados} ignorado(s) (já existiam)."
            if erros > 0:
                st.session_state['parcela_msg_sucesso'] = st.session_state.get('parcela_msg_sucesso', '') + f" | {erros} com erro."
            if novos == 0 and duplicados > 0:
                st.session_state['parcela_msg_sucesso'] = f"?? Nenhum item novo importado — {duplicados} já existiam no sistema."

            ParcelasManager._resetar_estado_pdf()
            # Limpa widget keys da auditoria para não manter dados obsoletos
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and (k.startswith("audit_") or k.startswith("manual_")):
                    del st.session_state[k]
            ParcelasManager._safe_rerun()

        except Exception as e:
            st.error(f"Erro fatal na importação: {e}")

    @staticmethod
    def _tab_previsao():
        """Aba com previsão de gastos - Dashboard completo (lê de faturas + itens)."""
        st.subheader(" Dashboard de Previsão de Gastos")

        user_id = db.get_user_id()
        df_contas = db.buscar(f"SELECT * FROM contas WHERE user_id = {user_id} ORDER BY nome")
        df_cats = db.buscar(f"SELECT * FROM categorias WHERE user_id = {user_id} ORDER BY nome")

        # Busca faturas do usuário
        df_faturas = db.buscar(f"""
            SELECT f.id as fatura_id, f.competencia, f.valor_total, f.data_vencimento,
                   f.status, f.data_pagamento, c.nome as banco, f.conta_id
            FROM faturas f
            LEFT JOIN contas c ON f.conta_id = c.id
            WHERE f.user_id = {user_id}
            ORDER BY f.data_vencimento ASC
        """)

                # Busca itens de fatura do usuário (somente parcelas futuras + Trava Anti-Duplicidade na previsão)
        df_itens = db.buscar(f"""
                        SELECT i.id, i.fatura_id, i.descricao, i.valor, i.data_compra,
                                     i.parcela_atual, i.parcela_total,
                                     cat.nome as categoria, c.nome as banco,
                                     f.competencia, f.data_vencimento, f.status,
                                     i.categoria_id
                        FROM itens_fatura i
                        JOIN faturas f ON i.fatura_id = f.id
                        LEFT JOIN contas c ON f.conta_id = c.id
                        LEFT JOIN categorias cat ON i.categoria_id = cat.id
                        WHERE i.user_id = {user_id}
                            AND i.parcela_atual < i.parcela_total
                            -- TRAVA: Ignora esta parcela se ela já existir em uma fatura real/importada
                            AND NOT EXISTS (
                                    SELECT 1 
                                    FROM itens_fatura i_real
                                    JOIN faturas f_real ON i_real.fatura_id = f_real.id
                                    WHERE i_real.user_id = {user_id}
                                        -- 1. Valida se é o mesmo cartão e a mesma competência (mês/ano)
                                        AND f_real.conta_id = f.conta_id
                                        AND f_real.competencia = f.competencia
                                        -- 2. Identifica que é exatamente a mesma compra
                                        AND i_real.descricao = i.descricao
                                        AND i_real.parcela_atual = i.parcela_atual
                                        -- 3. O Diferenciador: garante que a subquery só ache itens "reais"
                                        -- (Ajuste 'fechada' ou 'importada' para o status que seu sistema dá ao importar)
                                        AND (f_real.status = 'fechada' OR f_real.status = 'importada')
                            )
                        ORDER BY f.data_vencimento ASC, i.descricao
                """)

        if df_itens.empty:
            st.info("? Nenhuma parcela lançada no cartão ainda.")
            return

        df_itens['data_vencimento'] = pd.to_datetime(df_itens['data_vencimento'])
        df_itens['valor_abs'] = df_itens['valor'].abs()

        # 1. MÉTRICAS DE TOPO
        total_divida = df_itens['valor_abs'].sum()

        df_itens['Mes_Ano'] = df_itens['data_vencimento'].dt.to_period('M')
        agrupado_mes = df_itens.groupby('Mes_Ano')['valor_abs'].sum().reset_index()
        agrupado_mes['Mes_Ano_Str'] = agrupado_mes['Mes_Ano'].astype(str)
        agrupado_mes = agrupado_mes.sort_values('Mes_Ano')

        if not agrupado_mes.empty:
            mes_mais_pesado = agrupado_mes.loc[agrupado_mes['valor_abs'].idxmax()]
        else:
            mes_mais_pesado = None

        c_met1, c_met2 = st.columns(2)
        c_met1.markdown(f"""
            <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; border-left:5px solid #e74c3c;">
                <small>Total Parcelado a Pagar (Geral)</small><br><strong style="font-size: 22px; color: #c0392b;">{moeda(total_divida)}</strong>
            </div>
        """, unsafe_allow_html=True)

        if mes_mais_pesado is not None:
            c_met2.markdown(f"""
                <div style="background:#f1f2f6; color:#333333; padding:15px; border-radius:10px; border-left:5px solid #f39c12;">
                    <small>Mês mais pesado ({mes_mais_pesado['Mes_Ano_Str']})</small><br><strong style="font-size: 22px; color: #d35400;">{moeda(mes_mais_pesado['valor_abs'])}</strong>
                </div>
            """, unsafe_allow_html=True)
        else:
            c_met2.info("Sem dados por mês para calcular o mês mais pesado.")

        st.write("")

        st.markdown("---")

        # 2. GRÁFICO DE EVOLUÇÃO
        st.markdown("** Evolução do Parcelamento nos Próximos Meses**")
        agrupado_mes['cumulativo'] = agrupado_mes['valor_abs'].cumsum()
        fig = go.Figure()
        fig.add_bar(x=agrupado_mes['Mes_Ano_Str'], y=agrupado_mes['valor_abs'], name='Mensal', marker_color='#e74c3c')
        fig.add_trace(go.Scatter(x=agrupado_mes['Mes_Ano_Str'], y=agrupado_mes['cumulativo'], mode='lines+markers', name='Cumulativo', line=dict(color='#1f77b4')))
        fig.update_layout(yaxis_title='Valor (R$)', xaxis_title='Mês/Ano', legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
        fig.update_yaxes(tickprefix='R$ ')
        st.plotly_chart(fig, width='stretch')

        st.markdown("---")

        # 3. DISTRIBUIÇÃO POR CARTÃO / CATEGORIA
        st.markdown("** Distribuição por Cartão / Categoria (Próximos Meses)**")
        distrib_cartao = df_itens.groupby('banco')['valor_abs'].sum().reset_index().sort_values('valor_abs', ascending=False)
        distrib_categoria = df_itens.groupby('categoria')['valor_abs'].sum().reset_index().sort_values('valor_abs', ascending=False)

        d1, d2 = st.columns(2)
        with d1:
            if not distrib_cartao.empty:
                fig1 = px.pie(distrib_cartao, values='valor_abs', names='banco', title='Por Cartão', hole=0.4)
                st.plotly_chart(fig1, width='stretch')
            else:
                st.info("Sem dados por cartão.")
        with d2:
            if not distrib_categoria.empty:
                fig2 = px.pie(distrib_categoria, values='valor_abs', names='categoria', title='Por Categoria', hole=0.4)
                st.plotly_chart(fig2, width='stretch')
            else:
                st.info("Sem dados por categoria.")

        st.markdown("---")

        # 4. EXPORTAÇÃO / RELATÓRIO
        st.markdown("** Exportar Relatório**")
        csv_rel = df_itens[['id','data_vencimento','descricao','valor_abs','banco','categoria','parcela_atual','parcela_total']].copy()
        csv_rel = csv_rel.rename(columns={
            'id': 'ID',
            'data_vencimento': 'Data Vencimento',
            'descricao': 'Descrição',
            'valor_abs': 'Valor (R$)',
            'banco': 'Cartão',
            'categoria': 'Categoria',
            'parcela_atual': 'Parcela',
            'parcela_total': 'Total Parcelas'
        })
        csv_bytes = csv_rel.to_csv(index=False).encode('utf-8')
        st.download_button(" Baixar CSV de Previsão", data=csv_bytes, file_name="previsao_parcelas.csv", mime="text/csv")

        st.markdown("---")

        # 5. LISTAGEM POR FATURA (grouped by month ? card ? items)
        st.markdown("** Detalhamento por Mês**")

        msg_sucesso = st.session_state.pop('parcela_msg_sucesso', None)
        if msg_sucesso:
            st.toast(msg_sucesso)

        meses_previsao = st.slider("Ver previsão detalhada para quantos meses?", 1, 24, 6)
        primeiro_mes = df_itens['data_vencimento'].min().replace(day=1)

        # IDs selecionados para exclusão em massa
        all_item_ids = df_itens['id'].tolist()
        selected_ids = [
            int(k.replace('sel_item_', ''))
            for k in st.session_state
            if isinstance(k, str) and k.startswith('sel_item_') and st.session_state[k]
            and int(k.replace('sel_item_', '')) in all_item_ids
        ]

        for i in range(meses_previsao):
            mes_atual = primeiro_mes + relativedelta(months=i)
            f_mes = df_itens[
                (df_itens['data_vencimento'].dt.month == mes_atual.month) &
                (df_itens['data_vencimento'].dt.year == mes_atual.year)
            ]

            if not f_mes.empty:
                total_mes = f_mes['valor_abs'].sum()
                ids_no_mes = set(f_mes['id'].tolist())
                tem_selecionados = bool(ids_no_mes & set(selected_ids))

                with st.expander(f" {mes_atual.strftime('%m/%Y')} — Total do Mês: {moeda(total_mes)}", expanded=tem_selecionados):
                    cartoes_no_mes = f_mes['banco'].fillna("Desconhecido").unique()

                    for cartao in cartoes_no_mes:
                        f_cartao = f_mes[f_mes['banco'].fillna("Desconhecido") == cartao]
                        subtotal_cartao = f_cartao['valor_abs'].sum()

                        # Status da fatura (aberta/paga)
                        status_fatura = f_cartao['status'].iloc[0] if 'status' in f_cartao.columns else 'aberta'
                        badge = " Paga" if status_fatura == 'paga' else " Aberta"

                        st.markdown(
                            f"** Fatura: {cartao}** — Subtotal: "
                            f"<span style='color:#c0392b;'>{moeda(subtotal_cartao)}</span> "
                            f"<small>({badge})</small>",
                            unsafe_allow_html=True
                        )

                        for _, r in f_cartao.iterrows():
                            c_sel, c1, c2, c3, c4, c5 = st.columns([0.4, 1.3, 3.0, 2.3, 0.7, 0.7])

                            parc_label = f"({int(r['parcela_atual']):02d}/{int(r['parcela_total']):02d})"

                            with c_sel:
                                st.checkbox("Selecionar", key=f"sel_item_{r['id']}", label_visibility="collapsed")

                            c1.write(pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y'))
                            c2.markdown(
                                f"**{r['descricao']}** {parc_label}<br>"
                                f"<span style='color:gray; font-size:12px;'>{r.get('categoria','')}</span>",
                                unsafe_allow_html=True
                            )
                            c3.markdown(
                                f"<div style='text-align: right; color:#c0392b; font-weight:bold;'>"
                                f"{moeda(abs(r['valor']))}</div>",
                                unsafe_allow_html=True
                            )

                            with c4:
                                if st.button("\u200b", key=f"edit_item_{r['id']}", help="Editar", icon=":material/edit:"):
                                    key_ed = f"editing_item_{r['id']}"
                                    st.session_state[key_ed] = not st.session_state.get(key_ed, False)

                            with c5:
                                if st.button("\u200b", key=f"del_item_{r['id']}", help="Excluir", icon=":material/delete:"):
                                    st.session_state['ids_para_excluir'] = [int(r['id'])]
                                    st.session_state['descs_para_excluir'] = [f"{r['descricao']} {parc_label} ({moeda(abs(r['valor']))})"]
                                    st.session_state['excluir_tipo'] = 'item_fatura'
                                    _confirmar_exclusao_dialog()

                            # Formulário de edição inline
                            if st.session_state.get(f"editing_item_{r['id']}"):
                                with st.form(f"form_edit_item_{r['id']}"):
                                    d_desc = st.text_input("Descrição", value=r['descricao'], key=f"edit_desc_i_{r['id']}")
                                    d_val = st.number_input("Valor (R$)", min_value=0.0, value=float(abs(r['valor'])), key=f"edit_val_i_{r['id']}")
                                    cat_op = df_cats['nome'].tolist() if not df_cats.empty else []
                                    default_cat_idx = 0
                                    try:
                                        default_cat_idx = cat_op.index(r.get('categoria', '')) if r.get('categoria', '') in cat_op else 0
                                    except Exception:
                                        default_cat_idx = 0
                                    sel_cat = st.selectbox("Categoria", cat_op, index=default_cat_idx, key=f"edit_cat_i_{r['id']}")

                                    save_clicked = st.form_submit_button("Salvar alterações")
                                    cancel_clicked = st.form_submit_button("Voltar")

                                    if cancel_clicked:
                                        st.session_state[f"editing_item_{r['id']}"] = False
                                        st.rerun()

                                    if save_clicked:
                                        try:
                                            ctid = int(df_cats[df_cats.nome == sel_cat].id.values[0])
                                            db.executar(
                                                "UPDATE itens_fatura SET descricao=?, valor=?, categoria_id=? WHERE id=? AND user_id=?",
                                                (d_desc, abs(float(d_val)), ctid, int(r['id']), user_id)
                                            )
                                            # Recalcula total da fatura
                                            db.atualizar_total_fatura(int(r['fatura_id']))
                                            st.success("Item atualizado com sucesso.")
                                        except Exception as e:
                                            st.error(f"Erro ao atualizar item: {e}")
                                        st.session_state[f"editing_item_{r['id']}"] = False
                                        st.rerun()

        # Exclusão em massa
        if selected_ids:
            st.markdown("---")
            col_bulk_info, col_bulk_btn = st.columns([3, 1])
            with col_bulk_info:
                st.info(f" **{len(selected_ids)}** item(ns) selecionado(s)")
            with col_bulk_btn:
                if st.button("Excluir selecionados", type="primary", width='stretch', icon=":material/delete:"):
                    descs = []
                    for sid in selected_ids:
                        row_match = df_itens[df_itens['id'] == sid]
                        if not row_match.empty:
                            desc = row_match.iloc[0]['descricao']
                            descs.append(f"{desc} ({moeda(abs(row_match.iloc[0]['valor']))})")
                    st.session_state['ids_para_excluir'] = selected_ids
                    st.session_state['descs_para_excluir'] = descs
                    st.session_state['excluir_tipo'] = 'item_fatura'
                    _confirmar_exclusao_dialog()