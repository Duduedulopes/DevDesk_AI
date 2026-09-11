"""Códigos canônicos do DEFLATE e as tabelas fixas do RFC 1951 §3.2.6.

O formato aceita DOIS tipos de bloco Einstein: o *stored* (bytes crus) e o
comprimido. O comprimido usa códigos Huffman — e a forma que a RFC manda
escrevê-los é a **canônica**: os códigos são números sem prefixo, em ordem
crescente de comprimento e, dentro do mesmo comprimento, em ordem crescente
de símbolo. A maior vantagem didática da versão canônica é que o
decodificador NÃO precisa de árvore: basta conhecer a ordem.

Há dois conjuntos:
  COM_ARVORES_FIXAS — o RFC 1951 define os comprimentos de TODOS os símbolos
                      de uma vez (não manda a tabela no stream). É o bloco
                      `BTYPE=01`. Simples, mas não adapta a distribuição.
  COM_ARVORES_DINAMICAS — o compressor escolhe os comprimentos, e o protocolo
                      os transmite (`BTYPE=10`). Aqui NÃO implementamos: o
                      código fixo já reproduz o formato, e o ganho dinâmico
                      é uma otimização que não muda a forma de ler/escrever
                      a corrente.

Tabelas fixas (RFC 1951 §3.2.6), os códigos são dados explicitamente:

  símbolos 0-143   → comprimento 8
  símbolos 144-255 → comprimento 9
  símbolos 256-279 → comprimento 7
  símbolos 280-287 → comprimento 8

E os 32 códigos de distância são todos de comprimento 5.
"""


def _codigos_por_comprimento(comprimentos):
    """Converte {símbolo: comprimento} no dicionário {símbolo: (código, n)}.

    A atribuição canônica: caminha os símbolos em ordem crescente de
    comprimento, depois crescente de símbolo (ordem estável), somando 1 ao
    código a cada passo e deslocando `n` bits quando o comprimento muda.
    """
    pares = sorted(comprimentos.items(), key=lambda p: (p[1], p[0]))
    codigo = 0
    anterior = 0
    tabela = {}
    for simbolo, n in pares:
        codigo <<= n - anterior
        tabela[simbolo] = (codigo, n)
        codigo += 1
        anterior = n
    return tabela


def tabela_fixa_litlen():
    """{símbolo: (código, n)} para literais/comprimentos do bloco fixo."""
    comprimentos = {}
    for s in range(0, 144):
        comprimentos[s] = 8
    for s in range(144, 256):
        comprimentos[s] = 9
    for s in range(256, 280):
        comprimentos[s] = 7
    for s in range(280, 288):
        comprimentos[s] = 8
    return _codigos_por_comprimento(comprimentos)


def tabela_fixa_distancia():
    """{código: (código, n)} para os 32 códigos de distância, sempre 5 bits.

    Como todos têm o mesmo comprimento, o código canônico do código de
    distância é o próprio número: 0→0, 1→1, ..., 31→31.
    """
    return {c: (c, 5) for c in range(32)}


def montar_indice(comprimentos):
    """Inverte a tabela para decodificação: {(código, n): símbolo}.

    O leitor acumula bits como `v = v*2 + bit` (MSB primeiro, que é a
    ordem da RFC). A cada bit, procura `(v, comprimento)`. Como os códigos
    são sem prefixo, achar é garantido — e a chave casa exatamente com o
    `(código, n)` que `_codigos_por_comprimento` atribuiu.
    """
    tabela = _codigos_por_comprimento(comprimentos)
    return {(c, n): s for s, (c, n) in tabela.items()}


# Tabelas fixas pré-computadas, uma única vez (são constantes do protocolo).
FIXA_LITLEN = None
FIXA_DISTANCIA = None
INDICE_FIXO_LITLEN = None
INDICE_FIXO_DISTANCIA = None


def _inicializar():
    global FIXA_LITLEN, FIXA_DISTANCIA, INDICE_FIXO_LITLEN, INDICE_FIXO_DISTANCIA
    litlen = {}
    for s in range(0, 144):
        litlen[s] = 8
    for s in range(144, 256):
        litlen[s] = 9
    for s in range(256, 280):
        litlen[s] = 7
    for s in range(280, 288):
        litlen[s] = 8
    FIXA_LITLEN = _codigos_por_comprimento(litlen)
    FIXA_DISTANCIA = _codigos_por_comprimento({c: 5 for c in range(32)})
    INDICE_FIXO_LITLEN = {(c, n): s for s, (c, n) in FIXA_LITLEN.items()}
    INDICE_FIXO_DISTANCIA = {(c, n): s for s, (c, n) in FIXA_DISTANCIA.items()}


_inicializar()