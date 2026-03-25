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
        """Extrai texto de arquivo PDF com fallback para pytesseract no Streamlit Cloud."""
        try:
            # TENTATIVA 1: PyPDF2 (rápido, funciona offline)
            pdf_reader = PyPDF2.PdfReader(
                io.BytesIO(file.read()),
                password=senha if senha else None
            )
            texto = ""
            for page in pdf_reader.pages:
                texto += page.extract_text() or ""
            
            # Se conseguiu extrair texto significativo, retorna
            if texto and len(texto.strip()) > 50:
                return texto
            
            # TENTATIVA 2: pytesseract (mais robusto, funciona no Streamlit Cloud)
            try:
                from PIL import Image
                import pytesseract
                
                file.seek(0)  # Volta ao início do arquivo
                from pdf2image import convert_from_bytes
                
                images = convert_from_bytes(file.read())
                texto_tesseract = ""
                
                for img in images[:5]:  # Limita a 5 páginas para não demorar
                    texto_tesseract += pytesseract.image_to_string(img, lang='por') + "\n"
                
                if texto_tesseract and len(texto_tesseract.strip()) > 50:
                    return texto_tesseract
                
            except Exception as e:
                pass  # Se pytesseract falhar, retorna resultado do PyPDF2
            
            return texto if texto else "Erro: Não foi possível extrair texto do PDF"
            
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
    def limpar_texto_ocr(texto):
        """Corrige caracteres corrompidos comuns do OCR - versão otimizada."""
        import re
        
        # PASSO 0: REMOVER ESPAÇOS EXTRAS ENTRE CARACTERES
        # "R   1   .   2   4   6" -> "R1.246" ou quebra de linhas no meio de números
        # Remove quebras de linha e espaços múltiplos dentro de números/símbolos
        texto = re.sub(r'(\d)\s+(\d)', r'\1\2', texto)  # Remove espaço entre dígitos
        texto = re.sub(r'([R])\s+(\$|[4%#@])', r'\1\2', texto)  # Remove espaço em R$
        texto = re.sub(r'(\w)\s+(\w)', r'\1\2', texto)  # Remove espaço entre palavras (cuidado!)
        
        # PASSO 1: Normalizar símbolos monetários corrompidos ANTES de outras substituições
        # Traduz R$, R4, R%, R# e similares para R$
        texto = re.sub(r'R[4%#@]', 'R$', texto)
        
        # PASSO 2: Corrigir números corrompidos em valores monetários
        substituicoes_numeros = {
            '+': '8',        # + -> 8
            '%': '8',        # % -> 8
            ')': '0',        # ) -> 0
            '(': '0',        # ( -> 0
            'O': '0',        # O -> 0 (apenas em contexto de números)
            'o': '0',        # o -> 0 minúsculo também
            'l': '1',        # l -> 1
            'L': '1',        # L -> 1
            'M': '1',        # M -> 1
            'S': '5',        # S -> 5
            'B': '8',        # B -> 8
            'Z': '2',        # Z -> 2
            'z': '2',        # z minúsculo também
        }
        
        resultado = texto
        for char_errado, char_correto in substituicoes_numeros.items():
            resultado = resultado.replace(char_errado, char_correto)
        
        # PASSO 3: Corrigir caracteres acentuados corrompidos
        substituicoes_chars = {
            'õ': 'o', 'ó': 'o', 'ô': 'o',
            'í': 'i', 'ì': 'i', 'î': 'i',
            'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
            'ç': 'c', 'é': 'e', 'è': 'e', 'ê': 'e',
            'ú': 'u', 'ù': 'u', 'û': 'u',
            'ö': 'o', 'ä': 'a', 'ü': 'u', 'ï': 'i',
            'ñ': 'n', 'ý': 'y',
        }
        
        for char_errado, char_correto in substituicoes_chars.items():
            resultado = resultado.replace(char_errado, char_correto)
        
        return resultado
    
    @staticmethod
    def extrair_parcelas(texto):
        """
        Extrai parcelas do texto da fatura com múltiplos padrões.
        Suporta: Itaú, Bradesco, Nubank, Inter, Santander, Visa, Mercado Pago, etc.
        """
        # PRIMEIRO: Limpar o texto de caracteres corrompidos do OCR
        texto = UtilsManager.limpar_texto_ocr(texto)
        
        parcelas = []
        texto_limpo = " ".join(texto.split())
        
        # PADRÃO 1: Com parênteses (X/Y) - Mais comum
        # "Curso Python (1/12) R$ 99,00" ou "Compra (1/12) R$ 100,00"
        padrao_parenteses = r'([^(]+?)\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)\s*[Rr]\$\s*([\d.,]+)'
        
        # PADRÃO 2: Santander/Visa com datas
        # "2 12/06 QUITA*052PAGBOLETO 09/17 70,28"
        padrao_santander = r'(\d+)?\s+(\d{2}/\d{2})\s+(.+?)\s+(\d{2}/\d{2})\s+([\d,]+?)(?:\s{2,}|$)'
        
        # PADRÃO 2.5: Mercado Pago "Parcela X de Y R$ VALOR"
        # "FERROLHOGO Parcela 12 de 19 R$ 48,03" ou "Parce1a 12 de 19" (após limpeza)
        # Usa [1l] para aceitar tanto "1" quanto "l" após limpeza
        # Também aceita espaços dispersos: "R  $" ou "1  2  de  1  9"
        padrao_mercadopago = r'(.+?)\s+Parce[1l]a\s+(\d+)\s+de\s+(\d+)\s+[Rr]\$\s*[+\-]?\s*([\d.,]+)'
        
        # PADRÃO 2.6: Mercado Pago alternativo (muito quebrado)
        # Se o OCR está fazendo loucura, tenta um padrão mais vago
        padrao_mercadopago_alt = r'(.+?)\s+Parce\w+\s+(\d{1,2})\s+de\s+(\d{1,2})\s+[Rr][\$4%#@]\s*[+\-]?\s*([\d.,]+)'
        
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
        
        # Tenta padrão Mercado Pago alternativo (mais robusto)
        for match in re.finditer(padrao_mercadopago_alt, texto_limpo, re.IGNORECASE):
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
limpar_texto_ocr = UtilsManager.limpar_texto_ocr
extrair_parcelas = UtilsManager.extrair_parcelas
get_cor_saldo = UtilsManager.get_cor_saldo
get_cor_valor = UtilsManager.get_cor_valor
