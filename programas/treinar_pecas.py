"""Aprende o vocabulário de peças e mede o que ele economiza."""
import io
import sys, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from pathlib import Path
from texto.pecas import Pecas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="dados/corpus.txt")
    ap.add_argument("--aprender_em", type=int, default=1_200_000,
                    help="fatia usada para APRENDER as fusões (aplicar é barato)")
    ap.add_argument("--fusoes", type=int, default=400)
    ap.add_argument("--saida", default="modelos/pecas.json")
    a = ap.parse_args()

    texto = Path(a.corpus).read_text(encoding="utf-8")
    amostra = texto[:a.aprender_em]
    print(f"\n  aprendendo em {len(amostra):,} caracteres, {a.fusoes} fusões\n")

    t = time.time()
    def aviso(n, peca, quantas):
        print(f"     {n:4} fusões · última: {peca!r} ({quantas:,}×) · {time.time()-t:.0f}s",
              flush=True)

    p = Pecas.treinar(amostra, a.fusoes, aviso)
    p.guardar(a.saida)

    print(f"\n  {p}")
    print(f"\n  ── as 40 primeiras peças aprendidas ──")
    aprendidas = [a_ + b_ for a_, b_ in p.fusoes[:40]]
    for i in range(0, 40, 8):
        print("     " + "  ".join(f"{x!r:>12}" for x in aprendidas[i:i+8]))

    # A MEDIDA QUE IMPORTA: quantos caracteres cabem numa peça.
    prova = texto[a.aprender_em:a.aprender_em + 200_000]
    idx = p.codificar(prova)
    n_car = p.caracteres_de(idx)
    print(f"\n  ── em 200 mil caracteres NÃO usados no aprendizado ──")
    print(f"     peças            : {len(idx):,}")
    print(f"     caracteres        : {n_car:,}")
    print(f"     caracteres/peça   : {n_car/len(idx):.2f}")
    print(f"\n  Cada peça vale {n_car/len(idx):.2f} caracteres. É por este número")
    print(f"  que bits/peça precisa ser dividido para virar bits/caractere.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
