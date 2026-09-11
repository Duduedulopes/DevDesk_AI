"""`compressao` — DEFLATE (RFC 1951) e gzip (RFC 1952) da mão na massa.

Pacote didático: cada formato implementado do zero, sem tocar na
biblioteca padrão, apenas para mostrar que o formato BATE por si só.
Os módulos em camadas:

  bitio.py     — empacotamento LSB-first dos bits e alinhamento a byte
  lz77.py      — a janela deslizante: acha repetições antes do Huffman
  huffman.py   — códigos canônicos e as tabelas fixas (RFC §3.2.6)
  shape.py     — comprimento/distância ↔ código + extra bits (§3.2.5)
  deflate.py   — o formato RFC 1951: blocos stored e Huffman fixo
  gzip_.py     — o envelope RFC 1952: cabeçalho, CRC32 e ISIZE

O teste de verdade é a interoperabilidade: o que esta pasta escreve, o
`zlib` e o `gzip` da biblioteca padrão leem; o que eles escrevem, isto
lê de volta byte a byte. `provas/conferir_deflate.py` roda essa prova.
"""

from . import bitio, deflate, gzip_, huffman, lz77, shape
from .deflate import comprimir, descomprimir
from .gzip_ import crc32

_liga_tudo = (bitio, deflate, gzip_, huffman, lz77, shape)

__all__ = ["comprimir", "descomprimir", "crc32", "deflate", "gzip_",
           "lz77", "huffman", "shape", "bitio"]