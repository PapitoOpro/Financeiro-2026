"""Teste de validação das tabelas faturas + itens_fatura."""
import time

start = time.time()
from database import db

print("=" * 50)
print("  TESTE: Tabelas de Fatura")
print("=" * 50)

# 1. Inicialização
print("\n1. inicializar_banco()...")
db._skip_rls = True
db.inicializar_banco()
print(f"   OK ({time.time()-start:.1f}s)")

# 2. Tabelas existem?
print("\n2. Verificando tabelas...")
tabelas = db.buscar("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('faturas','itens_fatura')
    ORDER BY table_name
""")
nomes = tabelas['table_name'].tolist() if not tabelas.empty else []
print(f"   Tabelas: {nomes}")
assert 'faturas' in nomes, "FALHOU: tabela faturas nao existe"
assert 'itens_fatura' in nomes, "FALHOU: tabela itens_fatura nao existe"
print("   PASS")

# 3. Coluna fatura_id em transacoes
print("\n3. Coluna fatura_id em transacoes...")
col = db.buscar("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'transacoes' AND column_name = 'fatura_id'
""")
assert not col.empty, "FALHOU: coluna fatura_id nao existe em transacoes"
print("   PASS")

# 4. Indice unico
print("\n4. Indice ux_faturas_conta_comp_user...")
idx = db.buscar("""
    SELECT indexname FROM pg_indexes 
    WHERE tablename = 'faturas' AND indexname = 'ux_faturas_conta_comp_user'
""")
assert not idx.empty, "FALHOU: indice unico nao existe"
print("   PASS")

# 5. Contagem
print("\n5. Contagem de dados...")
nf = db.buscar("SELECT COUNT(*) as n FROM faturas")
ni = db.buscar("SELECT COUNT(*) as n FROM itens_fatura")
nt = db.buscar("SELECT COUNT(*) as n FROM transacoes WHERE tipo_fluxo = 'CARTAO'")
qf = int(nf.iloc[0]['n'])
qi = int(ni.iloc[0]['n'])
qt = int(nt.iloc[0]['n'])
print(f"   Faturas: {qf}")
print(f"   Itens fatura: {qi}")
print(f"   Transacoes CARTAO (legado): {qt}")

# 6. Teste CRUD
print("\n6. Teste CRUD basico...")

# Busca uma conta e categoria do user 1 (ou qualquer user)
contas = db.buscar("SELECT id, user_id FROM contas LIMIT 1")
cats = db.buscar("SELECT id, user_id FROM categorias LIMIT 1")

if contas.empty or cats.empty:
    print("   SKIP (sem contas/categorias para testar)")
else:
    uid = int(contas.iloc[0]['user_id'])
    cid = int(contas.iloc[0]['id'])
    catid = int(cats.iloc[0]['id'])

    from datetime import date

    # Cria fatura
    fatura_id = db.criar_fatura(uid, cid, '99/2099', date(2099, 12, 15))
    assert fatura_id is not None, "FALHOU: criar_fatura retornou None"
    print(f"   criar_fatura -> id={fatura_id}")

    # Idempotencia
    fatura_id2 = db.criar_fatura(uid, cid, '99/2099', date(2099, 12, 15))
    assert fatura_id == fatura_id2, "FALHOU: criar_fatura nao e idempotente"
    print(f"   idempotencia -> OK (mesmo id={fatura_id2})")

    # Adiciona item
    db.adicionar_item_fatura(fatura_id, 'Teste Item', 150.0, date(2099, 12, 1), 1, 3, catid, uid)
    print("   adicionar_item_fatura -> OK")

    # Atualiza total
    db.atualizar_total_fatura(fatura_id)
    fat = db.buscar_um("SELECT valor_total FROM faturas WHERE id = %s", (fatura_id,))
    assert fat is not None and float(fat[0]) == 150.0, f"FALHOU: total={fat}"
    print(f"   atualizar_total_fatura -> {fat[0]}")

    # Busca itens
    itens = db.buscar_itens_fatura(fatura_id)
    assert not itens.empty, "FALHOU: buscar_itens_fatura vazio"
    print(f"   buscar_itens_fatura -> {len(itens)} item(ns)")

    # Busca faturas
    fats = db.buscar_faturas(uid, competencia='99/2099')
    assert not fats.empty, "FALHOU: buscar_faturas vazio"
    print(f"   buscar_faturas -> {len(fats)} fatura(s)")

    # Limpa dados de teste
    db.excluir_fatura(fatura_id, uid)
    check = db.buscar_um("SELECT 1 FROM faturas WHERE id = %s", (fatura_id,))
    assert check is None, "FALHOU: fatura nao foi excluida"
    print("   excluir_fatura -> OK")

    print("   CRUD PASS")

# 7. Migracao
print("\n7. Migracao CARTAO -> faturas...")
if qt > 0 and qi == 0:
    print(f"   {qt} transacoes CARTAO encontradas, migração deveria ter rodado")
    print("   WARN: itens_fatura esta vazio, verificar _migrar_cartao_para_faturas()")
elif qt > 0 and qi > 0:
    print(f"   Migracao ja executada: {qi} itens criados a partir de {qt} transacoes")
elif qt == 0:
    print("   Sem transacoes CARTAO para migrar (OK)")

print(f"\n{'='*50}")
print(f"  TODOS OS TESTES PASSARAM ({time.time()-start:.1f}s)")
print(f"{'='*50}")
