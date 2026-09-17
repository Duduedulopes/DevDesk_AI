# -*- coding: utf-8 -*-
"""CONSERTAR — pelo prompt de comando.

    python programas/consertar.py <arquivo ou pasta>
    python programas/consertar.py <pasta> --gravar     não pergunta, grava
    python programas/consertar.py <pasta> --importar   (Python) também importa

O QUE ELE FAZ, NESTA ORDEM

    1. chama o juiz     `dotnet build` no C#, `ast.parse` no Python
    2. escolhe a família de conserto de cada erro
    3. aplica NUMA CÓPIA
    4. chama o juiz DE NOVO — o erro sumiu? apareceu outro?
    5. te mostra o diff e pergunta se pode gravar

O PASSO 4 É O ARQUIVO INTEIRO. Sem ele isto seria um programa que edita o
seu código por palpite. Com ele, cada conserto que aparece na tela já foi
submetido ao mesmo juiz que reprovou o código antes — e o que não passou
aparece marcado, não escondido.

E A CÓPIA NÃO É EXCESSO DE ZELO. O conserto errado existe: um `)` na
coluna errada pode fazer o arquivo compilar significando outra coisa. Na
cópia, o pior que acontece é você ler o diff e dizer não.

O QUE ELE NÃO FAZ

Não conserta erro de execução — `KeyError` na linha 300 dentro de uma
função que só roda com certos dados. Dá para diagnosticar; não dá para
PROVAR o conserto sem rodar o seu programa com os dados que quebraram.
Quando for esse caso ele diz "achado", e não "provado", e a diferença
está na tela de propósito.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from modelo.consertos import (EXPLICACAO, EscolhaDeFamilia,      # noqa: E402
                              familia_pela_pista, montar)
from provas.juiz_python import (DIAGNOSTICO, Erro, PROVADO,      # noqa: E402
                                julgar as julgar_python)

FORA = {"bin", "obj", ".vs", ".git", "node_modules", "__pycache__", ".venv"}
ERRO_CS = re.compile(r"([\w .\-]+\.cs)\((\d+),(\d+)\):\s*error\s+(\w+):\s*(.+?)\s*(?:\[|$)",
                     re.M)


# ══════════════════════════════════════════════════════════════════════
#  O JUIZ DO C#
# ══════════════════════════════════════════════════════════════════════
def _preparar_csharp(pasta):
    """Rebaixa o TargetFramework e desliga as fontes do NuGet, se precisar.

    As duas coisas são sobre a MÁQUINA, não sobre o código: um projeto
    que mira .NET 10 numa máquina com SDK 8 não compila, e um `restore`
    sem internet trava. Nenhum dos dois é erro seu, e deixar o juiz
    reprovar o arquivo por causa deles seria mentir sobre o seu código.
    """
    for csproj in pasta.glob("*.csproj"):
        txt = csproj.read_text(encoding="utf-8", errors="replace")
        novo = re.sub(r"<TargetFramework>net(\d+)\.0</TargetFramework>",
                      lambda m: (f"<TargetFramework>net8.0</TargetFramework>"
                                 if int(m.group(1)) > 8 else m.group(0)), txt)
        if novo != txt:
            csproj.write_text(novo, encoding="utf-8")
    if not any(pasta.glob("nuget.config")) and not list(pasta.rglob("*.nupkg")):
        (pasta / "nuget.config").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<configuration>\n'
            '  <packageSources><clear /></packageSources>\n</configuration>\n',
            encoding="utf-8")


def julgar_csharp(pasta, tempo=300):
    pasta = Path(pasta)
    try:
        r = subprocess.run(["dotnet", "build", "-v", "q", "--nologo"], cwd=pasta,
                           capture_output=True, text=True, timeout=tempo)
    except FileNotFoundError:
        print("  `dotnet` não está no PATH — sem compilador não há juiz.")
        return None
    except subprocess.TimeoutExpired:
        print(f"  o build passou de {tempo}s.")
        return None
    saida = r.stdout + r.stderr
    erros, vistos = [], set()
    for m in ERRO_CS.finditer(saida):
        # O `dotnet build` REPETE cada erro, uma vez por passagem do build.
        # Sem isto a tela mostra o mesmo conserto duas vezes e pergunta
        # duas vezes se pode gravar — a segunda sobre um erro que a
        # primeira já resolveu.
        chave = (m.group(1), m.group(2), m.group(4))
        if chave in vistos:
            continue
        vistos.add(chave)
        arq = pasta / m.group(1)
        ln = int(m.group(2))
        texto = ""
        if arq.exists():
            ls = arq.read_text(encoding="utf-8", errors="replace").splitlines()
            texto = ls[ln - 1] if 0 < ln <= len(ls) else ""
        erros.append(Erro(arq, ln, int(m.group(3)), m.group(4), m.group(5),
                          texto=texto.rstrip()))
    return erros


def nomes_do_projeto(pasta):
    """Todos os nomes reais: classes, propriedades, valores de enum, LINQ.

    É contra esta lista que um nome errado é trocado. Ela vem do LEITOR
    que já existe — o mesmo que alimenta a rede das consultas.
    """
    nomes = {"Where", "Select", "Sum", "Count", "Any", "All", "ToList",
             "OrderBy", "OrderByDescending", "GroupBy", "FirstOrDefault",
             "First", "Last", "Min", "Max", "Average", "Distinct", "Take",
             "Skip", "Contains", "Console", "WriteLine", "ToString", "Length"}
    try:
        from modelo.leitor_csharp import ProjetoCSharp
        p = ProjetoCSharp(pasta)
        nomes |= set(p.entidades)
        for e in p.entidades:
            nomes |= {x.nome for x in p.opcoes_de(e)}
        nomes |= {v for vs in p.enums.values() for v in vs}
    except Exception:                                        # noqa: BLE001
        pass
    for f in Path(pasta).rglob("*.cs"):
        if any(x in FORA for x in f.parts):
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        nomes |= set(re.findall(r"\b(?:var|int|string|decimal|bool|double)\s+(\w+)\s*=", txt))
    return sorted(nomes)


def nomes_do_python(pasta):
    nomes = set(dir(__builtins__)) if not isinstance(__builtins__, dict) \
        else set(__builtins__)
    for f in Path(pasta).rglob("*.py"):
        if any(x in FORA for x in f.parts):
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        nomes |= set(re.findall(r"\bdef\s+(\w+)", txt))
        nomes |= set(re.findall(r"\bclass\s+(\w+)", txt))
        nomes |= set(re.findall(r"\bself\.(\w+)", txt))
        nomes |= set(re.findall(r"^\s*(\w+)\s*=", txt, re.M))
    return sorted(nomes)


# ══════════════════════════════════════════════════════════════════════
#  A RODADA
# ══════════════════════════════════════════════════════════════════════
class Caso:
    """Um erro, o conserto proposto, e o que o juiz disse DEPOIS dele."""

    def __init__(self, erro, conserto, veredito, sobraram):
        self.erro, self.conserto = erro, conserto
        self.veredito = veredito      # "provado" | "nao resolveu" | "achado"
        self.sobraram = sobraram


def uma_rodada(origem, linguagem, nomes, rede=None, tempo=300):
    """Julga, propõe e RE-JULGA numa cópia. Não toca no original."""
    with tempfile.TemporaryDirectory(prefix="conserto-") as tmp:
        copia = Path(tmp) / "obra"
        if origem.is_dir():
            shutil.copytree(origem, copia,
                            ignore=shutil.ignore_patterns(*FORA))
        else:
            copia.mkdir(parents=True)
            shutil.copy2(origem, copia / origem.name)
        if linguagem == "csharp":
            _preparar_csharp(copia)
            antes = julgar_csharp(copia, tempo)
        else:
            antes = julgar_python(copia)
        if antes is None:
            return None, []
        if not antes:
            return [], []

        casos = []
        for erro in antes:
            # DUAS OPINIÕES, E O JUIZ DESEMPATA.
            #
            # A rede acerta mais no geral (84% contra 50%), mas a pista é
            # melhor em `falta_token` (99% contra 97%) — ali o código do
            # erro já é a resposta. Em vez de eu escolher de antemão qual
            # das duas ouvir, tento as duas e deixo o `ast.parse` dizer
            # qual conserto funciona. É a mesma régua que reprovou o
            # arquivo; não há por que trocar de régua na hora de aprovar.
            opinioes = []
            if rede is not None:
                try:
                    f, _ = rede.escolher(erro)
                    opinioes.append(f)
                except Exception:                            # noqa: BLE001
                    pass
            pista = familia_pela_pista(erro)
            if pista and pista not in opinioes:
                opinioes.append(pista)
            conserto = fam = None
            for f in opinioes:
                c = montar(erro, f, nomes)
                if c is not None:
                    conserto, fam = c, f
                    break
            if conserto is None:
                # a família pode ser conhecida mesmo sem molde — e aí o que
                # ela sabe dizer vale mais que "não sei"
                aviso = next((EXPLICACAO[f] for f in opinioes if f in EXPLICACAO),
                             None)
                casos.append(Caso(erro, None, aviso or "sem conserto", None))
                continue
            # aplica na cópia, re-julga, e DESFAZ — um conserto de cada vez,
            # senão dois consertos na mesma rodada escondem qual funcionou
            alvo = Path(conserto.arquivo)
            guardado = alvo.read_text(encoding="utf-8")
            conserto.aplicar()
            depois = (julgar_csharp(copia, tempo) if linguagem == "csharp"
                      else julgar_python(copia))
            alvo.write_text(guardado, encoding="utf-8")
            if depois is None:
                casos.append(Caso(erro, conserto, "nao deu para julgar", None))
                continue
            mesmo = lambda e: (e.linha == erro.linha and e.codigo == erro.codigo
                               and Path(e.arquivo).name == Path(erro.arquivo).name)
            sumiu = not any(mesmo(e) for e in depois)
            # ERRO QUE APARECE DEPOIS NÃO É ERRO QUE EU CAUSEI.
            #
            # Um erro de sintaxe ESCONDE os erros semânticos do arquivo: o
            # compilador para de entender o código e não chega a conferir
            # os nomes. Consertar o `;` faz aparecerem três erros que já
            # estavam lá — e isso é progresso, não estrago.
            #
            # Medido: contando "menos erros que antes" como prova, um
            # conserto certo de `;` foi reprovado porque revelou dois
            # erros que eu mesmo tinha injetado antes.
            #
            # O que de fato acusaria estrago é erro NOVO na linha que eu
            # editei. Esse é meu; o resto do arquivo não é.
            estragou = any(Path(e.arquivo).name == Path(conserto.arquivo).name
                           and e.linha == conserto.linha and not mesmo(e)
                           for e in depois)
            revelados = len(depois) - (len(antes) - 1)
            casos.append(Caso(
                erro, conserto,
                "nao resolveu" if not sumiu else
                "estragou" if estragou else "provado",
                max(0, revelados)))
        # o caminho de volta: o conserto aponta para a cópia, e quem grava
        # é o original — traduzir aqui é mais seguro que lembrar depois
        for c in casos:
            if c.conserto:
                rel = Path(c.conserto.arquivo).relative_to(copia)
                c.conserto.arquivo = str(origem / rel if origem.is_dir() else origem)
        return casos, antes


def main():
    ap = argparse.ArgumentParser(description="conserta o que o juiz reprovar")
    ap.add_argument("alvo", help="arquivo ou pasta")
    ap.add_argument("--gravar", action="store_true",
                    help="grava sem perguntar (só o que o juiz PROVOU)")
    ap.add_argument("--importar", action="store_true",
                    help="Python: também importa cada módulo (EXECUTA o código)")
    arg = ap.parse_args()

    alvo = Path(arg.alvo).resolve()
    if not alvo.exists():
        print(f"não achei {alvo}")
        raise SystemExit(1)

    tem_cs = any(alvo.rglob("*.cs")) if alvo.is_dir() else alvo.suffix == ".cs"
    tem_py = any(alvo.rglob("*.py")) if alvo.is_dir() else alvo.suffix == ".py"
    linguagens = [x for x, tem in (("csharp", tem_cs), ("python", tem_py)) if tem]
    if not linguagens:
        print("não achei .cs nem .py aqui")
        raise SystemExit(1)

    # a rede é OPCIONAL: sem ela o programa continua funcionando pela
    # pista, só consertando menos. Um arquivo de modelo que falta não
    # pode derrubar um comando que a pessoa está usando para consertar o
    # projeto dela.
    rede = None
    caminho_rede = RAIZ / "modelos" / "consertos.json"
    if caminho_rede.exists():
        try:
            rede = EscolhaDeFamilia(caminho_rede)
            m = rede.medido
            print(f"  rede das famílias: {m.get('familia_rede', '?')} contra "
                  f"{m.get('familia_pista', '?')} só pelo código do erro")
        except Exception as e:                               # noqa: BLE001
            print(f"  (sem a rede das famílias: {e})")

    total = gravados = 0
    for ling in linguagens:
        nomes = (nomes_do_projeto(alvo) if ling == "csharp"
                 else nomes_do_python(alvo if alvo.is_dir() else alvo.parent))
        print(f"\n{'=' * 70}\n  {ling.upper()} — {alvo.name}\n{'=' * 70}")
        casos, antes = uma_rodada(alvo, ling, nomes, rede)
        if casos is None:
            continue
        if not casos:
            print("  o juiz não achou erro nenhum.")
            continue
        print(f"  {len(antes)} erro(s)\n")
        for c in casos:
            total += 1
            e = c.erro
            print(f"  {Path(e.arquivo).name}({e.linha},{e.coluna}): {e.codigo}: {e.mensagem}")
            if not c.conserto:
                if c.veredito != "sem conserto":
                    print(f"     {c.veredito}\n")
                else:
                    print("     não sei consertar este. O que eu sei dizer é o"
                          " que está acima.\n")
                continue
            print(c.conserto.diff())
            print(f"     porque: {c.conserto.porque}")
            selo = {"provado": "O JUIZ CONFIRMOU: com esta linha o erro some"
                               + (f" (e aparecem {c.sobraram} que estavam "
                                  "escondidos atrás dele)" if c.sobraram else ""),
                    "nao resolveu": "o juiz NÃO confirmou — o erro continua",
                    "estragou": "este erro some mas OUTRO nasce na mesma "
                                "linha — o conserto está errado",
                    }.get(c.veredito, c.veredito)
            print(f"     {selo}")
            if c.veredito != "provado":
                print("     (não vou gravar o que o juiz não confirmou)\n")
                continue
            if arg.gravar:
                c.conserto.aplicar(); gravados += 1
                print("     gravado.\n")
                continue
            try:
                r = input("     gravar? [s/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  parei aqui.")
                raise SystemExit(0)
            if r in ("s", "sim", "y"):
                c.conserto.aplicar(); gravados += 1
                print("     gravado.\n")
            else:
                print("     deixei como estava.\n")

    print(f"\n  {total} erro(s) analisado(s) · {gravados} gravado(s)")
    if gravados:
        print("  rode de novo: consertar um erro às vezes revela o seguinte.")


if __name__ == "__main__":
    main()
