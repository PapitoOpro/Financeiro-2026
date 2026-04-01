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
    """Verifica se XX/YY é uma parcela válida (não é data, não é à vista)."""
    try:
        atual, total = map(int, parc_str.split("/"))
        # Compra à vista: atual == total (01/01, 1/1, 03/03, etc.)
        if atual == total:
            return False
        # Parcela válida: total > 1 e atual <= total
        if total > 1 and 1 <= atual <= total:
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
# FUNÇÃO FINAL (USO SIMPLES)
# ==========================================

def processar_fatura(file, senha_pdf=None):
    try:
        # 1. Extrair texto
        texto = extrair_texto_pdf(file, senha_pdf)

        if not texto or texto.strip() == "":
            return "DESCONHECIDO", "", []

        # 2. Normalizar texto (remover acentos para regex funcionar)
        texto_norm = normalizar_texto(texto)

        # 3. Detectar banco (usa texto normalizado)
        banco = detectar_banco(texto_norm)

        # 4. Extrair parcelas (usa texto normalizado)
        dados = extrair_parcelas(texto_norm)

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