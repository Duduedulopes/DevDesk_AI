# -*- coding: utf-8 -*-
"""A rede que etiqueta CADA PEÇA da frase: qual é a linguagem, qual é o nome.

    "cria um projeto em rust chamado oficina"
       O    O     O    O   LING     O    NOME

O QUE MUDA EM RELAÇÃO AO CLASSIFICADOR, E POR QUÊ

O classificador de intenção tira a MÉDIA dos vetores da frase, porque
"quanto vendi hoje" e "hoje quanto vendi" pedem a mesma coisa — a ordem
não importa e a média resolve o tamanho variável de uma vez.

Aqui a ordem é TUDO. O que separa a linguagem do nome não são as palavras
em si — é onde elas estão:

    "projeto em ___"       o que vem aqui é LINGUAGEM
    "chamado ___"          o que vem aqui é NOME

Uma média jogaria essa informação fora. Então aqui os vetores são
CONCATENADOS numa janela em volta da peça que está sendo decidida — é a
mesma escolha do previsor de caracteres, pelo mesmo motivo.

    A arquitetura muda porque a pergunta mudou.

CADA PEÇA É A MÉDIA DAS SUAS PARTES, E ISSO É O QUE FAZ FUNCIONAR COM
PALAVRA QUE ELE NUNCA VIU

Uma peça do texto ("rust") vira a média dos pedaços dela: a palavra
inteira, se conhecida, mais os trigramas `<ru`, `rus`, `ust`, `t>`. Numa
palavra nunca vista a palavra inteira falta, mas os trigramas estão lá —
então ela chega na rede como um vetor de verdade, e não como um buraco.

É por isso que dá para etiquetar `rust` corretamente tendo treinado só com
python, c#, javascript, html, css e php: a decisão vem do LUGAR e do
formato, não de uma lista.

A BORDA TEM ÍNDICE PRÓPRIO

Na primeira peça da frase, a janela pede duas peças que não existem. Elas
não podem virar `<?>` (desconhecido): "não tem nada aqui" e "tem uma
palavra que eu não conheço" são informações diferentes, e a primeira é
justamente o que marca começo de frase.
"""
import numpy as np

from nucleo.ativacao import Softmax
from nucleo.custo import EntropiaCruzadaCategorica
from nucleo.rede import Rede
from nucleo.retropropagacao import gradiente_com_entrada

ETIQUETAS = ["O", "LING", "TIPO", "NOME"]


class Etiquetador:
    """Janela de peças concatenadas → uma etiqueta para a peça do meio."""

    def __init__(self, tamanho_vocabulario, janela=2, dimensao=24, ocultos=48,
                 etiquetas=None, semente=None):
        self.etiquetas = list(etiquetas or ETIQUETAS)
        self.janela = janela
        self.dimensao = dimensao
        self.largura = 2 * janela + 1
        # +1 para a borda, que fica no último índice
        self.V = tamanho_vocabulario + 1
        self.borda = tamanho_vocabulario

        g = np.random.default_rng(semente)
        self.tabela = g.standard_normal((self.V, dimensao)) * 0.1
        self.rede = Rede([self.largura * dimensao, ocultos, len(self.etiquetas)],
                         semente=semente, ativacao_saida=Softmax)

    # ── da frase para os números ──────────────────────────────────────
    def vetor_da_peca(self, pedacos):
        """A média dos pedaços de UMA peça do texto."""
        return self.tabela[pedacos].mean(axis=0)

    def entrada(self, frase_em_pedacos, i):
        """A janela em volta da posição i, concatenada numa coluna.

        `frase_em_pedacos` é uma lista: para cada peça do texto, a lista de
        índices dos pedaços dela.
        """
        partes = []
        for d in range(-self.janela, self.janela + 1):
            j = i + d
            if 0 <= j < len(frase_em_pedacos):
                partes.append(self.vetor_da_peca(frase_em_pedacos[j]))
            else:
                partes.append(self.tabela[self.borda])
        return np.concatenate(partes).reshape(-1, 1)

    def prever(self, frase_em_pedacos, i):
        return self.rede.frente(self.entrada(frase_em_pedacos, i))

    def etiquetar(self, frase_em_pedacos):
        """(etiqueta, confiança) para cada peça da frase."""
        saida = []
        for i in range(len(frase_em_pedacos)):
            p = self.prever(frase_em_pedacos, i).ravel()
            k = int(np.argmax(p))
            saida.append((self.etiquetas[k], float(p[k])))
        return saida

    # ── treino ────────────────────────────────────────────────────────
    def _alvo(self, k):
        y = np.zeros((len(self.etiquetas), 1))
        y[k] = 1.0
        return y

    def passo(self, lote, taxa):
        """Um passo de gradiente. `lote` = [(frase_em_pedacos, i, k), …]."""
        soma_pesos = [np.zeros_like(c.pesos) for c in self.rede.camadas]
        soma_vies = [np.zeros_like(c.vies) for c in self.rede.camadas]
        soma_tabela = np.zeros_like(self.tabela)

        for frase, i, k in lote:
            x = self.entrada(frase, i)
            gp, gv, erro_entrada = gradiente_com_entrada(
                self.rede, x, self._alvo(k), EntropiaCruzadaCategorica)
            for c in range(len(self.rede.camadas)):
                soma_pesos[c] += gp[c]
                soma_vies[c] += gv[c]

            # O erro volta CONCATENADO: os primeiros `dimensao` números são
            # da peça mais à esquerda da janela, os próximos da seguinte, e
            # assim por diante. Cortar na ordem certa é o que liga o
            # gradiente à peça que o gerou.
            erro = erro_entrada.ravel()
            for pos, d in enumerate(range(-self.janela, self.janela + 1)):
                fatia = erro[pos * self.dimensao:(pos + 1) * self.dimensao]
                j = i + d
                if 0 <= j < len(frase):
                    # A peça é a MÉDIA dos pedaços dela, então cada pedaço
                    # recebe a fatia dividida pela quantidade — a derivada
                    # da média, a mesma divisão do classificador.
                    pedacos = frase[j]
                    np.add.at(soma_tabela, pedacos, fatia / len(pedacos))
                else:
                    soma_tabela[self.borda] += fatia

        n = len(lote)
        for c, camada in enumerate(self.rede.camadas):
            camada.pesos -= (taxa / n) * soma_pesos[c]
            camada.vies -= (taxa / n) * soma_vies[c]
        self.tabela -= (taxa / n) * soma_tabela

    # ── medida ────────────────────────────────────────────────────────
    def avaliar(self, exemplos):
        """(acerto por peça, custo médio, matriz de confusão das etiquetas)."""
        n_et = len(self.etiquetas)
        M = np.zeros((n_et, n_et), dtype=int)
        soma, certos = 0.0, 0
        for frase, i, k in exemplos:
            p = self.prever(frase, i).ravel()
            esc = int(np.argmax(p))
            M[k, esc] += 1
            soma += -np.log(max(float(p[k]), 1e-12))
            certos += int(esc == k)
        n = max(1, len(exemplos))
        return certos / n, soma / n, M

    @property
    def n_parametros(self):
        return self.tabela.size + self.rede.n_parametros

    def para_dicionario(self, vocabulario):
        return {
            "etiquetas": self.etiquetas,
            "janela": self.janela,
            "dimensao": self.dimensao,
            "pecas": vocabulario.pecas,
            "tokenizador": "trigramas",
            "tabela": [[round(float(x), 4) for x in linha] for linha in self.tabela],
            "camadas": [{"ativacao": c.ativacao.nome,
                         "pesos": [[round(float(x), 4) for x in l] for l in c.pesos],
                         "vies": [round(float(x), 4) for x in c.vies.ravel()]}
                        for c in self.rede.camadas],
        }


class EtiquetadorTreinado:
    """Carrega o etiquetador gravado e lê uma frase — é o que o app usa.

    POR QUE UMA CLASSE SEPARADA E NÃO UM `de_dicionario`

    O `Etiquetador` é a rede que APRENDE: ele carrega tudo que o treino
    precisa. O aplicativo só quer perguntar. Separar deixa o app carregar
    um JSON e responder, sem arrastar o maquinário de treino junto — e
    deixa claro, na hora de ler o código, qual dos dois está em uso.
    """

    def __init__(self, caminho):
        import json

        from texto.vocabulario import Vocabulario

        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        # O tokenizador tem que bater. Carregar um modelo de peças com a
        # conta dos trigramas responde ruído em silêncio, que é pior do
        # que quebrar na cara.
        tok = d.get("tokenizador", "trigramas")
        if tok != "trigramas":
            raise ValueError(f"etiquetador gravado com '{tok}', "
                             "e este código só sabe trigramas")
        self.etiquetas = d["etiquetas"]
        self.medido = d.get("medido", {})
        self.vocab = Vocabulario([], minimo=1)
        self.vocab.pecas = d["pecas"]
        self.vocab.indice = {p: i for i, p in enumerate(d["pecas"])}
        self.rede = Etiquetador(len(d["pecas"]), janela=d["janela"],
                                dimensao=d["dimensao"],
                                ocultos=len(d["camadas"][0]["pesos"]),
                                etiquetas=self.etiquetas)
        self.rede.tabela = np.array(d["tabela"], dtype=float)
        for camada, cru in zip(self.rede.rede.camadas, d["camadas"]):
            camada.pesos = np.array(cru["pesos"], dtype=float)
            camada.vies = np.array(cru["vies"], dtype=float).reshape(-1, 1)

    def ler(self, frase):
        """A frase etiquetada: [(peça, etiqueta, confiança)]."""
        from texto.vocabulario import pedacos as partir

        pecas = frase.split()
        if not pecas:
            return []
        em_pedacos = [self.vocab.indices(p) or [self.rede.borda] for p in pecas]
        saida = []
        for i, peca in enumerate(pecas):
            p = self.rede.prever(em_pedacos, i).ravel()
            k = int(np.argmax(p))
            saida.append((peca, self.etiquetas[k], float(p[k])))
        return saida

    def campos(self, frase, limiar=0.5):
        """{'LING': 'csharp', 'TIPO': 'api', 'NOME': 'loja'} — o que deu.

        Peças seguidas com a mesma etiqueta viram um campo só: "linq to
        entities" são três peças LING e uma linguagem. Abaixo do limiar a
        peça não entra — e um campo que não sai é um campo para
        PERGUNTAR, não para inventar.
        """
        achado, atual, etiqueta_atual = {}, [], None
        for peca, etiqueta, confianca in self.ler(frase):
            if etiqueta != "O" and confianca >= limiar:
                if etiqueta == etiqueta_atual:
                    atual.append(peca)
                else:
                    if etiqueta_atual and etiqueta_atual not in achado:
                        achado[etiqueta_atual] = " ".join(atual)
                    atual, etiqueta_atual = [peca], etiqueta
            else:
                if etiqueta_atual and etiqueta_atual not in achado:
                    achado[etiqueta_atual] = " ".join(atual)
                atual, etiqueta_atual = [], None
        if etiqueta_atual and etiqueta_atual not in achado:
            achado[etiqueta_atual] = " ".join(atual)
        return achado
