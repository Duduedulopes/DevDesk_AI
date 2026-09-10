"""Modelo de linguagem sobre PEÇAS, medido em bits por CARACTERE.

A ÚNICA DIFERENÇA CONCEITUAL EM RELAÇÃO AO MODELO DE CARACTERES

Nenhuma, no motor. É a mesma tabela de embutimento, a mesma oculta com
sigmoide, a mesma softmax e a mesma entropia cruzada. O que muda é o que
conta como "símbolo": em vez de 234 caracteres, 564 peças.

E POR ISSO A MEDIÇÃO PRECISA MUDAR

`bits_por_caractere` do modelo de caracteres divide o total de bits pelo
número de PREVISÕES — e ali cada previsão era um caractere, então dava certo
por coincidência. Aqui cada previsão vale 1,82 caracteres em média.

    errado:  bits ÷ peças      → parece 1,8× melhor do que é
    certo :  bits ÷ caracteres → comparável com o gzip e com o modelo de char

Este arquivo faz a conta certa e nunca imprime a errada, para ninguém copiar
o número de dentro do log por engano.
"""
import io
import sys, time, math, argparse, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from pathlib import Path

from texto.pecas import Pecas
from modelo.linguagem import ModeloDeLinguagem

DEGRAUS = [(0.34, 0.5), (0.34, 0.1), (0.32, 0.02)]


def taxa_do_passo(passo, total):
    frac, ac = passo / total, 0.0
    for parte, taxa in DEGRAUS:
        ac += parte
        if frac <= ac:
            return taxa
    return DEGRAUS[-1][1]


def bits_por_caractere(m, pecas, indices, salto=1):
    """A medida honesta: bits acumulados ÷ caracteres cobertos."""
    bits = 0.0
    caracteres = 0
    for i in range(m.contexto, len(indices), salto):
        certo = indices[i]
        bits += m.bits_do_proximo(indices[i - m.contexto:i], certo)
        caracteres += pecas.tamanho[certo]
    return bits / caracteres if caracteres else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="dados/corpus.txt")
    ap.add_argument("--pecas", default="modelos/pecas.json")
    ap.add_argument("--caracteres", type=int, default=3_900_000)
    ap.add_argument("--contexto", type=int, default=8)
    ap.add_argument("--dimensao", type=int, default=16)
    ap.add_argument("--oculta", type=int, default=256)
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--passos", type=int, default=9000)
    ap.add_argument("--medir", type=int, default=10_000, help="peças por medição")
    ap.add_argument("--alvo", type=int, default=0,
                    help="total planejado de passos, para o cronograma de taxa")
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--saida", default="modelos/linguagem_pecas.json")
    ap.add_argument("--continuar", action="store_true")
    a = ap.parse_args()

    texto = Path(a.corpus).read_text(encoding="utf-8")[:a.caracteres]

    # A MESMA correção de metodologia do modelo de caracteres: o corpus vem
    # ordenado por fonte, e cortar no fim poria C# de um lado e prosa do
    # outro. Blocos embaralhados antes do corte.
    BLOCO = 2000
    blocos = [texto[i:i + BLOCO] for i in range(0, len(texto), BLOCO)]
    random.Random(a.semente).shuffle(blocos)
    texto = "".join(blocos)

    p = Pecas.carregar(a.pecas)
    print(f"\n  {p}")
    t0 = time.time()
    idx = p.codificar(texto)
    n_car = p.caracteres_de(idx)
    print(f"  corpus: {n_car:,} caracteres → {len(idx):,} peças "
          f"({n_car/len(idx):.2f} car/peça, {time.time()-t0:.0f}s)")

    corte = int(len(idx) * 0.9)
    tr, fo = idx[:corte], idx[corte:]
    am_tr, am_fo = tr[:a.medir], fo[:a.medir]

    ja = 0
    if a.continuar and Path(a.saida).exists():
        m, salvo = ModeloDeLinguagem.carregar(a.saida)
        ja = salvo.get("passos", 0)
        print(f"  retomando — {ja:,} passos já feitos")
    else:
        m = ModeloDeLinguagem(p.vocab, a.contexto, a.dimensao, a.oculta, a.semente)
    alcance = a.contexto * n_car / len(idx)
    print(f"  {m}")
    print(f"  contexto de {a.contexto} peças ≈ {alcance:.1f} caracteres de texto real\n")

    rng = random.Random(a.semente)
    print(f"  {'passo':>7}  {'treino':>7}  {'fora':>7}  {'dist':>6}  {'tempo':>6}   (bits/CARACTERE)")
    print("  " + "─" * 60)

    for passo in range(1, a.passos + 1):
        lote = []
        for _ in range(a.lote):
            i = rng.randrange(m.contexto, len(tr))
            lote.append((tr[i - m.contexto:i], tr[i]))
        # A taxa segue o cronograma pelo passo TOTAL, não pelo desta chamada:
        # senão cada retomada voltaria para 0,5 e desfaria o assentamento.
        m.passo(lote, taxa_do_passo(passo + ja, a.alvo or a.passos))

        if passo % max(1, a.passos // 6) == 0:
            b_tr = bits_por_caractere(m, p, am_tr, salto=5)
            b_fo = bits_por_caractere(m, p, am_fo, salto=5)
            print(f"  {passo+ja:7}  {b_tr:7.3f}  {b_fo:7.3f}  {b_fo-b_tr:+6.3f}  "
                  f"{time.time()-t0:5.0f}s", flush=True)
            m.guardar(a.saida, {"bits_por_caractere": b_fo,
                                "passos": passo + ja, "pecas": len(p)})

    final = bits_por_caractere(m, p, am_fo, salto=2)
    m.guardar(a.saida, {"bits_por_caractere": final,
                        "passos": a.passos + ja, "pecas": len(p)})

    print("  " + "─" * 60)
    print(f"\n  ══════ {final:.3f} bits/CARACTERE ══════\n")
    for nome, v in [("char ctx8 (mesmo orçamento)", 3.351), ("gzip -9", 2.910),
                    ("bzip2 -9", 2.473)]:
        d = v - final
        print(f"    contra {nome:28} ({v:.3f}): "
              f"{'GANHOU' if d > 0 else 'perdeu'} por {abs(d):.3f}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
