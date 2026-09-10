# -*- coding: utf-8 -*-
"""Treina o detector de linguagem por trecho de código, e grava o modelo."""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    python programas/treinar_detector.py
    python programas/treinar_detector.py --pastas "C:/Users/Samsung/Projetos_Eduardo"
    python programas/treinar_detector.py --so-medir      não grava nada

DE ONDE VEM O DADO

Do seu próprio código. Não tem corpus baixado da internet aqui: o
detector aprende o que É python olhando os seus arquivos .py, o que é C#
olhando os seus .cs. Por isso ele começa sabendo as linguagens que você
escreve, e não as que você nunca abriu.

TRÊS CORREÇÕES QUE A PRIMEIRA MEDIÇÃO OBRIGOU

1. O .html vinha com CSS e JS dentro, rotulado "html" — rótulo errado.
   Agora `juntar` corta o arquivo em regiões (ver modelo/detector.py).

2. python tinha 87 arquivos e html tinha 3. A rede aprendeu o prior:
   nunca respondia css nem html, e ainda assim marcava 85% no total,
   porque python e csharp eram 92% dos trechos. É a mesma armadilha do
   etiquetador, onde o `O` valia 75% das peças e inflava a média.

   Agora cada linguagem entra com a MESMA quantidade de trechos, e o
   número reportado é o RECALL MACRO — a média por linguagem, onde uma
   classe zerada aparece. Com as classes equilibradas o chute vale 1/N:
   é esse o piso a bater, não 50%.

3. O lado (treino/aval/teste) é escolhido UMA VEZ POR ARQUIVO, antes de
   olhar linguagem. Na primeira versão cada linguagem sorteava por conta
   própria, e o painel.html entrava três vezes — o <style> dele caía no
   treino e o <body> no teste. Mesmo arquivo dos dois lados. A
   conferência de vazamento acusou, e ela só acusou porque foi escrita
   antes de fazer falta.
"""
import argparse
import collections
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modelo.classificador import ClassificadorDeIntencao
from modelo.detector import arquivo_de, juntar, trechos_do_arquivo
from texto.vocabulario import Vocabulario

RAIZ = Path(__file__).resolve().parent.parent
MINIMO_DE_ARQUIVOS = 3        # com menos que isso não dá para dividir em três


def titulo(t):
    print("\n" + "═" * 70 + f"\n  {t}\n" + "═" * 70)


def macro(M):
    """Média do recall POR LINGUAGEM. É este o número que não mente."""
    return float(np.mean([M[i, i] / max(1, M[i].sum()) for i in range(len(M))]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pastas", nargs="*", default=[str(RAIZ.parent)],
                   help="onde procurar código (padrão: a pasta que contém o projeto)")
    p.add_argument("--saida", default=str(RAIZ / "modelos" / "detector.json"))
    p.add_argument("--so-medir", action="store_true")
    p.add_argument("--passos", type=int, default=5000)
    p.add_argument("--lote", type=int, default=64)
    p.add_argument("--taxa", type=float, default=0.6)
    p.add_argument("--dimensao", type=int, default=24)
    p.add_argument("--ocultos", type=int, default=48)
    p.add_argument("--semente", type=int, default=7)
    p.add_argument("--limiar", type=float, default=0.60,
                   help="abaixo disto o detector devolve None e o programa pergunta")
    a = p.parse_args()
    t0 = time.time()
    rng = random.Random(a.semente)

    titulo("O QUE FOI ENCONTRADO")
    por = juntar(a.pastas)
    descartadas = {l: len(v) for l, v in por.items() if len(v) < MINIMO_DE_ARQUIVOS}
    por = {l: v for l, v in por.items() if len(v) >= MINIMO_DE_ARQUIVOS}
    if not por:
        print("\n  Nenhuma linguagem com arquivos suficientes.")
        return 1
    linguagens = sorted(por)
    for l in a.pastas:
        print(f"\n  procurei em: {l}")
    if descartadas:
        print("\n  de fora, menos de "
              f"{MINIMO_DE_ARQUIVOS} arquivos (não dá para dividir em três):")
        for l, n in sorted(descartadas.items()):
            print(f"    {l:<12}{n} arquivo(s)")

    alvo = {"treino": 1400, "aval": 400, "teste": 400}   # por LINGUAGEM
    teto_por_arquivo = 120

    # ── o lado é escolhido por ARQUIVO, antes de olhar linguagem ──────
    arquivos = {}
    for l in linguagens:
        for caminho, t in por[l]:
            arquivos.setdefault(arquivo_de(caminho), []).append((l, t))
    lado, por_extensao = {}, {}
    for arq in arquivos:
        por_extensao.setdefault(arq.rsplit(".", 1)[-1].lower(), []).append(arq)
    for _, lista in sorted(por_extensao.items()):
        lista = sorted(lista)
        rng.shuffle(lista)
        n = len(lista)
        c1, c2 = max(1, int(n * 0.6)), max(2, int(n * 0.8))
        for arq in lista[:c1]:    lado[arq] = "treino"
        for arq in lista[c1:c2]:  lado[arq] = "aval"
        for arq in lista[c2:]:    lado[arq] = "teste"

    treino, aval, teste = [], [], []
    caixas = {"treino": treino, "aval": aval, "teste": teste}
    titulo("DIVISÃO POR ARQUIVO · trechos equilibrados por linguagem")
    print(f"\n  {'linguagem':<12}{'arq tr':>7}{'av':>4}{'te':>4}"
          f"{'trechos tr':>12}{'av':>6}{'te':>6}")
    for l in linguagens:
        conta = {}
        for nome in ("treino", "aval", "teste"):
            arqs = [(c, t) for c, t in por[l] if lado[arquivo_de(c)] == nome]
            q = min(teto_por_arquivo,
                    max(6, -(-alvo[nome] // max(1, len(arqs)))))
            colhidos = [(tr, l, arquivo_de(c))
                        for c, t in arqs for tr in trechos_do_arquivo(t, rng, q)]
            rng.shuffle(colhidos)
            colhidos = colhidos[:alvo[nome]]
            caixas[nome].extend(colhidos)
            conta[nome] = (len(colhidos), len(arqs))
        print(f"  {l:<12}{conta['treino'][1]:>7}{conta['aval'][1]:>4}"
              f"{conta['teste'][1]:>4}{conta['treino'][0]:>12}"
              f"{conta['aval'][0]:>6}{conta['teste'][0]:>6}")

    print(f"\n  trechos: treino {len(treino):,} · aval {len(aval):,} · teste {len(teste):,}")
    vaza = {c for _, _, c in treino} & {c for _, _, c in teste}
    print(f"  arquivos em treino E teste: {len(vaza)}   "
          + ("<- VAZAMENTO, não confie no número" if vaza else "ok"))
    print(f"  chute com classes equilibradas: {1/len(linguagens):.1%}")

    vocab = Vocabulario([t for t, _, _ in treino], minimo=3)
    vocab.nome = "trigramas"
    k_de = {l: i for i, l in enumerate(linguagens)}
    montar = lambda p: [(vocab.indices(t), k_de[l]) for t, l, _ in p]
    ex_tr, ex_av, ex_te = montar(treino), montar(aval), montar(teste)
    print(f"  vocabulário (só do treino): {len(vocab):,} peças")

    clf = ClassificadorDeIntencao(len(vocab), linguagens, dimensao=a.dimensao,
                                  ocultos=a.ocultos, semente=a.semente)
    titulo(f"TREINO — {clf.n_parametros:,} parâmetros")
    print(f"\n  {'passo':>7}{'treino':>9}{'aval':>8}{'macro':>8}{'bits':>8}")
    print("  " + "─" * 40)
    melhor = (-1.0, None, 0)
    for passo in range(1, a.passos + 1):
        if passo <= a.passos * 0.5:   t = a.taxa
        elif passo <= a.passos * 0.8: t = a.taxa * 0.3
        else:                         t = a.taxa * 0.1
        clf.passo(rng.sample(ex_tr, min(a.lote, len(ex_tr))), t)
        if passo % max(1, a.passos // 10) == 0:
            a_tr, _, _ = clf.avaliar(rng.sample(ex_tr, min(1500, len(ex_tr))))
            a_av, c_av, M_av = clf.avaliar(ex_av)
            m_av = macro(M_av)
            print(f"  {passo:>7}{a_tr:>9.1%}{a_av:>8.1%}{m_av:>8.1%}"
                  f"{c_av/math.log(2):>8.2f}", flush=True)
            # PARA NO MELHOR MACRO, não no melhor total: senão o critério
            # de parada premia justamente quem abandona a classe pequena.
            if m_av > melhor[0]:
                melhor = (m_av, (clf.tabela.copy(),
                                 [(c.pesos.copy(), c.vies.copy())
                                  for c in clf.rede.camadas]), passo)
    clf.tabela = melhor[1][0].copy()
    for c, (pe, vi) in zip(clf.rede.camadas, melhor[1][1]):
        c.pesos, c.vies = pe.copy(), vi.copy()

    a_te, c_te, M = clf.avaliar(ex_te)
    titulo("NO TESTE — trechos de arquivos que a rede nunca abriu")
    print(f"\n  parou no passo {melhor[2]}, o melhor macro da avaliação\n")
    print(f"  recall macro (média por linguagem): {macro(M):.1%}")
    print(f"  acerto no total                   : {a_te:.1%}")
    print(f"  chute                             : {1/len(linguagens):.1%}")
    print(f"  bits por trecho                   : {c_te/math.log(2):.2f}  "
          f"(teto do chute: {math.log2(len(linguagens)):.2f})")

    print(f"\n  {'era':<12}" + "".join(f"{l[:9]:>11}" for l in linguagens)
          + f"{'recall':>9}{'precisão':>10}")
    for i, l in enumerate(linguagens):
        tot, col = M[i].sum(), M[:, i].sum()
        print(f"  {l:<12}"
              + "".join(f"{int(M[i,j]):>11}" for j in range(len(linguagens)))
              + f"{M[i,i]/max(1,tot):>8.0%}{M[i,i]/max(1,col):>10.0%}")

    # ── o limiar: quanto ela fala, e quanto acerta quando fala ────────
    titulo("O LIMIAR — quando vale perguntar em vez de chutar")
    print(f"\n  {'limiar':>8}{'responde':>10}{'acerta falando':>16}{'erro calado':>13}")
    print("  " + "─" * 47)
    for limiar in (0.0, 0.40, 0.60, 0.80, 0.90, 0.95):
        falou = acertou = 0
        for (idx, k) in ex_te:
            pr = clf.prever(idx).ravel()
            j = int(np.argmax(pr))
            if float(pr[j]) >= limiar:
                falou += 1
                acertou += (j == k)
        n = len(ex_te)
        print(f"  {limiar:>8.2f}{falou/n:>10.1%}"
              f"{acertou/max(1,falou):>16.1%}{(falou-acertou)/n:>13.1%}")

    # ── onde ela erra, e de qual arquivo ──────────────────────────────
    titulo("DIAGNÓSTICO — os erros têm endereço?")
    erros = collections.Counter()
    for (idx, k), (_, l, arq) in zip(ex_te, teste):
        j = int(np.argmax(clf.prever(idx).ravel()))
        if j != k:
            erros[(l, linguagens[j], Path(arq).name)] += 1
    print(f"\n  {'era':<12}{'disse':<13}{'arquivo':<34}{'vezes':>6}")
    for (era, disse, arq), n in erros.most_common(10):
        print(f"  {era:<12}{disse:<13}{arq[:33]:<34}{n:>6}")
    if not erros:
        print("\n  nenhum")

    print("\n  na prática — trechos escritos na mão, que ela nunca viu:\n")
    provas = [
        ("public class Conta {\n    private double saldo;\n"
         "    public void Depositar(double v) { saldo += v; }\n}", "csharp"),
        ("def somar(a, b):\n    total = a + b\n    return total", "python"),
        (".botao {\n  background: #7c8cff;\n  border-radius: 8px;\n}", "css"),
        ("<div class=\"caixa\">\n  <h1>Ola</h1>\n  <p>texto</p>\n</div>", "html"),
        ("using System.Linq;\nvar grandes = numeros.Where(n => n > 10).ToList();", "csharp"),
        ("const botao = document.querySelector('#enviar');\n"
         "botao.addEventListener('click', () => {\n  console.log('clicou');\n});", "javascript"),
        ("body {\n  margin: 0;\n  font-family: sans-serif;\n  background: #101018;\n}", "css"),
        ("<ul class=\"menu\">\n  <li><a href=\"/loja\">Loja</a></li>\n"
         "  <li><a href=\"/carrinho\">Carrinho</a></li>\n</ul>", "html"),
    ]
    certos = 0
    for t, esperado in provas:
        pr = clf.prever(vocab.indices(t)).ravel()
        k = int(np.argmax(pr))
        ok = linguagens[k] == esperado and float(pr[k]) >= a.limiar
        certos += ok
        marca = "ok   " if ok else ("baixo" if float(pr[k]) < a.limiar else "ERROU")
        print(f"    {marca} {linguagens[k]:<11}{pr[k]:>5.0%}   "
              f"(era {esperado:<11}) {t.splitlines()[0][:36]!r}")
    print(f"\n    {certos}/{len(provas)} — contando abstenção como erro")

    if a.so_medir:
        titulo("NADA FOI GRAVADO (--so-medir)")
        print(f"\n  {time.time()-t0:.0f}s")
        return 0

    d = clf.para_dicionario(vocab)
    d["limiar"] = a.limiar
    d["tokenizador"] = vocab.nome
    d["medido"] = {
        "protocolo": "divisão por ARQUIVO (o lado é escolhido antes de olhar "
                     "linguagem), trechos de 3 a 15 linhas, classes equilibradas",
        "recall_macro_teste": round(macro(M), 4),
        "acerto_teste": round(float(a_te), 4),
        "chute": round(1 / len(linguagens), 4),
        "bits_por_trecho": round(c_te / math.log(2), 3),
        "teto_uniforme_bits": round(math.log2(len(linguagens)), 3),
        "passo_escolhido": melhor[2],
        "criterio_de_parada": "melhor recall macro na avaliação",
        "linguagens": linguagens,
        "recall_por_linguagem": {l: round(float(M[i, i] / max(1, M[i].sum())), 4)
                                 for i, l in enumerate(linguagens)},
        "n_trechos_treino": len(treino),
        "n_trechos_teste": len(teste),
        "n_arquivos": len(arquivos),
        "n_vocabulario": len(vocab),
        "vazamento_treino_teste": len(vaza),
        "pastas": [str(x) for x in a.pastas],
        "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    titulo("GRAVADO")
    print(f"\n  {a.saida}")
    print(f"     {len(linguagens)} linguagens · {len(vocab):,} peças · "
          f"limiar {a.limiar}")
    print(f"     recall macro {macro(M):.1%} · {time.time()-t0:.0f}s\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
