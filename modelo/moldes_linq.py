# -*- coding: utf-8 -*-
"""O CORPUS DE CONSULTAS: pares (pedido em português → LINQ que compila).

DE ONDE VEM O DADO, JÁ QUE NINGUÉM ESCREVEU MIL CONSULTAS À MÃO

Das classes do próprio projeto. `TransacaoFinanceira` tem `Valor` como
`decimal`, `Status` como um enum de quatro valores, `IsFraudeSuspeita`
como `bool`. Cada combinação de (operação × propriedade × comparação ×
valor) é uma consulta legítima, e o LINQ dela é EXATO por construção —
não é palpite, é a regra da linguagem aplicada a um tipo conhecido.

Isso responde a pergunta que sempre volta neste projeto ("e o dado?") de
um jeito que nenhuma outra parte respondeu: aqui o dado se gera, e o
compilador confere. Cada projeto C# novo que aparecer é corpus novo.

O QUE ISSO NÃO RESOLVE, E EU NÃO VOU FINGIR QUE RESOLVE

O lado do PORTUGUÊS é meu, escrito em moldes. A rede vai aprender a
esperar o jeito que EU escrevo o pedido, não o jeito que o Eduardo fala.
É o mesmo erro que já foi medido neste projeto (o corpus de moldes que
derrubou o acerto de 67,6% para 53,4%), e a defesa é a mesma: os oito
enunciados REAIS dele entram no teste, nunca no treino. Se a rede só
acertar os meus moldes, o número do teste vai dizer.
"""
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modelo.leitor_csharp import ProjetoCSharp        # noqa: E402

# ── como se PEDE cada operação, e como ela se ESCREVE ────────────────
#
# O molde do LINQ é fixo porque a linguagem é fixa. O molde do português
# é variado de propósito: mesma consulta, muitas maneiras de pedir.
OPERACOES = {
    "filtrar": {
        "aceita_predicado": True,
        "pedidos": ["me mostra {ent} com {p} {cmp} {v}",
                    "filtra {ent} onde {p} {cmp} {v}",
                    "quero {ent} que {tem} {p} {cmp} {v}",
                    "lista {ent} com {p} {cmp} {v}",
                    "traz {ent} cujo {p} {cmp} {v}",
                    "{ent} com {p} {cmp} {v}"],
        # O PEDIDO QUE DIZ SÓ O VALOR: "quero as transações canceladas".
        # Não tem "status" em lugar nenhum — a pessoa disse o valor do enum
        # e espera que se entenda.
        #
        # ISTO JÁ FOI UMA OPERAÇÃO SEPARADA, `filtrar_valor`, E FOI ERRO
        # MEU. O LINQ que sai é o mesmo `Where(...)`; eram dois rótulos
        # para uma saída só. A rede era obrigada a decidir entre duas
        # coisas que dão no mesmo, e punida quando errava uma distinção
        # que não tem consequência nenhuma. Medido: 82 erros em 141 na
        # classe separada, contra ZERO depois de juntar — sem trocar uma
        # linha da rede, só parando de perguntar o que não importa.
        "pedidos_so_valor": ["quero {ent} {v}",
                             "me mostra {ent} {v}",
                             "lista {ent} {v}",
                             "traz {ent} {v}",
                             "me traz {ent} {v}",
                             "quero ver {ent} {v}"],
        "linq": "{lista}.Where({x} => {x}.{P} {op} {lit}).ToList()",
    },
    "ordenar_desc": {
        "pedidos": ["ordena {ent} por {p} do maior para o menor",
                    "{ent} ordenadas por {p} decrescente",
                    "me lista {ent} do maior {p} para o menor",
                    "classifica {ent} por {p} decrescente"],
        "linq": "{lista}.OrderByDescending({x} => {x}.{P}).ToList()",
    },
    "ordenar_asc": {
        "pedidos": ["ordena {ent} por {p}",
                    "{ent} em ordem de {p}",
                    "me lista {ent} do menor {p} para o maior",
                    "classifica {ent} por {p} crescente"],
        "linq": "{lista}.OrderBy({x} => {x}.{P}).ToList()",
    },
    "agrupar": {
        "pedidos": ["agrupa {ent} por {p}",
                    "quantos {ent} tem de cada {p}",
                    "separa {ent} por {p}",
                    "{ent} agrupadas por {p}"],
        "linq": "{lista}.GroupBy({x} => {x}.{P}).ToList()",
    },
    "somar": {
        # OS QUATRO ÚLTIMOS TÊM "TODAS/TODOS" DE PROPÓSITO. Sem eles, o
        # pedido real "calcular a soma de todas as taxas de processamento"
        # saía `All(...)`: "todas" era a palavra do `All` no corpus e de
        # mais nenhuma operação, então ela mandava sozinha. Isto não se
        # conserta com regra, se conserta com exemplo — a rede precisa ver
        # "todas" convivendo com "soma".
        "pedidos": ["soma o {p} de {ent}",
                    "qual o total de {p} de {ent}",
                    "total de {p} em {ent}",
                    "quanto dá a soma de {p} de {ent}",
                    "quanto deu a soma de {p} de {ent}",
                    "calcular a soma de todas as {p} de {ent}",
                    "calcula a soma de todos os {p} de {ent}",
                    "soma de todas as {p} de {ent}",
                    "o total de todos os {p} de {ent}"],
        "linq": "{lista}.Sum({x} => {x}.{P})",
    },
    "contar": {
        "aceita_predicado": True,
        "pedidos": ["quantas {ent} tem {p} {cmp} {v}",
                    "conta {ent} com {p} {cmp} {v}",
                    "quantidade de {ent} onde {p} {cmp} {v}",
                    "quantos {ent} com {p} {cmp} {v}"],
        # "Quantas transações estão pendentes." — a pergunta do arquivo
        # dele, escrita do jeito dele. Sem estas frases, "quantas" perdia
        # para "filtrar" (0,62 contra 0,38): a maneira "só o valor" só
        # existia no filtrar, então valor solto virou sinal de Where.
        # Faltava o exemplo, não faltava rede.
        "pedidos_so_valor": ["quantas {ent} {v}",
                             "quantos {ent} {v}",
                             "quantas {ent} estao {v}",
                             "conta {ent} {v}",
                             "conta quantas {ent} {v}"],
        "linq": "{lista}.Count({x} => {x}.{P} {op} {lit})",
    },
    "existe": {
        "aceita_predicado": True,
        "pedidos": ["existe {ent} com {p} {cmp} {v}",
                    "tem alguma {ent} com {p} {cmp} {v}",
                    "alguma {ent} tem {p} {cmp} {v}",
                    "ha {ent} com {p} {cmp} {v}"],
        "pedidos_so_valor": ["tem {ent} {v}",
                             "existe {ent} {v}",
                             "tem alguma {ent} {v}",
                             "ha {ent} {v}"],
        "linq": "{lista}.Any({x} => {x}.{P} {op} {lit})",
    },
    "todos": {
        "aceita_predicado": True,
        "pedidos": ["todas {ent} tem {p} {cmp} {v}",
                    "todo {ent} tem {p} {cmp} {v}",
                    "confere se todas {ent} tem {p} {cmp} {v}",
                    "sera que todas {ent} tem {p} {cmp} {v}"],
        "linq": "{lista}.All({x} => {x}.{P} {op} {lit})",
    },
    "primeiro": {
        "aceita_predicado": True,
        "pedidos": ["pega a primeira {ent} com {p} {cmp} {v}",
                    "primeira {ent} onde {p} {cmp} {v}",
                    "me da a primeira {ent} com {p} {cmp} {v}",
                    "acha a primeira {ent} com {p} {cmp} {v}"],
        "linq": "{lista}.FirstOrDefault({x} => {x}.{P} {op} {lit})",
    },
    "projetar": {
        "pedidos": ["me mostra so o {p} de {ent}",
                    "quero apenas o {p} de {ent}",
                    "lista o {p} de {ent}",
                    "extrai o {p} de {ent}"],
        "linq": "{lista}.Select({x} => {x}.{P}).ToList()",
    },
}

# ── COMO SE PENDURA UM FILTRO NUMA OPERAÇÃO QUE NÃO ACEITA PREDICADO ──
#
# `Count(t => t.Status == X)` existe. `Sum(t => t.Status == X)` não existe —
# `Sum` recebe o que somar, não uma condição. Para somar só uma parte é
# preciso filtrar ANTES:
#
#     transacoes.Where(t => t.Status == Concluida).Sum(t => t.Valor)
#                └──── o filtro ────┘└─ a soma ─┘
#
# E ISTO NÃO É UMA DECISÃO DA REDE. Se a operação é `Sum` e a frase tem uma
# condição, o `Where` é OBRIGATÓRIO — a linguagem manda, não o gosto. A
# rede não ganha uma cabeça de "tem filtro?"; ela ganha uma pergunta nova e
# de verdade: QUAL propriedade é a do filtro, já que agora são duas
# propriedades na mesma frase ("soma o VALOR das transações com STATUS
# concluído").
SUFIXOS_FILTRO = [" com {pf} {cmp} {v}",
                  " onde {pf} {cmp} {v}",
                  " que tem {pf} {cmp} {v}",
                  " cujo {pf} {cmp} {v}",
                  " com {pf} {cmp} {v}"]
# e a maneira curta, que é como a pessoa realmente escreve:
#     "soma o valor de transações concluídas"
SUFIXOS_VALOR = [" {vf}", " que estao {vf}", " {vf}"]

# como se DIZ uma comparação, e o operador que ela vira
COMPARACOES = {
    ">":  ["acima de", "maior que", "superior a", "passando de", "mais de"],
    "<":  ["abaixo de", "menor que", "inferior a", "menos de"],
    ">=": ["de pelo menos", "no minimo", "a partir de"],
    "<=": ["no maximo", "ate"],
    # "DE" SAIU DAQUI, E FOI A CORREÇÃO MAIS BARATA DO DIA.
    #
    # "de" é a preposição mais comum do português: está em "soma o valor
    # DE transações", "quantidade DE logs", "a soma DE todas as taxas".
    # Tratá-la como maneira de dizer `==` fazia o código enxergar uma
    # comparação em quase todo pedido — e a partir daí inventar valor,
    # inventar filtro, cortar palavra no meio. Três bugs diferentes, uma
    # causa só.
    #
    # Perde-se a frase "status DE concluida", que quase ninguém escreve.
    "==": ["igual a", "igual", "que seja", "que e"],
    "!=": ["diferente de", "que nao seja"],
}
# comparação que faz sentido para cada tipo: não se pede "nome maior que"
POR_TIPO = {
    "numero": [">", "<", ">=", "<=", "==", "!="],
    "texto":  ["==", "!="],
    "enum":   ["==", "!="],
    "bool":   ["=="],
    "data":   [">", "<"],
}
VALORES_NUM = [10, 50, 100, 500, 1000, 1500, 2000, 5000, 10000, 15000, 1, 2, 3, 4]

# da frase mais longa para a mais curta: "de pelo menos" tem de ser testada
# antes de "de", senão "de" casa primeiro e leva o resto da frase junto
FRASES_CMP = sorted(((f, op) for op, fs in COMPARACOES.items() for f in fs),
                    key=lambda x: -len(x[0]))


def _sem_acento_com_mapa(texto):
    """Minúsculas e sem acento, guardando de onde cada letra veio.

    O mapa existe porque a busca precisa ser insensível a acento e caixa,
    mas o VALOR devolvido tem de sair do texto ORIGINAL: procurar em
    "ana silva" e devolver "ana silva" escreveria `== "ana silva"` num
    campo que no banco está "Ana Silva".
    """
    fora, mapa = [], []
    for i, ch in enumerate(texto or ""):
        base = "".join(c for c in unicodedata.normalize("NFD", ch.lower())
                       if unicodedata.category(c) != "Mn")
        for b in (base or " "):
            fora.append(b if (b.isalnum() or b.isspace()) else " ")
            mapa.append(i)
    return "".join(fora), mapa


# as palavras que penduram o filtro na frase
CONECTORES = ["que tem", "que tenha", "onde", "cujo", "cuja", "com"]


def partir_no_conector(pedido):
    """"soma o VALOR das transações COM STATUS igual a X" → as duas metades.

    POR QUE PARTIR, EM VEZ DE TREINAR MAIS

    Numa consulta encadeada há DUAS propriedades na mesma frase, uma para
    agregar e outra para filtrar. As duas cabeças da rede liam a frase
    INTEIRA e cada uma tinha de adivinhar qual metade era a sua. Medido:
    82% cada, e os erros eram quase todos a MESMA troca — o filtro no
    lugar da agregação e vice-versa.

    Não é falta de treino: é falta de informação. O resumo é uma média, e
    numa média "por codigo erro" e "onde id" chegam misturados.

    Onde a frase se parte não é opinião: está escrito. "com", "onde",
    "que tem", "cujo" são as palavras que penduram a condição — as mesmas
    que eu uso para ESCREVER o pedido. Cada cabeça passa a receber a sua
    metade, e a pergunta que sobra para a rede é a que importa: dentro
    desta metade, qual propriedade é esta?

    Sem conector, as duas metades são a frase inteira, e nada muda.
    """
    plano, mapa = _sem_acento_com_mapa(pedido)
    plano = " " + plano + " "
    corte = None
    for con in CONECTORES:
        padrao = r"(?<![a-z0-9])" + r"\s+".join(re.escape(w) for w in con.split()) \
                 + r"(?![a-z0-9])"
        for m in re.finditer(padrao, plano):
            k = m.start() - 1
            if 0 <= k < len(mapa) and (corte is None or mapa[k] > corte[0]):
                corte = (mapa[k], m.end() - 1)
    if corte is None:
        return pedido, pedido
    fim = corte[1]
    return (pedido[:corte[0]].strip(),
            (pedido[mapa[fim]:].strip() if fim < len(mapa) else ""))


# ══════════════════════════════════════════════════════════════════════
#  A CASCA DE CÓDIGO, E O NÚMERO BRASILEIRO
# ══════════════════════════════════════════════════════════════════════
#
# Estas três funções existem porque o pedido real não chega limpo. Ele
# chega colado do `Program.cs`, com `Console.WriteLine`, aspas, barras de
# comentário e uma linha de tracinhos. Medido, antes delas:
#
#   Console.WriteLine("1. Where — Filtragem no Repositório");
#     → transacoes.Where(t => t.ContaOrigem > "Console.WriteLine(\"1. ...")
#
# A frase inteira virou o valor comparado. A mesma pergunta sem a casca
# acertava a operação.

_SO_PONTUACAO = re.compile(r"^[\s\-=_*#/.]+$")


def descascar(pedido):
    """Tira a casca de código e devolve a frase que está dentro dela.

    O QUE SAI: `Console.WriteLine(...)` (ficando o texto de dentro), as
    barras de comentário, as linhas que são só tracinhos, a numeração de
    item (`1.`, `a)`) e o ponto-e-vírgula do fim.

    O QUE FICA: as aspas que sobraram. Depois de desembrulhar o
    `Console.WriteLine`, toda aspa restante é aspa de VALOR — 'Concluida',
    "Ana Silva" — e é assim que `valor_citado` sabe achar o literal sem
    confundir com o texto de uma chamada.
    """
    if not pedido:
        return ""
    txt = str(pedido)
    # Console.WriteLine("X") / Write("X")  →  X   (o texto de dentro serve)
    txt = re.sub(r'Console\.\w+\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)\s*;?',
                 lambda m: " " + m.group(1).replace('\\"', '"') + " ", txt)
    # o que sobrou de chamada sem string dentro
    txt = re.sub(r'Console\.\w+\s*\([^)]*\)\s*;?', " ", txt)
    linhas = []
    for linha in txt.splitlines():
        l = re.sub(r"^\s*(?://+|/\*+|\*+/?)\s*", "", linha)      # // e /* */
        l = re.sub(r"\s*\*/\s*$", "", l)
        if _SO_PONTUACAO.match(l):        # a régua de tracinhos não diz nada
            continue
        l = re.sub(r"^\s*(?:\d+\s*[.)\-]|[a-zA-Z]\s*[.)])\s+", "", l)  # 1.  a)
        linhas.append(l)
    txt = " ".join(x for x in linhas if x.strip())
    # A RÉGUA DE TRACINHOS depois de desembrulhada vira texto NO MEIO da
    # linha, e o corte por linha inteira não a pega mais. Some aqui, em
    # qualquer posição: quatro traços seguidos nunca são palavra.
    txt = re.sub(r"[-=_*~]{4,}", " ", txt)
    txt = re.sub(r"[;{}]+", " ", txt)
    return re.sub(r"\s{2,}", " ", txt).strip()


def valor_citado(pedido):
    """O texto entre aspas, quando ele é um VALOR e não uma frase inteira.

    O enunciado diz o valor com todas as letras — status 'Concluida',
    cliente "Ana Silva", categoria 'Tecnologia'. Isso não é palpite de
    cabeça nenhuma: está escrito, entre aspas, e quem adivinha o que está
    escrito erra de graça. Era o caso do 8a:

        FirstOrDefault(t => t.CpfCliente > "Buscar a primeira transação
                                            da cliente \"Ana Silva\"")

    O TETO DE 40 LETRAS separa um valor de uma frase citada. Nome de
    cliente, nome de categoria e nome de enum cabem folgado; uma oração
    não cabe — e se não couber, é melhor não ter valor nenhum do que ter
    a pergunta inteira como valor.
    """
    achados = re.findall(r"'([^']{1,40})'|\"([^\"]{1,40})\"", descascar(pedido) or "")
    for a, b in achados:
        v = (a or b).strip()
        # descarta o que claramente não é valor: sobra de código ou frase
        if v and not re.search(r"[(){};=]|\s{2,}", v) and len(v.split()) <= 4:
            return v
    return None


def numero_da_frase(texto):
    """O número, lido como BRASILEIRO. Devolve o texto pronto para o C#.

    `R$ 1.000,00` é mil reais. A conta antiga fazia
    `"1.000,00".replace(",", ".")` e entregava `1.000` ao C#, que é um
    decimal válido — vale UM. Compilava, passava no juiz, e filtrava pelo
    número errado: o pior defeito possível neste projeto, porque o
    compilador não pega.

    A regra que separa: ponto de MILHAR vem sempre em grupos de três
    (`15.000`, `1.234.567`); ponto DECIMAL, não (`1.5`). Então
    `\\d{1,3}(\\.\\d{3})+` é milhar e o resto é decimal.
    """
    if not texto:
        return None
    t = re.sub(r"R\$\s*", " ", str(texto))
    # 1.000,00  ·  1.234.567  ·  15.000
    m = re.search(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?", t)
    if m:
        n = m.group(0).replace(".", "").replace(",", ".")
        # `1000.00m` e `1000m` valem o mesmo para o C#, mas ninguém escreve
        # o primeiro. Os centavos zerados de "R$ 1.000,00" saem daqui.
        return n[:-3] if n.endswith(".00") else n
    # 1500,50 — vírgula decimal
    m = re.search(r"-?\d+,\d+", t)
    if m:
        return m.group(0).replace(",", ".")
    # 1500  ·  1.5 (ponto decimal de programador)
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return m.group(0) if m else None



# ══════════════════════════════════════════════════════════════════════
#  O PORTUGUÊS DO ENUNCIADO
# ══════════════════════════════════════════════════════════════════════
#
# Medido: os 12 desafios do Program.cs deram 2/12, e a maior parte dos
# erros não era de raciocínio — era de vocabulário. O corpus dizia
# "pega a primeira transacao com cliente nome igual a Ana Silva"; o
# enunciado diz "Buscar a primeira transação da cliente 'Ana Silva'".
# A rede nunca tinha visto "Buscar", "Calcular", "Validar", "Projetar".
#
# Isto não é uma segunda rede nem um segundo caminho: são frases a
# mais no MESMO corpus, com o MESMO gabarito. O que muda é só a
# quantidade de jeitos de dizer a mesma coisa.
FORMAIS = {'filtrar': ['Filtrar apenas {ent} com {p} {cmp} {v}', 'Filtrar {ent} cujo {p} {cmp} {v}', 'Selecionar as {ent} com {p} {cmp} {v}', 'Obter {ent} onde {p} {cmp} {v}', 'Restringir {ent} a {p} {cmp} {v}', 'Retornar as {ent} com {p} {cmp} {v}'],
            'primeiro': ['Buscar a primeira {ent} com {p} {cmp} {v}', 'Buscar a primeira {ent} onde {p} {cmp} {v}', 'Localizar a primeira {ent} com {p} {cmp} {v}', 'Retornar a primeira {ent} com {p} {cmp} {v}', 'Obter a primeira {ent} cujo {p} {cmp} {v}', 'Tentar buscar uma {ent} com {p} {cmp} {v}'],
            'somar': ['Calcular o montante total de {p} em {ent}', 'Calcular o total de {p} de {ent}', 'Calcular a soma de {p} das {ent}', 'Totalizar {p} de {ent}', 'Somar {p} das {ent}', 'Apurar o total de {p} em {ent}', 'Calcular o montante total movimentado em {p} de {ent}'],
            'contar': ['Contar quantas {ent} {tem} {p} {cmp} {v}', 'Contar {ent} com {p} {cmp} {v}', 'Contabilizar {ent} onde {p} {cmp} {v}', 'Apurar a quantidade de {ent} com {p} {cmp} {v}', 'Determinar quantas {ent} {tem} {p} {cmp} {v}'],
            'todos': ['Validar se todas as {ent} {tem} {p} {cmp} {v}', 'Validar se todas as {ent} possuem {p} {cmp} {v}', 'Verificar se todas as {ent} {tem} {p} {cmp} {v}', 'Garantir que todas as {ent} tenham {p} {cmp} {v}', 'Conferir se toda {ent} {tem} {p} {cmp} {v}'],
            'existe': ['Verificar se existe alguma {ent} com {p} {cmp} {v}', 'Verificar se há {ent} com {p} {cmp} {v}', 'Identificar se existe {ent} com {p} {cmp} {v}', 'Checar a existência de {ent} com {p} {cmp} {v}', 'Detectar se alguma {ent} {tem} {p} {cmp} {v}'],
            'agrupar': ['Agrupar as {ent} por {p}', 'Agrupar as {ent} por {p} exibindo o total de cada', 'Consolidar {ent} por {p}', 'Sumarizar as {ent} por {p}', 'Separar as {ent} por {p} mostrando as ocorrências de cada'],
            'projetar': ['Projetar a lista de {ent} para {p}', 'Extrair {p} de {ent}', 'Selecionar apenas {p} das {ent}', 'Mapear {ent} para {p}', 'Listar somente {p} de {ent}'],
            'ordenar_desc': ['Listar as {ent} ordenadas por {p} decrescente', 'Ordenar as {ent} por {p} em ordem decrescente', 'Listar as {ent} da maior {p} para a menor', 'Listar as {ent} da mais recente para a mais antiga por {p}', 'Classificar {ent} por {p} decrescente', 'Listar as {ent} ordenadas por {p} desc', 'Ordenar {ent} por {p} desc', '{ent} ordenadas por {p} descending', 'Listar as {ent} da mais recente para a mais antiga ({p} desc)', 'Listar as {ent} do maior {p} para o menor'],
            'ordenar_asc': ['Listar as {ent} ordenadas por {p} crescente', 'Ordenar as {ent} por {p} em ordem crescente', 'Listar as {ent} da menor {p} para a maior', 'Listar as {ent} da mais antiga para a mais recente por {p}', 'Classificar {ent} por {p} crescente', 'Listar as {ent} ordenadas por {p} asc', 'Ordenar {ent} por {p} asc', '{ent} ordenadas por {p} ascending', 'Listar as {ent} da mais antiga para a mais recente ({p} asc)', 'Listar as {ent} do menor {p} para o maior']}

# ══════════════════════════════════════════════════════════════════════
#  OS MOLDES QUE FALTAVAM
# ══════════════════════════════════════════════════════════════════════
#
# Medido nos 12 desafios do Program.cs: três deles não eram erro da rede,
# eram pedido que a SAÍDA não sabia escrever. `GroupBy` sozinho não conta
# nada, e "exibindo o total de ocorrências de cada nível" é contagem por
# grupo; `Select(t => t.Valor)` não é projetar para um DTO.
#
# Mudar a FORMA do problema já valeu 0% → 98,7% neste projeto uma vez.
# Aqui é a mesma ideia, menor: uma saída que não consegue dizer a resposta
# nunca vai acertá-la, por melhor que seja o treino.
OPERACOES["agrupar_contando"] = {
    "linq": "{lista}.GroupBy({x} => {x}.{P})"
            ".Select(g => new {{ Chave = g.Key, Total = g.Count() }}).ToList()",
    "pedidos": ["quantos {ent} tem de cada {p}",
                "conta {ent} por {p}",
                "Agrupar as {ent} por {p} exibindo o total de cada",
                "Agrupar {ent} por {p} mostrando o total de ocorrências de cada",
                "Contar as {ent} agrupadas por {p}",
                "Consolidar {ent} por {p} com a contagem de cada",
                "quantidade de {ent} por {p}",
                "total de {ent} de cada {p}"],
}
OPERACOES["projetar_dto"] = {
    # {corpo} é preenchido por `mapear_dto`, não pela rede
    "linq": "{lista}.Select({x} => new {P} {{ {corpo} }}).ToList()",
    "pedidos": ["Projetar a lista de {ent} para {p}",
                "Projetar {ent} para {p}",
                "Converter {ent} para {p}",
                "Mapear {ent} para {p}",
                "transforma {ent} em {p}",
                "Montar a lista de {p} a partir de {ent}",
                "Projetar a lista de {ent} para {p} formatando valores e datas"],
}

for _op, _frases in FORMAIS.items():
    if _op in OPERACOES:
        OPERACOES[_op]["pedidos"] = list(OPERACOES[_op]["pedidos"]) + _frases

# ══════════════════════════════════════════════════════════════════════
#  O DTO: de uma classe para outra
# ══════════════════════════════════════════════════════════════════════
FORMATO = {"decimal": '"C"', "double": '"C"', "float": '"C"',
           "DateTime": '"dd/MM/yyyy HH:mm"', "DateTimeOffset": '"dd/MM/yyyy HH:mm"'}
SUFIXOS_DE_FORMATO = ("Formatado", "Formatada", "Formatted", "Texto", "Str")


def mapear_dto(props_origem, props_dto, enums, x="x"):
    """`ValorFormatado = t.Valor.ToString("C")` — o corpo do `new X { ... }`.

    NÃO É REDE, E NÃO DEVE SER. Casar `CodigoRastreio` com `CodigoRastreio`
    é comparação de texto exato; casar `ValorFormatado` com `Valor` é tirar
    um sufixo conhecido. Chamar uma rede para decidir isso seria pedir
    palpite onde existe resposta — e palpite erra às vezes, `==` nunca.

    As três regras, nesta ordem:
        1. mesmo nome              → A = t.A
        2. nome + sufixo de formato → AFormatado = t.A.ToString("C")
        3. maior prefixo em comum   → DataFormatada ← DataHora

    E o `.ToString()` entra sozinho quando o destino é `string` e a origem
    não é: `Status` é enum, `Status` do DTO é texto, e sem a conversão o
    compilador recusa. Regra da linguagem, não gosto.
    """
    por_nome = {pr.nome: pr for pr in props_origem}
    linhas, nao_achou = [], []
    for d in props_dto:
        origem, fmt = por_nome.get(d.nome), None
        if origem is None:
            for suf in SUFIXOS_DE_FORMATO:          # ValorFormatado → Valor
                if d.nome.endswith(suf) and d.nome[:-len(suf)] in por_nome:
                    origem = por_nome[d.nome[:-len(suf)]]
                    fmt = FORMATO.get(origem.tipo)
                    break
        if origem is None:                          # DataFormatada → DataHora
            melhor, tam = None, 0
            for nome, pr in por_nome.items():
                i = 0
                while i < min(len(nome), len(d.nome)) and nome[i] == d.nome[i]:
                    i += 1
                if i > tam and i >= 4:
                    melhor, tam = pr, i
            if melhor is not None:
                origem, fmt = melhor, FORMATO.get(melhor.tipo)
        if origem is None:
            nao_achou.append(d.nome)
            continue
        leitura = f"{x}.{origem.nome}"
        if d.de_texto and not origem.de_texto:
            leitura += f".ToString({fmt})" if fmt else ".ToString()"
        elif fmt and d.de_texto:
            leitura += f".ToString({fmt})"
        linhas.append(f"{d.nome} = {leitura}")
    return linhas, nao_achou


def dtos_de(proj):
    """As classes que servem de DESTINO de projeção.

    Um DTO é uma classe do projeto que NÃO tem lista própria — ninguém
    guarda uma `List<TransacaoSeguraDto>`, ela é feita na hora. É esse o
    sinal, e não o sufixo do nome: `...Dto`, `...ViewModel` e `...Resumo`
    são convenções que mudam de time para time; "classe sem lista" é
    estrutural e vale em qualquer projeto.
    """
    return [n for n in proj.entidades
            if not proj.lista_de(n) and len(proj.opcoes_de(n)) >= 2]


# ══════════════════════════════════════════════════════════════════════
#  DUAS CONDIÇÕES — o teto
# ══════════════════════════════════════════════════════════════════════
#
# "Filtrar apenas transações com status 'Concluida' CUJO VALOR seja
# superior a R$ 1.000,00" pede duas coisas ao mesmo tempo. Todo molde
# tinha exatamente um `{lit}`: a rede escolhia uma das duas e largava a
# outra — e não por erro de treino. Não havia como DIZER a resposta.
#
# Partir a frase e resolver cada pedaço com a máquina que já existe é
# mais barato e mais confiável que uma cabeça nova: onde a frase se parte
# está escrito ("cujo", " e ", " ou "), e cada metade vira uma pergunta
# do tamanho das que a rede já responde bem.

# " e " / " ou " juntam condições; "cujo/onde/que tenha" abrem a segunda
JUNTORES = [(" ou ", "||"), (" e ", "&&"),
            (" cujo ", "&&"), (" cuja ", "&&"), (" cujos ", "&&"),
            (" cujas ", "&&"), (" e tambem ", "&&"), (" alem de ", "&&")]


def _tem_condicao(parte, palavras=()):
    """Este pedaço de frase carrega uma condição?

    Número, aspas e palavra de comparação são sinais que valem em qualquer
    projeto. `palavras` é o que só o projeto sabe: os nomes dos valores de
    enum ditos em português ("suspeita fraude", "concluida"). Sem isso,
    "...suspeita de fraude no dataset OU acima de R$ 15.000" não partia —
    o lado esquerdo é uma condição escrita por extenso, sem um dígito nem
    uma aspa para denunciá-la.
    """
    if not parte or not parte.strip():
        return False
    if (achar_comparacao(parte)[0] or re.search(r"\d", parte)
            or re.search(r"['\"]", parte)):
        return True
    plano = _sem_acento_com_mapa(parte)[0]
    return any(w and w in plano for w in palavras)


def partir_condicoes(pedido, palavras=()):
    """`(partes, juntor)` — as condições da frase e o `&&`/`||` que as liga.

    Devolve UMA parte quando só há uma condição, que é o caso comum e
    continua pelo caminho de sempre.

    O CORTE SÓ VALE SE OS DOIS LADOS TIVEREM CONDIÇÃO. "soma o valor E a
    taxa" tem um " e " e uma condição só; cortar ali inventaria um filtro
    do nada. `_tem_condicao` pede número, aspas ou palavra de comparação
    nos DOIS lados — sem isso o " e " é só um "e" de português.
    """
    if not pedido:
        return [pedido], "&&"
    plano, mapa = _sem_acento_com_mapa(pedido)
    for palavra, juntor in JUNTORES:
        for m in re.finditer(re.escape(palavra), plano):
            i, f = mapa[m.start()], mapa[min(m.end(), len(mapa) - 1)]
            a, b = pedido[:i].strip(), pedido[f:].strip()
            if _tem_condicao(a, palavras) and _tem_condicao(b, palavras):
                return [a, b], juntor
    return [pedido], "&&"


# os verbos que separam "de QUEM se fala" do "o QUE se valida"
#
#   "todas as transações CONCLUÍDAS  possuem  código de autorização"
#    └──── quem: o Where ────┘                └── o que: o predicado ──┘
#
# É a mesma ideia do `partir_no_conector`, com outras palavras: onde a
# frase se divide está escrito nela. `All(A && B)` e `Where(A).All(B)`
# não querem dizer a mesma coisa — o primeiro exige que TODAS sejam A e
# B; o segundo, que toda A seja B —, e é o verbo que diz qual dos dois.
VERBOS_DE_PREDICADO = ["possuem", "possui", "possuam", "estao com",
                       "contem", "apresentam", "apresenta", "tenham"]
# "preenchido" não é um valor: é "diferente de vazio"
PREENCHIDO = ["preenchido", "preenchida", "preenchidos", "preenchidas",
              "nao nulo", "informado", "informada", "nao vazio"]


def partir_no_verbo(pedido):
    """`(quem, o_que)` — ou `(pedido, None)` quando não há verbo separando."""
    if not pedido:
        return pedido, None
    plano, mapa = _sem_acento_com_mapa(pedido)
    for v in VERBOS_DE_PREDICADO:
        alvo = " " + _sem_acento_com_mapa(v)[0].strip() + " "
        i = plano.find(alvo)
        if i < 0:
            continue
        a = pedido[:mapa[i]].strip()
        j = min(i + len(alvo), len(mapa) - 1)
        b = pedido[mapa[j]:].strip()
        if a and b:
            return a, b
    return pedido, None


def pede_preenchido(texto):
    """A frase pede "não vazio"? — `CodigoAutorizacao != null`."""
    plano = _sem_acento_com_mapa(texto or "")[0]
    return any(w in plano for w in PREENCHIDO)


def cabe(op_nome, prop, enums):
    """Esta propriedade pode ser usada NESTA operação? — a regra, num lugar só.

    `Sum(t => t.Categoria)` não é uma escolha ruim: é um erro de TIPO.
    Categoria é string, Sum quer número, e o compilador recusa. Não é
    gosto meu — é regra da linguagem.

    POR QUE ESTA FUNÇÃO EXISTE, E É O CONSERTO DE UM BURACO

    Esta regra já estava escrita no `gerar`: o corpus nunca ensinou
    `somar` com uma propriedade de texto. Mas a INFERÊNCIA escolhia entre
    TODAS as propriedades da classe, sem olhar a operação — a restrição
    valia no treino e era jogada fora na hora de responder. Medido:

        "Calcular o montante total movimentado em transações concluídas"
            → transacoes.Where(...).Sum(t => t.Tipo)      (enum!)
        "Calcular o total movimentado na categoria 'Tecnologia'"
            → transacoes.Sum(t => t.Categoria)            (string!)

    Nenhum dos dois compila. Agora as duas pontas chamam esta função, e
    não há como uma mudar sem a outra.
    """
    fam = familia(prop, enums)
    if not fam or prop.colecao:
        return False
    if op_nome == "somar":
        return bool(prop.de_numero)
    if op_nome in ("agrupar", "agrupar_contando"):
        return fam in ("enum", "texto", "bool")
    if op_nome in ("ordenar_asc", "ordenar_desc"):
        return fam in ("numero", "data", "texto")
    return True


def metades(pedido, operacao):
    """As duas metades — mas SÓ onde a frase realmente tem duas.

    `Count(t => t.ClienteNome == "Ana Silva")` aceita a condição dentro
    dela: em "pega a primeira transação COM cliente nome igual a Ana
    Silva" o "com" não pendura filtro nenhum — ele abre a própria
    condição, e a propriedade está DEPOIS dele.

    Partir aí entregaria "pega a primeira transação" à cabeça da
    propriedade: uma metade sem propriedade nenhuma. Foi o que aconteceu,
    e o preço foi 71,3% — `ClienteNome` virava `CodigoRastreio`.

    Então a partição vale só para `Sum`, `Select`, `OrderBy` e `GroupBy`,
    as que NÃO aceitam predicado e por isso precisam de um `Where` à
    parte. Para as outras, as duas metades são a frase inteira.
    """
    if OPERACOES.get(operacao, {}).get("aceita_predicado"):
        # DUAS CONDIÇÕES TAMBÉM SÃO DUAS METADES, e esquecer isso custou
        # 6,7 pontos nas bases novas (96,7% → 90,0%) na primeira tentativa.
        #
        # Com dois nomes de propriedade na mesma frase e a cabeça lendo a
        # frase inteira, ela volta a ter de adivinhar qual metade é a sua
        # — o mesmo defeito que este arquivo já tinha corrigido para o
        # `Sum`, reaparecendo por outra porta. A regra é a mesma: cada
        # cabeça recebe o pedaço onde a resposta dela está.
        partes, _ = partir_condicoes(pedido)
        if len(partes) == 2:
            return partes[0], partes[1]
        return pedido, pedido
    return partir_no_conector(pedido)


def achar_comparacao(pedido, so_este=None):
    """Devolve (operador, o que vem DEPOIS da frase) ou (None, None).

    PALAVRA INTEIRA, E ISTO É O CONSERTO DE UM BUG QUE PASSOU BATIDO.

    A busca era `frase in pedido`, um pedaço de texto dentro de outro. Só
    que "de" é uma das maneiras de dizer `==`, e "pen-DE-ntes" contém
    "de". O código cortava a palavra no meio e usava o resto como valor:

        "quantas transações estão pendentes"  →  t.Categoria == "ntes"

    E "ate" (uma das maneiras de dizer `<=`) está dentro de "c-ATE-goria":

        "o total na categoria 'Tecnologia'"   →  t.ContaOrigem <= "goria..."

    O segundo nem compila. O primeiro compila e está errado, que é pior —
    erro que compila é erro que ninguém vê. Agora a frase só casa cercada
    de espaço ou de ponta de texto, e `\s+` entre as palavras aceita
    espaço duplo e quebra de linha.
    """
    plano, mapa = _sem_acento_com_mapa(pedido)
    plano = " " + plano + " "
    for f, op in FRASES_CMP:
        if so_este is not None and op != so_este:
            continue
        padrao = r"(?<![a-z0-9])" + r"\s+".join(re.escape(w) for w in f.split()) \
                 + r"(?![a-z0-9])"
        # A ÚLTIMA OCORRÊNCIA, e não a primeira. "quantidade de as
        # transações onde conta origem de Infra" tem dois "de", e o valor
        # vem depois do segundo. Pegando o primeiro, o valor saía a frase
        # inteira: `== "as transacoes onde conta origem de Infra"`.
        # A comparação encosta no valor; então a que interessa é a última.
        achados = list(re.finditer(padrao, plano))
        if not achados:
            continue
        k = achados[-1].end() - 1             # −1 do espaço que eu colei na frente
        return op, (pedido[mapa[k]:].strip() if k < len(mapa) else "")
    return None, None


def familia(p, enums):
    if p.tipo in enums:
        return "enum"
    if p.de_numero:
        return "numero"
    if p.de_texto:
        return "texto"
    if p.de_verdade:
        return "bool"
    if p.de_data:
        return "data"
    return None


def em_portugues(nome):
    """`TaxaProcessamento` → `taxa processamento`, que é como se fala."""
    saida = []
    for i, ch in enumerate(nome):
        if ch.isupper() and i and not nome[i - 1].isupper():
            saida.append(" ")
        saida.append(ch.lower())
    return "".join(saida)


def nomes_da_lista(classe, lista):
    """Como uma pessoa CHAMA aquela lista, tirado do próprio código.

    ISTO ERA UM DICIONÁRIO CHUMBADO, com `TransacaoFinanceira` e
    `LogSistema` escritos à mão — e um dicionário chumbado é exatamente o
    que impede a coisa de valer no projeto seguinte. Agora o nome vem da
    VARIÁVEL que o projeto usa (`transacoes`, `logs`, `pedidos`) mais o
    nome da classe em português, que é o outro jeito de a pessoa falar.

    O singular sai por regra de português tosca (tira o "s" final). Tosca
    de propósito: é só mais uma maneira de PEDIR, e se sair errada o pior
    que acontece é a rede ver uma frase estranha no treino. O LINQ nunca
    depende disso — quem escreve o nome da lista é o leitor do código.
    """
    fala = [lista]
    if lista.endswith("s"):
        fala += [f"as {lista}", f"os {lista}", lista[:-1]]
    else:
        fala += [f"o {lista}", f"a {lista}"]
    emp = em_portugues(classe)
    if emp not in fala:
        fala.append(emp)
    return fala


def gerar(proj, quantos=8000, semente=7):
    r = random.Random(semente)
    enums = proj.enums
    pares, vistos = [], set()
    entidades = [n for n in proj.entidades if proj.lista_de(n)]
    if not entidades:
        return pares
    # COTA POR OPERAÇÃO. Sem isso, `filtrar` sai com 1.512 exemplos e
    # `somar` com 72 — porque as operações com comparação têm muito mais
    # combinações possíveis. A rede aprenderia a escrever Where quase
    # sempre, que é a mesma armadilha do desequilíbrio de classe que já
    # zerou classes neste projeto duas vezes.
    cota = max(1, quantos // len(OPERACOES))
    feitos = {k: 0 for k in OPERACOES}
    tentativas = 0
    while len(pares) < quantos and tentativas < quantos * 60:
        tentativas += 1
        ent = r.choice(entidades)
        lista = proj.lista_de(ent)
        props = proj.opcoes_de(ent)
        faltando = [k for k in OPERACOES if feitos[k] < cota]
        op_nome = r.choice(faltando or list(OPERACOES))
        molde = OPERACOES[op_nome]
        # um em cada quatro filtros é pedido só pelo valor
        so_valor = bool(molde.get("pedidos_so_valor")) and r.random() < 0.25
        precisa_valor = "{v}" in molde["pedidos"][0] or "{cmp}" in " ".join(molde["pedidos"])

        # a propriedade tem de fazer sentido para a operação
        if so_valor:
            # só enum e bool: "quero as transações canceladas" funciona
            # porque `Cancelada` é um valor com nome. "quero as transações
            # 1500" não quer dizer nada.
            # SÓ ENUM. Com bool, o molde gerava "traz transacoes nao is
            # fraude suspeita" — português que ninguém escreve, e ainda
            # atrapalhava: a palavra "suspeita" puxava para o VALOR
            # `SuspeitaFraude` em vez da propriedade booleana.
            cand = [p for p in props if familia(p, enums) == "enum"]
        else:
            # A MESMA `cabe` que a inferência usa. Duas cópias da regra
            # viram duas regras diferentes no primeiro conserto.
            cand = [p for p in props if cabe(op_nome, p, enums)]
        if not cand:
            continue
        p = r.choice(cand)
        fam = familia(p, enums)

        op, lit, dito = "", "", ""
        if so_valor:
            # A COMPARAÇÃO É SEMPRE `==` AQUI, e tem de ser forçada. Se eu
            # deixasse o sorteio escolher, sairia "quero as transações
            # cancelada" com `!=` no LINQ — a frase dizendo uma coisa e o
            # código a contrária, e o corpus ensinando o oposto do que diz.
            op = "=="
            v = r.choice(enums[p.tipo])
            lit = f"{p.tipo}.{v}"
            falado = em_portugues(v)
            if r.random() < 0.5:                # "cancelada" e "canceladas"
                falado += "s"
        elif precisa_valor and "{cmp}" in " ".join(molde["pedidos"]):
            op = r.choice(POR_TIPO.get(fam, ["=="]))
            dito = r.choice(COMPARACOES[op])
            if fam == "enum":
                v = r.choice(enums[p.tipo])
                lit = f"{p.tipo}.{v}"
                falado = em_portugues(v)
            elif fam == "numero":
                v = r.choice(VALORES_NUM)
                lit = p.literal(v)
                falado = str(v)
            elif fam == "texto":
                v = r.choice(["Tecnologia", "Alimentacao", "Ana Silva", "Pendente",
                              "Pagamentos", "AntiFraude", "Infra"])
                lit = p.literal(v)
                falado = v
            elif fam == "bool":
                v = r.choice(["true", "false"])
                lit = v
                falado = "sim" if v == "true" else "nao"
            else:
                continue
        else:
            falado = ""

        # PROJETAR PARA UM DTO não escolhe propriedade: escolhe CLASSE de
        # destino, e o corpo do `new` sai de `mapear_dto`, que é comparação
        # de nomes e não palpite. Se o projeto não tem DTO nenhum, esta
        # operação simplesmente não entra no corpus dele.
        if op_nome == "projetar_dto":
            alvos = [d for d in dtos_de(proj) if d != ent]
            if not alvos:
                continue
            destino = r.choice(alvos)
            props_destino = proj.opcoes_de(destino)
            corpo, faltou = mapear_dto(props, props_destino, enums, x=lista[0])
            # UM PAR SÓ ENTRA SE A PROJEÇÃO FOR DE VERDADE. O gerador
            # produzia `logs → TransacaoSeguraDto` casando 1 de 7 campos
            # por parentesco de prefixo (`CodigoRastreio` ← `CodigoErro`).
            # Isso não é uma projeção, é uma coincidência de letras — e
            # treinar nela ensina a rede a projetar qualquer coisa em
            # qualquer coisa.
            if not corpo or len(corpo) < max(2, int(0.6 * len(props_destino))):
                continue
            frase = r.choice(molde["pedidos"]).format(
                ent=r.choice(nomes_da_lista(ent, lista)), p=destino,
                cmp="", v="", tem="")
            frase = " ".join(frase.split())
            linq = molde["linq"].format(lista=lista, x=lista[0], P=destino,
                                        corpo=", ".join(corpo))
            chave = (frase, linq)
            if chave in vistos:
                continue
            vistos.add(chave)
            feitos[op_nome] += 1
            pares.append({"pedido": frase, "linq": linq,
                          "operacao": op_nome, "entidade": ent,
                          "propriedade": None, "propriedade_filtro": None,
                          "base": f"{op_nome}:{ent}:{destino}"})
            continue

        frases = molde["pedidos_so_valor"] if so_valor else molde["pedidos"]
        frase_escolhida = r.choice(frases)
        pedido = frase_escolhida.format(
            ent=r.choice(nomes_da_lista(ent, lista)),
            p=em_portugues(p.nome), cmp=dito, v=falado, tem=r.choice(["tem", "tenha", "com"]))

        # ── e aqui o FILTRO PENDURADO, quando cabe ────────────────────
        prop_f, linq_filtro = None, ""
        if (not molde.get("aceita_predicado") and not so_valor
                and r.random() < 0.45):
            pf, _ = _sortear_filtro(r, props, p, enums,
                                    cabe_curto=frase_escolhida.rstrip().endswith("{ent}"))
            if pf is not None:
                prop_f, pedido_extra, linq_filtro = pf
                pedido += pedido_extra
        pedido = " ".join(pedido.split())

        # ── A SEGUNDA CONDIÇÃO ────────────────────────────────────────
        #
        # Só onde a operação aceita predicado (`Where`, `Count`, `Any`,
        # `All`, `FirstOrDefault`): nelas a condição mora dentro da
        # própria chamada, e duas condições viram `A && B` ali mesmo. Em
        # `Sum` e `GroupBy` a condição já é um `Where` à parte — outro
        # caminho, que continua como estava.
        #
        # Sem estes exemplos a rede nunca veria uma frase com duas
        # exigências, e o `partir_condicoes` da inferência estaria
        # resolvendo um problema que o treino nunca apresentou.
        segunda, prop_segunda = "", None
        if (molde.get("aceita_predicado") and not so_valor and lit
                and r.random() < 0.22):
            outras = [q for q in props
                      if q.nome != p.nome and familia(q, enums) and not q.colecao]
            if outras:
                q = r.choice(outras)
                fam2 = familia(q, enums)
                if fam2 == "enum" and enums.get(q.tipo):
                    v2 = r.choice(enums[q.tipo])
                    lit2, falado2 = f"{q.tipo}.{v2}", em_portugues(v2)
                elif fam2 == "numero":
                    v2 = r.choice(VALORES_NUM)
                    lit2, falado2 = q.literal(v2), str(v2)
                elif fam2 == "texto":
                    v2 = r.choice(["Tecnologia", "Ana Silva", "Infra"])
                    lit2, falado2 = q.literal(v2), v2
                else:
                    lit2 = falado2 = None
                if lit2:
                    op2 = r.choice(["==", ">", "<"] if fam2 == "numero" else ["==", "!="])
                    dito2 = r.choice(COMPARACOES[op2])
                    juntor, palavra = r.choice([("&&", " e "), ("&&", " e tambem "),
                                                ("||", " ou "), ("&&", " cujo ")])
                    pedido += f"{palavra}{em_portugues(q.nome)} {dito2} {falado2}"
                    pedido = " ".join(pedido.split())
                    segunda = f" {juntor} {lista[0]}.{q.nome} {op2} {lit2}"
                    prop_segunda = q.nome

        linq = molde["linq"].format(lista=lista, x=lista[0], P=p.nome, op=op, lit=lit)
        if segunda:
            # entra logo antes do parêntese que fecha o lambda
            corte = linq.index(")", linq.index("=>"))
            linq = linq[:corte] + segunda + linq[corte:]
        if linq_filtro:
            # `transacoes.Sum(...)` vira
            # `transacoes.Where(...).Sum(...)` — o filtro entra entre a
            # lista e a operação, que é exatamente onde ele vai no LINQ
            linq = linq.replace(f"{lista}.", f"{lista}.Where({lista[0]} => "
                                             f"{lista[0]}.{linq_filtro}).", 1)
        linq = " ".join(linq.split())
        if pedido in vistos:
            continue
        vistos.add(pedido)
        feitos[op_nome] += 1
        # A SEGUNDA CONDIÇÃO É O ALVO DA CABEÇA DO FILTRO. Ela já existe e
        # já sabe ler a segunda metade da frase — é exatamente o papel
        # dela. Sem este rótulo, a `Mf` não veria estes exemplos e a
        # segunda propriedade sairia de uma cabeça que nunca treinou nela.
        filtro_rotulo = prop_f or prop_segunda
        pares.append({"pedido": pedido, "linq": linq, "operacao": op_nome,
                      "entidade": ent, "propriedade": p.nome,
                      "propriedade_filtro": filtro_rotulo,
                      "base": f"{op_nome}:{ent}:{p.nome}"
                              + (f":+{filtro_rotulo}" if filtro_rotulo else "")})
    return pares


def _sortear_filtro(r, props, prop_agregada, enums, cabe_curto=True):
    """Escolhe a propriedade do filtro, a frase que o diz e o LINQ dele.

    A propriedade do filtro é OUTRA, diferente da que se agrega — é o que
    torna a pergunta interessante: "soma o VALOR das transações com STATUS
    concluído" tem duas propriedades e a rede tem de separar qual é qual.
    """
    cand = [x for x in props
            if x.nome != prop_agregada.nome and familia(x, enums) and not x.colecao]
    if not cand:
        return None, None
    pf = r.choice(cand)
    fam = familia(pf, enums)
    if fam == "enum":
        v = r.choice(enums[pf.tipo]); lit = f"{pf.tipo}.{v}"; falado = em_portugues(v)
    elif fam == "numero":
        v = r.choice(VALORES_NUM); lit = pf.literal(v); falado = str(v)
    elif fam == "texto":
        v = r.choice(["Tecnologia", "Alimentacao", "Ana Silva", "Pagamentos",
                      "AntiFraude", "Infra"])
        lit = pf.literal(v); falado = v
    elif fam == "bool":
        # "que tem is fraude suspeita QUE E NAO" era o que saía antes:
        # português nenhum, e a rede aprendia a ler lixo. Bool no filtro
        # só na forma que existe: "com <propriedade> igual a sim".
        v = r.choice(["true", "false"]); lit = v
        falado = "sim" if v == "true" else "nao"
        return (pf.nome, f" com {em_portugues(pf.nome)} igual a {falado}",
                f"{pf.nome} == {lit}"), None
    else:
        return None, None
    # a maneira curta ("... concluídas") só existe para enum: é o único
    # tipo cujo valor tem NOME. "as transações 1500" não quer dizer nada.
    # A MANEIRA CURTA SÓ ONDE A FRASE TERMINA NA LISTA. Pendurada em
    # "me lista log do maior mensagem para o menor" saía "...para o menor
    # infos" — português que ninguém escreve, e exemplo ruim é dado ruim.
    if fam == "enum" and cabe_curto and r.random() < 0.45:
        falado_curto = falado + ("s" if r.random() < 0.5 else "")
        frase = r.choice(SUFIXOS_VALOR).format(vf=falado_curto)
        op_f = "=="
    else:
        op_f = r.choice(POR_TIPO.get(fam, ["=="]))
        frase = r.choice(SUFIXOS_FILTRO).format(
            pf=em_portugues(pf.nome), cmp=r.choice(COMPARACOES[op_f]), v=falado)
    return (pf.nome, frase, f"{pf.nome} {op_f} {lit}"), None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python modelo/moldes_linq.py <pasta do projeto C#> [saida.jsonl]")
        raise SystemExit(1)
    proj = ProjetoCSharp(sys.argv[1])
    pares = gerar(proj, 8000)
    saida = Path(sys.argv[2] if len(sys.argv) > 2 else
                 Path(__file__).resolve().parent.parent / "dados" / "corpus_linq.jsonl")
    saida.parent.mkdir(parents=True, exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        for x in pares:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    import collections
    c = collections.Counter(x["operacao"] for x in pares)
    print(f"{len(pares):,} pares · {len(set(x['base'] for x in pares))} bases distintas")
    print(f"gravado em {saida}")
    for k, v in c.most_common():
        print(f"   {v:>5}  {k}")
    print("\nAMOSTRA:")
    for x in random.Random(1).sample(pares, 8):
        print(f"   {x['pedido']}")
        print(f"      → {x['linq']}")
