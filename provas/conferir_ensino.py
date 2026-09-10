# -*- coding: utf-8 -*-
"""Compila TODO exemplo de ensino antes de aceitá-lo como dado.

Ensinar a partir de exemplo quebrado é ensinar a quebrar. Cada arquivo
com papel `principal` (e os de código em geral) passa pelo compilador de
verdade da linguagem dele, com o {nome} já trocado — porque um exemplo
que só compila antes da substituição não serve para nada.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dados.ensino import ENSINO, COMBINACOES_NOVAS
from programas.colher_erros import compilar

NOME_DE_TESTE = "oficina"


def trocar(texto, nome):
    return texto.replace("{nome}", nome).replace("{Nome}", nome[:1].upper() + nome[1:])


COMPILAVEIS = {".py": "python", ".js": "javascript", ".cs": "csharp",
               ".php": "php", ".java": "java", ".cpp": "cpp"}


def main():
    pasta = Path(tempfile.mkdtemp(prefix="ensino_"))
    falhas, conferidos = [], 0
    print()
    for ex in ENSINO:
        ling, tipo = ex["linguagem"], ex["tipo"]
        papeis = [a["papel"] for a in ex["arquivos"]]
        linha = f"  {ling}+{tipo:<12} {len(ex['arquivos'])} arquivos  " \
                f"[{' '.join(papeis)}]"
        problemas = []
        nao_conferidos = 0
        for a in ex["arquivos"]:
            caminho = trocar(a["caminho"], NOME_DE_TESTE)
            conteudo = trocar(a["conteudo"], NOME_DE_TESTE)
            ext = Path(caminho).suffix.lower()
            if ext not in COMPILAVEIS:
                continue
            # C#: um arquivo solto de biblioteca não tem Main; compila como
            # biblioteca. O `compilar` monta exe — para o caso da biblioteca
            # isso daria erro de "sem ponto de entrada", que não é defeito
            # do exemplo. Então só o `principal` de projeto executável vai.
            if ext == ".cs" and "Main(" not in conteudo:
                continue
            pl = pasta / f"{ling}_{tipo}"
            pl.mkdir(parents=True, exist_ok=True)
            # C#: os arquivos irmãos do MESMO exemplo vão juntos na chamada
            # do csc (como `dotnet build` faria) — Program.cs pode chamar
            # Rotas.cs dentro do próprio projeto.
            irmaos = {trocar(o["caminho"], NOME_DE_TESTE): trocar(o["conteudo"], NOME_DE_TESTE)
                      for o in ex["arquivos"] if o is not a
                      and Path(trocar(o["caminho"], NOME_DE_TESTE)).suffix.lower() == ".cs"} \
                if ext == ".cs" else None
            ok, msg = compilar(conteudo, COMPILAVEIS[ext], pl, outros=irmaos)
            if ok is None:
                nao_conferidos += 1
                continue  # máquina sem esse compilador: não confere
            conferidos += 1
            if ok is False:
                problemas.append((caminho, msg.strip().splitlines()[0][:90]))
        if problemas:
            print(linha + "   ← NÃO COMPILA")
            for c, m in problemas:
                print(f"      {c}\n        {m}")
            falhas.append((ling, tipo, problemas))
        elif nao_conferidos:
            sufixo = "s" if nao_conferidos > 1 else ""
            print(linha + f"   sem compilador ({nao_conferidos} nao conferido{sufixo})")
        else:
            print(linha + "   ok")

    shutil.rmtree(pasta, ignore_errors=True)
    print(f"\n  {len(ENSINO)} exemplos de ensino · {conferidos} arquivos compilados")
    print(f"  {len(falhas)} com problema")

    print(f"\n  combinações guardadas para o teste de composição:")
    for l, t in COMBINACOES_NOVAS:
        tem_ling = any(e["linguagem"] == l for e in ENSINO)
        tem_tipo = any(e["tipo"] == t for e in ENSINO)
        print(f"    {l}+{t:<12} linguagem ensinada: {'sim' if tem_ling else 'NAO'} · "
              f"tipo ensinado: {'sim' if tem_tipo else 'NAO'} · "
              f"a combinação: {'ENSINADA (nao serve de teste)' if any(e['linguagem']==l and e['tipo']==t for e in ENSINO) else 'nao'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
