"""DEFLATE: o formato da RFC 1951, picado no que o formato realmente é.

O stream é uma sequência de blocos. Cada bloco começa com 3 bits:
  BFINAL  (1 bit)  — 1 quando é o último bloco;
  BTYPE   (2 bits) — 00 = stored, 01 = Huffman fixo, 10 = Huffman dinâmico.

Decisões deste programa:

  SÓ STORED E FIXO — o BTYPE=10 (árvore dinâmica transmitida) é uma
  otimização de tamanho sobre o fixo; a forma de ler e escrever a corrente
  é a mesma. O fixo já é 100% interoperável com `zlib` e `gzip`.

  UM BLOCO POR STREAM — o compressor decide entre stored e fixed olhando
  qual coube em menos bytes e escreve um ÚNICO bloco (BFINAL=1). O blog é
  um compromisso legítimo do formato: quem lê aceita N blocos; quem escreve
  é o dono da estratégia. Simplifica demais a didática.

  ESCOLHA HONESTA — se o fixed for maior que o dado cru (dado aleatório,
  por exemplo), gravamos stored. Comprimir não pode virar inchaço.
"""

from .bitio import BitWriter, BitReader
from . import huffman
from . import lz77
from . import shape

STORED, FIXO = 0b00, 0b01

FIM_DE_BLOCO = 256          # símbolo de fim de bloco na tabela litlen
PRIMEIRO_CODIGO_COMPRIMENTO = 257  # onde os comprimentos começam na tabela


def _valor_cruzado(valor, base, extra):
    """Extra bits (LSB-first) do valor, dentro da base do código."""
    return valor - base


def comprimir(dados):
    """Comprime `dados` (bytes) no menor stream DEFLATE dos dois blocos.

    Monta os dois candidatos (stored e fixed) e devolve o menor. O tamanho
    honesto de um stored block é `len(dados) + 5` (cabeçalho de 5 bytes);
    o do fixed é medido de verdade depois de escrito.
    """
    dados = bytes(dados)

    stored = _bloco_stored(dados)
    if len(dados) < 4:  # 4 bytes mal cabem no cabeçalho do bloco
        return stored

    fixed = _bloco_fixo(dados)
    return fixed if len(fixed) < len(stored) else stored


def _bloco_stored(dados):
    """Bloco stored (BTYPE=00): bytes crus, com LEN/NLEN para conferir.

    RFC 1951 §3.2.3: DEPOIS do header de 3 bits, alinha no byte e manda
    LEN (2 bytes LE), NLEN (2 bytes, o complemento de um de LEN), e os
    bytes. O leitor confere NLEN para pegar corrupção.
    """
    es = BitWriter()
    es.bit(1)                  # BFINAL = 1 (bloco único)
    es.escrever(STORED, 2, primeiro_msb=False)  # BTYPE, LSB first
    es.alinhar()
    n = len(dados)
    # LEN, NLEN e os dados são bytes crus little-endian, não bits.
    cabecalho = n.to_bytes(2, "little") + (~n & 0xFFFF).to_bytes(2, "little")
    return es.finalizar() + cabecalho + dados


def _bloco_fixo(dados):
    """Bloco Huffman fixo (BTYPE=01) para `dados`, com LZ77 dentro.

    Cada token LZ77 vira:
      literal        → código litlen do byte (símbolo 0-255)
      (len, dist)    → código litlen do len + extra + código dist + extra
    termina com o símbolo FIM_DE_BLOCO (256).
    """
    es = BitWriter()
    es.bit(1)                                    # BFINAL = 1
    es.escrever(FIXO, 2, primeiro_msb=False)     # BTYPE
    for tok in lz77.codificar(dados):
        if isinstance(tok, int):                 # literal
            codigo, n = huffman.FIXA_LITLEN[tok]
            es.escrever(codigo, n, primeiro_msb=True)
        else:
            tamanho, distancia = tok
            _escrever_comprimento(es, tamanho)
            _escrever_distancia(es, distancia)
    codigo, n = huffman.FIXA_LITLEN[FIM_DE_BLOCO]
    es.escrever(codigo, n, primeiro_msb=True)
    return es.finalizar()


def _escrever_comprimento(es, tamanho):
    """Codifica o comprimento de um match no stream (código + extra)."""
    codigo, extra_valor = shape.codigo_comprimento(tamanho)
    base, extra_n = shape.COMPRIMENTO_POR_CODIGO[codigo]
    c, n = huffman.FIXA_LITLEN[codigo]
    es.escrever(c, n, primeiro_msb=True)         # código do comprimento
    if extra_n:                                  # extra bits LSB-first
        es.escrever(extra_valor, extra_n, primeiro_msb=False)


def _escrever_distancia(es, distancia):
    """Codifica a distância de um match no stream (código 5 bits + extra)."""
    codigo, extra_valor = shape.codigo_distancia(distancia)
    base, extra_n = shape.DISTANCIA_POR_CODIGO[codigo]
    c, n = huffman.FIXA_DISTANCIA[codigo]
    es.escrever(c, n, primeiro_msb=True)         # código da distância
    if extra_n:                                  # extra bits LSB-first
        es.escrever(extra_valor, extra_n, primeiro_msb=False)


def descomprimir(dados):
    """Reconstrói os bytes originais de um stream DEFLATE.

    Lê blocos até BFINAL=1. Para cada bloco, desempacota stored ou fixed.
    Acumula tudo numa saída única — e devolve bytes exatos (`zlib` e
    `gzip` da biblioteca padrão usam exatamente esse fluxo).
    """
    saida, _n = _descomprimir_ate(dados)
    return saida


def descomprimir_ate(dados):
    """Como `descomprimir`, mas devolve (bytes, bytes-consumidos).

    O gzip escreve o stream DEFLATE SEM marcador de fim e em seguida o
    trailer (CRC32 + ISIZE): quem lê o .gz precisa saber onde o DEFLATE
    acabou para achar o trailer. `bytes-consumidos` é esse número —
    arredondando o meio-byte final para cima, porque o trailer começa no
    byte seguinte.
    """
    return _descomprimir_ate(dados)


def _descomprimir_ate(dados):
    leitor = BitReader(dados)
    saida = bytearray()
    fim = False
    while not fim:
        bfinal = leitor.bit()
        if bfinal is None:
            break
        btype_raw = leitor.escrever(2, primeiro_msb=False)
        if btype_raw in (0b10, 0b11):
            raise ValueError(f"BTYPE={btype_raw:02b} (árvore dinâmica) não "
                             "implementado; o fixo já cobre o formato")
        if btype_raw == STORED:
            _ler_stored(leitor, saida)
        else:
            _ler_fixo(leitor, saida)
        fim = bool(bfinal)
    return bytes(saida), leitor.posicao_bytes()


def _ler_stored(leitor, saida):
    """Desempacota um bloco stored no `saida` e confere NLEN."""
    leitor.alinhar()
    if len(leitor.restantes()) < 4:
        raise ValueError("bloco stored truncado: faltam LEN/NLEN")
    cabecalho = leitor.bytes_brutos(4)
    n = int.from_bytes(cabecalho[0:2], "little")
    nlen = int.from_bytes(cabecalho[2:4], "little")
    if nlen != (~n & 0xFFFF):
        raise ValueError("NLEN não bate com LEN: stream corrompido")
    corpo = leitor.bytes_brutos(n)
    if len(corpo) < n:
        raise ValueError("bloco stored declara mais bytes que o stream")
    saida.extend(corpo)


def _ler_fixo(leitor, saida):
    """Desempacota um bloco Huffman fixo no `saida`."""
    while True:
        simbolo = _ler_simbolo(leitor, huffman.INDICE_FIXO_LITLEN)
        if simbolo == FIM_DE_BLOCO:
            return
        if simbolo < 256:
            saida.append(simbolo)
            continue
        # símbolo de comprimento: agora vem a distância (também Huffman fixa)
        base, extra_n = shape.COMPRIMENTO_POR_CODIGO[simbolo]
        extra = leitor.escrever(extra_n, primeiro_msb=False)
        tamanho = base + extra
        dist_simbolo = _ler_simbolo(leitor, huffman.INDICE_FIXO_DISTANCIA)
        base_d, extra_d_n = shape.DISTANCIA_POR_CODIGO[dist_simbolo]
        extra_d = leitor.escrever(extra_d_n, primeiro_msb=False)
        distancia = base_d + extra_d
        _desenrolar(saida, tamanho, distancia)


def _ler_simbolo(leitor, indice):
    """Lê um símbolo Huffman, bit a bit, sem saber o comprimento antes.

    Acumula `v = v*2 + bit` (a ordem da RFC: o primeiro bit é o MSB do
    código). Como os códigos são sem prefixo, a primeira chave que casar
    é a certa — e o `(v, n)` da chave é exatamente o código gravado.
    """
    n = 1
    v = 0
    while n <= 15:
        b = leitor.bit()
        if b is None:
            raise EOFError("fim do stream antes de fechar o símbolo")
        v = (v << 1) | b
        if (v, n) in indice:
            return indice[(v, n)]
        n += 1
    raise ValueError("código Huffman sem fim válido; stream corrompido")


def _desenrolar(saida, tamanho, distancia):
    """Copia `tamanho` bytes, `distancia` para trás, um a um (overlap ok)."""
    if distancia < 1 or distancia > len(saida):
        raise ValueError("match aponta para fora da saída; stream corrompido")
    for _ in range(tamanho):
        saida.append(saida[-distancia])