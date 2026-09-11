"""Parâmetros do LZ77 dentro do DEFLATE: comprimento e distância ↔ código.

O LZ77 não grava "copie 20 bytes do passado" no stream: o protocolo limita
o vocabulário a códigos. Cada comprimento e cada distância vira um código
da tabela + "extra bits" (quando o intervalo do código tem mais de um
valor). RFC 1951 §3.2.5 define as duas tabelas exatas — é isso que permite
ao leitor saber quantos bits extra está por vir sem precisar de outro canal.

Regras internas deste módulo:
  COMPRIMENTO máximo 258 (DEFLATE não manda além disso; o casador deve
                      respeitar).
  Código 285 é reservado: representa 258 puro, sem extra bits.
  DISTÂNCIA máxima 32768 (janela máxima do DEFLATE).
"""

# (código, base, extra) para comprimentos: o código cobre [base, base+2^extra).
# RFC 1951 §3.2.5: 257-264 cobrem 3-10 sem extra; os extras começam no 265.
COMPRIMENTOS = [
    # código   base   extra    # intervalo
    (257, 3, 0),                # 3
    (258, 4, 0),                # 4
    (259, 5, 0),                # 5
    (260, 6, 0),                # 6
    (261, 7, 0),                # 7
    (262, 8, 0),                # 8
    (263, 9, 0),                # 9
    (264, 10, 0),               # 10
    (265, 11, 1),               # 11-12
    (266, 13, 1),               # 13-14
    (267, 15, 1),               # 15-16
    (268, 17, 1),               # 17-18
    (269, 19, 2),               # 19-22
    (270, 23, 2),               # 23-26
    (271, 27, 2),               # 27-30
    (272, 31, 2),               # 31-34
    (273, 35, 3),               # 35-42
    (274, 43, 3),               # 43-50
    (275, 51, 3),               # 51-58
    (276, 59, 3),               # 59-66
    (277, 67, 4),               # 67-82
    (278, 83, 4),               # 83-98
    (279, 99, 4),               # 99-114
    (280, 115, 4),              # 115-130
    (281, 131, 5),              # 131-162
    (282, 163, 5),              # 163-194
    (283, 195, 5),              # 195-226
    (284, 227, 5),              # 227-257
]
COMPRIMENTO_MAX = 258

# (código, base, extra) para distâncias, onde a base é a menor do intervalo.
DISTANCIAS = [
    (0, 1, 0),                  # 1
    (1, 2, 0),                  # 2
    (2, 3, 0),                  # 3
    (3, 4, 0),                  # 4
    (4, 5, 1),                  # 5-6
    (5, 7, 1),                  # 7-8
    (6, 9, 2),                  # 9-12
    (7, 13, 2),                 # 13-16
    (8, 17, 3),                 # 17-24
    (9, 25, 3),                 # 25-32
    (10, 33, 4),                # 33-48
    (11, 49, 4),                # 49-64
    (12, 65, 5),                # 65-96
    (13, 97, 5),                # 97-128
    (14, 129, 6),               # 129-192
    (15, 193, 6),               # 193-256
    (16, 257, 7),               # 257-384
    (17, 385, 7),               # 385-512
    (18, 513, 8),               # 513-768
    (19, 769, 8),               # 769-1024
    (20, 1025, 9),              # 1025-1536
    (21, 1537, 9),              # 1537-2048
    (22, 2049, 10),             # 2049-3072
    (23, 3073, 10),             # 3073-4096
    (24, 4097, 11),             # 4097-6144
    (25, 6145, 11),             # 6145-8192
    (26, 8193, 12),             # 8193-12288
    (27, 12289, 12),            # 12289-16384
    (28, 16385, 13),            # 16385-24576
    (29, 24577, 13),            # 24577-32768
]
DISTANCIA_MAX = 32768

# Índices invertidos para a leitura: do código direto para (base, extra).
COMPRIMENTO_POR_CODIGO = {codigo: (base, extra) for codigo, base, extra in COMPRIMENTOS}
COMPRIMENTO_POR_CODIGO[285] = (258, 0)  # o DEFLATE reserva 285 como "258 puro"

DISTANCIA_POR_CODIGO = {codigo: (base, extra) for codigo, base, extra in DISTANCIAS}


def codigo_comprimento(valor):
    """(código, extra_bits) para um comprimento de match, ou None se inválido."""
    if valor < 3 or valor > COMPRIMENTO_MAX:
        return None
    if valor == 258:
        return 285, 0
    for codigo, base, extra in COMPRIMENTOS:
        if base <= valor <= base + 2 ** extra - 1:
            return codigo, valor - base
    return None


def codigo_distancia(valor):
    """(código, extra_bits) para uma distância de match, ou None se inválido."""
    if valor < 1 or valor > DISTANCIA_MAX:
        return None
    for codigo, base, extra in DISTANCIAS:
        if base <= valor <= base + 2 ** extra - 1:
            return codigo, valor - base
    return None


def valor_comprimento(codigo, extra):
    """Comprimento devolvido por (código, valor de extra bits)."""
    base, n = COMPRIMENTO_POR_CODIGO[codigo]
    return base + extra


def valor_distancia(codigo, extra):
    """Distância devolvida por (código, valor de extra bits)."""
    base, n = DISTANCIA_POR_CODIGO[codigo]
    return base + extra