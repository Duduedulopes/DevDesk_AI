# -*- coding: utf-8 -*-
"""A REDE QUE DECIDE — e por que isto funciona onde soletrar não funcionou.

O QUE A MEDIDA ANTERIOR DISSE, E O QUE SE FAZ COM ISSO

Escrevendo letra por letra, das 45 posições de uma consulta só 5 dependem
do pedido — e elas valem 31% da informação. Errar o método na letra 11
custa 1,5 bit numa conta que soma 45 posições. Sai mais barato chutar
sempre `Any` do que aprender que "soma" quer dizer `Sum`. A rede não
aprendeu mal: ela minimizou exatamente o que eu mandei minimizar.

Aqui o objetivo muda de forma. São QUATRO decisões, cada uma com a sua
própria perda:

    operação      "soma" → Sum          (10 opções)
    propriedade   "valor" → Valor       (as que existem na classe)
    comparação    "acima de" → >        (6 opções + nenhuma)
    valor         1000 → 1000m          (o tipo manda no sufixo)

Errar a operação agora custa a perda INTEIRA daquela decisão, não 1,5 bit
diluído em 45. É a mesma lição do escritor de caminhos, que só saiu de
58% para 79% quando a FORMA do problema mudou — e não quando treinou mais.

A REDE CONTINUA DECIDINDO TUDO. O que ela deixa de fazer é soletrar
`S-u-m`, que não é inteligência nenhuma: é ortografia de C#, e disso o
molde dá conta sem errar nunca.

O CASAMENTO DE NOMES É O QUE FAZ ISTO VALER EM QUALQUER PROJETO

A propriedade não é uma classe fixa de um softmax — seria preciso
retreinar a cada projeto novo. Ela é PONTUADA: a rede lê o pedido, lê o
NOME da propriedade (`TaxaProcessamento` → "taxa processamento"), e diz o
quanto um combina com o outro. Propriedade que ela nunca viu na vida
recebe nota, porque a nota é feita dos pedaços do nome.

    nota(pedido, nome) = (u·W)·v      u = resumo do pedido
                                      v = resumo do nome
                                      W = o que se aprende

Treina-se escolhendo entre as propriedades QUE EXISTEM naquela classe: a
certa contra as outras. É a mesma conta do softmax, só que as opções mudam
a cada pedido — que é exatamente o mundo real.
"""
import collections
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from texto.vocabulario import normalizar, pedacos  # noqa: E402
from modelo.moldes_linq import OPERACOES, COMPARACOES  # noqa: E402

OPS = sorted(OPERACOES)
CMPS = sorted(COMPARACOES) + ["nenhuma"]


def sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def softmax(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def pecas_com_ordem(texto):
    """Os pedaços de sempre MAIS os pares de palavras vizinhas.

    POR QUE OS PARES, E POR QUE SÓ AQUI

    O resumo do pedido é a MÉDIA dos vetores dos pedaços, e média não tem
    ordem. Some-se a isso que os pedaços são palavras e trigramas de
    palavra, e o resultado é este, medido:

        "me lista as transações do MENOR id para o MAIOR"
        "me lista as transações do MAIOR id para o MENOR"

        conjunto de pedaços diferentes entre as duas: NENHUM.

    Para a rede as duas frases eram o mesmo objeto — e ela tinha de
    responder `OrderBy` para uma e `OrderByDescending` para a outra. Não é
    exemplo difícil, é exemplo IMPOSSÍVEL, e nenhum treino a mais
    resolveria.

    O par vizinho ("do~menor", "menor~id") carrega a ordem local, que é
    exatamente a informação que faltava. Não vira modelo de sequência —
    continua sendo média — mas passa a distinguir vizinhança.

    Fica nesta peneira, e não no `texto/vocabulario.py`, porque os outros
    modelos do projeto foram treinados com os pedaços de lá: mexer neles
    invalidaria detector, etiquetador e compositor de uma vez.
    """
    ps = list(pedacos(texto))
    palavras = normalizar(texto).split()
    return ps + [f"{a}~{b}" for a, b in zip(palavras, palavras[1:])]


class Peneira:
    """As peças de texto, compartilhadas entre pedido e nome de propriedade.

    UMA tabela só, de propósito: "valor" no pedido e `Valor` no nome da
    propriedade dividem os mesmos trigramas, e dividir a tabela é dar de
    graça metade do casamento. Separá-las obrigaria a rede a aprender do
    zero que as duas palavras são a mesma coisa.
    """

    def __init__(self, textos=(), minimo=1):
        c = collections.Counter()
        for t in textos:
            c.update(set(pecas_com_ordem(t)))
        self.pecas = ["<?>"] + sorted(p for p, n in c.items() if n >= minimo)
        self.indice = {p: i for i, p in enumerate(self.pecas)}

    @classmethod
    def de_lista(cls, pecas):
        p = cls()
        p.pecas = list(pecas)
        p.indice = {x: i for i, x in enumerate(p.pecas)}
        return p

    def __len__(self):
        return len(self.pecas)

    def ids(self, texto):
        v = [self.indice[p] for p in pecas_com_ordem(texto) if p in self.indice]
        return v or [0]


class Decisor:
    def __init__(self, n_pecas, dim=48, ocultos=96, semente=7):
        r = np.random.default_rng(semente)
        self.d, self.H = dim, ocultos
        self.E = r.normal(0, 0.1, (n_pecas, dim))            # peças, compartilhada
        # cabeça da OPERAÇÃO
        self.W1 = r.normal(0, 1 / math.sqrt(dim), (dim, ocultos))
        self.b1 = np.zeros(ocultos)
        self.W2 = r.normal(0, 1 / math.sqrt(ocultos), (ocultos, len(OPS)))
        self.b2 = np.zeros(len(OPS))
        # cabeça da COMPARAÇÃO
        self.W3 = r.normal(0, 1 / math.sqrt(dim), (dim, ocultos))
        self.b3 = np.zeros(ocultos)
        self.W4 = r.normal(0, 1 / math.sqrt(ocultos), (ocultos, len(CMPS)))
        self.b4 = np.zeros(len(CMPS))
        # CASAMENTO de nomes: nota = (u·M)·v
        #
        # DOIS matriz, e não uma. "qual lista?" e "qual propriedade?" são
        # perguntas diferentes: a primeira olha para o substantivo do
        # pedido ("transacoes", "logs"), a segunda para o atributo
        # ("valor", "severidade"). Uma matriz só teria de servir às duas e
        # serviria mal às duas.
        #
        # A primeira versão tinha só a `M` — e eu usava ela para escolher
        # a lista TAMBÉM, sem nunca ter treinado isso. A cabeça da lista
        # respondia no chute, e o erro aparecia como `logs.Sum(...)` para
        # um pedido que dizia "transacoes" com todas as letras.
        self.M = np.eye(dim) + r.normal(0, 0.01, (dim, dim))    # propriedade
        self.Me = np.eye(dim) + r.normal(0, 0.01, (dim, dim))   # lista
        # TERCEIRA MATRIZ: a propriedade do FILTRO.
        #
        # "soma o VALOR das transações com STATUS concluído" tem duas
        # propriedades na mesma frase, e elas têm papéis diferentes: uma é
        # o que se soma, a outra é o que se filtra. Uma matriz só teria de
        # apontar para as duas ao mesmo tempo a partir do mesmo pedido, o
        # que é impossível — ela devolve UMA ordem de preferência.
        #
        # É a mesma lição da `Me`: pergunta diferente, régua diferente.
        self.Mf = np.eye(dim) + r.normal(0, 0.01, (dim, dim))   # filtro

    @property
    def n_parametros(self):
        return sum(x.size for x in (self.E, self.W1, self.b1, self.W2, self.b2,
                                    self.W3, self.b3, self.W4, self.b4,
                                    self.M, self.Me, self.Mf))

    def resumo(self, ids):
        return self.E[ids].mean(axis=0)

    # ── guardar e abrir ──────────────────────────────────────────────
    PESOS = ("E", "W1", "b1", "W2", "b2", "W3", "b3", "W4", "b4",
             "M", "Me", "Mf")

    def para_dicionario(self):
        d = {"dim": self.d, "ocultos": self.H,
             "operacoes": list(OPS), "comparacoes": list(CMPS)}
        d.update({k: getattr(self, k).tolist() for k in self.PESOS})
        return d

    @classmethod
    def de_dicionario(cls, d):
        # A LISTA DE OPERAÇÕES TEM DE SER A MESMA, E ISTO CUSTOU UMA HORA.
        #
        # A rede guarda 10 números na saída da operação; qual número é qual
        # operação vem de `sorted(OPERACOES)`, que mora no CÓDIGO. Ao
        # acrescentar `filtrar_valor` aos moldes, a lista virou 11 nomes e
        # tudo depois de "filtrar" andou uma casa: o número que dizia
        # `Sum` passou a ser lido como `Select`.
        #
        # E nada quebrou. O modelo carregou, respondeu, e o LINQ até
        # COMPILAVA — só respondia outra coisa. Erro que não levanta a mão
        # é o caro. Agora ele levanta.
        if d.get("operacoes") and list(d["operacoes"]) != list(OPS):
            faltam = set(OPS) - set(d["operacoes"])
            sobram = set(d["operacoes"]) - set(OPS)
            raise ValueError(
                "este modelo foi treinado com outra lista de operações "
                f"({len(d['operacoes'])} contra {len(OPS)} de agora"
                + (f"; novas: {', '.join(sorted(faltam))}" if faltam else "")
                + (f"; sumiram: {', '.join(sorted(sobram))}" if sobram else "")
                + "). Retreine: python programas/treinar_consulta.py <pasta>")
        if d.get("comparacoes") and list(d["comparacoes"]) != list(CMPS):
            raise ValueError("este modelo foi treinado com outra lista de "
                             "comparações. Retreine.")
        faltando = [k for k in cls.PESOS if k not in d]
        if faltando:
            raise ValueError(
                f"faltam pesos neste modelo ({', '.join(faltando)}): ele é de "
                "uma versão anterior da rede. Retreine: "
                "python programas/treinar_consulta.py <pasta>")
        r = cls(len(d["E"]), dim=d["dim"], ocultos=d["ocultos"])
        for k in cls.PESOS:
            setattr(r, k, np.array(d[k], dtype=float))
        return r

    # ── operação e comparação: softmax comum ─────────────────────────
    def _cabeca(self, u, W1, b1, W2, b2):
        h = sig(u @ W1 + b1)
        return h, softmax(h @ W2 + b2)

    def operacao(self, u):
        return self._cabeca(u, self.W1, self.b1, self.W2, self.b2)

    def comparacao(self, u):
        return self._cabeca(u, self.W3, self.b3, self.W4, self.b4)

    # ── casamento: nota de cada candidato, softmax entre eles ────────
    @staticmethod
    def unitario(vs):
        """Cada nome candidato com comprimento 1. Isto NÃO é enfeite.

        Sem isto, quem ganha a disputa é o vetor mais COMPRIDO, e o
        comprimento mede quantas vezes o treino empurrou aquele nome — não
        o quanto ele combina com o pedido. Foi medido duas vezes no mesmo
        dia: `SuspeitaFraude` (norma 1,97) ganhando de `Concluida` (0,66)
        num pedido que dizia "concluida"; e `Id` ganhando de `Valor` em
        "soma de valor", porque `Id` tem três pedaços e recebe empurrão em
        todo exemplo de soma.

        Normalizar SÓ na hora de responder custaria 4,2% no corpus — a
        rede teria sido treinada numa geometria e cobrada em outra. Por
        isso a normalização está aqui dentro, e o treino passa por ela.
        """
        return vs / (np.linalg.norm(vs, axis=1, keepdims=True) + 1e-12)

    def notas(self, u, vs, qual="prop"):
        """vs: (K, d) — os resumos dos K nomes candidatos."""
        M = {"prop": self.M, "lista": self.Me, "filtro": self.Mf}[qual]
        return softmax(self.unitario(vs) @ (M.T @ u))

    @staticmethod
    def _casar(vs, q, certo):
        """A conta do casamento e a sua derivada, com a normalização dentro.

        s_j = v̂_j · q com v̂ = v/‖v‖. Então:

            ∂s_j/∂q = v̂_j
            ∂s_j/∂v_j = (I − v̂_j v̂_jᵀ) q / ‖v_j‖

        O termo (I − v̂v̂ᵀ) é o que sobra do gradiente depois de tirar a
        parte que só mudaria o COMPRIMENTO — e é exatamente a parte que a
        normalização joga fora. Esquecê-lo seria derivar outra função, e a
        conferência numérica acusaria.
        """
        n = np.linalg.norm(vs, axis=1, keepdims=True) + 1e-12
        vh = vs / n
        s = vh @ q
        p = softmax(s)
        dz = p.copy(); dz[certo] -= 1.0
        dq = vh.T @ dz
        # (I − v̂v̂ᵀ)q  =  q − (v̂·q) v̂
        dvs = (dz / n.ravel())[:, None] * (q[None, :] - s[:, None] * vh)
        return p, dz, dq, dvs

    # ── um passo sobre um exemplo ────────────────────────────────────
    def passo(self, ids_pedido, k_op, k_cmp, ids_cands, k_certo,
              ids_listas, k_lista, ids_agreg, ids_filtro, k_filtro, taxa):
        """`ids_agreg` e `ids_filtro` são as METADES da frase.

        Sem filtro, as duas são a frase inteira. Com filtro, a primeira é
        o que vem antes do "com/onde/que tem" e a segunda o que vem
        depois — e é isso que impede as duas cabeças de trocarem de lugar.
        """
        u = self.resumo(ids_pedido)
        ua = self.resumo(ids_agreg)
        du = np.zeros_like(u)
        dua = np.zeros_like(ua)
        perda = 0.0

        # operação
        h1, p1 = self.operacao(u)
        perda += -math.log(max(p1[k_op], 1e-15))
        dz1 = p1.copy(); dz1[k_op] -= 1.0
        gW2 = np.outer(h1, dz1); gb2 = dz1
        dh1 = (self.W2 @ dz1) * h1 * (1 - h1)
        gW1 = np.outer(u, dh1); gb1 = dh1
        du += self.W1 @ dh1

        # comparação
        h2, p2 = self.comparacao(u)
        perda += -math.log(max(p2[k_cmp], 1e-15))
        dz2 = p2.copy(); dz2[k_cmp] -= 1.0
        gW4 = np.outer(h2, dz2); gb4 = dz2
        dh2 = (self.W4 @ dz2) * h2 * (1 - h2)
        gW3 = np.outer(u, dh2); gb3 = dh2
        du += self.W3 @ dh2

        # casamento da propriedade AGREGADA — sobre a sua metade da frase
        vs = np.array([self.resumo(c) for c in ids_cands])       # (K, d)
        q = self.M.T @ ua                                         # (d,)
        p3, dz3, dq, dvs = self._casar(vs, q, k_certo)
        perda += -math.log(max(p3[k_certo], 1e-15))
        gM = np.outer(ua, dq)                                     # M.T@ua → dM = ua ⊗ dq
        dua += self.M @ dq

        # casamento da LISTA — a cabeça que faltava treinar
        vl = np.array([self.resumo(c) for c in ids_listas])
        ql = self.Me.T @ u
        p4, dz4, dql, dvl = self._casar(vl, ql, k_lista)
        perda += -math.log(max(p4[k_lista], 1e-15))
        gMe = np.outer(u, dql)
        du += self.Me @ dql

        # casamento da propriedade do FILTRO — só nos pedidos que têm um.
        #
        # Sem o `if`, os pedidos sem filtro empurrariam a `Mf` para um alvo
        # inventado, e ela aprenderia a apontar para qualquer coisa. Perda
        # só existe onde existe resposta certa.
        gMf = None
        if k_filtro is not None:
            uf = self.resumo(ids_filtro)
            qf = self.Mf.T @ uf
            p5, dz5, dqf, dvf = self._casar(vs, qf, k_filtro)
            perda += -math.log(max(p5[k_filtro], 1e-15))
            gMf = np.outer(uf, dqf)
            duf = self.Mf @ dqf

        # aplica
        if gMf is not None:
            self.Mf -= taxa * gMf
            np.add.at(self.E, np.asarray(ids_filtro), -taxa * duf / len(ids_filtro))
            for j, c in enumerate(ids_cands):
                np.add.at(self.E, np.asarray(c), -taxa * dvf[j] / len(c))
        self.Me -= taxa * gMe
        for j, c in enumerate(ids_listas):
            np.add.at(self.E, np.asarray(c), -taxa * dvl[j] / len(c))
        self.W2 -= taxa * gW2; self.b2 -= taxa * gb2
        self.W1 -= taxa * gW1; self.b1 -= taxa * gb1
        self.W4 -= taxa * gW4; self.b4 -= taxa * gb4
        self.W3 -= taxa * gW3; self.b3 -= taxa * gb3
        self.M -= taxa * gM
        np.add.at(self.E, np.asarray(ids_pedido), -taxa * du / len(ids_pedido))
        np.add.at(self.E, np.asarray(ids_agreg), -taxa * dua / len(ids_agreg))
        for j, c in enumerate(ids_cands):
            np.add.at(self.E, np.asarray(c), -taxa * dvs[j] / len(c))
        return perda


# ══════════════════════════════════════════════════════════════════════
#  CONFERÊNCIA NUMÉRICA — a peça nova aqui é o casamento bilinear
# ══════════════════════════════════════════════════════════════════════
def conferir(semente=4, eps=1e-5):
    r = np.random.default_rng(semente)
    rede = Decisor(25, dim=6, ocultos=8, semente=semente)
    ped = [int(x) for x in r.integers(0, 25, 4)]
    agreg = [int(x) for x in r.integers(0, 25, 3)]
    filtro = [int(x) for x in r.integers(0, 25, 3)]
    cands = [[int(x) for x in r.integers(0, 25, 3)] for _ in range(5)]
    listas = [[int(x) for x in r.integers(0, 25, 2)] for _ in range(3)]
    k_op, k_cmp, k_certo, k_lista, k_filtro = 2, 3, 1, 2, 4

    def perda():
        u = rede.resumo(ped)
        _, p1 = rede.operacao(u)
        _, p2 = rede.comparacao(u)
        vs = np.array([rede.resumo(c) for c in cands])
        p3 = rede.notas(rede.resumo(agreg), vs)
        vl = np.array([rede.resumo(c) for c in listas])
        p4 = rede.notas(u, vl, "lista")
        p5 = rede.notas(rede.resumo(filtro), vs, "filtro")
        return (-math.log(max(p1[k_op], 1e-15)) - math.log(max(p2[k_cmp], 1e-15))
                - math.log(max(p3[k_certo], 1e-15)) - math.log(max(p4[k_lista], 1e-15))
                - math.log(max(p5[k_filtro], 1e-15)))

    nomes = ("E", "W1", "b1", "W2", "b2", "W3", "b3", "W4", "b4", "M", "Me", "Mf")
    antes = {k: getattr(rede, k).copy() for k in nomes}
    rede.passo(ped, k_op, k_cmp, cands, k_certo, listas, k_lista,
               agreg, filtro, k_filtro, taxa=1.0)
    grad = {k: antes[k] - getattr(rede, k) for k in nomes}
    for k in nomes:
        setattr(rede, k, antes[k].copy())

    piores = []
    for nome in nomes:
        M = getattr(rede, nome); G = grad[nome]
        pr = pa = 0.0
        for k in [tuple(int(r.integers(0, s)) for s in M.shape) for _ in range(40)]:
            g0 = M[k]
            M[k] = g0 + eps; mais = perda()
            M[k] = g0 - eps; menos = perda()
            M[k] = g0
            num = (mais - menos) / (2 * eps); ana = G[k]
            ab = abs(num - ana)
            pa = max(pa, ab); pr = max(pr, ab / max(abs(num), abs(ana), 1e-4))
        piores.append((nome, pr, pa))
    return piores


if __name__ == "__main__":
    print("CONFERÊNCIA NUMÉRICA (decisor: operação + comparação + casamento)")
    print(f"  {'peso':<5}{'relativo':>12}{'absoluto':>12}   veredito")
    tudo = True
    for nome, rel, ab in conferir():
        ok = rel < 1e-5 or ab < 1e-9
        tudo &= ok
        print(f"  {nome:<5}{rel:>12.2e}{ab:>12.2e}   {'ok' if ok else 'ERRADO'}")
    print("\n  " + ("gradiente confere — pode treinar" if tudo
                    else "NÃO TREINE: a conta está errada"))
