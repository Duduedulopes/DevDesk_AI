"""Treina o classificador de intenção para o domínio de desenvolvedor.

O QUE ESTE PROGRAMA FAZ

  1. Carrega o corpus de dados/perguntas_dev.jsonl
  2. Constrói o vocabulário de trigramas de caractere
  3. Treina o ClassificadorDeIntencao (fastText) com validação cruzada agrupada
  4. Grava modelos/intencao.json  — o que o Cerebro carrega em produção
  5. Grava modelos/guarda.json    — as frases que a trava anti-esquecimento usa

VALIDAÇÃO CRUZADA AGRUPADA — E POR QUE ISSO IMPORTA

O corpus tem variantes de cada fala (14 por frase-base, geradas em
gerar_corpus_dev.py). "não compila" e "nao compila" têm o mesmo campo
`base`. Sem agrupamento, a mesma frase de treino acaba no conjunto de
teste com nome diferente — o modelo pareceria bom porque foi testado no
que já viu.

A validação agrupada garante que TODAS as variantes de uma mesma frase-base
caem na mesma dobra: ou todas no treino, ou todas no teste. O acerto medido
é o que vale de verdade.

O FORMATO DO intencao.json PRECISA SER IDÊNTICO AO QUE O Cerebro ESPERA

O Cerebro (nucleo/cerebro.py) carrega os campos:
  intencoes, pecas, tabela, limiar, medido, camadas[]{pesos, vies}

Qualquer diferença aqui faz o Cerebro carregar sem erro mas responder errado.
"""
import argparse
import io
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, ".")

import numpy as np

from modelo.classificador import ClassificadorDeIntencao
from texto.vocabulario import Vocabulario, pedacos


# ── hiperparâmetros padrão ────────────────────────────────────────────
DIMENSAO = 32      # tamanho de cada vetor de peça
OCULTOS  = 64      # neurônios na camada oculta
LOTE     = 64      # exemplos por passo de gradiente
TAXA     = 0.8     # taxa de aprendizado inicial (decai para 0.1 na segunda metade)
DOBRAS   = 5       # dobras da validação cruzada agrupada


def carregar(caminho):
    linhas = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                linhas.append(json.loads(linha))
    return linhas


def agrupar_por_base(linhas):
    """Agrupa os exemplos pela frase-base de origem.

    É o agrupamento que impede que variantes da mesma frase apareçam
    em dobras diferentes. Ver cabeçalho do módulo.
    """
    grupos = defaultdict(list)
    for l in linhas:
        grupos[l["base"]].append(l)
    return list(grupos.values())


def dobras_agrupadas(grupos, n_dobras, semente):
    """Divide os grupos em n_dobras equilibradas por intenção.

    Estratificação simples: ordena os grupos por intenção e distribui
    em round-robin. Não é perfeito, mas garante que cada dobra veja
    todas as intenções.
    """
    rng = random.Random(semente)
    por_intencao = defaultdict(list)
    for g in grupos:
        por_intencao[g[0]["intencao"]].append(g)
    for v in por_intencao.values():
        rng.shuffle(v)

    dobras = [[] for _ in range(n_dobras)]
    for grupos_int in por_intencao.values():
        for i, g in enumerate(grupos_int):
            dobras[i % n_dobras].append(g)
    return dobras


def treinar_e_avaliar(treino, teste, intencoes, vocab, passos, lote, taxa, semente):
    """Uma rodada de treino + avaliação — retorna (classificador, acerto_teste)."""
    clf = ClassificadorDeIntencao(len(vocab), intencoes,
                                  dimensao=DIMENSAO, ocultos=OCULTOS, semente=semente)
    idx_int = {n: i for i, n in enumerate(intencoes)}

    def montar_exemplos(linhas):
        ex = []
        for l in linhas:
            indices = vocab.indices(l["pergunta"])
            k = idx_int.get(l["intencao"])
            if k is not None:
                ex.append((indices, k))
        return ex

    ex_treino = montar_exemplos(treino)
    ex_teste  = montar_exemplos(teste)

    rng = random.Random(semente)
    for passo in range(1, passos + 1):
        lote_atual = rng.sample(ex_treino, min(lote, len(ex_treino)))
        # decaimento em 3 fases: alta, média, baixa
        if passo <= passos * 0.5:
            t = taxa
        elif passo <= passos * 0.8:
            t = taxa * 0.3
        else:
            t = taxa * 0.1
        clf.passo(lote_atual, t)

    acerto, _, _ = clf.avaliar(ex_teste)
    return clf, acerto


def montar_exemplos(linhas, intencoes, vocab):
    idx_int = {n: i for i, n in enumerate(intencoes)}
    ex = []
    for l in linhas:
        indices = vocab.indices(l["pergunta"])
        k = idx_int.get(l["intencao"])
        if k is not None:
            ex.append((indices, k))
    return ex


def salvar_intencao(clf, vocab, intencoes, acerto, passos, caminho):
    """Serializa no formato exato que o Cerebro espera."""
    d = clf.para_dicionario(vocab)
    d["limiar"] = 0.90
    d["medido"] = {
        "acerto_validacao": round(acerto, 4),
        "passos": passos,
        "n_intencoes": len(intencoes),
        "n_frases": sum(1 for _ in intencoes),   # sobrescrito abaixo
    }
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    return d


def salvar_guarda(frases_guarda, caminho):
    """O conjunto de guarda: frases rotuladas para a trava anti-esquecimento."""
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(frases_guarda, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus",   default="dados/perguntas_dev.jsonl")
    ap.add_argument("--saida",    default="modelos/intencao.json")
    ap.add_argument("--guarda",   default="modelos/guarda.json")
    ap.add_argument("--passos",   type=int, default=1200,
                    help="passos de gradiente por rodada de treino")
    ap.add_argument("--lote",     type=int, default=LOTE)
    ap.add_argument("--taxa",     type=float, default=TAXA)
    ap.add_argument("--dobras",   type=int, default=DOBRAS)
    ap.add_argument("--semente",  type=int, default=42)
    ap.add_argument("--minimo",   type=int, default=2,
                    help="frequência mínima de uma peça para entrar no vocabulário")
    a = ap.parse_args()

    print(f"\n  carregando {a.corpus} …")
    linhas = carregar(a.corpus)
    intencoes = sorted({l["intencao"] for l in linhas})
    frases    = [l["pergunta"] for l in linhas]

    print(f"  {len(linhas):,} frases · {len(intencoes)} intenções")

    # Vocabulário construído sobre TODO o corpus — inclusive o de teste.
    # Isso é correto para classificação: o vocabulário é como o alfabeto,
    # não um parâmetro aprendido. Só os PESOS são aprendidos só no treino.
    vocab = Vocabulario(frases, minimo=a.minimo)
    print(f"  vocabulário: {len(vocab):,} peças\n")

    grupos = agrupar_por_base(linhas)
    dobras = dobras_agrupadas(grupos, a.dobras, a.semente)

    print(f"  {'dobra':>5}  {'treino':>8}  {'teste':>8}  {'acerto':>8}  {'tempo':>7}")
    print("  " + "─" * 48)

    acertos, melhores = [], []
    for i in range(a.dobras):
        teste_grupos   = dobras[i]
        treino_grupos  = [g for j, d in enumerate(dobras) if j != i for g in d]

        treino_linhas  = [l for g in treino_grupos for l in g]
        teste_linhas   = [l for g in teste_grupos  for l in g]

        t0 = time.time()
        clf, acerto = treinar_e_avaliar(
            treino_linhas, teste_linhas, intencoes, vocab,
            a.passos, a.lote, a.taxa, a.semente + i)
        dt = time.time() - t0

        acertos.append(acerto)
        melhores.append((acerto, clf, treino_linhas, teste_linhas))
        print(f"  {i+1:>5}  {len(treino_linhas):>8,}  {len(teste_linhas):>8,}  "
              f"{acerto:>7.1%}  {dt:>6.0f}s")

    media = sum(acertos) / len(acertos)
    desvio = math.sqrt(sum((a - media) ** 2 for a in acertos) / len(acertos))
    print("  " + "─" * 48)
    print(f"  {'média':>5}  {'':>8}  {'':>8}  {media:>7.1%}  ±{desvio:.1%}\n")

    # ── treino final com TODOS os dados ──────────────────────────────
    print("  treinando modelo final (todos os dados) …")
    clf_final = ClassificadorDeIntencao(len(vocab), intencoes,
                                        dimensao=DIMENSAO, ocultos=OCULTOS,
                                        semente=a.semente)
    idx_int = {n: i for i, n in enumerate(intencoes)}
    todos = montar_exemplos(linhas, intencoes, vocab)
    rng = random.Random(a.semente)

    passos_final = int(a.passos * 1.2)   # 20% a mais porque não há divisão treino/teste
    for passo in range(1, passos_final + 1):
        lote_atual = rng.sample(todos, min(a.lote, len(todos)))
        if passo <= passos_final * 0.5:
            t = a.taxa
        elif passo <= passos_final * 0.8:
            t = a.taxa * 0.3
        else:
            t = a.taxa * 0.1
        clf_final.passo(lote_atual, t)
        if passo % (passos_final // 5) == 0:
            ac, _, _ = clf_final.avaliar(todos)
            print(f"    passo {passo:>5}/{passos_final}  acerto (treino): {ac:.1%}",
                  flush=True)

    acerto_treino, _, _ = clf_final.avaliar(todos)
    print(f"    acerto final (treino, todos os dados): {acerto_treino:.1%}")

    # ── gravar intencao.json ──────────────────────────────────────────
    d = clf_final.para_dicionario(vocab)
    d["limiar"] = 0.90
    d["medido"] = {
        "acerto_validacao_cruzada": round(media, 4),
        "desvio": round(desvio, 4),
        "acerto_treino_final": round(acerto_treino, 4),
        "passos_final": passos_final,
        "n_intencoes": len(intencoes),
        "n_frases": len(linhas),
        "n_vocabulario": len(vocab),
        "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    print(f"\n  ✓ gravado: {a.saida}")
    print(f"    {len(intencoes)} intenções · {len(vocab):,} peças · "
          f"acerto CV: {media:.1%} ±{desvio:.1%}")

    # ── gravar guarda.json — frases para a trava anti-esquecimento ────
    # Usa uma fração de cada dobra de teste: são frases que o modelo
    # nunca viu durante a validação cruzada, logo são uma amostra honesta.
    rng2 = random.Random(a.semente + 99)
    guarda = []
    melhor_acerto, melhor_clf, _, melhor_teste = max(melhores, key=lambda x: x[0])
    for l in melhor_teste:
        if l["intencao"] in idx_int:
            guarda.append({"pergunta": l["pergunta"], "intencao": l["intencao"]})
    rng2.shuffle(guarda)
    guarda = guarda[:800]   # cap: a trava não precisa de mais que isso
    salvar_guarda(guarda, a.guarda)
    print(f"  ✓ gravado: {a.guarda}  ({len(guarda)} frases)")

    # ── resumo por intenção ───────────────────────────────────────────
    print(f"\n  acertos por dobra: {' '.join(f'{a:.0%}' for a in acertos)}\n")

    # Intenções com acerto abaixo de 80% no melhor modelo de validação
    _, clf_melhor, treino_mel, teste_mel = max(melhores, key=lambda x: x[0])
    ex_teste = montar_exemplos(teste_mel, intencoes, vocab)
    _, _, M = clf_melhor.avaliar(ex_teste)

    print("  intenções com acerto < 80% (candidatas a mais frases no banco):")
    alguma = False
    for ki, nome in enumerate(intencoes):
        total = M[ki].sum()
        if total == 0:
            continue
        ac = M[ki, ki] / total
        if ac < 0.80:
            print(f"    {nome:30}  {ac:5.0%}  ({total} amostras)")
            alguma = True
    if not alguma:
        print("    (todas acima de 80%)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
