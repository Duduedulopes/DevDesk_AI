# -*- coding: utf-8 -*-
"""Reconhece a linguagem olhando o CÓDIGO — quando você cola um exemplo.

    "faz um projeto assim ó:               → ela lê o trecho e sabe:
       public class Conta { ... }"           é C#. Não precisou perguntar.

POR QUE ISTO EXISTE

A etiquetadora tira da FRASE o que está escrito nela. Se você não disser
a linguagem, não há o que extrair. Mas colar um exemplo é dizer a
linguagem — só que dizendo em código em vez de em português.

E quando ela não reconhece, ela PERGUNTA. A abstenção aqui é resultado de
primeira classe, igual à do classificador de intenção: abaixo do limiar
ela devolve None, e quem chamou pergunta em vez de chutar.

A DIVISÃO É POR ARQUIVO, E ISSO NÃO É DETALHE

Um arquivo de código tem centenas de linhas parecidas entre si. Dividir
por LINHA jogaria linhas do mesmo arquivo no treino e no teste, e a rede
seria medida contra o que já viu — a mesma armadilha que inflou 35 pontos
na medição das intenções, com outra roupa.

Aqui a unidade é o ARQUIVO: ou ele inteiro está no treino, ou inteiro no
teste. E os trechos de teste vêm de arquivos que a rede nunca abriu.

O TRECHO É CURTO DE PROPÓSITO

Ela é medida em pedaços de 3 a 15 linhas, porque é isso que a pessoa
cola — não um arquivo inteiro. Acertar com o arquivo todo seria fácil e
não serviria para nada.

UM ARQUIVO .html NÃO É UM ARQUIVO DE HTML

Na primeira medição eu errei aqui, e o erro era do dado, não da rede. O
`painel/painel.html` tem 300 KB, e a maior parte é CSS dentro de <style>
e JavaScript dentro de <script>. Recortar trecho de lá e carimbar "html"
ensina que uma regra de CSS se chama html.

Agora o .html é cortado em REGIÕES antes de virar exemplo: o que está
dentro de <style> vira css, dentro de <script> vira javascript, e o resto
— as tags de verdade — vira html. O arquivo que era veneno virou a maior
fonte de CSS que temos. A região carrega o caminho do arquivo de origem,
senão a divisão por arquivo vazaria pela porta dos fundos.

CÓDIGO DE BIBLIOTECA NÃO É CÓDIGO SEU

`painel/vendor/monaco/vs/editor/editor.main.js` tem 3,7 MB de JavaScript
minificado que nem você nem eu escrevemos. Treinar nele ensinaria a rede
a reconhecer o estilo de um empacotador, não o seu. Fica de fora por
pasta (`vendor`, `node_modules`) e por formato: arquivo com linha média
gigante é minificado, e ninguém digita assim.
"""
import json
import random
import re
from pathlib import Path

import numpy as np

from modelo.classificador import ClassificadorDeIntencao
from texto.vocabulario import Vocabulario

EXTENSOES = {".py": "python", ".cs": "csharp", ".js": "javascript",
             ".mjs": "javascript", ".java": "java", ".cpp": "cpp",
             ".cc": "cpp", ".h": "cpp", ".hpp": "cpp", ".php": "php",
             ".html": "html", ".htm": "html", ".css": "css", ".sql": "sql"}

# pastas que não são código escrito por gente daqui
PASTAS_FORA = {"__pycache__", "node_modules", "obj", "bin", ".git",
               "vendor", ".vs", "dist", "build", "packages", ".venv",
               "venv", "migrations", "TestResults"}

LINHA_MEDIA_MAXIMA = 200      # acima disso é minificado, não digitado
MINIMO_DE_BYTES = 300

# O MENOR TRECHO QUE VALE UMA RESPOSTA — um número só, usado nos DOIS
# lados: filtra o que entra no treino e barra o que entra na pergunta.
# Quando eram dois números diferentes, o modelo respondia com 99,9% de
# confiança a um `x = 1` que ele nunca tinha visto no treino. A confiança
# era real; a pergunta é que não era. `x = 1` é python, é C#, é tudo.
#
# POR QUE 3 LINHAS E NÃO 2, medido: baixando para 2 linhas o recall macro
# caiu de 86,5% para 85,2% e o `def somar(a, b)` de três linhas — que é
# python sem discussão — virou csharp com 97% de confiança. Trecho de
# duas linhas é ambíguo de verdade, e ensinar com ele estraga também o
# caso claro. Então abaixo disto ela não responde: devolve None e o
# programa pergunta, que é a resposta certa para uma pergunta ambígua.
MINIMO_DO_TRECHO = 40
MINIMO_DE_LINHAS = 3

_STYLE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
_SCRIPT = re.compile(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)


# ══════════════════════════════════════════════════════════════════════
#  PREPARO DO DADO
# ══════════════════════════════════════════════════════════════════════
def minificado(texto):
    """Linha média enorme = empacotador, não pessoa."""
    linhas = texto.splitlines() or [texto]
    return len(texto) / max(1, len(linhas)) > LINHA_MEDIA_MAXIMA


def regioes(texto, ling):
    """Um .html vira até três montes: o css dele, o js dele, e o html dele.

    Devolve [(linguagem_de_verdade, texto)]. Para qualquer outra extensão
    devolve o arquivo inteiro, que é o caso normal.
    """
    if ling != "html":
        return [(ling, texto)]
    saida, resto = [], texto
    for regex, verdade in ((_STYLE, "css"), (_SCRIPT, "javascript")):
        pedacos = regex.findall(resto)
        if pedacos:
            junto = "\n".join(pedacos)
            if len(junto.strip()) >= MINIMO_DE_BYTES:
                saida.append((verdade, junto))
        resto = regex.sub("\n", resto)
    if len(resto.strip()) >= MINIMO_DE_BYTES:
        saida.append(("html", resto))
    return saida


def trechos_do_arquivo(texto, rng, quantos=40, min_linhas=3, max_linhas=15):
    """Recorta pedaços do tamanho que uma pessoa cola."""
    linhas = texto.splitlines()
    if len(linhas) < min_linhas:
        return []
    saida = []
    for _ in range(quantos):
        n = rng.randint(min_linhas, max_linhas)
        if len(linhas) <= n:
            i, n = 0, len(linhas)
        else:
            i = rng.randrange(0, len(linhas) - n)
        t = "\n".join(linhas[i:i + n]).strip()
        # Pedaço só de comentário ou só de linha em branco não ensina
        # linguagem nenhuma — ensina a chutar.
        if len(t) < MINIMO_DO_TRECHO or t.count("\n") < MINIMO_DE_LINHAS - 1:
            continue
        saida.append(t)
    return saida


def juntar(pastas):
    """{linguagem: [(caminho, texto)]} — com os .html separados por região.

    O `caminho` de uma região leva um sufixo (#css, #javascript) para
    você ver de onde veio; a divisão por arquivo usa o caminho SEM ele.
    """
    por_ling, vistos = {}, set()
    for pasta in pastas:
        for arq in sorted(Path(pasta).rglob("*")):
            if not arq.is_file():
                continue
            ling = EXTENSOES.get(arq.suffix.lower())
            if not ling:
                continue
            # por PARTE do caminho, não por texto: no Windows a barra é \
            if PASTAS_FORA & set(arq.parts):
                continue
            try:
                t = arq.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if len(t) < MINIMO_DE_BYTES or minificado(t) or t in vistos:
                continue
            vistos.add(t)
            for verdade, corpo in regioes(t, ling):
                sufixo = "" if verdade == ling else f"#{verdade}"
                por_ling.setdefault(verdade, []).append((str(arq) + sufixo, corpo))
    return por_ling


def arquivo_de(caminho):
    """Tira o sufixo de região: a divisão é por ARQUIVO, não por região."""
    return caminho.split("#")[0]


# ══════════════════════════════════════════════════════════════════════
#  O QUE O APLICATIVO USA
# ══════════════════════════════════════════════════════════════════════
class Detector:
    """Carrega o modelo gravado e responde — ou admite que não sabe.

        d = Detector(RAIZ / "modelos" / "detector.json")
        d.adivinhar("public class Conta {")   → ("csharp", 0.99)
        d.adivinhar("x = 1")                  → None   (abaixo do limiar)
    """

    def __init__(self, caminho):
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        # O tokenizador tem que bater. Carregar um modelo de peças com a
        # conta dos trigramas responde ruído em silêncio, que é pior do
        # que quebrar.
        self.tokenizador = d.get("tokenizador", "trigramas")
        if self.tokenizador != "trigramas":
            raise ValueError(f"detector gravado com '{self.tokenizador}', "
                             "e este código só sabe trigramas")
        self.linguagens = d["intencoes"]
        self.limiar = float(d.get("limiar", 0.6))
        self.medido = d.get("medido", {})
        self.vocab = Vocabulario([], minimo=1)
        self.vocab.pecas = d["pecas"]
        self.vocab.indice = {p: i for i, p in enumerate(d["pecas"])}
        self.rede = ClassificadorDeIntencao(len(d["pecas"]), self.linguagens,
                                            dimensao=d["dimensao"],
                                            ocultos=len(d["camadas"][0]["pesos"]))
        self.rede.tabela = np.array(d["tabela"], dtype=float)
        for camada, cru in zip(self.rede.rede.camadas, d["camadas"]):
            camada.pesos = np.array(cru["pesos"], dtype=float)
            camada.vies = np.array(cru["vies"], dtype=float).reshape(-1, 1)

    def probabilidades(self, trecho):
        return self.rede.prever(self.vocab.indices(trecho)).ravel()

    def adivinhar(self, trecho, limiar=None):
        """(linguagem, confiança) — ou None, que quer dizer 'me diz você'.

        O TRECHO CURTO DEMAIS NÃO É PERGUNTA VÁLIDA. Ela foi treinada em
        pedaços de 3 a 15 linhas; num `x = 1` ela respondeu python com
        99,9% de confiança, e a confiança era real — só que a pergunta
        não era. `x = 1` é python, é C#, é javascript, é tudo.

        Achei isso no teste de ida-e-volta do próprio modelo. O filtro
        que existia só no preparo do treino agora existe também na hora
        de responder, que é onde ele faz falta.
        """
        if not trecho or not trecho.strip():
            return None
        corpo = trecho.strip()
        if len(corpo) < MINIMO_DO_TRECHO or corpo.count("\n") < MINIMO_DE_LINHAS - 1:
            return None
        p = self.probabilidades(trecho)
        k = int(np.argmax(p))
        confianca = float(p[k])
        if confianca < (self.limiar if limiar is None else limiar):
            return None
        return self.linguagens[k], confianca
