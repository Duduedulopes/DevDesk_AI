# -*- coding: utf-8 -*-
"""Treina a rede etiquetadora e mede nas linguagens que ela NUNCA viu."""
import io
import json, math, random, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modelo.etiquetador import Etiquetador, ETIQUETAS
from texto.vocabulario import Vocabulario, pedacos as partir

RAIZ = Path(__file__).resolve().parent.parent

def ler(nome):
    with open(RAIZ/"dados"/nome, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

def dividir(linhas, semente=7, fatias=(0.6,0.2,0.2)):
    rng = random.Random(semente)
    bases = defaultdict(list)
    for l in linhas: bases[l["base"]].append(l)
    grupos = list(bases.values())
    rng.shuffle(grupos)
    n = len(grupos); c1 = int(n*fatias[0]); c2 = c1+int(n*fatias[1])
    p = ([], [], [])
    for destino, fatia in zip(p, (grupos[:c1], grupos[c1:c2], grupos[c2:])):
        for g in fatia: destino.extend(g)
    for x in p: rng.shuffle(x)
    return p

def em_pedacos(pecas, vocab):
    return [vocab.indices(p) for p in pecas]

def montar(linhas, vocab):
    k_de = {e:i for i,e in enumerate(ETIQUETAS)}
    ex = []
    for l in linhas:
        frase = em_pedacos(l["pecas"], vocab)
        for i, et in enumerate(l["etiquetas"]):
            ex.append((frase, i, k_de[et]))
    return ex

def main():
    t0 = time.time()
    treino_todo = ler("criar_treino.jsonl")
    novas = ler("criar_novas.jsonl")
    tr, av, te = dividir(treino_todo)

    # vocabulário SÓ do treino
    vocab = Vocabulario([l["frase"] for l in tr], minimo=1)
    ex_tr, ex_av, ex_te = (montar(x, vocab) for x in (tr, av, te))
    ex_novas = montar(novas, vocab)

    print(f"\n  vocabulário (só do treino): {len(vocab):,} pedaços")
    print(f"  peças a etiquetar: treino {len(ex_tr):,} · aval {len(ex_av):,} · "
          f"teste {len(ex_te):,} · NOVAS {len(ex_novas):,}")

    et = Etiquetador(len(vocab), janela=2, dimensao=24, ocultos=48, semente=7)
    print(f"  parâmetros: {et.n_parametros:,}\n")
    rng = random.Random(7)
    passos, lote, taxa = 6000, 64, 0.5
    print(f"  {'passo':>6} {'treino':>8} {'aval':>8} {'NOVAS':>8} {'bits':>7}")
    print("  " + "─"*44)
    melhor = (-1, None, 0)
    for passo in range(1, passos+1):
        b = rng.sample(ex_tr, min(lote, len(ex_tr)))
        t = taxa if passo <= passos*0.5 else taxa*0.3 if passo <= passos*0.8 else taxa*0.1
        et.passo(b, t)
        if passo % (passos//10) == 0:
            a_tr,_,_ = et.avaliar(rng.sample(ex_tr, 2000))
            a_av,c_av,_ = et.avaliar(ex_av)
            a_no,_,_ = et.avaliar(rng.sample(ex_novas, 2000))
            print(f"  {passo:>6} {a_tr:>8.1%} {a_av:>8.1%} {a_no:>8.1%} {c_av/math.log(2):>7.2f}", flush=True)
            if a_av > melhor[0]:
                melhor = (a_av, (et.tabela.copy(), [(c.pesos.copy(), c.vies.copy()) for c in et.rede.camadas]), passo)
    et.tabela, camadas = melhor[1][0].copy(), melhor[1][1]
    for c,(p,v) in zip(et.rede.camadas, camadas): c.pesos, c.vies = p.copy(), v.copy()
    print(f"\n  parou no passo {melhor[2]}")

    # ── a medida por campo, que é a que não mente ────────────────────
    # O acerto médio conta o `O` junto, e `O` é 3 de cada 4 peças: uma rede
    # que só respondesse `O` já marcaria 75%. O que interessa é quanto ela
    # acerta CADA campo, e principalmente nas linguagens que nunca viu.
    import collections
    def por_campo(conjunto, nome):
        certo = collections.Counter(); total = collections.Counter()
        for it in conjunto:
            em_pedacos = [vocab.indices(x) or [et.borda] for x in it["pecas"]]
            saiu = [ETIQUETAS[int(np.argmax(et.prever(em_pedacos, i).ravel()))]
                    for i in range(len(em_pedacos))]
            for s_, a_ in zip(saiu, it["etiquetas"]):
                if a_ != "O":
                    total[a_] += 1; certo[a_] += (s_ == a_)
        print(f"\n  {nome}")
        for campo in ("LING", "TIPO", "NOME"):
            t = total[campo]
            print(f"    {campo:<6}{certo[campo]:>5}/{t:<6}"
                  f"{(certo[campo]/t if t else 0):>7.1%}")
        return {c: (certo[c] / total[c] if total[c] else 0.0)
                for c in ("LING", "TIPO", "NOME")}

    m_te = por_campo(te, "nas linguagens ENSINADAS")
    m_no = por_campo(novas, "nas linguagens que ela NUNCA VIU")

    # ── grava, que é o que faltava para o aplicativo usar ─────────────
    d = et.para_dicionario(vocab)
    d["medido"] = {
        "protocolo": "divisão por base (as variantes de uma frase ficam juntas); "
                     "as linguagens NOVAS nunca entraram no treino",
        "acerto_avaliacao": round(melhor[0], 4),
        "passo_escolhido": melhor[2],
        "por_campo_ensinadas": {k: round(v, 4) for k, v in m_te.items()},
        "por_campo_novas": {k: round(v, 4) for k, v in m_no.items()},
        "n_frases_treino": len(tr), "n_frases_teste": len(te),
        "n_frases_novas": len(novas), "n_vocabulario": len(vocab),
        "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    saida = RAIZ / "modelos" / "etiquetador.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    print(f"\n  gravado: {saida}")
    print(f"    {len(vocab):,} peças · {et.n_parametros:,} parâmetros")

    with open("/tmp/an/_etq.pkl","wb") as f:
        import pickle; pickle.dump({"vocab": vocab, "et": et, "te": te, "novas": novas,
                                    "ex_te": ex_te, "ex_novas": ex_novas}, f)
    print(f"  {time.time()-t0:.0f}s")

if __name__ == "__main__":
    raise SystemExit(main())
