"""
A régua do projeto: bits por caractere.

O QUE ESTE NÚMERO É, E POR QUE ELE É O ÚNICO QUE IMPORTA.

Treinar a rede para prever o próximo caractere é minimizar a entropia
cruzada. A entropia cruzada média, dividida por ln(2), é exatamente quantos
BITS a rede precisa para dizer qual é o próximo caractere. Isso não é uma
analogia com compressão — é compressão. Um modelo que atinge 2,0 bits/car
comprime o corpus para 1/4 do tamanho de um texto sem modelo nenhum.

Por isso "quanto mais dado a gente comprimir, mais inteligente ela é" é uma
tese mensurável, e este arquivo é o instrumento que a mede.

OS ADVERSÁRIOS, do mais burro ao mais difícil:

  uniforme   — nenhum modelo: log2(alfabeto). O teto absoluto.
  frequência — só conta letra: quantas vezes cada uma aparece. Ordem 0.
  bigrama    — olha o caractere anterior. Ordem 1.
  trigrama   — olha os dois anteriores. Ordem 2.
  gzip -9    — LZ77 + Huffman, de 1992. É este que a rede precisa bater.

Bater o gzip é o marco: significa que a rede aprendeu estrutura que um
compressor genérico não enxerga. Não bater significa que treinamos um
compressor pior que o que já vinha no sistema operacional.
"""
import io
import gzip, lzma, bz2, math, argparse
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter, defaultdict
from pathlib import Path


def uniforme(t: str) -> float:
    return math.log2(len(set(t)))


def ordem_n(t: str, n: int) -> float:
    """Entropia condicional a n caracteres anteriores, com suavização de Laplace.

    Sem suavização, um contexto visto uma vez só daria probabilidade 1 ao que
    veio depois — e 0 a todo o resto. O primeiro caractere inédito custaria
    infinitos bits, o que é falso: o modelo não sabia, mas o dado existe.
    """
    alfabeto = len(set(t))
    contagem = defaultdict(Counter)
    for i in range(n, len(t)):
        contagem[t[i - n:i]][t[i]] += 1

    bits = 0.0
    for i in range(n, len(t)):
        ctx, c = t[i - n:i], t[i]
        tab = contagem[ctx]
        p = (tab[c] + 1) / (sum(tab.values()) + alfabeto)
        bits -= math.log2(p)
    return bits / (len(t) - n)


def compressor(nome, fn, bruto: bytes, n_car: int) -> tuple[str, float]:
    return nome, len(fn(bruto)) * 8 / n_car


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="dados/corpus.txt")
    ap.add_argument("--amostra", type=int, default=400_000,
                    help="os modelos de ordem n são O(n) mas pesados; 0 = tudo")
    args = ap.parse_args()

    t = Path(args.corpus).read_text(encoding="utf-8")
    if args.amostra and len(t) > args.amostra:
        t = t[:args.amostra]
    bruto = t.encode("utf-8")

    print(f"\n  corpus  : {len(t):,} caracteres · alfabeto de {len(set(t))}")
    print(f"  em utf-8: {len(bruto):,} bytes\n")

    linhas = [
        ("uniforme (sem modelo)", uniforme(t)),
        ("frequência (ordem 0)",  ordem_n(t, 0)),
        ("bigrama (ordem 1)",     ordem_n(t, 1)),
        ("trigrama (ordem 2)",    ordem_n(t, 2)),
        compressor("gzip -9",  lambda b: gzip.compress(b, 9), bruto, len(t)),
        compressor("bzip2 -9", lambda b: bz2.compress(b, 9),  bruto, len(t)),
        compressor("lzma -9",  lambda b: lzma.compress(b),    bruto, len(t)),
    ]

    pior = max(v for _, v in linhas)
    print(f"  {'modelo':24} {'bits/car':>9}   {'tamanho':>9}")
    print("  " + "─" * 62)
    for nome, v in linhas:
        barra = "█" * int(v / pior * 22)
        print(f"  {nome:24} {v:9.3f}   {v/8*len(t)/1024:7.0f} KB  {barra}")
    print("  " + "─" * 62)

    alvo = min(v for n, v in linhas if n.startswith(("gzip", "bzip2", "lzma")))
    print(f"\n  O ALVO DA REDE: abaixo de {alvo:.3f} bits/car.")
    print(f"  Acima disso, treinamos um compressor pior que o do sistema.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
