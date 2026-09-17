# -*- coding: utf-8 -*-
"""Treina a política do AGENTE por autojogo, e a mede contra a sequência da regra.

    python programas/treinar_agente.py
    python programas/treinar_agente.py --so-medir   não grava nada

COMO O ESTADO É GERADO, E POR QUE ESTA FORMA É A MEDIDA QUE MANDOU

`texto_do_caso` gera 66 peças. Colando a saída inteira de `ler` e de
`procurar`, o estado vai a 498 — e o erro vira 13% do que a rede lê: o
resumo é uma média, e o conteúdo do arquivo afoga a mensagem do
compilador. Por isso a saída de cada ferramenta entra RESUMIDA
(`ler: 9 linhas`, `julgar: 2 erro(s) restante(s)`); a saída completa fica
num campo do passo, à parte, onde os moldes vão buscá-la.

O QUE O AUTOJOGO APRENDE (E O QUE NÃO)

Cada caso é um `.py` real deste projeto quebrado de um dos quinze jeitos
do `treinar_consertos`, rodado numa CÓPIA temporária contra o `ast.parse`
de verdade. A política joga com ε-greedy sobre a sequência da regra:
quase sempre a escolha de uma pessoa sensata, de vez em quando um palpite.
SÓ O QUE TERMINA APROVADO PELO JUIZ vira exemplo — rodada que estourou os
seis passos não ensina nada, porque ensinaria a repetir o que falhou.

O que a rede aprende é ESTADO → FERRAMENTA, e é só isso. O argumento
(`qual nome procurar`, `qual família tentar`) continua saindo por `==` do
que a mensagem citou — pedir palpite onde existe resposta exata é trocar
acerto por chance, a regra que governa o resto do projeto.

A MEDIÇÃO É O AGENTE, NÃO A ACURÁCIA

A prova divide as pastas como no `treinar_consertos`: treino em
modelo/nucleo/compressao/conhecimento, prova em painel/texto/acao/visao/
audio, arquivos que nunca viram o treino. E a régua não é "a rede acertou
a próxima ferramenta dela mesma" — é o juiz: a sequência terminou com o
erro sumido e nada nascendo na linha editada? A rede tem de provar que
serve contra a `PoliticaPorRegra` neste mesmo julgamento.

A EFICIÊNCIA TEM UM PISO, E O PISO É 1

Toda rodada aprovada termina no único passo que importa: o `consertar`
que o juiz aprovou. O molde monta só do que já conhece (o erro, a família,
os nomes do arquivo) — não precisa de `ler` nem de `julgar` antes, e por
isso o MÍNIMO de passos de qualquer caso resolvido é 1. Cada passo antes
do vencedor é desperdício: fosse inevitável, o piso subiria.

Daí a métrica de eficiência: `eficiência = resolvidos / total de passos`
dos casos aprovados. É a fração dos passos que eram o mínimo necessário —
a regra, que sempre começa lendo o arquivo, rende ~0,5; a rede que
aprendeu a ir direto ao `consertar` se aproxima de 1,0. E `no_minimo`
conta quantos casos fecharam no 1º passo, para ninguém se esconder na
média.

O corpus PRINCIPAL é o do juiz de PYTHON (ast.parse), então só há códigos de
sintaxe na prática — `SyntaxError`, `IndentationError` e filhos. Nele, todo
molde se monta com o erro e os nomes do próprio arquivo, e a ablação mostra
que o `ler` é decorativo (321 → 321).

AO LADO DELE, UMA SUÍTE C# EXISTE PARA O CONTRÁRIO

Os casos de `TREINO_CS`/`PROVA_CS` são cópias do projeto `Linq` de verdade,
quebradas onde a resposta NÃO está na linha do erro: renomear a propriedade
no Model (CS0117), tirar o `using` do namespace do projeto (CS0246), e pôr
o argumento errado cujo certo está na linha ao lado (CS1503). Aqui o
`procurar` acha a declaração noutro arquivo e o `ler` traz a linha irmã.

É a objeção de que `ler`/`procurar` eram cena, respondida com número: eles
entram no AUTOJOGO (só `TREINO_CS`), a rede passa a vê-los, e a prova é
`PROVA_CS` — outra propriedade, outro `using`, outra linha, nenhuma delas
vista no treino. Os exemplos C# entram repetidos (`REPETICAO_CS`) porque
são 5 casos contra 794 de Python; sem a repetição o gradiente não os vê.
"""

import argparse
import collections
import json
import random
import re
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np                                             # noqa: E402,F401
from modelo.agente import Agente, PoliticaPorRegra             # noqa: E402
from modelo.classificador import ClassificadorDeIntencao       # noqa: E402
from modelo.consertos import texto_do_caso                     # noqa: E402
from modelo.decisor_linq import Peneira                        # noqa: E402
from modelo.ferramentas import NOMES                           # noqa: E402
from provas.juiz_python import erros_de_sintaxe                # noqa: E402
from programas.consertar import (_preparar_csharp,             # noqa: E402
                                 julgar_csharp)
from programas.treinar_consertos import (PASTAS_PROVA,         # noqa: E402
                                         PASTAS_TREINO, SEM,
                                         colher)

SEM = 42
EPS = 0.2            # probabilidade de palpite no lugar da escolha da regra


class PoliticaExploradora:
    """ε-greedy sobre a sequência da regra — o palpite do autojogo.

    Quase sempre a escolha sensata da `PoliticaPorRegra`; com probabilidade
    ε, um palpite entre as cinco ferramentas. O palpite quase sempre
    desperdiça um passo ou acaba a rodada (`desistir`) — mas é ele, e não
    a regra, que ensina a rede o que NÃO repetir depois de um `ler`
    inútil. A regra sozinha dá UMA resposta por estado, e uma rede
    treinada numa resposta só não tem o que aprender.
    """

    def __init__(self, base, rnd, eps):
        self.base, self.rnd, self.eps = base, rnd, eps

    def escolher(self, estado):
        if self.rnd.random() < self.eps:
            return self.rnd.choice(NOMES)
        return self.base.escolher(estado)


class PoliticaAprendida:
    """O `PoliticaDaRede` em memória — a mesma conta, sem o JSON no meio.

    O arquivo gravado só vale se, lido de volta, produzir este mesmíssimo
    comportamento: é o que a medição abaixo confere, e é o que o
    `PoliticaDaRede` promete a quem carrega o modelo depois.
    """

    def __init__(self, rede, peneira):
        self.rede, self.peneira = rede, peneira

    def escolher(self, estado):
        return self.rede.responder(self.peneira.ids(estado.testo()))[0]


# ══════════════════════════════════════════════════════════════════════
#  A ABLAÇÃO — O EXPERIMENTO QUE DECIDE O QUE `ler` ACRESCENTA
# ══════════════════════════════════════════════════════════════════════
# É a pergunta que o histograma faz: `ler` entra SEMPRE no primeiro passo
# da regra — não é decisão, é constante. Medir de novo sem ele no catálogo
# decide: se o mesmo 321/339 sair com menos passos, o `ler` era cena; se
# cair, ele carregava o problema (e aí se mostra EM QUAIS casos caiu). As
# duas políticas abaixo são as DUAS de cima com a máscara no índice do
# `ler` — nada além disso muda.

class PoliticaPorRegraSemLer(PoliticaPorRegra):
    """A regra sem a primeira regra: sem `ler`, vai direto à decisão."""

    def escolher(self, estado):
        if (self._cita_nome_procurar(estado.erro)
                and not any(p.acao == "procurar" for p in estado.passos)):
            return "procurar"
        if self._restam_familias(estado):
            return "consertar"
        return "desistir"


class PoliticaAprendidaSemLer(PoliticaAprendida):
    """A rede em memória com o pedaço do `ler` zerado na máscara."""

    def escolher(self, estado):
        p = self.rede.prever(self.peneira.ids(estado.testo()))
        p[NOMES.index("ler")] = 0.0
        return NOMES[int(np.argmax(p))]


_NOME = re.compile(r"\b[a-z_][a-z0-9_]{0,30}\b")


def _nomes_do(texto):
    """Os identificadores do arquivo — o que um conserto de nome pode usar."""
    return list({m.group(0) for m in _NOME.finditer(texto)})


def _exemplos_de(estado):
    """Cada passo de uma rodada APROVADA vira um exemplo (estado → ferramenta).

    O estado de um passo é o texto até AQUELE passo: exatamente o que a
    política viu quando escolheu aquela ferramenta. O exemplo não revela o
    fim da rodada — mostra o caminho, e é o caminho que a rede imita.
    """
    exemplos = []
    for i, p in enumerate(estado.passos):
        partes = [texto_do_caso(estado.erro)]
        for j, q in enumerate(estado.passos[:i], 1):
            partes.append(f"passo{j} {q.acao}: {q.resumo}")
        exemplos.append((" || ".join(partes), p.acao))
    return exemplos


def _uma_rodada(caso, alvo, politica, rede_familias=None):
    """Um caso quebrado numa CÓPIA, jogado até a política decidir parar."""
    alvo.write_text(caso["quebrado"], encoding="utf-8")
    e = erros_de_sintaxe(alvo)[0]
    contexto = {
        "julgar": lambda: erros_de_sintaxe(alvo),
        "raiz": str(alvo.parent),
        "nomes": _nomes_do(caso["quebrado"]),
        # O `consertar` do AGENTE consulta o contexto, não a política. As
        # duas fontes têm de ser a mesma rede, senão a política "vê"
        # família que o consertar não acha e o agente roda em círculo.
        "rede_familias": rede_familias,
    }
    return Agente(politica).rodar(e, contexto)


def _avaliar(politica, casos, alvo, rede_familias=None):
    """`(resolvidos, passos médios, eficiência, no_mínimo, uso)` — juiz decide.

    A eficiência mede o DESPERDÍCIO, não a velocidade: a rodada aprovada
    termina no `consertar` vencedor, o mínimo de qualquer caso é 1 passo,
    e cada passo antes dele foi gasto a mais. `eficiência` é a fração dos
    passos gastos que eram o mínimo mesmo; `no_mínimo` conta os casos que
    fecharam no 1º passo. A regra sempre lê antes de consertar e rende
    ~0,5; a rede tem de se aproximar de 1,0.

    `uso` é o histograma de ferramentas de TODAS as rodadas (resolvidas e
    não). É ele que mostra quando o agente virou um loop que só conserta:
    se `ler` e `procurar` nunca aparecem, o corpus não tem o problema que
    essas ferramentas resolvem — e o empate não significa "a rede chegou
    igual", significa "a prova não testou o que diferencia".
    """
    resolvidos, passos, total, no_minimo = 0, [], 0, 0
    uso = collections.Counter()
    for c in casos:
        st = _uma_rodada(c, alvo, politica, rede_familias)
        uso.update(p.acao for p in st.passos)
        if st.resolvido:
            resolvidos += 1
            n = len(st.passos)
            passos.append(n)
            total += n
            if n == 1:
                no_minimo += 1
    media = sum(passos) / len(passos) if passos else 0.0
    eficiencia = resolvidos / total if total else 0.0
    return resolvidos, media, eficiencia, no_minimo, uso


# ══════════════════════════════════════════════════════════════════════
#  A SUÍTE C# — a objeção 3: a resposta que NÃO está na linha do erro
# ══════════════════════════════════════════════════════════════════════
# No corpus Python o `ler` é decorativo (a ablação mostrou 321 → 321): todo
# molde se monta com o erro e os nomes do próprio arquivo. Estes casos são o
# contrário, de propósito — renomear a propriedade noutro arquivo (CS0117),
# tirar o `using` do namespace do projeto (CS0246), e pôr o argumento errado
# cujo certo está na linha ao lado (CS1503). Aqui quem carrega o caso é o
# `procurar` (achou a declaração noutro arquivo) e o `ler` (trouxe a linha
# irmã) — e a ablação tem de MOSTRAR a queda.
#
# O SPLIT É COMO O DO PYTHON, e pelo mesmo motivo: renomes, usings e
# argumentos repetem a MESMA forma em linhas diferentes, e um caso que a rede
# só viu no treino não prova nada. `cs0117_modulo`, `cs0246_dtos` e
# `cs1503_tostring_data` são a prova — nenhum deles aparece no treino.
ORIGEM_CS = RAIZ.parent / "Linq"
TREINO_CS = (
    {"nome": "cs0117_valor",
     "mutacoes": [("Models/TransacaoFinanceira.cs",
                   "public decimal Valor { get; set; }",
                   "public decimal ValorBruto { get; set; }")]},
    {"nome": "cs0117_categoria",
     "mutacoes": [("Models/TransacaoFinanceira.cs",
                   "public string Categoria { get; set; } = string.Empty;",
                   "public string CategoriaTransacao { get; set; } = string.Empty;")]},
    {"nome": "cs0117_mensagem",
     "mutacoes": [("Models/LogSistema.cs",
                   "public string Mensagem { get; set; } = string.Empty;",
                   "public string MensagemLog { get; set; } = string.Empty;")]},
    {"nome": "cs0246_models",
     "mutacoes": [("Program.cs", "using LinqAvancado.Models;\n", "")]},
    {"nome": "cs1503_tostring_valor",
     "mutacoes": [("Program.cs", 'x.Valor.ToString("C")',
                   "x.Valor.ToString(x.DataHora)")]},
)
PROVA_CS = (
    {"nome": "cs0117_modulo",
     "mutacoes": [("Models/LogSistema.cs",
                   "public string Modulo { get; set; } = string.Empty;",
                   "public string ModuloSistema { get; set; } = string.Empty;")]},
    {"nome": "cs0246_dtos",
     "mutacoes": [("Program.cs", "using LinqAvancado.DTOs;\n", "")]},
    {"nome": "cs1503_tostring_data",
     "mutacoes": [("Program.cs", 'x.DataHora.ToString("dd/MM/yyyy HH:mm")',
                   "x.DataHora.ToString(x.Valor)")]},
)
CASOS_CS = TREINO_CS + PROVA_CS
# OS CASOS C# ENTRAM REPETIDOS NO TREINO. São 5 contra 794 de Python: sem a
# repetição o gradiente não os vê, e a rede continuaria tirando 1/3 na prova
# C#. Repetir não é enganar a régua — a prova é OUTRA (`PROVA_CS`), e nenhum
# exemplo de lá entra aqui.
REPETICAO_CS = 40
_COMENTARIO_CS = re.compile(r"//[^\n]*")
_STRING_CS = re.compile(r'"(?:[^"\\]|\\.)*"')


def _nomes_cs(texto):
    """Só o código: comentário e string fora.

    Sem isto, o `"valor"` de uma mensagem de `Console.WriteLine` entra como
    candidato e o molde de nome pode trocar por ele — um conserto que
    compila significando outra coisa. O molde da declaração pega esse caso
    antes (a mensagem é CS0117/CS1061), mas o fallback não pode ser armadilha.
    """
    t = _STRING_CS.sub(" ", _COMENTARIO_CS.sub(" ", texto))
    return list({m.group(0) for m in _NOME.finditer(t)})


def _prepara_caso_cs(caso, trabalho):
    """Uma cópia do projeto real quebrada de um jeito — e o erro do juiz.

    Cópia NOVA: o `dotnet build` deixa `bin/obj` e um conserto reprovado
    poderia ficar no disco. O juiz é o `julgar_csharp` de verdade, não um
    parse de mentira — é o mesmo que reprova o projeto do usuário.
    """
    destino = Path(tempfile.mkdtemp(prefix="cs-", dir=trabalho)) / "proj"
    shutil.copytree(ORIGEM_CS, destino,
                    ignore=shutil.ignore_patterns("bin", "obj", ".vs", ".git"))
    for rel, de, para in caso["mutacoes"]:
        p = destino / rel
        txt = p.read_text(encoding="utf-8")
        if txt.count(de) != 1:
            raise RuntimeError(
                f"{caso['nome']}: {de!r} aparece {txt.count(de)}x no arquivo")
        p.write_text(txt.replace(de, para, 1), encoding="utf-8")
    _preparar_csharp(destino)
    erros = julgar_csharp(destino)
    if not erros:
        return None, None, None
    e = erros[0]
    aberto = Path(e.arquivo).read_text(encoding="utf-8")
    # NOMES SÓ DO ARQUIVO QUEBRADO, como no Python: o agente não pode usar a
    # lista do projeto inteiro para adivinhar o que o `procurar`/`ler` deviam
    # ter trazido. O que não está aqui só aparece via ferramenta.
    contexto = {"julgar": lambda d=destino: julgar_csharp(d),
                "raiz": str(destino),
                "nomes": _nomes_cs(aberto),
                "rede_familias": None}
    return e, contexto, e.codigo


def _uma_rodada_cs(caso, trabalho, politica, rede_familias=None):
    """Um caso C# preparado e jogado — o `_uma_rodada` do projeto de verdade."""
    e, contexto, _codigo = _prepara_caso_cs(caso, trabalho)
    if e is None:
        return None
    contexto["rede_familias"] = rede_familias
    return Agente(politica).rodar(e, contexto)


def _avaliar_cs(politica, trabalho, rede_familias=None, casos=PROVA_CS):
    """A mesma régua da `_avaliar`, com o projeto de verdade no lugar do `.py`."""
    resolvidos, passos, total, no_minimo = 0, [], 0, 0
    uso = collections.Counter()
    por_caso = []
    for caso in casos:
        e, contexto, codigo = _prepara_caso_cs(caso, trabalho)
        if e is None:
            por_caso.append((caso["nome"], False, "sem erro", 0))
            continue
        contexto["rede_familias"] = rede_familias
        st = Agente(politica).rodar(e, contexto)
        uso.update(p.acao for p in st.passos)
        por_caso.append((caso["nome"], st.resolvido, codigo, len(st.passos)))
        if st.resolvido:
            resolvidos += 1
            k = len(st.passos)
            passos.append(k)
            total += k
            if k == 1:
                no_minimo += 1
    media = sum(passos) / len(passos) if passos else 0.0
    eficiencia = resolvidos / total if total else 0.0
    return resolvidos, media, eficiencia, no_minimo, uso, por_caso


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=60)
    ap.add_argument("--taxa", type=float, default=0.35)
    ap.add_argument("--eps", type=float, default=EPS)
    ap.add_argument("--so-medir", action="store_true")
    ap.add_argument("--modelo", default=str(RAIZ / "modelos" / "agente.json"))
    arg = ap.parse_args()

    print("colhendo as quebras de verdade do treinar_consertos…")
    treino = colher(PASTAS_TREINO)
    prova = colher(PASTAS_PROVA, por_quebra=25, semente=SEM + 1)
    print(f"  treino {len(treino):,} casos ({len(PASTAS_TREINO)} pastas)")
    print(f"  prova  {len(prova):,} casos (OUTRAS pastas, nenhuma em comum)")
    if not treino or not prova:
        print("corpus vazio — nada a treinar")
        raise SystemExit(1)

    # A BASE MAIS FORTE SE O MODELO DAS FAMÍLIAS EXISTIR. Sem ele a regra
    # só tenta a pista do código (`SyntaxError` → `falta_token`), que não
    # distingue vírgula, operador e palavra errada — e é contra a versão
    # real do programa que a rede tem de se medir, não contra uma versão
    # mais fraca.
    rede_familias = None
    p_fam = RAIZ / "modelos" / "consertos.json"
    if p_fam.exists():
        try:
            from modelo.consertos import EscolhaDeFamilia       # noqa: PLC0415
            rede_familias = EscolhaDeFamilia(p_fam)
        except Exception:                                       # noqa: BLE001
            rede_familias = None
    heuristica = PoliticaPorRegra(rede_familias)

    exemplos = []
    rnd = random.Random(SEM)
    with tempfile.TemporaryDirectory(prefix="agente-") as tmp:
        alvo = Path(tmp) / "caso.py"
        print("\nautojogo: regra + ε-greedy, só o que o juiz aprovar vira exemplo…")
        resolvidos = 0
        for n, c in enumerate(treino, 1):
            st = _uma_rodada(c, alvo, heuristica, rede_familias)
            if st.resolvido:
                resolvidos += 1
                exemplos += _exemplos_de(st)
            for _ in range(2):
                st = _uma_rodada(c, alvo, PoliticaExploradora(heuristica, rnd, arg.eps),
                                 rede_familias)
                if st.resolvido:
                    exemplos += _exemplos_de(st)
            if n % 200 == 0:
                print(f"  {n:,} casos… ({len(exemplos):,} exemplos até agora)")
        print(f"  regra sozinha aprovou {resolvidos}/{len(treino)} casos")

        # O TREINO C# ENTRA NO MESMO AUTOJOGO — é aqui que a rede vê, pela
        # primeira vez, um erro cuja resposta mora noutro arquivo, e aprende
        # que CS0117/CS0246 pedem `procurar` e CS1503 pede `consertar`. Os
        # casos de prova (`PROVA_CS`) NÃO entram: são de outra linha e de
        # outro arquivo, e só eles medem se a rede generalizou a forma.
        exemplos_cs = []
        if ORIGEM_CS.exists():
            for caso in TREINO_CS:
                for politica in (heuristica,
                                 PoliticaExploradora(heuristica, rnd, arg.eps),
                                 PoliticaExploradora(heuristica, rnd, arg.eps)):
                    st = _uma_rodada_cs(caso, tmp, politica, rede_familias)
                    if st is not None and st.resolvido:
                        exemplos_cs += _exemplos_de(st)
            exemplos += exemplos_cs * REPETICAO_CS
            print(f"  C# no autojogo: {len(TREINO_CS)} casos de treino → "
                  f"{len(exemplos_cs)} exemplos ×{REPETICAO_CS} = "
                  f"{len(exemplos_cs) * REPETICAO_CS:,}")

        if not exemplos:
            print("nenhuma sequência aprovada pelo juiz no treino — nada a aprender")
            raise SystemExit(1)
        print(f"  {len(exemplos):,} exemplos (estado → ferramenta), de rodadas aprovadas")

        peneira = Peneira([t for t, _ in exemplos])
        print(f"\n  {len(peneira):,} peças · {len(NOMES)} ferramentas")
        print("  " + " · ".join(
            f"{k} {v}" for k, v in collections.Counter(
                a for _, a in exemplos).most_common()))

        ex = [(peneira.ids(t), NOMES.index(a)) for t, a in exemplos]
        rede = ClassificadorDeIntencao(len(peneira), NOMES, dimensao=32,
                                       ocultos=48, semente=SEM)
        for epoca in range(1, arg.epocas + 1):
            rnd.shuffle(ex)
            for i in range(0, len(ex), 16):
                rede.passo(ex[i:i + 16], arg.taxa)
            if epoca % max(1, arg.epocas // 5) == 0 or epoca == 1:
                print(f"  época {epoca:>3}/{arg.epocas}  treino "
                      f"{rede.avaliar(ex)[0]:.1%}")

        # ── A PROVA QUE IMPORTA: a política eficaz contra a regra ─────
        print("\n" + "=" * 70)
        print("  O AGENTE na prova — resolvido = o juiz disse \"provado\"")
        print("=" * 70)
        r_regra, p_regra, e_regra, m_regra, uso_regra = _avaliar(
            heuristica, prova, alvo, rede_familias)
        r_rede, p_rede, e_rede, m_rede, uso_rede = _avaliar(
            PoliticaAprendida(rede, peneira), prova, alvo, rede_familias)
        n = len(prova)
        print(f"\n  {'política':24} {'resolvidos':>14} {'':>7} {'passos médios':>14}")
        print("  " + "-" * 62)
        print(f"  {'regra (linha de base)':24} {r_regra:>4}/{n} = {r_regra/n:>4.0%} "
              f"{'':>5} {p_regra:>6.2f}")
        print(f"  {'rede':24} {r_rede:>4}/{n} = {r_rede/n:>4.0%} "
              f"{'':>5} {p_rede:>6.2f}")
        print("\n  eficiência — mínimo 1 passo (o `consertar` vencedor); "
              "cada passo antes é desperdício")
        print(f"  {'política':24} {'eficiência':>12} {'':>5} {'no mínimo':>10}")
        print("  " + "-" * 54)
        print(f"  {'regra (linha de base)':24} {e_regra:>10.0%} "
              f"{'':>7} {m_regra:>4}/{r_regra}")
        print(f"  {'rede':24} {e_rede:>10.0%} "
              f"{'':>7} {m_rede:>4}/{r_rede}")
        print("\n  histograma de ferramentas — TODAS as rodadas (sempre no "
              "relatório):")
        print(f"  {'política':24} {'passos':>7}   ferramentas")
        print("  " + "-" * 62)
        for rot, uso in (("regra (linha de base)", uso_regra),
                         ("rede", uso_rede)):
            partes = " · ".join(f"{a} {uso[a]}"
                                for a in sorted(uso))
            print(f"  {rot:24} {sum(uso.values()):>7}   {partes}")

        # ── A ABLAÇÃO: `ler` fora do catálogo, nada mais muda ─────────
        # O histograma denuncia `ler` como constante (regra lê SEMPRE no
        # 1º passo — não é decisão). Tirá-lo do catálogo é o experimento
        # que decide: se continuar 321/339, o `ler` era decorativo neste
        # corpus e o agente resolve tudo no 1º passo; se cair, mostra-se
        # em quais casos ele carregava o problema.
        print("\n" + "=" * 70)
        print("  ABLAÇÃO — 'ler' fora do catálogo, nada mais muda")
        print("=" * 70)
        rs, ps, es, ms, us = _avaliar(
            PoliticaPorRegraSemLer(rede_familias), prova, alvo, rede_familias)
        rl, pl, el, ml, ul = _avaliar(
            PoliticaAprendidaSemLer(rede, peneira), prova, alvo, rede_familias)
        print(f"\n  {'política':24} {'resolvidos':>14} {'':>7} {'passos médios':>14}")
        print("  " + "-" * 62)
        print(f"  {'regra (linha de base)':24} {r_regra:>4}/{n} = {r_regra/n:>4.0%} "
              f"{'':>5} {p_regra:>6.2f}")
        print(f"  {'regra sem LER':24} {rs:>4}/{n} = {rs/n:>4.0%} "
              f"{'':>5} {ps:>6.2f}")
        print(f"  {'rede sem LER':24} {rl:>4}/{n} = {rl/n:>4.0%} "
              f"{'':>5} {pl:>6.2f}")
        print("\n  se sem o `ler` o resolvido não cai, o `ler` era decorativo "
              "neste corpus:")
        print(f"      regra {r_regra} → {rs}   rede {r_rede} → {rl}")
        if (rs, rl) == (r_regra, r_rede):
            print("  → `ler` não carrega nenhum caso destes 339; o agente "
                  "resolve tudo no consertar do 1º passo")
        # a conclusão que o histograma da os números permite — é a régua
        # do empate, não opinião
        print(f"\n  a rede pode ser removida sem perda medida.")
        cs_suite = None
        if ORIGEM_CS.exists():
            print("\n" + "=" * 70)
            print("  SUÍTE C# — a objeção 3: a resposta mora em OUTRO arquivo")
            print("=" * 70)
            print("  TREINO (a rede viu):")
            for c in TREINO_CS:
                print(f"    {c['nome']}")
            print("  PROVA (a rede NÃO viu nenhum destes):")
            for c in PROVA_CS:
                print(f"    {c['nome']}")
            with tempfile.TemporaryDirectory(prefix="csharp-") as tmpc:
                cs_regra = _avaliar_cs(heuristica, tmpc, rede_familias, PROVA_CS)
                cs_rede = _avaliar_cs(PoliticaAprendida(rede, peneira), tmpc,
                                      rede_familias, PROVA_CS)
                cs_sem = _avaliar_cs(PoliticaPorRegraSemLer(rede_familias),
                                     tmpc, rede_familias, PROVA_CS)
                cs_rede_sem = _avaliar_cs(
                    PoliticaAprendidaSemLer(rede, peneira), tmpc,
                    rede_familias, PROVA_CS)
            m = len(PROVA_CS)
            colunas = (("regra", cs_regra), ("rede", cs_rede),
                       ("regra s/ler", cs_sem), ("rede s/ler", cs_rede_sem))
            print(f"\n  {'caso':32} " + " ".join(
                f"{rot:>12}" for rot, _ in colunas))
            print("  " + "-" * 74)
            for i, (nome, _, codigo, _) in enumerate(cs_regra[5]):
                marcas = []
                for _, (r, _me, _ef, _mi, _u, por) in colunas:
                    _, ok, _c, k = por[i]
                    marcas.append(f"{'ok' if ok else 'X'} ({codigo},{k}p)")
                print(f"  {nome:32} " + " ".join(f"{x:>12}" for x in marcas))
            print(f"\n  {'política':32} {'resolvidos':>10} {'':>4} "
                  f"{'passos':>7} {'eficiência':>11}")
            print("  " + "-" * 66)
            for rot, (r, me, ef, mi, _u, _p) in colunas:
                print(f"  {rot:32} {r:>5}/{m} {'':>4} {me:>7.2f} {ef:>11.0%}")
            cs_suite = (cs_regra, cs_rede, cs_sem, cs_rede_sem)
            print("\n  aqui o `procurar` (CS0117/CS0246) e o `ler` (CS1503) "
                  "carregam o caso:")
            print(f"      regra {cs_regra[0]}/{m} → sem ler {cs_sem[0]}/{m}   "
                  f"rede {cs_rede[0]}/{m} → sem ler {cs_rede_sem[0]}/{m}")
            if cs_sem[0] < cs_regra[0]:
                print("  → ao contrário do corpus Python, o `ler` carrega caso "
                      "aqui: ele deixa de ser decorativo.")
        else:
            print(f"\n  (suíte C# pulada: não achei {ORIGEM_CS})")
        if arg.so_medir:
            print("\n--so-medir: nada gravado")
            return
        Path(arg.modelo).parent.mkdir(parents=True, exist_ok=True)
        with open(arg.modelo, "w", encoding="utf-8") as f:
            json.dump({**rede.para_dicionario(peneira),
                       "tokenizador": "peneira",
                       "medido": {
                           "agente_regra": f"{r_regra}/{n}",
                           "agente_rede": f"{r_rede}/{n}",
                           "passos_regra": f"{p_regra:.2f}",
                           "passos_rede": f"{p_rede:.2f}",
                           "eficiencia_regra": f"{e_regra:.3f}",
                           "eficiencia_rede": f"{e_rede:.3f}",
                           "no_minimo_regra": m_regra,
                           "no_minimo_rede": m_rede,
                           "uso_regra": dict(uso_regra),
                           "uso_rede": dict(uso_rede),
                           "abla_regra": f"{rs}/{n}",
                           "abla_rede": f"{rl}/{n}",
                           "abla_passos_regra": f"{ps:.2f}",
                           "abla_passos_rede": f"{pl:.2f}",
                           "abla_eficiencia_regra": f"{es:.3f}",
                           "abla_eficiencia_rede": f"{el:.3f}",
                           "abla_no_minimo_regra": ms,
                           "abla_no_minimo_rede": ml,
                           "abla_uso_regra": dict(us),
                           "abla_uso_rede": dict(ul),
                           "csharp_total": len(PROVA_CS) if cs_suite else 0,
                           "csharp_treino": len(TREINO_CS) if cs_suite else 0,
                           "csharp_repeticao": (REPETICAO_CS
                                                if cs_suite else 0),
                           "csharp_regra": (f"{cs_suite[0][0]}/{len(PROVA_CS)}"
                                            if cs_suite else None),
                           "csharp_rede": (f"{cs_suite[1][0]}/{len(PROVA_CS)}"
                                           if cs_suite else None),
                           "csharp_sem_ler_regra": (
                               f"{cs_suite[2][0]}/{len(PROVA_CS)}"
                               if cs_suite else None),
                           "csharp_sem_ler_rede": (
                               f"{cs_suite[3][0]}/{len(PROVA_CS)}"
                               if cs_suite else None),
                           "pastas_treino": list(PASTAS_TREINO),
                           "pastas_prova": list(PASTAS_PROVA),
                           "eps": arg.eps}}, f)
        print(f"\n  gravado em {arg.modelo}")


if __name__ == "__main__":
    main()