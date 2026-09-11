"""O ciclo de treino: o que transforma culpa em correcao.

A retropropagacao entrega o gradiente — a direcao em que o custo sobe.
Treinar e andar PARA ONDE ELE DESCE, um pouco de cada vez:

    parametro -= taxa * valor_do_gradiente

Cada termo dessa conta merece o seu registro:

    PARAMETRO NAO E PESO — o vies tambem aprende. A retropropagacao devolve
    gradiente para os dois, e o treino mexe nos dois.

    TAXA DE APRENDIZADO — tambem chamada passo, e o tamanho do degrau dado em
    cada correcao. Grande demais: a rede pula a razoavel e fica
    oscilando. Pequena demais: a rede anda devagar e nao chega. E o
    hiperparametro mais chato do campo — por isso existe um agendamento
    (`taxa_cosseno`) que comeca ousado e afina a ponta.

    GRADIENTE MEDIO — o gradiente de UM exemplo aponta para o minimo daquela
    unica pessoa. Treinar com um exemplo so corrige a rede na direcao certa
    para ELE e errada para os outros. A media sobre um minilote (ou sobre o
    lote inteiro) e uma estimativa do gradiente do problema INTEIRO — e e
    isso que impede a rede de se apaixonar por um caso.

CUSTO COMO FAROL — a unica razao de todo esse passeio. `custo_medio` mede o
quao ruim a rede esta AGORA; `treinar` devolve esse numero por epoca, e e
essa curva que diz se o treino esta de fato aprendendo ou so rodando.
"""

import math

import numpy as np

from nucleo.retropropagacao import gradiente


def minilotes(dados, tamanho, gerador=None):
    """Divide `dados` em pedacos de `tamanho`, EMBARALHADOS.

    O embaralhamento nao e enfeite: sem ele, o algoritmo estocastico vê os
    exemplos na mesma ordem sempre, e um pedaco do problema pode nunca ser
    visto antes do fim. Embaralhar a cada epoca e o que garante que todos
    os exemplos voltam a ser visitados.

    O ultimo lote fica menor quando o tamanho nao divide o total — exemplo
    com 10 itens e lote 3: [3, 3, 3, 1]. Isso e normal e proposital.
    """
    if gerador is None:
        gerador = np.random.default_rng()
    indices = gerador.permutation(len(dados))
    return [[dados[j] for j in indices[i:i + tamanho]]
            for i in range(0, len(dados), tamanho)]


def custo_medio(rede, dados, custo):
    """A media do custo sobre todos os exemplos — o farol do treino.

    O custo de UM exemplo e so zumbido. O que importa e o custo MEDIO
    sobre o conjunto: e ele que o gradiente minimiza e e ele que a epoca
    mede para dizer se o treino esta rendendo.
    """
    custos = [custo.fn(rede.frente(x), y) for x, y in dados]
    return sum(custos) / len(custos)


def acertos(rede, dados):
    """Quantos exemplos a rede acertou, de um total de len(dados).

    "Acertar" e a classe de maior probabilidade prevista ser a de maior
    probabilidade esperada. Serve tanto para a saida unica (XOR, onde o
    argmax de uma posicao e a propria) quanto para a softmax de 10 clases
    do MNIST — a conta e a mesma.
    """
    certo = 0
    for x, y in dados:
        previsao = int(rede.frente(x).argmax())
        alvo = int(np.asarray(y).argmax())
        if previsao == alvo:
            certo += 1
    return certo


def passo(rede, dados, *, taxa=0.5, custo=None):
    """Um passo de descida do gradiente sobre o LOTE INTEIRO de uma vez.

    O gradiente de cada exemplo e calculado e somado; o passo usa a MEDIA.
    Com o lote inteiro, cada passo e garantido de descer no custo medio (a
    menos que a taxa seja grande demais) — e e o que o teste
    `test_um_passo_reduz_o_custo` explora.

    `custo` e obrigatorio: sem saber o custo a retropropagacao nao sabe
    calcular o erro na camada de saida.
    """
    if custo is None:
        raise ValueError("`passo` precisa de um custo")

    soma_pesos = [np.zeros_like(c.pesos) for c in rede.camadas]
    soma_vies = [np.zeros_like(c.vies) for c in rede.camadas]

    for x, y in dados:
        g_pesos, g_vies = gradiente(rede, x, y, custo)
        for i in range(len(rede.camadas)):
            soma_pesos[i] += g_pesos[i]
            soma_vies[i] += g_vies[i]

    n = len(dados)
    for i, camada in enumerate(rede.camadas):
        camada.pesos -= taxa * soma_pesos[i] / n
        camada.vies -= taxa * soma_vies[i] / n


def treinar(rede, dados, *, epocas=1, tamanho_lote=10, taxa=0.5,
            custo=None, semente=None):
    """Roda o ciclo completo e devolve o custo medio por epoca.

    Cada epoca: embaralha, corta em minilotes de `tamanho_lote`, aplica um
    `passo` para cada minilote (cada um estima o gradiente do problema
    inteiro) e mede o custo medio ao fim da epoca. A lista devolvida é a
    historia do custo — deveria descer.

    O `semente` vale ouro aqui: com a mesma semente, o mesmo treino sai a
    mesma rede. E assim que um defeito se reproporciona e se confere.
    """
    if custo is None:
        raise ValueError("`treinar` precisa de um custo")

    gerador = np.random.default_rng(semente)
    historico = []
    for _ in range(epocas):
        for lote in minilotes(dados, tamanho_lote, gerador):
            passo(rede, lote, taxa=taxa, custo=custo)
        historico.append(custo_medio(rede, dados, custo))
    return historico


def taxa_cosseno(inicial, epoca, total):
    """Agendamento de taxa cosseno: comeca em `inicial`, termina em 0.

        taxa(ep) = inicial * (1 + cos(pi * ep / (total - 1))) / 2

    POR QUE COSSENO

    A maior carencia da taxa fixa e que ela e um so numero para treinos
    longos: grande demais para a afinar, pequena demais para o inicio. O
    cosseno comeca OUSADO e vai amacando — nenhum hiperparametro novo, so
    uma forma. As pontas rendem pouco (a derivada do cosseno vai a zero);
    conhecer essa curvatura e o que o teste `test_cosseno_e_quase_plano_nas
    _pontas` mede.

    O `total - 1` no denominador e a escolha de epoca: a list-inicial (0)
    vale `inicial`, e a ULTIMA epoca vale exatamente 0.0.
    """
    if total < 1:
        raise ValueError("`total` de epocas precisa ser ao menos 1")
    if total == 1:
        return inicial
    angulo = math.pi * epoca / (total - 1)
    return inicial * (1.0 + math.cos(angulo)) / 2.0