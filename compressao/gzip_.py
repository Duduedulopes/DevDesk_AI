"""GZIP (RFC 1952): o envelope que deu nome à extensão `.gz`.

O DEFLATE entrega a corrente comprimida, mas nada sobre o dono: quantos
bytes eram o original, se o original chegou inteiro. O gzip é esse
markup — um cabeçalho de 10 bytes na frente e um trailer (CRC32 + ISIZE)
no fim, com o stream DEFLATE no meio.

Duas decisões deste módulo:

  CABEÇALHO MÍNIMO — o gzip permite campos extra (nome, comentário,
  carimbo de tempo...). Gravamos só os 10 bytes obrigatórios, FLG=0, e na
  leitura respeitamos os campos SE aparecerem (pular é obrigatório). A
  regra de ouro: quem escreve é dono; quem lê tem que aguentar tudo.

  CRC32 DO ZERO — o `zlib` da biblioteca padrão já tem `crc32()`, mas
  este pacote inteiro existe para mostrar o formato funcionando com a
  mão na massa. Então o CRC aqui é uma tabela de 256 entradas construída
  na primeira chamada — a versão posta-crème do algoritmo (mesma conta,
  tabela pré-calculada em vez do loop bit a bit).
"""

from . import deflate
from .bitio import BitReader

MAGIC = b"\x1f\x8b"          # identificação do formato
MEXODO = 8                    # método de compressão: 8 = DEFLATE

_CABECALHO = MAGIC + bytes([MEXODO, 0])   # + MTIME(4) + XFL + OS = 10 bytes


def comprimir(dados):
    """Comprime `dados` e devolve um membro gzip completo (`.gz`).

    Cabeçalho de 10 bytes (magic, método, FLG=0, MTIME=0, XFL, OS=3),
    stream DEFLATE, e o trailer: CRC32 e ISIZE, ambos little-endian.
    """
    dados = bytes(dados)
    # MTIME 4 bytes (0 = sem carimbo), XFL 1, OS 1 (3 = Unix)
    cabecalho = _CABECALHO + (0).to_bytes(4, "little") + b"\x00\x03"
    corpo = deflate.comprimir(dados)
    trailer = crc32(dados).to_bytes(4, "little") \
        + (len(dados) % (1 << 32)).to_bytes(4, "little")
    return cabecalho + corpo + trailer


def descomprimir(arquivo):
    """Reconstrói os bytes originais de um membro gzip e CONFeRE o trailer.

    Pula o cabeçalho (e os campos extra, se existirem), acha onde o
    DEFLATE termina e lê CRC32 + ISIZE. Não confia em quem escreveu:
    recalcula o CRC e confere o tamanho — arquivo capenga vira erro, não
    dado silenciosamente errado.
    """
    arquivo = bytes(arquivo)
    leitor = BitReader(arquivo)
    if arquivo[:2] != MAGIC:
        raise ValueError("não é gzip: magic 1f 8b ausente")
    if arquivo[2] != MEXODO:
        raise ValueError(f"método {arquivo[2]} não é o DEFLATE ({MEXODO})")

    # Cabeçalho fixo: magic(2) método(1) FLG(1) MTIME(4) XFL(1) OS(1)
    flg = arquivo[3]
    pos = 10
    pos = _pular_extra(arquivo, flg, pos)

    # Stream DEFLATE: descomprime e descobre em que byte o trailer começa.
    corpo = arquivo[pos:]
    saida, consumidos = deflate.descomprimir_ate(corpo)
    fim = pos + consumidos

    if fim + 8 > len(arquivo):
        raise ValueError("gzip truncado: falta o trailer (CRC32 + ISIZE)")
    crc_lido = int.from_bytes(arquivo[fim:fim + 4], "little")
    isize_lido = int.from_bytes(arquivo[fim + 4:fim + 8], "little")

    # Conferir é a alma do formato: o gzip existe para pegar corrupção.
    crc_certo = crc32(saida)
    if crc_lido != crc_certo:
        raise ValueError(f"CRC32 não confere: lido {crc_lido:08x}, "
                         f"calculado {crc_certo:08x} — arquivo corrompido")
    isize_certo = len(saida) % (1 << 32)
    if isize_lido != isize_certo:
        raise ValueError(f"ISIZE não confere: lido {isize_lido}, "
                         f"executado {isize_certo} — arquivo corrompido")
    return saida


def _pular_extra(arquivo, flg, pos):
    """Avança sobre os campos opcionais do cabeçalho (RFC 1952 §2.3.1.1).

    FLG decide o que existe; a ordem é fixa: FEXTRA, FNAME, FCOMMENT,
    FHCRC. FTEXT (bit 0) é só uma etiqueta e não tem campo nenhum — o
    escritor que declare FTEXT está só dizendo que o dono é texto.
    """
    if flg & 0b100:    # FEXTRA: 2 bytes de comprimento + o campo
        if pos + 2 > len(arquivo):
            raise ValueError("gzip truncado: FEXTRA sem comprimento")
        n = int.from_bytes(arquivo[pos:pos + 2], "little")
        if pos + 2 + n > len(arquivo):
            raise ValueError("gzip truncado: FEXTRA menor que o declarado")
        pos += 2 + n
    for bit in (0b1000, 0b10000):   # FNAME, FCOMMENT: strings NUL-terminadas
        if flg & bit:
            fim = arquivo.find(b"\x00", pos)
            if fim < 0:
                raise ValueError("gzip truncado: campo de texto sem fim")
            pos = fim + 1
    if flg & 0b10:     # FHCRC: 2 bytes; ao ler, o CRC do cabeçalho
        # só interessa a quem confere o cabeçalho — nós conferimos o dono.
        pos += 2
    return pos


def crc32(dados):
    """CRC-32 (IEEE, polinômio 0xEDB88320) dos `dados`, sem zlib.

    O gzip manda o valor pronto e o leitor tem que recalcular para
    conferir — é esse o desejo reverso do formulário. O polinômio refletido
    0xEDB88320 é a constante do formato; o algoritmo é o clássico de
    tabela de 256 entradas, pré-computada na primeira chamada.
    """
    dados = bytes(dados)
    if not hasattr(crc32, "tabela"):
        tabela = []
        for n in range(256):
            c = n
            for _ in range(8):
                c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
            tabela.append(c)
        crc32.tabela = tabela
    crc = 0xFFFFFFFF
    for byte in dados:
        crc = crc32.tabela[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF