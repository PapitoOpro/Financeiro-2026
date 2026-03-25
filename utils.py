# ==========================================
# FUNÇÕES UTILITÁRIAS
# ==========================================

import unicodedata
import PyPDF2
import io
import re
from config import BANCOS_CONHECIDOS

class UtilsManager:
    """Gerenciador de funções utilitárias."""
    
    @staticmethod
    def formatar_moeda(valor):
        """Formata valor como moeda brasileira."""
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    @staticmethod
    def remover_acentos(texto):
        """Remove acentuação de um texto."""
        if not texto:
            return ""
        return "".join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        ).upper()
    
    @staticmethod
    def extrair_texto_pdf(file, senha=None):
        """Extrai texto de arquivo PDF."""
        try:
            pdf_reader = PyPDF2.PdfReader(
                io.BytesIO(file.read()),
                password=senha if senha else None
            )
            texto = ""
            for page in pdf_reader.pages:
                texto += page.extract_text() or ""
            return texto
        except Exception as e:
            return f"Erro ao ler PDF: {str(e)}"
    
    @staticmethod
    def detectar_banco(texto):
        """Detecta o banco pelo texto do PDF."""
        texto_lower = texto.lower()
        
        for palavra_chave, nome_banco in BANCOS_CONHECIDOS.items():
            if palavra_chave in texto_lower:
                return nome_banco
        
        return "GENÉRICO"
    
    @staticmethod
    def extrair_parcelas(texto):
        """
        Extrai parcelas do texto da fatura com múltiplos padrões.
        Suporta: Itaú, Bradesco, Nubank, Inter, Santander, Visa, Mercado Pago, etc.
        """
        parcelas = []
        texto_limpo = " ".join(texto.split())
        
        # PADRÃO 1: Com parênteses (X/Y) - Mais comum
        # "Curso Python (1/12) R$ 99,00" ou "Compra (1/12) R$ 100,00"
        padrao_parenteses = r'([^(]+?)\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)\s*[Rr]\$\s*([\d.,]+)'
        
        # PADRÃO 2: Santander/Visa com datas
        # "2 12/06 QUITA*052PAGBOLETO 09/17 70,28"
        padrao_santander = r'(\d+)?\s+(\d{2}/\d{2})\s+(.+?)\s+(\d{2}/\d{2})\s+([\d,]+?)(?:\s{2,}|$)'
        
        # PADRÃO 2.5: Mercado Pago "Parcela X de Y R$ VALOR"
        # "FERROLHOGO Parcela 12 de 19 R$ 48,03" (OCR às vezes coloca +/- extras)
        padrao_mercadopago = r'(.+?)\s+Parcela\s+(\d+)\s+de\s+(\d+)\s+[Rr]\$\s*[+\-]?\s*([\d.,]+)'
        
        # PADRÃO 3: "X de Y parcelas" ou "X/Y parcelas"
        # "5 de 12 parcelas R$ 150,00" ou "1/12 parcelas de R$ 100,00"
        padrao_de_parcelas = r'(\d+)\s+(?:de|/)\s+(\d+)\s*parcelas?\s+[Dd]e\s+[Rr]\$\s*([\d.,]+)'
        
        # PADRÃO 4: Mercado Pago ou format simples
        # "Descrição 1/12 R$ 100,00"
        padrao_simples = r'([A-Z0-9\s\*\-]{5,}?)\s+(\d+)/(\d+)\s+[Rr]\$\s*([\d.,]+)'
        
        # PADRÃO 5: Apenas números
        # "1/12 R$ 100,00"
        padrao_apenas_numeros = r'^(\d+)/(\d+)\s+[Rr]\$\s*([\d.,]+)'
        
        # PADRÃO 6: Com ponto e vírgula ou separadores
        # "Desc ; 1/12 ; R$ 100"
        padrao_separado = r'([^;:]+?);\s*(\d+)/(\d+)\s*;\s*[Rr]\$\s*([\d.,]+)'
        
        matches = []
        
        # Tenta padrão com parênteses (mais confiável)
        for match in re.finditer(padrao_parenteses, texto_limpo, re.IGNORECASE):
            desc, parc_atual, parc_total, valor = match.groups()
            desc = desc.strip()
            if desc and len(desc) > 2 and not desc[0].isdigit():
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        matches.append((desc, f"{parc_atual}/{parc_total}", val_float))
                except:
                    pass
        
        if matches:
            return matches
        
        # Tenta padrão Mercado Pago "Parcela X de Y"
        for match in re.finditer(padrao_mercadopago, texto_limpo, re.IGNORECASE):
            desc, parc_atual, parc_total, valor = match.groups()
            desc = desc.strip()
            if desc and len(desc) > 2 and not desc[0].isdigit():
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        parc_tuple = (desc, f"{parc_atual}/{parc_total}", val_float)
                        if parc_tuple not in matches:
                            matches.append(parc_tuple)
                except:
                    pass
        
        if matches:
            return matches
        
        # Tenta padrão Santander
        for match in re.finditer(padrao_santander, texto_limpo, re.IGNORECASE):
            groups = match.groups()
            if len(groups) == 5:
                _, data_compra, desc, data_parc, valor = groups
                desc = desc.strip()
                if desc and len(desc) > 2 and not desc[0].isdigit():
                    try:
                        val_float = float(valor.replace(".", "").replace(",", "."))
                        if val_float > 0:
                            parc_tuple = (desc, data_parc, val_float)
                            if parc_tuple not in matches:
                                matches.append(parc_tuple)
                    except:
                        pass
        
        if matches:
            return matches
        
        # Tenta "X de Y parcelas"
        for match in re.finditer(padrao_de_parcelas, texto_limpo, re.IGNORECASE):
            parc_atual, parc_total, valor = match.groups()
            try:
                val_float = float(valor.replace(".", "").replace(",", "."))
                if val_float > 0:
                    # Extrai descrição do contexto
                    pos = match.start()
                    contexto = texto_limpo[max(0, pos-150):pos]
                    desc = contexto.split()[-3] if len(contexto.split()) > 3 else "Parcela"
                    matches.append((desc, f"{parc_atual}/{parc_total}", val_float))
            except:
                pass
        
        if matches:
            return matches
        
        # Tenta padrão simples (Mercado Pago)
        for match in re.finditer(padrao_simples, texto_limpo, re.IGNORECASE):
            desc, parc_atual, parc_total, valor = match.groups()
            desc = desc.strip()
            if desc and len(desc) > 2:
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        parc_tuple = (desc, f"{parc_atual}/{parc_total}", val_float)
                        if parc_tuple not in matches:
                            matches.append(parc_tuple)
                except:
                    pass
        
        if matches:
            return matches
        
        # Tenta padrão com separador (ponto-vírgula)
        for match in re.finditer(padrao_separado, texto_limpo, re.IGNORECASE):
            desc, parc_atual, parc_total, valor = match.groups()
            desc = desc.strip()
            if desc and len(desc) > 2:
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        matches.append((desc, f"{parc_atual}/{parc_total}", val_float))
                except:
                    pass
        
        return matches
    
    @staticmethod
    def get_cor_saldo(valor):
        """Retorna cor apropriada para um saldo."""
        if valor >= 0:
            return "#2ecc71"  # Verde
        else:
            return "#e74c3c"  # Vermelho
    
    @staticmethod
    def get_cor_valor(valor):
        """Retorna cor apropriada para um valor."""
        if valor > 0:
            return "#27ae60"  # Verde positivo
        elif valor < 0:
            return "#c0392b"  # Vermelho negativo
        else:
            return "#333333"  # Cinza neutro

# Instâncias para fácil importação
moeda = UtilsManager.formatar_moeda
remover_acentos = UtilsManager.remover_acentos
extrair_texto_pdf = UtilsManager.extrair_texto_pdf
detectar_banco = UtilsManager.detectar_banco
extrair_parcelas = UtilsManager.extrair_parcelas
get_cor_saldo = UtilsManager.get_cor_saldo
get_cor_valor = UtilsManager.get_cor_valor
