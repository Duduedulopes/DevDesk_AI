# -*- coding: utf-8 -*-
"""O AGENTE — o `consertar.py` com um catálogo no lugar da ação única.

    perceber → escolher a FERRAMENTA → usar → ver o que voltou → repetir

O ONDE está decidido (o juiz diz linha e coluna), o O QUE também (o NOME que
não existe, o token que falta). O que sobra é a ESTRATÉGIA: em que ordem usar
as ferramentas, e quando desistir. É só isso que a política aprende.

O ESTADO É UM TEXTO, MAS NÃO COLA TUDO — e a medição mandou

`texto_do_caso` gera 66 peças. Colando `ler` e `procurar` inteiros, o estado
vai a 498: o erro vira 13% do que a rede lê, e o resumo é uma média — o
conteúdo do meu código afoga a mensagem do compilador.

A saída de cada ferramenta entra RESUMIDA, como a forma do resultado e não o
corpo dele:

    ler: 9 linhas            (ou "nao abriu")
    procurar: nenhum achado  (ou "2 achado(s), o primeiro em Transacao.cs")
    julgar: 2 erro(s) restante(s)
    consertar: familia nome_errado reprovada pelo juiz

A saída COMPLETA fica guardada num campo do passo, à parte — é o que os
moldes precisam (`montar`), e não o que a Peneira precisa (a média).

O PASSO QUE FALHOU É O REGISTRO MAIS IMPORTANTE

"consertar: familia nome_errado reprovada pelo juiz" diz o que NÃO funcionou.
Sem esse slot o agente tenta a mesma família de novo até estourar os seis
passos. Ele entra no texto E num conjunto (`falhas_de_conserto`) que a
política consulta antes de oferecer `consertar` de novo.

O ARGUMENTO NÃO É ESCOLHA DA REDE

Quando o compilador diz `'valorr' does not contain...`, qual nome procurar
está escrito na mensagem — é `==`, não palpite. A política escolhe a
FERRAMENTA; o argumento sai do estado. É a mesma regra que governa o resto do
projeto.

AUTORIZAÇÃO — LER É LIVRE, ESCREVER PEDE

    livres     `ler`, `procurar`, `julgar` — nada mudam no disco, rodam
               sobre a cópia.
    escreve    `consertar` — grava na CÓPIA, re-julga, e o resultado
               aprovado passa pelo diff e pelo `[s/N]` no programa.

COM E SEM REDE, NO MESMO LUGAR

A `PoliticaPorRegra` é a linha de base e o programa roda sem modelo nenhum.
A `PoliticaDaRede` lê o JSON treinado quando ele existe — e é a mesma forma
(média de peças → oculta → softmax) do `ClassificadorDeIntencao`. A trava do
tokenizador é a do `EscolhaDeFamilia`: modelo lido com o tokenizador errado
aponta para as linhas erradas da tabela e responde ruído SEM LEVANTAR
EXCEÇÃO.
"""
from pathlib import Path

import numpy as np

from modelo.consertos import (FAMILIAS, PISTAS, _NOME_CITADO,
                              familia_pela_pista, montar, texto_do_caso)
from modelo.decisor_linq import Peneira
from modelo.ferramentas import NOMES, usar

LIMITE_DE_PASSOS = 6


# ══════════════════════════════════════════════════════════════════════
#  O ESTADO — um texto para a Peneira, as saídas completas à parte
# ══════════════════════════════════════════════════════════════════════
class PassoDoAgente:
    """Uma ferramenta usada: a ação, o RESUMO dela e a saída COMPLETA.

    O resumo é o que a Peneira lê (a forma do resultado). A saída completa é
    o que os moldes usam — ficando num campo separado ela não afoga a
    mensagem do compilador no meio do código.
    """

    __slots__ = ("acao", "resumo", "completo")

    def __init__(self, acao, resumo, completo=None):
        self.acao, self.resumo, self.completo = acao, resumo, completo

    def __repr__(self):
        return f"<passo {self.acao}: {self.resumo}>"


class EstadoDeAgente:
    """Tudo o que o agente sabe sobre um erro, no formato que a Peneira lê.

    O texto é montado como o `texto_do_caso`: o erro primeiro, e depois cada
    ferramenta como `"passo N <acao>: <resumo>"`. O passo N dentro do texto
    dá à rede o orçamento que resta — sem ele, "passo 2 de 6" e "passo 5 de
    6" seriam o mesmo objeto.
    """

    def __init__(self, erro):
        self.erro = erro
        self.passos = []
        # AS FAMÍLIAS QUE O JUIZ JÁ REPROVOU. É o registro que impede o
        # agente de tentar a mesma coisa duas vezes — e a pior tentativa é
        # a repetida, porque custa um passo e entrega zero informação.
        self.falhas_de_conserto = set()
        self.resolvido = False
        self.conserto = None          # o `Conserto` aprovado pelo juiz, se houve

    def registrar(self, acao, resumo, completo=None):
        self.passos.append(PassoDoAgente(acao, resumo, completo))

    def testo(self):
        """O texto único que a política lê."""
        partes = [texto_do_caso(self.erro)]
        for i, p in enumerate(self.passos, 1):
            partes.append(f"passo{i} {p.acao}: {p.resumo}")
        return " || ".join(partes)

    def completo_de(self, acao):
        """A última saída completa da ferramenta `acao`, ou None.

        É este o caminho dos moldes: `procurar` devolveu onde o nome aparece,
        e é essa lista que um conserto de `nome_errado` pode consultar — sem
        precisar reconstituí-la da prosa que entrou na média.
        """
        for p in reversed(self.passos):
            if p.acao == acao and p.completo is not None:
                return p.completo
        return None

    def ja_tentou(self, familia):
        return familia in self.falhas_de_conserto

    def raciocinio(self):
        """A sequência inteira do que foi tentado — metade do valor do agente.

        Quando os seis passos estouram, é isto que fica na tela: não "não
        sei", mas "fui por aqui, por aqui, e aqui o juiz me reprovou".
        """
        linhas = [f"  erro: {self.erro}"]
        for i, p in enumerate(self.passos, 1):
            linhas.append(f"  passo {i}: {p.acao} — {p.resumo}")
        linhas.append("  RESOLVIDO" if self.resolvido
                      else f"  sem sucesso em {len(self.passos)} passo(s)")
        return "\n".join(linhas)


# ══════════════════════════════════════════════════════════════════════
#  OS RESUMOS — a forma do resultado, denunciando a saída completa
# ══════════════════════════════════════════════════════════════════════
def resumo_ler(saida):
    if not saida or "não consegui abrir" in saida:
        return "nao abriu"
    return f"{len(saida.splitlines())} linhas"


def resumo_procurar(saida):
    if "não aparece em nenhum arquivo" in (saida or ""):
        return "nenhum achado"
    achados = [l for l in (saida or "").splitlines()
               if ":" in l and not l.startswith("`")]
    if not achados:
        return "nenhum achado"
    primeiro = achados[0].split(":", 1)[0]
    return f"{len(achados)} achado(s), primeiro em {primeiro}"


def resumo_julgar(saida):
    try:
        n = len(saida)
    except TypeError:
        n = 0
    return "sem erros" if n == 0 else f"{n} erro(s) restante(s)"


def resumo_consertar(familia, veredito):
    return f"familia {familia} {veredito}"


# ══════════════════════════════════════════════════════════════════════
#  O JUIZ DIANTE DE UM CONSERTO — a mesma régua do `consertar.py`
# ══════════════════════════════════════════════════════════════════════
def veredito_do_juiz(depois, erro, conserto):
    """`provado` quando o erro some E nada nasce na linha que eu editei.

    A régua é exatamente a do `uma_rodada`, na mesma ordem:

       nao resolveu → o mesmo erro (arquivo, linha, código) continua lá
       estragou     → o erro some mas OUTRO nasce na linha que eu editei
       provado      → o erro some e nada nasce na linha editada

    A ordem importa: enquanto o erro original está lá, é `nao resolveu`,
    mesmo que outro erro tenha nascido junto. E erro que aparece DEPOIS não
    é erro que eu causei: um `;` que faltava esconde os erros semânticos
    atrás dele, e consertá-lo os revela. Isso é progresso, e por isso
    "menos erros que antes" nunca foi a métrica.
    """
    if depois is None:
        return "nao deu para julgar"
    mesmo = lambda e: (e.linha == erro.linha and e.codigo == erro.codigo
                       and Path(e.arquivo).name == Path(erro.arquivo).name)
    if any(mesmo(e) for e in depois):
        return "nao resolveu"
    estragou = any(
        Path(e.arquivo).name == Path(conserto.arquivo).name
        and e.linha == conserto.linha and not mesmo(e)
        for e in depois)
    return "estragou" if estragou else "provado"


# ══════════════════════════════════════════════════════════════════════
#  AS POLÍTICAS — escolher a ferramenta dado o estado
# ══════════════════════════════════════════════════════════════════════
def sugestoes_de_familia(erro, rede=None):
    """A opinião sobre a família — o que o agente tenta PRIMEIRO.

    A mesma ordem do `uma_rodada`: a rede das famílias primeiro (acerta mais
    no geral), a pista do código do erro depois. A pista sozinha é a linha de
    base — e em `SyntaxError` puro ela não distingue nada, que é onde 53%
    das quebras de Python caem.
    """
    opinioes = []
    if rede is not None:
        try:
            opinioes.append(rede.escolher(erro)[0])
        except Exception:                                   # noqa: BLE001
            pass
    pista = familia_pela_pista(erro)
    if pista and pista not in opinioes:
        opinioes.append(pista)
    return opinioes


_SINTAXE_PREFERIDAS = ("falta_virgula", "palavra_errada",
                       "igual_no_if", "pontuacao_dobrada")


def _outras_familias(erro):
    """As famílias que a opinião não viu, na ordem de valer tentar.

    Para `SyntaxError`, as quatro da FORMA da linha vêm primeiro — a
    mensagem ambígua ("invalid syntax", "forgot a comma?") não distingue
    entre elas, mas o MOLDE distingue, e a medição na prova mostrou que
    só essas quatro resolviam os 35 casos em que a opinião errara.
    `falta_operador` e `nao_sei` ficam de fora: não têm molde, e tentá-las
    custa um passo sem devolver informação.
    """
    preferidas = (_SINTAXE_PREFERIDAS
                  if str(getattr(erro, "codigo", "") or "") == "SyntaxError"
                  else ())
    return list(preferidas) + [f for f in FAMILIAS
                               if f not in preferidas
                               and f not in ("falta_operador", "nao_sei")]


def _candidatas_familia(erro, estado, rede=None):
    """A ordem inteira de tentativa: a opinião primeiro, o resto depois.

    É esta a ÚNICA fonte de candidatas do agente — a política e o
    `consertar` olham o MESMO pedaço. Foi a divergência entre duas fontes
    que custou o conserto que a primeira medição mostrou (a política via
    a rede, o consertar não). E quando a opinião falha e a família certa
    não estava nela, a segunda volta mostra o resto — sem ela o agente
    desistia nos 35 casos medidas na prova.
    """
    ordem = list(sugestoes_de_familia(erro, rede))
    for f in _outras_familias(erro):
        if f not in ordem:
            ordem.append(f)
    return [f for f in ordem if f not in estado.falhas_de_conserto]


class PoliticaPorRegra:
    """A linha de base: a mesma sequência que uma pessoa sensata faria.

    ORDEM DAS REGRAS, E PORQUE ESTA ORDEM

    1. nada ainda        → `ler`: ver as linhas em volta antes de decidir.
    2. cita nome         → `procurar`: onde o nome mora (erro de outro
                          arquivo se resolve lá, não na linha do erro).
    3. resta família     → `consertar`: tentar a família ainda não reprovada.
    4. nada resta        → `desistir`: dizer "não sei" é ferramenta, não
                          falha — inventar seria pior.

    É CONTRA este número que a `PoliticaDaRede` tem de provar que serve.
    """

    def __init__(self, rede_familias=None):
        self.rede_familias = rede_familias

    @staticmethod
    def _cita_nome_procurar(erro):
        cod = str(getattr(erro, "codigo", "") or "")
        if cod in (PISTAS.get("nome_errado", []) + PISTAS.get("falta_using", [])):
            return bool(_NOME_CITADO.search(erro.mensagem or ""))
        return False

    def _restam_familias(self, estado):
        return bool(_candidatas_familia(estado.erro, estado,
                                       self.rede_familias))

    def escolher(self, estado):
        if not estado.passos:
            return "ler"
        if (self._cita_nome_procurar(estado.erro)
                and not any(p.acao == "procurar" for p in estado.passos)):
            return "procurar"
        if self._restam_familias(estado):
            return "consertar"
        return "desistir"


class PoliticaDaRede:
    """A política aprendida: o estado → a ferramenta.

    A MESMA FORMA DE DUAS OUTRAS REDES DO PROJETO: média das peças → oculta →
    softmax. Não há rede nova aqui — a forma que serve para escolher família
    serve para escolher ferramenta, e a diferença é só o rótulo de saída.

    A TRAVA DO TOKENIZADOR É OBRIGATÓRIA. Um modelo lido com o tokenizador
    errado não dá erro — dá ruído com cara de resposta, porque os índices
    das peças apontam para as linhas erradas da tabela. Já aconteceu aqui.
    """

    def __init__(self, caminho):
        import json
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("tokenizador") != "peneira":
            raise ValueError(
                f"{caminho} foi treinado com tokenizador {d.get('tokenizador')!r}; "
                "esta política só sabe ler 'peneira'. Retreine com "
                "`programas/treinar_agente.py`.")
        if list(d.get("intencoes", [])) != NOMES:
            raise ValueError(
                "este modelo foi treinado com outra lista de ferramentas "
                f"({len(d.get('intencoes', []))} contra {len(NOMES)} de agora): "
                "ele decide para ferramentas que não existem. Retreine com "
                "`programas/treinar_agente.py`.")
        self.peneira = Peneira.de_lista(d["pecas"])
        self.tabela = np.array(d["tabela"], dtype=float)
        c = d["camadas"]
        self.w0 = np.array(c[0]["pesos"]); self.b0 = np.array(c[0]["vies"]).reshape(-1, 1)
        self.w1 = np.array(c[1]["pesos"]); self.b1 = np.array(c[1]["vies"]).reshape(-1, 1)
        self.medido = d.get("medido", {})
        self._np = np

    def escolher(self, estado):
        np = self._np
        idx = self.peneira.ids(estado.testo())
        media = self.tabela[idx].mean(axis=0).reshape(-1, 1)
        oculta = 1.0 / (1.0 + np.exp(-(self.w0 @ media + self.b0)))
        z = self.w1 @ oculta + self.b1
        e = np.exp(z - z.max())
        p = (e / e.sum()).ravel()
        return NOMES[int(p.argmax())]


# ══════════════════════════════════════════════════════════════════════
#  O LAÇO
# ══════════════════════════════════════════════════════════════════════
class Agente:
    """O laço de decisão: escolhe a ferramenta, usa, vê o que voltou.

    `contexto` carrega o que varia de rodada para rodada:

        julgar          () → lista de Erro: o juiz sobre a CÓPIA atual
        raiz            a pasta do projeto (para `procurar`)
        nomes           os nomes do projeto (para `montar`)
        rede_familias   opcional, o `EscolhaDeFamilia` treinado

    PERCEBER QUE LER É LIVRE E ESCREVER PEDE está nesta função: as três
    livres caem em `usar`, o `consertar` aplica na cópia, re-julga e desfaz —
    e só o resultado PROVADO chega ao `estado.conserto`, para o programa
    mostrar o diff e perguntar. E se a tentativa falha, a família entra em
    `falhas_de_conserto` e o texto da série — esta é a memória que impede a
    repetição.
    """

    def __init__(self, politica, limite=LIMITE_DE_PASSOS):
        self.politica = politica
        self.limite = limite

    def _proxima_familia(self, estado, contexto):
        candidatas = _candidatas_familia(estado.erro, estado,
                                         contexto.get("rede_familias"))
        return candidatas[0] if candidatas else None

    def _consertar(self, estado, contexto):
        fam = self._proxima_familia(estado, contexto)
        if fam is None:
            estado.registrar("consertar", "sem familia candidata")
            return
        conserto = montar(estado.erro, fam, contexto.get("nomes", ()),
                          achados=estado.completo_de("procurar"),
                          lido=estado.completo_de("ler"),
                          raiz=contexto.get("raiz"))
        if conserto is None:
            # A família acertou e o molde mesmo assim não montou — a
            # mensagem não citou o nome, o tipo não está na tabela. Marcar
            # como falha impede tentar de novo no passo seguinte.
            estado.falhas_de_conserto.add(fam)
            estado.registrar("consertar",
                             resumo_consertar(fam, "sem molde"))
            return
        alvo = Path(conserto.arquivo)
        guardado = alvo.read_text(encoding="utf-8")
        conserto.aplicar()
        depois = contexto["julgar"]()
        alvo.write_text(guardado, encoding="utf-8")
        veredito = veredito_do_juiz(depois, estado.erro, conserto)
        if veredito == "provado":
            estado.resolvido = True
            estado.conserto = conserto
        else:
            estado.falhas_de_conserto.add(fam)
        estado.registrar("consertar", resumo_consertar(fam, veredito))

    def rodar(self, erro, contexto):
        """Um erro → o estado final, com a sequência inteira tentada."""
        estado = EstadoDeAgente(erro)
        while len(estado.passos) < self.limite and not estado.resolvido:
            acao = self.politica.escolher(estado)
            if acao == "desistir":
                estado.registrar("desistir", "desisti")
                break
            if acao == "consertar":
                self._consertar(estado, contexto)
                continue
            saida = usar(acao, erro, contexto)      # ler | procurar | julgar
            if acao == "ler":
                resumo = resumo_ler(saida)
            elif acao == "procurar":
                resumo = resumo_procurar(saida)
            else:
                resumo = resumo_julgar(saida)
            estado.registrar(acao, resumo, saida)
        return estado