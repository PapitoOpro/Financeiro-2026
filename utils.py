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
                t = pagina.extract_text()
                if t:
                    texto += t + "\n"
    except:
        pass

    # FALLBACK OCR (SE TEXTO VEIO RUIM)
    if len(texto) < 1000:
        try:
            file.seek(0)
            pdf2image_kwargs = {}
            if senha:
                pdf2image_kwargs["userpw"] = senha
            images = convert_from_bytes(file.read(), dpi=300, **pdf2image_kwargs)

            for img in images:
                img_np = np.array(img)

                gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

                custom_config = r'--oem 3 --psm 6 -l por'
                texto += pytesseract.image_to_string(thresh, config=custom_config)

        except:
            pass

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
            continue

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

def _cortar_texto_antes_proximas_faturas(texto):
    """Remove tudo a partir de 'Compras parceladas - próximas faturas' e seções similares.
    
    Essas seções listam parcelas que cairão em faturas FUTURAS e não devem
    ser importadas — o sistema já projeta parcelas futuras automaticamente.
    """
    padroes_corte = [
        r'Compras\s+parceladas\s*[-–—]\s*proximas?\s+faturas?',
        r'Proximas?\s+faturas?',
        r'Demais\s+faturas?',
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
    resultados = []
    chaves_vistas = set() # (desc_normalizada, parcela) para evitar duplicatas reais

    # 1. Limpeza de ruídos comuns de OCR
    texto = texto.replace("R4", "R$").replace("I0F", "IOF")

    def _add_resultado(desc, parc, val):
        """Adiciona resultado evitando duplicatas reais (mesma desc + mesma parcela)."""
        # Normaliza a descrição removendo datas iniciais, "Parcela" e espaços extras
        desc_norm = re.sub(r'^\d{1,2}/\d{1,2}\s+', '', desc.strip()).strip()
        desc_norm = re.sub(r'\s*Parcela\s*$', '', desc_norm, flags=re.IGNORECASE).strip()
        desc_upper = desc_norm.upper()
        
        # Verifica se já existe uma parcela com mesma numeração e descrição similar
        for existing_desc, _ in chaves_vistas:
            if existing_desc in desc_upper or desc_upper in existing_desc:
                # Mesma parcela, descrição é substring - duplicata
                if (existing_desc, parc) in chaves_vistas or (desc_upper, parc) in chaves_vistas:
                    return False
        
        chave = (desc_upper, parc)
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
            if _is_parcela_valida(parc):
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
    # Só pega se o segundo XX/YY tem total > 12 (não pode ser mês) OU
    # se o total > atual (indica parcela, não data)
    regex_lead = re.findall(
        r'^\s*(\d{1,2}/\d{1,2})\s+(.+?)\s+(\d{1,2}/\d{1,2})\s*(?:R\$\s*)?([\d\.,]+,\d{2})',
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
    regex_relax = re.findall(
        r'([A-Za-z*][\w\s.*\-]*?)(\d{1,2}/\d{1,2})\s*(?:R\$\s*)?([\d\.,]+,\d{2})',
        texto, re.IGNORECASE
    )
    for desc, parc, valor in regex_relax:
        try:
            val_limpo = float(valor.replace(".", "").replace(",", "."))
            if _is_parcela_valida(parc):
                _add_resultado(desc.strip(), parc, val_limpo)
        except: continue

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
    resultados = []
    chaves_vistas = set()

    # Normaliza descrições já capturadas como parcelas para evitar duplicatas
    descs_parceladas = set()
    if itens_parcelados:
        for desc, _, _ in itens_parcelados:
            descs_parceladas.add(re.sub(r'\s+', ' ', desc.upper().strip()))

    # Padrões que indicam linhas de cabeçalho/rodapé (NÃO são transações).
    # Só filtra quando a linha NÃO começa com DD/MM (padrão de transação).
    # Linhas com DD/MM são sempre processadas (são transações reais).
    skip_patterns = [
        'total da fatura', 'total desta fatura', 'total para',
        'pagamento efetuado', 'pagamento minimo',
        'saldo financiado', 'saldo anterior',
        'limite total', 'limite de credito',
        'encargos (', 'encargos financ',
        'lancamentos atuais',
        'credito disponivel',
        'proxima fatura', 'proximas faturas',
        'cpf', 'cnpj',
        'demonstrativo', 'informacoes adicionais',
        'central de atendimento', 'ouvidoria',
        'www.', 'http',
    ]

    for linha in texto.split('\n'):
        linha = linha.strip()
        if not linha or len(linha) < 8:
            continue

        linha_lower = linha.lower()

        # Linhas que começam com DD/MM são transações — nunca pular
        comeca_com_data = re.match(r'^\d{1,2}/\d{1,2}\s', linha)

        # Pula linhas de cabeçalho/rodapé (apenas se NÃO parecem transação)
        if not comeca_com_data and any(skip in linha_lower for skip in skip_patterns):
            continue

        # Padrão: DD/MM DESCRICAO VALOR (valor no final da linha)
        match = re.match(
            r'(\d{1,2}/\d{1,2})\s+(.+?)\s+([\d.]+,\d{2})\s*$',
            linha
        )

        if not match:
            continue

        date_str, desc_raw, valor_str = match.groups()

        # Valida que DD/MM é uma data (dia 1-31, mês 1-12)
        try:
            dd, mm = map(int, date_str.split('/'))
            if not (1 <= dd <= 31 and 1 <= mm <= 12):
                continue
        except (ValueError, AttributeError):
            continue

        desc = desc_raw.strip()

        # Se a descrição contém padrão XX/YY com total > 1, é parcela
        # → já foi capturada por extrair_parcelas(), pular
        parc_in_desc = re.search(r'(\d{1,2})/(\d{1,2})', desc)
        if parc_in_desc:
            try:
                a, t = int(parc_in_desc.group(1)), int(parc_in_desc.group(2))
                if t > 1 and a <= t:
                    continue
            except (ValueError, AttributeError):
                pass

        # Verifica duplicata com itens parcelados (mesma descrição base)
        desc_norm = re.sub(r'\s+', ' ', desc.upper().strip())
        is_dup = False
        for dp in descs_parceladas:
            if dp in desc_norm or desc_norm in dp:
                is_dup = True
                break
        if is_dup:
            continue

        try:
            val = float(valor_str.replace(".", "").replace(",", "."))
            if abs(val) < 0.01:
                continue

            chave = (desc_norm, "1/1")
            if chave not in chaves_vistas:
                chaves_vistas.add(chave)
                resultados.append((desc, "1/1", val))
        except (ValueError, TypeError):
            continue

    return resultados


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
        # 1. Extrair texto
        texto = extrair_texto_pdf(file, senha_pdf)

        if not texto or texto.strip() == "":
            return "DESCONHECIDO", "", []

        # 2. Normalizar texto (remover acentos para regex funcionar)
        texto_norm = normalizar_texto(texto)

        # 3. Detectar banco (usa texto normalizado)
        banco = detectar_banco(texto_norm)

        # 4. Cortar texto ANTES de "próximas faturas" para não importar parcelas futuras
        texto_fatura_atual = _cortar_texto_antes_proximas_faturas(texto_norm)

        # 5. Extrair parcelas (itens com indicador XX/YY) — apenas da fatura atual
        dados_parcelados = extrair_parcelas(texto_fatura_atual)

        # 6. Extrair itens à vista (sem indicador de parcela) — apenas da fatura atual
        if incluir_avista:
            dados_avista = extrair_itens_avista(texto_fatura_atual, dados_parcelados)
            dados = dados_parcelados + dados_avista
        else:
            dados = dados_parcelados

        return banco, texto, dados

    except Exception as e:
        print("Erro ao processar fatura:", e)
        return "ERRO", "", []


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