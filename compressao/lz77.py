"""LZ77: a janela deslizante que acha repetições antes do Huffman.

Antes de escolher códigos, o DEFLATE tenta expulsar redundância do tipo
"isso já apareceu": um casamento `(tamanho, distância)` diz "copie N bytes,
você está a D de distância atrás". Só o que não casou vira literal.

Duas decisões de implementação merecem anotação:

  JANELA — o DEFLATE limita a janela a 32768 bytes (distância máxima).
  COMPRIMENTO — o DEFLATE corta o match em 258 bytes. Emparelhar mais não
  faz crescer o stream de um jeito honesto: o formato não sabe representar.

  Emparelhamento GREEDY — a cada posição acha o maior match a partir dela
  e segue adiante. Não é o compromisso ótimo global (isso exigiria olhar
  o futuro todo), mas é o algoritmo clássico e didático. Para provar
  que não trapaceia, o descompressor roda sobre qualquer sequência de
  tokens e a prova conferir o round-trip byte a byte.
"""

# Tamanho máximo da janela e de match, conforme o formato.
JANELA = 32768
COMPRIMENTO_MAX = 258
MINIMO = 3  # matches menores que 3 bytes nunca compensam: literal sai mais barato


def _maior_match(dados, pos, inicio_janela):
    """(tamanho, distância) do melhor casamento em `dados[pos:]`.

    Procura em todas as posições candidatas da janela, comparando o máximo
    que o formato permite (258). Como o DEFLATE permite copiar de posições
    à frente quando D é pequeno (o "overlap"), a comparação usa `dados[
    cand + k]` — não limita o match ao início da entrada.
    """
    melhor = (0, 0)  # (tamanho, distância)
    for cand in range(max(inicio_janela, 0), pos):
        k = 0
        while k < COMPRIMENTO_MAX and pos + k < len(dados):
            if dados[cand + k] != dados[pos + k]:
                break
            k += 1
        if k > melhor[0]:
            melhor = (k, pos - cand)
            if k == COMPRIMENTO_MAX:
                break
    return melhor


def codificar(dados):
    """Converte `dados` em tokens LZ77.

    O token de saída é um inteiro 0-255 (literal) ou uma tupla
    `(tamanho, distância)`. Fica fácil de inspecionar à mão — e é essa
    lista que o compactador de DEFLATE transforma em códigos.
    """
    dados = bytes(dados)
    tokens = []
    pos = 0
    n = len(dados)
    while pos < n:
        inicio_janela = pos - JANELA
        tamanho, distancia = _maior_match(dados, pos, inicio_janela)
        if tamanho >= MINIMO:
            tokens.append((tamanho, distancia))
            pos += tamanho
        else:
            tokens.append(dados[pos])
            pos += 1
    return tokens


def decodificar(tokens, nbytes=None):
    """Reconstrói os dados originais a partir dos tokens.

    Desenrola o overlap sem trapaça: copia byte a byte da posição `pos - d`,
    que já foi preenchida nas iterações anteriores do loop (é exatamente
    assim que um compressor pode "se copiar à frente").
    """
    saida = bytearray()
    for tok in tokens:
        if isinstance(tok, int):  # literal
            saida.append(tok)
        else:
            tamanho, distancia = tok
            if distancia < 1:
                raise ValueError("distância 0 em token LZ77; token inválido")
            if distancia > len(saida):
                raise ValueError(
                    f"distância {distancia} maior que o já decodificado; "
                    "token inválido")
            for _ in range(tamanho):
                saida.append(saida[-distancia])
    resultado = bytes(saida)
    if nbytes is not None and len(resultado) != nbytes:
        raise ValueError(f"esperava {nbytes} bytes, saiu {len(resultado)}")
    return resultado