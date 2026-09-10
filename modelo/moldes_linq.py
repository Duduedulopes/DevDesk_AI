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
        elif op_nome in ("somar",):
            cand = [p for p in props if p.de_numero]
        elif op_nome in ("agrupar",):
            cand = [p for p in props if familia(p, enums) in ("enum", "texto", "bool")]
        elif op_nome in ("ordenar_asc", "ordenar_desc"):
            cand = [p for p in props if familia(p, enums) in ("numero", "data", "texto")]
        else:
            cand = [p for p in props if familia(p, enums) and not p.colecao]
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

        linq = molde["linq"].format(lista=lista, x=lista[0], P=p.nome, op=op, lit=lit)
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
        pares.append({"pedido": pedido, "linq": linq, "operacao": op_nome,
                      "entidade": ent, "propriedade": p.nome,
                      "propriedade_filtro": prop_f,
                      "base": f"{op_nome}:{ent}:{p.nome}"
                              + (f":+{prop_f}" if prop_f else "")})
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
