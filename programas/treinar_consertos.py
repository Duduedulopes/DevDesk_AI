# -*- coding: utf-8 -*-
"""Treina a rede que escolhe a FAMÍLIA de conserto, e a mede honestamente.

    python programas/treinar_consertos.py
    python programas/treinar_consertos.py --so-medir     não grava nada

DE ONDE VEM O CORPUS

Não de moldes meus. Eu pego os `.py` REAIS deste projeto, quebro cada um
de quinze jeitos que gente comete, e guardo o que o `ast.parse` de
verdade devolveu, junto com a família que EU SEI ser a certa — porque fui
eu que quebrei.

A única coisa inventada aqui é a quebra. A mensagem de erro é do Python.

A PROVA É EM ARQUIVOS QUE NÃO ENTRARAM NO CORPUS

Treino em `modelo/` e `nucleo/`; meço em `painel/`, `texto/` e `acao/`.
Arquivos diferentes, escritos em momentos diferentes, com vocabulário
diferente.

E ISSO NÃO É PRECIOSISMO — é a lição mais cara deste projeto. A rede das
consultas LINQ media 98,7% "em bases que nunca viu" e acertava 2 de 12 nos
enunciados reais do arquivo do Eduardo, porque o corpus e a prova saíam do
MESMO gerador. Dividir por arquivo é o mínimo para o número querer dizer
alguma coisa.

O QUE ELA PRECISA GANHAR

A linha de base é o `familia_pela_pista`: olhar só o código do erro. Em
`SyntaxError` puro a pista não distingue nada — e 53% das quebras de
Python caem aí. É contra esse número que a rede tem de provar que serve.
"""
import argparse
import collections
import json
import random
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import numpy as np                                             # noqa: E402
from modelo.classificador import ClassificadorDeIntencao       # noqa: E402
from modelo.consertos import (FAMILIAS, familia_pela_pista,    # noqa: E402
                              montar, texto_do_caso)
from modelo.decisor_linq import Peneira                        # noqa: E402
from provas.juiz_python import compila, erros_de_sintaxe       # noqa: E402

SEM = 42
PASTAS_TREINO = ("modelo", "nucleo", "compressao", "conhecimento")
PASTAS_PROVA = ("painel", "texto", "acao", "visao", "audio")


# ══════════════════════════════════════════════════════════════════════
#  AS QUINZE QUEBRAS — cada uma com a família que ela CAUSA
# ══════════════════════════════════════════════════════════════════════
def _virgula_arg(l):
    m = re.search(r"\(\s*([a-z_]\w*)\s*,\s*", l)
    return l[:m.end(1)] + " " + l[m.end():] if m else None


def _virgula_lista(l):
    m = re.search(r"\[\s*([^\[\],]{1,12}),\s", l)
    return l[:m.end(1)] + " " + l[m.end():] if m else None


def _virgula_dict(l):
    m = re.search(r'("[^"]{1,14}":\s*[^,{}]{1,14}),\s', l)
    return l[:m.end(1)] + " " + l[m.end():] if m else None


def _igual_no_if(l):
    m = re.search(r"\b(if|elif|while)\s+([\w.]+)\s*==\s*", l)
    return l[:m.start()] + l[m.start():m.end()].replace("==", "=", 1) + l[m.end():] \
        if m else None


def _sem_dois_pontos(l):
    s = l.rstrip()
    return s[:-1] if s.endswith(":") and re.match(
        r"\s*(def|if|for|while|class|with|try|else|elif)\b", l) else None


def _sem_fecha(l):
    return l.replace("))", ")", 1) if "))" in l else None


def _sem_abre(l):
    m = re.search(r"(\w)\(", l)
    return l[:m.end(1)] + l[m.end():] if m else None


def _aspas(l):
    m = re.search(r'"([^"]{2,20})"', l)
    return l[:m.end(1)] + l[m.end():] if m else None


def _indent_mais(l):
    return "    " + l if l.startswith("    ") and l.strip() else None


def _indent_menos(l):
    return l[4:] if l.startswith("        ") and l.strip() else None


def _def_sem_par(l):
    m = re.match(r"(\s*def \w+)\(", l)
    return m.group(1) + l[m.end():] if m else None


def _palavra(l):
    for p in ("return", "elif", "import", "while", "class", "except"):
        m = re.match(rf"(\s*){p}\b", l)
        if m:
            return m.group(1) + p[:-2] + p[-1] + l[m.end():]
    return None


def _ponto_dobrado(l):
    m = re.search(r"(\w)\.(\w)", l)
    return l[:m.end(1)] + ".." + l[m.start(2):] if m else None


def _sem_operador(l):
    m = re.search(r"(\w) ([+\-*/]) (\w)", l)
    return l[:m.end(1)] + " " + l[m.start(3):] if m else None


QUEBRAS = [
    (_virgula_arg, "falta_virgula"), (_virgula_lista, "falta_virgula"),
    (_virgula_dict, "falta_virgula"), (_igual_no_if, "igual_no_if"),
    (_sem_dois_pontos, "falta_token"), (_sem_fecha, "falta_token"),
    (_sem_abre, "falta_token"), (_aspas, "falta_token"),
    (_indent_mais, "indentacao"), (_indent_menos, "indentacao"),
    (_def_sem_par, "falta_token"), (_palavra, "palavra_errada"),
    (_ponto_dobrado, "pontuacao_dobrada"), (_sem_operador, "falta_operador"),
]


def colher(pastas, por_quebra=60, semente=SEM):
    """Quebra os arquivos reais e colhe (texto do caso, família, erro)."""
    fontes = sorted(p for d in pastas for p in (RAIZ / d).glob("*.py")
                    if p.stat().st_size > 400)
    rnd = random.Random(semente)
    casos = []
    with tempfile.TemporaryDirectory(prefix="corpus-") as tmp:
        alvo = Path(tmp) / "caso.py"
        for quebrar, familia in QUEBRAS:
            feitos = 0
            ordem = list(fontes)
            rnd.shuffle(ordem)
            for fonte in ordem:
                if feitos >= por_quebra:
                    break
                linhas = fonte.read_text(encoding="utf-8").splitlines()
                idx = [i for i in range(len(linhas)) if quebrar(linhas[i])]
                rnd.shuffle(idx)
                for i in idx[:6]:
                    if feitos >= por_quebra:
                        break
                    ls = list(linhas)
                    ls[i] = quebrar(linhas[i])
                    alvo.write_text("\n".join(ls) + "\n", encoding="utf-8")
                    erros = erros_de_sintaxe(alvo)
                    if not erros:
                        continue      # quebrei e continuou válido: não serve
                    feitos += 1
                    e = erros[0]
                    # o caminho do arquivo é temporário — o que importa é o
                    # TEXTO, e o texto é o do arquivo real
                    casos.append({"texto": texto_do_caso(e), "familia": familia,
                                  "codigo": e.codigo, "mensagem": e.mensagem,
                                  "linha_codigo": e.texto, "linha_n": e.linha,
                                  "quebrado": "\n".join(ls) + "\n",
                                  "certo": linhas[i], "fonte": fonte.name})
    return casos


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=60)
    ap.add_argument("--taxa", type=float, default=0.35)
    ap.add_argument("--so-medir", action="store_true")
    ap.add_argument("--modelo", default=str(RAIZ / "modelos" / "consertos.json"))
    arg = ap.parse_args()

    print("colhendo o corpus quebrando arquivos de verdade…")
    treino = colher(PASTAS_TREINO)
    prova = colher(PASTAS_PROVA, por_quebra=25, semente=SEM + 1)
    print(f"  treino {len(treino):,} casos ({len(PASTAS_TREINO)} pastas)")
    print(f"  prova  {len(prova):,} casos (OUTRAS pastas, nenhuma em comum)\n")
    if not treino or not prova:
        print("corpus vazio — nada a treinar")
        raise SystemExit(1)

    peneira = Peneira([c["texto"] for c in treino])
    familias = [f for f in FAMILIAS if f != "nao_sei"]
    print(f"  {len(peneira):,} peças · {len(familias)} famílias")
    conta = collections.Counter(c["familia"] for c in treino)
    print("  " + " · ".join(f"{k} {v}" for k, v in conta.most_common()) + "\n")

    def preparar(casos):
        return [(peneira.ids(c["texto"]), familias.index(c["familia"]))
                for c in casos if c["familia"] in familias]

    ex_tr, ex_te = preparar(treino), preparar(prova)
    rede = ClassificadorDeIntencao(len(peneira), familias, dimensao=32,
                                   ocultos=48, semente=SEM)
    rnd = random.Random(SEM)
    for ep in range(1, arg.epocas + 1):
        rnd.shuffle(ex_tr)
        for i in range(0, len(ex_tr), 16):
            rede.passo(ex_tr[i:i + 16], arg.taxa)
        if ep % max(1, arg.epocas // 5) == 0 or ep == 1:
            a_tr = rede.avaliar(ex_tr)[0]
            a_te = rede.avaliar(ex_te)[0]
            print(f"  época {ep:>3}/{arg.epocas}  treino {a_tr:.1%}  prova {a_te:.1%}")

    # ── A PROVA QUE IMPORTA: a rede contra a pista, e o conserto no juiz ──
    print("\n" + "=" * 74)
    print("  A FAMÍLIA — a rede contra olhar só o código do erro")
    print("=" * 74)
    acerto_rede = acerto_pista = 0
    por_fam = collections.defaultdict(lambda: [0, 0, 0])
    for c in prova:
        if c["familia"] not in familias:
            continue
        fam_rede = rede.responder(peneira.ids(c["texto"]))[0]

        class _E:  # o `familia_pela_pista` só olha `.codigo`
            codigo = c["codigo"]
        fam_pista = familia_pela_pista(_E()) or "nao_sei"
        certo = c["familia"]
        por_fam[certo][0] += 1
        por_fam[certo][1] += fam_rede == certo
        por_fam[certo][2] += fam_pista == certo
        acerto_rede += fam_rede == certo
        acerto_pista += fam_pista == certo
    n = sum(v[0] for v in por_fam.values())
    print(f"\n  {'família':20} {'casos':>6} {'a rede':>9} {'a pista':>9}")
    print("  " + "-" * 48)
    for f in familias:
        if f not in por_fam:
            continue
        t, r, p = por_fam[f]
        print(f"  {f:20} {t:>6} {r/t:>8.0%} {p/t:>9.0%}")
    print("  " + "-" * 48)
    print(f"  {'TOTAL':20} {n:>6} {acerto_rede/n:>8.0%} {acerto_pista/n:>9.0%}")

    # ── e o que interessa de verdade: o juiz aprovou o conserto? ──────
    print("\n" + "=" * 74)
    print("  O CONSERTO — julgado pelo `ast.parse`, não pela minha opinião")
    print("=" * 74)
    # O JUIZ É O ARQUIVO INTEIRO, e a primeira versão desta prova errava
    # exatamente aqui: eu escrevia a LINHA SOLTA num arquivo e mandava
    # parsear. Uma linha indentada sozinha nunca é Python válido, então
    # quase tudo dava "errado" — e o número que saiu (4%) media o meu
    # harness, não o conserto.
    placar = collections.Counter()
    with tempfile.TemporaryDirectory(prefix="prova-") as tmp:
        alvo = Path(tmp) / "caso.py"
        for c in prova:
            if c["familia"] not in familias:
                continue
            for quem, fam in (("rede", rede.responder(peneira.ids(c["texto"]))[0]),
                              ("pista", familia_pela_pista(
                                  type("E", (), {"codigo": c["codigo"]})()) or "")):
                alvo.write_text(c["quebrado"], encoding="utf-8")

                class _Er:
                    arquivo = str(alvo)
                    linha, coluna = c["linha_n"], 0
                    codigo, mensagem = c["codigo"], c["mensagem"]
                    texto = c["linha_codigo"]
                conserto = montar(_Er(), fam) if fam else None
                if conserto is None:
                    placar[f"{quem}|sem molde"] += 1
                    continue
                conserto.aplicar()
                voltou = compila(alvo)
                igual = conserto.depois.strip() == c["certo"].strip()
                # DUAS MEDIDAS DIFERENTES, e as duas importam:
                #   voltou  → o arquivo é Python válido de novo (o juiz)
                #   igual   → é exatamente a linha que estava lá antes
                # A segunda é mais dura: existe conserto que faz o arquivo
                # parsear sem ser o que a pessoa tinha escrito.
                placar[f"{quem}|valido"] += voltou
                placar[f"{quem}|igual"] += igual
                placar[f"{quem}|{'ok' if voltou else 'nao resolveu'}"] += 1
    print(f"  {'':6} {'volta a parsear':>18} {'igual ao original':>20} "
          f"{'sem molde':>11}")
    for quem in ("pista", "rede"):
        tot = placar[f"{quem}|ok"] + placar[f"{quem}|nao resolveu"] + \
            placar[f"{quem}|sem molde"]
        v, i, s = (placar[f"{quem}|valido"], placar[f"{quem}|igual"],
                   placar[f"{quem}|sem molde"])
        print(f"  {quem:6} {v:>6}/{tot} = {v/max(1,tot):>4.0%}   "
              f"{i:>7}/{tot} = {i/max(1,tot):>4.0%}   {s:>10}")

    if arg.so_medir:
        print("\n--so-medir: nada gravado")
        return
    Path(arg.modelo).parent.mkdir(parents=True, exist_ok=True)
    with open(arg.modelo, "w", encoding="utf-8") as f:
        json.dump({**rede.para_dicionario(peneira),
                   # O TOKENIZADOR FICA ESCRITO NO ARQUIVO. É a trava que o
                   # `Cerebro` já tem e o motivo dela: um modelo lido com
                   # outro tokenizador aponta para as linhas erradas da
                   # tabela e responde ruído SEM LEVANTAR EXCEÇÃO. Este
                   # aqui é `peneira` (palavra + bigrama + trigrama), e
                   # não o `pedacos()` do cérebro.
                   "tokenizador": "peneira",
                   "medido": {"familia_rede": f"{acerto_rede}/{n}",
                              "familia_pista": f"{acerto_pista}/{n}",
                              "pastas_treino": list(PASTAS_TREINO),
                              "pastas_prova": list(PASTAS_PROVA)}}, f)
    print(f"\n  gravado em {arg.modelo}")


if __name__ == "__main__":
    main()
