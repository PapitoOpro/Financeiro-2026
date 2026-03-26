# utils.py

import re
import unicodedata
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import numpy as np
import cv2

# ==========================================
# 🔥 EXTRAÇÃO INTELIGENTE (PDF → TEXTO)
# ==========================================

def extrair_texto_pdf(file, senha=None):
    texto = ""

    # 🥇 TENTAR EXTRAÇÃO DIRETA (RÁPIDO E PRECISO)
    try:
        file.seek(0)
        with pdfplumber.open(file) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto += t + "\n"
    except:
        pass

    # 🥈 FALLBACK OCR (SE TEXTO VEIO RUIM)
    if len(texto) < 1000:
        try:
            file.seek(0)
            images = convert_from_bytes(file.read(), dpi=300)

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
# 🧼 NORMALIZAÇÃO (ANTI-OCR BUG)
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

    texto = re.sub(r'\s+', ' ', texto)

    return texto


# ==========================================
# 🏦 DETECTOR DE BANCO
# ==========================================

def detectar_banco(texto):
    t = texto.lower()

    if "mercado pago" in t:
        return "MERCADO_PAGO"
    elif "nubank" in t:
        return "NUBANK"
    elif "itau" in t:
        return "ITAU"
    elif "bradesco" in t:
        return "BRADESCO"

    return "GENÉRICO"


# ==========================================
# 💳 PARSER - MERCADO PAGO (SEU CASO)
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
# 🌍 PARSER GENÉRICO (OUTROS BANCOS)
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
# 🧠 ORQUESTRADOR PRINCIPAL
# ==========================================

def extrair_parcelas(texto):
    import re
    resultados = []

    padrao = re.findall(
        r'(\d{1,2}/\d{1,2})\s+(.+?)\s+R\$\s?([\d\.,]+)',
        texto
    )

    for parc, desc, valor in padrao:
        valor = float(valor.replace('.', '').replace(',', '.'))
        resultados.append((desc.strip(), parc, valor))

    return resultados

# ==========================================
# 🚀 FUNÇÃO FINAL (USO SIMPLES)
# ==========================================

def processar_fatura(file, senha_pdf=None):
    try:
        # 1. Extrair texto
        texto = extrair_texto_pdf(file, senha_pdf)

        if not texto or texto.strip() == "":
            return "DESCONHECIDO", "", []

        # 2. Detectar banco
        banco = detectar_banco(texto)

        # 3. Extrair parcelas
        dados = extrair_parcelas(texto)

        return banco, texto, dados

    except Exception as e:
        print("Erro ao processar fatura:", e)
        return "ERRO", "", []


# ==========================================
# 💰 FUNÇÕES UTILITÁRIAS - FORMATAÇÃO
# ==========================================

def moeda(valor):
    """Formata valor como moeda brasileira (R$)."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_cor_saldo(saldo):
    """Retorna cor baseada no saldo (positivo=verde, negativo=vermelho)."""
    if saldo >= 0:
        return "#10B981"  # Verde
    else:
        return "#EF4444"  # Vermelho

def get_cor_valor(valor):
    """Retorna cor baseada no valor (positivo=verde, negativo=vermelho)."""
    if valor >= 0:
        return "#10B981"  # Verde
    else:
        return "#EF4444"  # Vermelho