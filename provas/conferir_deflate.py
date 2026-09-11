# -*- coding: utf-8 -*-
"""Prova de interop do pacote `compressao` contra `zlib`/`gzip` da stdlib.

A única prova que vale para um formato escrito da mão na massa é o
diálogo com quem implementa o padrão de verdade. Cada caso roda o
round-trip do próprio pacote E os dois sentidos da ponte:

  meu-escreve → eles-leem    (o que eu gero, o zlib/gzip descomprime)
  eles-escrevem → eu-leio   (o que eles geram, eu ainda leio)

Se qualquer sentido falhar, o formato não é o formato — este script
termina com código de erro 1 e imprime a lista exata.
"""
import gzip as gzip_stdlib
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compressao import deflate, gzip_


CASOS = [
    (b"",                            "vazio"),
    (b"a",                           "literal unico"),
    (b"a" * 5,                       "match de 5"),
    (b"a" * 8,                       "match de 8"),
    (b"a" * 10,                      "match de 10"),
    (b"a" * 258,                     "comprimento maximo"),
    (b"ab" * 100,                    "match pequeno repetido"),
    (b"abcdabcdabcd",                "match medio"),
    (b"banana banana banana",        "sofrimento"),
    (bytes(range(256)),              "todos os bytes uma vez"),
    (bytes(range(256)) * 3,          "todos os bytes repetidos"),
    (b"x" * 300,                     "match esticado"),
    (b"a" * 10 + b"b" + b"a" * 20,   "tres matches em sequencia"),
]


def conferir_deflate():
    """Round-trip próprio + dois sentidos da ponte com o zlib raw."""
    falhas = []
    for dados, nome in CASOS:
        # sentidos da ponte, nível 9 (que usa Huffman dinâmico — o nosso
        # leitor tem que aguentar o que o zlib escreve por padrão).
        z = zlib.compressobj(level=9, wbits=-15)
        seu = z.compress(dados) + z.flush()
        meu = deflate.comprimir(dados)
        linhas = []
        if not _round_trip(dados, nome):
            falhas.append((nome, "round-trip do proprio pacote"))
        if zlib.decompressobj(-15).decompress(meu) != dados:
            falhas.append((nome, "zlib nao leu o que eu escrevi"))
        if deflate.descomprimir(seu) != dados:
            falhas.append((nome, "eu nao li o que o zlib escreveu"))
        print(f"  deflate  {nome:<30} {len(meu):>6}B meu  {len(seu):>5}B zlib"
              + ("  OK" if not falhas or falhas[-1][0] != nome else "  FALHOU"))
    return falhas


def conferir_gzip():
    """Round-trip próprio + dois sentidos vs. gzip, níveis stored e comprimido."""
    falhas = []
    for dados, nome in CASOS:
        meu = gzip_.comprimir(dados)
        if gzip_.descomprimir(meu) != dados:
            falhas.append((nome, "round-trip do proprio gzip"))
        if gzip_stdlib.decompress(meu) != dados:
            falhas.append((nome, "gzip da stdlib nao leu o que eu escrevi"))
        for nivel in (0, 9):   # 0 = stored, 9 = comprimido
            seu = gzip_stdlib.compress(dados, compresslevel=nivel)
            if gzip_.descomprimir(seu) != dados:
                falhas.append((nome, f"eu nao li o que o gzip nivel {nivel} escreveu"))
        print(f"  gzip     {nome:<30} {len(meu):>6}B meu  vs stdlib OK"
              if not falhas or falhas[-1][0] != nome
              else f"  gzip     {nome:<30} FALHOU")
    return falhas


def _round_trip(dados, nome):
    """Meu write + meu read: o teste mais básico e mais importante."""
    try:
        return deflate.descomprimir(deflate.comprimir(dados)) == dados
    except Exception:
        return False


def main():
    print("Prova de interoperabilidade do pacote compressao\n")
    falhas = conferir_deflate() + conferir_gzip()
    print(f"\n  {len(CASOS)} casos · {len(falhas)} falhas")
    if falhas:
        for nome, msg in falhas:
            print(f"    {nome}: {msg}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())