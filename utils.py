# utils.py

import re
import unicodedata
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import numpy as np
import cv2


# ==========================================
# EXTRAÇÃO INTELIGENTE (PDF → TEXTO)
# ==========================================

def extrair_texto_pdf(file, senha=None):
    texto = ""

    # TENTAR EXTRAÇÃO DIRETA (RÁPIDO E PRECISO)
    try:
        file.seek(0)
        open_kwargs = {}
        if senha:
            open_kwargs["password"] = senha
        with pdfplumber.open(file, **open_kwargs) as pdf:
            for pagina in pdf.pages:
                # Extração padrão
                t = pagina.extract_text()
                if t:
                    texto += t + "\n"
    except Exception as e:
        erro_str = str(e).lower()
        if "password" in erro_str or "encrypted" in erro_str or "decrypt" in erro_str:
            return "__PDF_PROTEGIDO__"
        pass

    # OCR desabilitado por solicitação do usuário
    # if len(texto) < 1000:
    #     try:
    #         file.seek(0)
    #         pdf2image_kwargs = {}
    #         if senha:
    #             pdf2image_kwargs["userpw"] = senha
    #         images = convert_from_bytes(file.read(), dpi=300, **pdf2image_kwargs)
    #
    #         for img in images:
    #             img_np = np.array(img)
    #
    #             gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    #             _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    #
    #             custom_config = r'--oem 3 --psm 6 -l por'
    #             texto += pytesseract.image_to_string(thresh, config=custom_config)
    #
    #     except:
    #         pass

    return texto


# ==========================================
# NORMALIZAÇÃO (ANTI-OCR BUG)
# ==========================================

def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("utf-8")

    correcoes = {
        "R4": "R$",
        "8uros": "juros",
        "zulta": "multa",
        "FO5": "IOF",
    }

    for errado, certo in correcoes.items():
        texto = texto.replace(errado, certo)

    texto = re.sub(r'[^\S\n]+', ' ', texto) # Colapsa espaços mas preserva quebras de linha

    return texto


# ==========================================
# DETECTOR DE BANCO
# ==========================================

def detectar_banco(texto):
    t = texto.lower()

    if "mercado pago" in t:
        return "MERCADO_PAGO"
    elif "porto bank" in t or "portobank" in t or "portoseg" in t or "porto seguro" in t or "cartaoportoseguro" in t:
        return "PORTO_BANK"
    elif "nubank" in t:
        return "NUBANK"
    elif "banco itau" in t or "itau s.a" in t or "financeira itau" in t:
        return "ITAU"
    elif "itau" in t and ("passai" in t or "passaí" in t):
        # Fatura Itaú com compras no Assaí/Passaí — é Itaú
        return "ITAU"
    elif "passai" in t or "passaí" in t:
        return "PASSAI"
    elif "itau" in t:
        return "ITAU"
    elif "bradesco" in t:
        return "BRADESCO"

    return "GENÉRICO"


# ==========================================
# PARSER - MERCADO PAGO (SEU CASO)
# ==========================================

def parser_mercado_pago(texto):
    padrao = re.findall(
        r'([A-Z0-9\s]+?)\s+Parcela\s+(\d+)\s+de\s+(\d+)\s+R\$\s*([\d\.,]+)',
        texto
    )

    dados = []

    for desc, atual, total, valor in padrao:
        try:
            valor = float(valor.replace('.', '').replace(',', '.'))
            dados.append((desc.strip(), f"{atual}/{total}", valor))
        except:
            return

    return dados


# ==========================================
# PARSER GENÉRICO (OUTROS BANCOS)
# ==========================================

def parser_generico(texto):
    padrao = re.findall(
        r'(.+?)\s+(\d{1,2}/\d{1,2})\s+R\$\s*([\d\.,]+)',
        texto
    )

    dados = []

    for desc, parc, valor in padrao:
        try:
            valor = float(valor.replace('.', '').replace(',', '.'))
            dados.append((desc.strip(), parc, valor))
        except:
            continue

    return dados


# ==========================================
# ORQUESTRADOR PRINCIPAL
# ==========================================

def _split_multicolunas(texto):
    """Divide linhas com múltiplas transações (formato Itaú 2 colunas).

    O pdfplumber extrai faturas Itaú em layout de 2 colunas, mesclando
    duas transações por linha. Ex:
      '28/02 ASSAI 347,53 01/03 Conveniencia 22,04'
    Se torna:
      '28/02 ASSAI 347,53'
      '01/03 Conveniencia 22,04'
    """
    linhas_out = []
    for linha in texto.split('\n'):
        import re

def limpar_linha(linha):
    linha = linha.strip()

    # remove parênteses quebrados
    linha = linha.replace("(", "").replace(")", "")

    # corrige texto colado (DIFERENCI04/12 → DIFERENCI 04/12)
    linha = re.sub(r'([A-Z])(\d{2}/\d{2})', r'\1 \2', linha)

    # corrige "- 0,01" → "-0,01"
    linha = re.sub(r'-\s+(\d)', r'-\1', linha)

    # remove múltiplos espaços
    linha = re.sub(r'\s+', ' ', linha)

    return linha
    linha = limpar_linha(linha)
        # Primeiro: separa quando um valor é seguido por marcador Itaú (L, S, E, P)
        # Ex: "10/12 DROGRARIA SAO 04/04 51,87 L Total dos lancamentos atuais 1.579,37"
        # → "10/12 DROGRARIA SAO 04/04 51,87" (descarta o resto que é resumo)
    linha_split_marker = re.sub(
            r'(\d{1,3}(?:\.\d{3})*,\d{2})\s+[LSEP]\s+(?:Total|Lancamentos|Credito).*',
            r'\1',
            linha, flags=re.IGNORECASE
        )

        # Divide onde um valor monetário (NNN,NN ou -NNN,NN) é seguido por DD/MM (nova transação)
    partes = re.split(
            r'(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(?=\d{1,2}/\d{1,2}\b)',
            linha_split_marker
        )

    if len(partes) >= 3:
            # partes alternadas: [texto0, valor0, texto1, valor1, ..., textoN]
            i = 0
            while i < len(partes) - 1:
                combined = (partes[i].strip() + ' ' + partes[i + 1]).strip()
                if combined:
                    linhas_out.append(combined)
                i += 2
            # Último segmento (última transação da linha)
            if i < len(partes) and partes[i].strip():
                linhas_out.append(partes[i].strip())
    else:
            # Sem split multi-coluna — verifica se há transação DD/MM embarcada
            # Ex: "RAFAELRODRIGUES(final8122) 04/03 BURGERKING 118,30"
            stripped = linha_split_marker.strip()
            if stripped and not re.match(r'\d{1,2}/\d{1,2}\b', stripped):
                m = re.search(
                    r'(\d{1,2}/\d{1,2}\s+\S.*?\s+\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
                    stripped
                )
                if m:
                    linhas_out.append(m.group(1))
                else:
                    linhas_out.append(linha_split_marker)
            else:
                linhas_out.append(linha_split_marker)

    return '\n'.join(linhas_out)
    
def _cortar_texto_antes_proximas_faturas(texto):
    """Remove tudo a partir de 'Compras parceladas - próximas faturas' e seções similares.
    
    Essas seções listam parcelas que cairão em faturas FUTURAS e não devem
    ser importadas — o sistema já projeta parcelas futuras automaticamente.
    """
    # Padrões específicos de seções de parcelas futuras.
    # Os padrões amplos (ex: 'Proximas faturas') requerem início de linha
    # para não casar com menções no cabeçalho como 'Data proxima fatura: 15/04'.
    padroes_corte = [
        # Formato Itaú: "Compras parceladas - próximas faturas"
        r'Compras\s+parceladas\s*[-–—:]\s*proximas?\s+faturas?',
        # Seção genérica (somente como título de linha, não no meio de texto)
        r'(?:^|\n)\s*Proximas?\s+faturas?\s*(?:\n|$)',
        # Seção "Demais faturas" (somente como título de linha)
        r'(?:^|\n)\s*Demais\s+faturas?\s*(?:\n|$)',
        # Formato descritivo
        r'Compras\s+que\s+serao\s+cobradas',
    ]
    for padrao in padroes_corte:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            return texto[:match.start()]
    return texto


def _extrair_secao_parceladas(texto):
    """Extrai apenas a seção de compras parceladas de faturas Itaú/similares.
    
    Retorna o texto da seção ou string vazia se não encontrar.
    """
    # Busca seções como "Compras parceladas" que indicam parcelas reais
    padrao_secao = re.search(
        r'(?:Compras\s+parceladas|Parcelas\s+futuras|proximas\s+faturas).*?'
        r'((?:.*?\n)*?)'
        r'(?:Proxima\s+fatura|Total\s+para|Demais\s+faturas|Limites\s+de|$)',
        texto, re.IGNORECASE | re.DOTALL
    )
    if padrao_secao:
        return padrao_secao.group(0)
    return ""


def _is_data_transacao(valor_str):
    """Verifica se um valor XX/YY parece ser uma data de transação (DD/MM) e não parcela."""
    try:
        dd, mm = map(int, valor_str.split("/"))
        # Datas: dia 1-31, mês 1-12
        # Parcelas: geralmente total > 1 e atual <= total
        # Se mm <= 12 e dd <= 31, provavelmente é data
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            return True
    except (ValueError, AttributeError):
        pass
    return False


def _is_parcela_valida(parc_str):
    """Verifica se XX/YY é uma parcela válida (não é data). Inclui à vista (1/1)."""
    try:
        atual, total = map(int, parc_str.split("/"))
        # Parcela válida: total >= 1 e atual <= total
        if total >= 1 and 1 <= atual <= total:
            return True
        return False
    except (ValueError, AttributeError):
        return False


def extrair_parcelas(texto):
    import re
    if not texto:
        return []
    resultados = []
    chaves_vistas = set() # (desc_normalizada, parcela, valor) para evitar duplicatas reais

    # 1. Limpeza de ruídos comuns de OCR
    texto = texto.replace("R4", "R$").replace("I0F", "IOF")

    def _add_resultado(desc, parc, val):
        """Adiciona resultado evitando duplicatas reais (mesma desc + mesma parcela + mesmo valor).
        
        Duas compras no mesmo estabelecimento com mesma parcela mas valores
        diferentes são transações distintas (ex: 2x ATACADAO 02/02).
        """
        # Normaliza a descrição removendo datas iniciais, "Parcela" e espaços extras
        desc_norm = re.sub(r'^\d{1,2}/\d{1,2}\s+', '', desc.strip()).strip()
        desc_norm = re.sub(r'\s*Parcela\s*$', '', desc_norm, flags=re.IGNORECASE).strip()
        desc_upper = desc_norm.upper()
        val_round = round(val, 2)
        
        # Verifica se já existe uma parcela com mesma numeração, valor e descrição similar
        for existing_desc, existing_parc, existing_val in chaves_vistas:
            if existing_parc != parc or existing_val != val_round:
                continue
            if existing_desc in desc_upper or desc_upper in existing_desc:
                return False
        
        chave = (desc_upper, parc, val_round)
        if chave not in chaves_vistas:
            chaves_vistas.add(chave)
            resultados.append((desc_norm, parc, val))
            return True
        return False

    # ==============================================================
    # PASSO 1: Tentar extrair da seção "Compras parceladas" (Itaú)
    # ==============================================================
    secao_parceladas = _extrair_secao_parceladas(texto)
    if secao_parceladas:
        # Dentro da seção parcelada, formato típico:
        # DD/MM DESCRICAOXX/YY VALOR ou DD/MM DESCRICAO XX/YY VALOR
        regex_secao = re.findall(
            r'(\d{1,2}/\d{1,2})\s+(.+?)(\d{1,2}/\d{1,2})\s*(?:R\$\s*)?([\d\.,]+,\d{2})',
            secao_parceladas, re.IGNORECASE
        )
        for date_str, desc, parc, valor in regex_secao:
            try:
                val_limpo = float(valor.replace(".", "").replace(",", "."))
                atual_p, total_p = map(int, parc.split("/"))
                # Se atual == total e ambos <= 12, é data - pular
                if atual_p == total_p and atual_p <= 12:
                    continue
                if _is_parcela_valida(parc):
                    _add_resultado(desc.strip(), parc, val_limpo)
            except: continue

    # ==============================================================
    # PASSO 2: Padrões genéricos para outros bancos
    # ==============================================================
    
    # PADRÃO A: "Descricao Parcela 01 de 10 R$ 100,00" (Mercado Pago / Nubank)
    regex_extenso = re.findall(
        r'(.+?)\s+Parcela\s+(\d{1,2})\s+de\s+(\d{1,2})\s+R\$\s?([\d\.,]+)', 
        texto, re.IGNORECASE
    )
    for desc, atual, total, valor in regex_extenso:
        try:
            val_limpo = float(valor.replace(".", "").replace(",", "."))
            parc_formatada = f"{int(atual)}/{int(total)}"
            if _is_parcela_valida(parc_formatada):
                _add_resultado(desc.strip(), parc_formatada, val_limpo)
        except: continue

    # PADRÃO B: "Descricao 01/10 R$ 100,00" (Itaú / Santander)
    regex_barra = re.findall(
        r'(.+?)\s+(\d{1,2}/\d{1,2})\s+R\$\s?([\d\.,]+)', 
        texto, re.IGNORECASE
    )
    for desc, parc, valor in regex_barra:
        try:
            val_limpo = float(valor.replace(".", "").replace(",", "."))
            # Só considera como parcela se NÃO for data (ex: 02/02 não é parcela, é data)
            if _is_parcela_valida(parc) and not _is_data_transacao(parc):
                _add_resultado(desc.strip(), parc, val_limpo)
        except: continue

    # PADRÃO C: formato '05 de 10 299,08' (sem palavra 'Parcela')
    # Também pega quando o número cola na desc: 'ALLIANZ SEGU*05 de 10 299,08'
    regex_de = re.findall(
        r'(.+?)\s*(\d{1,2})\s+de\s+(\d{1,2})\s*(?:R\$\s*)?([\d\.,]+,\d{2})',
        texto, re.IGNORECASE
    )
    for desc, atual, total, valor in regex_de:
        try:
            val_limpo = float(valor.replace(".", "").replace(",", "."))
            parc_formatada = f"{int(atual)}/{int(total)}"
            if _is_parcela_valida(parc_formatada):
                _add_resultado(desc.strip(), parc_formatada, val_limpo)
        except: continue

    # PADRÃO D: linhas com data + descrição + parcela + valor
    # Ex: '08/03 VIVO SP LJ N551 12/12 391,74'
    # Ex: '10/02 CARREFOUR COM 02/10 CAJAMAR BR 125,62' (cidade entre parcela e valor)
    # Nota: como a linha já começa com DD/MM (data da compra),
    # o segundo XX/YY é SEMPRE a parcela (nunca uma data).
    # IMPORTANTE: usar [ \t] em vez de \s para NÃO cruzar linhas!
    regex_lead = re.findall(
        r'^[ \t]*(\d{1,2}/\d{1,2})[ \t]+(.+?)[ \t]+(\d{1,2}/\d{1,2})[ \t]+.*?(\d{1,3}(?:\.\d{3})*,\d{2})[ \t]*$',
        texto, re.IGNORECASE | re.MULTILINE
    )
    for date_str, desc, parc, valor in regex_lead:
        try:
            val_limpo = float(valor.replace(".", "").replace(",", "."))
            if _is_parcela_valida(parc):
                _add_resultado(desc.strip(), parc, val_limpo)
        except: continue

    # PADRÃO E: formato relaxado onde o 'xx/yy' cola ao texto
    # Ex: 'AMAZONMKTPLC*FITOW04/05 35,52' ou 'ANUIDADE DIFERENCI05/12 16,65'
    # Nota: usa [ \t] em vez de \s para NÃO casar quebras de linha (evita falsos positivos)
    regex_relax = re.findall(
        r'([A-Za-z*][\w \t.*\-]*?)(\d{1,2}/\d{1,2})\s*(?:R\$\s*)?([\d\.,]+,\d{2})',
        texto, re.IGNORECASE
    )
    for desc, parc, valor in regex_relax:
        try:
            val_limpo = float(valor.replace(".", "").replace(",", "."))
            if _is_parcela_valida(parc):
                _add_resultado(desc.strip(), parc, val_limpo)
        except: continue

    # ================================================================
    # PÓS-PROCESSAMENTO: dedup parcelas consecutivas do mesmo item
    # Itaú mostra parcela atual (ex: 04/12) E a do próximo mês (05/12)
    # no corpo da fatura. Manter apenas a de MENOR número — o sistema
    # projeta as futuras automaticamente ao importar.
    # ================================================================
    by_desc_total = {}  # (desc_base, total, valor) -> (menor_atual, indice)
    for i, (desc, parc, val) in enumerate(resultados):
        try:
            atual, total = map(int, parc.split("/"))
            desc_base = re.sub(r'\s+', ' ', desc.upper().strip())
            key = (desc_base, total, round(val, 2))
            if key not in by_desc_total or atual < by_desc_total[key][0]:
                by_desc_total[key] = (atual, i)
        except:
            pass

    indices_remover = set()
    for i, (desc, parc, val) in enumerate(resultados):
        try:
            atual, total = map(int, parc.split("/"))
            desc_base = re.sub(r'\s+', ' ', desc.upper().strip())
            key = (desc_base, total, round(val, 2))
            if key in by_desc_total and by_desc_total[key][1] != i:
                indices_remover.add(i)
        except:
            pass

    if indices_remover:
        resultados = [r for i, r in enumerate(resultados) if i not in indices_remover]

    return resultados


def _is_compra_avista(parc):
    """Retorna True se a parcela indica compra à vista (01/01, 1/1, etc.)."""
    try:
        atual, total = map(int, parc.split("/"))
        return atual == total # 01/01, 1/1, 03/03, etc.
    except (ValueError, AttributeError):
        return True # Se não conseguiu parsear, considera à vista


# ==========================================
# EXTRAÇÃO DE ITENS À VISTA (SEM PARCELA)
# ==========================================

def extrair_itens_avista(texto, itens_parcelados=None):
    """Extrai itens à vista (sem indicador de parcela) de faturas de cartão.

    Captura linhas no formato DD/MM DESCRICAO VALOR que não foram
    identificadas como parcelas pela função extrair_parcelas().

    Args:
        texto: Texto normalizado da fatura
        itens_parcelados: Lista de (desc, parc, val) já extraídos como parcelas
    Returns:
        Lista de tuplas (descricao, "1/1", valor)
    """

    if not texto:
        return []
    resultados = []

    # Normaliza itens já capturados como parcelas para evitar duplicatas
    # Armazena (desc_normalizada, valor) para detecção precisa:
    # mesma loja com valor diferente é transação DISTINTA (ex: 2x Atacadão)
    parcelados_desc_val = set()  # (desc_normalizada, valor_round)
    if itens_parcelados:
        for desc, parc, val in itens_parcelados:
            desc_norm = re.sub(r'\s+', ' ', desc.upper().strip())
            parcelados_desc_val.add((desc_norm, round(val, 2)))

    # Padrões que indicam linhas de cabeçalho/rodapé (NÃO são transações).
    # Só filtra quando a linha NÃO começa com DD/MM (padrão de transação).
    # Linhas com DD/MM são sempre processadas (são transações reais).
    skip_patterns = [
        'total da fatura', 'total desta fatura', 'total para',
        'total dos lancamentos', 'total dos pagamentos',
        'lancamentos no cartao', 'lancamentos produtos',
        'pagamento efetuado', 'pagamento minimo', 'pagamento pix',
        'saldo financiado', 'saldo anterior',
        'limite total', 'limite de credito',
        'encargos (', 'encargos financ', 'encargos cobrados',
        'encargos refin', 'juros de mora', 'juros do rotativo',
        'multa por atraso', 'iof de financ',
        'lancamentos atuais',
        'credito disponivel',
        'proxima fatura', 'proximas faturas',
        'principal (r$', 'principal(r$',
        'cpf', 'cnpj',
        'demonstrativo', 'informacoes adicionais',
        'central de atendimento', 'ouvidoria',
        'www.', 'http',
    ]


    for linha in texto.split('\n'):
        linha = linha.strip()
        print(f"[DEBUG] Processando linha: {linha}")
        if not linha or len(linha) < 8:
            print(f"[DESCARTADO - LINHA CURTA OU VAZIA] {linha}")
            continue

        linha_lower = linha.lower()
        comeca_com_data = re.match(r'^\d{1,2}/\d{1,2}\s', linha)

        taxas_bancarias = [
            'encargos refin', 'encargos financ', 'encargos de',
            'encargos pix', 'juros de mora',
            'multa por atraso', 'multa ', 'iof ',
            'juros rotativo', 'juros do rotativo',
            'pagamento pix', 'pagamento efetuado',
        ]
        if comeca_com_data:
            resto = re.sub(r'^\d{1,2}/\d{1,2}\s+', '', linha_lower)
            if any(resto.startswith(taxa) for taxa in taxas_bancarias):
                print(f"[DESCARTADO - TAXA BANCÁRIA] {linha}")
                continue

        if not comeca_com_data and any(skip in linha_lower for skip in skip_patterns):
            print(f"[DESCARTADO - CABEÇALHO/RODAPÉ] {linha}")
            continue

        # Regex permissivo: DD/MM <texto> <valor decimal no final>
        match = re.match(r'^(\d{1,2}/\d{1,2})\s+(.+?)\s+(-?\d+[.,]\d{2})\s*$', linha)
        if not match:
            # Tenta pegar valor colado ao final (ex: texto com valor grudado)
            match_valor = re.search(r'(-?\d+[.,]\d{2})$', linha)
            if not match_valor:
                print(f"[DESCARTADO - SEM VALOR] {linha}")
                continue
            valor_str = match_valor.group(1)
            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
            except Exception:
                print(f"[DESCARTADO - VALOR INVÁLIDO] {linha}")
                continue
            descricao = linha[:match_valor.start()].strip()
            descricao = re.sub(r'^\d{1,2}/\d{1,2}\s+', '', descricao)
            desc_norm = re.sub(r'\s+', ' ', descricao.upper().strip())
            desc_base = re.sub(r'\s*\d{1,2}/\d{1,2}\s*', ' ', desc_norm).strip()
            val_round = round(valor, 2)
            if (desc_norm, val_round) in parcelados_desc_val or (desc_base, val_round) in parcelados_desc_val:
                print(f"[DESCARTADO - DUPLICATA PARCELADO] {linha}")
                continue
            if any(
                (dp in desc_norm or desc_norm in dp) and v == val_round
                for dp, v in parcelados_desc_val
            ):
                print(f"[DESCARTADO - DUPLICATA SUBSTRING] {linha}")
                continue
            print(f"[ACEITO - AVISTA] {descricao} | {valor}")
            resultados.append((descricao, "1/1", valor))
            continue

        date_str, desc_raw, valor_str = match.groups()
        try:
            dd, mm = map(int, date_str.split('/'))
            if not (1 <= dd <= 31 and 1 <= mm <= 12):
                print(f"[DESCARTADO - DATA INVÁLIDA] {linha}")
                continue
        except (ValueError, AttributeError):
            print(f"[DESCARTADO - DATA INVÁLIDA] {linha}")
            continue

        desc = desc_raw.strip()
        try:
            val = float(valor_str.replace(".", "").replace(",", "."))
            if abs(val) < 0.01:
                print(f"[DESCARTADO - VALOR MUITO PEQUENO] {linha}")
                continue
        except (ValueError, TypeError):
            print(f"[DESCARTADO - VALOR INVÁLIDO] {linha}")
            continue

        desc_norm = re.sub(r'\s+', ' ', desc.upper().strip())
        desc_base = re.sub(r'\s*\d{1,2}/\d{1,2}\s*', ' ', desc_norm).strip()
        val_round = round(val, 2)
        if (desc_norm, val_round) in parcelados_desc_val or (desc_base, val_round) in parcelados_desc_val:
            print(f"[DESCARTADO - DUPLICATA PARCELADO] {linha}")
            continue
        if any(
            (dp in desc_norm or desc_norm in dp) and v == val_round
            for dp, v in parcelados_desc_val
        ):
            print(f"[DESCARTADO - DUPLICATA SUBSTRING] {linha}")
            continue

        print(f"[ACEITO - AVISTA] {desc} | {val}")
        resultados.append((desc, "1/1", val))

    return resultados


# ==========================================
# EXTRAÇÃO VIA COORDENADAS (MULTI-COLUNA)
# ==========================================

def _extrair_texto_words_pdf(file, senha=None):
    """Extrai texto via extract_words() com separação por colunas.

    Reconstrói linhas a partir das coordenadas de cada palavra no PDF.
    Mais robusto que extract_text() para layouts multi-coluna (ex: Itaú)
    onde extract_text() mescla ou perde transações inteiras.
    """
    texto = ""
    open_kwargs = {}
    if senha:
        open_kwargs["password"] = senha

    try:
        file.seek(0)
        with pdfplumber.open(file, **open_kwargs) as pdf:
            for pagina in pdf.pages:
                words = pagina.extract_words(
                    keep_blank_chars=True,
                    use_text_flow=False,
                    x_tolerance=3,
                    y_tolerance=3,
                )
                if not words:
                    continue

                # Agrupa palavras por posição Y (mesma linha visual)
                linhas = {}
                for w in words:
                    y_key = round(w['top'] / 3) * 3
                    if y_key not in linhas:
                        linhas[y_key] = []
                    linhas[y_key].append(w)

                for y_key in sorted(linhas.keys()):
                    row = sorted(linhas[y_key], key=lambda w: w['x0'])

                    # Separa segmentos em gaps horizontais grandes (>30pt = coluna)
                    segments = []
                    seg = [row[0]]
                    for i in range(1, len(row)):
                        gap = row[i]['x0'] - row[i - 1]['x1']
                        if gap > 30:
                            segments.append(seg)
                            seg = [row[i]]
                        else:
                            seg.append(row[i])
                    segments.append(seg)

                    for s in segments:
                        line_text = ' '.join(w['text'] for w in s)
                        if line_text.strip():
                            texto += line_text.strip() + "\n"
    except:
        pass

    return texto


# ==========================================
# FUNÇÃO FINAL (USO SIMPLES)
# ==========================================

def processar_fatura(file, senha_pdf=None, incluir_avista=True):
    """Processa uma fatura PDF extraindo todos os itens.

    Args:
        file: Arquivo PDF da fatura
        senha_pdf: Senha do PDF (se houver)
        incluir_avista: Se True, inclui itens à vista (sem parcela) além dos parcelados
    Returns:
        Tupla (banco_detectado, texto_extraido, lista_de_itens)
        Cada item é uma tupla (descricao, parcela_str, valor)
    """
    try:
        # 1. Extrair texto básico (para exibição debug e detecção de banco)
        texto = extrair_texto_pdf(file, senha_pdf)

        if not texto or texto.strip() == "":
            return "DESCONHECIDO", "", [], ""

        if texto.strip() == "__PDF_PROTEGIDO__":
            return "__PDF_PROTEGIDO__", "", [], ""

        # 2. Normalizar texto (remover acentos para regex funcionar)
        texto_norm = normalizar_texto(texto)

        # 3. Detectar banco (usa texto normalizado)
        banco = detectar_banco(texto_norm)

        # 4. Preparar candidatos de extração — cada um com pipeline independente
        #    (normalizar → cortar próximas faturas → split multicolunas)
        #    Antes, concatenávamos tudo e o corte "próximas faturas" eliminava
        #    dados de outros métodos de extração.
        def _preparar_candidato(texto_raw):
            tn = normalizar_texto(texto_raw)
            tc = _cortar_texto_antes_proximas_faturas(tn)
            return _split_multicolunas(tc)

        def _contar_transacoes(t):
            return len(re.findall(r'^\d{1,2}/\d{1,2}\s+\S', t, re.MULTILINE))

        candidatos = []

        # Candidato A: extract_text() padrão
        texto_a = _preparar_candidato(texto)
        candidatos.append(("extract_text", texto_a, _contar_transacoes(texto_a)))

        # Candidato B: extract_words() (separação por coordenadas — multi-coluna)
        texto_words_raw = _extrair_texto_words_pdf(file, senha_pdf)
        if texto_words_raw.strip():
            texto_b = _preparar_candidato(texto_words_raw)
            candidatos.append(("extract_words", texto_b, _contar_transacoes(texto_b)))

        # Candidato C: extract_text(layout=True) (preserva posição de colunas)
        try:
            file.seek(0)
            open_kwargs = {"password": senha_pdf} if senha_pdf else {}
            texto_layout_raw = ""
            with pdfplumber.open(file, **open_kwargs) as pdf_l:
                for pagina in pdf_l.pages:
                    tl = pagina.extract_text(layout=True)
                    if tl:
                        texto_layout_raw += tl + "\n"
            if texto_layout_raw.strip():
                texto_c = _preparar_candidato(texto_layout_raw)
                candidatos.append(("layout", texto_c, _contar_transacoes(texto_c)))
        except:
            pass

        # Candidato D: crop por colunas (recorta página em metade esq/dir)
        # Essencial para Itaú que usa layout 2 colunas onde extract_text()
        # mescla as colunas e perde transações da coluna esquerda.
        try:
            file.seek(0)
            open_kwargs = {"password": senha_pdf} if senha_pdf else {}
            texto_crop_raw = ""
            with pdfplumber.open(file, **open_kwargs) as pdf_crop:
                for pagina in pdf_crop.pages:
                    w = pagina.width
                    h = pagina.height
                    # Metade esquerda (compras e saques no Itaú)
                    left = pagina.crop((0, 0, w * 0.48, h))
                    t_left = left.extract_text() or ""
                    # Metade direita (produtos e serviços no Itaú)
                    right = pagina.crop((w * 0.48, 0, w, h))
                    t_right = right.extract_text() or ""
                    texto_crop_raw += t_left + "\n" + t_right + "\n"
            if texto_crop_raw.strip():
                texto_d = _preparar_candidato(texto_crop_raw)
                candidatos.append(("crop_columns", texto_d, _contar_transacoes(texto_d)))
        except:
            pass

        # 5. Escolhe o candidato com MAIS transações DD/MM
        candidatos.sort(key=lambda c: c[2], reverse=True)
        melhor_nome, texto_fatura_atual, n_tx = candidatos[0]
        print(f"[DEBUG] Candidatos: {[(c[0], c[2]) for c in candidatos]}")
        print(f"[DEBUG] Usando {melhor_nome} ({n_tx} transações)")

        # 6. Extrair parcelas (itens com indicador XX/YY) — apenas da fatura atual
        dados_parcelados = extrair_parcelas(texto_fatura_atual)
        print(f"[DEBUG] Parcelas encontradas: {len(dados_parcelados)}")

        # 7. Extrair itens à vista (sem indicador de parcela) — apenas da fatura atual
        if incluir_avista:
            dados_avista = extrair_itens_avista(texto_fatura_atual, dados_parcelados)
            print(f"[DEBUG] Itens à vista encontrados: {len(dados_avista)}")
            dados = dados_parcelados + dados_avista
        else:
            dados = dados_parcelados

        return banco, texto, _dedup_itens(dados), melhor_nome

    except Exception as e:
        print("Erro ao processar fatura:", e)
        return "ERRO", "", [], ""


def _dedup_itens(dados):
    """Remove duplicatas de parcelas (mesma desc + mesma parcela + mesmo valor).
    
    Itens à vista (1/1) são mantidos mesmo que tenham mesma descrição
    (ex: 3x TagItau 50,00 são cobranças reais distintas).
    
    Duas compras no mesmo estabelecimento com mesma parcela mas valores
    diferentes são transações distintas (ex: 2x ATACADAO 02/02).
    """
    seen_desc_parc = set()  # (desc_norm, parc, valor)
    resultado = []
    for desc, parc, val in dados:
        desc_norm = re.sub(r'\s+', ' ', desc.upper().strip())
        desc_base = re.sub(r'\s*\d{1,2}/\d{1,2}\s*', ' ', desc_norm).strip()
        val_round = round(val, 2)
        key = (desc_norm, parc, val_round)
        key_base = (desc_base, parc, val_round)

        # Permite múltiplas compras idênticas à vista (parc == '1/1')
        if parc == '1/1':
            resultado.append((desc, parc, val))
            continue

        # Para parcelas, deduplica normalmente
        if key in seen_desc_parc or key_base in seen_desc_parc:
            continue
        seen_desc_parc.add(key)
        seen_desc_parc.add(key_base)
        resultado.append((desc, parc, val))
    return resultado


def processar_texto_colado(texto_raw, incluir_avista=True):
    """Processa texto colado manualmente (copiado do PDF pelo usuário).

    Quando a extração automática falha em PDFs multi-coluna, o usuário
    pode selecionar e copiar o texto do PDF e colar aqui.

    Returns:
        Tupla (banco_detectado, texto_normalizado, lista_de_itens, metodo)
    """
    if not texto_raw or not texto_raw.strip():
        return "DESCONHECIDO", "", [], "texto_colado"

    texto_norm = normalizar_texto(texto_raw)
    banco = detectar_banco(texto_norm)
    texto_cortado = _cortar_texto_antes_proximas_faturas(texto_norm)
    texto_processado = _split_multicolunas(texto_cortado)

    dados_parcelados = extrair_parcelas(texto_processado)

    if incluir_avista:
        dados_avista = extrair_itens_avista(texto_processado, dados_parcelados)
        dados = dados_parcelados + dados_avista
    else:
        dados = dados_parcelados

    return banco, texto_norm, _dedup_itens(dados), "texto_colado"


# ==========================================
# FUNÇÕES UTILITÁRIAS - FORMATAÇÃO
# ==========================================

def moeda(valor):
    """Formata valor como moeda brasileira (R$)."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_cor_saldo(saldo):
    """Retorna cor baseada no saldo (positivo=verde, negativo=vermelho)."""
    if saldo >= 0:
        return "#10B981" # Verde
    else:
        return "#EF4444" # Vermelho

def get_cor_valor(valor):
    """Retorna cor baseada no valor (positivo=verde, negativo=vermelho)."""
    if valor >= 0:
        return "#10B981" # Verde
    else:
        return "#EF4444" # Vermelho