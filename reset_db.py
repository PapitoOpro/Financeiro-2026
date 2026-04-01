# ==========================================
# SCRIPT PARA RESETAR BANCO DE DADOS
# ==========================================
# Use este script para limpar todos os dados de teste
# Comando: python reset_db.py

import psycopg2
import streamlit as st
from database import db

def resetar_banco():
    """Deleta todos os dados das tabelas, mantendo a estrutura."""
    try:
        conn = db.get_connection()
        
        # Delete em ordem inversa de dependência (foreign keys)
        print(" Deletando dados...")
        
        db.executar("DELETE FROM transacoes")
        print(" Transações deletadas")
        
        db.executar("DELETE FROM usuarios")
        print(" Usuários deletados")
        
        db.executar("DELETE FROM categorias")
        print(" Categorias deletadas")
        
        db.executar("DELETE FROM contas")
        print(" Contas deletadas")
        
        print("\n Banco de dados resetado com sucesso!")
        print(" Agora você pode começar do zero.\n")
        
        return True
        
    except Exception as e:
        print(f" Erro ao resetar: {e}")
        return False

def dropar_e_recriar():
    """Deleta TODAS as tabelas e recria do zero."""
    try:
        conn = db.get_connection()
        
        print(" Deletando tabelas...")
        
        # Drop em ordem inversa de dependência
        db.executar("DROP TABLE IF EXISTS transacoes")
        db.executar("DROP TABLE IF EXISTS usuarios")
        db.executar("DROP TABLE IF EXISTS categorias")
        db.executar("DROP TABLE IF EXISTS contas")
        
        print(" Tabelas deletadas")
        
        # Recriar tabelas
        print(" Recriando tabelas...")
        db.inicializar_banco()
        
        print(" Tabelas recriadas com sucesso!\n")
        return True
        
    except Exception as e:
        print(f" Erro: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("RESETAR BANCO DE DADOS - Sistema Financeiro 2026")
    print("=" * 50)
    print()
    
    while True:
        print("Escolha uma opção:")
        print("1 - Deletar apenas DADOS (manter tabelas)")
        print("2 - Deletar TUDO e recriar do zero")
        print("0 - Cancelar")
        print()
        
        opcao = input("Digite sua escolha (0-2): ").strip()
        
        if opcao == "0":
            print(" Cancelado")
            break
        elif opcao == "1":
            confirma = input("\n Tem certeza que quer deletar TODOS os dados? (sim/não): ").strip().lower()
            if confirma == "sim":
                resetar_banco()
                break
            else:
                print(" Cancelado\n")
        elif opcao == "2":
            confirma = input("\n ATENÇÃO! Isto vai deletar TODAS as tabelas. Tem certeza? (sim/não): ").strip().lower()
            if confirma == "sim":
                dropar_e_recriar()
                break
            else:
                print(" Cancelado\n")
        else:
            print(" Opção inválida\n")
