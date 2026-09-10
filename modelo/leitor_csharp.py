# -*- coding: utf-8 -*-
"""LER AS CLASSES DE UM PROJETO C# — o chão de qualquer consulta LINQ.

POR QUE ISTO NÃO É A REDE, E NEM DEVE SER

Para escrever `transacoes.Where(t => t.Valor > 1000m)` é preciso saber
três coisas que NÃO se adivinham:

    · a lista se chama `transacoes` e é de `TransacaoFinanceira`
    · essa classe tem uma propriedade `Valor`
    · `Valor` é `decimal`, então o literal leva `m` no fim

Nada disso é opinião. Está escrito no arquivo, exato, e ler é a
ferramenta certa: uma rede que "adivinha" que existe uma propriedade
`Valor` vai um dia adivinhar `Valorr` e o compilador recusa. O que a rede
faz é ESCOLHER entre o que existe; quem diz o que existe é este arquivo.

É também o que faz a coisa funcionar em QUALQUER projeto: as propriedades
não vêm do treino, vêm do código que está na frente dela. Trocou de
projeto, trocou a lista de opções, sem retreinar nada.

O QUE ELE NÃO FAZ

Não é um compilador de C#. É um leitor de DECLARAÇÕES, que é a parte
regular da linguagem: `public decimal Valor { get; set; }` tem sempre a
mesma cara. Corpo de método, expressão, genérico aninhado de três níveis
— nada disso passa por aqui, e não precisa passar.
"""
import re
from pathlib import Path

# `public decimal Valor { get; set; }` · `public string? Codigo { get; set; }`
# `public List<string> Tags { get; set; } = new();`
PROPRIEDADE = re.compile(
    r"^\s*public\s+(?!class|enum|record|interface)"
    r"(?P<tipo>[A-Za-z_][\w<>,\.\[\]]*\??)\s+"
    r"(?P<nome>[A-Za-z_]\w*)\s*\{\s*get\s*;",
    re.M)
CLASSE = re.compile(r"^\s*public\s+(?:sealed\s+|abstract\s+|partial\s+)*"
                    r"(?:class|record)\s+(?P<nome>\w+)", re.M)
ENUM = re.compile(r"^\s*public\s+enum\s+(?P<nome>\w+)\s*\{(?P<corpo>[^}]*)\}", re.M)
# `var transacoes = new List<TransacaoFinanceira>` · `List<LogSistema> logs =`
LISTA_VAR = re.compile(
    r"\b(?:var\s+(?P<n1>\w+)\s*=\s*new\s+List<(?P<t1>\w+)>"
    r"|List<(?P<t2>\w+)>\s+(?P<n2>\w+)\s*=)")

NUMEROS = {"int", "long", "short", "byte", "float", "double", "decimal"}
SUFIXO = {"decimal": "m", "float": "f", "double": "d", "long": "L"}


class Propriedade:
    def __init__(self, nome, tipo):
        self.nome = nome
        self.bruto = tipo
        self.opcional = tipo.endswith("?")
        t = tipo.rstrip("?")
        self.colecao = t.startswith(("List<", "IEnumerable<", "ICollection<",
                                     "IList<")) or t.endswith("[]")
        self.tipo = t

    @property
    def de_texto(self):
        return self.tipo == "string"

    @property
    def de_numero(self):
        return self.tipo in NUMEROS

    @property
    def de_data(self):
        return self.tipo in ("DateTime", "DateTimeOffset", "DateOnly")

    @property
    def de_verdade(self):
        return self.tipo == "bool"

    def literal(self, valor):
        """Escreve o valor do jeito que o C# aceita para ESTE tipo.

        `1000` numa propriedade decimal precisa virar `1000m`, senão o
        compilador recusa a comparação. Isso é regra de linguagem, não de
        gosto — e é o tipo de detalhe que faz a diferença entre código que
        compila e código que quase compila.
        """
        if self.de_texto:
            return '"%s"' % str(valor).replace('"', '\\"')
        if self.de_numero:
            return f"{valor}{SUFIXO.get(self.tipo, '')}"
        if self.de_verdade:
            return "true" if str(valor).lower() in ("true", "sim", "1") else "false"
        return str(valor)

    def __repr__(self):
        marcas = "".join(m for m, c in (("?", self.opcional), ("[]", self.colecao)) if c)
        return f"{self.nome}:{self.tipo}{marcas}"


class Entidade:
    def __init__(self, nome, arquivo):
        self.nome, self.arquivo = nome, arquivo
        self.propriedades = []

    def prop(self, nome):
        baixo = nome.strip().lower()
        for p in self.propriedades:
            if p.nome.lower() == baixo:
                return p
        return None

    def __repr__(self):
        return f"{self.nome}({len(self.propriedades)} props)"


class ProjetoCSharp:
    """O que um projeto C# oferece a uma consulta: entidades, enums, listas."""

    def __init__(self, raiz):
        self.raiz = Path(raiz)
        self.entidades = {}      # nome da classe -> Entidade
        self.enums = {}          # nome do enum   -> [valores]
        self.listas = {}         # nome da variável -> nome da classe
        self.ler()

    # ── leitura ──────────────────────────────────────────────────────
    FORA = {"bin", "obj", ".vs", ".git", "node_modules", "packages"}

    def arquivos(self):
        for f in sorted(self.raiz.rglob("*.cs")):
            if any(p in self.FORA for p in f.parts):
                continue
            # o próprio compilador gera .cs em obj/; ler isso seria ler
            # o que a máquina escreveu e não o que a pessoa escreveu
            if f.name.endswith((".g.cs", ".AssemblyInfo.cs")):
                continue
            yield f

    def ler(self):
        for f in self.arquivos():
            try:
                texto = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in ENUM.finditer(texto):
                valores = [v.strip().split("=")[0].strip()
                           for v in m.group("corpo").split(",") if v.strip()]
                self.enums[m.group("nome")] = [v for v in valores if v]
            # cada classe leva as propriedades que aparecem DEPOIS dela e
            # antes da próxima — é o que separa duas classes no mesmo arquivo
            marcos = [(m.start(), m.group("nome")) for m in CLASSE.finditer(texto)]
            for i, (pos, nome) in enumerate(marcos):
                fim = marcos[i + 1][0] if i + 1 < len(marcos) else len(texto)
                ent = self.entidades.setdefault(nome, Entidade(nome, f))
                for p in PROPRIEDADE.finditer(texto[pos:fim]):
                    if not ent.prop(p.group("nome")):
                        ent.propriedades.append(
                            Propriedade(p.group("nome"), p.group("tipo")))
            for m in LISTA_VAR.finditer(texto):
                nome = m.group("n1") or m.group("n2")
                tipo = m.group("t1") or m.group("t2")
                if nome and tipo:
                    self.listas[nome] = tipo

    # ── o que a rede recebe como opções ──────────────────────────────
    def opcoes_de(self, entidade):
        """As propriedades daquela classe: é entre ESTAS que a rede escolhe."""
        e = self.entidades.get(entidade)
        return list(e.propriedades) if e else []

    def valores_do_enum(self, tipo):
        return self.enums.get(tipo.rstrip("?"), [])

    def lista_de(self, entidade):
        """A variável que guarda a lista daquela classe, se houver."""
        for var, tipo in self.listas.items():
            if tipo == entidade:
                return var
        return None

    def resumo(self):
        linhas = [f"{len(self.entidades)} classes · {len(self.enums)} enums · "
                  f"{len(self.listas)} listas"]
        for nome, e in self.entidades.items():
            lista = self.lista_de(nome)
            onde = f"  <- lista `{lista}`" if lista else ""
            linhas.append(f"\n  {nome}{onde}")
            for p in e.propriedades:
                extra = ""
                if p.tipo in self.enums:
                    extra = "  {" + " · ".join(self.enums[p.tipo]) + "}"
                linhas.append(f"     {p.nome:<24} {p.bruto:<18}{extra}")
        if self.enums:
            linhas.append("")
            for nome, vals in self.enums.items():
                linhas.append(f"  enum {nome}: {', '.join(vals)}")
        return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("uso: python modelo/leitor_csharp.py <pasta do projeto C#>")
        raise SystemExit(1)
    print(ProjetoCSharp(sys.argv[1]).resumo())
