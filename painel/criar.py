# -*- coding: utf-8 -*-
"""DO PEDIDO ESCRITO ATÉ A PASTA CRIADA — quem chama as redes, na ordem.

    "vc pode criar o projeto de uma calculadora em C#?"
                        │
       etiquetador ─────┤ tira da frase: LING=c#  TIPO=?  NOME=calculadora
                        │
       detector ────────┤ se veio código colado, ele diz a linguagem
                        │
       compositor ──────┤ (linguagem, tipo, nome) → a árvore
                        │
                        ▼
              mostra a árvore e PERGUNTA

O QUE FALTA, ELE PERGUNTA — NÃO INVENTA

Esta é a regra da casa e vale aqui inteira. Se a frase não disse a
linguagem e não veio exemplo de código, ele não escolhe uma: pergunta.
Se a rede da estrutura não sabe onde um papel mora, pergunta. Se nunca
viu aquele papel naquela linguagem, diz isso com todas as letras.

E NADA VAI PARA O DISCO SEM VOCÊ CONFIRMAR

`planejar` devolve o plano. Escrever é outra chamada, depois do sim. Um
programa que cria dezessete arquivos na sua pasta enquanto você ainda
está lendo o que ele entendeu não é assistente, é acidente.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# O que a pessoa escreve → o tipo que as redes conhecem. Isto NÃO é a
# rede pensando: é a ponte entre a palavra que saiu do etiquetador e o
# nome interno do tipo. O etiquetador é quem achou a palavra na frase.
TIPOS_CONHECIDOS = {
    "console": "console", "terminal": "console", "cli": "console",
    "api": "api", "rest": "api", "servico": "api", "serviço": "api",
    "biblioteca": "biblioteca", "lib": "biblioteca", "pacote": "biblioteca",
    "site": "site", "web": "site", "pagina": "site", "página": "site",
}
LINGUAGENS_CONHECIDAS = {
    "c#": "csharp", "csharp": "csharp", "c sharp": "csharp", ".net": "csharp",
    "dotnet": "csharp", "python": "python", "py": "python",
    "javascript": "javascript", "js": "javascript", "node": "javascript",
    "php": "php", "html": "html", "css": "css",
}


# as palavrinhas que o etiquetador cola no campo sem querer
PALAVRAS_VAZIAS = {"de", "do", "da", "dum", "duma", "em", "no", "na", "um",
                   "uma", "o", "a", "os", "as", "para", "pra", "com", "tipo",
                   "projeto", "meu", "minha", "esse", "essa"}

# pontuação que o etiquetador gruda na palavra: "c#," tinha a vírgula
# colada e a busca procurava "c#," inteiro, com a vírgula — e errava,
# dizendo "não sei escrever nessa linguagem" para uma linguagem que ele
# conhece desde o primeiro dia.
PONTUACAO = ".,;:!?()[]{}\"'«»"


def _limpar(w):
    return w.strip(PONTUACAO + " \t\r\n").lower()


def traduzir(bruto, tabela):
    """Acha a palavra conhecida DENTRO do que o etiquetador devolveu.

    O ETIQUETADOR ENTREGA O CAMPO COM EXTRA GRUDADO. Em "cria um projeto
    DE CONSOLE em C#" ele devolve TIPO='de console' (a preposição vem
    junto) e LING='C#,' (a vírgula vem junto). A busca procurava essas
    strings inteiras, errava, e o resultado era esta frase na tela:

        nome: console — você escreveu 'de console' — não é um tipo que eu
        conheço, então entendi como o nome

    Ou seja: o programa dizia não conhecer "console", que está na lista de
    tipos dele desde o primeiro dia. E ainda batizava o projeto de
    "console" e perguntava o tipo de novo.

    Limpar cada palavra antes de procurar resolve os dois casos — procura
    "console" e "c#" — e devolver O QUE SOBROU mantém a regra da casa:
    nada do que foi extraído se perde. "calculadora console" vira
    tipo=console com "calculadora" sobrando para o nome.
    """
    if not bruto:
        return None, ""
    achou = tabela.get(_limpar(str(bruto)))
    if achou:
        return achou, ""
    palavras = [_limpar(w) for w in str(bruto).split() if _limpar(w)
                not in PALAVRAS_VAZIAS]
    for i, w in enumerate(palavras):
        if w in tabela:
            return tabela[w], " ".join(palavras[:i] + palavras[i + 1:])
    return None, bruto


def _resgatar(frase, achado, criador):
    """Resgata campos da frase inteira quando o etiquetador os perdeu.

    O etiquetador etiqueta pela vizinhança e tem um limite medido: frases
    onde o nome fica longe da palavra-chave devolvem TIPO=NOME=ruído. Mas
    o pedido estava escrito com TODAS AS LETRAS na frase. Se um campo
    ainda está vazio aqui embaixo, procurar as palavras conhecidas e o
    padrão "se chama X" na frase inteira é ler o que já foi dito — não é
    adivinhar. Só preenche o que continua vazio; o que a rede acertou não
    é tocado.
    """
    import re
    baixa = (frase or "").lower()
    palavras = [_limpar(w) for w in re.split(r"[\s,;.!?_]+", baixa) if _limpar(w)]

    if achado["linguagem"] is None:
        for w in palavras:
            ling = (LINGUAGENS_CONHECIDAS.get(w)
                    or (w if w in criador.linguagens_que_sei() else None))
            if ling:
                achado["linguagem"] = ling
                achado["de_onde"]["linguagem"] = f"vi '{w}' na sua frase"
                break

    if achado["tipo"] is None:
        for w in palavras:
            tipo = (TIPOS_CONHECIDOS.get(w)
                    or (w if w in criador.tipos_que_sei() else None))
            if tipo:
                achado["tipo"] = tipo
                achado["de_onde"]["tipo"] = f"vi '{w}' na sua frase"
                break

    if achado["nome"] is None:
        _resgatar_nome(frase, achado, criador)
    else:
        # O etiquetador pode pôr uma linguagem no lugar do NOME: na frase
        # "csharp, console, calculadora" (sem contexto de pergunta) ele
        # devolve NOME='csharp,'. Um nome que, limpo, É uma linguagem ou um
        # tipo conhecido não é nome — é o etiquetador perdido. Põe o campo
        # de volta como vazio e deixa o `_resgatar_nome` encontrar o nome
        # de verdade na frase.
        limpo = _limpar(achado["nome"])
        if limpo in LINGUAGENS_CONHECIDAS or limpo in TIPOS_CONHECIDOS \
                or limpo in criador.linguagens_que_sei() \
                or limpo in criador.tipos_que_sei():
            achado["nome"] = None
            achado["de_onde"].pop("nome", None)
            _resgatar_nome(frase, achado, criador)
        # O NOME PODE SER LIXO MESMO SEM SER LINGUAGEM/TIPO. Medido:
        # "a linguagem VAI SER em Python, ... vai se chamar calculadora de
        # dieta" devolve TIPO='vai ser' e bate o nome como "vai ser" logo
        # abaixo — porque "vai ser" virou o campo TIPO e a sobra dele era
        # o nome. O padrão "SE CHAMA X" é mais explícito que "o nome que
        # sobrou do tipo": se a frase diz com todas as letras qual é o
        # nome, é ele que manda.
        _resgatar_nome(frase, achado, criador, so_na_frase=True)


def _resgatar_nome(frase, achado, criador, so_na_frase=False):
    """Acha o nome pelo padrão explícito "se chama X" na frase inteira.

    Com `so_na_frase=True`, substitui o nome atual SÓ quando o padrão
    explícito aparece na frase — o "vai ser" lixo cede para o
    "calculadora de dieta" que a pessoa escreveu com todas as letras.
    """
    import re
    baixa = (frase or "").lower()
    # "o projeto vai se chamar calculadora de dieta" / "chamado estoque" /
    # "o nome é loja" — o padrão mais explícito de dar nome. Captura o nome
    # INTEIRO, incluindo partes com espaço ("calculadora de dieta"), e
    # corta na primeira vírgula/cláusula de propósito ("... , vai ser
    # usada para ..." não pode entrar no nome).
    talvez = [_limpar(g) for g in re.findall(
        r"(?:se\s+chama[r]?\s+|chamad[oa]\s+|o\s+nome\s+(?:é|e)\s+)"
        r"(?:de\s+)?([\w\-]+(?:\s+[\w\-]+)*)", baixa)]
    while talvez and (not talvez[0] or len(talvez[0]) < 4):
        talvez.pop(0)
    if not talvez:
        return None
    nome = talvez[0]
    # corta no propósito colado: "calculadora para contas" → "calculadora"
    for marco in (" para ", " pra ", " que ", " usado ", " usada ",
                  " utiliza ", " usado(a) "):
        corte = nome.find(marco)
        if corte > 0:
            nome = nome[:corte]
            break
    if not nome or len(nome) < 4:
        return None
    if not so_na_frase or achado.get("nome") != nome:
        achado["nome"] = nome
        achado["de_onde"]["nome"] = f"vi '{nome}' na sua frase"
    return nome


class Criador:
    """Junta etiquetador + detector + compositor num pedido só."""

    def __init__(self, raiz=RAIZ):
        self.raiz = Path(raiz)
        self.etiquetador = self.detector = self.compositor = None
        self.faltou = []
        self._carregar()

    def _carregar(self):
        """Carrega o que existir. O que faltar vira aviso, não exceção.

        O aplicativo tem que subir mesmo sem os três modelos treinados —
        senão quem clonou o projeto e ainda não rodou os treinos fica com
        um programa que não abre, sem saber por quê.
        """
        try:
            from modelo.etiquetador import EtiquetadorTreinado
            self.etiquetador = EtiquetadorTreinado(
                self.raiz / "modelos" / "etiquetador.json")
        except Exception as e:
            self.faltou.append(f"etiquetador: {e}")
        try:
            from modelo.detector import Detector
            self.detector = Detector(self.raiz / "modelos" / "detector.json")
        except Exception as e:
            self.faltou.append(f"detector: {e}")
        try:
            from modelo.compositor import Compositor
            self.compositor = Compositor(self.raiz / "modelos" / "compositor.json")
        except Exception as e:
            self.faltou.append(f"compositor: {e}")

    @property
    def pronto(self):
        return self.compositor is not None

    # ── o que ele sabe montar, saído da MEMÓRIA ──────────────────────
    def tipos_que_sei(self, linguagem=None):
        """Os tipos que o compositor JÁ MONTOU — e nessa linguagem, se dita.

        Sai de `compositor.memoria`, não de uma lista escrita à mão: no dia
        em que ele aprender `python|worker`, a opção aparece aqui sozinha,
        sem ninguém editar este arquivo.
        """
        if self.compositor is None:
            return []
        vistos = []
        for chave in self.compositor.memoria:
            partes = str(chave).split("|")
            if len(partes) < 2:
                continue
            if linguagem and partes[0] != linguagem:
                continue
            if partes[1] not in vistos:
                vistos.append(partes[1])
        if vistos:
            return vistos
        return list(getattr(self.compositor.estrutura, "tipos", []))

    def linguagens_que_sei(self):
        if self.compositor is None:
            return []
        return list(getattr(self.compositor.estrutura, "linguagens", []))

    # ── entender o pedido ────────────────────────────────────────────
    def entender(self, frase, codigo=None, antes=None):
        """Devolve o que deu para tirar, e o que ficou faltando.

        A ORDEM DAS FONTES É DE PROPÓSITO: o que a pessoa ESCREVEU vale
        mais que o que o detector adivinhou de um trecho colado. Se ela
        disse "em python" e colou um exemplo em C#, ela quer python — o
        exemplo é ilustração, a frase é o pedido.

        `antes` É O QUE JÁ FOI ENTENDIDO NESTA CONVERSA, e existe por um
        defeito medido: cada frase era lida do zero. Você pedia "cria um
        projeto calculadora em python", ele perguntava o tipo, você
        respondia "console" — e essa resposta chegava aqui como uma frase
        sem linguagem e sem nome. Ele perguntava tudo de novo, para
        sempre. O que vem novo manda; o que não vem, fica.
        """
        achado = {"linguagem": None, "tipo": None, "nome": None,
                  "de_onde": {}, "faltando": []}
        if antes:
            for campo in ("linguagem", "tipo", "nome"):
                if antes.get(campo):
                    achado[campo] = antes[campo]
                    achado["de_onde"][campo] = (antes.get("de_onde", {})
                                                .get(campo, "você já tinha dito"))
        campos = {}
        if self.etiquetador is not None:
            try:
                campos = self.etiquetador.campos(frase)
            except Exception:
                campos = {}

        bruto_ling = (campos.get("LING") or "").strip().lower()
        if bruto_ling:
            ling, _ = traduzir(bruto_ling, LINGUAGENS_CONHECIDAS)
            if ling:
                achado["linguagem"] = ling
                achado["de_onde"]["linguagem"] = f"você escreveu '{bruto_ling}'"
            else:
                achado["faltando"].append(
                    f"você escreveu '{bruto_ling}' e eu ainda não sei escrever "
                    f"nessa linguagem — as que eu sei estão logo abaixo")

        if achado["linguagem"] is None and codigo and self.detector is not None:
            palpite = self.detector.adivinhar(codigo)
            if palpite:
                achado["linguagem"] = palpite[0]
                achado["de_onde"]["linguagem"] = (
                    f"o exemplo que você colou é {palpite[0]} ({palpite[1]:.0%})")

        bruto_tipo = (campos.get("TIPO") or "").strip().lower()
        sobrou_do_tipo = ""
        if bruto_tipo:
            tipo, sobra = traduzir(bruto_tipo, TIPOS_CONHECIDOS)
            if tipo:
                achado["tipo"] = tipo
                achado["de_onde"]["tipo"] = f"você escreveu '{bruto_tipo}'"
                # o que sobrou do campo continua sendo pedido da pessoa —
                # "calculadora console" tem o tipo E o nome no mesmo campo
                sobrou_do_tipo = sobra
            else:
                sobrou_do_tipo = bruto_tipo

        nome = (campos.get("NOME") or "").strip()

        # O TIPO PODE TER SIDO ETIQUETADO COMO NOME. "cria um projeto
        # console em C#" às vezes sai NOME='console', TIPO=''. A palavra é
        # a mesma e a lista de tipos é a mesma; deixar passar era batizar o
        # projeto de "console" e perguntar o tipo logo abaixo.
        if achado["tipo"] is None and nome:
            do_nome, resto_nome = traduzir(nome.lower(), TIPOS_CONHECIDOS)
            if do_nome:
                achado["tipo"] = do_nome
                achado["de_onde"]["tipo"] = f"você escreveu '{nome}'"
                nome = resto_nome.strip()

        # ── NADA DO QUE FOI EXTRAÍDO SE PERDE ────────────────────────
        #
        # Em "cria um projeto calculadora em python" o etiquetador achou
        # "calculadora" e chamou de TIPO. A tradução procurou na lista de
        # tipos, não achou, e a palavra SUMIA — e aí ele perguntava "que
        # tipo?" e "como vai se chamar?", sendo que o nome estava escrito
        # na frase, e ele tinha achado.
        #
        # Se a palavra não é um tipo conhecido, ela ainda é um CAMPO do
        # pedido: o etiquetador já disse isso. E só sobrou um campo onde
        # ela cabe. Isso não é chute, é aproveitar o que já foi medido.
        #
        # Quando as duas partes estão coladas na frase ("sistema de
        # aluguel" + "carros" em "um sistema de aluguel de carros"), elas
        # são UM nome só, e cortar no meio dava a pasta "carros".
        if sobrou_do_tipo:
            baixa = (frase or "").lower()
            junto = None
            for cola in (f"{sobrou_do_tipo} de {nome}".lower(),
                         f"{sobrou_do_tipo} {nome}".lower()):
                if nome and cola in baixa:
                    junto = cola
                    break
            if junto:
                nome = junto
                achado["de_onde"]["nome"] = f"você escreveu '{junto}'"
            elif not nome:
                # "monta um projeto DE LOJA em php" dava o nome "de loja".
                # A preposição da frase não faz parte do nome de nada.
                nome = sobrou_do_tipo
                for pre in ("de ", "da ", "do ", "dum ", "duma ", "para ", "pra "):
                    if nome.startswith(pre):
                        nome = nome[len(pre):]
                        break
                achado["de_onde"]["nome"] = (
                    f"você escreveu '{sobrou_do_tipo}' — não é um tipo que eu "
                    f"conheço, então entendi como o nome")

        # UM NOME JÁ DADO NÃO CAI POR SOBRA DE OUTRA FRASE.
        #
        # "na verdade quero em php" é uma frase sobre a LINGUAGEM. O
        # etiquetador tira dela NOME='verdade' — e isso entrava por cima
        # do "agenda" que já estava decidido. Se a frase mudou a
        # linguagem ou o tipo, ela era sobre isso; o nome que sobra dela é
        # ruído, e o nome que já existe fica.
        virou_de_assunto = bool(antes) and (
            (achado["linguagem"] and achado["linguagem"] != (antes or {}).get("linguagem"))
            or (achado["tipo"] and achado["tipo"] != (antes or {}).get("tipo")))
        # NOME DE TRÊS LETRAS TIRADO DO MEIO DA FRASE QUASE NUNCA É NOME.
        #
        # Em "e o projeto? faz console" o etiquetador devolveu NOME='faz'.
        # Não é uma lista de verbos escrita à mão — é um corte por
        # tamanho: nome de projeto com 1 a 3 letras é raro, e quando
        # alguém quer mesmo um, diz de novo e ele entra pela resposta
        # curta logo abaixo, que não tem esse corte porque ali a pergunta
        # foi minha e a resposta é inequívoca.
        if nome and len(nome) < 4:
            nome = ""
            achado["de_onde"].pop("nome", None)
        if nome and not (virou_de_assunto and (antes or {}).get("nome")):
            achado["nome"] = nome
            achado["de_onde"].setdefault("nome", f"você escreveu '{nome}'")

        # ── A RESPOSTA CURTA A UMA PERGUNTA QUE EU FIZ ───────────────
        #
        # O etiquetador foi treinado em FRASES, com janela de ±2 em volta
        # da palavra. Medido: `campos("console")` devolve {} e
        # `campos("python")` devolve NOME='python'. Uma palavra sozinha não
        # tem contexto nenhum, então ele não tem de onde tirar o papel dela.
        #
        # Mas EU acabei de perguntar. Se a pergunta foi "que tipo?" e a
        # resposta tem duas palavras, ela é o tipo — isso é o contexto da
        # conversa, não adivinhação. Só vale quando `antes` existe: fora de
        # uma pergunta minha, "console" pode ser qualquer coisa.
        if antes and frase and len(frase.split()) <= 3:
            curta = frase.strip().lower().strip("?.!,")
            # "CSHARP, CONSOLE, CALCULADORA" SÃO TRÊS RESPOSTAS, UMA POR
            # CAMPO. O usuário respondeu a pergunta "responda o que falta"
            # com uma lista — e antes a lista inteira caía num campo só: a
            # busca procurava "csharp, console, calculadora" na tabela,
            # errava, e o etiquetador ainda marcava "csharp," como NOME.
            # Separar por vírgula e preencher na ordem linguagem → tipo →
            # nome é ler a resposta do jeito que ela foi escrita.
            partes = [_limpar(p) for p in curta.split(",")]
            partes = [p for p in partes if p]
            so_lista = len(partes) > 1

            # A ETIQUETA `NOME` DE UMA PALAVRA SOLTA NÃO VALE NADA, e isso
            # foi medido: `campos("python")` devolve NOME='python'. Ele
            # etiqueta pela vizinhança, e palavra sozinha não tem
            # vizinhança — então chuta o campo mais comum. Respondendo
            # "python" à pergunta "em que linguagem?", o projeto ia se
            # chamar "python". E respondendo "csharp, console, calculadora"
            # ele marcava "csharp," como NOME. Só apago o que o etiquetador
            # pôs AGORA; nome que veio de antes na conversa fica.
            if (achado["nome"] and (achado["nome"].lower() == curta or so_lista)
                    and achado["nome"] != (antes or {}).get("nome")):
                # devolve o nome que já estava guardado, se havia um: a
                # resposta "csharp" à pergunta da linguagem não pode apagar
                # o "sistema de aluguel de carros" que ele já tinha dito.
                achado["nome"] = (antes or {}).get("nome")
                if achado["nome"]:
                    achado["de_onde"]["nome"] = (
                        (antes.get("de_onde") or {}).get("nome", "você já tinha dito"))
                else:
                    achado["de_onde"].pop("nome", None)

            # CADA PARTE VAI PARA O CAMPO DA NATUREZA DELA, EM ORDEM DE
            # IMPORTÂNCIA: linguagem, tipo, nome. Antes a decisão era "o
            # próximo campo vazio", e isso quebrava quando `antes` já
            # preenchia linguagem+tipo: a lista "csharp, console,
            # calculadora" batizava o projeto de "csharp". Decidir pelo que
            # a PARTE É (e não pelo que falta) lê a lista do jeito certo na
            # ordem natural e também em ordem trocada ("console, csharp").
            for parte in partes:
                ling = (LINGUAGENS_CONHECIDAS.get(parte)
                        or (parte if parte in self.linguagens_que_sei() else None))
                if ling:
                    if achado["linguagem"] is None:
                        achado["linguagem"] = ling
                        achado["de_onde"]["linguagem"] = f"você respondeu '{parte}'"
                    continue
                tipo = (TIPOS_CONHECIDOS.get(parte)
                        or (parte if parte in self.tipos_que_sei() else None))
                if tipo:
                    if achado["tipo"] is None:
                        achado["tipo"] = tipo
                        achado["de_onde"]["tipo"] = f"você respondeu '{parte}'"
                    continue
                if achado["nome"] is None:
                    achado["nome"] = parte
                    achado["de_onde"]["nome"] = f"você respondeu '{parte}'"

        # ── QUANDO O ETIQUETADOR PERDE A FRASE INTEIRA ────────────────
        #
        # Medido: "gostaria de fazer em Csharp, um console, o projeto vai
        # se chamar calculadora" devolve TIPO='fazer' e NOME='vai' — o
        # etiquetador etiqueta pela vizinhança e esta frase tem o nome longe
        # da palavra-chave. O pedido tinha tudo com todas as letras: "csharp"
        # e "console" são palavras conhecidas das listas da casa, e "se
        # chamar X" é o padrão mais explícito que existe para dar um nome.
        # Vale passar a frase de novo e RESGATAR o que está escrito nela —
        # isto não é adivinhar, é ler.
        if achado["linguagem"] is None or achado["tipo"] is None \
                or achado["nome"] is None:
            _resgatar(frase, achado, self)

        # ── PERGUNTAR EM BRANCO É PERGUNTAR MAL ──────────────────────
        # "que tipo de projeto?" sozinho obriga a pessoa a adivinhar o que
        # ele aceita. As opções saem da MEMÓRIA do compositor, filtradas
        # pela linguagem que ela já disse — só o que ele sabe mesmo montar.
        # Elas NÃO colam na pergunta: vão numa linha separada de sugestão
        # (a `_pedido_pela_metade` monta isso), porque lista colada vira
        # resposta colada — o usuário copia a lista inteira e o etiquetador
        # lê "csharp, html, javascript…" como se fosse um nome. Pergunta
        # curta, opções por baixo.
        if achado["linguagem"] is None:
            achado["faltando"].append("em que linguagem?")
        if achado["tipo"] is None:
            achado["faltando"].append("que tipo de projeto?")
        if achado["nome"] is None:
            achado["faltando"].append("como o projeto vai se chamar?")

        # ── O NOME JÁ DITO NÃO MORRE POR ACIDENTE ─────────────────────
        # O `antes` guardou "mediaprovas"; a RESPOSTA da pergunta do
        # propósito foi "calcular a media das provas...". O etiquetador
        # marcou "media das" como NOME e o plano ia sair **media-das**,
        # apagando o nome que a pessoa deu com todas as letras. A
        # proteção da linha de cima só cobre resposta curta ou lista —
        # frase longa passava. Nome só troca se a frase REVELOU outro com
        # o padrão explícito ("se chama X", "chamado X", "o nome é X").
        import re as _re
        if ((antes or {}).get("nome")
                and achado["nome"] != antes["nome"]
                and not _re.search(
                    r"\b(?:se chama|se chamar|chamad[oa]|chamar|o nome é"
                    r"|denominad[oa]|apelidado)\b[^.,;]*",
                    frase, _re.IGNORECASE)):
            achado["nome"] = antes["nome"]
            achado["de_onde"]["nome"] = (antes.get("de_onde") or {}).get(
                "nome", "você já tinha dito")
        return achado

    @staticmethod
    def nome_de_pasta(nome):
        """"sistema de aluguel de carros" → "sistema-de-aluguel-de-carros".

        O nome que a pessoa fala vira pasta, e pasta com espaço e acento dá
        dor de cabeça em terminal, em git e em import. Isto não é decidir
        nada pelo usuário: o nome dele continua aparecendo na conversa, o
        que muda é só a forma que vai para o disco.
        """
        import re
        import unicodedata
        limpo = unicodedata.normalize("NFD", (nome or "").strip())
        limpo = "".join(c for c in limpo
                        if unicodedata.category(c) != "Mn")
        limpo = re.sub(r"[^A-Za-z0-9._-]+", "-", limpo).strip("-")
        return limpo or "projeto"

    # ── o plano ──────────────────────────────────────────────────────
    def planejar(self, linguagem, tipo, nome, gerar=False):
        if not self.pronto:
            return {"erro": "compositor_nao_treinado", "faltou": self.faltou}
        return self.compositor.planejar(linguagem, tipo, nome,
                                        gerar_conteudo=gerar)

    def arvore(self, plano):
        """O plano como texto de árvore, para caber num cartão."""
        if "erro" in plano:
            return f"não consegui planejar: {plano['erro']}"
        linhas = [f"{plano['nome']}/"]
        caminhos = sorted(a["caminho"] for a in plano["arquivos"])
        por_arquivo = {a["caminho"]: a for a in plano["arquivos"]}
        vistas = set()
        for cam in caminhos:
            partes = Path(cam).parts
            for nivel in range(1, len(partes)):
                pasta = "/".join(partes[:nivel])
                if pasta not in vistas:
                    vistas.add(pasta)
                    linhas.append("  " * nivel + partes[nivel - 1] + "/")
            a = por_arquivo[cam]
            # A MARCA DIZ DE ONDE VEIO. Um arquivo que ele lembrou e um
            # que ele adaptou não valem o mesmo, e você tem que ver a
            # diferença ANTES de confirmar, não depois de compilar.
            origem = a["origem"]
            if origem == "memoria":
                marca = ""
            elif origem == "gerado":
                marca = "  (escrito pela rede)"
            elif origem == "nao_sei":
                marca = "  ← não sei escrever este"
            elif origem == "extensao_estranha":
                marca = "  ← o nome não bate com a linguagem"
            elif origem == "memoria_de_outra_linguagem":
                marca = "  (de outra linguagem, mesma extensão)"
            elif origem.startswith("memoria_de_"):
                marca = f"  (do seu exemplo de {origem[len('memoria_de_'):]})"
            else:
                marca = "  (confira)"
            linhas.append("  " * len(partes) + partes[-1] + marca)
        return "\n".join(linhas)

    def escrever(self, plano, onde):
        return self.compositor.escrever_no_disco(plano, onde)
