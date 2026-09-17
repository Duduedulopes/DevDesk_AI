# -*- coding: utf-8 -*-
"""AS FERRAMENTAS DO AGENTE — o que ele pode fazer, e o que isso custa.

O `consertar.py` sabia UMA coisa: trocar a linha que o juiz apontou. Por
isso ele dizia "não sei consertar este" no `CS1503` — a informação para
resolver não estava naquela linha, e ele não tinha como ir buscar.

Um agente é o mesmo laço com um CATÁLOGO no lugar da ação única:

    perceber → escolher a ferramenta → usar → ver o que voltou → de novo

A DIVISÃO QUE IMPORTA: LER É LIVRE, ESCREVER PEDE

    livres    `ler`, `procurar`, `julgar` — não mudam nada no seu disco e
              rodam sobre a cópia. Parar para perguntar a cada uma delas
              faria um agente que pergunta seis vezes para consertar um
              ponto-e-vírgula.
    pedem     `editar`, `inserir` — tocam no seu arquivo. Continuam
              passando pelo diff e pelo `s`, como antes.

E `desistir` É UMA FERRAMENTA, não uma falha do laço. Um agente que não
tem como dizer "não sei" inventa — foi por isso que o `escritor_linq`
escrevia consulta que compilava e estava errada.

O ARGUMENTO NÃO É ESCOLHA DA REDE

Quando o compilador diz `'valorr' does not contain...`, QUAL nome
procurar não é julgamento: está escrito na mensagem. A rede escolhe a
FERRAMENTA; o argumento sai do estado por `==`. É a mesma regra que
governa o resto do projeto — pedir palpite onde existe resposta exata é
trocar acerto por chance.
"""
import re
from pathlib import Path

from modelo.consertos import montar, nome_do_tipo

FORA = {"bin", "obj", ".vs", ".git", "node_modules", "__pycache__", ".venv"}


class Ferramenta:
    """Nome, o que faz, e se mexe no disco de alguém."""

    def __init__(self, nome, escreve, resumo):
        self.nome, self.escreve, self.resumo = nome, escreve, resumo

    def __repr__(self):
        return f"<{self.nome}{' (escreve)' if self.escreve else ''}>"


CATALOGO = [
    Ferramenta("ler", False,
               "ver as linhas em volta do erro — o que a linha sozinha não conta"),
    Ferramenta("procurar", False,
               "achar onde o nome citado no erro aparece no resto do projeto"),
    Ferramenta("consertar", True,
               "aplicar o conserto da família escolhida nesta linha"),
    Ferramenta("julgar", False,
               "rodar o compilador de novo e ver o que sobrou"),
    Ferramenta("desistir", False,
               "dizer que não sei — com o que eu descobri até aqui"),
]
NOMES = [f.nome for f in CATALOGO]
POR_NOME = {f.nome: f for f in CATALOGO}


# ══════════════════════════════════════════════════════════════════════
#  O QUE CADA UMA FAZ
# ══════════════════════════════════════════════════════════════════════
def _linhas(caminho):
    try:
        return Path(caminho).read_text(encoding="utf-8",
                                       errors="replace").splitlines()
    except OSError:
        return []


def ler(erro, volta=4):
    """As linhas em volta do erro, numeradas.

    QUATRO LINHAS PARA CADA LADO, e não o arquivo inteiro: o que resolve
    quase todo erro de compilador está ao alcance da vista — a variável
    declarada duas linhas acima, o parêntese aberto na anterior. Jogar o
    arquivo inteiro no estado afogaria o sinal no ruído, e a `Peneira`
    não tem como saber qual parte importa.
    """
    ls = _linhas(erro.arquivo)
    if not ls:
        return "não consegui abrir o arquivo"
    a = max(0, erro.linha - 1 - volta)
    b = min(len(ls), erro.linha + volta)
    saida = []
    for i in range(a, b):
        marca = ">" if i == erro.linha - 1 else " "
        saida.append(f"{marca}{i + 1:>4} {ls[i]}")
    return "\n".join(saida)


def procurar(erro, raiz, nome=None):
    """Onde o nome citado no erro aparece no projeto — com arquivo e linha.

    É ISTO QUE RESOLVE O ERRO DE OUTRO ARQUIVO. Você renomeia uma
    propriedade no Model e o `Program.cs` quebra; a linha do erro não
    tem a resposta, mas a declaração tem — e ela está a uma busca de
    distância.

    QUEM SE BUSCA: quando a mensagem diz "does not contain a definition
    for" (CS0117/CS1061), o nome a procurar é o TIPO, não o membro — o
    membro já foi renomeado e não aparece em lugar nenhum. Sem isso o
    `procurar` só devolveria as próprias linhas quebradas.
    """
    if nome is None:
        nome = nome_do_tipo(erro)
    if not nome:
        return "o erro não cita nome nenhum para procurar"
    achados = []
    raiz = Path(raiz)
    alvos = [p for p in raiz.rglob("*.*")
             if p.suffix in (".cs", ".py") and not any(x in FORA for x in p.parts)]
    for p in alvos[:400]:
        try:
            onde = p.relative_to(raiz)
        except ValueError:
            onde = p
        for i, l in enumerate(_linhas(p), 1):
            if re.search(rf"\b{re.escape(nome)}\b", l):
                achados.append(f"{onde}:{i} {l.strip()[:80]}")
            if len(achados) >= 12:
                break
        if len(achados) >= 12:
            break
    if not achados:
        # NÃO ACHAR É INFORMAÇÃO, e das boas: se o nome não existe em
        # lugar nenhum do projeto, ele foi digitado errado — e não é um
        # nome de outro arquivo que faltou importar.
        return f"`{nome}` não aparece em nenhum arquivo do projeto"
    return f"`{nome}` aparece em:\n" + "\n".join(achados)


def consertar(erro, familia, nomes_conhecidos):
    """O conserto da família escolhida — ou o motivo de não dar."""
    c = montar(erro, familia, nomes_conhecidos)
    return c if c is not None else None


def usar(acao, erro, contexto):
    """Roda a ferramenta e devolve o que ela achou, como TEXTO.

    Texto, e não objeto: o que volta vai para o ESTADO, e o estado é lido
    pela mesma `Peneira` que lê o erro. Uma ferramenta que devolvesse uma
    estrutura precisaria de um caminho só dela até a rede.
    """
    if acao == "ler":
        return ler(erro)
    if acao == "procurar":
        return procurar(erro, contexto.get("raiz", "."))
    if acao == "julgar":
        return contexto["julgar"]()
    if acao == "desistir":
        return "desisti"
    return ""
