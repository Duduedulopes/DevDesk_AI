"""Testes do pacote `compressao` (RFC 1951/1952) contra a biblioteca padrão.

O valor destes testes é a ponte: cada um roda o meu código contra o
`zlib`/`gzip` do Python. Manualmente, o `provas/conferir_deflate.py`
imprime a mesma prova caso a caso.
"""
import gzip as gzip_stdlib
import sys
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compressao import deflate, gzip_
from compressao.shape import (COMPRIMENTO_POR_CODIGO, DISTANCIA_POR_CODIGO,
                              codigo_comprimento, codigo_distancia)

CASOS = [
    b"",
    b"a",
    b"a" * 5,
    b"a" * 8,
    b"a" * 10,
    b"a" * 258,
    b"ab" * 100,
    b"abcdabcdabcd",
    b"banana banana banana",
    bytes(range(256)),
    bytes(range(256)) * 3,
    b"x" * 300,
    b"a" * 10 + b"b" + b"a" * 20,
]


# --------------------------------------------------------------- deflate

@pytest.mark.parametrize("dados", CASOS, ids=lambda d: f"len{len(d)}")
def test_deflate_round_trip_proprio(dados):
    assert deflate.descomprimir(deflate.comprimir(dados)) == dados


@pytest.mark.parametrize("dados", CASOS, ids=lambda d: f"len{len(d)}")
def test_zlib_le_o_que_eu_escrevo(dados):
    saida = deflate.comprimir(dados)
    assert zlib.decompressobj(-15).decompress(saida) == dados


@pytest.mark.parametrize("dados", CASOS, ids=lambda d: f"len{len(d)}")
def test_eu_leio_o_que_o_zlib_escreve(dados):
    z = zlib.compressobj(level=9, wbits=-15)
    seu = z.compress(dados) + z.flush()
    assert deflate.descomprimir(seu) == dados


def test_descomprimir_ate_devolve_onde_parou():
    """O gzip depende de saber onde o DEFLATE termina para ler o trailer."""
    z = zlib.compressobj(level=9, wbits=-15)
    seu = z.compress(b"abc") + z.flush()
    saida, n = deflate.descomprimir_ate(seu)
    assert saida == b"abc"
    assert n == len(seu)  # sem nada a seguir, o stream ocupa o arquivo todo


def test_descomprimir_ate_para_antes_do_lixo():
    corpo = deflate.comprimir(b"abc") + b"LIXO_TRILHANDO_ATRAS"
    saida, n = deflate.descomprimir_ate(corpo)
    assert saida == b"abc"
    assert n < len(corpo)
    assert corpo[n:] == b"LIXO_TRILHANDO_ATRAS"


def test_rejeitar_tipo_de_bloco_dinamico():
    """BTYPE=10 (árvore transmitida) é declarado não implementado, não
    silenciosamente bugado: melhor um erro claro que um resultado errado."""
    stream = bytes([1, 0b10000000, 0])  # BFINAL=1 + BTYPE=10 (pouco importa o resto)
    with pytest.raises(ValueError):
        deflate.descomprimir(stream)


# ----------------------------------------------------------------- gzip

@pytest.mark.parametrize("dados", CASOS, ids=lambda d: f"len{len(d)}")
def test_gzip_round_trip_proprio(dados):
    assert gzip_.descomprimir(gzip_.comprimir(dados)) == dados


@pytest.mark.parametrize("dados", CASOS, ids=lambda d: f"len{len(d)}")
def test_gzip_stdlib_le_o_que_eu_escrevo(dados):
    assert gzip_stdlib.decompress(gzip_.comprimir(dados)) == dados


@pytest.mark.parametrize("nivel", [0, 9])
@pytest.mark.parametrize("dados", CASOS, ids=lambda d: f"len{len(d)}")
def test_eu_leio_o_que_o_gzip_escreve(dados, nivel):
    seu = gzip_stdlib.compress(dados, compresslevel=nivel)
    assert gzip_.descomprimir(seu) == dados


def test_gzip_reclama_de_nao_gzip():
    with pytest.raises(ValueError):
        gzip_.descomprimir(b"isto nao e um gzip")


def test_gzip_reclama_de_corrupcao_do_corpo():
    """A razão de existir do gzip: corrupção é capturada pelo CRC, não
    devolvida como dados errados."""
    bom = gzip_stdlib.compress(b"corromper isto tem que pegar" * 20)
    ruim = bytearray(bom)
    ruim[20] ^= 0x08
    with pytest.raises(ValueError):
        gzip_.descomprimir(bytes(ruim))


def test_gzip_reclama_de_corrupcao_do_trailer():
    bom = gzip_stdlib.compress(b"corromper o trailer" * 10)
    ruim = bytearray(bom)
    ruim[-1] ^= 0xFF
    with pytest.raises(ValueError):
        gzip_.descomprimir(bytes(ruim))


def test_gzip_reclama_de_truncamento():
    bom = gzip_stdlib.compress(b"truncar tem que doer" * 10)
    with pytest.raises(ValueError):
        gzip_.descomprimir(bom[:-4])


def test_crc32_bate_com_o_zlib():
    """O meu CRC32-tabela tem que dar EXATAMENTE o mesmo inteiro que o
    `zlib.crc32` — a prova de que a tabela foi montada com o polinômio
    certo (0xEDB88320) e o complemento no fim."""
    for dados in (b"", b"a", b"banana", bytes(range(256)) * 5):
        assert gzip_.crc32(dados) == zlib.crc32(dados)


# ---------------------------------------------------------------- shape

def test_cada_comprimento_cai_no_proprio_intervalo():
    for v in range(3, 259):
        codigo, extra = codigo_comprimento(v)
        base, n = COMPRIMENTO_POR_CODIGO[codigo]
        assert base <= v <= base + (1 << n) - 1


def test_cada_distancia_cai_no_proprio_intervalo():
    for v in range(1, 32769):
        codigo, extra = codigo_distancia(v)
        base, n = DISTANCIA_POR_CODIGO[codigo]
        assert base <= v <= base + (1 << n) - 1


def test_comprimento_258_e_o_codigo_285_sem_extra():
    codigo, extra = codigo_comprimento(258)
    assert codigo == 285
    assert extra == 0