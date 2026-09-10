"""A prova do gradiente do modelo de linguagem.

POR QUE ESTE ARQUIVO EXISTE ANTES DE QUALQUER TREINO

Retropropagação errada não levanta exceção. Ela treina, a perda cai um
pouco, e o defeito se disfarça de "faltou época". Um número de bits/car
produzido por um gradiente não conferido não vale nada.

O que já estava provado: `gradiente` e `gradiente_com_entrada`, no motor.
O que é NOVO aqui: desdobrar o erro da entrada nos N pedaços e somá-los nas
linhas certas da tabela de embutimento.

A ARMADILHA QUE ESTE TESTE PROCURA

Quando o mesmo caractere aparece duas vezes na janela — "aaa", "ada", um
espaço repetido — as duas posições apontam para a MESMA linha da tabela.
As duas contribuições precisam SOMAR. Quem escreve `gt[janela] = por_posicao`
em vez de `np.add.at` perde uma delas, e perde em silêncio.

Por isso a janela do teste tem repetição de propósito, e por isso existe o
controle: a mesma conta com a soma trocada por atribuição TEM que reprovar.
Sem um controle, um teste de gradiente só prova que a conta é consistente
consigo mesma.
"""
import sys, math
sys.path.insert(0, ".")
import numpy as np

from nucleo.custo import EntropiaCruzadaCategorica as Custo
from nucleo.retropropagacao import gradiente_com_entrada
from modelo.linguagem import ModeloDeLinguagem

EPS = 1e-5


def gradiente_da_tabela(m, janela, certo, acumular=True):
    """O gradiente analítico da tabela para UM exemplo.

    `acumular=False` reproduz o defeito de propósito: é o controle.
    """
    x, y = m.entrada(janela), m.alvo(certo)
    _, _, erro_entrada = gradiente_com_entrada(m.rede, x, y, Custo)
    por_posicao = erro_entrada.reshape(m.contexto, m.dimensao)

    gt = np.zeros_like(m.tabela)
    if acumular:
        np.add.at(gt, list(janela), por_posicao)
    else:
        gt[list(janela)] = por_posicao          # ← o defeito
    return gt


def gradiente_numerico_da_tabela(m, janela, certo):
    """A definição de derivada, aplicada a cada número da tabela."""
    y = m.alvo(certo)
    g = np.zeros_like(m.tabela)
    it = np.nditer(m.tabela, flags=["multi_index"])
    while not it.finished:
        i = it.multi_index
        orig = m.tabela[i]
        m.tabela[i] = orig + EPS
        mais = Custo.fn(m.prever(janela), y)
        m.tabela[i] = orig - EPS
        menos = Custo.fn(m.prever(janela), y)
        m.tabela[i] = orig
        g[i] = (mais - menos) / (2 * EPS)
        it.iternext()
    return g


def relativo(a, b):
    """Diferença relativa: |a-b| / max(|a|,|b|). Escala-independente."""
    d = np.abs(a - b)
    n = np.maximum(np.abs(a), np.abs(b))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(n > 1e-12, d / n, 0.0)
    return float(np.max(r))


def main():
    alfabeto = list("abcde ")
    m = ModeloDeLinguagem(alfabeto, contexto=4, dimensao=4, oculta=5, semente=11)
    print(f"\n  {m}\n")

    # JANELAS COM REPETIÇÃO DE PROPÓSITO. A primeira repete 'a' três vezes;
    # a segunda repete o espaço. É onde a soma importa.
    casos = [
        (m.codificar("aaab"), m.indice["c"]),
        (m.codificar("a a "), m.indice["b"]),
        (m.codificar("abcd"), m.indice["e"]),
        (m.codificar("edcb"), m.indice["a"]),
    ]

    print("  ── a conta certa: soma as contribuições ──")
    pior = 0.0
    for janela, certo in casos:
        an = gradiente_da_tabela(m, janela, certo, acumular=True)
        nu = gradiente_numerico_da_tabela(m, janela, certo)
        r = relativo(an, nu)
        pior = max(pior, r)
        texto = "".join(alfabeto[i] for i in janela)
        print(f'     "{texto}" → {alfabeto[certo]!r}   diferença relativa {r:.3e}')
    print(f"\n     pior caso: {pior:.3e}   {'✔ PASSOU' if pior < 1e-6 else '✗ REPROVOU'}")

    print("\n  ── o controle: a mesma conta SEM acumular ──")
    print("     (tem que reprovar, senão o teste não está olhando nada)")
    pior_c = 0.0
    for janela, certo in casos[:2]:                      # só as com repetição
        an = gradiente_da_tabela(m, janela, certo, acumular=False)
        nu = gradiente_numerico_da_tabela(m, janela, certo)
        r = relativo(an, nu)
        pior_c = max(pior_c, r)
        texto = "".join(alfabeto[i] for i in janela)
        print(f'     "{texto}" → {alfabeto[certo]!r}   diferença relativa {r:.3e}')

    print(f"\n     pior caso: {pior_c:.3e}   "
          f"{'✔ reprovou, como devia' if pior_c > 1e-3 else '✗ PASSOU — o teste é cego'}")
    print(f"\n  ══════ separação entre o certo e o errado: {pior_c/max(pior,1e-18):.1e}× ══════\n")

    ok = pior < 1e-6 and pior_c > 1e-3
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
