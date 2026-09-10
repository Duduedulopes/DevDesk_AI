# -*- coding: utf-8 -*-
"""A MESMA atenção, em lote — e a prova de que é a mesma.

A versão de referência (`atencao.py`) roda um exemplo por vez. É a que se
lê para entender, e é a que o verificador numérico aprovou. Mas 288 mil
passagens num laço de Python levam meia hora, e meia hora por experimento
mata a vontade de experimentar.

Esta aqui faz o mesmo com as frases EMPILHADAS e preenchidas até o mesmo
comprimento. O empilhamento traz um cuidado que não existia antes: as
posições de enchimento não podem receber atenção nenhuma, senão a rede
aprende a olhar para o vazio. Elas levam −infinito ANTES do softmax, que
é o jeito certo — zerar DEPOIS deixaria a soma diferente de 1.

E não se confia nisto de graça: `conferir_contra_referencia()` roda as
duas em cima dos mesmos pesos e compara saída e gradiente.
"""
import math

import numpy as np

TETO = 5.0      # norma máxima do gradiente por passo


class AtencaoEmLote:
    def __init__(self, n_pecas, n_saidas, dimensao=64, chave=32, semente=7):
        r = np.random.default_rng(semente)
        self.D, self.d, self.S = dimensao, chave, n_saidas
        self.E = r.normal(0, 0.1, (n_pecas, dimensao))
        self.Wk = r.normal(0, 1 / math.sqrt(dimensao), (dimensao, chave))
        self.Wv = r.normal(0, 1 / math.sqrt(dimensao), (dimensao, chave))
        self.Q = r.normal(0, 1 / math.sqrt(chave), (n_saidas, chave))
        self.w = r.normal(0, 1 / math.sqrt(chave), (n_saidas, chave))
        self.b = np.zeros(n_saidas)

    @staticmethod
    def empilhar(listas):
        """(B, n) de índices + (B, n) de máscara, preenchidos com zero."""
        n = max(len(x) for x in listas)
        idx = np.zeros((len(listas), n), dtype=np.int64)
        masc = np.zeros((len(listas), n))
        for i, x in enumerate(listas):
            idx[i, :len(x)] = x
            masc[i, :len(x)] = 1.0
        return idx, masc

    def frente(self, idx, masc):
        X = self.E[idx]                                  # (B, n, D)
        K = X @ self.Wk                                  # (B, n, d)
        V = X @ self.Wv
        Sc = np.einsum("sd,bnd->bsn", self.Q, K) / math.sqrt(self.d)
        # O ENCHIMENTO NÃO PODE SER OLHADO: o que é enchimento leva um
        # número muito negativo ANTES do softmax, e aí o peso dele vira
        # zero e a soma continua valendo 1. Zerar DEPOIS do softmax
        # deixaria a soma diferente de 1, que é outro erro.
        #
        # −1e9 e não −1e30: depois de exp() os dois dão zero igual, mas
        # −1e30 estoura a subtração do máximo quando o próprio Sc cresce,
        # e o resultado é NaN silencioso. Foi o que aconteceu no primeiro
        # treino: a perda virou NaN e o laço seguiu adiante sem reclamar.
        Sc = np.clip(Sc, -60.0, 60.0)
        Sc = np.where(masc[:, None, :] > 0, Sc, -1e9)
        Sc = Sc - Sc.max(axis=2, keepdims=True)
        A = np.exp(Sc)
        A /= A.sum(axis=2, keepdims=True)
        C = np.einsum("bsn,bnd->bsd", A, V)
        z = np.einsum("sd,bsd->bs", self.w, C) + self.b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))
        return X, K, V, A, C, p

    def passo(self, idx, masc, Y, taxa, peso_sim=1.0):
        B = len(idx)
        X, K, V, A, C, p = self.frente(idx, masc)
        pe = 1.0 + (peso_sim - 1.0) * Y
        e = 1e-12
        perda = -(pe * (Y * np.log(p + e) + (1 - Y) * np.log(1 - p + e))).sum() / B

        dz = (p - Y) * pe / B                            # (B, S)
        gw = np.einsum("bs,bsd->sd", dz, C)
        gb = dz.sum(axis=0)
        dC = np.einsum("bs,sd->bsd", dz, self.w)
        dA = np.einsum("bsd,bnd->bsn", dC, V)
        dV = np.einsum("bsn,bsd->bnd", A, dC)
        dSc = A * (dA - (dA * A).sum(axis=2, keepdims=True)) / math.sqrt(self.d)
        dSc *= masc[:, None, :]
        gQ = np.einsum("bsn,bnd->sd", dSc, K)
        dK = np.einsum("bsn,sd->bnd", dSc, self.Q)
        gWk = np.einsum("bnD,bnd->Dd", X, dK)
        gWv = np.einsum("bnD,bnd->Dd", X, dV)
        dX = dK @ self.Wk.T + dV @ self.Wv.T
        dX *= masc[:, :, None]

        # FREIO NO GRADIENTE. Sem ele isto explodiu: `Sc` cresceu, a
        # subtração do máximo virou NaN e o treino seguiu adiante
        # calculando com lixo, sem reclamar. Pesar os "sim" em 12×
        # multiplica o gradiente por 12 junto — o erro foi meu, de pôr
        # peso sem pôr limite.
        #
        # Corta pela NORMA do conjunto, não peso a peso: cortar cada peso
        # sozinho mudaria a DIREÇÃO do gradiente, e a direção é a
        # informação que ele carrega. Assim só o tamanho muda.
        #
        # E LOTE ESTRAGADO NÃO ENCOSTA NOS PESOS: um NaN que entra
        # contamina a rede inteira de uma vez, e daí nada se recupera.
        gs = [gw, gb, gQ, gWk, gWv, dX]
        norma = math.sqrt(sum(float((g * g).sum()) for g in gs))
        if not (math.isfinite(norma) and math.isfinite(perda)):
            return float("nan")
        if norma > TETO:
            k = TETO / norma
            gw, gb, gQ, gWk, gWv, dX = (g * k for g in gs)

        self.w -= taxa * gw
        self.b -= taxa * gb
        self.Q -= taxa * gQ
        self.Wk -= taxa * gWk
        self.Wv -= taxa * gWv
        np.add.at(self.E, idx.reshape(-1), -taxa * dX.reshape(-1, self.D))
        return perda


def conferir_contra_referencia():
    """As duas implementações, os mesmos pesos, o mesmo dado."""
    import sys
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
    from nucleo.atencao import AtencaoMultiRotulo

    r = np.random.default_rng(11)
    ref = AtencaoMultiRotulo(50, 7, dimensao=12, chave=8, semente=5)
    lot = AtencaoEmLote(50, 7, dimensao=12, chave=8, semente=5)
    for k in ("E", "Wk", "Wv", "Q", "w", "b"):
        setattr(lot, k, getattr(ref, k).copy())

    frases = [list(r.integers(0, 50, size=n)) for n in (6, 11, 4)]
    Y = (r.random((3, 7)) < 0.4).astype(float)
    idx, masc = AtencaoEmLote.empilhar(frases)

    _, _, _, _, _, p_lote = lot.frente(idx, masc)
    p_ref = np.array([ref.frente(f)["p"] for f in frases])
    dif_saida = np.abs(p_lote - p_ref).max()

    # gradiente: um passo com taxa 1 em cada, e comparar o deslocamento
    ref.passo([(f, y) for f, y in zip(frases, Y)], 1.0)
    lot.passo(idx, masc, Y, 1.0)
    difs = {k: np.abs(getattr(ref, k) - getattr(lot, k)).max()
            for k in ("E", "Wk", "Wv", "Q", "w", "b")}
    return dif_saida, difs


if __name__ == "__main__":
    ds, dg = conferir_contra_referencia()
    print("A VERSÃO EM LOTE É A MESMA DA REFERÊNCIA?")
    print(f"  maior diferença na saída:     {ds:.2e}")
    for k, v in dg.items():
        print(f"  maior diferença no peso {k:<3}  {v:.2e}")
    tudo = ds < 1e-12 and all(v < 1e-12 for v in dg.values())
    print("\n  " + ("são a mesma conta" if tudo else "DIFEREM — não use a de lote"))
