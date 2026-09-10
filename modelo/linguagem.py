"""O modelo de linguagem: prever o próximo caractere.

A ARQUITETURA, E POR QUE ELA É ESTA

    janela de N caracteres
        │   cada um vira um vetor de D números (tabela de embutimento)
        ▼
    concatenação  (N·D números)
        │
        ▼
    camada oculta, sigmoide          ← a sua função
        │
        ▼
    softmax sobre o alfabeto
        │
        ▼
    entropia cruzada contra o caractere que veio de verdade   ← a sua perda

É o modelo do Bengio, de 2003, e é a avó de tudo que veio depois. Usa
exatamente as três peças que já estavam em `nucleo/`: sigmoide, descida do
gradiente e entropia cruzada. Não há nada aqui que o motor já não soubesse
fazer — o que muda é o que se pede a ele que preveja.

A CONTA QUE ELE MINIMIZA É A TAXA DE COMPRESSÃO

`EntropiaCruzadaCategorica` devolve -ln(a[certo]) — o custo em nats de
codificar o caractere que veio, usando as probabilidades que o modelo
acredita. Dividido por ln(2), isso é BITS. A perda média do treino, em bits,
é literalmente quantos bits por caractere o modelo precisa para escrever o
corpus.

    perda baixa = compressão boa = o modelo entendeu a estrutura

Não é analogia. É a mesma conta, e o `custo.py` já dizia isso.

A TABELA DE EMBUTIMENTO É PARÂMETRO, NÃO DADO

É por isso que o treino usa `gradiente_com_entrada` em vez de `gradiente`: o
erro precisa chegar até a entrada, porque a entrada é feita de números que
também são aprendidos. Sem isso a tabela ficaria congelada no sorteio
inicial, e cada caractere seria representado por ruído para sempre.
"""
import json
import math
import numpy as np

from nucleo.rede import Rede
from nucleo.ativacao import Softmax
from nucleo.custo import EntropiaCruzadaCategorica
from nucleo.retropropagacao import gradiente_com_entrada

LN2 = math.log(2.0)


class ModeloDeLinguagem:
    """Prevê o próximo caractere a partir dos N anteriores."""

    def __init__(self, alfabeto, contexto=8, dimensao=16, oculta=256, semente=None):
        self.alfabeto = list(alfabeto)
        self.indice = {c: i for i, c in enumerate(self.alfabeto)}
        self.contexto = contexto
        self.dimensao = dimensao

        v = len(self.alfabeto)
        g = np.random.default_rng(semente)

        # A tabela: uma linha por caractere, D números cada.
        # Dividida por raiz(D) pelo mesmo motivo que os pesos da camada —
        # a concatenação vira a entrada de uma soma de N·D termos, e sem
        # isso a sigmoide da oculta nasce saturada.
        self.tabela = g.standard_normal((v, dimensao)) / np.sqrt(dimensao)

        self.rede = Rede([contexto * dimensao, oculta, v],
                         semente=semente, ativacao_saida=Softmax)

    # ── conversão ────────────────────────────────────────────────────
    def codificar(self, texto):
        """Texto → índices. Caractere fora do alfabeto é descartado."""
        return [self.indice[c] for c in texto if c in self.indice]

    def entrada(self, janela):
        """Os N vetores da janela, emendados num vetor coluna só."""
        return self.tabela[list(janela)].reshape(-1, 1)

    def alvo(self, i):
        y = np.zeros((len(self.alfabeto), 1))
        y[i] = 1.0
        return y

    # ── uso ──────────────────────────────────────────────────────────
    def prever(self, janela):
        """A distribuição de probabilidade sobre o próximo caractere."""
        return self.rede.frente(self.entrada(janela))

    def bits_do_proximo(self, janela, certo):
        """Quantos bits este modelo gasta para dizer qual foi o próximo."""
        a = self.prever(janela)
        # `.ravel()` NÃO é enfeite: `a` tem forma (alfabeto, 1), então
        # a[certo] é um vetor de um elemento. O NumPy 2 recusa converter
        # isso em número — TypeError: only 0-dimensional arrays. Rodava no
        # NumPy antigo, quebrou na atualização, e quebra AQUI: na medição
        # de bits, que é o número que o projeto inteiro usa como régua.
        return -math.log2(max(float(a.ravel()[certo]), 1e-15))

    def bits_por_caractere(self, indices, salto=1):
        """A medida do projeto, sobre um texto que o modelo não treinou.

        `salto` amostra o texto em vez de medir caractere a caractere —
        útil enquanto o corpus é grande e a medição é frequente.
        """
        total, n = 0.0, 0
        for i in range(self.contexto, len(indices), salto):
            total += self.bits_do_proximo(indices[i - self.contexto:i], indices[i])
            n += 1
        return total / n if n else float("nan")

    # ── treino ───────────────────────────────────────────────────────
    def passo(self, lote, taxa):
        """Um passo de descida do gradiente sobre um minilote.

        `lote` é uma lista de (janela, indice_certo).
        Devolve a perda média do lote, em bits.
        """
        gp = [np.zeros_like(c.pesos) for c in self.rede.camadas]
        gv = [np.zeros_like(c.vies) for c in self.rede.camadas]
        gt = np.zeros_like(self.tabela)
        perda = 0.0

        for janela, certo in lote:
            x = self.entrada(janela)
            y = self.alvo(certo)

            dp, dv, erro_entrada = gradiente_com_entrada(
                self.rede, x, y, EntropiaCruzadaCategorica)

            for i in range(len(gp)):
                gp[i] += dp[i]
                gv[i] += dv[i]

            # O erro chega emendado; desdobra de volta em N pedaços de D.
            por_posicao = erro_entrada.reshape(self.contexto, self.dimensao)

            # ACUMULA, e isto não é detalhe: se o mesmo caractere aparece
            # duas vezes na janela ("aa"), as duas contribuições são da
            # MESMA linha da tabela. Atribuir em vez de somar perderia uma
            # delas em silêncio — o treino roda, a perda cai, e a tabela
            # aprende torto.
            np.add.at(gt, list(janela), por_posicao)

            perda += float(EntropiaCruzadaCategorica.fn(
                self.rede.camadas[-1].ultima_ativacao, y))

        n = len(lote)
        for i, c in enumerate(self.rede.camadas):
            c.pesos -= (taxa / n) * gp[i]
            c.vies  -= (taxa / n) * gv[i]
        self.tabela -= (taxa / n) * gt

        return perda / n / LN2

    @property
    def n_parametros(self):
        return self.tabela.size + self.rede.n_parametros

    # ── disco ────────────────────────────────────────────────────────
    def guardar(self, caminho, extra=None):
        d = {
            "alfabeto": self.alfabeto,
            "contexto": self.contexto,
            "dimensao": self.dimensao,
            "tabela": self.tabela.tolist(),
            "camadas": [{"pesos": c.pesos.tolist(), "vies": c.vies.ravel().tolist()}
                        for c in self.rede.camadas],
            "parametros": self.n_parametros,
        }
        if extra:
            d.update(extra)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(d, f)


    @classmethod
    def carregar(cls, caminho):
        """Retoma um modelo do disco, com os pesos exatamente onde pararam.

        POR QUE ISTO É NECESSÁRIO E NÃO CONVENIÊNCIA

        Um modelo de linguagem precisa de dezenas de passadas pelo corpus, e
        isso não cabe numa sessão só. Sem retomada, "treinar mais" significa
        começar do zero de novo — e a curva que já custou horas é jogada fora
        toda vez.

        Guardar e retomar também é o que torna o experimento honesto: dá para
        parar, medir, e continuar exatamente do mesmo ponto, em vez de
        comparar duas execuções que sortearam pesos iniciais diferentes.
        """
        import numpy as _np
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)

        m = cls(d["alfabeto"], d["contexto"], d["dimensao"],
                oculta=len(d["camadas"][0]["vies"]), semente=0)
        m.tabela = _np.array(d["tabela"], dtype=float)
        for c, salvo in zip(m.rede.camadas, d["camadas"]):
            c.pesos = _np.array(salvo["pesos"], dtype=float)
            c.vies = _np.array(salvo["vies"], dtype=float).reshape(-1, 1)
        return m, d

    def __repr__(self):
        return (f"ModeloDeLinguagem(contexto={self.contexto}, "
                f"dim={self.dimensao}, alfabeto={len(self.alfabeto)}, "
                f"{self.n_parametros:,} parametros)")
