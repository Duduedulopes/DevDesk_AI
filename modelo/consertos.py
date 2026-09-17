# -*- coding: utf-8 -*-
"""CONSERTAR O ERRO — a família primeiro, o molde depois.

    dotnet build / ast.parse   →   CS1061: 'List<T>' does not contain
                                   a definition for 'Filtrar'
                                        ↓
    rede: que FAMÍLIA de conserto é esta?    →  nome_errado
                                        ↓
    molde: trocar pelo nome real mais próximo → `.Where`
                                        ↓
    juiz de novo: o erro sumiu? apareceu outro?

POR QUE NÃO É UMA REDE QUE ESCREVE O CÓDIGO CONSERTADO

Porque este projeto já tentou isso, em outro lugar, e mediu: o
`escritor_linq` escrevia LINQ letra por letra e chegou a 100% de código
que COMPILA e 0% de código CERTO. A mesma pergunta, virada de "escreva a
resposta" para "escolha entre estas opções", foi de 0% para 98,7%.

Erro de compilador é ainda mais favorável a essa virada: o compilador já
diz ONDE está, QUAL token falta, e muitas vezes NOMEIA o identificador
errado. Sobra escolher entre poucas saídas — e é exatamente isso que uma
rede pequena faz bem.

O QUE A MEDIÇÃO MOSTROU, E QUE MUDOU O DESENHO

Injetei erros de verdade nos `.cs` do projeto Linq e compilei um por um:

    falta ponto e vírgula  →  CS1002 ×6, CS1514 ×1, CS1513 ×1
    caixa errada           →  CS1003 ×3, CS1002 ×3, CS0260 ×2
    falta o `new`          →  CS1002 ×6, CS1955 ×2

O MESMO CS1002 saiu de três quebras diferentes. Então o código do erro
sozinho não identifica o conserto, e a entrada da rede tem de ser
    (código, mensagem, o texto da linha)
e não só o código. Foi essa medição que escreveu `texto_do_caso`.

O QUE É REDE E O QUE NÃO É

    rede     qual família, quando o código é ambíguo
    `==`     o token que falta (o compilador diz qual e em que coluna)
    `==`     qual nome real substitui o errado (distância de texto contra
             os nomes que o leitor já extraiu do projeto)

Pedir palpite onde existe resposta exata é trocar acerto por chance.
"""
import difflib
import re
import unicodedata
from pathlib import Path

from modelo.leitor_csharp import PROPRIEDADE

# ══════════════════════════════════════════════════════════════════════
#  AS FAMÍLIAS
# ══════════════════════════════════════════════════════════════════════
FAMILIAS = [
    "nome_errado",      # o identificador não existe — trocar pelo parecido
    "falta_token",      # falta `;` `)` `}` `,` `:` — o compilador diz qual
    "falta_using",      # falta `using X;` / `import x`
    "tipo_errado",      # precisa de cast, sufixo (m/f/L) ou ToString()
    "falta_new",        # `new` esquecido
    "indentacao",       # bloco sem indentar (só Python)
    # ── as que só a LINHA distingue, porque a mensagem não distingue ──
    "falta_virgula",    # `f(a b)` · `[1 2]` · `{"a": 1 "b": 2}`
    "falta_operador",   # `i 1` onde ia `i + 1` — DIAGNOSTICA, não conserta
    "igual_no_if",      # `if x = 1:` → `==`
    "palavra_errada",   # `retrn` · `elsif` · `improt`
    "pontuacao_dobrada",  # `a..b` · `x,,y`
    "nao_sei",          # nenhuma das acima — e dizer isso é resposta
]

# POR QUE ESTAS CINCO EXISTEM, E O NÚMERO QUE AS JUSTIFICA
#
# 53% das quebras de Python caem em mensagem vaga (medido em 179 casos
# injetados nos arquivos reais deste projeto). E a mensagem não só é vaga
# como às vezes MENTE:
#
#     falta vírgula   36 casos  →  "Perhaps you forgot a comma?"
#     falta operador   8 casos  →  "Perhaps you forgot a comma?"
#
# A MESMA sugestão para duas causas diferentes. Quem obedece à mensagem
# põe uma vírgula onde faltava um `+`. O que desempata é a LINHA — e ler
# a linha é o que uma rede de peças faz bem.
#
# Três outras dão `invalid syntax` seco, sem sugestão nenhuma:
# `retrn` (12/12), `elsif` (12/12) e `a..b` (11/12).

# o que dizer quando a família é reconhecida mas o conserto não é óbvio
EXPLICACAO = {
    "falta_operador": ("faltou um operador entre os dois valores desta "
                       "linha. Qual (+ - * /) é você quem sabe — eu "
                       "chutar aqui seria trocar o seu cálculo pelo meu."),
}

# o que o compilador costuma dizer em cada família. NÃO é a decisão final
# (o CS1002 aparece em três famílias) — é o que alimenta o corpus e o que
# serve de rede de segurança quando a rede não passa do limiar.
PISTAS = {
    "nome_errado": ["CS0103", "CS1061", "CS0117", "NameError", "AttributeError"],
    "falta_token": ["CS1002", "CS1026", "CS1513", "CS1514", "CS1003", "CS1519",
                    "SyntaxError"],
    "falta_using": ["CS0246", "CS0234", "ModuleNotFoundError", "ImportError"],
    "tipo_errado": ["CS0029", "CS1503", "CS0266", "CS0019", "TypeError"],
    "falta_new": ["CS1955", "CS0119"],
    "indentacao": ["IndentationError", "TabError"],
}

# `CS1002: ; expected` → o token é o que vem antes de "expected"
_TOKEN_PEDIDO = re.compile(r"^\s*(\S+)\s+expected", re.I)
# `The name 'culturaBR' does not exist` → o nome errado está entre aspas
_NOME_CITADO = re.compile(r"['\"‘’]([A-Za-z_][A-Za-z0-9_]*)['\"‘’]")
# `'T' does not contain a definition for 'X'`: o PRIMEIRO é o tipo, o
# ÚLTIMO é o membro. Só a declaração (do tipo) tem o nome novo.
_DEFINICAO = re.compile(r"does not contain a definition|não contém uma definição",
                        re.I)


def nome_do_tipo(erro):
    """O nome que o `procurar` deve buscar para CHEGAR à declaração.

    Quando a mensagem diz "does not contain a definition for" (CS0117/CS1061),
    os dois nomes entre aspas são o TIPO (certo) e o MEMBRO (errado).
    Procurar o membro leva às USAGENS; é o TIPO que leva à declaração — e é
    lá que mora a resposta de um erro que nasceu noutro arquivo.
    """
    msg = getattr(erro, "mensagem", "") or ""
    citados = _NOME_CITADO.findall(msg)
    if not citados:
        return None
    if _DEFINICAO.search(msg) and len(citados) > 1:
        return citados[0]
    return citados[-1]


def texto_do_caso(erro):
    """A frase que a rede lê. UM texto, e não três campos separados.

    O código do erro entra como palavra (`cs1002`), a mensagem entra
    inteira, e a linha do código entra depois de `||`. A `Peneira` corta
    tudo em peças e a média não se importa com a fronteira — mas o `||`
    sobrevive como peça e marca onde a mensagem acaba, o que dá à rede um
    jeito barato de saber que `expected` veio do compilador e não do
    código da pessoa.
    """
    cod = str(getattr(erro, "codigo", "") or "").lower()
    msg = str(getattr(erro, "mensagem", "") or "")
    linha = str(getattr(erro, "texto", "") or "").strip()
    return f"{cod} {msg} || {linha}"


def familia_pela_pista(erro):
    """A família que as pistas sugerem, ou None. A rede pode discordar."""
    cod = str(getattr(erro, "codigo", "") or "")
    for fam, codigos in PISTAS.items():
        if cod in codigos:
            return fam
    return None


# ══════════════════════════════════════════════════════════════════════
#  OS MOLDES DE CONSERTO
# ══════════════════════════════════════════════════════════════════════
class Conserto:
    """Uma edição concreta: neste arquivo, nesta linha, isto vira aquilo."""

    __slots__ = ("arquivo", "linha", "antes", "depois", "familia", "porque")

    def __init__(self, arquivo, linha, antes, depois, familia, porque):
        self.arquivo, self.linha = str(arquivo), int(linha)
        self.antes, self.depois = antes, depois
        self.familia, self.porque = familia, porque

    def __repr__(self):
        return f"{Path(self.arquivo).name}:{self.linha} [{self.familia}] {self.porque}"

    def diff(self):
        """As duas linhas, como o `git diff` mostraria."""
        return (f"  {Path(self.arquivo).name}, linha {self.linha}\n"
                f"    - {self.antes.strip()}\n"
                f"    + {self.depois.strip()}")

    def aplicar(self, em=None):
        """Grava a linha nova. `em` permite escrever numa CÓPIA."""
        alvo = Path(em or self.arquivo)
        ls = alvo.read_text(encoding="utf-8").splitlines()
        if not (1 <= self.linha <= len(ls)):
            return False
        ls[self.linha - 1] = self.depois
        alvo.write_text("\n".join(ls) + "\n", encoding="utf-8")
        return True


def _plano(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _nome_mais_parecido(errado, conhecidos, teto=0.55):
    """O nome real mais próximo do errado, ou None se nenhum chega perto.

    O TETO EXISTE PARA ELA PODER NÃO SABER. Sem ele, `culturaBR` viraria
    o nome menos diferente da lista mesmo que fosse outra coisa
    completamente — e um conserto que compila mas troca a variável errada
    é pior que nenhum conserto, porque some no meio do código.
    """
    if not errado or not conhecidos:
        return None
    melhor, nota = None, 0.0
    alvo = _plano(errado)
    for c in conhecidos:
        n = difflib.SequenceMatcher(None, alvo, _plano(c)).ratio()
        # mesma palavra com caixa diferente é o caso mais comum de todos
        if _plano(c) == alvo and c != errado:
            n = 1.0
        if n > nota:
            melhor, nota = c, n
    return melhor if nota >= teto else None


def conserto_nome_errado(erro, nomes_conhecidos):
    """`.Filtrar` → `.Where`, `culturaBR` → `culturaBr`.

    O compilador NOMEIA o identificador que não existe — está entre aspas
    na mensagem dele. Não há nada para adivinhar sobre QUAL nome está
    errado; a única pergunta é por qual trocar, e isso é distância de
    texto contra os nomes que o leitor extraiu do projeto.
    """
    linha = erro.texto or ""
    if not linha:
        return None
    # QUAL DOS NOMES ENTRE ASPAS É O ERRADO — e isto custou 6 de 6.
    #
    #   CS1061: 'TransacaoFinanceira' does not contain a definition for 'valor'
    #            └── o tipo, que está certo ──┘                          └ o errado
    #
    # Pegando o primeiro, eu tentava consertar o nome da CLASSE. Quando a
    # mensagem tem "does not contain a definition for", o nome errado é o
    # ÚLTIMO; nas outras (`The name 'x' does not exist`) só há um.
    citados = _NOME_CITADO.findall(erro.mensagem)
    if not citados:
        return None
    errado = citados[-1] if len(citados) > 1 else citados[0]
    if errado not in linha:
        # o último não aparece na linha: tenta os outros, do fim para o começo
        errado = next((c for c in reversed(citados) if c in linha), None)
        if errado is None:
            return None
    certo = _nome_mais_parecido(errado, [n for n in nomes_conhecidos if n != errado])
    if not certo:
        return None
    novo = re.sub(rf"\b{re.escape(errado)}\b", certo, linha, count=1)
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "nome_errado",
                    f"`{errado}` não existe; o nome real mais próximo é `{certo}`")


def conserto_parenteses_aberto(erro):
    """`SyntaxError: '(' was never closed` → fecha no fim da expressão.

    O PYTHON APONTA A ABERTURA, NÃO A FALTA. O C# diz "`)` esperado na
    coluna 47" e acabou; o Python diz "o `(` da linha 12 nunca fechou" —
    a linha 12 é onde o problema COMEÇA, não onde o conserto vai. Medido:
    0 de 8, porque eu tratava as duas mensagens como se fossem a mesma.

    O conserto é contar os parênteses da linha e fechar o que sobrou, no
    fim — antes do comentário, se houver, senão o `)` entra no texto do
    comentário e não fecha nada.
    """
    linha = erro.texto or ""
    if not linha or "never closed" not in (erro.mensagem or ""):
        return None
    # A MENSAGEM COMEÇA COM ASPA: `'(' was never closed`. Pegando o
    # primeiro caractere eu pegava a aspa, não o parêntese — e o molde
    # devolvia None em 8 de 8 sem nem olhar a linha.
    m = re.search(r"([(\[{])['\"]?\s+was never closed", erro.mensagem)
    if not m:
        return None
    abre = m.group(1)
    alvo = {"(": ")", "[": "]", "{": "}"}[abre]
    faltam = linha.count(abre) - linha.count(alvo)
    if faltam <= 0:
        return None
    corpo, _, comentario = linha.partition("#")
    novo = corpo.rstrip() + alvo * faltam + (("  # " + comentario.strip())
                                             if comentario.strip() else "")
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                    f"faltou fechar {faltam} `{abre}` nesta linha")


def conserto_falta_token(erro):
    """`CS1002: ; expected` na coluna 47 → põe `;` na coluna 47.

    AQUI NÃO HÁ PALPITE NENHUM. O compilador diz o token e a coluna. Se
    ele está errado sobre isso, nada do que eu inventar melhora.
    """
    linha = erro.texto or ""
    m = _TOKEN_PEDIDO.match(erro.mensagem) or re.search(
        r"expected\s+['\"]?([;)\}\],:])", erro.mensagem)
    if not m or not linha:
        return None
    token = m.group(1).strip("'\"")
    if token not in ";)}],:" or len(token) != 1:
        return None
    col = erro.coluna if 0 < erro.coluna <= len(linha) + 1 else len(linha.rstrip()) + 1
    novo = linha[:col - 1].rstrip() + token + linha[col - 1:]
    if novo.strip() == linha.strip():
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                    f"o compilador pediu `{token}` na coluna {col}")


def conserto_parenteses_sem_abre(erro):
    """`print"oi"` → `print("oi")`, `def main):` → `def main():`.

    O balde que faltava: a ABERTURA arrancada de uma chamada ou de uma
    definição. O Python não diz "falta o `(`" — diz `unmatched ')'`, e por
    isso o `conserto_parenteses_aberto` (que só olha `never closed`) e o
    `conserto_falta_token` (que espera `expected`) passavam direto.
    Medido: o inventário de irresolúveis pôs ~10 casos neste balde.

    SÓ ONDE O REPARO É INEQUÍVOCO: o nome da função colado numa aspa
    (o `(` sumiu entre um nome e o que segue) e `def NOME)` sem argumentos.
    Nome colado a IDENTIFICADOR (`sortedresultados`) fica de fora — não
    há como saber onde o nome acaba.
    """
    linha = erro.texto or ""
    msg = (erro.mensagem or "").lower()
    if not linha.strip() or ("unmatched" not in msg
                             and "does not match" not in msg):
        return None

    m = re.search(r"([A-Za-z_]\w*)([\"'\[])", linha)
    if m:
        novo = linha[:m.end(1)] + "(" + linha[m.end(1):]
        return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                        f"a chamada `{m.group(1)}` perdeu a abertura de parêntese")

    m = re.match(r"(\s*def\s+[A-Za-z_]\w*)\)", linha)
    if m:
        novo = linha[:m.end() - 1] + "(" + linha[m.end() - 1:]
        return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                        "a definição perdeu a abertura de parêntese")
    return None


# as fronteiras em que uma string que perdeu a aspa de fechamento termina
_FRONTEIRA_ASPA = re.compile(r"[.,:)}\]'\"]")


def conserto_aspas_sem_fechar(erro):
    """`nome="Remover produto,` → `nome="Remover produto",`.

    O `_aspas` arranca a aspa de FECHAMENTO de string. O Python responde
    `unterminated string literal`, e o molde da falta de token não tem o
    que `expected` dizer. Medido: o inventário pôs 8 casos neste balde.

    O fechamento entra na PRIMEIRA FRONTEIRA ESTRUTURAL depois da
    ABERTURA: `} ] ) : , . " '` ou fim da linha. Era a COLUNA do erro que
    escolhia qual aspa era a abertura — e o Python aponta a linha toda,
    não a aspa, então o molde pegava a ÚLTIMA e dobrava o fechamento no
    fim da linha (6 de 8 falhavam exatamente assim). A abertura de verdade
    é a PRIMEIRA aspa da linha, e é o `juiz` quem garante o palpite: se a
    linha não voltar a parsear, o conserto é reprovado como qualquer outro.
    """
    linha = erro.texto or ""
    msg = (erro.mensagem or "").lower()
    if "unterminated string literal" not in msg or not linha.strip():
        return None
    q = None
    for aspas in "\"'":
        if linha.count(aspas) % 2 == 1:
            q = aspas
            break
    if q is None:
        return None
    i = linha.find(q)
    resto = linha[i + 1:]
    fim = _FRONTEIRA_ASPA.search(resto)
    onde = (i + 1 + fim.start()) if fim else len(linha)
    novo = linha[:onde] + q + linha[onde:]
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                    "a string perdeu a aspa de fechamento")


# as palavras que o leitor talvez não conheça mas que abrem chamadas: o
# `_sem_abre` cola `min` em `read`, `set` em `sorted`, `zip` em… `zip`.
_ABREM_CHAMADA = {
    "self", "open", "len", "min", "max", "set", "sorted", "zip", "str",
    "int", "list", "dict", "range", "sum", "map", "filter", "any", "all",
    "bytes", "read", "write", "encode", "decode", "input", "print",
}

# os sufixos que nunca são início de parâmetro — `read_bytes` é um nome só
_PREFIXO_QUE_TRAVA = re.compile(r"._[_A-Za-z0-9]*$")


# As palavras do próprio Python que nunca podem virar SUFIXO de um nome
# colado: `listar_past(as)` e `ma(in)` nasciam de o sufixo ser `as`/`in`
# (a aspa do `with` e o `in` vivem no arquivo e até em PALAVRAS_PY).
_SUFIXO_PROIBIDO = {
    "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or",
    "pass", "raise", "return", "try", "while", "with", "yield",
    "True", "False", "None",
}


def conserto_def_grudado(erro, nomes_conhecidos=()):
    """`def prontoself):` → `def pronto(self):`.

    O `_sem_abre` tira o `(` do cabeçalho e cola o nome da função no
    primeiro parâmetro: `pronto(self` vira `prontoself`. O compilador diz
    `unmatched ')'` — o `)` sobrou sem a abertura dele, e o `_sem_abre`
    NÃO é a família `falta_token` esperando `expected`.

    Quatro casos, quatro prioridades — é a ORDEM que distingue o nome
    inteiro (`def listar_pastas):` → `listar_pastas()`) do nome colado
    no parâmetro (`def prontoself):` → `pronto(self)`):
      1. o nome INTEIRO é conhecido do leitor: nome só, `` entra depois.
      2. o nome termina em `self`: é um método que perdeu o parêntese.
      3. `def NOME):` — o parêntese sumiu sem colar nada.
      4. sufixo conhecido mais comprido: `_ler_textocaminho` → `(...`.
    Medido: ~10 dos 36 `falta_token` irresolvíveis desta forma.
    """
    linha = erro.texto or ""
    msg = (erro.mensagem or "").lower()
    if not linha.strip() or ("unmatched" not in msg
                             and "does not match" not in msg):
        return None
    m = re.match(r"(\s*def\s+)([A-Za-z_]\w*)", linha)
    if not m:
        return None
    inicio = m.end(2)
    run = m.group(2)
    resto = linha[inicio:].lstrip()
    plenos = set(nomes_conhecidos)
    conhecido = (plenos | _ABREM_CHAMADA) - _SUFIXO_PROIBIDO

    # 1) método: `def prontoself):` / `def __init__self, raiz=...):`
    if run.endswith("self") and len(run) > len("self"):
        corte = inicio - len("self")
        novo = linha[:corte] + "(" + linha[corte:]
        return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                        f"`{run[:-4]}` é o método que perdeu a abertura de parêntese")

    # 2) `def NOME):` → `def NOME():` — o parêntese sumiu sem colar nada
    if run not in _SUFIXO_PROIBIDO and resto.startswith(")"):
        novo = linha[:inicio] + "(" + linha[inicio:]
        return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                        f"o cabeçalho `def {run}` perdeu a abertura de parêntese")

    # 3) sufixo conhecido mais comprido: `_ler_textocaminho` → `_ler_texto(caminho`
    melhor = None
    for k in conhecido:
        if (len(k) >= 2 and run.endswith(k) and len(run) > len(k)
                and not linha[:inicio - len(k)].endswith("_")
                and not _PREFIXO_QUE_TRAVA.match(run[:len(run) - len(k)])):
            if melhor is None or len(k) > len(melhor):
                melhor = k
    if melhor is None:
        return None
    corte = inicio - len(melhor)
    novo = linha[:corte] + "(" + linha[corte:]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                    f"`{linha[corte:inicio]}` é a chamada que perdeu a "
                    f"abertura de parêntese antes de `{melhor}`")


def conserto_nome_grudado(erro, nomes_conhecidos=()):
    """`openimagem)` → `open(imagem)`, `readmin(` → `read(min(`.

    A MESMA perda de `(` que o `conserto_def_grudado`, fora do cabeçalho
    de `def`: `Image.open(imagem` vira `Image.openimagem`, `read(min(resta`
    vira `readmin(resta`. O Python responde `unmatched ')'` — o fechamento
    de uma chamada cuja abertura já era. Os reparos, em ordem:

    COM ARGUMENTO  name e primeiro argumento colados, e o argumento é um
                    nome que o leitor conhece: `open(caminho...` ⇒
                    `opencaminho`: entra `(` antes de `caminho`.
    SEM ARGUMENTO   `.read_bytes)` → `.read_bytes()` — só quando o nome
                    vem de um ATRIBUTO: o `)` solto depois de um `.` quase
                    nunca é outra coisa, e qualquer corte errado o `)` que
                    sobra denuncia.
    Medido: ~15 dos 36 `falta_token` irresolvíveis desta forma.
    """
    linha = erro.texto or ""
    msg = (erro.mensagem or "").lower()
    if not linha.strip() or re.match(r"\s*def\b", linha) or not (
            "unmatched" in msg or "does not match" in msg):
        return None
    conhecido = (set(nomes_conhecidos) | _ABREM_CHAMADA) - _SUFIXO_PROIBIDO
    col = erro.coluna or 0
    alvos = []

    for m in re.finditer(r"[A-Za-z_]\w*", linha):
        run, fim = m.group(0), m.end()
        depois = linha[fim:fim + 1]
        antes = linha[:m.start()]
        if antes and (antes[-1].isalnum() or antes[-1] in "(["):
            continue
        # COM ARGUMENTO: nome e argumento colados, seguidos de `)` `,` `(`
        suf = maior_sufixo_conhecido(run, conhecido)
        if suf is not None and depois in ",)(":
            alvos.append((abs(fim - len(suf) - col) if col else -fim,
                          fim - len(suf)))
            continue
        # SEM ARGUMENTO: `.items)` `.read_bytes)` `.lower)` `Lock)`
        if depois == ")" and "." in antes[-1:]:
            alvos.append((abs(fim - col) if col else -fim, fim))

    if not alvos:
        return None
    _, corte = min(alvos)
    novo = linha[:corte] + "(" + linha[corte:]
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                    "a chamada perdeu a abertura de parêntese")


def conserto_parentese_antes_dois_pontos(erro):
    """`if len(primeira.split() <= 1:` → `if len(primeira.split()) <= 1:`.

    O `_sem_fecha` tira um `))` de `...split())):` sobrando `...split():`,
    ou um `))` de `k in (...)):` sobrando `k in (...):`. O `(:` final não
    chama o `conserto_parenteses_aberto` (a mensagem é `invalid syntax`,
    não `never closed`), e o token `)` não vem com `expected`. Medido: 3
    dos 36 `falta_token` irresolvíveis desta forma — as únicas em que a
    sobra é de abrir um parêntese para fechar antes do `:`.
    """
    linha = erro.texto or ""
    corpo = linha.rstrip()
    if not re.search(r"\)*\s*:$", corpo):
        return None
    abre = corpo.count("(")
    fecha = corpo.count(")")
    faltam = abre - fecha
    if not (0 < faltam <= 2):
        return None
    doi = corpo.rfind(":")
    novo = linha[:doi] + ")" * faltam + linha[doi:]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_token",
                    f"faltou fechar {faltam} parêntese antes dos dois pontos")


def _sufixo_util(run, conhecido):
    return [_k for _k in conhecido if conhecido_termina(run, _k)]


def conhecido_termina(run, k):
    return len(k) >= 2 and run != k and run.endswith(k)


def maior_sufixo_conhecido(run, conhecido):
    melhor = None
    for k in conhecido:
        if not conhecido_termina(run, k):
            continue
        raiz = run[:len(run) - len(k)]
        if not raiz or raiz.endswith("_") or _PREFIXO_QUE_TRAVA.match(raiz):
            continue
        if melhor is None or len(k) > len(melhor):
            melhor = k
    return melhor


# os `using` que cobrem quase tudo que some num projeto de estudo
USINGS = {
    "List": "System.Collections.Generic", "Dictionary": "System.Collections.Generic",
    "IEnumerable": "System.Collections.Generic", "HashSet": "System.Collections.Generic",
    "Enumerable": "System.Linq", "IQueryable": "System.Linq",
    "CultureInfo": "System.Globalization", "NumberStyles": "System.Globalization",
    "File": "System.IO", "Path": "System.IO", "Directory": "System.IO",
    "Task": "System.Threading.Tasks", "Regex": "System.Text.RegularExpressions",
    "StringBuilder": "System.Text", "JsonSerializer": "System.Text.Json",
    "DateTime": "System", "Math": "System", "Console": "System",
}


def _insere_using(erro, tipo, espaco):
    """`using <espaco>;` entra SEMPRE no topo, depois dos que já existem.

    O C# não se importa com a ordem; quem lê, sim.
    """
    try:
        ls = Path(erro.arquivo).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if any(l.strip() == f"using {espaco};" for l in ls):
        return None
    ultimo = max((i for i, l in enumerate(ls) if l.strip().startswith("using ")),
                 default=-1)
    alvo = ultimo + 1
    return Conserto(erro.arquivo, alvo + 1,
                    ls[alvo] if alvo < len(ls) else "",
                    f"using {espaco};\n" + (ls[alvo] if alvo < len(ls) else ""),
                    "falta_using",
                    f"`{tipo}` mora em `{espaco}` — falta o using")


def conserto_falta_using(erro):
    """`CS0246: The type 'CultureInfo' could not be found` → `using System.Globalization;`"""
    m = _NOME_CITADO.search(erro.mensagem)
    if not m:
        return None
    espaco = USINGS.get(m.group(1))
    if not espaco:
        return None
    return _insere_using(erro, m.group(1), espaco)


SUFIXO_DO_TIPO = {"decimal": "m", "float": "f", "double": "d", "long": "L"}


# ══════════════════════════════════════════════════════════════════════
#  OS MOLDES QUE LEEM — consomem a saída do `procurar` e do `ler`
# ══════════════════════════════════════════════════════════════════════
# O `procurar` devolve linhas no formato `<caminho relativo>:<linha> <texto>`.
# O molde do `consertar.py` só tinha o erro, a família e os nomes do
# PRÓPRIO arquivo; o do agente recebe também o que as ferramentas acharam.
# É o caminho que faltava: a linha do erro não tem a resposta, a declaração
# tem, e o `procurar`/`ler` a trazem.
_ACHADO = re.compile(r"([^\s:]+\.cs):\d+")
_NAMESPACE = re.compile(r"^\s*namespace\s+([\w.]+)\s*[;{]", re.M)


def _caminhos_achados(achados, raiz):
    """Os arquivos que o `procurar` citou — resolvidos contra a raiz."""
    if not achados or not raiz:
        return []
    vistos, caminhos = set(), []
    for m in _ACHADO.finditer(achados):
        p = Path(raiz) / m.group(1)
        if p.exists() and p not in vistos:
            vistos.add(p)
            caminhos.append(p)
    return caminhos


def _texto(caminho):
    try:
        return Path(caminho).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def conserto_nome_de_declaracao(erro, achados, raiz):
    """CS0117/CS1061 entre arquivos: renomearam a propriedade no declarante.

    A linha do erro usa o nome VELHO; ele já não existe em lugar nenhum.
    O que existe é a DECLARAÇÃO, noutro arquivo — o `procurar` a apontou
    (buscando o TIPO, porque é a única parte ainda viva), e é dela que este
    molde lê o nome NOVO.

    Devolver None quando o `procurar` não achou a declaração é a resposta de
    sempre: sem ela, não há como saber o nome real — e escolher um parecido
    no arquivo errado é o conserto que compila significando outra coisa.
    """
    linha = erro.texto or ""
    citados = _NOME_CITADO.findall(erro.mensagem or "")
    if not linha or not citados:
        return None
    errado = citados[-1] if len(citados) > 1 else citados[0]
    if errado not in linha:
        errado = next((c for c in reversed(citados) if c in linha), None)
        if errado is None:
            return None
    membros = []
    for p in _caminhos_achados(achados, raiz):
        membros += [m.group("nome") for m in PROPRIEDADE.finditer(_texto(p))]
    certo = _nome_mais_parecido(errado, [n for n in membros if n != errado])
    if not certo:
        return None
    novo = re.sub(rf"\b{re.escape(errado)}\b", certo, linha, count=1)
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "nome_errado",
                    f"`{errado}` foi renomeado onde é declarado; "
                    f"o nome de lá é `{certo}`")


def conserto_using_do_projeto(erro, achados, raiz):
    """CS0246 num tipo do PRÓPRIO projeto: falta o `using` do namespace dele.

    O `USINGS` cobre os tipos do .NET; para um tipo do projeto a resposta
    não está em tabela nenhuma — está no `namespace` do arquivo que declara
    a classe. O `procurar` aponta esse arquivo e este molde lê a linha dele.
    """
    m = _NOME_CITADO.search(erro.mensagem or "")
    if not m or not achados or not raiz:
        return None
    tipo = m.group(1)
    for p in _caminhos_achados(achados, raiz):
        txt = _texto(p)
        if not re.search(rf"\b(?:class|record|struct|interface|enum)\s+"
                         rf"{re.escape(tipo)}\b", txt):
            continue
        ns = _NAMESPACE.search(txt)
        if ns:
            return _insere_using(erro, tipo, ns.group(1))
    return None


def conserto_tipo_errado(erro):
    """`CS0029: cannot convert 'int' to 'decimal'` num literal → põe o sufixo.

    SÓ ONDE É LITERAL. `1000` para `decimal` é `1000m`, e isso é regra da
    linguagem. Já converter uma VARIÁVEL de um tipo para outro é decisão
    de quem escreveu — um cast calado pode truncar o número, e truncar
    dinheiro em silêncio é o tipo de conserto que ninguém quer.
    """
    linha = erro.texto or ""
    m = re.search(r"convert (?:type )?['\"](\w+)['\"] to ['\"](\w+)['\"]", erro.mensagem)
    if not m or not linha:
        return None
    de, para = m.group(1), m.group(2)
    suf = SUFIXO_DO_TIPO.get(para)
    if not suf or de not in ("int", "long", "double"):
        return None
    lit = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", linha)
    if not lit:
        return None
    novo = linha[:lit.end()] + suf + linha[lit.end():]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "tipo_errado",
                    f"literal de `{de}` num lugar de `{para}` — falta o sufixo `{suf}`")


def conserto_argumento_por_irmao(erro, lido):
    """CS1503: o argumento certo está na LINHA AO LADO, e o `ler` a mostra.

    `x.Valor.ToString(x.DataHora)` acusa "não é possível converter de
    'DateTime' para 'IFormatProvider?'" — a linha não diz o que pôr no
    lugar. A linha IRMÃ, o `ToString("<formato>")` logo abaixo, diz. Este
    molde pega o argumento da MESMA chamada numa linha vizinha do que foi
    lido.

    É mais frágil que os outros, de propósito: o valor sai do texto, não de
    uma tabela. O juiz continua sendo quem aprova — e é ele que impede o
    palpite de virar código.
    """
    linha = erro.texto or ""
    if not linha or not lido or not re.search(r"Argumento \d|Argument \d",
                                              erro.mensagem or ""):
        return None
    for ch in re.finditer(r"\.(\w+)\(([^()]*)\)", linha):
        metodo, arg = ch.group(1), ch.group(2)
        if not arg.strip():
            continue
        for l in lido.splitlines():
            if l.lstrip().startswith(">"):      # a própria linha do erro
                continue
            for c in re.finditer(rf"\.{re.escape(metodo)}\(([^()]*)\)", l):
                outro = c.group(1)
                if outro.strip() and outro != arg:
                    novo = linha[:ch.start(2)] + outro + linha[ch.end(2):]
                    return Conserto(erro.arquivo, erro.linha, linha, novo,
                                    "tipo_errado",
                                    f"o argumento certo está na linha ao "
                                    f"lado: `{outro}`")
    return None


def conserto_falta_new(erro):
    """`CS1955: Non-invocable member 'CultureInfo' cannot be used like a method.`"""
    linha = erro.texto or ""
    m = _NOME_CITADO.search(erro.mensagem)
    if not m or not linha:
        return None
    tipo = m.group(1)
    novo = re.sub(rf"(?<!new )\b{re.escape(tipo)}\s*\(", f"new {tipo}(", linha, count=1)
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_new",
                    f"`{tipo}` é um tipo, não um método — falta o `new`")


def conserto_indentacao(erro):
    """Indentação são TRÊS problemas diferentes, e eu tratava como um.

        expected an indented block    falta indentar   → indenta MAIS
        unexpected indent             sobra indentação → indenta MENOS
        unindent does not match       nível inventado  → alinha com um real

    Medido: 2 de 8, e 5 dos fracassos eram eu indentando MAIS uma linha
    que já tinha indentação demais — piorando exatamente o que devia
    consertar. Um nome de família ("indentacao") não é um conserto.
    """
    linha = erro.texto or ""
    msg = (erro.mensagem or "").lower()
    if not linha.strip():
        return None
    try:
        ls = Path(erro.arquivo).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    anteriores = [l for l in ls[:erro.linha - 1] if l.strip()]
    anterior = anteriores[-1] if anteriores else ""
    base = len(anterior) - len(anterior.lstrip())

    if "expected an indented block" in msg:
        alvo = base + 4
        porque = f"o bloco aberto acima pede indentação de {alvo}"
    elif "unexpected indent" in msg:
        # a linha anterior manda: é o nível em que esta devia estar
        alvo = base + (4 if anterior.rstrip().endswith(":") else 0)
        porque = f"esta linha está indentada demais; o nível daqui é {alvo}"
    elif "unindent" in msg or "does not match" in msg:
        # os níveis que EXISTEM acima; o conserto é cair num deles
        niveis = sorted({len(l) - len(l.lstrip()) for l in anteriores})
        atual = len(linha) - len(linha.lstrip())
        abaixo = [n for n in niveis if n <= atual]
        if not abaixo:
            return None
        alvo = abaixo[-1]
        porque = f"nível {atual} não existe neste bloco; o mais próximo é {alvo}"
    else:
        return None
    novo = " " * alvo + linha.lstrip()
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "indentacao", porque)


# as palavras do Python que a gente digita errado com mais frequência
PALAVRAS_PY = ["return", "import", "from", "class", "def", "elif", "else",
               "while", "for", "if", "try", "except", "finally", "with",
               "lambda", "yield", "assert", "raise", "global", "nonlocal",
               "pass", "break", "continue", "and", "or", "not", "in", "is",
               "None", "True", "False", "print", "len", "range", "self"]


def conserto_falta_virgula(erro):
    """`f(a b)` → `f(a, b)`. A vírgula entra ENTRE os dois valores.

    O Python aponta a coluna do segundo valor — e às vezes nem isso. O
    jeito que funciona é achar, na linha, dois pedaços colados que
    deviam estar separados: `nome nome`, `nome "texto"`, `] [`.
    """
    linha = erro.texto or ""
    if not linha.strip():
        return None
    # dentro de parênteses/colchetes/chaves: dois valores sem vírgula
    padroes = [r"(\w)\s+(\w)", r"(\w)\s+([\"'])", r"([\"'])\s+(\w)",
               r"(\))\s+(\w)", r"(\])\s+(\[)"]
    col = erro.coluna or 0
    melhor = None
    for pad in padroes:
        for m in re.finditer(pad, linha):
            # o que o Python apontou tem prioridade; senão, o mais à direita
            dist = abs(m.end(1) - col) if col else -m.end(1)
            if melhor is None or dist < melhor[0]:
                melhor = (dist, m.end(1))
    if melhor is None:
        return None
    corte = melhor[1]
    # nunca separar palavra-chave do que vem depois: `return x`, `not y`
    antes = re.search(r"(\w+)$", linha[:corte])
    if antes and antes.group(1) in PALAVRAS_PY:
        return None
    novo = linha[:corte] + "," + linha[corte:]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_virgula",
                    "faltou a vírgula separando os dois valores")


def conserto_virgula_no_dict(erro):
    """`{"ok": False "porque": ...}` → a vírgula que separa os pares.

    O `conserto_falta_virgula` não chega aqui: ele procura palavra colada
    em palavra, e em dicionário o que cola é `) "chave":`, `"valor" "chave":`
    ou `] "chave":` — o valor e a CHAVE seguinte, sem vírgula no meio.
    Medido: 16 dos 28 `falta_virgula` irresolvíveis vivem exatamente aqui.

    A `"chave":` é a pista: é ela que pode aparecer logo ATRÁS de um valor.
    Olhando para trás, se o que a precede não é `{`, `,` nem começo de
    linha, é um valor que engoliu a própria vírgula.
    """
    linha = erro.texto or ""
    if not linha.strip():
        return None
    for m in re.finditer(r'(["\'])[^"\']*\1\s*:', linha):
        j = m.start() - 1
        while j >= 0 and linha[j].isspace():
            j -= 1
        # o que precede a chave: `{` `,` ou nada = já está certa.
        # valor de dicionário acaba em letra/número, `)`, `]`, `}` ou aspas.
        if j < 0 or not (linha[j].isalnum() or linha[j] in "\"'])}"):
            continue
        novo = linha[:j + 1] + "," + linha[j + 1:]
        return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_virgula",
                        "faltou a vírgula separando os pares do dicionário")
    return None


def conserto_virgula_apos_self(erro):
    """`def desfazer(self caminho):` → `def desfazer(self, caminho):`.

    O `conserto_falta_virgula` NÃO PODE chegar aqui: o `self` está na lista
    das palavras que nunca cortam (`return x` não pode virar `return, x`),
    e a guarda o barra antes de olhar o contexto. Mas num cabeçalho de
    `def` o `self` seguido de parâmetro é SEMPRE falta de vírgula — a
    gramática não conhece `self parametro`. Medido: 7 dos 28 `falta_virgula`
    irresolvíveis vivem aqui.
    """
    linha = erro.texto or ""
    m = re.search(r"(\bdef\s+[A-Za-z_]\w*\s*\(\s*self)\s+([A-Za-z_]\w*)",
                  linha)
    if not m:
        return None
    corte = m.end(1)
    novo = linha[:corte] + "," + linha[corte:]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_virgula",
                    "no cabeçalho do `def`, `self` e o parâmetro pedem vírgula")


def conserto_virgula_no_for(erro):
    """`for p _ in brutos` → `for p, _ in brutos`.

    A mensagem (`'in' expected after for-loop variables`) diz que o `in`
    chegou cedo — a vírgula que separava as duas variáveis sumiu. Medido:
    2 dos 28 `falta_virgula` irresolvíveis.
    """
    linha = erro.texto or ""
    m = re.search(r"\bfor\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s+in\b", linha)
    if not m:
        return None
    corte = m.end(1)
    novo = linha[:corte] + "," + linha[corte:]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_virgula",
                    "faltou a vírgula entre as duas variáveis do `for`")


def conserto_virgula_em_chamada_com_aspas(erro):
    """`hasattr(s 'x')` → `hasattr(s, 'x')`.

    O molde geral ignora este caso: ele procura `nome( ) nome( ) aspas`,
    e aqui o que cola é um NOME do projeto numa string literal — o
    segundo argumento de `hasattr`/`getattr`/`isinstance`. A pista é o
    `(` imediatamente atrás: dentro de uma CHAMADA, `nome 'assim'` só
    pode ser dois argumentos sem vírgula. Medido: 3 dos 6 `falta_virgula`
    que sobraram.
    """
    linha = erro.texto or ""
    for m in re.finditer(r"\(\s*([A-Za-z_]\w*)\s+([\"'])", linha):
        fim = m.end(1)
        novo = linha[:fim] + "," + linha[fim:]
        return Conserto(erro.arquivo, erro.linha, linha, novo, "falta_virgula",
                        f"dentro da chamada, `{m.group(1)}` e o texto a seguir "
                        f"pedem vírgula")
    return None


def conserto_igual_no_if(erro):
    """`if x = 1:` → `if x == 1:`

    Aqui o próprio Python já diz ("Maybe you meant '==' or ':=' instead
    of '='?"), e mesmo assim vale o molde: a mensagem oferece DOIS
    caminhos e quem escolhe é o contexto. Dentro de um `if`/`while` de
    comparação, é `==`.
    """
    linha = erro.texto or ""
    if not re.match(r"\s*(if|elif|while)\b", linha):
        return None
    novo = re.sub(r"(?<![=!<>+\-*/])=(?!=)", "==", linha, count=1)
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "igual_no_if",
                    "dentro de um `if` a comparação é `==`; `=` atribui")


def conserto_palavra_errada(erro, nomes_conhecidos=()):
    """`retrn` → `return`, `elsif` → `elif`.

    A primeira palavra da linha é a que manda numa instrução Python, e
    `invalid syntax` sem mais nada quase sempre é ela. Comparo com as
    palavras da linguagem antes dos nomes do projeto: `elsif` parece
    `elif` e também parece um monte de variável, mas só uma das duas
    coisas pode abrir uma linha.
    """
    linha = erro.texto or ""
    m = re.match(r"(\s*)([A-Za-z_]\w*)", linha)
    if not m:
        return None
    palavra = m.group(2)
    if palavra in PALAVRAS_PY:
        return None                      # já é palavra válida
    certa = _nome_mais_parecido(palavra, PALAVRAS_PY, teto=0.7)
    if not certa:
        return None
    novo = m.group(1) + certa + linha[m.end():]
    return Conserto(erro.arquivo, erro.linha, linha, novo, "palavra_errada",
                    f"`{palavra}` não é palavra do Python; a mais próxima é `{certa}`")


def conserto_pontuacao_dobrada(erro):
    """`a..b` → `a.b`, `f(x,,y)` → `f(x,y)`."""
    linha = erro.texto or ""
    novo = re.sub(r"([.,:;])\1+", r"\1", linha, count=1)
    if novo == linha:
        return None
    return Conserto(erro.arquivo, erro.linha, linha, novo, "pontuacao_dobrada",
                    "pontuação repetida — uma só basta")


class EscolhaDeFamilia:
    """A rede que lê o caso e diz a família. Opcional — sem ela, a pista.

    POR QUE ELA EXISTE, COM O NÚMERO QUE A JUSTIFICA

    Olhar só o código do erro acerta 50% das famílias e conserta 21% dos
    casos. A rede, lendo (código + mensagem + a LINHA), acerta 84% e
    conserta 48% — medido em pastas que não entraram no corpus.

    A diferença mora onde a mensagem do Python é vaga: `invalid syntax`
    não distingue nada, e em 53% das quebras é isso que ele diz. Pior: o
    Python sugere "Perhaps you forgot a comma?" tanto para vírgula que
    falta quanto para OPERADOR que falta. Quem obedece à mensagem põe
    vírgula onde ia um `+`.
    """

    def __init__(self, caminho):
        import json
        import numpy as np
        from modelo.decisor_linq import Peneira
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        # A MESMA TRAVA DO `Cerebro`, pelo mesmo motivo: ler um modelo com
        # o tokenizador errado não dá erro — dá ruído com cara de resposta.
        tok = d.get("tokenizador")
        if tok != "peneira":
            raise ValueError(
                f"{caminho} foi treinado com tokenizador {tok!r}; esta classe "
                f"só sabe ler 'peneira'. Retreine com "
                f"`programas/treinar_consertos.py`.")
        self.familias = d["intencoes"]
        self.peneira = Peneira.de_lista(d["pecas"])
        self.tabela = np.array(d["tabela"], dtype=float)
        c = d["camadas"]
        self.w0 = np.array(c[0]["pesos"]); self.b0 = np.array(c[0]["vies"]).reshape(-1, 1)
        self.w1 = np.array(c[1]["pesos"]); self.b1 = np.array(c[1]["vies"]).reshape(-1, 1)
        self.medido = d.get("medido", {})
        self._np = np

    def escolher(self, erro):
        """(família, confiança)."""
        np = self._np
        idx = self.peneira.ids(texto_do_caso(erro))
        media = self.tabela[idx].mean(axis=0).reshape(-1, 1)
        oculta = 1.0 / (1.0 + np.exp(-(self.w0 @ media + self.b0)))
        z = self.w1 @ oculta + self.b1
        e = np.exp(z - z.max())
        p = (e / e.sum()).ravel()
        k = int(p.argmax())
        return self.familias[k], float(p[k])


def montar(erro, familia, nomes_conhecidos=(), achados=None, lido=None, raiz=None):
    """A família escolhida → o conserto concreto, ou None quando não dá.

    DEVOLVER None É RESPOSTA. A rede pode acertar a família e o molde
    mesmo assim não conseguir montar a edição — a mensagem não citou o
    nome, o tipo não está na tabela. Inventar alguma coisa nessa hora é
    trocar "não sei" por um conserto errado que compila.

    `achados` e `lido` são o que o AGENTE trouxe de fora do arquivo: a
    saída do `procurar` e a do `ler`. Sem eles os moldes continuam mudos
    (é o comportamento do `consertar.py`, que não tem ferramentas); com
    eles, um erro cuja resposta mora noutro arquivo passa a ter conserto.
    """
    if familia == "nome_errado":
        if _DEFINICAO.search(erro.mensagem or "") and achados and raiz:
            # CS0117/CS1061 dizem "o TIPO não tem este membro" — quem manda
            # no membro é a DECLARAÇÃO, não o arquivo que quebrou. Já o
            # `conserto_nome_errado` só enxerga nomes do próprio arquivo e
            # pode pegar um parecido de string/mentira; por isso a
            # declaração vem primeiro (e só quando o `procurar` a achou).
            return (conserto_nome_de_declaracao(erro, achados, raiz)
                    or conserto_nome_errado(erro, nomes_conhecidos))
        return (conserto_nome_errado(erro, nomes_conhecidos)
                or conserto_nome_de_declaracao(erro, achados, raiz))
    if familia == "falta_token":
        # o parêntese aberto vem antes: a mensagem dele não tem "expected"
        # e o `conserto_falta_token` devolveria None sem nem olhar. Em
        # seguida os moldes das perdas que o Python reporta como
        # `unmatched ')'` / `unterminated string literal`.
        return (conserto_parenteses_aberto(erro)
                or conserto_falta_token(erro)
                or conserto_def_grudado(erro, nomes_conhecidos)
                or conserto_nome_grudado(erro, nomes_conhecidos)
                or conserto_parenteses_sem_abre(erro)
                or conserto_aspas_sem_fechar(erro)
                or conserto_parentese_antes_dois_pontos(erro))
    if familia == "falta_using":
        return (conserto_falta_using(erro)
                or conserto_using_do_projeto(erro, achados, raiz))
    if familia == "tipo_errado":
        return (conserto_tipo_errado(erro)
                or conserto_argumento_por_irmao(erro, lido))
    if familia == "falta_new":
        return conserto_falta_new(erro)
    if familia == "indentacao":
        return conserto_indentacao(erro)
    if familia == "falta_virgula":
        # os específicos vêm PRIMEIRO: o geral é o que sobra. Deixar o
        # geral na frente fazia ele roubar os casos (`for p _ in` virava
        # `p _, in`, e `hasattr(s 'x')` ganhava vírgula no lugar errado).
        return (conserto_virgula_no_for(erro)
                or conserto_virgula_apos_self(erro)
                or conserto_virgula_no_dict(erro)
                or conserto_virgula_em_chamada_com_aspas(erro)
                or conserto_falta_virgula(erro))
    if familia == "igual_no_if":
        return conserto_igual_no_if(erro)
    if familia == "palavra_errada":
        return conserto_palavra_errada(erro, nomes_conhecidos)
    if familia == "pontuacao_dobrada":
        return conserto_pontuacao_dobrada(erro)
    # `falta_operador` NÃO TEM MOLDE, DE PROPÓSITO. Saber que falta um
    # operador é diagnóstico; saber se era `+` ou `*` é adivinhar o que a
    # pessoa quis calcular. Ver `EXPLICACAO`.
    return None
