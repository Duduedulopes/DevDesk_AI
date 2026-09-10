"""Quanto contexto vale a pena? Uma configuração por chamada, e comparação justa.

A PERGUNTA

Com 8 caracteres o modelo não vê nem uma palavra inteira. Dobrar o contexto
dobra a entrada, dobra os pesos da primeira camada e deixa cada passo mais
lento. O ganho compensa? E até onde?

A REGRA DA COMPARAÇÃO JUSTA

Cada contexto treina DO ZERO, com o mesmo número de passos, o mesmo corpus,
a mesma semente e o mesmo cronograma de taxa. Comparar um modelo novo contra
um que já levou 78 mil passos não diria nada sobre contexto — diria sobre
quem treinou mais.

Registra também o tempo e o número de parâmetros, porque "melhorou" sem o
custo ao lado é meia informação: um modelo que ganha 0,05 bits e demora o
triplo pode não valer.

O CRONOGRAMA DE TAXA, E POR QUE ELE ESTÁ AQUI DENTRO

Medido no passo anterior: com taxa fixa em 0,5 o modelo travou em 2,86 e
baixando para 0,1 destravou e caiu para 2,75. Passo grande faz a rede quicar
em volta do mínimo em vez de assentar. Então a taxa cai em degraus — não é
ajuste fino, é a diferença entre medir a arquitetura e medir um treino mal
configurado.
"""
import io
import sys, time, math, json, argparse, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from pathlib import Path

from modelo.linguagem import ModeloDeLinguagem

# Três degraus, um terço do treino cada. Os valores vieram da medição.
DEGRAUS = [(0.34, 0.5), (0.34, 0.1), (0.32, 0.02)]


def taxa_do_passo(passo, total):
    fracao, acumulado = passo / total, 0.0
    for parte, taxa in DEGRAUS:
        acumulado += parte
        if fracao <= acumulado:
            return taxa
    return DEGRAUS[-1][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contexto", type=int, required=True)
    ap.add_argument("--corpus", default="dados/corpus.txt")
    ap.add_argument("--caracteres", type=int, default=200_000)
    ap.add_argument("--dimensao", type=int, default=16)
    ap.add_argument("--oculta", type=int, default=256)
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--passos", type=int, default=9000)
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--resultados", default="dados/varredura_contexto.jsonl")
    ap.add_argument("--medir", type=int, default=30_000,
                    help="caracteres usados em cada medição, nas duas pontas")
    a = ap.parse_args()

    texto = Path(a.corpus).read_text(encoding="utf-8")[:a.caracteres]

    # ── EMBARALHAR EM BLOCOS ANTES DE CORTAR ──────────────────────────
    #
    # O corpus vem ORDENADO POR FONTE: caderno, docs, READMEs, perguntas,
    # Python, C#. Cortar 90/10 no fim deixa prosa em português no treino e
    # C# puro no teste — e código é muito mais previsível que prosa.
    #
    # Medido antes de consertar: o modelo dava 3,712 bits no treino e 2,144
    # no "de fora". Texto nunca visto saindo 1,5 bit MELHOR que o treinado é
    # impossível; o que estava acontecendo é que a prova era mais fácil.
    #
    # Embaralhar em blocos de 2.000 caracteres põe a mesma mistura de fontes
    # nos dois lados. Blocos, e não caracteres soltos, porque a janela precisa
    # de vizinhança contínua para existir — com 2.000 de bloco e contexto 16,
    # menos de 1% das janelas cai numa emenda.
    import random as _r
    BLOCO = 2000
    blocos = [texto[i:i + BLOCO] for i in range(0, len(texto), BLOCO)]
    _r.Random(a.semente).shuffle(blocos)
    texto = "".join(blocos)

    corte = int(len(texto) * 0.9)
    alfabeto = sorted(set(texto))

    m = ModeloDeLinguagem(alfabeto, a.contexto, a.dimensao, a.oculta, a.semente)
    tr, fo = m.codificar(texto[:corte]), m.codificar(texto[corte:])

    # AMOSTRAS FIXAS PARA MEDIR, e do mesmo tamanho nas duas pontas.
    # Medir treino num pedaço e "fora" noutro de tamanho diferente tornaria
    # a distância entre eles incomparável. E medir 390 mil caracteres a cada
    # marco custaria mais tempo que o próprio treino.
    amostra_tr = tr[:a.medir]
    amostra_fo = fo[:a.medir]

    print(f"\n  contexto {a.contexto:>2} · {m.n_parametros:,} parâmetros · "
          f"{a.passos:,} passos")

    rng = random.Random(a.semente)
    inicio = time.time()
    for passo in range(1, a.passos + 1):
        lote = []
        for _ in range(a.lote):
            i = rng.randrange(m.contexto, len(tr))
            lote.append((tr[i - m.contexto:i], tr[i]))
        m.passo(lote, taxa_do_passo(passo, a.passos))
        if passo % max(1, a.passos // 6) == 0:
            b_tr = m.bits_por_caractere(amostra_tr, salto=9)
            b_fo = m.bits_por_caractere(amostra_fo, salto=9)
            print(f"     {passo:6}   treino {b_tr:6.3f}   fora {b_fo:6.3f}"
                  f"   distância {b_fo - b_tr:+.3f}   {time.time()-inicio:5.0f}s",
                  flush=True)

    segundos = time.time() - inicio
    bpc = m.bits_por_caractere(amostra_fo, salto=3)
    bpc_tr = m.bits_por_caractere(amostra_tr, salto=3)

    r = {"contexto": a.contexto, "parametros": m.n_parametros, "passos": a.passos,
         "bits_por_caractere": round(bpc, 4), "bits_treino": round(bpc_tr, 4),
         "distancia": round(bpc - bpc_tr, 4),
         "segundos": round(segundos, 1), "alfabeto": len(alfabeto),
         "passos_por_s": round(a.passos / segundos, 1), "caracteres": a.caracteres}
    with open(a.resultados, "a", encoding="utf-8") as f:
        f.write(json.dumps(r) + "\n")

    m.guardar(f"modelos/varredura_ctx{a.contexto}_{a.caracteres//1000}k.json", {"bits_por_caractere": bpc,
                                                          "passos": a.passos})
    print(f"\n  ══ ctx {a.contexto}: fora {bpc:.3f} · treino {bpc_tr:.3f} · "
          f"distância {bpc-bpc_tr:+.3f} · {segundos:.0f}s ══\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
