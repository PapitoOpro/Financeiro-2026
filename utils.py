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
        Extrai parcelas do texto da fatura.
        Procura por padrões como:
        - "Compra (1/12) R$ 100,00"
        - "Parcelado: 1/12 - R$ 100,00"
        """
        parcelas = []
        
        # Padrão: "qualquer coisa (X/Y) R$ valor"
        padrao = r'(.+?)\s*\((\d+)/(\d+)\)\s*R\$\s*([\d.,]+)'
        matches = re.finditer(padrao, texto)
        
        for match in matches:
            descricao, parcela_atual, total_parcelas, valor = match.groups()
            
            # Limpa descrição
            descricao = descricao.strip()
            
            # Converte valor para float
            try:
                valor_float = float(valor.replace(".", "").replace(",", "."))
                parcelas.append((descricao, f"{parcela_atual}/{total_parcelas}", valor_float))
            except:
                pass
        
        return parcelas
    
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
