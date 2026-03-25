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
        Suporta: Itaú, Bradesco, Nubank, Inter, Santander, Visa, etc.
        """
        parcelas = []
        texto_limpo = " ".join(texto.split())
        
        # Padrão 6: Santander/Visa com data de compra - VERSÃO ULTRA MELHORADA
        # Formato: [num] DATA_COMPRA DESCRICAO DATA_PARCELA VALOR
        # Exemplo: "2 12/06 QUITA*052PAGBOLETO 09/17 70,28" ou "21/10 CPFL PAULISTA 05/10 47,02"
        # Exemplo: "2 13/02 CONSORCIO *EMBRACON 01/03 913,34"
        # Padrão mais flexível: permite qualquer caractere na descrição (menos dígitos no começo após espaço)
        padrao6_flexivel = r'(\d+)?\s+(\d{2}/\d{2})\s+(.+?)\s+(\d{2}/\d{2})\s+([\d,]+?)(?:\s{2,}|$)'
        
        # Padrão 1: "qualquer coisa (X/Y) R$ valor"
        padrao1 = r'(.+?)\s*\((\d+)/(\d+)\)\s*[Rr]\$\s*([\d.,]+)'
        
        # Padrão 2: "X/Y parcelas de R$ valor"
        padrao2 = r'(\d+)/(\d+)\s*(?:parcelas? de|[-–])\s*[Rr]\$\s*([\d.,]+)'
        
        # Padrão 3: "Descrição X/Y R$ valor"
        padrao3 = r'(.+?)\s+(\d+)/(\d+)\s+[Rr]\$\s*([\d.,]+)'
        
        matches = []
        
        # Tenta padrão 6 flexível (Santander com data de compra)
        for match in re.finditer(padrao6_flexivel, texto_limpo, re.IGNORECASE):
            groups = match.groups()
            if len(groups) == 5:
                num_parcela, data_compra, descricao, data_parcela, valor = groups
                descricao = descricao.strip()
                
                # Filtra: descrição deve ter pelo menos 3 caracteres e não começar com dígitos
                if (descricao and len(descricao) > 2 and data_parcela and valor and 
                    not descricao[0].isdigit()):
                    try:
                        val_float = float(valor.replace(".", "").replace(",", "."))
                        if val_float > 0:
                            parc_tuple = (descricao, data_parcela, val_float)
                            # Evita duplicatas
                            if parc_tuple not in matches:
                                matches.append(parc_tuple)
                    except:
                        pass
        
        # Se encontrou com padrão 6, retorna
        if matches:
            return matches
        
        # Tenta padrão 1 (com descrição e parênteses)
        for match in re.finditer(padrao1, texto_limpo, re.IGNORECASE | re.DOTALL):
            descricao, parcela_atual, total_parcelas, valor = match.groups()
            if descricao.strip() and parcela_atual and total_parcelas and valor:
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        matches.append((descricao.strip(), f"{parcela_atual}/{total_parcelas}", val_float))
                except:
                    pass
        
        if matches:
            return matches
        
        # Tenta padrão 2
        for match in re.finditer(padrao2, texto_limpo, re.IGNORECASE):
            parcela_atual, total_parcelas, valor = match.groups()
            if parcela_atual and total_parcelas and valor:
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        pos = match.start()
                        contexto = texto_limpo[max(0, pos-100):pos]
                        descricao = contexto.split('\n')[-1] if '\n' in contexto else contexto[-50:]
                        matches.append((descricao.strip(), f"{parcela_atual}/{total_parcelas}", val_float))
                except:
                    pass
        
        if matches:
            return matches
        
        # Tenta padrão 3 (último recurso)
        for match in re.finditer(padrao3, texto_limpo, re.IGNORECASE):
            descricao, parcela_atual, total_parcelas, valor = match.groups()
            if descricao.strip() and parcela_atual and total_parcelas and valor:
                try:
                    val_float = float(valor.replace(".", "").replace(",", "."))
                    if val_float > 0:
                        matches.append((descricao.strip(), f"{parcela_atual}/{total_parcelas}", val_float))
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
