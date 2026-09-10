# -*- coding: utf-8 -*-
"""ATENÇÃO DO ZERO — Q, K, V, e a conferência numérica do gradiente.

POR QUE ATENÇÃO, E NÃO MAIS TREINO

A rede multi-rótulo faz MÉDIA dos vetores das peças do parágrafo. Medido:

    pedidos no parágrafo    conjunto exato
            1                   48,4%
            2                   28,1%
            3                   10,2%
            4                    2,9%

A média dá o mesmo peso a toda palavra e apaga a informação de QUAL
palavra pertence a QUAL pedido. Quatro pedidos viram um vetor só. Não é
falta de época: é a peça errada.

O DESENHO: UMA CONSULTA POR INTENÇÃO

    X   (n, D)      as peças do texto, já embutidas
    K = X·Wk        (n, d)   o que cada peça OFERECE
    V = X·Wv        (n, d)   o que cada peça ENTREGA
    Q   (S, d)      uma consulta APRENDIDA por intenção — a pergunta
                             "quais palavras deste texto falam de mim?"

    Sc = Q·Kᵀ/√d    (S, n)   quanto cada intenção liga para cada peça
    A  = softmax_n(Sc)       distribuição sobre as PALAVRAS, por intenção
    C  = A·V        (S, d)   o resumo do texto do ponto de vista de cada uma
    z  = Σ(w⊙C) + b (S,)
    p  = sigmoide(z)

A diferença que interessa: `login` puxa a consulta do login, `pagamento`
puxa a do pagamento, e as duas olham para pedaços DIFERENTES do mesmo
parágrafo em vez de se dissolverem numa média.

O √d NÃO É ENFEITE: sem ele o produto escalar cresce com d, o softmax
satura e o gradiente morre. É a mesma razão do artigo de 2017.

A CONFERÊNCIA NUMÉRICA VEM ANTES DO TREINO

Gradiente errado não dá erro: o treino roda, a perda até cai um pouco, e
o número final mente. Então cada peso é conferido contra
(f(x+ε) − f(x−ε)) / 2ε antes de qualquer época.
"""
import math

import numpy as np


class AtencaoMultiRotulo:
    """Uma cabeça de atenção com uma consulta por saída."""

    def __init__(self, n_pecas, n_saidas, dimensao=32, chave=24, semente=7):
        r = np.random.default_rng(semente)
        self.D, self.d, self.S = dimensao, chave, n_saidas
        self.E = r.normal(0, 0.1, (n_pecas, dimensao))
        self.Wk = r.normal(0, 1 / math.sqrt(dimensao), (dimensao, chave))
        self.Wv = r.normal(0, 1 / math.sqrt(dimensao), (dimensao, chave))
        self.Q = r.normal(0, 1 / math.sqrt(chave), (n_saidas, chave))
        self.w = r.normal(0, 1 / math.sqrt(chave), (n_saidas, chave))
        self.b = np.zeros(n_saidas)

    # ── frente ───────────────────────────────────────────────────────
    def frente(self, pecas):
        X = self.E[pecas]                       # (n, D)
        K = X @ self.Wk                         # (n, d)
        V = X @ self.Wv                         # (n, d)
        Sc = (self.Q @ K.T) / math.sqrt(self.d)  # (S, n)
        Sc = Sc - Sc.max(axis=1, keepdims=True)
        A = np.exp(Sc)
        A /= A.sum(axis=1, keepdims=True)       # softmax SOBRE AS PALAVRAS
        C = A @ V                               # (S, d)
        z = (self.w * C).sum(axis=1) + self.b   # (S,)
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))
        return {"X": X, "K": K, "V": V, "A": A, "C": C, "z": z, "p": p}

    # ── gradiente ────────────────────────────────────────────────────
    def gradiente(self, pecas, y, peso_sim=1.0):
        """Devolve (perda, gradientes). `y` é o vetor 0/1 das saídas."""
        f = self.frente(pecas)
        p, A, C, V, K, X = f["p"], f["A"], f["C"], f["V"], f["K"], f["X"]

        pe = 1.0 + (peso_sim - 1.0) * y
        eps = 1e-12
        perda = -(pe * (y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))).sum()

        dz = (p - y) * pe                        # (S,)
        gw = dz[:, None] * C                     # (S, d)
        gb = dz
        dC = dz[:, None] * self.w                # (S, d)
        dA = dC @ V.T                            # (S, n)
        dV = A.T @ dC                            # (n, d)
        # jacobiano do softmax, linha a linha
        dSc = A * (dA - (dA * A).sum(axis=1, keepdims=True))
        dSc /= math.sqrt(self.d)
        gQ = dSc @ K                             # (S, d)
        dK = dSc.T @ self.Q                      # (n, d)
        gWk = X.T @ dK                           # (D, d)
        gWv = X.T @ dV                           # (D, d)
        dX = dK @ self.Wk.T + dV @ self.Wv.T     # (n, D)
        return perda, {"w": gw, "b": gb, "Q": gQ, "Wk": gWk, "Wv": gWv, "dX": dX}

    def passo(self, lote, taxa, peso_sim=1.0):
        """Um passo sobre um lote de (peças, y). Devolve a perda média."""
        acum = {k: np.zeros_like(getattr(self, k)) for k in ("w", "b", "Q", "Wk", "Wv")}
        gE = {}
        total = 0.0
        for pecas, y in lote:
            perda, g = self.gradiente(pecas, y, peso_sim)
            total += perda
            for k in acum:
                acum[k] += g[k]
            for j, i in enumerate(pecas):
                gE[i] = gE.get(i, 0.0) + g["dX"][j]
        n = len(lote)
        for k in acum:
            setattr(self, k, getattr(self, k) - (taxa / n) * acum[k])
        for i, gi in gE.items():
            self.E[i] -= (taxa / n) * gi
        return total / n


# ══════════════════════════════════════════════════════════════════════
#  A CONFERÊNCIA NUMÉRICA — antes de treinar, e não depois
# ══════════════════════════════════════════════════════════════════════
def conferir(semente=3, eps=1e-5):
    """Confere o gradiente analítico contra a diferença central.

    O CUIDADO QUE FALTOU NA PRIMEIRA VERSÃO, e que quase me fez consertar
    um código que estava certo:

    dividir |num − ana| pelo próprio valor é honesto quando o valor é
    grande, e é uma armadilha quando ele é minúsculo. O pior caso do `Q`
    tinha gradiente 7,87e-07 e diferença absoluta de 1,71e-10 — os dois
    números batiam em dez casas decimais, e o relativo dava 2,17e-04, que
    parece defeito.

    Como se sabe que era ruído e não erro: baixando o passo de 1e-4 para
    1e-6 o relativo PIOROU (2,99e-06 → 2,17e-04). Derivada errada não
    melhora quando o passo cresce; arredondamento sim, porque a subtração
    de dois números quase iguais perde casas.

    Então o veredito olha os dois: relativo com PISO no denominador, e
    absoluto. Passa quem satisfaz um dos dois.
    """
    r = np.random.default_rng(semente)
    rede = AtencaoMultiRotulo(n_pecas=40, n_saidas=6, dimensao=10, chave=7,
                              semente=semente)
    pecas = list(r.integers(0, 40, size=9))
    y = (r.random(6) < 0.4).astype(float)

    def perda_agora():
        f = rede.frente(pecas)
        p = f["p"]
        e = 1e-12
        return -(y * np.log(p + e) + (1 - y) * np.log(1 - p + e)).sum()

    _, g = rede.gradiente(pecas, y)
    # a tabela de embutimento entra pela porta de trás: dX volta para as
    # linhas usadas, e a MESMA peça pode aparecer duas vezes na frase
    gE = np.zeros_like(rede.E)
    for j, i in enumerate(pecas):
        gE[i] += g["dX"][j]

    piores = []
    for nome in ("w", "b", "Q", "Wk", "Wv", "E"):
        M = rede.E if nome == "E" else getattr(rede, nome)
        G = gE if nome == "E" else g[nome]
        pior = (0.0, 0.0)
        # amostra: conferir todo peso de todas as matrizes é caro e não
        # acrescenta — o que se procura é UM erro sistemático
        idx = [tuple(r.integers(0, s) for s in M.shape) for _ in range(60)]
        for k in idx:
            guardado = M[k]
            M[k] = guardado + eps
            mais = perda_agora()
            M[k] = guardado - eps
            menos = perda_agora()
            M[k] = guardado
            num = (mais - menos) / (2 * eps)
            ana = G[k]
            absoluto = abs(num - ana)
            # PISO no denominador: sem ele, gradiente minúsculo vira
            # "erro" gigante por divisão, e não é erro nenhum.
            relativo = absoluto / max(abs(num), abs(ana), 1e-4)
            if relativo > pior[0]:
                pior = (relativo, absoluto)
            pior = (pior[0], max(pior[1], absoluto))
        piores.append((nome, pior[0], pior[1]))
    return piores


if __name__ == "__main__":
    print("CONFERÊNCIA NUMÉRICA DO GRADIENTE")
    print("  (diferença relativa entre a derivada analítica e a numérica)")
    print(f"  {'peso':<6}{'relativo':>13}{'absoluto':>13}   veredito")
    tudo_bem = True
    for nome, rel, abs_ in conferir():
        ok = rel < 1e-5 or abs_ < 1e-9
        tudo_bem &= ok
        print(f"  {nome:<6}{rel:>13.2e}{abs_:>13.2e}   {'ok' if ok else 'ERRADO'}")
    print("\n  " + ("gradiente confere — pode treinar"
                    if tudo_bem else "NÃO TREINE: a conta está errada"))
