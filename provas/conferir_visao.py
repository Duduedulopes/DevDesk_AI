# -*- coding: utf-8 -*-
"""Prova da percepção visual: o CLIP vê um print sintético como categoria.

Primeira chamada baixa os pesos (uma vez, para `dados/visao/pesos`);
as seguintes rodam offline. A prova monta prints de verdade do suporte —
janela de erro, instalador, configuração de rede — COMO O CLIP PRECISA
QUE ELES SEJAM: com cor, barras de janela e texto legível. Print de
suporte é uma tela inteira, não um bloco de texto em fundo branco, e o
olho vê a tela inteira.

A exigência central: reconhecer a categoria certa de cada print. Coberto
que o vetor fecha com as descrições em português, terminamos com 0.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from visao import clip_


def montar_print(cabecalho, linhas, cor_borda, cor_fundo="white"):
    """Desenha uma janela de aplicativo com título e corpo de texto."""
    from PIL import Image, ImageDraw, ImageFont

    largura, altura = 1024, 700
    imagem = Image.new("RGB", (largura, altura), cor_fundo)
    desenho = ImageDraw.Draw(imagem)

    try:
        fonte_titulo = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 44)
        fonte_corpo = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 34)
    except OSError:
        fonte_titulo = fonte_corpo = ImageFont.load_default(size=40)

    # barra de título da janela, como em qualquer sistema
    desenho.rectangle([40, 40, 984, 110], fill=cor_borda)
    desenho.text((60, 52), cabecalho, font=fonte_titulo, fill="white")
    # corpo da janela
    desenho.rectangle([40, 110, 984, 660], outline=cor_borda, width=6)
    for i, linha in enumerate(linhas):
        desenho.text((80, 150 + i * 60), linha, font=fonte_corpo, fill="black")
    return imagem


PRINTS = [
    ("erro_de_impressora", "Erro 0x000000be — Impressora offline", [
        "A impressora HP DeskJet 2755e esta offline.",
        "Verifique se esta ligada e conectada.",
        "Clique em Tentar novamente para continuar.",
    ], "#c00000", "#fff0f0"),
    ("instalacao_driver", "Instalando driver do dispositivo", [
        "Driver: HP Universal Print Driver 6.0.12",
        "Progresso: 52%",
        "Aguarde enquanto o Windows instala...",
    ], "#1f6feb", "#f0f7ff"),
    ("config_rede", "Configuracoes de rede — Conectado", [
        "IPv4: 192.168.1.14     Mascara: 255.255.255.0",
        "Gateway: 192.168.1.1    DNS: 8.8.8.8",
        "Status: Conectado       Velocidade: 100 Mbps",
    ], "#107c10", "#f2fbf2"),
    ("cadeira", "Nossa Loja — Cadeira Gamer", [
        "Cadeira gamer ergonomica com apoio de lombar",
        "Assento em espuma de alta densidade",
        "Peso maximo: 150kg    Garantia: 1 ano",
        "Preco: R$ 1.299,00  [Comprar agora]",
    ], "#86198f", "#fff3e6"),
]


def montar_print_produto(cabecalho, linhas, borda):
    """Como `montar_print`, mas com uma foto grande do produto no corpo."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        fonte_titulo = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 44)
        fonte_corpo = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 30)
    except OSError:
        fonte_titulo = fonte_corpo = ImageFont.load_default(size=40)

    imagem = Image.new("RGB", (1024, 700), "#fff7ec")
    desenho = ImageDraw.Draw(imagem)
    # barra de título da janela do navegador
    desenho.rectangle([40, 40, 984, 110], fill=borda)
    desenho.text((60, 52), cabecalho, font=fonte_titulo, fill="white")
    # corpo da loja: texto à esquerda, foto GIGANTE à direita
    desenho.text((80, 150), linhas[0], font=fonte_corpo, fill="black")
    desenho.text((80, 195), linhas[1], font=fonte_corpo, fill="black")
    # a "foto" (600x400): cadeira colorida com fundo de estúdio
    desenho.rectangle([380, 160, 960, 600], fill="#4a3f8f")
    desenho.rounded_rectangle([520, 250, 820, 540], radius=40,
                              fill="#7a5aa1")
    desenho.polygon([(520, 250), (820, 250), (820, 430), (520, 430)],
                    fill="#966fc4")
    desenho.line([560, 470, 535, 545], fill="#4b2f74", width=18)
    desenho.line([780, 470, 805, 545], fill="#4b2f74", width=18)
    desenho.rectangle([515, 545, 545, 585], fill="#c9a227", width=2)
    desenho.rectangle([795, 545, 825, 585], fill="#c9a227", width=2)
    # botão verde de compra, a assinatura de uma loja
    desenho.rounded_rectangle([80, 620, 360, 670], radius=14, fill="#16a34a")
    desenho.text((110, 631), linhas[3], font=fonte_corpo, fill="white")
    return imagem


CATEGORIAS = [
    "um erro de impressora offline no Windows",
    "a instalacao de um driver do Windows",
    "a configuracao de rede de um computador",
    "uma pagina da Nossa Loja vendendo uma cadeira gamer",
]


def conferir_visao():
    falhas = []
    for nome, cabecalho, linhas, borda, fundo in PRINTS:
        if nome == "cadeira":
            imagem = montar_print_produto(cabecalho, linhas, borda)
        else:
            imagem = montar_print(cabecalho, linhas, borda, fundo)
        ranking = clip_.pontuar(imagem, CATEGORIAS)
        melhor, prob = ranking[0]
        print(f"{nome:22s} -> {melhor}  ({prob * 100:4.1f}%)")
        esperado = {
            "erro_de_impressora": "erro",
            "instalacao_driver": "driver",
            "config_rede": "rede",
            "cadeira": "cadeira",
        }[nome]
        if esperado not in melhor:
            falhas.append(f"{nome}: esperava '{esperado}', viu '{melhor}'")

    if falhas:
        print("\nFALHAS:")
        for f in falhas:
            print(" -", f)
        return 1

    print("\ntodos os quatro prints foram reconhecidos na categoria certa.")
    return 0


if __name__ == "__main__":
    sys.exit(conferir_visao())