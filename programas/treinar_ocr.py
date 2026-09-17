# -*- coding: utf-8 -*-
"""Treina a rede que lê uma célula de texto e diz que letra é.

    python programas/treinar_ocr.py
    python programas/treinar_ocr.py --so-medir

DE ONDE VEM O CORPUS: EU DESENHO AS LETRAS

Diferente de tudo o mais neste projeto, aqui o corpus é sintético de
propósito — e é legítimo, porque a resposta certa é conhecida por
construção: eu desenho um `A`, então aquela imagem É um `A`. Não há
rótulo para adivinhar nem juiz para consultar.

O risco continua sendo o de sempre, e é o mesmo do LINQ: a letra que EU
desenho pode não parecer com a letra que o computador DELE desenha.
Fontes diferentes, antialiasing diferente, zoom diferente.

TRÊS DEFESAS CONTRA ISSO, E A TERCEIRA É A QUE VALE

    1. VÁRIAS FONTES no corpus, não uma
    2. A PROVA É NUMA FONTE QUE NÃO ENTROU NO TREINO
    3. A PROVA DE VERDADE É O PRINT DELE, com o texto que eu sei que
       está lá escrito

A terceira é a única que mede a distância até o mundo. As duas primeiras
medem a distância até mim.
"""
import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from visao.ocr import (CELULA_A, CELULA_L, binarizar,        # noqa: E402
                       apertar, blocos_da_faixa, celulas_da_banda,
                       faixas_de_texto, normalizar, passo_da_grade)

SEM = 42

# ASCII imprimível + o que o português precisa. O espaço entra como letra
# de verdade: numa grade monoespaçada a célula vazia É um caractere, e
# tratá-la à parte criaria um caminho especial só para ela.
LETRAS = ([" "] + [chr(c) for c in range(33, 127)]
          + list("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ°ºª—–…"))

# TODAS as monoespaçadas que a máquina tiver, menos a de prova.
#
# Cinco fontes davam 98% no corpus e 22% numa fonte nova: a rede decorava
# o desenho em vez de aprender a letra. Variedade no corpus é a única
# defesa barata contra isso — e as itálicas entram de propósito, porque
# ensinam que um `a` inclinado continua sendo `a`.
# A FONTE DA TELA DELE ENTRA AQUI, E ISSO É UMA ESCOLHA, NÃO UM DESCUIDO.
#
# A Cascadia Mono é a fonte que o painel do DevDesk usa — é ela que
# aparece nos prints que ele manda. Treinar sem ela era treinar para ler
# a tela de outra pessoa: 57% numa fonte nova e ~20% no print dele.
#
# Pondo-a no treino, a prova do print deixa de medir "consegue ler um
# tipo de letra que nunca viu" e passa a medir "consegue ler ESTA tela" —
# que é o trabalho. A outra pergunta continua sendo respondida pela
# `FONTE_PROVA`, que segue fora do treino.
#
# O print continua sendo prova honesta: ele tem o antialiasing do
# Windows, a escala real e a chuva de letras por trás. Nada disso está no
# meu corpus, e eu nunca treinei naquela imagem.
# ONDE AS FONTES DO WINDOWS MORAM. Elas NÃO são copiadas para dentro do
# projeto: são da Microsoft, já estão instaladas na máquina, e um
# repositório não é lugar para guardar cópia de fonte de sistema. O
# treinador procura; se não achar, treina com as que houver e diz isso.
FONTES_DO_SISTEMA = [
    r"C:\Windows\Fonts\CascadiaMono.ttf",
    r"C:\Windows\Fonts\CascadiaCode.ttf",
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\consolab.ttf",
    r"C:\Windows\Fonts\lucon.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/mnt/c/Windows/Fonts/CascadiaMono.ttf",       # WSL
    str(Path.home() / "Library/Fonts/CascadiaMono.ttf"),   # mac
]

FONTES_TREINO = [
    "visao/fontes/CascadiaMono.ttf",
    "visao/fontes/CascadiaCode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Italic.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMonoOblique.ttf",
    "/usr/share/texmf/fonts/opentype/public/lm/lmmono10-regular.otf",
    "/usr/share/texmf/fonts/opentype/public/lm/lmmonolt10-bold.otf",
    "/usr/share/texmf/fonts/opentype/public/lm/lmmonolt10-regular.otf",
    "/usr/share/texmf/fonts/opentype/public/lm/lmmonoltcond10-regular.otf",
    "/usr/share/texmf/fonts/opentype/public/lm/lmmonoslant10-regular.otf",
    "/usr/share/texmf/fonts/opentype/public/lm/lmmono12-regular.otf",
]
# a fonte que NÃO entra no treino — é ela que diz se a rede aprendeu
# "letra" ou só decorou o desenho das minhas fontes
FONTE_PROVA = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"

TAMANHOS = [13, 14, 15, 16, 17, 18, 19, 20]


def desenhar_linha(texto, caminho_fonte, tamanho, dx=0, dy=0,
                   claro=235, escuro=12):
    """Uma LINHA de texto desenhada, como uma tela desenharia.

    LINHA, E NÃO LETRA SOLTA — e este foi o conserto que levou o OCR de
    11% para o que ele é hoje.

    Na primeira versão eu desenhava cada letra sozinha, no topo de uma
    caixa alta, e treinava nisso. Mas o LEITOR não vê isso: ele acha a
    faixa apertada da linha de texto e fatia. A letra que ele entrega
    para a rede está encostada no alto e embaixo da faixa; a que eu
    treinava estava solta no meio de uma caixa.

    Duas coisas diferentes com o mesmo nome — 60% de acerto no PRÓPRIO
    corpus, e o treino nem conseguia descer a perda.

    Agora o corpus sai pelo MESMO caminho da leitura: desenha a linha,
    binariza, acha a faixa, mede o passo, fatia. O que a rede treina é,
    por construção, o que ela vai receber.
    """
    try:
        fonte = ImageFont.truetype(caminho_fonte, tamanho)
    except OSError:
        return None
    larg = int(round(fonte.getlength("M") * len(texto))) + 8
    alt = int(tamanho * 2.0)
    im = Image.new("L", (max(larg, 12), alt), escuro)
    ImageDraw.Draw(im).text((4 + dx, alt * 0.25 + dy), texto,
                            font=fonte, fill=claro)
    return im


def sujar(im, rnd):
    """Borrão e espessura — a aumentação que SOBREVIVE à binarização.

    A primeira versão variava brilho e contraste. Inútil: o `binarizar`
    roda logo depois e apaga exatamente essa variação. O corpus inteiro
    tinha uma aumentação só, o deslocamento de ±1 pixel.

    Estas duas mudam a FORMA, que é o que sobra depois do corte:

        borrão      antialiasing de tela e de escala — engorda ou come as
                    pontas finas, que é onde `i`/`l` e `.`/`,` se decidem
        espessura   a mesma letra em negrito, ou numa tela com subpixel
                    diferente, tem traço mais grosso

    E elas são aplicadas ANTES do limiar, que é onde a tela as aplica.
    """
    from PIL import ImageFilter
    if rnd.random() < 0.55:
        im = im.filter(ImageFilter.GaussianBlur(rnd.uniform(0.3, 1.1)))
    r = rnd.random()
    if r < 0.2:
        im = im.filter(ImageFilter.MaxFilter(3))      # engrossa
    elif r < 0.4:
        im = im.filter(ImageFilter.MinFilter(3))      # afina
    return im


def desenhar(letra, caminho_fonte, tamanho, dx=0, dy=0, claro=235, escuro=12):
    """Uma célula com a letra desenhada, do jeito que uma tela desenharia.

    O DESLOCAMENTO SUB-PIXEL (`dx`,`dy`) NÃO É ENFEITE. Na tela real a
    grade quase nunca cai em pixel inteiro: a mesma letra aparece meio
    pixel para a direita numa coluna e meio para a esquerda na outra, e o
    antialiasing muda com ela. Treinar só na posição perfeita faz uma rede
    que acerta no laboratório e erra no print.
    """
    try:
        fonte = ImageFont.truetype(caminho_fonte, tamanho)
    except OSError:
        return None
    # desenha grande e mede, para descobrir o passo desta fonte/tamanho
    larg = max(1, int(round(fonte.getlength("M"))))
    alt = int(tamanho * 1.45)
    im = Image.new("L", (larg + 4, alt + 4), escuro)
    ImageDraw.Draw(im).text((2 + dx, 1 + dy), letra, font=fonte, fill=claro)
    return im, larg


def celulas_de_uma_linha(texto, fonte, tamanho, rnd):
    """[(vetor, letra)] — fatiado na grade QUE EU SEI, não na que eu meço.

    ESTE É O CONSERTO MAIS IMPORTANTE DESTE ARQUIVO.

    A primeira versão media o passo com `passo_da_grade`, igual ao leitor.
    Parecia coerente e estava errado: a medição acerta por volta de ±1
    pixel, e numa linha de 18 letras esse 1 pixel ACUMULA até a célula 12
    conter metade de duas letras. O rótulo continuava sendo a letra 12 —
    e eu treinava a rede a chamar de `É` um pedaço de `D` colado num `e`.

    Medido, e foi assim que eu vi: tinta média de 0,29 por célula (texto
    de verdade dá 0,10-0,15), célula rotulada `' '` com tinta dentro, e
    acerto de 16% numa fonte nova por mais fontes que eu jogasse no
    corpus. Não era decoreba — era corpus mentiroso.

    Aqui eu NÃO PRECISO MEDIR: fui eu que desenhei. `getlength` dá o passo
    exato em float, e a origem é onde eu mandei o `text()` desenhar. A
    grade sai perfeita e o rótulo casa com o desenho, sempre.

    Medir continua sendo o trabalho do LEITOR — ele não desenhou nada e
    não tem como saber. Treinar no que eu sei e ler no que ele mede é
    justamente o que a aumentação de ±1 pixel existe para cobrir.
    """
    dx, dy = rnd.choice([0, 0, 1, -1]), rnd.choice([0, 0, 1, -1])
    im = desenhar_linha(texto, fonte, tamanho, dx=dx, dy=dy,
                        claro=rnd.randint(170, 255), escuro=rnd.randint(0, 45))
    if im is None:
        return []
    im = sujar(im, rnd)
    tinta = binarizar(im)
    faixas = faixas_de_texto(tinta)
    if len(faixas) != 1:
        return []
    y0, y1 = faixas[0]
    try:
        passo = ImageFont.truetype(fonte, tamanho).getlength("M")
    except OSError:
        return []
    if passo < 4:
        return []
    banda = tinta[y0:y1]
    # A ORIGEM É A PRIMEIRA TINTA — como o LEITOR faz, e não como eu
    # desenhei. O `text()` começa na origem da caneta, que fica uns dois
    # pixels à esquerda da primeira tinta (a margem interna do glifo). O
    # leitor não tem como saber isso: ele só vê pixel aceso. Treinando na
    # minha origem e lendo na dele, toda célula chegava deslocada.
    col = banda.any(axis=0)
    if not col.any():
        return []
    origem = int(col.argmax())
    banda = tinta[y0:y1]
    fora = []
    for i, letra in enumerate(texto):
        a = int(round(origem + i * passo))
        b = int(round(origem + (i + 1) * passo))
        if b > banda.shape[1]:
            break
        fora.append((normalizar(banda[:, a:b]), letra))
    return fora


def corpus(fontes, por_letra, semente):
    """Linhas aleatórias com todas as letras, fatiadas como o leitor fatia."""
    rnd = random.Random(semente)
    indice = {c: k for k, c in enumerate(LETRAS)}
    conta = {c: 0 for c in LETRAS}
    X, y = [], []
    alvo = por_letra * len(LETRAS)
    tentativas = 0
    while len(X) < alvo and tentativas < alvo * 3:
        tentativas += 1
        # a linha mistura as letras que ainda faltam com letras comuns, para
        # o corpus ficar equilibrado sem virar sopa de símbolos
        faltando = [c for c in LETRAS if conta[c] < por_letra and c != " "]
        if not faltando:
            break
        n = rnd.randint(6, 18)
        texto = "".join(rnd.choice(faltando) if rnd.random() < 0.6
                        else rnd.choice(LETRAS) for _ in range(n))
        texto = texto.lstrip() or rnd.choice(faltando)
        for vetor, letra in celulas_de_uma_linha(
                texto, rnd.choice(fontes), rnd.choice(TAMANHOS), rnd):
            if letra in indice and conta[letra] < por_letra * 1.4:
                X.append(vetor); y.append(indice[letra]); conta[letra] += 1
    return np.array(X), np.array(y)


# ══════════════════════════════════════════════════════════════════════
#  A REDE — uma camada escondida, ReLU, softmax
# ══════════════════════════════════════════════════════════════════════
def treinar(X, y, n_saidas, ocultos=400, epocas=80, taxa=2.0, semente=SEM):
    r = np.random.default_rng(semente)
    n, d = X.shape
    w0 = r.normal(0, np.sqrt(2 / d), (d, ocultos)); b0 = np.zeros(ocultos)
    w1 = r.normal(0, np.sqrt(2 / ocultos), (ocultos, n_saidas)); b1 = np.zeros(n_saidas)
    Y = np.zeros((n, n_saidas)); Y[np.arange(n), y] = 1.0
    lote = 128
    for ep in range(1, epocas + 1):
        ordem = r.permutation(n)
        perda = 0.0
        t = taxa * 0.5 * (1 + np.cos(np.pi * (ep - 1) / epocas))
        for i in range(0, n, lote):
            idx = ordem[i:i + lote]
            xb, yb = X[idx], Y[idx]
            h = np.maximum(0, xb @ w0 + b0)
            z = h @ w1 + b1
            z -= z.max(axis=1, keepdims=True)
            e = np.exp(z); p = e / e.sum(axis=1, keepdims=True)
            perda += -np.log(np.maximum((p * yb).sum(axis=1), 1e-12)).sum()
            dz = (p - yb) / len(idx)
            gw1 = h.T @ dz; gb1 = dz.sum(axis=0)
            dh = (dz @ w1.T) * (h > 0)
            gw0 = xb.T @ dh; gb0 = dh.sum(axis=0)
            w1 -= t * gw1; b1 -= t * gb1
            w0 -= t * gw0; b0 -= t * gb0
        if ep % max(1, epocas // 5) == 0 or ep == 1:
            print(f"  época {ep:>3}/{epocas}  perda {perda/n:.4f}")
    return w0, b0, w1, b1


def acerto(w0, b0, w1, b1, X, y):
    h = np.maximum(0, X @ w0 + b0)
    return float((np.argmax(h @ w1 + b1, axis=1) == y).mean())


# ══════════════════════════════════════════════════════════════════════
#  A PROVA QUE IMPORTA: o print de verdade
# ══════════════════════════════════════════════════════════════════════
# o que EU SEI que está escrito nele — conferido olhando a imagem
PRINT_REAL = (RAIZ / "dados" / "anexos" /
              "20260915-145122-Captura_de_tela_2026-09-15_145110.png")
GABARITO = {113: "Boa tarde Eduardo! como posso ajudar?"}


def ler_com(w0, b0, w1, b1, caminho):
    im = Image.open(caminho)
    tinta = binarizar(im)
    saida = {}
    for y0, y1 in faixas_de_texto(tinta):
        banda = tinta[y0:y1]
        for x0, x1 in blocos_da_faixa(banda):
            dy0, dy1 = apertar(banda, x0, x1)
            passo = passo_da_grade(banda[dy0:dy1, x0:x1])
            if not passo:
                continue
            cels = celulas_da_banda(tinta, y0 + dy0, y0 + dy1, passo, x0, x1)
            if not cels:
                continue
            X = np.array([normalizar(c) for _, c in cels])
            h = np.maximum(0, X @ w0 + b0)
            k = np.argmax(h @ w1 + b1, axis=1)
            saida[(y0, x0)] = "".join(LETRAS[i] for i in k).rstrip()
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-letra", type=int, default=90)
    ap.add_argument("--epocas", type=int, default=40)
    ap.add_argument("--so-medir", action="store_true")
    ap.add_argument("--modelo", default=str(RAIZ / "modelos" / "ocr.json"))
    arg = ap.parse_args()

    fontes = [str(RAIZ / f) if not f.startswith("/") else f
              for f in FONTES_TREINO]
    fontes = [f for f in fontes if Path(f).exists()]
    doSistema = [f for f in FONTES_DO_SISTEMA if Path(f).exists()]
    fontes += doSistema
    if doSistema:
        print("  do sistema: " + ", ".join(Path(f).name for f in doSistema))
    elif not any("Cascadia" in f for f in fontes):
        # DIZER O QUE FALTA, em vez de treinar pior em silêncio. A fonte
        # da tela de quem usa é a que mais importa no corpus: sem ela o
        # acerto no print de verdade cai de 78% para cerca de 20%.
        print("  AVISO: não achei a Cascadia Mono nem a Consolas nesta "
              "máquina.\n         O OCR vai ler pior os prints do painel — "
              "ele usa Cascadia.")
    print(f"{len(LETRAS)} letras · {len(fontes)} fontes de treino · "
          f"{len(TAMANHOS)} tamanhos")
    if not fontes:
        print("nenhuma fonte monoespaçada encontrada")
        raise SystemExit(1)

    X, y = corpus(fontes, arg.por_letra, SEM)
    print(f"corpus: {len(X):,} células de {X.shape[1]} pixels\n")
    w0, b0, w1, b1 = treinar(X, y, len(LETRAS), epocas=arg.epocas)

    print(f"\n  no próprio corpus:        {acerto(w0,b0,w1,b1,X,y):.1%}")
    if Path(FONTE_PROVA).exists():
        Xp, yp = corpus([FONTE_PROVA], 25, SEM + 7)
        print(f"  numa FONTE que não viu:   {acerto(w0,b0,w1,b1,Xp,yp):.1%}"
              f"   ({Path(FONTE_PROVA).name})")

    # ── e agora o que vale: o print do Eduardo ────────────────────────
    print("\n" + "=" * 70)
    print("  O PRINT DE VERDADE")
    print("=" * 70)
    if not PRINT_REAL.exists():
        print(f"  (não achei {PRINT_REAL.name} — sem esta prova o número "
              "acima mede só a distância até mim)")
    else:
        lido = ler_com(w0, b0, w1, b1, PRINT_REAL)
        for _, esperado in GABARITO.items():
            # ACHA A FAIXA PELO CONTEÚDO, não pelo `y`. A altura em que a
            # linha começa muda quando eu mexo no detector de faixa — e
            # uma prova que quebra quando eu conserto o código não mede o
            # conserto, mede a minha memória do número antigo.
            saiu = max(lido.values(),
                       key=lambda s: sum(a == b for a, b in zip(s, esperado)),
                       default="(faixa não encontrada)")
            iguais = sum(a == b for a, b in zip(saiu, esperado))
            print(f"\n  esperado: {esperado!r}")
            print(f"  saiu    : {saiu!r}")
            print(f"  letra por letra: {iguais}/{len(esperado)} = "
                  f"{iguais/len(esperado):.0%}")
        print("\n  outras faixas que ele leu:")
        for chave in sorted(lido)[:10]:
            if lido[chave].strip():
                print(f"    y={chave[0]:<4} x={chave[1]:<5} {lido[chave][:60]!r}")

    if arg.so_medir:
        print("\n--so-medir: nada gravado")
        return
    Path(arg.modelo).parent.mkdir(parents=True, exist_ok=True)
    with open(arg.modelo, "w", encoding="utf-8") as f:
        json.dump({"tokenizador": "celula", "letras": LETRAS,
                   "forma": [CELULA_A, CELULA_L],
                   "w0": w0.round(4).tolist(), "b0": b0.round(4).tolist(),
                   "w1": w1.round(4).tolist(), "b1": b1.round(4).tolist(),
                   "medido": {"fontes_treino": [Path(f).name for f in fontes],
                              "fonte_prova": Path(FONTE_PROVA).name}}, f)
    print(f"\n  gravado em {arg.modelo}")


if __name__ == "__main__":
    main()
