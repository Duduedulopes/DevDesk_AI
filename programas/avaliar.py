# -*- coding: utf-8 -*-
"""Divisão 60/20/20, métricas honestas e o modelo que vai para produção.
    python programas/avaliar.py                 mede e grava o modelo
    python programas/avaliar.py --so-medir      mede e não grava nada
    python programas/avaliar.py --pecas         usa BPE em vez de trigramas

POR QUE ESTE PROGRAMA EXISTE, TENDO treinar_classificador.py

São duas ferramentas para duas perguntas, e as duas valem:

    treinar_classificador.py   validação cruzada em 5 dobras. Responde
                               "quanto este MÉTODO acerta?", usando todo o
                               corpus como teste ao longo das 5 rodadas.

    avaliar.py (este)          divisão fixa 60/20/20. Responde "quanto
                               ESTE modelo, o que vai rodar, acerta em
                               dados que ele nunca viu?" — e devolve as
                               métricas por intenção, a matriz de confusão
                               e o conjunto de guarda.

AS TRÊS FATIAS, E O QUE CADA UMA PODE FAZER

    treino 60%     ajusta os pesos
    avaliação 20%  decide ONDE PARAR. Olhada muitas vezes durante o treino,
                   então ela já não é imparcial no fim — quem escolhe não
                   pode julgar.
    teste 20%      medida UMA vez, no fim. É o número que vale.

O TESTE VIRA O CONJUNTO DE GUARDA, E ISSO CONSERTA UM BUG

A guarda é o que a trava anti-esquecimento usa para medir estrago quando
você corrige a rede. Para isso funcionar, ela precisa ser feita de frases
que o modelo NÃO treinou.

O guarda.json anterior saía da dobra de teste do melhor modelo da validação
cruzada — um modelo que era jogado fora. O modelo que ia para produção era
treinado no corpus INTEIRO, então aquelas 800 frases eram treino dele.
Resultado medido: acerto na guarda 99,62%, e a trava passou a recusar TODA
correção, porque qualquer uma custava mais que os 0,12% de uma frase.

Aqui o modelo entregue nunca vê o teste. A guarda volta a medir retenção
de verdade, e não memorização.

O EMBARALHAMENTO É POR BASE, E A DIFERENÇA FOI MEDIDA

O corpus tem ~16 variantes mecânicas de cada frase escrita à mão (erro de
dedo, enchimento, maiúscula), marcadas pelo campo `base`. Embaralhar por
FRASE joga "nao compila" no teste enquanto "não compila" ficou no treino:
mede-se o modelo contra o que ele já viu.

    por base   61,6% no teste
    por frase  96,9% no teste     ← +35,3 pontos de mentira

Rode com --ingenuo para ver esse número você mesmo.
"""
import argparse
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modelo.classificador import ClassificadorDeIntencao
from texto.vocabulario import Vocabulario, normalizar

RAIZ = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════════════
#  A DIVISÃO
# ══════════════════════════════════════════════════════════════════════
def carregar(caminho):
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def dividir(linhas, semente=7, fatias=(0.6, 0.2, 0.2), por_base=True):
    """Embaralha, estratifica por intenção e agrupa por base.

    As três coisas ao mesmo tempo:

      embaralhar    a ordem é sorteada, não a do arquivo
      estratificar  cada intenção é dividida separadamente, então as três
                    fatias têm as 52 na mesma proporção
      agrupar       a unidade sorteada é a BASE — as ~16 variantes de uma
                    frase caem todas do mesmo lado

    `por_base=False` desliga só o agrupamento. Serve para medir o tamanho
    do erro que ele evita, e para mais nada.
    """
    rng = random.Random(semente)
    if por_base:
        unidades = defaultdict(list)
        for l in linhas:
            unidades[l["base"]].append(l)
        grupos = list(unidades.values())
    else:
        grupos = [[l] for l in linhas]

    por_intencao = defaultdict(list)
    for g in grupos:
        por_intencao[g[0]["intencao"]].append(g)

    partes = ([], [], [])
    for grupos_da_intencao in por_intencao.values():
        rng.shuffle(grupos_da_intencao)
        n = len(grupos_da_intencao)
        c1 = int(round(n * fatias[0]))
        c2 = c1 + int(round(n * fatias[1]))
        for destino, fatia in zip(partes, (grupos_da_intencao[:c1],
                                           grupos_da_intencao[c1:c2],
                                           grupos_da_intencao[c2:])):
            for g in fatia:
                destino.extend(g)
    for p in partes:
        rng.shuffle(p)
    return partes


# ══════════════════════════════════════════════════════════════════════
#  TOKENIZAÇÃO
# ══════════════════════════════════════════════════════════════════════
class VocabularioDePecas:
    """BPE em vez de trigramas — atrás de `--pecas`, e não por padrão.

    MEDIDO, NA MESMA DIVISÃO 60/20/20:

        trigramas de caractere   61,6% no teste   4.964 peças
        peças BPE (600 fusões)   57,6% no teste     637 peças

    O motivo está escrito no próprio texto/vocabulario.py: com trigramas,
    "faturmento" divide `fat`, `atu`, `tur` com "faturamento", e o erro de
    digitação vira ruído em vez de virar palavra desconhecida.

    Este corpus é feito de erro de digitação — ~16 variantes por frase
    escrita. O BPE segmenta `compila` e `compilla` em peças completamente
    diferentes e perde o parentesco. A virtude dele (pedaço com
    significado) não é a virtude que ESTE corpus precisa.

    E TEM UM SEGUNDO MOTIVO, MAIOR: o nucleo/cerebro.py chama `pedacos()`
    direto, com trigramas fixos no código. Um modelo de peças carregaria
    sem erro nenhum e apontaria para linhas erradas da tabela — o pior
    tipo de defeito, o que não levanta exceção. Por isso o JSON agora
    grava o campo `tokenizador` e o Cerebro recusa o que não sabe ler.
    """

    nome = "pecas"

    def __init__(self, frases_de_treino, n_fusoes=600):
        from texto.pecas import Pecas
        # AS FUSÕES SÃO APRENDIDAS SÓ NO TREINO. Trigrama sai de uma regra
        # fixa e pode ser calculado sobre tudo; fusão de BPE é aprendida
        # dos dados, e aprender no corpus inteiro deixaria a lista carregar
        # informação das frases de teste.
        self.bpe = Pecas.treinar("\n".join(normalizar(f) for f in frases_de_treino),
                                 n_fusoes=n_fusoes)
        self.pecas = ["<?>"] + list(self.bpe.vocab)

    def __len__(self):
        return len(self.pecas)

    def indices(self, texto):
        return [i + 1 for i in self.bpe.codificar(normalizar(texto))] or [0]


def montar(linhas, intencoes, vocab):
    k_de = {n: i for i, n in enumerate(intencoes)}
    return [(vocab.indices(l["pergunta"]), k_de[l["intencao"]])
            for l in linhas if l["intencao"] in k_de]


# ══════════════════════════════════════════════════════════════════════
#  TREINO — quem decide onde parar é a AVALIAÇÃO
# ══════════════════════════════════════════════════════════════════════
def guardar_pesos(clf):
    return (clf.tabela.copy(),
            [(c.pesos.copy(), c.vies.copy()) for c in clf.rede.camadas])


def repor_pesos(clf, guardado):
    tabela, camadas = guardado
    clf.tabela = tabela.copy()
    for c, (p, v) in zip(clf.rede.camadas, camadas):
        c.pesos, c.vies = p.copy(), v.copy()


def treinar(ex_treino, ex_aval, intencoes, tam_vocab, a):
    """Treina e devolve (modelo no melhor ponto, curva, passo escolhido).

    PARAR NO MELHOR DA AVALIAÇÃO, e não no último passo. Medido nesta
    rede: o acerto no treino continua subindo até 99,6% enquanto o da
    avaliação empaca em 52% lá pelo passo 7.500. Treinar depois disso só
    decora — e é por isso que a avaliação existe.
    """
    clf = ClassificadorDeIntencao(tam_vocab, intencoes, dimensao=a.dimensao,
                                  ocultos=a.ocultos, semente=a.semente)
    rng = random.Random(a.semente)
    curva, melhor = [], (-1.0, None, 0)
    cada = max(1, a.passos // a.medicoes)

    print(f"    {'passo':>7} {'treino':>8} {'avaliação':>10} {'vão':>7} {'bits':>7}")
    print("    " + "─" * 44)
    for passo in range(1, a.passos + 1):
        lote = rng.sample(ex_treino, min(a.lote, len(ex_treino)))
        # decaimento em três fases: forte para sair do lugar, fraco para assentar
        if passo <= a.passos * 0.5:   t = a.taxa
        elif passo <= a.passos * 0.8: t = a.taxa * 0.3
        else:                         t = a.taxa * 0.1
        clf.passo(lote, t)

        if passo % cada == 0 or passo == a.passos:
            # Amostra do treino: medir nas 16 mil a cada parada custaria
            # mais tempo que o próprio treino, e 3 mil já dão a curva.
            amostra = (ex_treino if len(ex_treino) <= 3000
                       else rng.sample(ex_treino, 3000))
            a_tr, _, _ = clf.avaliar(amostra)
            a_av, c_av, _ = clf.avaliar(ex_aval)
            curva.append({"passo": passo, "treino": a_tr, "aval": a_av,
                          "bits": c_av / math.log(2)})
            if a_av > melhor[0]:
                melhor = (a_av, guardar_pesos(clf), passo)
            print(f"    {passo:>7} {a_tr:>8.1%} {a_av:>10.1%} "
                  f"{a_tr-a_av:>7.1%} {c_av/math.log(2):>7.2f}", flush=True)

    repor_pesos(clf, melhor[1])
    return clf, curva, melhor[2]


# ══════════════════════════════════════════════════════════════════════
#  MÉTRICAS
# ══════════════════════════════════════════════════════════════════════
def contagens(M, k):
    """VP, VN, FP, FN de UMA classe, tirados da matriz de confusão.

    M[real, previsto]. Para a classe k:

        VP  M[k,k]                 era k e disse k
        FN  o resto da LINHA k     era k e disse outra coisa
        FP  o resto da COLUNA k    era outra coisa e disse k
        VN  todo o resto           não era k e não disse k

    Com 52 classes não existe "o" verdadeiro positivo: existe um por
    intenção. E o VN é sempre enorme — por isso acurácia por classe não
    diz nada e precisão/recall dizem.
    """
    vp = int(M[k, k])
    fn = int(M[k, :].sum()) - vp
    fp = int(M[:, k].sum()) - vp
    return vp, int(M.sum()) - vp - fn - fp, fp, fn


def por_classe(M, nomes):
    saida = []
    for k, nome in enumerate(nomes):
        vp, vn, fp, fn = contagens(M, k)
        prec = vp / (vp + fp) if vp + fp else 0.0
        rec = vp / (vp + fn) if vp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        saida.append({"intencao": nome, "vp": vp, "vn": vn, "fp": fp, "fn": fn,
                      "precisao": prec, "recall": rec, "f1": f1, "suporte": vp + fn})
    return saida


def resumo(M, nomes, custo):
    """Macro, ponderada e micro dizem coisas diferentes — todas as três.

    macro      média simples entre as intenções: uma rara pesa igual a uma
               comum, então mostra se alguma classe foi abandonada.
    ponderada  média pesada pelo tamanho de cada classe: parece com a
               experiência de quem usa.
    micro      junta VP/FP/FN de todas antes de dividir. Em classificação
               de rótulo único ela É a acurácia — as três colunas iguais
               não é erro de conta.
    """
    linhas = por_classe(M, nomes)
    n = max(1, int(M.sum()))
    peso = lambda c: sum(l[c] * l["suporte"] for l in linhas) / n
    return {"n": n, "acuracia": int(np.trace(M)) / n,
            "macro_precisao": sum(l["precisao"] for l in linhas) / len(linhas),
            "macro_recall": sum(l["recall"] for l in linhas) / len(linhas),
            "macro_f1": sum(l["f1"] for l in linhas) / len(linhas),
            "pond_precisao": peso("precisao"), "pond_recall": peso("recall"),
            "pond_f1": peso("f1"),
            "bits": custo / math.log(2), "linhas": linhas}


def com_limiar(clf, exemplos, limiar):
    """O que muda quando o modelo pode se ABSTER.

    Precisão e recall contam como erro algo que, na tela, vira uma
    pergunta. Separar as duas coisas é o que diz se o assistente serve:
    erro calado é caro, pergunta não é.
    """
    certo_falando = errado_falando = certo_calado = 0
    for indices, k in exemplos:
        p = clf.prever(indices)
        esc = int(np.argmax(p))
        acertou = esc == k
        if float(p[esc, 0]) >= limiar:
            certo_falando += acertou
            errado_falando += not acertou
        else:
            certo_calado += acertou
    n = max(1, len(exemplos))
    fala = certo_falando + errado_falando
    return {"limiar": limiar, "cobertura": fala / n,
            "precisao_falando": certo_falando / max(1, fala),
            "erro_calado": errado_falando / n,
            "abstencao": (n - fala) / n,
            "topo_certo_calado": certo_calado / max(1, n - fala)}


# ══════════════════════════════════════════════════════════════════════
#  RELATÓRIO — no terminal, fora do aplicativo
# ══════════════════════════════════════════════════════════════════════
def titulo(t):
    print("\n" + "═" * 76 + f"\n  {t}\n" + "═" * 76)


def relatorio(r, curva, teto, quantas=12):
    titulo("MÉTRICAS NO TESTE — medido uma vez, em dados nunca vistos")
    print(f"\n  acurácia               {r['acuracia']:>7.1%}   ({r['n']:,} frases)")
    print(f"\n  {'':24}{'precisão':>10}{'recall':>9}{'F1':>9}")
    for rot, k in (("macro (todas iguais)", "macro"), ("ponderada (por tamanho)", "pond")):
        print(f"  {rot:<24}{r[k+'_precisao']:>9.1%}{r[k+'_recall']:>9.1%}{r[k+'_f1']:>9.1%}")
    print(f"\n  entropia cruzada       {r['bits']:>7.2f} bits/frase")
    print(f"  teto de quem chuta     {teto:>7.2f} bits   (log2 de {len(r['linhas'])} intenções)")
    print(f"  → comprime {teto/max(r['bits'],1e-9):.1f}× · economiza {teto-r['bits']:.2f} bits por frase")

    titulo("VIÉS E VARIÂNCIA")
    c = curva[-1]
    print(f"\n  VIÉS       erro no treino  {1-c['treino']:>7.1%}")
    print(f"  VARIÂNCIA  vão treino→aval {c['treino']-c['aval']:>7.1%}")
    if 1 - c["treino"] < 0.05 and c["treino"] - c["aval"] > 0.15:
        print("\n  Viés baixo, variância alta: ela decora o treino e não leva junto.")
        print("  Rede maior NÃO ajuda. O que move este número é mais frase-BASE")
        print("  distinta — variante mecânica da mesma frase não conta.")
    elif 1 - c["treino"] > 0.15:
        print("\n  Viés alto: nem no treino ela acerta. Falta capacidade ou passos.")
    else:
        print("\n  Os dois em faixa razoável.")

    titulo(f"VP / VN / FP / FN — as {quantas//2} piores e as {quantas//2} melhores")
    ls = sorted(r["linhas"], key=lambda x: x["f1"])
    cab = f"\n  {'intenção':<26}{'VP':>5}{'FN':>5}{'FP':>5}{'VN':>7}{'prec':>8}{'rec':>7}{'F1':>7}"
    print(cab); print("  " + "─" * 70)
    for l in ls[:quantas//2] + [None] + ls[-quantas//2:]:
        if l is None:
            print("  " + "·" * 70); continue
        print(f"  {l['intencao']:<26}{l['vp']:>5}{l['fn']:>5}{l['fp']:>5}{l['vn']:>7}"
              f"{l['precisao']:>8.0%}{l['recall']:>7.0%}{l['f1']:>7.0%}")
    zeradas = [l["intencao"] for l in r["linhas"] if l["vp"] == 0]
    if zeradas:
        print(f"\n  NUNCA acertam uma: {', '.join(zeradas)}")


def matriz(M, nomes, quantas=12):
    titulo(f"MATRIZ DE CONFUSÃO — as {quantas} trocas mais frequentes")
    pares = [(int(M[i, j]), nomes[i], nomes[j], M[i, j] / max(1, M[i, :].sum()))
             for i in range(len(nomes)) for j in range(len(nomes))
             if i != j and M[i, j] > 0]
    pares.sort(reverse=True)
    print(f"\n  {'era':<26}{'disse':<26}{'vezes':>7}{'da classe':>11}")
    print("  " + "─" * 70)
    for n, real, prev, frac in pares[:quantas]:
        print(f"  {real:<26}{prev:<26}{n:>7}{frac:>10.0%}")
    print(f"\n  (a matriz inteira é {len(nomes)}×{len(nomes)} e não cabe em tela —"
          f" estas são as {quantas} maiores)")


def tabela_limiares(clf, ex_teste, limiares):
    titulo("COM A ABSTENÇÃO — o que a pessoa realmente vê")
    print("\n  A acurácia conta como erro algo que na tela vira pergunta.")
    print("  Separando:\n")
    print(f"  {'limiar':>8}{'responde':>11}{'acerta falando':>17}"
          f"{'erro calado':>14}{'se abstém':>12}")
    print("  " + "─" * 64)
    saida = []
    for lim in limiares:
        a = com_limiar(clf, ex_teste, lim)
        saida.append(a)
        print(f"  {lim:>8.0%}{a['cobertura']:>11.1%}{a['precisao_falando']:>17.1%}"
              f"{a['erro_calado']:>14.1%}{a['abstencao']:>12.1%}")
    return saida


# ══════════════════════════════════════════════════════════════════════
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", default=str(RAIZ / "dados" / "perguntas_dev.jsonl"))
    p.add_argument("--saida",  default=str(RAIZ / "modelos" / "intencao.json"))
    p.add_argument("--guarda", default=str(RAIZ / "modelos" / "guarda.json"))
    p.add_argument("--passos", type=int, default=15000)
    p.add_argument("--lote", type=int, default=64)
    p.add_argument("--taxa", type=float, default=0.8)
    p.add_argument("--dimensao", type=int, default=32)
    p.add_argument("--ocultos", type=int, default=64)
    p.add_argument("--semente", type=int, default=7)
    p.add_argument("--medicoes", type=int, default=10, help="pontos na curva")
    p.add_argument("--limiar", type=float, default=0.90)
    p.add_argument("--tamanho-guarda", type=int, default=800)
    p.add_argument("--pecas", action="store_true", help="BPE em vez de trigramas")
    p.add_argument("--ingenuo", action="store_true",
                   help="embaralha por FRASE — só para ver o tamanho da inflação")
    p.add_argument("--so-medir", action="store_true", help="não grava nada")
    a = p.parse_args()

    t0 = time.time()
    linhas = carregar(a.corpus)
    intencoes = sorted({l["intencao"] for l in linhas})
    treino, aval, teste = dividir(linhas, a.semente, por_base=not a.ingenuo)

    titulo("A DIVISÃO 60 / 20 / 20")
    if a.ingenuo:
        print("\n  ⚠  MODO INGÊNUO: embaralhado por FRASE. O número vai sair")
        print("     inflado de propósito. Não anote no caderno.\n")
    bases = lambda p: len({l["base"] for l in p})
    print(f"\n  {'fatia':<12}{'frases':>9}{'bases':>8}{'%':>8}{'intenções':>11}")
    print("  " + "─" * 48)
    for nome, parte in (("treino", treino), ("avaliação", aval), ("teste", teste)):
        print(f"  {nome:<12}{len(parte):>9,}{bases(parte):>8}"
              f"{len(parte)/len(linhas):>8.1%}{len({l['intencao'] for l in parte}):>11}")
    vazam_b = len({l["base"] for l in treino} & {l["base"] for l in teste})
    vazam_f = len({l["pergunta"] for l in treino} & {l["pergunta"] for l in teste})
    print(f"\n  bases em treino E teste:   {vazam_b}" + ("  ← VAZAMENTO" if vazam_b else "  ✓"))
    print(f"  frases em treino E teste:  {vazam_f}" + ("  ← VAZAMENTO" if vazam_f else "  ✓"))

    if a.pecas:
        vocab = VocabularioDePecas([l["pergunta"] for l in treino])
    else:
        vocab = Vocabulario([l["pergunta"] for l in treino], minimo=2)
        vocab.nome = "trigramas"

    ex_tr, ex_av, ex_te = (montar(x, intencoes, vocab) for x in (treino, aval, teste))

    titulo(f"TREINO — {len(vocab):,} peças ({vocab.nome}), "
           f"{sum(len(i) for i, _ in ex_tr)/len(ex_tr):.1f} por frase")
    clf, curva, passo_escolhido = treinar(ex_tr, ex_av, intencoes, len(vocab), a)
    print(f"\n  parou no passo {passo_escolhido} — o melhor da avaliação")

    a_te, c_te, M_te = clf.avaliar(ex_te)
    r = resumo(M_te, intencoes, c_te)
    teto = math.log2(len(intencoes))
    relatorio(r, curva, teto)
    matriz(M_te, intencoes)
    limiares = tabela_limiares(clf, ex_te, (0.80, 0.90, a.limiar, 0.95, 0.99))

    if a.so_medir or a.ingenuo:
        titulo("NADA FOI GRAVADO" + (" (--so-medir)" if a.so_medir else " (modo ingênuo)"))
        print(f"\n  {time.time()-t0:.0f}s")
        return 0

    # ── gravar ────────────────────────────────────────────────────────
    d = clf.para_dicionario(vocab)
    d["limiar"] = a.limiar
    # QUAL TOKENIZADOR — o Cerebro precisa saber, senão carrega um modelo
    # de peças com a conta dos trigramas e responde ruído sem dar erro.
    d["tokenizador"] = vocab.nome
    d["medido"] = {
        "protocolo": "divisao 60/20/20 embaralhada, estratificada por intencao"
                     + (", agrupada por base" if not a.ingenuo else ", POR FRASE (ingenua)"),
        "acerto_teste": round(r["acuracia"], 4),
        "macro_f1": round(r["macro_f1"], 4),
        "bits_por_frase": round(r["bits"], 3),
        "teto_uniforme_bits": round(teto, 3),
        "acerto_treino": round(curva[-1]["treino"], 4),
        "acerto_avaliacao": round(curva[-1]["aval"], 4),
        "variancia_vao": round(curva[-1]["treino"] - curva[-1]["aval"], 4),
        "passo_escolhido": passo_escolhido,
        "n_intencoes": len(intencoes),
        "n_frases_treino": len(treino),
        "n_frases_teste": len(teste),
        "n_vocabulario": len(vocab),
        "cobertura_no_limiar": round(limiares[2]["cobertura"], 4),
        "precisao_falando": round(limiares[2]["precisao_falando"], 4),
        "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

    # A GUARDA SAI DO TESTE — a fatia que o modelo entregue nunca viu.
    rng = random.Random(a.semente + 99)
    amostra = teste[:] ; rng.shuffle(amostra)
    guarda = [{"pergunta": l["pergunta"], "intencao": l["intencao"]}
              for l in amostra[:a.tamanho_guarda]]
    with open(a.guarda, "w", encoding="utf-8") as f:
        json.dump(guarda, f, ensure_ascii=False, indent=1)

    titulo("GRAVADO")
    print(f"\n  {a.saida}")
    print(f"     {len(intencoes)} intenções · {len(vocab):,} peças ({vocab.nome}) · "
          f"limiar {a.limiar:.0%}")
    print(f"     acerto no teste: {r['acuracia']:.1%}   (o número honesto)")
    print(f"\n  {a.guarda}")
    print(f"     {len(guarda)} frases tiradas do TESTE — o modelo nunca treinou nelas,")
    print(f"     então a trava anti-esquecimento volta a medir retenção de verdade.")
    print(f"\n  {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
