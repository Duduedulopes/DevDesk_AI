# -*- coding: utf-8 -*-
"""O CONSULTOR: recebe um pedido em português e devolve o LINQ.

    from modelo.consulta_linq import Consultor
    c = Consultor("modelos/consulta.json", r"C:\\Users\\Samsung\\Projetos_Eduardo\\Linq")
    c.montar("soma o valor de transacoes")
    # 'transacoes.Sum(t => t.Valor)'

O PROJETO ENTRA AQUI, E NÃO NO TREINO

O modelo guardado não sabe que existe uma classe `TransacaoFinanceira`
nem uma propriedade `Valor` — e é de propósito. Ele sabe pontuar um
pedido contra um NOME qualquer. Quem diz quais nomes existem é o leitor
de C#, lendo a pasta que se aponta agora. Trocar de projeto é trocar o
segundo argumento.

O QUANTO ISSO VALE — MEDIDO, com o `dotnet build` como juiz

    projeto Linq, modelo treinado nele (~2 min)
        22/22 nas perguntas escritas à mão
        148/150 (98,7%) em bases que a rede nunca viu
             consultas simples     251/251  (100%)
             consultas encadeadas  143/149  (96,0%)

    projeto NOVO (uma loja: Produto, Pedido), o MESMO modelo do Linq,
    zero retreino
        15/15 compilam · 6/15 certas  (40%)

    o mesmo projeto novo, treinado nele
        15/15 compilam · 14/15 certas
        139/150 (92,7%) em bases dele que a rede nunca viu

O PORQUÊ DOS 40%: a tabela de pedaços foi montada com as palavras do
projeto Linq. "preço unitário", "frete cobrado", "estoque disponível" não
têm pedaço nenhum lá dentro — caem todos no `<?>`, o mesmo vetor para
tudo, e sem diferença entre eles não há escolha possível. O casamento por
trigramas generaliza para nome PARECIDO, não para vocabulário inteiro
novo.

O QUE FAZ FUNCIONAR: treinar no projeto, que custa ~15 segundos e não
precisa de dado nenhum escrito à mão — o corpus se gera das classes do
próprio projeto (`programas/treinar_consulta.py <pasta>`). A máquina toda
é independente de projeto; o modelo é por projeto.

    Se um dia interessar um modelo só para todos: o conserto conhecido é
    trocar a tabela de pedaços por HASH (todo trigrama cai num balde, e
    trigrama nunca visto também tem vetor). É mudança na `Peneira`, não no
    resto — e é decisão sua, não minha.

O QUE ELE NÃO SABE FAZER, E É BOM SABER DISSO

UM FILTRO, uma vez. `Where(...).Sum(...)` sai; duas condições
("transações concluídas ACIMA de 1000") não.

ELE LÊ OS NOMES DAS PROPRIEDADES DO PROJETO, e o pedido precisa nomear
uma delas — ou um valor de enum. "Calcular o montante total movimentado"
não tem `Valor` em lugar nenhum e ele erra; "soma o valor" acerta. Medido
no exercício 7 do arquivo do Eduardo: 2/4 no texto literal do enunciado,
4/4 dito como quem conversa.

    Fechar essa distância seria uma lista de sinônimos de negócio
    ("montante" → `Valor`), que é chumbar vocabulário de um projeto só —
    exatamente o que este arquivo passou o dia tirando. Fica registrado
    como decisão em aberto, não como conserto esquecido.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modelo.decisor_linq import Decisor, Peneira, OPS, CMPS   # noqa: E402
from modelo.leitor_csharp import ProjetoCSharp                # noqa: E402
from modelo.moldes_linq import (OPERACOES, achar_comparacao, cabe,  # noqa: E402
                                descascar, dtos_de, em_portugues, familia,
                                mapear_dto, metades, numero_da_frase,
                                partir_condicoes, partir_no_verbo,
                                pede_preenchido, valor_citado)


def _plano(texto):
    """minúsculas, sem acento — só para comparar palavra com palavra."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", t).split())


class Consultor:
    def __init__(self, caminho_modelo, projeto):
        with open(caminho_modelo, encoding="utf-8") as f:
            d = json.load(f)
        self.rede = Decisor.de_dicionario(d["rede"])
        self.peneira = Peneira.de_lista(d["pecas"])
        self.medido = d.get("medido", {})
        self.abrir_projeto(projeto)

    # ── o projeto: pode trocar a qualquer hora, sem retreinar ─────────
    def abrir_projeto(self, projeto):
        self.proj = projeto if isinstance(projeto, ProjetoCSharp) \
            else ProjetoCSharp(projeto)
        p = self.proj
        self.lista_de = {e: p.lista_de(e) for e in p.entidades if p.lista_de(e)}
        self.entidades = sorted(self.lista_de)
        # os resumos dos NOMES são calculados uma vez: são fixos enquanto
        # o projeto for o mesmo, e refazê-los a cada pedido seria pagar
        # duas vezes pela mesma conta
        self.ids_lista = {e: self.peneira.ids(self.lista_de[e])
                          for e in self.entidades}
        self.cands = {e: [(pr, self.peneira.ids(em_portugues(pr.nome)))
                          for pr in p.opcoes_de(e)] for e in self.entidades}
        self._v_lista = (np.array([self.rede.resumo(self.ids_lista[e])
                                   for e in self.entidades])
                         if self.entidades else np.zeros((0, self.rede.d)))
        self._v_prop = {e: np.array([self.rede.resumo(c) for _, c in self.cands[e]])
                        for e in self.entidades if self.cands[e]}
        # O CAMINHO DE VOLTA: valor de enum → propriedade que o guarda.
        # `Cancelada` é valor de `StatusTransacao`, e `StatusTransacao` é o
        # tipo da propriedade `Status`. As duas pontas já estão no leitor;
        # só faltava ligar uma na outra.
        self.por_valor = []
        for e in self.entidades:
            for pr, _ in self.cands[e]:
                for v in self.proj.enums.get(pr.tipo, []):
                    self.por_valor.append(
                        (_plano(em_portugues(v)), e, pr, f"{pr.tipo}.{v}"))
        # o valor mais longo primeiro: "suspeita fraude" antes de "fraude"
        self.por_valor.sort(key=lambda x: -len(x[0]))
        # As palavras que já são NOME de alguma coisa no projeto —
        # propriedade, lista ou classe — não são valor de enum. "suspeita"
        # está dentro de `IsFraudeSuspeita`; "transacoes" é a lista. Sem
        # esta lista, o parentesco por trigrama pegava essas palavras e
        # inventava um filtro que a frase nunca pediu.
        # O que, NESTE projeto, denuncia que um pedaço de frase é uma
        # condição: o nome de um valor de enum ou o nome de uma
        # propriedade. Usado só para decidir ONDE PARTIR uma frase de duas
        # condições — nunca para escolher a resposta.
        self.palavras_de_condicao = (
            {w for vs in self.proj.enums.values() for v in vs
             for w in _plano(em_portugues(v)).split() if len(w) > 3}
            | {w for e in self.entidades for pr, _ in self.cands[e]
               for w in _plano(em_portugues(pr.nome)).split() if len(w) > 3})
        self.palavras_de_nome = (
            {w for e in self.entidades for pr, _ in self.cands[e]
             for w in _plano(em_portugues(pr.nome)).split()}
            | {w for v in self.lista_de.values() for w in _plano(v).split()}
            | {w for e in self.entidades for w in _plano(em_portugues(e)).split()})

    def pronto(self):
        """Dá para consultar? (projeto sem lista nenhuma não dá)"""
        return bool(self.entidades) and bool(self._v_prop)

    # ── as quatro decisões ────────────────────────────────────────────
    def decidir(self, pedido):
        u = self.rede.resumo(self.peneira.ids(pedido))
        _, p_op = self.rede.operacao(u)
        op = OPS[int(p_op.argmax())]
        ent, prop = self.lista_e_propriedade(
            u, self.rede.resumo(self.peneira.ids(metades(pedido, op)[0])), op=op)
        _, p_cmp = self.rede.comparacao(u)
        return op, ent, prop, CMPS[int(p_cmp.argmax())]

    def par_de_propriedades(self, ua, uf, ent, op=None):
        """A propriedade AGREGADA e a do FILTRO, escolhidas como um par só.

        As duas cabeças leem o MESMO pedido e têm de apontar para
        propriedades DIFERENTES: em "agrupa as transações por CPF CLIENTE
        com CÓDIGO RASTREIO diferente de Infra", uma é o agrupamento e a
        outra é o filtro. Decidindo cada uma sozinha, elas trocavam de
        lugar — e a consulta saía agrupando pelo que devia filtrar.

        Somando as notas das duas e proibindo o empate (a mesma
        propriedade nos dois papéis), a escolha vira uma só e a proibição
        vira parte da conta, não um remendo depois. É a mesma correção que
        já valeu para lista+propriedade.
        """
        cands = self.cands[ent]
        if len(cands) < 2:
            return (cands[0][0] if cands else None), None
        V = self.rede.unitario(self._v_prop[ent])
        sa = V @ (self.rede.M.T @ ua)      # a metade de antes do conector
        sf = V @ (self.rede.Mf.T @ uf)     # a metade de depois
        # o melhor filtro para cada agregada é o melhor que não é ela
        # A MESMA REGRA DE TIPO DA OUTRA CABEÇA, e este era o buraco.
        #
        # `lista_e_propriedade` já respeitava a operação, mas quando o
        # pedido tem filtro quem escolhe é AQUI — e aqui não respeitava.
        # Medido: `Where(...).Sum(t => t.Tipo)` (enum) e
        # `Where(...).Sum(t => t.IsFraudeSuspeita)` (bool). Nenhum dos
        # dois compila, e `cabe("somar", Tipo)` já dizia False — a regra
        # existia e este caminho passava por fora dela.
        #
        # Só a AGREGADA é restrita: a do filtro compara com um valor e
        # qualquer tipo comparável serve.
        if op is not None:
            pode = np.array([cabe(op, pr, self.proj.enums) for pr, _ in cands])
            if pode.any():
                sa = np.where(pode, sa, -1e18)
        ordem_f = np.argsort(-sf)
        melhor, alvo = (None, None), -1e18
        for i in range(len(cands)):
            j = int(ordem_f[0] if ordem_f[0] != i else ordem_f[1])
            if sa[i] + sf[j] > alvo:
                alvo, melhor = sa[i] + sf[j], (cands[i][0], cands[j][0])
        return melhor

    def lista_e_propriedade(self, u, ua=None, op=None):
        """AS DUAS JUNTAS, e não uma depois da outra.

        Escolher a lista primeiro e a propriedade dentro dela deixa um erro
        sem conserto: se a cabeça da lista erra, a propriedade certa nem
        entra na disputa. Aconteceu com "quanto deu a soma das taxas
        processamento" — a frase não diz o nome de lista nenhuma, a cabeça
        da lista chutou `logs`, e a resposta saiu `logs.Sum(l => l.Mensagem)`
        sendo que `TaxaProcessamento` só existe em transações.

        E SOMAM-SE AS NOTAS CRUAS, não as probabilidades. O softmax da
        propriedade é calculado DENTRO de cada classe, então ele sempre
        entrega 1,000 a alguém: num pedido sobre "taxa processamento", a
        classe `LogSistema` dava 1,000 para `Mensagem` só porque alguém
        tinha de ganhar ali dentro. Probabilidade de dentro de uma caixa
        não se compara com a de outra caixa. A nota crua se compara — é a
        mesma régua (o mesmo `M`, o mesmo pedido) para todos os pares.
        """
        q = self.rede.M.T @ (u if ua is None else ua)
        ql = self.rede.Me.T @ u
        melhor, alvo = None, -1e18
        for i, e in enumerate(self.entidades):
            if e not in self._v_prop:
                continue
            nota_lista = float(self.rede.unitario(self._v_lista[i:i + 1])[0] @ ql)
            s = self.rede.unitario(self._v_prop[e]) @ q
            # A OPERAÇÃO MANDA NO QUE PODE SER ESCOLHIDO. `Sum` de uma
            # string não é resposta ruim, é erro de compilação — e o
            # corpus já ensinava isso. Aqui a mesma regra passa a valer
            # na hora de responder (`cabe`, em moldes_linq).
            if op is not None:
                pode = np.array([cabe(op, pr, self.proj.enums)
                                 for pr, _ in self.cands[e]])
                if not pode.any():
                    continue          # esta classe não serve para esta operação
                s = np.where(pode, s, -1e18)
            k = int(s.argmax())
            if s[k] + nota_lista > alvo:
                alvo, melhor = s[k] + nota_lista, (e, self.cands[e][k][0])
        return melhor

    # ── quando a frase diz o VALOR e não a propriedade ────────────────
    def pelo_valor(self, pedido):
        """"quero as transações canceladas" → (Status, "StatusTransacao.Cancelada").

        POR QUE ISTO NÃO É A REDE, E NEM DEVE SER

        A rede compara o pedido com os NOMES das propriedades: "valor" com
        `Valor`, "severidade" com `Severidade`. É um pulo só. Aqui são dois:

            "canceladas"     → é valor do enum StatusTransacao
            StatusTransacao  → é o tipo da propriedade Status
            logo             → a propriedade é Status

        O segundo pulo é uma CONSULTA A TABELA, não um julgamento: quem diz
        que `Cancelada` pertence a `StatusTransacao` é o arquivo `.cs`, e
        quem diz que `Status` é daquele tipo é o mesmo arquivo. Fazer a rede
        adivinhar isso seria pedir que ela chutasse o que está escrito.

        SÓ ENTRA QUANDO A FRASE NÃO DISSE A COMPARAÇÃO. Se a pessoa
        escreveu "status igual a pendente", ela já entregou a propriedade e
        quem decide é a rede. Isto é para quando o valor solto é a única
        pista que existe.
        """
        plano = " " + _plano(pedido) + " "
        # O GUARDA VALE AQUI TAMBÉM, e faltava.
        #
        # `CodigoErro` em português é "codigo erro", e "erro" casa por
        # prefixo com o valor `Error` do enum. Resultado: "soma o codigo
        # erro de logs" ganhava um `Where(l => l.Severidade == Error)` que
        # a frase nunca pediu. Dezoito dos erros de uma medição, um bug só.
        #
        # Palavra que é NOME de coisa no projeto não é VALOR de coisa.
        palavras = [w for w in plano.split() if w not in self.palavras_de_nome]
        for valor, ent, prop, literal in self.por_valor:
            if len(valor) < 4:
                continue
            if " " in valor:                       # "suspeita fraude"
                if f" {valor} " in plano:
                    return ent, prop, literal
                continue
            for w in palavras:                     # "canceladas" ↔ "cancelada"
                curto, longo = sorted((w, valor), key=len)
                if len(curto) >= 4 and longo.startswith(curto):
                    return ent, prop, literal
        return self._pelo_valor_parecido(palavras)

    # o prefixo resolve "canceladas"↔"cancelada". Não resolve
    # "criticos"↔"Critical": o enum está em inglês e o pedido em português,
    # e nenhuma das duas palavras começa com a outra. O parentesco existe
    # nos TRIGRAMAS (crit, riti, itic), que é a mesma régua que a rede usa
    # para casar nome de propriedade — então uso ela aqui também.
    #
    #   criticos → Critical +0,77 · Info +0,56    (mede-se, e passa)
    #   erros    → Error    +0,71 · Info +0,24    (passa)
    #   avisos   → Error    +0,43                 (não passa: 0,43 < 0,60)
    #   transacoes → tudo NEGATIVO                (o controle: nada casa)
    PISO, MARGEM = 0.60, 0.10

    def _pelo_valor_parecido(self, palavras):
        if not self.por_valor:
            return None, None, None
        vs = self.rede.unitario(
            np.array([self.rede.resumo(self.peneira.ids(v))
                      for v, _, _, _ in self.por_valor]))
        melhor = (None, -9.0, -9.0)
        for w in palavras:
            if len(w) < 4 or w in self.palavras_de_nome:
                continue
            u = self.rede.resumo(self.peneira.ids(w))
            nota = vs @ (u / (np.linalg.norm(u) + 1e-12))
            ordem = np.argsort(-nota)
            k, alto = int(ordem[0]), float(nota[ordem[0]])
            segundo = float(nota[ordem[1]]) if len(ordem) > 1 else -9.0
            if alto > melhor[1]:
                melhor = (k, alto, segundo)
        k, alto, segundo = melhor
        # PISO E MARGEM. O piso corta o palpite fraco; a margem corta o
        # empate — se dois valores do enum pontuam quase igual, a palavra
        # não está apontando para nenhum dos dois.
        if k is None or alto < self.PISO or (alto - segundo) < self.MARGEM:
            return None, None, None
        _, ent, prop, literal = self.por_valor[k]
        return ent, prop, literal

    def _ha_filtro(self, pedido, op_dito):
        """A frase traz uma condição? (comparação escrita, ou valor de enum)"""
        return op_dito is not None or self.pelo_valor(pedido)[1] is not None

    def _filtro(self, pedido, ent, prop_agregada, op_dito, prop_f=None):
        """"<propriedade> <op> <valor>" do Where, ou None se não há filtro.

        Duas maneiras de a frase trazer o filtro, e cada uma tem a sua
        ferramenta:

            "soma o valor das transações COM STATUS IGUAL A CONCLUIDA"
                a frase diz a propriedade → quem escolhe é a `Mf`

            "soma o valor das transações CONCLUÍDAS"
                a frase diz só o valor → quem acha é o caminho de volta
                do enum, que já existe

        A propriedade agregada sai da disputa: o corpus nunca filtra pela
        mesma coluna que soma, e deixá-la concorrer só cria erro.
        """
        cands = [(pr, ids) for pr, ids in self.cands[ent]
                 if pr.nome != prop_agregada.nome]
        if not cands:
            return None
        if op_dito is None:                       # "…transações concluídas"
            # A CLASSE TEM DE SER A MESMA, e este `e2` estava sendo jogado
            # fora. `pelo_valor` procura o valor em TODO o projeto, e
            # devolvia uma propriedade de outra classe:
            #
            #   transacoes.Where(t => t.Severidade == SeveridadeLog.Error)
            #              .Sum(t => t.TaxaProcessamento)
            #
            # `Severidade` é de `LogSistema`. Não compila, nunca vai
            # compilar, e o juiz só pegaria depois de escrito.
            e2, pf, literal = self.pelo_valor(pedido)
            if (pf is None or e2 != ent or pf.nome == prop_agregada.nome
                    or not any(pr.nome == pf.nome for pr, _ in cands)):
                return None
            return f"{pf.nome} == {literal}"
        pf = prop_f
        if pf is None or pf.nome == prop_agregada.nome:
            vs = np.array([self.rede.resumo(ids) for _, ids in cands])
            pf = cands[int(self.rede.notas(self.rede.resumo(self.peneira.ids(pedido)),
                                           vs, "filtro").argmax())][0]
        lit = self.valor_de(pedido, pf, op_dito)
        return f"{pf.nome} {op_dito} {lit}"

    # ── com QUE valor comparar ────────────────────────────────────────
    def valor_de(self, pedido, prop, cmp_):
        """A rede decidiu O QUE comparar; aqui se acha COM QUE.

        Isto é extração, não julgamento: achar onde a frase diz o valor e
        escrevê-lo do jeito que o C# aceita para AQUELE tipo. `1000` numa
        propriedade decimal vira `1000m` — regra da linguagem, não opinião.
        """
        # O RESTO VEM DE QUALQUER FRASE DE COMPARAÇÃO, não só da que a rede
        # escolheu. Onde o valor está na frase não depende de qual operador
        # se decidiu: em "cliente nome igual a Cliente Inexistente" o valor
        # começa depois do "igual a", tenha a rede dito `==` ou `!=`.
        #
        # Procurando só pela frase do operador escolhido, quando a rede
        # errava o operador o valor virava A FRASE INTEIRA:
        #   ClienteNome != "primeira transacao onde cliente nome igual a..."
        # O QUE VEM DEPOIS DO OPERADOR; na falta dele, O QUE ESTÁ ENTRE
        # ASPAS; e só então a frase inteira.
        #
        # O meio deste caminho faltava, e custou uma regressão que eu
        # mesmo causei: ao fazer as aspas bloquearem o palpite de enum,
        # "quantas transações estão no status 'Pendente'" passou a
        # comparar a FRASE TODA com os nomes dos valores do enum — e
        # `Concluida` ganhou de `Pendente` por causa do resto da frase.
        # A palavra entre aspas É a resposta; o resto é contexto.
        resto = achar_comparacao(pedido)[1] or valor_citado(pedido) or pedido
        fam = familia(prop, self.proj.enums)
        if fam == "enum":
            # AQUI A SEMELHANÇA É CRUA, sem a matriz aprendida — e é de
            # propósito.
            #
            # A `M` foi treinada para casar PEDIDO INTEIRO com NOME DE
            # PROPRIEDADE ("me mostra transacoes com status..." ↔ "status").
            # Escolher o valor do enum é outra pergunta: o que sobrou depois
            # do "igual a" é literalmente a palavra do enum ("concluida" ↔
            # `Concluida`). Passar isso pela M é usar a régua errada — e o
            # resultado apareceu: ela escolheu `SuspeitaFraude` para um
            # pedido que dizia "concluida" com todas as letras.
            #
            # Os dois textos dividem a MESMA tabela de peças, então a
            # semelhança entre eles já mede o que interessa: quantos
            # pedaços têm em comum.
            #
            # E É COSSENO, NÃO PRODUTO ESCALAR — medido, não escolhido por
            # gosto. Com o produto cru, "concluida" escolhia
            # `SuspeitaFraude`: os números eram 0,771 contra 0,436, mas a
            # NORMA de "suspeita fraude" era 1,97 e a de "concluida" 0,66.
            # Ganhou o vetor mais COMPRIDO, não o mais parecido — e o
            # comprimento diz quantas vezes o treino empurrou aquela
            # palavra, que não tem nada a ver com a pergunta. Dividindo
            # pelas normas: 1,000 contra 0,594, e a certa ganha.
            vals = self.proj.enums[prop.tipo]
            u = self.rede.resumo(self.peneira.ids(resto or pedido))
            vs = np.array([self.rede.resumo(self.peneira.ids(em_portugues(v)))
                           for v in vals])
            nota = self.rede.unitario(vs) @ (u / (np.linalg.norm(u) + 1e-12))
            return f"{prop.tipo}.{vals[int(nota.argmax())]}"
        if fam == "numero":
            # BRASILEIRO. `R$ 1.000,00` é mil, não um — e a conta antiga
            # entregava `1.000m` ao C#, que compila e vale 1.
            n = numero_da_frase(resto) or numero_da_frase(pedido)
            return prop.literal(n if n is not None else 0)
        if fam == "bool":
            return "true" if not re.search(r"\bn[aã]o\b|\bfalse\b", resto) else "false"
        if fam == "texto":
            # O QUE ESTÁ ENTRE ASPAS GANHA DE TUDO. O enunciado escreve o
            # valor com todas as letras — cliente "Ana Silva", categoria
            # 'Tecnologia'. Sem esta linha o literal virava a pergunta
            # inteira, porque `resto` é "tudo que vem depois do operador"
            # e numa frase sem operador isso é a frase.
            citado = valor_citado(pedido)
            if citado:
                return prop.literal(citado)
            sobra = resto.strip(" ?.!")
            # UM LITERAL DE TEXTO NUNCA É UMA ORAÇÃO. Se o que sobrou tem
            # cara de frase, é porque não havia valor na frase — e vazio
            # é mais honesto que a pergunta copiada para dentro do código.
            if len(sobra) > 40 or len(sobra.split()) > 5:
                return prop.literal("")
            return prop.literal(sobra)
        return prop.literal(resto.strip())

    # ── duas condições ────────────────────────────────────────────────
    def _uma_condicao(self, texto, ent, op, evitar=None, filtro=False):
        """`(propriedade, sinal, literal)` de UM pedaço de frase.

        É a mesma pergunta que a rede já responde bem — "nesta frase, qual
        propriedade?" — feita sobre um pedaço menor. Nada aqui é cabeça
        nova: é a `M` de sempre lendo meia frase em vez de uma inteira.
        """
        cands = self.cands[ent]
        if not cands:
            return None
        u = self.rede.resumo(self.peneira.ids(texto))
        # A PRIMEIRA CONDIÇÃO É A `M`, A SEGUNDA É A `Mf` — as mesmas duas
        # matrizes que o treino usa para a metade de antes e a de depois.
        # Usar a `M` nas duas seria perguntar a mesma coisa duas vezes.
        matriz = self.rede.Mf if filtro else self.rede.M
        s = self.rede.unitario(self._v_prop[ent]) @ (matriz.T @ u)
        # a propriedade do outro pedaço não pode ser esta: "status X e
        # valor Y" são duas propriedades, e repetir uma perde a outra
        for i, (pr, _) in enumerate(cands):
            if evitar is not None and pr.nome == evitar.nome:
                s[i] = -1e18
        prop = cands[int(s.argmax())][0]
        cmp_ = achar_comparacao(texto)[0]
        if cmp_ is None:
            # sem operador escrito: o valor por extenso manda ("suspeita de
            # fraude", "concluida"), e na falta dele é igualdade
            e2, p2, lit2 = self.pelo_valor(texto)
            if p2 is not None and (evitar is None or p2.nome != evitar.nome):
                return p2, "==", lit2
            cmp_ = "=="
        return prop, cmp_, self.valor_de(texto, prop, cmp_)

    def _duas_condicoes(self, pedido, ent, op):
        """`t.Status == X && t.Valor > Y` — ou None quando só há uma.

        POR QUE ISTO NÃO É UMA CABEÇA NOVA

        Porque a pergunta difícil já estava resolvida. O que faltava era
        um lugar na SAÍDA para a segunda resposta: todo molde tinha um
        `{lit}` só, e a rede era obrigada a escolher entre as duas
        condições que a frase pedia. Não era erro de treino — era um
        pedido que o formato não sabia escrever.

        Onde a frase se parte está escrito nela ("cujo", " e ", " ou "),
        como já estava para separar a agregação do filtro.
        """
        partes, juntor = partir_condicoes(pedido, self.palavras_de_condicao)
        if len(partes) < 2:
            return None
        x = self.lista_de[ent][0]
        primeira = self._uma_condicao(partes[0], ent, op)
        if primeira is None:
            return None
        segunda = self._uma_condicao(partes[1], ent, op, evitar=primeira[0],
                                     filtro=True)
        if segunda is None:
            return None
        pedacos = []
        for prop, cmp_, lit in (primeira, segunda):
            if cmp_ == "nenhuma" or lit is None or lit == '""':
                return None      # meia condição não é resposta
            pedacos.append(f"{x}.{prop.nome} {cmp_} {lit}")
        return f" {juntor} ".join(pedacos)

    # ── Where + All / Where + Any ─────────────────────────────────────
    def _restricao_e_predicado(self, pedido, ent, op):
        """`transacoes.Where(concluídas).All(tem código)` — ou None.

        A DIFERENÇA QUE ISTO GUARDA NÃO É DE ESTILO, É DE SENTIDO:

            All(t => t.Status == Concluida && t.Codigo != null)
                "toda transação é concluída E tem código"
            Where(t => t.Status == Concluida).All(t => t.Codigo != null)
                "toda transação concluída tem código"

        A primeira é falsa assim que existir uma transação pendente. O
        enunciado pede a segunda, e as duas frases em português diferem
        por uma palavra: o verbo. "transações CONCLUÍDAS POSSUEM código"
        põe a restrição no substantivo e o que se valida depois do verbo.
        """
        quem, oque = partir_no_verbo(pedido)
        if not oque:
            return None
        # a restrição: o valor dito por extenso do lado de "quem"
        _, prop_q, lit_q = self.pelo_valor(quem)
        if prop_q is None:
            return None
        # o predicado: a propriedade do outro lado
        cands = self.cands[ent]
        u = self.rede.resumo(self.peneira.ids(oque))
        s = self.rede.unitario(self._v_prop[ent]) @ (self.rede.Mf.T @ u)
        for i, (pr, _) in enumerate(cands):
            if pr.nome == prop_q.nome:
                s[i] = -1e18
        prop_o = cands[int(s.argmax())][0]
        if pede_preenchido(oque):
            cond = f"{{x}}.{prop_o.nome} != null"
        else:
            cmp_o = achar_comparacao(oque)[0] or "=="
            lit_o = self.valor_de(oque, prop_o, cmp_o)
            if not lit_o or lit_o == '""':
                return None
            cond = f"{{x}}.{prop_o.nome} {cmp_o} {lit_o}"
        lista = self.lista_de[ent]
        x = lista[0]
        chamada = OPERACOES[op]["linq"].split("{lista}.")[1].split("(")[0]
        return (f"{lista}.Where({x} => {x}.{prop_q.nome} == {lit_q})"
                f".{chamada}({x} => {cond.format(x=x)})")

    # ── projetar para um DTO ──────────────────────────────────────────
    def _projetar_dto(self, pedido, ent):
        """`transacoes.Select(t => new TransacaoSeguraDto { ... }).ToList()`

        A CLASSE DE DESTINO NÃO É PALPITE: o enunciado escreve o nome
        dela — "Projetar a lista de transações para 'TransacaoSeguraDto'".
        Procurar o nome escrito acerta sempre; pedir para uma cabeça
        adivinhar entre as classes do projeto acerta quase sempre. Entre
        as duas, a busca de texto.

        A cabeça da OPERAÇÃO continua sendo rede — é ela que entende que
        "Projetar/Converter/Mapear ... para X" é isto e não um `Select` de
        uma coluna só. O que sai da rede é a decisão; o que entra no
        código é comparação de nomes.
        """
        alvos = [d for d in dtos_de(self.proj) if d != ent]
        if not alvos:
            return None
        plano = _plano(pedido)
        destino = next((d for d in alvos if _plano(d) in plano), None)
        if destino is None:
            citado = valor_citado(pedido)
            if citado:
                destino = next((d for d in alvos
                                if _plano(d) == _plano(citado)), None)
        if destino is None and len(alvos) == 1:
            # UM DTO SÓ NO PROJETO: não há ambiguidade para resolver.
            destino = alvos[0]
        if destino is None:
            return None
        lista = self.lista_de[ent]
        corpo, faltou = mapear_dto(self.proj.opcoes_de(ent),
                                   self.proj.opcoes_de(destino),
                                   self.proj.enums, x=lista[0])
        if not corpo:
            return None
        # O QUE NÃO CASOU FICA ESCRITO NO CÓDIGO, como comentário. Deixar
        # um campo de fora calado é entregar um DTO pela metade que
        # compila — e o buraco só aparece na tela do usuário.
        aviso = f"  /* sem origem: {', '.join(faltou)} */" if faltou else ""
        return (f"{lista}.Select({lista[0]} => new {destino} "
                f"{{ {', '.join(corpo)} }}){aviso}.ToList()")

    # ── montar ────────────────────────────────────────────────────────
    def montar(self, pedido):
        """O LINQ, pronto para colar no projeto. `None` se não há o que consultar."""
        if not self.pronto():
            return None
        # A CASCA SAI AQUI, UMA VEZ SÓ. Descascar dentro de cada cabeça
        # daria quatro versões da mesma frase e quatro jeitos de
        # discordarem. Daqui para baixo, `pedido` é texto de gente.
        pedido = descascar(pedido) or pedido
        op, ent, prop, cmp_ = self.decidir(pedido)
        if op == "projetar_dto":
            return self._projetar_dto(pedido, ent)
        # DUAS CONDIÇÕES, quando a frase pede duas e a operação aceita
        # predicado. `Sum` e `GroupBy` não comparam com nada: nelas a
        # segunda condição, se houver, é um `Where` à parte — o caminho
        # que já existia.
        if op in ("todos", "existe"):
            # a restrição no substantivo vem ANTES das duas condições: se
            # a frase tem verbo separando, ela não é `A && B`
            wa = self._restricao_e_predicado(pedido, ent, op)
            if wa:
                return wa
        if OPERACOES[op].get("aceita_predicado"):
            duas = self._duas_condicoes(pedido, ent, op)
            if duas:
                lista = self.lista_de[ent]
                molde = OPERACOES[op]["linq"]
                # O MOLDE É PREENCHIDO COM UM MARCADOR e a condição única
                # é trocada pelas duas. Recortar o texto do molde à mão
                # (procurar o parêntese, o "=>") já comeu o `.ToList()` do
                # fim numa primeira tentativa — o molde sabe a forma dele,
                # e quem monta não precisa adivinhar onde ela termina.
                alvo = molde.format(lista=lista, x=lista[0],
                                    P="\x00P", op="\x00O", lit="\x00L")
                marca = f"{lista[0]}.\x00P \x00O \x00L"
                if marca not in alvo:
                    return None
                return alvo.replace(marca, duas)
        # SE A FRASE DIZ O OPERADOR, QUEM MANDA É A FRASE.
        #
        # "cliente nome IGUAL A Ana Silva" não é palpite de ninguém: está
        # escrito. E a cabeça da comparação foi treinada exatamente com
        # este rótulo — ela aprendeu a reproduzir esta consulta —, então
        # quando as duas discordam é porque a rede errou o que a tabela
        # acerta. Medido: ela disse `!=` numa frase que dizia "igual a".
        #
        # A cabeça continua decidindo onde importa: quando a frase NÃO diz
        # a comparação ("quero as transações canceladas"), aí a resposta é
        # `nenhuma` ou não, e isso é julgamento.
        op_dito = achar_comparacao(pedido)[0]
        if op_dito is not None:
            cmp_ = op_dito
        # E SE A FRASE NÃO DIZ O OPERADOR MAS DIZ O VALOR ENTRE ASPAS,
        # o operador é `==`. O enunciado escreve `da cliente "Ana Silva"`,
        # `status 'Concluida'`, `categoria 'Tecnologia'` — ninguém escreve
        # "igual a" ali, e ninguém quer dizer outra coisa.
        #
        # Sem isto, medido: a frase com o valor escrito em letras saía
        # `linq: None` ("não achei com que comparar"), com a resposta
        # inteira dentro das aspas a dois passos de distância.
        citado = valor_citado(pedido)
        if op_dito is None and citado:
            cmp_ = "=="
        # SÓ ONDE O MOLDE USA UM VALOR. `GroupBy(x => x.P)` e
        # `Sum(x => x.P)` não comparam com nada — se "canceladas" aparecer
        # num "agrupa as transações canceladas por categoria", o valor não
        # é a resposta, é ruído, e deixar ele trocar a propriedade estraga
        # um agrupamento que estava certo. Foi o que aconteceu: `agrupar`
        # errou 4 de 10 antes deste guarda.
        # `citado` BLOQUEIA o palpite. `pelo_valor` casa o texto com nomes
        # de enum por parentesco de trigrama, e em "um cliente inexistente"
        # ele casou `Pendente` com "inexistente" — as duas terminam em
        # "ente". Onde o valor está escrito, não há o que adivinhar.
        if "{lit}" in OPERACOES[op]["linq"] and op_dito is None and not citado:
            e2, p2, lit2 = self.pelo_valor(pedido)
            if p2 is not None:
                ent, prop, cmp_ = e2, p2, "=="
                lista = self.lista_de[ent]
                molde = OPERACOES[op]["linq"]
                return " ".join(molde.format(lista=lista, x=lista[0], P=prop.nome,
                                             op="==", lit=lit2).split())
        lista = self.lista_de[ent]
        molde = OPERACOES[op]["linq"]
        lit = "" if cmp_ == "nenhuma" else self.valor_de(pedido, prop, cmp_)
        sinal = "" if cmp_ == "nenhuma" else cmp_
        # ── O FILTRO PENDURADO ────────────────────────────────────────
        # `Sum` não aceita condição; se a frase traz uma, ela SÓ pode ser
        # um `Where` antes. Não é escolha, é a linguagem: por isso não há
        # cabeça de rede decidindo "tem filtro?" — há um `if`.
        if not OPERACOES[op].get("aceita_predicado") and self._ha_filtro(pedido, op_dito):
            # O PAR SÓ QUANDO HÁ FILTRO. Escolhendo o par sempre, um pedido
            # simples ("soma o valor de transações") teria a propriedade
            # agregada trocada para caber num filtro que não existe.
            antes, depois = metades(pedido, op)
            prop, prop_f = self.par_de_propriedades(
                self.rede.resumo(self.peneira.ids(antes)),
                self.rede.resumo(self.peneira.ids(depois)), ent, op=op)
            filtro = self._filtro(pedido, ent, prop, op_dito, prop_f)
            if filtro:
                return " ".join(
                    OPERACOES[op]["linq"].format(
                        lista=lista, x=lista[0], P=prop.nome, op="", lit=""
                    ).replace(f"{lista}.", f"{lista}.Where({lista[0]} => "
                                           f"{lista[0]}.{filtro}).", 1).split())
        # O MOLDE PEDE UM VALOR E NÃO HÁ VALOR NENHUM NA FRASE: devolve
        # `None`, e não um palpite.
        #
        # Antes daqui saía `logs.Where(l => l.Severidade > Warning)` para
        # "me mostra os logs criticos" — a rede não reconheceu "criticos"
        # (o enum está em inglês, `Critical`, e o plural português não
        # casou), e o código preencheu o buraco com o que sobrou. Saiu uma
        # consulta que COMPILA e responde outra pergunta, que é o pior
        # tipo de erro: ninguém vê.
        #
        # `None` é uma resposta. "Compilou" não é o mesmo que "respondeu".
        if "{op}" in molde and cmp_ == "nenhuma":
            return None
        return " ".join(molde.format(lista=lista, x=lista[0], P=prop.nome,
                                     op=sinal, lit=lit).split())

    def explicar(self, pedido):
        """As decisões separadas — para mostrar o porquê, não só o quê."""
        if not self.pronto():
            return {}
        pedido = descascar(pedido) or pedido
        op, ent, prop, cmp_ = self.decidir(pedido)
        op_dito = achar_comparacao(pedido)[0]
        if op_dito is None and valor_citado(pedido):
            cmp_ = "=="            # o mesmo de `montar`: o escrito manda
        filtro = None
        if not OPERACOES[op].get("aceita_predicado") and self._ha_filtro(pedido, op_dito):
            antes, depois = metades(pedido, op)
            prop, prop_f = self.par_de_propriedades(
                self.rede.resumo(self.peneira.ids(antes)),
                self.rede.resumo(self.peneira.ids(depois)), ent, op=op)
            filtro = self._filtro(pedido, ent, prop, op_dito, prop_f)
        return {"operacao": op, "lista": self.lista_de[ent], "classe": ent,
                "propriedade": prop.nome, "tipo": prop.bruto,
                "comparacao": op_dito or cmp_, "filtro": filtro,
                "linq": self.montar(pedido)}


def treinar(proj, epocas=14, taxa=0.25, semente=42, pares=None, avisar=None):
    """Treina do zero sobre um projeto C# e devolve (rede, peneira, pares).

    SEM JUIZ AQUI DENTRO, DE PROPÓSITO. O `dotnet build` é como EU meço se
    a rede está boa; não é peça do funcionamento. Se o treino chamasse o
    compilador, o programa não conseguiria aprender um projeto novo numa
    máquina sem .NET instalado — e aprender não precisa de compilador,
    porque o corpus já nasce certo por construção.

    A prova com o juiz continua existindo, em
    `programas/treinar_consulta.py`, que é ferramenta de bancada.
    """
    import collections
    import math
    import random
    from modelo.decisor_linq import Decisor, Peneira, OPS, CMPS
    from modelo.moldes_linq import achar_comparacao, gerar, metades

    pares = pares if pares is not None else gerar(proj, 8000)
    if not pares:
        return None, None, []
    rng = random.Random(semente)

    # A DIVISÃO POR BASE não é para medir aqui — é para o vocabulário não
    # nascer com as palavras do teste dentro. Treina-se em tudo.
    nomes_props = [em_portugues(p.nome) for e in proj.entidades
                   for p in proj.opcoes_de(e)]
    nomes_enum = [em_portugues(v) for vals in proj.enums.values() for v in vals]
    peneira = Peneira([p["pedido"] for p in pares] + nomes_props + nomes_enum
                      + list(proj.listas), minimo=1)
    rede = Decisor(len(peneira), dim=48, ocultos=96, semente=semente)

    ent_de = {e: proj.lista_de(e) for e in proj.entidades if proj.lista_de(e)}
    entidades = sorted(ent_de)
    ids_lista = [peneira.ids(ent_de[e]) for e in entidades]
    cands = {e: [(p, peneira.ids(em_portugues(p.nome))) for p in proj.opcoes_de(e)]
             for e in entidades}

    exemplos = []
    for p in pares:
        cs = cands.get(p["entidade"], [])
        # PROJETAR PARA UM DTO não tem propriedade de origem: o alvo é a
        # classe inteira. Estes exemplos ensinam a OPERAÇÃO e a LISTA, e
        # deixam a cabeça da propriedade em paz (`k_certo=None`).
        if p["operacao"] == "projetar_dto":
            antes, depois = metades(p["pedido"], p["operacao"])
            exemplos.append((peneira.ids(p["pedido"]), OPS.index(p["operacao"]),
                             CMPS.index("nenhuma"),
                             [c for _, c in cs], None, ids_lista,
                             entidades.index(p["entidade"]),
                             peneira.ids(antes), peneira.ids(depois), None))
            continue
        k = [i for i, (pr, _) in enumerate(cs) if pr.nome == p["propriedade"]]
        if not k:
            continue
        kf = None
        if p.get("propriedade_filtro"):
            achou = [i for i, (pr, _) in enumerate(cs)
                     if pr.nome == p["propriedade_filtro"]]
            kf = achou[0] if achou else None
        antes, depois = metades(p["pedido"], p["operacao"])
        exemplos.append((peneira.ids(p["pedido"]), OPS.index(p["operacao"]),
                         CMPS.index(achar_comparacao(p["pedido"])[0] or "nenhuma"),
                         [c for _, c in cs], k[0], ids_lista,
                         entidades.index(p["entidade"]),
                         peneira.ids(antes), peneira.ids(depois), kf))

    for ep in range(1, epocas + 1):
        rng.shuffle(exemplos)
        t = taxa * 0.5 * (1 + math.cos(math.pi * (ep - 1) / epocas))
        soma = 0.0
        for ex in exemplos:
            soma += rede.passo(*ex, t)
        if avisar:
            avisar(ep, epocas, soma / max(1, len(exemplos)))
    return rede, peneira, pares


def caminho_do_modelo(raiz, projeto):
    """Um modelo POR PROJETO, e o nome da pasta é a chave.

    Com um `modelos/consulta.json` só, treinar no projeto seguinte
    apagaria o anterior sem avisar — e o erro apareceria depois, como
    resposta ruim, longe da causa.
    """
    nome = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(projeto).resolve().name).strip("_")
    return Path(raiz) / "modelos" / f"consulta_{nome.lower() or 'projeto'}.json"


def guardar(caminho, rede, peneira, medido=None):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump({"rede": rede.para_dicionario(), "pecas": peneira.pecas,
                   "medido": medido or {}}, f)
    return caminho


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: python modelo/consulta_linq.py <modelos/consulta.json> "
              "<pasta do projeto C#> [pedido]")
        raise SystemExit(1)
    c = Consultor(sys.argv[1], sys.argv[2])
    if c.medido:
        print("medido no treino: " + " · ".join(f"{k} {v}" for k, v in c.medido.items()))
    if len(sys.argv) > 3:
        print(c.montar(" ".join(sys.argv[3:])))
    else:
        print(f"{len(c.entidades)} listas: " +
              ", ".join(f"{c.lista_de[e]} ({e})" for e in c.entidades))
        print("escreva o pedido, linha vazia para sair\n")
        while True:
            try:
                p = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not p:
                break
            print("  " + str(c.montar(p)))
