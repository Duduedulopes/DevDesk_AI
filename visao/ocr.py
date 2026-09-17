# -*- coding: utf-8 -*-
"""LER AS LETRAS DE UM PRINT — e por que este OCR é pequeno de propósito.

O caso que ele resolve é o print de terminal e de janela de programa:
fonte MONOESPAÇADA, alto contraste, sem rotação, sem perspectiva, sem
letra cursiva. É o caso mais fácil que OCR tem, e é exatamente o que cai
aqui — print do erro, print do build, print da tela travada.

E ele é pequeno porque o problema é pequeno. Um OCR de propósito geral
tem de lidar com foto torta de papel amassado; este só precisa de uma
grade.

    binarizar → achar as FAIXAS de texto → medir o PASSO da grade
              → fatiar em células → a rede diz que letra é cada uma

O QUE A MEDIÇÃO DEU, NO PRINT REAL DO EDUARDO (1903×1012)

    glifo     9 px de largura
    célula   11 px de passo    (22 = duas células, ou seja um espaço)
    tinta     1,3% dos pixels; acima de 160 de brilho, só 0,10%

POR QUE O PASSO É MEDIDO E NÃO FIXO

Porque 11 px é o passo NAQUELE print, com aquele zoom, naquele monitor.
O mesmo terminal num monitor 4K dá 22. Fixar o número aqui faria o
leitor funcionar num computador e falhar no seguinte, sem dizer por quê.
O histograma dos começos de glifo entrega o passo de graça.

A CHUVA DE LETRAS É O INIMIGO DESTE ARQUIVO

O painel do DevDesk tem centenas de caracteres caindo ao fundo, fracos e
em posições aleatórias. Eles são texto de verdade — um OCR ingênuo lê
todos e devolve lixo. O que os separa não é o brilho (embora ajude): é
que texto de VERDADE se alinha em LINHA, e chuva não. Por isso a faixa
tem de ter densidade mínima e altura plausível para ser aceita.
"""
import numpy as np

# uma célula vira sempre este tamanho antes de ir para a rede, para que o
# mesmo modelo sirva a prints de zoom diferente
CELULA_L, CELULA_A = 12, 20

# abaixo disto uma faixa é chuva, não linha de texto
MIN_TINTA_NA_LINHA = 0.02       # 2% das colunas da faixa com tinta
MIN_ALTURA, MAX_ALTURA = 6, 60  # px


def cinza(imagem):
    """A imagem em cinza, 0..255, como matriz."""
    a = np.asarray(imagem, dtype=float)
    if a.ndim == 3:
        # o canal alfa não é luz: um PNG de tela vem RGBA e incluí-lo na
        # média escurece tudo por igual, jogando o limiar para baixo
        a = a[:, :, :3]
        a = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    return a


def limiar_de_otsu(a):
    """O corte entre fundo e tinta, escolhido pelo próprio histograma.

    Otsu procura o corte que deixa os dois lados o mais "apertados"
    possível. Num print de terminal isso cai naturalmente entre o preto do
    fundo e o verde da letra, sem eu escolher número nenhum — e escolher
    à mão seria acertar neste print e errar no próximo.
    """
    h = np.bincount(a.astype(np.uint8).ravel(), minlength=256).astype(float)
    total = h.sum()
    if total == 0:
        return 128.0
    p = h / total
    niveis = np.arange(256)
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * niveis)
    mt = m0[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        entre = (mt * w0 - m0) ** 2 / (w0 * (1 - w0))
    entre[~np.isfinite(entre)] = -1
    return float(np.argmax(entre))


def binarizar(imagem, limiar=None):
    """True onde há tinta. Detecta sozinha se o texto é claro ou escuro."""
    a = cinza(imagem)
    t = limiar_de_otsu(a) if limiar is None else limiar
    claro = (a > t)
    # TEXTO CLARO NO ESCURO ou escuro no claro? Quem for MINORIA é a
    # tinta. Um print de terminal é 98% fundo; um print do Word é 95%
    # papel. Contar resolve os dois sem um botão que a pessoa tenha que
    # saber apertar.
    return claro if claro.mean() < 0.5 else ~claro


# ══════════════════════════════════════════════════════════════════════
#  AS FAIXAS DE TEXTO
# ══════════════════════════════════════════════════════════════════════
def faixas_de_texto(tinta, min_tinta=MIN_TINTA_NA_LINHA):
    """[(y0, y1)] — as bandas horizontais que parecem linha de texto.

    ACHA PELO CORPO E CRESCE ATÉ AS PONTAS. São duas perguntas
    diferentes com respostas diferentes:

        onde HÁ linha?     precisa de densidade, senão a chuva de letras
                           do fundo vira linha
        onde ela ACABA?    qualquer tinta serve, porque a haste do `d` e
                           o rabo do `p` são poucos pixels numa linha só

    Usando a densidade para as duas coisas, a faixa saía cortada em cima
    e embaixo — e foi o que aconteceu no print do Eduardo: o `B` chegava
    na rede sem a barra de cima, parecendo outra letra. Medido: a linha
    tinha tinta desde y=109 e a faixa começava em 113.
    """
    por_linha = tinta.mean(axis=1)
    cheia = por_linha > min_tinta
    # PARA CRESCER, UM QUARTO DA DENSIDADE — não "qualquer pixel".
    #
    # Com `> 0` a faixa crescia sem parar: a chuva de letras do fundo
    # acende pelo menos um pixel em quase toda linha da imagem, e a
    # saudação acabou fundida com o fundo numa faixa só. Um quarto do
    # limiar é frouxo o bastante para a haste do `d` e apertado o
    # bastante para a chuva ficar de fora.
    tem_tinta = por_linha > min_tinta * 0.25
    faixas, dentro, inicio = [], False, 0
    for y, c in enumerate(cheia):
        if c and not dentro:
            dentro, inicio = True, y
        elif not c and dentro:
            dentro = False
            if MIN_ALTURA <= y - inicio <= MAX_ALTURA:
                faixas.append((inicio, y))
    if dentro and MIN_ALTURA <= len(cheia) - inicio <= MAX_ALTURA:
        faixas.append((inicio, len(cheia)))

    crescidas = []
    for y0, y1 in faixas:
        while y0 > 0 and tem_tinta[y0 - 1] and (y1 - y0) < MAX_ALTURA:
            y0 -= 1
        while y1 < len(tem_tinta) and tem_tinta[y1] and (y1 - y0) < MAX_ALTURA:
            y1 += 1
        # duas faixas que cresceram uma para dentro da outra viram uma só
        if crescidas and y0 <= crescidas[-1][1]:
            crescidas[-1] = (crescidas[-1][0], max(crescidas[-1][1], y1))
        else:
            crescidas.append((y0, y1))
    return crescidas


def passo_da_grade(banda, minimo=5, maximo=60):
    """O passo da grade monoespaçada, medido nos começos de glifo.

    A conta é o MODO das distâncias entre começos consecutivos, e não a
    média: numa frase com espaços, as distâncias são o passo, o dobro do
    passo e o triplo. A média ficaria entre eles e erraria todas as
    fatias; o valor mais FREQUENTE é o passo.
    """
    col = banda.any(axis=0)
    if not col.any():
        return None
    bordas = np.diff(col.astype(int))
    inicios = np.where(bordas == 1)[0] + 1
    if col[0]:
        inicios = np.insert(inicios, 0, 0)
    if len(inicios) < 3:
        return None
    passos = np.diff(inicios)
    passos = passos[(passos >= minimo) & (passos <= maximo)]
    if len(passos) == 0:
        return None
    # os múltiplos (espaços) voltam ao passo base pela divisão inteira
    conta = np.bincount(passos)
    base = int(np.argmax(conta))
    for divisor in (2, 3):
        # se o passo mais comum for na verdade o DOBRO (texto cheio de
        # espaços), a metade dele também tem de aparecer
        meio = base // divisor
        if meio >= minimo and conta[meio:meio + 1].sum() > conta[base] * 0.6:
            base = meio
    return base or None


def blocos_da_faixa(banda, folga=3):
    """[(x0, x1)] — os pedaços de texto SEPARADOS dentro da mesma altura.

    UMA FAIXA HORIZONTAL NÃO É UMA LINHA DE TEXTO. Numa tela de programa,
    a mesma altura pode conter o nome de uma conversa na barra lateral, a
    saudação no meio e um número na direita — três textos, com três
    grades diferentes, e nenhuma relação entre eles.

    No print do Eduardo o caso é pior: a chuva de letras do fundo acende
    pixels na altura da saudação, bem longe dela. Medindo o passo na
    faixa inteira, eu media a distância entre uma letra da saudação e uma
    pinga da chuva — e a grade saía sem sentido.

    O corte é onde há um vão de várias células. `folga` é em MÚLTIPLOS do
    vão típico entre glifos, e não em pixels: um espaço entre palavras
    não pode separar blocos, mas um vão de três células já é outro
    elemento da tela.
    """
    import collections
    col = banda.any(axis=0)
    if not col.any():
        return []
    # O CORTE É EM CÉLULAS, NÃO EM VÃOS ENTRE LETRAS.
    #
    # A primeira versão media o vão típico entre glifos (uns 2 px) e
    # cortava em 3 vezes isso — 10 px. Mas um ESPAÇO numa grade de 11 px
    # é um vão de 11 px. Resultado: a saudação foi partida em seis
    # blocos, um por palavra, e cada palavra virou uma leitura separada
    # sem os espaços entre elas.
    #
    # A unidade certa é o passo da grade: um espaço é UMA célula, e outro
    # elemento da tela está a várias. Medir o passo aqui é aproximado (a
    # faixa ainda tem chuva), mas o modo continua sendo o passo do texto,
    # que é quem tem mais glifos.
    passo = passo_da_grade(banda)
    if passo:
        corte = max(8, int(passo * folga))
    else:
        vazios, n = [], 0
        for c in col:
            if c:
                if n:
                    vazios.append(n)
                n = 0
            else:
                n += 1
        tipico = (collections.Counter(vazios).most_common(1)[0][0] + 1) if vazios else 2
        corte = max(8, int(tipico * folga) + 4)
    blocos, dentro, inicio, zeros = [], False, 0, 0
    for x, c in enumerate(col):
        if c:
            if not dentro:
                dentro, inicio = True, x
            zeros = 0
        elif dentro:
            zeros += 1
            if zeros >= corte:
                blocos.append((inicio, x - zeros + 1))
                dentro = False
    if dentro:
        blocos.append((inicio, len(col)))
    # um bloco de duas letras não tem grade que se meça
    return [(a, b) for a, b in blocos if b - a >= 12]


def apertar(banda, x0, x1):
    """(dy0, dy1) — as linhas que o texto DESTE bloco realmente ocupa.

    A faixa é achada na largura inteira e por isso chega folgada: no
    print do Eduardo ela cresceu para cima até y=100 pegando chuva, e a
    saudação, que mora de 109 para baixo, ficou espremida na metade
    inferior. Normalizada, a letra chegava à rede com um terço da caixa
    vazio em cima — nada parecido com o corpus, onde a letra preenche.

    Dentro do bloco não há chuva: o bloco já é o recorte horizontal do
    texto. Então aqui QUALQUER tinta vale, e o aperto é exato.
    """
    pedaco = banda[:, x0:x1]
    linhas = pedaco.any(axis=1)
    if not linhas.any():
        return 0, banda.shape[0]
    return int(linhas.argmax()), int(len(linhas) - linhas[::-1].argmax())


def celulas_da_banda(tinta, y0, y1, passo, x0=None, x1=None):
    """Fatia a banda em células de largura `passo`. [(x, recorte)]"""
    banda = tinta[y0:y1]
    col = banda.any(axis=0)
    if not col.any():
        return []
    esq = int(np.argmax(col)) if x0 is None else x0
    dir_ = (len(col) - int(np.argmax(col[::-1]))) if x1 is None else x1
    saida = []
    x = esq
    while x < dir_:
        saida.append((x, banda[:, x:x + passo]))
        x += passo
    return saida


def normalizar(celula, larg=CELULA_L, alt=CELULA_A):
    """A célula no tamanho fixo que a rede espera, como vetor 0..1.

    A CÉLULA INTEIRA É REDIMENSIONADA — não o glifo.

    A diferença é tudo. Recortar no retângulo da LETRA e esticar faria
    `.` e `'` virarem a mesma mancha, porque o que os separa é onde eles
    ficam dentro da célula. Redimensionar a CÉLULA mantém isso: o ponto
    continua embaixo, a aspa continua em cima, e só a escala muda.

    E sem isto o mesmo `A` em corpo 13 e em corpo 20 chegava à rede como
    duas figuras sem parentesco. Medido: 98% no próprio corpus e 17% numa
    fonte nova — decoreba pura. A rede tinha de aprender cada letra oito
    vezes, uma por tamanho, e não sobrava capacidade para generalizar.

    A MÉDIA POR ÁREA, e não o vizinho mais próximo: a célula é binária,
    então a média devolve a FRAÇÃO de tinta de cada pedaço — que é o
    antialiasing de volta, de graça, e é informação que o vizinho joga
    fora.
    """
    a = np.asarray(celula, dtype=float)
    h, w = a.shape
    if h == 0 or w == 0:
        return np.zeros(alt * larg)
    # índices de origem para cada pixel de destino, em blocos
    ys = (np.arange(alt + 1) * h / alt).astype(int)
    xs = (np.arange(larg + 1) * w / larg).astype(int)
    fora = np.zeros((alt, larg), dtype=float)
    for i in range(alt):
        y0, y1 = ys[i], max(ys[i] + 1, ys[i + 1])
        linha = a[y0:y1]
        for j in range(larg):
            x0, x1 = xs[j], max(xs[j] + 1, xs[j + 1])
            bloco = linha[:, x0:x1]
            fora[i, j] = bloco.mean() if bloco.size else 0.0
    return fora.ravel()


# ══════════════════════════════════════════════════════════════════════
#  O LEITOR
# ══════════════════════════════════════════════════════════════════════
class Leitor:
    """A rede treinada + a segmentação. `ler(imagem)` devolve o texto."""

    def __init__(self, caminho):
        import json
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("tokenizador") != "celula":
            raise ValueError(
                f"{caminho} não é um modelo de OCR desta classe "
                f"(tokenizador {d.get('tokenizador')!r}).")
        self.letras = d["letras"]
        self.forma = tuple(d.get("forma", (CELULA_A, CELULA_L)))
        self.w0 = np.array(d["w0"]); self.b0 = np.array(d["b0"])
        self.w1 = np.array(d["w1"]); self.b1 = np.array(d["b1"])
        self.medido = d.get("medido", {})

    def _prever(self, X):
        h = np.maximum(0, X @ self.w0 + self.b0)
        z = h @ self.w1 + self.b1
        z -= z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def ler(self, imagem, confianca=0.0):
        """O texto do print, linha por linha e bloco por bloco."""
        tinta = binarizar(imagem)
        linhas = []
        for y0, y1 in faixas_de_texto(tinta):
            banda = tinta[y0:y1]
            pedacos = []
            for x0, x1 in blocos_da_faixa(banda):
                # CADA BLOCO TEM A SUA PRÓPRIA GRADE. O menu e a barra
                # lateral podem estar na mesma altura com tamanhos de
                # fonte diferentes — medir os dois juntos não daria o
                # passo de nenhum dos dois.
                dy0, dy1 = apertar(banda, x0, x1)
                if dy1 - dy0 < MIN_ALTURA:
                    continue
                passo = passo_da_grade(banda[dy0:dy1, x0:x1])
                if not passo:
                    continue
                cels = celulas_da_banda(tinta, y0 + dy0, y0 + dy1,
                                        passo, x0, x1)
                if not cels:
                    continue
                X = np.array([normalizar(c, self.forma[1], self.forma[0])
                              for _, c in cels])
                p = self._prever(X)
                k = p.argmax(axis=1)
                pedacos.append("".join(
                    self.letras[i] if p[j, i] >= confianca else "\N{REPLACEMENT CHARACTER}"
                    for j, i in enumerate(k)).rstrip())
            texto = "   ".join(x for x in pedacos if x.strip())
            if texto.strip():
                linhas.append(texto)
        return "\n".join(linhas)
