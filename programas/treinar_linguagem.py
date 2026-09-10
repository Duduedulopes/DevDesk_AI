"""Treina o modelo de linguagem e mede bits por caractere.

A REGRA DE OURO DESTE ARQUIVO: o número que vale é o do texto DE FORA.

A perda de treino sempre cai — inclusive quando o modelo está só decorando.
O que diz se ele aprendeu estrutura é o custo sobre texto que ele nunca viu.
É esse que a gente compara com o gzip e o bzip2, porque um compressor também
não viu o texto antes de comprimi-lo.
"""
import sys, time, math, argparse, random
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
import numpy as np
from pathlib import Path

from modelo.linguagem import ModeloDeLinguagem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="dados/corpus.txt")
    ap.add_argument("--caracteres", type=int, default=300_000)
    ap.add_argument("--contexto", type=int, default=8)
    ap.add_argument("--dimensao", type=int, default=16)
    ap.add_argument("--oculta", type=int, default=256)
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--taxa", type=float, default=0.5)
    ap.add_argument("--passos", type=int, default=4000)
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--saida", default="modelos/linguagem.json")
    ap.add_argument("--continuar", action="store_true",
                    help="retoma de --saida em vez de sortear pesos novos")
    a = ap.parse_args()

    texto = Path(a.corpus).read_text(encoding="utf-8")[:a.caracteres]

    # SEPARAÇÃO POR BLOCO, e não sorteando caracteres. Sortear janelas de um
    # texto só faria treino e prova compartilharem vizinhança: o modelo veria
    # "compress" no treino e seria testado em "ompressã" — mesma frase, outro
    # nome. O corte tem que ser em bloco.
    corte = int(len(texto) * 0.9)
    treino_txt, fora_txt = texto[:corte], texto[corte:]

    alfabeto = sorted(set(texto))
    ja_feitos = 0
    if a.continuar and Path(a.saida).exists():
        m, salvo = ModeloDeLinguagem.carregar(a.saida)
        ja_feitos = salvo.get("passos", 0)
        # O alfabeto TEM que ser o mesmo: os índices da tabela dependem dele.
        # Um corpus diferente daria outro alfabeto e a tabela apontaria para
        # as letras erradas — sem erro nenhum, só um modelo que virou lixo.
        if m.alfabeto != alfabeto:
            raise SystemExit(f"  alfabeto mudou ({len(m.alfabeto)} → {len(alfabeto)}): "
                             f"use o mesmo --caracteres do treino anterior")
        print(f"\n  retomando de {a.saida} — {ja_feitos:,} passos já feitos")
    else:
        m = ModeloDeLinguagem(alfabeto, a.contexto, a.dimensao, a.oculta, a.semente)

    tr = m.codificar(treino_txt)
    fo = m.codificar(fora_txt)

    print(f"\n  {m}")
    print(f"  treino : {len(tr):,} caracteres")
    print(f"  de fora: {len(fo):,} caracteres  (o juiz)")
    print(f"  uniforme (teto): {math.log2(len(alfabeto)):.3f} bits/car\n")

    rng = random.Random(a.semente)
    def sortear_lote():
        lote = []
        for _ in range(a.lote):
            i = rng.randrange(m.contexto, len(tr))
            lote.append((tr[i - m.contexto:i], tr[i]))
        return lote

    print(f"  {'passo':>7} {'perda(treino)':>14} {'bits/car(fora)':>15} {'tempo':>8}")
    print("  " + "─" * 50)

    inicio = time.time()
    marcos = []
    for passo in range(1, a.passos + 1):
        perda = m.passo(sortear_lote(), a.taxa)
        if passo % max(1, a.passos // 10) == 0 or passo == 1:
            bpc = m.bits_por_caractere(fo, salto=7)
            marcos.append((passo, perda, bpc))
            print(f"  {passo + ja_feitos:7} {perda:14.3f} {bpc:15.3f} "
                  f"{time.time()-inicio:7.0f}s", flush=True)
            # Grava a cada marco. Treino longo que cai sem gravar perde tudo.
            m.guardar(a.saida, {"bits_por_caractere": bpc,
                                "passos": passo + ja_feitos,
                                "caracteres_treino": len(tr)})

    final = m.bits_por_caractere(fo, salto=1)
    print("  " + "─" * 50)
    print(f"\n  ══════ {final:.3f} bits/caractere no texto de fora ══════\n")

    for nome, valor in [("uniforme", math.log2(len(alfabeto))), ("gzip -9", 2.910),
                        ("bzip2 -9", 2.473)]:
        d = valor - final
        print(f"    contra {nome:10} ({valor:.3f}):  "
              f"{'GANHOU' if d > 0 else 'perdeu'} por {abs(d):.3f} bits")

    m.guardar(a.saida, {"bits_por_caractere": final, "passos": a.passos + ja_feitos,
                        "caracteres_treino": len(tr)})
    print(f"\n  gravado: {a.saida}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
