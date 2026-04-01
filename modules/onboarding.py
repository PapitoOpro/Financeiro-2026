# ==========================================
# MÓDULO: ONBOARDING - CONFIGURAÇÃO INICIAL
# ==========================================

import streamlit as st
from database import db

# Templates de perfis de orçamento
PERFIS_ORCAMENTO = {
    "50/30/20 (Clássico)": {
        "descricao": "50% Necessidades, 30% Desejos, 20% Poupança. Regra clássica e equilibrada.",
        "categorias": [
            {"nome": "Moradia", "pct": 30, "icone": "", "subs": ["Aluguel", "Condomínio", "IPTU", "Manutenção"]},
            {"nome": "Alimentação", "pct": 15, "icone": "", "subs": ["Supermercado", "Padaria", "Feira", "Delivery"]},
            {"nome": "Transporte", "pct": 5, "icone": "", "subs": ["Combustível", "Uber", "Estacionamento", "Manutenção Veículo"]},
            {"nome": "Lazer", "pct": 10, "icone": "", "subs": ["Restaurantes", "Cinema", "Streaming", "Viagens"]},
            {"nome": "Compras Pessoais", "pct": 10, "icone": "", "subs": ["Roupas", "Eletrônicos", "Presentes"]},
            {"nome": "Saúde", "pct": 5, "icone": "", "subs": ["Plano de Saúde", "Farmácia", "Academia"]},
            {"nome": "Educação", "pct": 5, "icone": "", "subs": ["Cursos", "Livros", "Mensalidade"]},
            {"nome": "Poupança/Investimentos", "pct": 20, "icone": "", "subs": ["Reserva de Emergência", "Investimentos", "Previdência"]},
        ]
    },
    "Estudante": {
        "descricao": "Foco em educação e sobrevivência com renda limitada.",
        "categorias": [
            {"nome": "Moradia", "pct": 35, "icone": "", "subs": ["Aluguel", "Condomínio", "Internet"]},
            {"nome": "Alimentação", "pct": 25, "icone": "", "subs": ["Supermercado", "Restaurante Universitário", "Delivery"]},
            {"nome": "Transporte", "pct": 10, "icone": "", "subs": ["Ônibus", "Uber", "Estacionamento"]},
            {"nome": "Educação", "pct": 10, "icone": "", "subs": ["Material", "Livros", "Cursos", "Impressão"]},
            {"nome": "Lazer", "pct": 10, "icone": "", "subs": ["Streaming", "Saídas", "Jogos"]},
            {"nome": "Poupança", "pct": 10, "icone": "", "subs": ["Reserva de Emergência"]},
        ]
    },
    "Família": {
        "descricao": "Distribuição equilibrada para quem tem dependentes.",
        "categorias": [
            {"nome": "Moradia", "pct": 30, "icone": "", "subs": ["Aluguel/Financiamento", "Condomínio", "IPTU", "Energia", "Água", "Gás"]},
            {"nome": "Alimentação", "pct": 20, "icone": "", "subs": ["Supermercado", "Hortifrúti", "Padaria", "Delivery"]},
            {"nome": "Educação Filhos", "pct": 10, "icone": "", "subs": ["Escola", "Material Escolar", "Cursos"]},
            {"nome": "Saúde", "pct": 10, "icone": "", "subs": ["Plano de Saúde", "Farmácia", "Dentista", "Pediatra"]},
            {"nome": "Transporte", "pct": 10, "icone": "", "subs": ["Combustível", "Seguro Auto", "Manutenção", "Uber"]},
            {"nome": "Lazer", "pct": 5, "icone": "", "subs": ["Passeios", "Restaurantes", "Streaming"]},
            {"nome": "Poupança", "pct": 15, "icone": "", "subs": ["Reserva de Emergência", "Investimentos", "Faculdade Filhos"]},
        ]
    },
    "Autônomo": {
        "descricao": "Renda variável exige mais controle e reserva maior.",
        "categorias": [
            {"nome": "Moradia", "pct": 25, "icone": "", "subs": ["Aluguel", "Condomínio", "Internet", "Energia"]},
            {"nome": "Alimentação", "pct": 15, "icone": "", "subs": ["Supermercado", "Restaurantes", "Delivery"]},
            {"nome": "Negócio/Trabalho", "pct": 15, "icone": "", "subs": ["Ferramentas", "Marketing", "Software", "Coworking"]},
            {"nome": "Impostos/MEI", "pct": 10, "icone": "", "subs": ["DAS/MEI", "IRPF", "Contador"]},
            {"nome": "Transporte", "pct": 5, "icone": "", "subs": ["Combustível", "Uber", "Manutenção"]},
            {"nome": "Lazer", "pct": 5, "icone": "", "subs": ["Restaurantes", "Cinema", "Streaming"]},
            {"nome": "Saúde", "pct": 5, "icone": "", "subs": ["Plano", "Farmácia", "Academia"]},
            {"nome": "Poupança/Reserva", "pct": 20, "icone": "", "subs": ["Reserva de Emergência", "Investimentos", "Fluxo de Caixa"]},
        ]
    },
    "Minimalista": {
        "descricao": "Para quem quer simplificar ao máximo e focar em poupar.",
        "categorias": [
            {"nome": "Essenciais", "pct": 50, "icone": "", "subs": ["Moradia", "Alimentação", "Saúde", "Transporte"]},
            {"nome": "Pessoal", "pct": 20, "icone": "", "subs": ["Lazer", "Compras", "Educação"]},
            {"nome": "Poupança", "pct": 30, "icone": "", "subs": ["Reserva de Emergência", "Investimentos"]},
        ]
    },
    "Personalizado": {
        "descricao": "Comece do zero e monte suas próprias categorias.",
        "categorias": []
    }
}


class OnboardingManager:
    """Gerencia o fluxo de onboarding para novos usuários."""

    @staticmethod
    def renderizar():
        """Renderiza o fluxo completo de onboarding."""
        st.markdown(
            "<h1 style='text-align:center;'> Bem-vindo ao Finanças Pro 2026!</h1>"
            "<p style='text-align:center; color:#666; font-size:16px;'>"
            "Vamos configurar seu perfil financeiro em poucos passos.</p>",
            unsafe_allow_html=True
        )

        if 'onboarding_step' not in st.session_state:
            st.session_state.onboarding_step = 1

        step = st.session_state.onboarding_step

        # Progresso visual
        st.progress(step / 3, text=f"Passo {step} de 3")

        if step == 1:
            OnboardingManager._step_perfil()
        elif step == 2:
            OnboardingManager._step_ajuste_percentuais()
        elif step == 3:
            OnboardingManager._step_confirmacao()

    @staticmethod
    def _step_perfil():
        """Passo 1: Escolha do perfil de orçamento."""
        st.markdown("### Passo 1: Escolha seu perfil financeiro")
        st.caption("Selecione o modelo que mais se encaixa na sua realidade. Você poderá ajustar tudo depois.")

        perfil_nomes = list(PERFIS_ORCAMENTO.keys())

        # Cards de perfil
        cols = st.columns(3)
        for i, nome in enumerate(perfil_nomes):
            perfil = PERFIS_ORCAMENTO[nome]
            with cols[i % 3]:
                selecionado = st.session_state.get('onboarding_perfil') == nome
                borda = "3px solid #3498db" if selecionado else "1px solid #ddd"
                bg = "#ebf5fb" if selecionado else "#f8f9fa"

                st.markdown(f"""
                    <div style="background:{bg}; border:{borda}; padding:15px; border-radius:10px; 
                                margin-bottom:10px; min-height:120px;">
                        <div style="font-size:16px; font-weight:bold;">{nome}</div>
                        <div style="font-size:16px; color:#000; margin-top:5px;">{perfil['descricao']}</div>
                        <div style="font-size:11px; color:#999; margin-top:8px;">
                            {len(perfil['categorias'])} categorias
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if st.button(f"Selecionar", key=f"sel_perfil_{i}", use_container_width=True):
                    st.session_state.onboarding_perfil = nome
                    # Inicializa categorias editáveis
                    st.session_state.onboarding_categorias = [
                        {**cat} for cat in perfil['categorias']
                    ]
                    st.rerun()

        if st.session_state.get('onboarding_perfil'):
            st.success(f"Perfil selecionado: **{st.session_state.onboarding_perfil}**")

            if st.button("Próximo →", type="primary", use_container_width=True):
                st.session_state.onboarding_step = 2
                st.rerun()

    @staticmethod
    def _step_ajuste_percentuais():
        """Passo 2: Ajuste de percentuais com barra de 100%."""
        st.markdown("### Passo 2: Ajuste suas metas de orçamento")
        st.caption("Distribua sua renda entre as categorias. O total deve somar 100%.")

        categorias = st.session_state.get('onboarding_categorias', [])

        if not categorias:
            st.warning("Nenhuma categoria configurada. Volte e selecione um perfil.")
            if st.button("← Voltar"):
                st.session_state.onboarding_step = 1
                st.rerun()
            return

        # Sincroniza valores dos widgets com a lista de categorias
        for i, cat in enumerate(categorias):
            pct_key = f"ob_cat_pct_{i}"
            nome_key = f"ob_cat_nome_{i}"
            if pct_key in st.session_state:
                categorias[i]['pct'] = int(round(st.session_state[pct_key]))
            if nome_key in st.session_state:
                categorias[i]['nome'] = st.session_state[nome_key]

        # Calcula total atual (já sincronizado)
        total_pct = sum(int(round(cat.get('pct', 0))) for cat in categorias)

        # Barra global de 100%
        barra_cor = "#2ecc71" if total_pct == 100 else ("#f39c12" if total_pct < 100 else "#e74c3c")
        barra_width = min(total_pct, 100)

        st.markdown(f"""
            <div style="background:#f1f2f6; border-radius:10px; padding:15px; margin-bottom:20px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <strong>Distribuição Total</strong>
                    <strong style="color:{barra_cor};">{total_pct}% / 100%</strong>
                </div>
                <div style="background:#e0e0e0; border-radius:6px; height:20px;">
                    <div style="background:{barra_cor}; width:{barra_width}%; height:20px; border-radius:6px;
                                transition: width 0.3s ease;"></div>
                </div>
                {'<div style="color:#e74c3c; font-size:12px; margin-top:5px;"> O total ultrapassou 100%!</div>' if total_pct > 100 else ''}
                {'<div style="color:#f39c12; font-size:12px; margin-top:5px;">Faltam ' + str(100 - total_pct) + '% para completar.</div>' if total_pct < 100 else ''}
            </div>
        """, unsafe_allow_html=True)

        # Edição de categorias
        for i, cat in enumerate(categorias):
            col_icon, col_nome, col_pct, col_del = st.columns([0.5, 3, 2, 0.5])

            with col_icon:
                st.markdown(f"<div style='font-size:24px; padding-top:25px;'>{cat.get('icone', '')}</div>",
                            unsafe_allow_html=True)

            with col_nome:
                st.text_input("Categoria", value=cat['nome'], key=f"ob_cat_nome_{i}",
                                          label_visibility="collapsed")

            with col_pct:
                st.number_input(
                    "%", min_value=0, max_value=100, value=int(round(cat.get('pct', 0))),
                    step=1, key=f"ob_cat_pct_{i}", label_visibility="collapsed"
                )

            with col_del:
                if st.button("", key=f"ob_del_{i}"):
                    categorias.pop(i)
                    st.session_state.onboarding_categorias = categorias
                    st.rerun()

        # Adicionar categoria
        st.markdown("---")
        col_add_nome, col_add_pct, col_add_btn = st.columns([3, 1, 1])
        with col_add_nome:
            nova_cat = st.text_input("Nova categoria", placeholder="Ex: Pets, Assinaturas...",
                                     key="ob_nova_cat", label_visibility="collapsed")
        with col_add_pct:
            nova_pct = st.number_input("% Nova", min_value=0, max_value=100, value=0,
                                       step=1, key="ob_nova_pct", label_visibility="collapsed")
        with col_add_btn:
            if st.button("", key="ob_add_cat"):
                if nova_cat.strip():
                    categorias.append({
                        "nome": nova_cat.strip(), "pct": nova_pct,
                        "icone": "", "subs": []
                    })
                    st.session_state.onboarding_categorias = categorias
                    st.rerun()

        st.session_state.onboarding_categorias = categorias

        # Navegação
        st.markdown("---")
        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.onboarding_step = 1
                st.rerun()
        with col_next:
            if total_pct == 100:
                if st.button("Próximo →", type="primary", use_container_width=True):
                    st.session_state.onboarding_step = 3
                    st.rerun()
            else:
                st.button("Próximo →", use_container_width=True, disabled=True,
                           help="Ajuste os percentuais para somar 100%")

    @staticmethod
    def _step_confirmacao():
        """Passo 3: Confirmação e salvamento."""
        st.markdown("### Passo 3: Confirme sua configuração")
        st.caption("Revise suas categorias antes de salvar. Você pode alterar tudo depois em Cadastros.")

        categorias = st.session_state.get('onboarding_categorias', [])
        perfil = st.session_state.get('onboarding_perfil', 'Personalizado')

        st.info(f"Perfil: **{perfil}**")

        # Preview visual
        for cat in categorias:
            pct = cat.get('pct', 0)
            cor = "#2ecc71" if pct <= 20 else ("#f39c12" if pct <= 40 else "#3498db")
            icone = cat.get('icone', '')
            subs_text = ", ".join(cat.get('subs', [])) if cat.get('subs') else "Sem subcategorias"

            st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; 
                            background:#f8f9fa; padding:10px 15px; border-radius:8px;">
                    <div style="font-size:20px;">{icone}</div>
                    <div style="flex:1;">
                        <div style="font-weight:bold;">{cat['nome']}</div>
                        <div style="font-size:11px; color:#888;">{subs_text}</div>
                    </div>
                    <div style="background:{cor}; color:white; padding:4px 12px; border-radius:12px; 
                                font-weight:bold; font-size:14px;">{pct}%</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        col_back, col_save = st.columns(2)
        with col_back:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.onboarding_step = 2
                st.rerun()
        with col_save:
            if st.button(" Salvar e Começar!", type="primary", use_container_width=True):
                OnboardingManager._salvar_configuracao(categorias)

    @staticmethod
    def _salvar_configuracao(categorias):
        """Salva categorias + subcategorias no banco e marca onboarding como concluído."""
        user_id = db.get_user_id()

        for cat in categorias:
            # Insere categoria macro
            db.executar(
                "INSERT INTO categorias (nome, percentual_meta, icone, ativa, user_id) "
                "VALUES (%s, %s, %s, TRUE, %s) ON CONFLICT (nome, user_id) DO UPDATE "
                "SET percentual_meta = EXCLUDED.percentual_meta, icone = EXCLUDED.icone",
                (cat['nome'], cat.get('pct', 0), cat.get('icone', ''), user_id)
            )

            # Busca ID da categoria inserida
            cat_row = db.buscar_um(
                "SELECT id FROM categorias WHERE nome = %s AND user_id = %s",
                (cat['nome'], user_id)
            )
            if cat_row:
                cat_id = cat_row[0]
                for sub in cat.get('subs', []):
                    db.executar(
                        "INSERT INTO subcategorias (nome, categoria_id, ativa, user_id) "
                        "VALUES (%s, %s, TRUE, %s) ON CONFLICT (nome, categoria_id, user_id) DO NOTHING",
                        (sub, cat_id, user_id)
                    )

        # Marca onboarding como concluído
        db.marcar_onboarding_completo(user_id)

        st.success(" Configuração salva com sucesso! Redirecionando...")
        st.session_state.pop('onboarding_step', None)
        st.session_state.pop('onboarding_perfil', None)
        st.session_state.pop('onboarding_categorias', None)
        st.rerun()
