import re

def limpar_texto_ocr(texto):
    import re
    
    # Remove espaço entre dígitos DENTRO de números
    texto = re.sub(r'(\d)\s+(\d)', r'\1\2', texto)
    # Remove espaço entre R e símbolo monetário
    texto = re.sub(r'([R])\s+(\$|[4%#@])', r'\1\2', texto)
    # NÃO remove espaço entre palavras - preserva estrutura
    
    # Corrige R$ corrompido
    texto = re.sub(r'R[4%#@]', 'R$', texto)
    
    # Substitui números
    subs_num = {'+': '8', '%': '8', ')': '0', '(': '0', 'O': '0', 'o': '0',
                'l': '1', 'L': '1', 'M': '1', 'S': '5', 'B': '8', 'Z': '2', 'z': '2'}
    resultado = texto
    for k, v in subs_num.items():
        resultado = resultado.replace(k, v)
    
    # Substitui acentos
    subs_acentos = {'õ': 'o', 'ó': 'o', 'ô': 'o', 'í': 'i', 'ì': 'i', 'î': 'i',
                    'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ç': 'c', 'é': 'e', 'è': 'e', 'ê': 'e'}
    for k, v in subs_acentos.items():
        resultado = resultado.replace(k, v)
    
    return resultado

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
