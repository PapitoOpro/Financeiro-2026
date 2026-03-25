import re

def limpar_texto_ocr(texto):
    """Versão INTELIGENTE com contextos"""
    import re
    
    # PASSO 0: Remover espaços extras APENAS entre dígitos
    texto = re.sub(r'(\d)\s+(\d)', r'\1\2', texto)
    texto = re.sub(r'([R])\s+(\$|[4%#@])', r'\1\2', texto)
    
    # PASSO 1: Corrigir "R$" corrompido
    texto = re.sub(r'R[4%#@]', 'R$', texto)
    
    # PASSO 2: Limpar valores (R$ XXX,XX)
    def limpar_valor(match):
        valor_str = match.group(0)
        valor_str = valor_str.replace('+', '8').replace('%', '8').replace(')', '0')
        valor_str = valor_str.replace('(', '0').replace('M', '8').replace('Z', '2').replace('z', '2')
        return valor_str
    
    texto = re.sub(r'R\$\s*[+\-]?[\d.,)\(M%ZzO]+', limpar_valor, texto)
    
    # PASSO 3: Limpar parcelas (X/Y)
    def limpar_parcela(match):
        parc_str = match.group(0)
        parc_str = parc_str.replace('M', '1').replace('L', '1').replace('l', '1')
        parc_str = parc_str.replace('O', '0').replace(')', '0')
        return parc_str
    
    texto = re.sub(r'[MmLlOo0-9]+/[MmLlOo0-9]+', limpar_parcela, texto)
    
    # PASSO 4: Acentos
    subs_acentos = {'õ': 'o', 'ó': 'o', 'ô': 'o', 'í': 'i', 'ì': 'i', 'î': 'i',
                    'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ç': 'c', 'é': 'e', 'è': 'e', 'ê': 'e',
                    'ú': 'u', 'ù': 'u', 'û': 'u', 'ö': 'o', 'ä': 'a', 'ü': 'u', 'ï': 'i',
                    'ñ': 'n', 'ý': 'y'}
    for k, v in subs_acentos.items():
        texto = texto.replace(k, v)
    
    return texto

# Teste com dados REAIS
texto_real = """0)/01zERíóõOLFVREBEZóGóRíOzZRL Parcela 12 de 19 R4 +%,03
11/0)zERíóõOPóUOB+PROõNTOS Parcela 6 de 6 R4 6,62
06/09REàBRFOS zOTORS Parcela 3 de 12 R4 M93,02
01/10Eí BMPROõNTOS Parcela M de 10 R4 +9,++
11/12zPBRó5óELSONGó Parcela 1 de 2 R4 62,9M"""

print("TEXTO ORIGINAL:")
print("=" * 80)
print(texto_real)

texto_limpo = limpar_texto_ocr(texto_real)
print("\n" + "=" * 80)
print("TEXTO APÓS LIMPEZA INTELIGENTE:")
print("=" * 80)
print(texto_limpo)

# Extrai com regex
padrao = r'(.+?)\s+Parce[1l]a\s+(\d+)\s+de\s+(\d+)\s+[Rr]\$\s*[+\-]?\s*([\d.,]+)'
matches = re.findall(padrao, texto_limpo, re.IGNORECASE)

print("\n" + "=" * 80)
print(f"PARCELAS EXTRAIDAS: {len(matches)}")
print("=" * 80)
for i, (desc, atual, total, valor) in enumerate(matches, 1):
    valor_float = float(valor.replace('.', '').replace(',', '.'))
    print(f"{i}. {desc.strip()[:50]:50} | {atual}/{total} | R$ {valor_float:8.2f}")


# Dados REAIS do usuário
texto_real = """0)/01zERíóõOLFVREBEZóGóRíOzZRL Parcela 12 de 19 R4 +%,03
11/0)zERíóõOPóUOB+PROõNTOS Parcela 6 de 6 R4 6,62
11/0)zERíóõOPóUOB+PROõNTOS Parcela 6 de 6 R4 2%,)0
06/09REàBRFOS zOTORS Parcela 3 de 12 R4 M93,02
01/10Eí BMPROõNTOS Parcela M de 10 R4 +9,++
11/12zPBRó5óELSONGó Parcela 1 de 2 R4 62,9M
2+/12zPBzELFzóFS R4 9,%0"""

print("TEXTO ORIGINAL (Corrompido):")
print("=" * 80)
print(texto_real)
print("\n" + "=" * 80)

texto_limpo = limpar_texto_ocr(texto_real)
print("\nTEXTO APÓS LIMPEZA:")
print("=" * 80)
print(texto_limpo)
print("\n" + "=" * 80)

# Testa o regex
padrao = r'(.+?)\s+Parce[1l]a\s+(\d+)\s+de\s+(\d+)\s+[Rr]\$\s*[+\-]?\s*([\d.,]+)'

print("\nTESTANDO REGEX:")
print("=" * 80)

matches = re.findall(padrao, texto_limpo, re.IGNORECASE)
print(f"Encontradas: {len(matches)} parcelas\n")

for i, (desc, atual, total, valor) in enumerate(matches, 1):
    valor_float = float(valor.replace('.', '').replace(',', '.'))
    print(f"{i}. {desc.strip()[:40]:40} | {atual}/{total} | R$ {valor_float:8.2f}")

print("\n" + "=" * 80)
print(f"RESULTADO: {len(matches)}/7 parcelas extraidas")
