# -*- coding: utf-8 -*-
"""Treina a rede que responde consultas LINQ, e a submete ao compilador.

    python programas/treinar_consulta.py <pasta do projeto C#>
    python programas/treinar_consulta.py <pasta> --epocas 12
    python programas/treinar_consulta.py <pasta> --so-medir     não grava nada

A DIVISÃO DO TREINO É POR BASE (operação:classe:propriedade). Sem isso a
rede é testada em combinações que já viu com outras palavras e o número
sobe de mentira — já aconteceu neste projeto, 27 pontos de mentira.

E QUEM JULGA É O `dotnet build`. "Parece certo" não conta.

O CAMINHO QUE ESTE ARQUIVO NÃO SEGUIU, E FICA REGISTRADO

A primeira tentativa foi uma rede que escreve o LINQ letra por letra
(`modelo/escritor_linq.py`). Resultado medido: 100% das consultas
COMPILAM e 0% estão certas. O motivo está escrito no cabeçalho dela.
Mesmo corpus, mesmo juiz, outra FORMA de problema: 0% → 98,7%.

E ELE TREINA POR PROJETO. O modelo do projeto A respondendo sobre o
projeto B acerta 40% (medido); treinado no B, 92,7%. O motivo está no
cabeçalho de `modelo/consulta_linq.py`, com o número.
"""
import argparse
import collections
import json
import random
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from modelo.consulta_linq import (Consultor, caminho_do_modelo,  # noqa: E402
                                  guardar, treinar)
from modelo.decisor_linq import conferir                     # noqa: E402
from modelo.leitor_csharp import ProjetoCSharp               # noqa: E402
from modelo.moldes_linq import gerar                         # noqa: E402
from provas.juiz_csharp import Juiz                          # noqa: E402

SEM = 42

ap = argparse.ArgumentParser()
ap.add_argument("projeto", help="pasta de um projeto C#")
ap.add_argument("--epocas", type=int, default=12)
ap.add_argument("--taxa", type=float, default=0.25)
ap.add_argument("--corpus", default=None,
                help="por padrão dados/corpus_<pasta do projeto>.jsonl")
ap.add_argument("--modelo", default=None,
                help="por padrão modelos/consulta_<pasta do projeto>.json")
ap.add_argument("--so-medir", action="store_true")
arg = ap.parse_args()
arg.modelo = arg.modelo or str(caminho_do_modelo(RAIZ, arg.projeto))
# corpus por projeto pelo mesmo motivo do modelo: treinar no seguinte
# não pode apagar o anterior sem avisar
arg.corpus = arg.corpus or str(RAIZ / "dados" /
                               (Path(arg.modelo).stem.replace("consulta_", "corpus_")
                                + ".jsonl"))

print("gradiente antes de treinar:", end=" ")
for n, rel, ab in conferir():
    if rel > 1e-5 and ab > 1e-9:
        print(f"\n   {n}: rel {rel:.1e} abs {ab:.1e}  ERRADO — NÃO TREINE")
        raise SystemExit(1)
print("confere\n")

proj = ProjetoCSharp(arg.projeto)
print(proj.resumo() + "\n")
if not [e for e in proj.entidades if proj.lista_de(e)]:
    print("este projeto não tem nenhuma List<T> — não há o que consultar")
    raise SystemExit(1)

# ── o corpus: gerado do próprio projeto ──────────────────────────────
corpus = Path(arg.corpus)
pares = gerar(proj, 8000)
if not arg.so_medir:
    corpus.parent.mkdir(parents=True, exist_ok=True)
    with open(corpus, "w", encoding="utf-8") as f:
        for x in pares:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

rng = random.Random(SEM)
por_base = collections.defaultdict(list)
for p in pares:
    por_base[p["base"]].append(p)
bases = sorted(por_base)
rng.shuffle(bases)
corte = int(len(bases) * 0.82)
tr = [p for b in bases[:corte] for p in por_base[b]]
te = [p for b in bases[corte:] for p in por_base[b]]

# O TREINO EM SI mora em `modelo/consulta_linq.py`, porque o PROGRAMA
# também precisa treinar (projeto novo aberto no painel) e duas cópias da
# mesma conta viram duas contas diferentes no primeiro conserto. Aqui só
# se passa a metade de TREINO das bases: a de teste tem de ficar fora até
# do vocabulário.
print(f"{len(pares):,} pares · {len(bases)} bases "
      f"({len(tr):,} treino / {len(te):,} teste, divididos POR BASE)")
t0 = time.time()


def mostrar(ep, total, perda):
    if ep % max(1, total // 6) == 0 or ep == 1:
        print(f"  época {ep:>3}/{total}  perda {perda:6.3f}  ({time.time()-t0:.0f}s)")


rede, peneira, _ = treinar(proj, epocas=arg.epocas, taxa=arg.taxa,
                           semente=SEM, pares=tr, avisar=mostrar)
print(f"peneira: {len(peneira):,} peças · rede: {rede.n_parametros:,} parâmetros")

# ══════════════════════════════════════════════════════════════════════
#  A PROVA — pelo MESMO caminho que o programa usa de verdade
# ══════════════════════════════════════════════════════════════════════
# Grava primeiro e testa pelo Consultor recém-aberto: se o guardar/abrir
# perder alguma coisa, o número da prova cai e eu fico sabendo. Testar o
# objeto que está na memória esconderia exatamente esse defeito.
provisorio = Path(arg.modelo) if not arg.so_medir else \
    Path(arg.modelo).with_suffix(".teste.json")
guardar(provisorio, rede, peneira)
consultor = Consultor(provisorio, proj)
juiz = Juiz(arg.projeto, proj)


def julgar(marca, casos):
    escritas = [(f"{marca}{i}", consultor.montar(p)) for i, (p, _) in enumerate(casos)]
    vered = juiz.compilar(escritas)
    comp = cert = 0
    linhas = []
    for i, (pedido, esperado) in enumerate(casos):
        saiu = escritas[i][1]
        ok, err = vered[f"{marca}{i}"]
        igual = esperado is not None and saiu.strip() == esperado.strip()
        comp += ok
        cert += igual
        linhas.append((pedido, saiu, ok, igual, err))
    return comp, cert, linhas


# ── as perguntas ESCRITAS À MÃO, no português de quem pede ───────────
# Elas nunca entram no treino. O corpus é feito de moldes meus, e uma
# rede que só acerta os meus moldes não serve para nada — estas oito
# saíram dos enunciados do arquivo, escritas por outra pessoa.
MAO = RAIZ / "dados" / "consultas_a_mao.json"
escritas_a_mao = json.loads(MAO.read_text(encoding="utf-8")) if MAO.exists() else {}
chave = Path(arg.projeto).resolve().name.lower()
casos_mao = escritas_a_mao.get(chave, [])

print("\n" + "=" * 78)
if casos_mao:
    for grupo in casos_mao:
        casos = [(c["pedido"], c.get("linq")) for c in grupo["casos"]]
        comp, cert, linhas = julgar(grupo["marca"], casos)
        gab = sum(1 for _, e in casos if e)
        print(f"\n{grupo['titulo']}   compila {comp}/{len(casos)}"
              + (f" · certa {cert}/{gab}" if gab else ""))
        print("-" * 78)
        for pedido, saiu, ok, igual, err in linhas:
            print(f"  {'OK' if ok else 'X '}{'=' if igual else ' '} {pedido}")
            print(f"      → {saiu}")
            if not ok:
                print(f"        {err}")
else:
    print("(sem perguntas escritas à mão para este projeto em "
          "dados/consultas_a_mao.json — só a prova das bases novas)")

# ── e a prova grande: bases que a rede nunca viu ─────────────────────
print("\n" + "=" * 78)
amostra = random.Random(9).sample(te, min(150, len(te)))
comp, cert, _ = julgar("H", [(p["pedido"], p["linq"]) for p in amostra])
print(f"BASES QUE ELA NUNCA VIU — {len(amostra)} pedidos")
print(f"   compila:                     {comp}/{len(amostra)} = {comp/len(amostra):.1%}")
print(f"   exatamente a consulta certa: {cert}/{len(amostra)} = {cert/len(amostra):.1%}")
juiz.fechar()

medido = {"compila": f"{comp}/{len(amostra)}", "certa": f"{cert}/{len(amostra)}",
          "projeto": Path(arg.projeto).resolve().name,
          "bases_de_teste": len(bases) - corte}
if arg.so_medir:
    provisorio.unlink(missing_ok=True)
    print("\n--so-medir: nada foi gravado")
else:
    guardar(arg.modelo, rede, peneira, medido)
    print(f"\ngravado em {arg.modelo}")
