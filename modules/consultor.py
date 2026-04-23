# ==========================================
# MÓDULO: CONSULTOR FINANCEIRO IA
# ==========================================
# Agente de IA usando Claude Haiku para responder perguntas
# sobre gastos, parcelas e uso do sistema.
# Custo estimado: < $0,01 por conversa (Claude Haiku)
# ==========================================

import streamlit as st
import anthropic
from database import db
from datetime import date, timedelta
import pandas as pd

# ==========================================
# PROMPT DO SISTEMA
# ==========================================
SYSTEM_PROMPT_BASE = """Você é o Consultor Financeiro IA do sistema **Finanças Pro 2026**.
Seu papel é ajudar o usuário a entender seus gastos e usar o sistema com confiança.

## SOBRE O SISTEMA (para responder dúvidas de uso):
- **Controle de Caixa**: tela principal para lançar entradas e saídas do dia a dia.
  Para lançar: preencha descrição, valor, tipo (Entrada/Saída), data, banco e subcategoria, depois clique em "Lançar no Caixa".
- **Projeção de Gastos**: controla parcelas de cartão.
  - Aba "Manual": cadastra parcelas manualmente.
  - Aba "Importações": faz upload de PDF da fatura do cartão (Nubank, Itaú, Bradesco, Mercado Pago, Porto Bank) — o sistema extrai os lançamentos automaticamente. Basta fazer upload do PDF, revisar os itens e confirmar.
  - Aba "Previsão": gráficos de compromissos futuros mês a mês.
- **Cadastros**: gerencia categorias, subcategorias e bancos/cartões.
- **Relatórios**: analisa gastos com filtros, exporta em Excel/PDF e mostra Curva ABC.
- **Compensar**: marcar que o dinheiro efetivamente saiu/entrou da conta.
- **Arquivar categoria**: oculta a categoria dos formulários sem perder o histórico.

## REGRAS:
- Responda sempre em **português do Brasil**, de forma direta e amigável.
- Use formatação markdown (negrito, listas) para facilitar a leitura.
- Quando mencionar valores, use o formato **R$ X.XXX,XX**.
- Se o usuário perguntar algo que você não sabe com os dados disponíveis, diga claramente.
- Não invente dados que não estejam no contexto financeiro fornecido.
- Use emojis com moderação para deixar a resposta mais visual.

## DADOS FINANCEIROS DO USUÁRIO:
{contexto_financeiro}
"""


# ==========================================
# GERENCIADOR DO CONSULTOR
# ==========================================
class ConsultorManager:

    @staticmethod
    def _buscar_contexto_financeiro(user_id: int) -> str:
        """
        Monta um resumo financeiro do usuário para contexto do agente.
        Busca apenas o essencial para minimizar tokens (custo).
        """
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        tres_meses_atras = (hoje - timedelta(days=90)).replace(day=1)

        linhas = [f"Data de referência: {hoje.strftime('%d/%m/%Y')}"]

        # --- Resumo financeiro do mês atual ---
        df_mes = db.buscar(
            """
            SELECT t.descricao, t.valor, t.data_vencimento,
                   cat.nome AS categoria, c.nome AS conta, t.compensado
            FROM transacoes t
            LEFT JOIN categorias cat ON t.categoria_id = cat.id
            LEFT JOIN contas c ON t.conta_id = c.id
            WHERE t.user_id = %s
              AND t.data_vencimento >= %s
            ORDER BY t.data_vencimento DESC
            LIMIT 60
            """,
            (user_id, inicio_mes),
        )

        if not df_mes.empty:
            entradas = df_mes[df_mes["valor"] > 0]["valor"].sum()
            saidas = df_mes[df_mes["valor"] < 0]["valor"].sum()
            saldo = df_mes["valor"].sum()
            comp = df_mes["compensado"].sum() if "compensado" in df_mes else 0

            linhas.append(
                f"\n### Resumo do mês atual ({inicio_mes.strftime('%m/%Y')})\n"
                f"- Entradas: R$ {entradas:,.2f}\n"
                f"- Saídas: R$ {abs(saidas):,.2f}\n"
                f"- Saldo: R$ {saldo:,.2f}\n"
                f"- Lançamentos: {len(df_mes)} ({int(comp)} compensados)"
            )

            # Últimos 10 lançamentos
            linhas.append("\n### Últimos lançamentos do mês")
            for _, row in df_mes.head(10).iterrows():
                status = "?" if row.get("compensado") else "?"
                cat = f" | {row['categoria']}" if row.get("categoria") else ""
                linhas.append(
                    f"{status} {row['data_vencimento']} | {row['descricao']} | R$ {row['valor']:,.2f}{cat}"
                )
        else:
            linhas.append("\n### Mês atual\nNenhum lançamento encontrado neste mês.")

        # --- Gastos por categoria (últimos 3 meses) ---
        df_cat = db.buscar(
            """
            SELECT cat.nome AS categoria,
                   cat.percentual_meta,
                   SUM(CASE WHEN t.valor < 0 THEN ABS(t.valor) ELSE 0 END) AS total_saida,
                   SUM(CASE WHEN t.valor > 0 THEN t.valor ELSE 0 END) AS total_entrada,
                   COUNT(*) AS qtd
            FROM transacoes t
            JOIN categorias cat ON t.categoria_id = cat.id
            WHERE t.user_id = %s
              AND t.data_vencimento >= %s
            GROUP BY cat.nome, cat.percentual_meta
            ORDER BY total_saida DESC
            """,
            (user_id, tres_meses_atras),
        )

        if not df_cat.empty:
            linhas.append("\n### Gastos por categoria (últimos 3 meses)")
            for _, row in df_cat.iterrows():
                meta_str = (
                    f" | Meta do orçamento: {row['percentual_meta']}%"
                    if row.get("percentual_meta")
                    else ""
                )
                linhas.append(
                    f"- {row['categoria']}: R$ {row['total_saida']:,.2f} saídas / "
                    f"R$ {row['total_entrada']:,.2f} entradas "
                    f"({int(row['qtd'])} lançamentos){meta_str}"
                )

        # --- Parcelas futuras ---
        try:
            df_parcelas = db.buscar_itens_parcelas_futuras(user_id)
            if not df_parcelas.empty:
                total_parcelas = df_parcelas["valor"].sum()
                linhas.append(
                    f"\n### Parcelas futuras em aberto\n"
                    f"Total de {len(df_parcelas)} parcelas | Valor total: R$ {total_parcelas:,.2f}"
                )
                for _, row in df_parcelas.head(15).iterrows():
                    cartao = row.get("cartao") or "N/A"
                    linhas.append(
                        f"- {row['descricao']} | Parcela {row['parcela_atual']}/{row['parcela_total']} "
                        f"| R$ {row['valor']:,.2f} | {cartao}"
                    )
                if len(df_parcelas) > 15:
                    linhas.append(f"  ... e mais {len(df_parcelas) - 15} parcelas.")
        except Exception:
            pass

        # --- Contas/cartões cadastrados ---
        df_contas = db.buscar(
            "SELECT nome FROM contas WHERE user_id = %s", (user_id,)
        )
        if not df_contas.empty:
            nomes = ", ".join(df_contas["nome"].tolist())
            linhas.append(f"\n### Bancos/Cartões cadastrados\n{nomes}")

        return "\n".join(linhas)

    @staticmethod
    def _get_api_key() -> str | None:
        """Retorna a chave da API Anthropic a partir dos secrets."""
        try:
            return st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
        except Exception:
            return None

    @staticmethod
    def _atualizar_contexto(user_id: int):
        """Força atualização do contexto financeiro no session_state."""
        with st.spinner("?? Carregando seus dados financeiros..."):
            st.session_state.consultor_contexto = ConsultorManager._buscar_contexto_financeiro(user_id)
            st.session_state.consultor_contexto_data = date.today().isoformat()

    @staticmethod
    def renderizar():
        user_id = st.session_state.get("usuario_id")

        # -- Cabeçalho ----------------------------------------------
        st.title("?? Consultor Financeiro IA")
        st.caption("Powered by Claude Haiku · Tire dúvidas sobre seus gastos e o sistema")

        # -- Verifica API Key ----------------------------------------
        api_key = ConsultorManager._get_api_key()
        if not api_key:
            st.error(
                "?? **Chave da API não configurada.**\n\n"
                "Adicione `ANTHROPIC_API_KEY = 'sk-ant-...'` no arquivo `.streamlit/secrets.toml` "
                "ou nas variáveis de ambiente do Streamlit Cloud."
            )
            with st.expander("Como obter a chave?"):
                st.markdown(
                    "1. Acesse [console.anthropic.com](https://console.anthropic.com)\n"
                    "2. Vá em **API Keys ? Create Key**\n"
                    "3. Copie a chave e adicione em `secrets.toml`:\n"
                    "```toml\nANTHROPIC_API_KEY = 'sk-ant-sua-chave-aqui'\n```"
                )
            return

        # -- Inicializa estado ---------------------------------------
        if "consultor_historico" not in st.session_state:
            st.session_state.consultor_historico = []

        # Contexto financeiro: carrega 1x por dia
        hoje_str = date.today().isoformat()
        if (
            "consultor_contexto" not in st.session_state
            or st.session_state.get("consultor_contexto_data") != hoje_str
        ):
            ConsultorManager._atualizar_contexto(user_id)

        # -- Barra de ações ------------------------------------------
        col_title, col_refresh, col_clear = st.columns([5, 1, 1])
        with col_refresh:
            if st.button("?? Atualizar dados", help="Recarrega seus dados financeiros"):
                ConsultorManager._atualizar_contexto(user_id)
                st.toast("Dados atualizados!", icon="?")
        with col_clear:
            if st.button("??? Limpar chat", help="Apaga o histórico da conversa"):
                st.session_state.consultor_historico = []
                st.rerun()

        # -- Sugestões de perguntas (apenas quando chat vazio) -------
        if not st.session_state.consultor_historico:
            st.markdown("#### ?? Perguntas frequentes")
            sugestoes = [
                ("??", "Quanto gastei por categoria este mês?"),
                ("??", "Quais são minhas parcelas futuras?"),
                ("??", "Qual mês terei mais gastos?"),
                ("??", "Como importar minha fatura de cartão?"),
                ("?", "Como lançar uma despesa parcelada?"),
                ("??", "Meu orçamento está saudável?"),
            ]

            col1, col2, col3 = st.columns(3)
            colunas = [col1, col2, col3]
            for i, (icone, texto) in enumerate(sugestoes):
                with colunas[i % 3]:
                    if st.button(
                        f"{icone} {texto}",
                        key=f"sug_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.consultor_pendente = texto
                        st.rerun()

            st.markdown("---")

        # -- Exibe histórico do chat ---------------------------------
        for msg in st.session_state.consultor_historico:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # -- Input do usuário ----------------------------------------
        pergunta = st.chat_input("Pergunte sobre seus gastos ou como usar o sistema...")

        # Pergunta via botão de sugestão tem prioridade
        if "consultor_pendente" in st.session_state:
            pergunta = st.session_state.pop("consultor_pendente")

        # -- Processa pergunta ---------------------------------------
        if pergunta:
            # Exibe mensagem do usuário imediatamente
            with st.chat_message("user"):
                st.markdown(pergunta)
            st.session_state.consultor_historico.append(
                {"role": "user", "content": pergunta}
            )

            # Monta system prompt com contexto financeiro atual
            system_prompt = SYSTEM_PROMPT_BASE.format(
                contexto_financeiro=st.session_state.consultor_contexto
            )

            # Monta histórico de mensagens para a API (sem o contexto repetido)
            mensagens_api = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.consultor_historico
            ]

            # Chama Claude Haiku
            with st.chat_message("assistant"):
                placeholder = st.empty()
                resposta_completa = ""

                try:
                    client = anthropic.Anthropic(api_key=api_key)

                    # Usa streaming para resposta mais rápida e dinâmica
                    with client.messages.stream(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=1024,
                        system=system_prompt,
                        messages=mensagens_api,
                    ) as stream:
                        for text_chunk in stream.text_stream:
                            resposta_completa += text_chunk
                            placeholder.markdown(resposta_completa + "¦")

                    placeholder.markdown(resposta_completa)
                    st.session_state.consultor_historico.append(
                        {"role": "assistant", "content": resposta_completa}
                    )

                except anthropic.AuthenticationError:
                    placeholder.error(
                        "? Chave de API inválida. Verifique o `ANTHROPIC_API_KEY` nas configurações."
                    )
                    st.session_state.consultor_historico.pop()

                except anthropic.RateLimitError:
                    placeholder.warning(
                        "? Limite de requisições atingido. Aguarde alguns segundos e tente novamente."
                    )
                    st.session_state.consultor_historico.pop()

                except Exception as e:
                    placeholder.error(f"? Erro inesperado: {str(e)}")
                    st.session_state.consultor_historico.pop()

        # -- Rodapé informativo --------------------------------------
        if st.session_state.consultor_historico:
            num_msgs = len(st.session_state.consultor_historico)
            tokens_est = num_msgs * 600  # estimativa conservadora
            custo_est = (tokens_est / 1_000_000) * 0.80  # $0.80/M tokens input Haiku
            st.caption(
                f"?? {num_msgs // 2} pergunta(s) nesta sessão · "
                f"Custo estimado: ~${custo_est:.4f} USD"
            )