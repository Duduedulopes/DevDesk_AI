# -*- coding: utf-8 -*-
"""O COMPILADOR COMO JUIZ — em qualquer projeto C#, e sem tocar nele.

    python provas/juiz_csharp.py <pasta do projeto C#> [corpus.jsonl]

POR QUE UM JUIZ, E NÃO UM GABARITO

"Parece certo" não é medida. `transacoes.Wher(t => t.Valorr > 10)` parece
certo e não existe: nem o método nem a propriedade. A única resposta sem
opinião é a do `dotnet build`, que diz sim ou não e ainda diz em que
linha errou.

DUAS DECISÕES DE ENGENHARIA QUE VALEM A PENA CONTAR

1. TODAS AS CONSULTAS NUMA COMPILAÇÃO SÓ. Uma por uma custaria ~3
   segundos cada; 150 consultas seriam 7 minutos. Todas juntas num
   arquivo, cada uma numa variável própria, custam os mesmos 3 segundos —
   e o número da linha do erro diz exatamente qual delas caiu.

2. O JUIZ TRABALHA NUMA CÓPIA. Ele copia os `.cs` e o `.csproj` para uma
   pasta temporária e compila lá. O projeto da pessoa não ganha um
   `Consultas.cs` que ela não escreveu, nem um `bin/` novo. Um teste que
   suja o que está testando não é teste.

O CABEÇALHO É LIDO, NÃO ESCRITO À MÃO

Os `using` saem dos `namespace` que existem no projeto, e os parâmetros
saem das listas que o leitor achou (`transacoes`, `logs`, o que for). Era
aqui que estava o último pedaço chumbado no projeto do Eduardo — e
chumbado ele valeria para um projeto só.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modelo.leitor_csharp import ProjetoCSharp        # noqa: E402

NAMESPACE = re.compile(r"^\s*namespace\s+([\w\.]+)\s*[;{]", re.M)
PACOTE = re.compile(r"<PackageReference\b")
ENTRADA = re.compile(r"\bstatic\s+(?:async\s+)?(?:void|int|Task(?:<int>)?)\s+Main\s*\(")
FORA = {"bin", "obj", ".vs", ".git", "node_modules", "packages"}
# uma pasta de `.cs` sem `.csproj` ainda é um projeto que dá para julgar:
# o `.csproj` que falta é escrito NA CÓPIA, e some junto com ela
CSPROJ = ('<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n'
          '    <OutputType>{saida}</OutputType>\n'
          '    <TargetFramework>net8.0</TargetFramework>\n'
          '    <Nullable>enable</Nullable>\n'
          '    <ImplicitUsings>enable</ImplicitUsings>\n'
          '  </PropertyGroup>\n</Project>\n')
# sem fonte de pacote não há restore pela rede: num projeto que não usa
# pacote nenhum isso é o que faz o build funcionar offline, e num que usa
# seria o que o quebraria — por isso a conferência antes de escrever
SEM_REDE = ('<?xml version="1.0" encoding="utf-8"?>\n<configuration>\n'
            '  <packageSources><clear /></packageSources>\n</configuration>\n')


class Juiz:
    """Compila consultas contra um projeto C#, numa cópia descartável."""

    def __init__(self, projeto, proj_lido=None):
        self.origem = Path(projeto)
        self.proj = proj_lido or ProjetoCSharp(self.origem)
        self.pasta = Path(tempfile.mkdtemp(prefix="juiz_csharp_"))
        self._copiar()
        self._cabecalho()

    # ── a cópia ──────────────────────────────────────────────────────
    def _copiar(self):
        usa_pacote = False
        for f in self.origem.rglob("*"):
            if not f.is_file() or any(p in FORA for p in f.relative_to(self.origem).parts):
                continue
            if f.suffix.lower() not in (".cs", ".csproj", ".props", ".targets", ".json"):
                continue
            destino = self.pasta / f.relative_to(self.origem)
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, destino)
            if f.suffix.lower() == ".csproj" and PACOTE.search(
                    f.read_text(encoding="utf-8", errors="ignore")):
                usa_pacote = True
        fontes = list(self.pasta.rglob("*.cs"))
        if not fontes:
            raise RuntimeError(f"não achei nenhum .cs em {self.origem}")
        if not list(self.pasta.rglob("*.csproj")):
            tem_main = any(ENTRADA.search(f.read_text(encoding="utf-8", errors="ignore"))
                           for f in fontes)
            solto = any(f.name == "Program.cs" for f in fontes)
            saida = "Exe" if (tem_main or solto) else "Library"
            (self.pasta / f"{self.origem.resolve().name or 'Projeto'}.csproj").write_text(
                CSPROJ.format(saida=saida), encoding="utf-8")
        if not usa_pacote:
            (self.pasta / "NuGet.config").write_text(SEM_REDE, encoding="utf-8")
        self._alvo_que_a_maquina_tem()

    def _alvo_que_a_maquina_tem(self):
        """Se o projeto mira um .NET que esta máquina não tem, mira o que tem.

        O `.csproj` dele diz `net10.0`; a máquina onde eu meço tem o 8. Sem
        isto o build falha por FALTA DE SDK e todas as consultas aparecem
        como erradas — o juiz diria "a rede errou tudo" quando o que faltou
        foi o compilador. Reprovar por motivo errado é pior que não medir.

        Só a CÓPIA é alterada, e o aviso sai na tela: se o código usa algo
        que só existe na versão nova, o erro vai aparecer e é legítimo.
        """
        tenho = set()
        try:
            r = subprocess.run(["dotnet", "--list-runtimes"],
                               capture_output=True, text=True, timeout=60)
            for m in re.finditer(r"Microsoft\.NETCore\.App (\d+)\.(\d+)", r.stdout):
                tenho.add((int(m.group(1)), int(m.group(2))))
        except (OSError, subprocess.SubprocessError):
            return
        if not tenho:
            return
        maior = max(tenho)
        for cs in self.pasta.rglob("*.csproj"):
            texto = cs.read_text(encoding="utf-8-sig", errors="ignore")
            m = re.search(r"<TargetFramework>net(\d+)\.(\d+)</TargetFramework>", texto)
            if not m or (int(m.group(1)), int(m.group(2))) in tenho:
                continue
            novo = f"net{maior[0]}.{maior[1]}"
            print(f"   (aviso: o projeto mira net{m.group(1)}.{m.group(2)} e esta "
                  f"máquina só tem até {novo}; a cópia foi ajustada)")
            cs.write_text(re.sub(r"<TargetFramework>[^<]*</TargetFramework>",
                                 f"<TargetFramework>{novo}</TargetFramework>", texto),
                          encoding="utf-8")

    # ── o cabeçalho, lido do projeto ─────────────────────────────────
    def _cabecalho(self):
        nomes = []
        for f in sorted(self.pasta.rglob("*.cs")):
            for m in NAMESPACE.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                if m.group(1) not in nomes and m.group(1) != "Prova":
                    nomes.append(m.group(1))
        self.listas = [(v, t) for v, t in sorted(self.proj.listas.items())]
        args = ", ".join(f"List<{t}> {v}" for v, t in self.listas) or "int _vazio"
        usos = "".join(f"using {n};\n" for n in nomes)
        self.cabeca = (f"{usos}\nnamespace Prova;\n\npublic static class Consultas\n"
                       f"{{\n    public static void Rodar({args})\n    {{\n")
        self.linhas_cabeca = self.cabeca.count("\n")

    # ── julgar ───────────────────────────────────────────────────────
    def compilar(self, consultas, tempo=300):
        """[(rotulo, linq)] -> {rotulo: (compila, erro)}. Uma compilação só."""
        if not consultas:
            return {}
        linhas, mapa = [], {}
        for i, (rotulo, linq) in enumerate(consultas):
            # `var` deixa o compilador inferir o tipo: se a consulta devolve
            # bool, int, decimal ou lista, ele aceita do mesmo jeito — o que
            # se está julgando é a EXPRESSÃO, não o tipo que eu esperava.
            linhas.append(f"        var r{i} = {linq};")
            mapa[self.linhas_cabeca + i + 1] = rotulo
        alvo = self.pasta / "Consultas.cs"
        alvo.write_text(self.cabeca + "\n".join(linhas) + "\n    }\n}\n",
                        encoding="utf-8")
        try:
            r = subprocess.run(["dotnet", "build", "-v", "q", "--nologo"],
                               cwd=self.pasta, capture_output=True, text=True,
                               timeout=tempo)
            saida = r.stdout + r.stderr
        except FileNotFoundError:
            raise RuntimeError("`dotnet` não está no PATH — sem juiz não há medida")
        ruins = {}
        for m in re.finditer(
                r"Consultas\.cs\((\d+),\d+\):\s*error\s+(\w+):\s*(.+?)\s*(?:\[|$)",
                saida, re.M):
            rot = mapa.get(int(m.group(1)))
            if rot is not None and rot not in ruins:
                ruins[rot] = f"{m.group(2)}: {m.group(3)[:90]}"
        # erro que não caiu em nenhuma linha nossa (o projeto não compila,
        # falta SDK, restore falhou): reprovar tudo em silêncio seria
        # mentir sobre a rede, então isso vira erro de verdade
        if not ruins and "error" in saida.lower() and " 0 Error" not in saida:
            geral = next((l.strip() for l in saida.splitlines()
                          if ": error" in l.lower()), "")
            if geral and "Consultas.cs" not in geral:
                raise RuntimeError(f"o projeto não compila nem sem as consultas: {geral}")
        alvo.unlink(missing_ok=True)
        return {rot: (rot not in ruins, ruins.get(rot, "")) for rot, _ in consultas}

    def fechar(self):
        shutil.rmtree(self.pasta, ignore_errors=True)


if __name__ == "__main__":
    import json
    import random
    if len(sys.argv) < 2:
        print("uso: python provas/juiz_csharp.py <pasta do projeto C#> [corpus.jsonl]")
        raise SystemExit(1)
    juiz = Juiz(sys.argv[1])
    print(f"cabeçalho lido do projeto:\n{juiz.cabeca}")
    # o juiz REPROVA? três consultas erradas de propósito
    print("prova do juiz (estas TÊM de falhar):")
    lista = juiz.listas[0][0] if juiz.listas else "x"
    ruins = [("propriedade inventada", f"{lista}.Where(z => z.NaoExisteIsso > 10).ToList()"),
             ("metodo inventado", f"{lista}.Wher(z => z != null).ToList()"),
             ("comparacao impossivel", f"{lista}.Count(z => z > z)")]
    for rot, (bom, err) in juiz.compilar(ruins).items():
        print(f"   {'PASSOU (ruim!)' if bom else 'reprovou'}  {rot:<22} {err[:60]}")

    caminho = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        Path(__file__).resolve().parent.parent / "dados" / "corpus_linq.jsonl"
    if caminho.exists():
        pares = [json.loads(l) for l in open(caminho, encoding="utf-8")]
        amostra = random.Random(3).sample(pares, min(150, len(pares)))
        res = juiz.compilar([(str(i), p["linq"]) for i, p in enumerate(amostra)])
        ok = sum(1 for v in res.values() if v[0])
        print(f"\nO CORPUS COMPILA? {ok}/{len(amostra)} = {ok/len(amostra):.1%}")
        for i, p in enumerate(amostra):
            if not res[str(i)][0]:
                print(f"   X  {p['linq']}\n      {res[str(i)][1]}")
    juiz.fechar()
