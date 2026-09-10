# -*- coding: utf-8 -*-
"""Testa os modelos treinados de compositor e consultas LINQ."""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Testar compositor
print("=" * 60)
print("TESTANDO COMPOSITOR DE PROJETOS")
print("=" * 60)

try:
    from modelo.compositor import Compositor
    
    caminho_compositor = Path("modelos/compositor.json")
    if caminho_compositor.exists():
        with open(caminho_compositor, encoding="utf-8") as f:
            dados_compositor = json.load(f)
        print(f"Modelo compositor carregado: {len(dados_compositor)} campos")
        print(f"Campos: {list(dados_compositor.keys())[:5]}...")
    else:
        print("Modelo compositor não encontrado")
except Exception as e:
    print(f"Erro ao carregar compositor: {e}")

# Testar consultor LINQ
print("\n" + "=" * 60)
print("TESTANDO CONSULTOR LINQ")
print("=" * 60)

try:
    from modelo.consulta_linq import Consultor
    
    caminho_consulta = Path("modelos/consulta_linq.json")
    if caminho_consulta.exists():
        with open(caminho_consulta, encoding="utf-8") as f:
            dados_consulta = json.load(f)
        print(f"Modelo consulta LINQ carregado: {len(dados_consulta)} campos")
        print(f"Campos: {list(dados_consulta.keys())[:5]}...")
    else:
        print("Modelo consulta LINQ não encontrado")
except Exception as e:
    print(f"Erro ao carregar consultor LINQ: {e}")

print("\n" + "=" * 60)
print("TESTE DE CRIAÇÃO DE PROJETO")
print("=" * 60)

try:
    from modelo.compositor import Compositor
    from dados.ensino import ENSINO
    
    # Testar criação de um projeto simples
    compositor = Compositor("modelos/compositor.json")
    
    # Criar um projeto Python console
    print("\nTestando criação de projeto Python console...")
    plano = compositor.planejar("python", "console", "meu_projeto")
    
    print(f"Tipo do plano: {type(plano)}")
    
    # O plano é um dicionário com a chave 'arquivos'
    if isinstance(plano, dict) and 'arquivos' in plano:
        arquivos = plano['arquivos']
        print(f"Sucesso! {len(arquivos)} arquivos planejados:")
        for arquivo in arquivos:
            print(f"  - Caminho: {arquivo.get('caminho', 'N/A')}")
            print(f"    Papel: {arquivo.get('papel', 'N/A')}")
            print(f"    Confianca: {arquivo.get('confianca', 'N/A')}")
            conteudo = arquivo.get('conteudo', '')
            print(f"    Tamanho: {len(conteudo)} caracteres")
            print(f"    Primeiras linhas: {conteudo[:200]}...")
            print()
        
        # Escrever no disco para testar
        import tempfile
        temp_dir = tempfile.mkdtemp()
        print(f"Escrevendo em diretório temporário: {temp_dir}")
        
        try:
            resultado = compositor.escrever_no_disco(plano, temp_dir)
            print(f"Resultado da escrita: {resultado}")
            
            # Listar arquivos criados
            from pathlib import Path
            temp_path = Path(temp_dir)
            if temp_path.exists():
                arquivos_criados = list(temp_path.rglob("*"))
                print(f"Arquivos criados: {len(arquivos_criados)}")
                for arquivo in arquivos_criados:
                    if arquivo.is_file():
                        print(f"  - {arquivo.relative_to(temp_path)}")
                        # Mostrar conteúdo do arquivo principal
                        if 'main.py' in str(arquivo):
                            print(f"    Conteúdo do main.py:")
                            print(arquivo.read_text()[:300])
        except Exception as e:
            print(f"Erro ao escrever no disco: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("O planejamento não retornou o formato esperado")
        
except Exception as e:
    print(f"Erro ao testar criação de projeto: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTE DE CONSULTA LINQ")
print("=" * 60)

try:
    from modelo.consulta_linq import Consultor
    from modelo.leitor_csharp import ProjetoCSharp
    
    # Carregar o projeto C#
    projeto_csharp = ProjetoCSharp(r"C:\Users\Samsung\Projetos_Eduardo\Linq")
    print(f"Projeto carregado do tipo: {type(projeto_csharp)}")
    
    # Tentar acessar entidades
    if hasattr(projeto_csharp, 'entidades'):
        print(f"Entidades: {len(projeto_csharp.entidades)}")
        for entidade in projeto_csharp.entidades:
            if hasattr(entidade, 'nome'):
                print(f"  - {entidade.nome}: {len(entidade.propriedades)} propriedades")
                for prop in entidade.propriedades[:3]:  # Mostrar as primeiras 3 propriedades
                    print(f"      {prop.nome}: {prop.tipo}")
            else:
                print(f"  - {entidade} (tipo: {type(entidade)})")
    
    # Testar consulta simples - o Consultor precisa do caminho do modelo primeiro
    consultor = Consultor("modelos/consulta_linq.json", projeto_csharp)
    
    print("\nTestando consulta: 'soma o valor de transacoes'")
    resultado = consultor.montar("soma o valor de transacoes")
    print(f"Resultado: {resultado}")
    
except Exception as e:
    print(f"Erro ao testar consulta LINQ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTES CONCLUÍDOS")
print("=" * 60)