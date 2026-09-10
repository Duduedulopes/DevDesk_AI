# -*- coding: utf-8 -*-
"""A REDE QUE ESCREVE O LINQ — caractere por caractere, lendo o pedido.

O DESENHO, E POR QUE ELE TEM DUAS METADES

    pedido em português                    LINQ, um caractere por vez
    "soma o valor de transacoes"           "transacoes.Sum(t => t.Valor)"
            │                                        ▲
            ▼                                        │
    [LEITOR]  média dos embutimentos          [ESCRITOR]  janela dos 12
    das peças do pedido → um vetor            caracteres anteriores
    de 48 números que resume o                       ++
    que foi pedido                            o vetor do leitor
                                                     │
                                                     ▼
                                          oculta sigmoide → softmax
                                          no alfabeto do LINQ

É o modelo do Bengio de novo — o mesmo que escreve caminho de arquivo no
compositor — com uma diferença: além dos caracteres anteriores, ele
recebe um resumo do PEDIDO. Sem esse resumo ele escreveria sempre a mesma
consulta, a mais comum do corpus.

O RESUMO É APRENDIDO JUNTO. O erro volta do caractere errado até os
embutimentos das palavras do pedido. Se não voltasse, o vetor do leitor
seria ruído fixo e a condição não significaria nada — foi o defeito que
já me pegou no `EscritorCondicionado`, e por isso o gradiente é conferido
aqui também.

ESTA REDE NÃO FUNCIONOU. ELA FICA AQUI PELO MOTIVO.

Medido, com o `dotnet build` como juiz: 100% das consultas COMPILAM e 0%
estão certas. Ela escreve praticamente sempre a mesma linha, seja qual
for o pedido — e a linha compila, o que torna o fracasso silencioso.

O PORQUÊ, COM NÚMERO. Das 45 posições de uma consulta, só 5 dependem do
pedido — e essas 5 valem 31% da informação. Errar o método na letra 11
custa 1,5 bit numa conta que soma 45 posições. Um n-grama de caractere
que NUNCA vê o pedido faz 0,471 bits/char; esta rede, que vê, faz 0,311.
O pedido acrescentou 0,16 bit/char: quase nada. Ignorar o pedido é a
jogada que minimiza a perda que eu mandei minimizar. A rede não aprendeu
mal — ela aprendeu certo o objetivo errado.

O CONSERTO FOI MUDAR A FORMA DO PROBLEMA, e está em `decisor_linq.py`:
quatro decisões com quatro perdas, em vez de 45 letras com uma. Mesmo
corpus, mesmo juiz, mesma máquina: 0% → 98,7%.

Fica aqui porque peça que falha sem deixar registro do porquê é peça que
alguém reconstrói daqui a três meses.

O QUE ELA PODIA ERRAR, E ERA O AVISO

Ela escreve LETRA POR LETRA. Nada a impede de escrever `t.Valorr`,
`.Wher(` ou de esquecer um parêntese — e é por isso que o `dotnet build`
está do outro lado, como juiz. A medida honesta não é "parece certo": é
quantas das consultas COMPILAM, e dessas, quantas são a consulta certa.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

COMECO = "\x02"
FIM = "\x03"


class EscritorDeConsulta:
    def __init__(self, n_pecas, alfabeto, contexto=12, dim_char=24,
                 dim_pedido=48, ocultos=256, semente=7):
        r = np.random.default_rng(semente)
        self.alfabeto = list(alfabeto)
        self.indice = {c: i for i, c in enumerate(self.alfabeto)}
        self.C, self.dc, self.dp, self.H = contexto, dim_char, dim_pedido, ocultos
        self.V = len(self.alfabeto)
        entrada = contexto * dim_char + dim_pedido
        self.Ep = r.normal(0, 0.1, (n_pecas, dim_pedido))    # peças do pedido
        self.Ec = r.normal(0, 0.1, (self.V, dim_char))       # caracteres do LINQ
        self.W1 = r.normal(0, 1 / math.sqrt(entrada), (entrada, ocultos))
        self.b1 = np.zeros(ocultos)
        self.W2 = r.normal(0, 1 / math.sqrt(ocultos), (ocultos, self.V))
        self.b2 = np.zeros(self.V)

    @property
    def n_parametros(self):
        return sum(x.size for x in (self.Ep, self.Ec, self.W1, self.b1, self.W2, self.b2))

    # ── frente ───────────────────────────────────────────────────────
    def frente(self, janelas, resumos):
        """janelas (B, C) de índices de caractere · resumos (B, dp)."""
        emb = self.Ec[janelas].reshape(len(janelas), -1)      # (B, C*dc)
        x = np.concatenate([emb, resumos], axis=1)            # (B, C*dc+dp)
        h = 1.0 / (1.0 + np.exp(-np.clip(x @ self.W1 + self.b1, -60, 60)))
        z = h @ self.W2 + self.b2
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z)
        p /= p.sum(axis=1, keepdims=True)
        return x, h, p

    def resumir(self, listas_de_pecas):
        """A média dos embutimentos das peças de cada pedido."""
        return np.array([self.Ep[p].mean(axis=0) if len(p) else np.zeros(self.dp)
                         for p in listas_de_pecas])

    # ── um passo ─────────────────────────────────────────────────────
    def passo(self, janelas, pecas, certos, taxa):
        B = len(janelas)
        resumos = self.resumir(pecas)
        x, h, p = self.frente(janelas, resumos)
        perda = -np.log(np.maximum(p[np.arange(B), certos], 1e-15)).mean() / math.log(2)

        dz = p.copy()
        dz[np.arange(B), certos] -= 1.0
        # DIVIDIR POR ln(2), E ISTO NÃO É DETALHE.
        #
        # `p - alvo` é o gradiente da entropia cruzada em NATS. A perda que
        # este projeto reporta é em BITS (dividida por ln 2), porque bit por
        # caractere é a régua da casa — é a taxa de compressão.
        #
        # Sem esta linha o gradiente ficava ln(2) = 0,693 vezes maior que a
        # perda que ele deriva. O treino até rodaria (gradiente vezes uma
        # constante é o mesmo que taxa de aprendizado maior), mas a
        # conferência numérica acusou: erro relativo de 3,07e-01 em TODOS os
        # pesos, igualzinho. Erro igual em tudo é fator constante, e
        # 1 − 0,693 = 0,307. O número disse qual era a constante.
        dz /= B * math.log(2.0)
        gW2 = h.T @ dz
        gb2 = dz.sum(axis=0)
        dh = (dz @ self.W2.T) * h * (1 - h)
        gW1 = x.T @ dh
        gb1 = dh.sum(axis=0)
        dx = dh @ self.W1.T                                   # (B, C*dc+dp)
        demb = dx[:, :self.C * self.dc].reshape(B, self.C, self.dc)
        dres = dx[:, self.C * self.dc:]                       # (B, dp)

        self.W2 -= taxa * gW2
        self.b2 -= taxa * gb2
        self.W1 -= taxa * gW1
        self.b1 -= taxa * gb1
        # ACUMULA: a mesma letra pode estar duas vezes na janela, e as duas
        # contribuições são da MESMA linha da tabela. Atribuir perderia uma.
        np.add.at(self.Ec, np.asarray(janelas).reshape(-1),
                  -taxa * demb.reshape(-1, self.dc))
        # O ERRO VOLTA ATÉ AS PALAVRAS DO PEDIDO. A média divide o gradiente
        # entre as peças que a formaram — sem isto, o resumo do pedido nunca
        # aprenderia nada e a condição seria decoração.
        for j, ps in enumerate(pecas):
            if len(ps):
                np.add.at(self.Ep, np.asarray(ps), -taxa * dres[j] / len(ps))
        return perda

    # ── escrever ─────────────────────────────────────────────────────
    def escrever(self, pecas, maximo=140, temperatura=0.0, semente=None):
        r = np.random.default_rng(semente)
        resumo = self.resumir([pecas])
        jan = [self.indice[COMECO]] * self.C
        saida = []
        for _ in range(maximo):
            _, _, p = self.frente(np.array([jan]), resumo)
            p = p[0]
            if temperatura <= 0:
                k = int(p.argmax())
            else:
                q = np.power(p, 1.0 / temperatura)
                k = int(r.choice(len(q), p=q / q.sum()))
            ch = self.alfabeto[k]
            if ch == FIM:
                break
            saida.append(ch)
            jan = jan[1:] + [k]
        return "".join(saida)


# ══════════════════════════════════════════════════════════════════════
#  A CONFERÊNCIA NUMÉRICA — de novo, antes de treinar
# ══════════════════════════════════════════════════════════════════════
def conferir(semente=5, eps=1e-5):
    r = np.random.default_rng(semente)
    alf = list("abc()=> .") + [COMECO, FIM]
    rede = EscritorDeConsulta(30, alf, contexto=4, dim_char=6, dim_pedido=5,
                              ocultos=12, semente=semente)
    jan = np.array([[r.integers(0, len(alf)) for _ in range(4)] for _ in range(3)])
    pcs = [[int(r.integers(0, 30)) for _ in range(4)] for _ in range(3)]
    certos = np.array([int(r.integers(0, len(alf))) for _ in range(3)])

    def perda():
        _, _, p = rede.frente(jan, rede.resumir(pcs))
        return -np.log(np.maximum(p[np.arange(3), certos], 1e-15)).mean() / math.log(2)

    guardado = {k: getattr(rede, k).copy()
                for k in ("Ep", "Ec", "W1", "b1", "W2", "b2")}
    rede.passo(jan, pcs, certos, taxa=1.0)      # o passo É o gradiente, com taxa 1
    grad = {k: guardado[k] - getattr(rede, k) for k in guardado}
    for k, v in guardado.items():
        setattr(rede, k, v.copy())

    piores = []
    for nome in ("Ep", "Ec", "W1", "b1", "W2", "b2"):
        M = getattr(rede, nome)
        G = grad[nome]
        pior_rel = pior_abs = 0.0
        idx = [tuple(int(r.integers(0, s)) for s in M.shape) for _ in range(40)]
        for k in idx:
            g0 = M[k]
            M[k] = g0 + eps; mais = perda()
            M[k] = g0 - eps; menos = perda()
            M[k] = g0
            num = (mais - menos) / (2 * eps)
            ana = G[k]
            ab = abs(num - ana)
            pior_abs = max(pior_abs, ab)
            pior_rel = max(pior_rel, ab / max(abs(num), abs(ana), 1e-4))
        piores.append((nome, pior_rel, pior_abs))
    return piores


if __name__ == "__main__":
    print("CONFERÊNCIA NUMÉRICA DO GRADIENTE (escritor de consulta)")
    print(f"  {'peso':<5}{'relativo':>12}{'absoluto':>12}   veredito")
    tudo = True
    for nome, rel, ab in conferir():
        ok = rel < 1e-5 or ab < 1e-9
        tudo &= ok
        print(f"  {nome:<5}{rel:>12.2e}{ab:>12.2e}   {'ok' if ok else 'ERRADO'}")
    print("\n  " + ("gradiente confere — pode treinar"
                    if tudo else "NÃO TREINE: a conta está errada"))
