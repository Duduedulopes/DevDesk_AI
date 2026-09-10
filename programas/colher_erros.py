# -*- coding: utf-8 -*-
"""Colhe erros de compilação DE VERDADE — quebrando código que funciona."""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

"""    python programas/colher_erros.py
    python programas/colher_erros.py --linguagens python,csharp

A IDEIA, E ELA MUDA O CUSTO DO PROBLEMA

Em tudo que este projeto fez até aqui, o rótulo certo tinha que vir de
alguém: você clicando na intenção certa, ou um gerador que sabia onde
tinha posto cada campo.

Para erro de compilação não precisa. **O compilador é o juiz.** Ele diz
sim ou não, sozinho, sempre, de graça. Então o corpus se COLHE em vez de
se escrever:

    pega código que compila
      → quebra de um jeito que a gente escolheu
        → roda o compilador DE VERDADE
          → guarda (código quebrado, erro real, qual foi o defeito, conserto)

O rótulo sai de graça duas vezes: sabemos qual defeito injetamos, e
sabemos qual é o conserto — é o código original.

E O LAÇO SE VERIFICA SOZINHO

Depois, quando a rede propuser uma correção, não é preciso perguntar a
ninguém se ela está certa: aplica e recompila. Compilou, acertou. É um
sinal de acerto automático, e quase nenhum problema de aprendizado tem
isso.

DUAS CONFERÊNCIAS QUE TODO EXEMPLO PRECISA PASSAR

    1. o código ORIGINAL compila          senão a semente está podre
    2. o código QUEBRADO não compila      senão não houve defeito nenhum

Sem a segunda, o corpus encheria de exemplos onde o "defeito" não quebrou
nada — e a rede aprenderia a ver erro onde não tem.

POR QUE VERIFICAÇÃO DE SINTAXE E NÃO BUILD COMPLETO

`dotnet build` leva segundos e monta projeto inteiro; `csc` direto leva
meio segundo. Para colher erro de compilação a diferença não importa — o
que interessa é a mensagem do compilador, e ela é a mesma.

    python  41ms      node  194ms      php  341ms
    csc    568ms      g++  1400ms    javac 1350ms

Medido nesta máquina. É por isso que o programa colhe muito de Python e
pouco de C++: o orçamento é tempo, não vontade.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════════════
#  AS SEMENTES — código que compila, e é isso que importa nelas
# ══════════════════════════════════════════════════════════════════════
SEMENTES = {
"python": {
"somar": '''def somar(a, b):
    total = a + b
    return total

def dobrar(x):
    return x * 2

if __name__ == "__main__":
    resultado = somar(2, 3)
    print("resultado:", dobrar(resultado))
''',
"lista": '''import json

def carregar(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)

def maiores(itens, corte):
    saida = []
    for item in itens:
        if item > corte:
            saida.append(item)
    return saida

print(maiores([1, 5, 9], 4))
''',
"classe": '''class Conta:
    def __init__(self, dono, saldo=0):
        self.dono = dono
        self.saldo = saldo

    def depositar(self, valor):
        if valor <= 0:
            raise ValueError("valor invalido")
        self.saldo += valor
        return self.saldo

conta = Conta("Eduardo")
print(conta.depositar(100))
''',
},
"javascript": {
"somar": '''function somar(a, b) {
  const total = a + b;
  return total;
}

function dobrar(x) {
  return x * 2;
}

const resultado = somar(2, 3);
console.log("resultado:", dobrar(resultado));
''',
"lista": '''const itens = [1, 5, 9, 12];

function maiores(lista, corte) {
  const saida = [];
  for (const item of lista) {
    if (item > corte) {
      saida.push(item);
    }
  }
  return saida;
}

console.log(maiores(itens, 4));
''',
"classe": '''class Conta {
  constructor(dono, saldo = 0) {
    this.dono = dono;
    this.saldo = saldo;
  }

  depositar(valor) {
    if (valor <= 0) {
      throw new Error("valor invalido");
    }
    this.saldo += valor;
    return this.saldo;
  }
}

const conta = new Conta("Eduardo");
console.log(conta.depositar(100));
''',
},
"php": {
"somar": '''<?php
function somar($a, $b) {
    $total = $a + $b;
    return $total;
}

function dobrar($x) {
    return $x * 2;
}

$resultado = somar(2, 3);
echo dobrar($resultado);
''',
"lista": '''<?php
function maiores(array $itens, int $corte): array {
    $saida = [];
    foreach ($itens as $item) {
        if ($item > $corte) {
            $saida[] = $item;
        }
    }
    return $saida;
}

print_r(maiores([1, 5, 9], 4));
''',
},
"csharp": {
"somar": '''using System;

class Programa
{
    static int Somar(int a, int b)
    {
        int total = a + b;
        return total;
    }

    static int Dobrar(int x)
    {
        return x * 2;
    }

    static void Main()
    {
        int resultado = Somar(2, 3);
        Console.WriteLine(Dobrar(resultado));
    }
}
''',
"lista": '''using System;
using System.Collections.Generic;

class Programa
{
    static List<int> Maiores(List<int> itens, int corte)
    {
        var saida = new List<int>();
        foreach (var item in itens)
        {
            if (item > corte)
            {
                saida.Add(item);
            }
        }
        return saida;
    }

    static void Main()
    {
        var itens = new List<int> { 1, 5, 9 };
        Console.WriteLine(Maiores(itens, 4).Count);
    }
}
''',
"linq": '''using System;
using System.Linq;
using System.Collections.Generic;

class Programa
{
    static void Main()
    {
        var numeros = new List<int> { 4, 8, 15, 16, 23, 42 };
        var grandes = numeros.Where(n => n > 10).OrderBy(n => n).ToList();
        var soma = numeros.Sum();
        Console.WriteLine($"{grandes.Count} grandes, soma {soma}");
    }
}
''',
},
"java": {
"somar": '''public class Programa {
    static int somar(int a, int b) {
        int total = a + b;
        return total;
    }

    static int dobrar(int x) {
        return x * 2;
    }

    public static void main(String[] args) {
        int resultado = somar(2, 3);
        System.out.println(dobrar(resultado));
    }
}
''',
"lista": '''import java.util.ArrayList;
import java.util.List;

public class Programa {
    static List<Integer> maiores(List<Integer> itens, int corte) {
        List<Integer> saida = new ArrayList<>();
        for (Integer item : itens) {
            if (item > corte) {
                saida.add(item);
            }
        }
        return saida;
    }

    public static void main(String[] args) {
        List<Integer> itens = new ArrayList<>();
        itens.add(9);
        System.out.println(maiores(itens, 4).size());
    }
}
''',
},
"cpp": {
"somar": '''#include <iostream>

int somar(int a, int b) {
    int total = a + b;
    return total;
}

int dobrar(int x) {
    return x * 2;
}

int main() {
    int resultado = somar(2, 3);
    std::cout << dobrar(resultado) << std::endl;
    return 0;
}
''',
"lista": '''#include <iostream>
#include <vector>

std::vector<int> maiores(const std::vector<int>& itens, int corte) {
    std::vector<int> saida;
    for (int item : itens) {
        if (item > corte) {
            saida.push_back(item);
        }
    }
    return saida;
}

int main() {
    std::vector<int> itens = {1, 5, 9};
    std::cout << maiores(itens, 4).size() << std::endl;
    return 0;
}
''',
},
}


# ══════════════════════════════════════════════════════════════════════
#  OS DEFEITOS — cada um devolve TODAS as formas de aplicá-lo
#
#  Um injetor não devolve UM código quebrado: devolve um por lugar onde o
#  defeito cabe. A mesma semente com cinco `;` vira cinco exemplos
#  diferentes, cada um com a mensagem que o compilador deu para AQUELE
#  lugar — que é justamente a variedade que a rede precisa ver.
# ══════════════════════════════════════════════════════════════════════
def _cada_ocorrencia(codigo, padrao, troca):
    """Aplica `troca` em uma ocorrência de cada vez."""
    saida = []
    for m in re.finditer(padrao, codigo):
        saida.append(codigo[:m.start()] + troca(m) + codigo[m.end():])
    return saida


def tirou_ponto_e_virgula(codigo, ling):
    if ling == "python":
        return []
    return _cada_ocorrencia(codigo, r";", lambda m: "")


def tirou_dois_pontos(codigo, ling):
    if ling != "python":
        return []
    return _cada_ocorrencia(codigo, r":\n", lambda m: "\n")


def nome_desconhecido(codigo, ling):
    """Troca um uso de variável por um nome que não existe."""
    alvos = ["total", "resultado", "saida", "itens", "corte", "saldo", "valor",
             "numeros", "grandes"]
    saida = []
    for alvo in alvos:
        usos = [m for m in re.finditer(rf"\b{alvo}\b", codigo)]
        if len(usos) < 2:
            continue
        m = usos[-1]                    # o ÚLTIMO uso: declara e depois erra
        saida.append(codigo[:m.start()] + alvo + "x" + codigo[m.end():])
    return saida


def tirou_import(codigo, ling):
    padroes = {"python": r"^import .+\n", "java": r"^import .+;\n",
               "csharp": r"^using .+;\n", "cpp": r"^#include <.+>\n",
               "javascript": r"^const .+ = require\(.+\);\n", "php": r"^use .+;\n"}
    p = padroes.get(ling)
    if not p:
        return []
    return _cada_ocorrencia(codigo, p, lambda m: "")


def faltou_fechar(codigo, ling):
    if ling == "python":
        return []
    return _cada_ocorrencia(codigo, r"\n\}", lambda m: "")[:3]


def tipo_errado(codigo, ling):
    if ling not in ("csharp", "java", "cpp"):
        return []
    return _cada_ocorrencia(codigo, r"\bint (total|resultado|corte|x)\b",
                            lambda m: "string " + m.group(1))


def metodo_errado(codigo, ling):
    trocas = {"python": [("append", "apend"), ("print", "prnt")],
              "javascript": [("push", "psh"), ("console.log", "console.lg")],
              "csharp": [("WriteLine", "WritLine"), ("Add", "Addd"),
                         ("Where", "Wher"), ("OrderBy", "OrderBi")],
              "java": [("println", "printn"), ("add", "addd")],
              "cpp": [("push_back", "push_bak")],
              "php": [("print_r", "print_rr")]}
    saida = []
    for certo, errado in trocas.get(ling, []):
        if certo in codigo:
            saida.append(codigo.replace(certo, errado, 1))
    return saida


def faltou_aspas(codigo, ling):
    return _cada_ocorrencia(codigo, r'"[a-zA-Z: ]+"',
                            lambda m: m.group(0)[:-1])[:2]


DEFEITOS = {
    "tirou_ponto_e_virgula": tirou_ponto_e_virgula,
    "tirou_dois_pontos":     tirou_dois_pontos,
    "nome_desconhecido":     nome_desconhecido,
    "tirou_import":          tirou_import,
    "faltou_fechar":         faltou_fechar,
    "tipo_errado":           tipo_errado,
    "metodo_errado":         metodo_errado,
    "faltou_aspas":          faltou_aspas,
}


# ══════════════════════════════════════════════════════════════════════
#  OS COMPILADORES
# ══════════════════════════════════════════════════════════════════════
def achar_csharp():
    """csc do SDK + todas as DLLs do runtime como referência.

    `dotnet build` faria a mesma conferência montando um projeto inteiro e
    levando segundos. O csc direto responde em meio segundo — e é o mesmo
    compilador, então é a mesma mensagem de erro.

    O csc não fica num caminho único: no Linux mora em `/usr/share/dotnet`,
    no Windows em `%%ProgramFiles%%\\dotnet`. Procurar nos dois (e nos atalhos
    de usuário) é o que evita o assistente dizer "sem csc" onde há SDK.
    """
    raizes = [Path(os.environ.get("ProgramFiles", "")) / "dotnet",
              Path(os.environ.get("ProgramW6432", "")) / "dotnet",
              Path.home() / ".dotnet",
              Path("/usr/share/dotnet"),
              Path("/usr/lib/dotnet")]
    sdks = []
    for r in raizes:
        if r.exists():
            sdks += [p for p in (r / "sdk").glob("*/Roslyn/bincore/csc.dll")]
    sdks = sorted(set(sdks), key=lambda p: (p.parent.parent.parent.name,))
    if not sdks:
        return None, None
    # as refs do runtime vêm da MESMA instalação do csc, não das outras:
    #   <instalacao>/sdk/<versao>/Roslyn/bincore/csc.dll
    #   <instalacao>/shared/Microsoft.NETCore.App/<versao>/
    instalacao = sdks[0].parents[4]
    shared = instalacao / "shared"
    refs = sorted(shared.glob("Microsoft.NETCore.App/*/")) \
        if shared.exists() else []
    if not refs:
        return None, None
    return sdks[0], refs[-1]


CSC, CSC_REFS = achar_csharp()


def _e_assembly_gerenciado(caminho):
    """True se o .dll tem metadados CLI (assembly .NET), não só fotos PE.

    No Linux o runtime deixa as bibliotecas NATIVAS com `.so`, e um glob
    de `*.dll` pega só o gerenciado. No Windows as nativas TAMBÉM são
    `.dll` — `coreclr.dll`, `msquic.dll`, `System.IO.Compression.Native`.
    Passá-las como `/r:` para o csc é erro CS0009 "Imagem PE não contém
    metadados gerenciados". Em vez de seguir o mapa de seções (que muda de
    layout entre PE32 e PE32+), procuro a assinatura do cabeçalho CLI/COR20
    — um assembly gerenciado SEMPRE começa com `cb=0x48` e
    `MajorRuntimeVersion=2, Minor=5`; um PE nativo nunca tem.
    """
    try:
        with open(caminho, "rb") as f:
            dados = f.read(65536)
        return b"\x48\x00\x00\x00\x02\x00\x05\x00" in dados
    except OSError:
        return False


def _referencias_csharp():
    return sorted(p for p in CSC_REFS.glob("*.dll")
                  if _e_assembly_gerenciado(p))


def compilar(codigo, ling, pasta, outros=None):
    """Roda o compilador de verdade. Devolve (compilou, mensagem).

    `outros` = {relativo: conteudo} de arquivos irmãos gravados na pasta
    antes de compilar — para C# o csc recebe os `.cs` do mesmo projeto na
    mesma chamada (como `dotnet build`); nada muda nas outras linguagens.
    """
    nomes = {"python": "p.py", "javascript": "p.js", "php": "p.php",
             "csharp": "p.cs", "java": "Programa.java", "cpp": "p.cpp"}
    arq = pasta / nomes[ling]
    arq.write_text(codigo, encoding="utf-8")
    irmas = []
    if outros:
        for rel, conteudo in outros.items():
            alvo = pasta / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding="utf-8")
        irmas = list(outros.keys())

    if ling == "python":
        cmd = [sys.executable, "-m", "py_compile", str(arq)]
    elif ling == "javascript":
        cmd = ["node", "--check", str(arq)]
    elif ling == "php":
        cmd = ["php", "-l", str(arq)]
    elif ling == "cpp":
        cmd = ["g++", "-fsyntax-only", str(arq)]
    elif ling == "java":
        cmd = ["javac", "-d", str(pasta / "out"), str(arq)]
    elif ling == "csharp":
        if not CSC:
            return None, "sem csc"
        rsp = pasta / "refs.rsp"
        if not rsp.exists():
            linhas = ["/nologo", "/t:exe", "/nostdlib+"]
            # aspas em volta: no response file o espaço de "Program Files"
            # quebraria o caminho e o csc trataria "Files\dotnet\..." como
            # arquivo de origem — medido no meu Windows, erro CS2001.
            linhas += [f'/r:"{d}"' for d in _referencias_csharp()]
            rsp.write_text("\n".join(linhas), encoding="utf-8")
        fontes = [f'"{pasta / rel}"' for rel in irmas] + [f'"{arq}"']
        cmd = ["dotnet", str(CSC), f"@{rsp}", f"/out:{pasta}/p.dll"] + fontes
    else:
        return None, "linguagem desconhecida"

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           errors="replace")
    except FileNotFoundError:
        return None, f"sem {Path(cmd[0]).name}"
    except subprocess.TimeoutExpired:
        return None, "(passou de 60s)"
    saida = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
    return r.returncode == 0, saida


# ══════════════════════════════════════════════════════════════════════
#  LER A MENSAGEM DO COMPILADOR
#
#  CADA COMPILADOR ESCREVE DE UM JEITO, E FINGIR QUE HÁ UM FORMATO SÓ DÁ
#  NÚMERO ERRADO EM SILÊNCIO.
#
#      csharp   p.cs(12,9): error CS0103: The name 'x' does not exist
#      java     Programa.java:3: error: ';' expected
#      cpp      p.cpp:5:20: error: 'totalx' was not declared in this scope
#      python   File "p.py", line 10        (a mensagem vem na linha seguinte)
#      node     /caminho/p.js:11            (idem)
#      php      PHP Parse error: ... in /caminho/p.php on line 12
#
#  A primeira versão disto usava UMA regex pensada no formato do C# e
#  aplicava nos seis. Resultado medido: JavaScript devolvia "linha 1637"
#  — que era um pedaço do caminho do arquivo temporário — e Python e PHP
#  devolviam zero. Um leitor por compilador é mais código e é o certo.
LEITORES = {
    "csharp": r"\((?P<linha>\d+),(?P<coluna>\d+)\):\s*error\s+(?P<codigo>CS\d+):\s*(?P<msg>.+)",
    "java":   r"^[^:\n]+\.java:(?P<linha>\d+):\s*error:\s*(?P<msg>.+)",
    "cpp":    r"^[^:\n]+\.cpp:(?P<linha>\d+):(?P<coluna>\d+):\s*error:\s*(?P<msg>.+)",
    "python": r'File "[^"]+", line (?P<linha>\d+)',
    "javascript": r"^[^\n]+\.js:(?P<linha>\d+)$",
    "php":    r"(?P<msg>.+?)\s+in\s+[^\n]+\.php\s+on line\s+(?P<linha>\d+)",
}


def ler_erro(saida, ling):
    """(linha, coluna, codigo, mensagem) — ou zeros quando não reconhece."""
    padrao = LEITORES.get(ling)
    m = re.search(padrao, saida, re.M) if padrao else None
    if not m:
        primeira = saida.strip().splitlines()[0][:200] if saida.strip() else ""
        return 0, 0, "", primeira
    d = m.groupdict()
    msg = (d.get("msg") or "").strip()
    if ling in ("python", "javascript"):
        # Nestes dois a linha só diz ONDE. O QUE é vem no fim da saída:
        # "SyntaxError: invalid syntax".
        fim = [l for l in saida.strip().splitlines()
               if re.match(r"^\w*(Error|Exception)\b", l.strip())]
        msg = fim[-1].strip() if fim else msg
    cod = d.get("codigo") or ""
    if not cod:
        # java e cpp não numeram o erro; a própria mensagem vira a etiqueta
        cod = re.sub(r"[^a-z ]", "", msg.lower())[:40].strip().replace(" ", "_")
    return int(d.get("linha") or 0), int(d.get("coluna") or 0), cod, msg


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--linguagens", default=",".join(SEMENTES))
    p.add_argument("--saida", default=str(RAIZ / "dados" / "erros_colhidos.jsonl"))
    a = p.parse_args()
    quais = [x.strip() for x in a.linguagens.split(",") if x.strip() in SEMENTES]

    t0 = time.time()
    colhidos, descartados, sementes_podres = [], 0, []
    pasta = Path(tempfile.mkdtemp(prefix="colher_"))
    print()
    for ling in quais:
        pl = pasta / ling
        pl.mkdir(parents=True, exist_ok=True)
        ti = time.time()
        n_ling = 0
        for nome_semente, certo in SEMENTES[ling].items():
            # CONFERÊNCIA 1: a semente compila?
            ok, msg = compilar(certo, ling, pl)
            if not ok:
                sementes_podres.append((ling, nome_semente, msg.splitlines()[:1]))
                continue
            for nome_defeito, injetar in DEFEITOS.items():
                for errado in injetar(certo, ling):
                    if errado == certo:
                        continue
                    # CONFERÊNCIA 2: o defeito realmente quebrou?
                    ok2, erro = compilar(errado, ling, pl)
                    if ok2 is None or ok2 is True:
                        descartados += 1
                        continue
                    linha, coluna, cod, msg = ler_erro(erro, ling)
                    colhidos.append({
                        "linguagem": ling, "semente": nome_semente,
                        "defeito": nome_defeito,
                        "codigo_errado": errado, "codigo_certo": certo,
                        "erro": erro[:1500], "mensagem": msg,
                        "codigo_do_erro": cod, "linha": linha, "coluna": coluna,
                    })
                    n_ling += 1
        print(f"  {ling:<12} {n_ling:>4} exemplos   {time.time()-ti:>6.1f}s")

    shutil.rmtree(pasta, ignore_errors=True)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        for e in colhidos:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    sem_linha = sum(1 for e in colhidos if not e["linha"])
    print(f"\n  {len(colhidos)} exemplos colhidos em {time.time()-t0:.0f}s")
    print(f"  {sem_linha} sem linha reconhecida" +
          ("  <- o leitor daquele compilador precisa de olhada" if sem_linha else "  ok"))
    print(f"  {descartados} descartados — o 'defeito' não quebrou nada")
    if sementes_podres:
        print(f"  ⚠ sementes que não compilam: {sementes_podres}")
    print(f"  ✓ {a.saida}\n")

    por = {}
    for e in colhidos:
        por.setdefault(e["defeito"], 0)
        por[e["defeito"]] += 1
    print(f"  {'defeito':<24}{'exemplos':>9}")
    print("  " + "─" * 34)
    for d, n in sorted(por.items(), key=lambda x: -x[1]):
        print(f"  {d:<24}{n:>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
