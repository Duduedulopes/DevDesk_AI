# -*- coding: utf-8 -*-
"""ATENÇÃO × MÉDIA — o experimento que mede se atenção vale a pena aqui."""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    python programas/treinar_atencao.py 9000

RESULTADO DE 08/09/2026, para não se repetir o trabalho à toa:

                            atenção    média (saco de peças)
    conjunto exato           14,3%            22,2%
    precisão                 52,4%            64,0%
    recall                   61,5%            60,3%
    por pedidos: 1           23,8%            48,4%
                 2           18,5%            28,1%
                 3           10,8%            10,2%
                 4            3,8%             2,9%

A ATENÇÃO PERDEU. E o motivo não é a peça: é a comida.

Perda de treino 0,586 contra F1 de teste 56,6% — isso é decorar. São 546
mil parâmetros contra 26 mil parágrafos montados de uma matéria-prima de
1.400 frases-base. Mais capacidade, mesma comida: sobra capacidade para
decorar e falta dado para generalizar. É a MESMA conclusão que já tinha
saído no classificador da loja ("o gargalo é o dado, não a capacidade") e
no de intenção.

O ACHADO QUE VALEU A NOITE

Fui ver ONDE a consulta olhou quando ela errou o pedido de pagamento:

    consulta de 'apagar' → 'pag' · 'aga' · 'ame' · 'del' · 'lag'

São pedaços de "pagamento". O vocabulário é de trigramas de caractere, e
`pagamento`/`apagar` dividem `pag` e `aga`. Contando no corpus inteiro:

    pagamento 0 · login 0 · vitrine 0 · carrinho 0 · c# 0 · mvc 0
    projeto 1.260 · criar 268

Nove das palavras do pedido não existem no mundo dela. A atenção não
falhou: foi obrigada a opinar sobre palavras que nunca lhe apresentaram, e
agarrou o pedaço mais parecido que tinha.

Por isso este arquivo fica: a peça está pronta e conferida, esperando
dado. Quando as falas das partes existirem, é só rodar de novo.
"""
import collections
import json
import random
import sys
import time

import numpy as np

from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from texto.vocabulario import Vocabulario        # noqa: E402
from nucleo.atencao import conferir                # noqa: E402
from nucleo.atencao_lote import (AtencaoEmLote,     # noqa: E402
                                 conferir_contra_referencia)

SEM = 42
PASSOS = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
LOTE, TAXA, PESO_SIM = 128, 0.6, 12.0
LIGA = [", ", " e ", ", e ", ". ", ", depois ", " e também ", ", e aí "]

print("1) gradiente contra derivada numérica (versão de referência):")
for nome, rel, ab in conferir():
    print(f"   {nome:<4} relativo {rel:.1e} · absoluto {ab:.1e}")
ds, dg = conferir_contra_referencia()
print(f"2) versão em lote × referência: saída {ds:.1e} · "
      f"pior peso {max(dg.values()):.1e}")
print()

rng = random.Random(SEM)
linhas = [json.loads(l) for l in open(RAIZ / "dados" / "perguntas_dev.jsonl", encoding="utf-8") if l.strip()]
grupos = collections.defaultdict(list)
for l in linhas:
    grupos[l["base"]].append(l)
por_int = collections.defaultdict(list)
for base, ls in grupos.items():
    por_int[ls[0]["intencao"]].append(base)

bases_tr, bases_te = [], []
for inten, bases in por_int.items():
    bases = sorted(bases)
    rng.shuffle(bases)
    corte = max(1, int(len(bases) * 0.8))
    bases_tr += bases[:corte]
    bases_te += bases[corte:]

intencoes = sorted(por_int)
i_de = {n: i for i, n in enumerate(intencoes)}
V = len(intencoes)


def saco_de(bases):
    s = collections.defaultdict(list)
    for b in bases:
        for l in grupos[b]:
            s[l["intencao"]].append(l["pergunta"])
    return s


def montar(saco, quantos, r):
    nomes = [n for n in intencoes if len(saco.get(n, [])) >= 2]
    dados = []
    for _ in range(quantos):
        k = r.randint(1, 4)
        esc = r.sample(nomes, min(k, len(nomes)))
        t = r.choice(saco[esc[0]])
        for n in esc[1:]:
            t += r.choice(LIGA) + r.choice(saco[n])
        dados.append((t, set(esc)))
    return dados


treino = montar(saco_de(bases_tr), 26000, random.Random(SEM))
teste = montar(saco_de(bases_te), 3000, random.Random(SEM + 1))
vocab = Vocabulario([t for t, _ in treino], minimo=2)


def alvo(c):
    y = np.zeros(V)
    for n in c:
        y[i_de[n]] = 1.0
    return y


tr = [(vocab.indices(t), alvo(s)) for t, s in treino]
te = [(vocab.indices(t), alvo(s), len(s)) for t, s in teste]
print(f"{len(tr):,} parágrafos de treino · {len(te):,} de teste · "
      f"{len(vocab):,} peças · {V} intenções")

rede = AtencaoEmLote(len(vocab), V, dimensao=64, chave=32, semente=SEM)
n_par = (rede.E.size + rede.Wk.size + rede.Wv.size + rede.Q.size
         + rede.w.size + rede.b.size)
print(f"atenção: D=64 d=32 · {n_par:,} parâmetros\n")

t0 = time.time()
descartados = 0
r = random.Random(SEM)
for passo in range(1, PASSOS + 1):
    amostra = [tr[r.randrange(len(tr))] for _ in range(LOTE)]
    idx, masc = AtencaoEmLote.empilhar([a[0] for a in amostra])
    Yb = np.array([a[1] for a in amostra])
    taxa = TAXA if passo <= PASSOS * .5 else (TAXA * .3 if passo <= PASSOS * .8
                                              else TAXA * .1)
    perda = rede.passo(idx, masc, Yb, taxa, PESO_SIM)
    if perda != perda:                      # NaN: o lote foi descartado
        descartados = descartados + 1
    if passo % max(1, PASSOS // 8) == 0:
        print(f"  passo {passo:>6}/{PASSOS}  perda {perda:7.3f}  "
              f"lotes descartados {descartados}  ({time.time()-t0:.0f}s)")

P = []
for i in range(0, len(te), 256):
    fatia = te[i:i+256]
    ii, mm = AtencaoEmLote.empilhar([f[0] for f in fatia])
    P.append(rede.frente(ii, mm)[5])
P = np.concatenate(P)
Y = np.array([y for _, y, _ in te])
ns = [n for _, _, n in te]


def mede(lim, idx=None):
    idx = range(len(P)) if idx is None else idx
    tp = fp = fn = ex = tot = 0
    porn = collections.defaultdict(lambda: [0, 0])
    for i in idx:
        prev = set(np.where(P[i] >= lim)[0])
        real = set(np.where(Y[i] >= .5)[0])
        tp += len(prev & real); fp += len(prev - real); fn += len(real - prev)
        tot += 1
        porn[ns[i]][1] += 1
        if prev == real:
            ex += 1
            porn[ns[i]][0] += 1
    pr = tp / (tp + fp) if tp + fp else 0
    rc = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
    return f1, pr, rc, ex / tot, porn


val = range(len(P) // 3)
LIM = max((x / 100 for x in range(5, 96, 5)), key=lambda l: mede(l, val)[0])
f1, pr, rc, ex, porn = mede(LIM)
print(f"\nlimiar escolhido na validação: {LIM:.2f}")
print(f"CONJUNTO EXATO: {ex:.1%}  ·  precisão {pr:.1%} · recall {rc:.1%} · F1 {f1:.1%}")
print(f"\n{'pedidos':<10}{'ATENÇÃO':>12}{'média (antes)':>16}")
antes = {1: .484, 2: .281, 3: .102, 4: .029}
for n in sorted(porn):
    ok, tot = porn[n]
    print(f"{n:<10}{ok/tot:>11.1%}{antes.get(n, 0):>16.1%}")

P_ED = ("Crie para mim um site para meus projetos de modelagem 3D, gostaria de "
        "fazer o site em C# utilizando o MVC, e fazer uma vitrine para meus "
        "produtos com valores, vamos fazer um login para os usuários e criar "
        "uma forma de pagamento")
ii, mm = AtencaoEmLote.empilhar([vocab.indices(P_ED)])
Xf, Kf, Vf, Af, Cf, pf = rede.frente(ii, mm)
pf = pf[0]
o = np.argsort(pf)[::-1][:6]
print("\nA FRASE DO EDUARDO:")
for k in o:
    print(f"   {pf[k]:>6.1%}  {intencoes[k]}"
          + ("  ← acende" if pf[k] >= LIM else ""))

# ── o que a atenção OLHOU: é isto que a média não podia mostrar ──────
from texto.vocabulario import pedacos            # noqa: E402
pcs = [p for p in pedacos(P_ED) if p in vocab.indice]
k_top = int(o[0])
peso = Af[0][k_top]
melhores = np.argsort(peso)[::-1][:12]
print(f"\nonde a consulta de '{intencoes[k_top]}' olhou (12 peças de maior peso):")
print("   " + " · ".join(f"{pcs[i]!r}" for i in melhores if i < len(pcs)))
