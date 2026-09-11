"""Empacotador/leitor de bits: a fundação de qualquer corrente deflate.

O RFC 1951 é explícito sobre os dois sentidos de bits na mesma corrente:

  1. Toda a corrente é empacotada em bytes **do bit menos significativo
     pro mais** (bit 0 do byte é o primeiro bit do stream). Isso vale para
     tudo — códigos Huffman, extra bits, cabeçalhos. Não há exceção.

  2. DENTRO do que se escreve em campo, os sentidos diferem:
     - Código Huffman: o PRIMEIRO bit gravado é o bit mais significativo
       do código (é assim que o descompressor canônico caminha a tabela).
     - Extra bits de comprimento/distância: o primeiro gravado é o bit
       MENOS significativo do número.

Então o que muda é a *ordem* em que os bits do valor entram no byte,
nunca o empacotamento do byte. Escrever o código 0x30 (8 bits, 00110000)
significa gravar os bits 0,0,1,1,0,0,0,0 — o primeiro a entrar é o MSB.
O leitor faz o caminho inverso: lê bits e os acumula como `v = v*2 + b`,
devolvendo 0x30 de volta (a tabela canônica casa exatamente).

O alinhamento a byte (`alinhar`) é a única operação que insere lixo:
zeras até fechar o byte, usado SÓ no bloco *stored* (RFC 1951 §3.2.3).
"""


class BitWriter:
    """Empacota bits em bytes, LSB-first, sem armazenar preenchimento."""

    def __init__(self):
        self._fluxo = bytearray()   # bytes já fechados
        self._byte = 0              # byte parcial sendo montado
        self._pos = 0               # próximo bit: 0 = LSB do byte parcial

    def bit(self, valor):
        """Grava um bit (0/1) na posição LSB-first seguinte."""
        valor = int(valor) & 1
        self._byte |= valor << self._pos
        self._pos += 1
        if self._pos == 8:
            self._fluxo.append(self._byte)
            self._byte = 0
            self._pos = 0

    def escrever(self, valor, n, *, primeiro_msb=True):
        """Grava `n` bits do valor na ordem pedida.

        `primeiro_msb=True`  — códigos Huffman: grama do MSB pro LSB.
        `primeiro_msb=False` — extra bits: grama do LSB pro MSB.
        """
        if primeiro_msb:
            for i in range(n - 1, -1, -1):
                self.bit((valor >> i) & 1)
        else:
            for i in range(n):
                self.bit((valor >> i) & 1)

    def alinhar(self):
        """Preenche com zeros até fechar o byte — só para bloco *stored*."""
        while self._pos:
            self.bit(0)

    def finalizar(self):
        """Devolve a corrente empacotada; byte parcial entra como está.

        O DEFLATE e o gzip NÃO preenchem o fim da corrente: os bits que
        sobraram no último byte são simplesmente ignorados pelo leitor.
        """
        if self._pos:
            self._fluxo.append(self._byte)
            self._byte = 0
            self._pos = 0
        return bytes(self._fluxo)


class BitReader:
    """Lê uma corrente deflate bit a bit, da mesma forma que foi escrita."""

    def __init__(self, dados):
        self._dados = bytes(dados)
        self._i = 0     # byte atual
        self._pos = 0   # próximo bit dentro do byte (0 = LSB)

    def findo(self):
        return self._i >= len(self._dados) and self._pos >= 8

    def bit(self):
        """Lê um bit (0/1); levanta EOFError se a corrente acabou."""
        if self._i >= len(self._dados):
            raise EOFError("fim da corrente deflate batendo antes do previsto")
        valor = (self._dados[self._i] >> self._pos) & 1
        self._pos += 1
        if self._pos == 8:
            self._i += 1
            self._pos = 0
        return valor

    def escrever(self, n, *, primeiro_msb=True):
        """Lê `n` bits e devolve o inteiro.

        `primeiro_msb=True`  — o primeiro bit lido vira o MSB (Huffman).
        `primeiro_msb=False` — o primeiro bit lido vira o LSB (extra).
        """
        v = 0
        for _ in range(n):
            b = self.bit()
            if primeiro_msb:
                v = (v << 1) | b
            else:
                if b:
                    v |= 1 << _
        return v

    def alinhar(self):
        """Descarta os bits até o byte seguinte (leitura de bloco *stored*)."""
        while self._pos:
            self.bit()

    def restantes(self):
        """Devolve do byte atual até o fim, como bytes crus.

        Usado pelo bloco *stored* depois de `alinhar` — quando se sabe que
        estamos exatamente em um limite de byte e o resto são bytes crus.
        """
        if self._pos:
            raise ValueError("restantes() pedido no meio de um byte; "
                             "chame o alinhador antes")
        return bytes(self._dados[self._i:])

    def bytes_brutos(self, n):
        """Lê e devolve os próximos `n` bytes crus, avançando.

        Igual a `restantes` mas conta exatamente quanto leu — usado quando
        o stream não é o último dado do arquivo (o gzip manda o trailer
        logo depois do DEFLATE, e `restantes` engoliria o trailler junto).
        Exige limite de byte, como `restantes`.
        """
        if self._pos:
            raise ValueError("bytes_brutos() pedido no meio de um byte; "
                             "chame o alinhador antes")
        fim = self._i + n
        corpo = bytes(self._dados[self._i:fim])
        if len(corpo) < n:
            raise EOFError("fim da corrente batendo antes do previsto")
        self._i = fim
        return corpo

    def posicao_bytes(self):
        """Quantos bytes a leitura andou, arredondando o meio-byte para cima.

        Um stream DEFLATE termina sem alinhar: o último byte pode vir pela
        metade. O que vem depois (no gzip, o trailer) começa no PRÓXIMO
        byte — então o meio-byte conta como cheio.
        """
        return self._i + 1 if self._pos else self._i