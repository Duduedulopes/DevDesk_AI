"""A sessão: a pasta, o registro de ações, e o que espera confirmação.

O REGISTRO É A CONVERSA, E NÃO UM ANEXO DELA

Cada coisa que o assistente faz vira um CARTÃO tipado na mesma coluna da
conversa: pensou, leu um arquivo, rodou um comando, procurou, classificou.
A saída do comando aparece onde a decisão foi tomada, que é onde ela é
entendida.

A aba "Terminal" do painel da direita NÃO leva nada embora daqui: ela é
uma SEGUNDA VISTA dos mesmos cartões, para quem quer o histórico corrido
dos comandos sem rolar a conversa inteira. Não há cópia — a aba lê os
cartões que já existem. O original continua onde a decisão aconteceu.

O QUE ESCREVE NÃO ACONTECE SOZINHO

Ação de risco vira um cartão `pendente` e para ali até alguém confirmar.
O registro guarda o que foi feito, quando, e o que devolveu — é o que
permite auditar e desfazer.
"""
import getpass
import json
import os
import re
import unicodedata
import subprocess
import time
from datetime import datetime
from pathlib import Path

from painel import respostas

# Só leitura, e a lista é FECHADA. Lista de permissão e não de bloqueio:
# comando novo nasce precisando de confirmação, sem ninguém lembrar de
# bloqueá-lo. É a mesma escolha do PerfilDeQuemFala da loja.
SO_LEITURA = {
    "ls", "dir", "cat", "type", "head", "tail", "find", "findstr", "grep",
    "pwd", "cd", "tree", "wc", "du", "df", "whoami", "hostname", "date",
    "git", "python", "python3", "pip", "dotnet", "node", "npm",
    "get-childitem", "get-content", "get-location", "get-process",
    "get-service", "test-path", "select-string", "measure-object",
}
LEITURA_DE_GIT = {"status", "log", "diff", "branch", "remote", "show", "ls-files"}

# Pastas que a busca nunca entra: são milhares de arquivos que ninguém procura.
IGNORA_BUSCA = {".git", "__pycache__", ".venv", "node_modules", "obj", "bin",
                ".vs", "packages", "AppData", "$RECYCLE.BIN", ".nuget", ".gradle"}


# ── de quem e este computador ────────────────────────────────────────
#
# Tres tentativas, da mais sua para a mais genérica:
#
#   dados/seu_nome.txt   existe para você trocar sem abrir código. Uma
#                        linha, o nome, salvou.
#   o usuário do Windows o que a máquina sabe sozinha. Aqui ele é
#                        "Samsung", que é o nome do computador e não o seu
#                        — daí o arquivo acima existir.
#   "desenvolvedor"      para qualquer pessoa que abrir isto e não tenha
#                        nem uma coisa nem outra.
#
# Lido UMA vez por execução: o nome não muda no meio da conversa, e ler
# arquivo a cada saudação seria disco gasto à toa.
_NOME_GUARDADO = None

def _proximo_passo(plano):
    """Sugestão natural do que fazer com o projeto recém-criado.

    Projeto criado é só o começo — a próxima fala oferece um caminho
    concreto (abrir/rodar) em vez de dar os parabéns e calar.
    """
    ling = (plano.get("linguagem") or "").lower()
    tipo = (plano.get("tipo") or "").lower()
    comando = {
        ("csharp", "console"): "dotnet run",
        ("csharp", "api"): "dotnet run",
        ("csharp", "biblioteca"): "dotnet build",
        ("python", "console"): "python main.py",
        ("python", "site"): "python app.py",
        ("javascript", "site"): "npm start",
    }.get((ling, tipo))
    dica = f"Pronto! Criei o projeto em `{plano['nome']}`."
    if comando:
        dica += (f"\n\nPróximo passo: rode `{comando}` dentro da pasta — "
                 f"ou me diga `abrir {plano['nome']}` que eu mostro o "
                 f"código como ficou.")
    else:
        dica += ("\n\nPróximo passo: quer que eu abra a estrutura e a gente "
                 "decida o que fazer primeiro?")
    return dica

def quem_e_voce(casa=None):
    global _NOME_GUARDADO
    if _NOME_GUARDADO:
        return _NOME_GUARDADO
    casa = casa or Path(__file__).resolve().parent.parent
    nome = ""
    arquivo = casa / "dados" / "seu_nome.txt"
    try:
        if arquivo.is_file():
            nome = arquivo.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except (OSError, IndexError):
        nome = ""
    if not nome:
        try:
            nome = (getpass.getuser() or "").strip()
        except Exception:
            nome = ""
    # Primeiro nome só, e nada absurdo: um login de vinte e oito letras na
    # saudação fica pior do que não ter nome nenhum.
    primeiro = nome.split()[0] if nome.split() else ""
    _NOME_GUARDADO = primeiro if 1 < len(primeiro) <= 20 else "desenvolvedor"
    return _NOME_GUARDADO


# As intenções que são PAM-PAM-PAM da conversa — não ganham o prelúdio
# da primeira pergunta, porque a resposta já É a conversa (um "claro,
# deixa eu olhar" antes de "oi!" duplica a empolgação). `criar_projeto`
# também está fora: ele já tem mensagem própria de pergunta/planejamento.
_CONVERSA_PURA = {
    "saudacao", "despedida", "agradecimento", "confirmar", "cancelar",
    "ajuda", "quem_e_voce", "reclamacao", "fora_de_escopo",
    "criar_projeto",
}


class Sessao:
    def __init__(self, pasta, cerebro=None):
        self.pasta = Path(pasta).resolve()
        # A PASTA DE CASA: aquela com que o aplicativo subiu. `fechar_projeto`
        # volta para cá. Guardar isto no começo é o que permite fechar sem
        # ficar sem pasta nenhuma — ver o comentário lá embaixo.
        self.pasta_inicial = self.pasta
        self.cerebro = cerebro
        self.cartoes = []
        self.pendentes = {}
        self.abas = []          # arquivos abertos no painel da direita
        self.tela = self._tela_parada()
        self.estado = "parado"
        self._voltas = {}       # caminho -> conteúdo anterior, para desfazer
        self.id = self._novo_id()
        self.ultima_mensagem = ""  # armazena última mensagem para as funções de resposta
        self.nome = ""
        self.criada = time.time()
        self._proximo = 1
        self._alvo_pendente = None   # abrir_projeto/arquivo pediu o caminho
        # O PEDIDO DE PROJETO A MEIO CAMINHO. Não é cópia de nada que
        # esteja nos cartões — é o único lugar onde mora o que já foi
        # entendido enquanto faltam campos. Sem ele, responder "console"
        # à pergunta "que tipo?" recomeçava do zero.
        self.pedido_projeto = None
        # A GARAGEM. Pedido de projeto que ficou pela metade porque a
        # conversa virou para outro assunto. NÃO se apaga: é o que já foi
        # entendido, e serve para voltar sem repetir e para virar treino.
        self.pedidos_parados = []
        # A PRIMEIRA PERGUNTA DE CADA CONVERSA merece um passo antes da
        # resposta — "claro, deixa eu olhar" — e só a primeira. Depois a
        # pessoa já sabe que estou ouvindo, repetir ficaria burocrático.
        self._primeiro_pedido = True

    # ── o estado: ONDE o sistema parou, e por que ────────────────────
    #
    # Veio do `AgentState` do Agent Canvas (MIT), em
    # `src/types/agent-state.tsx`. Treze estados la; o que importou nao foi
    # a lista, foi o que ela ADMITE:
    #
    #     awaiting_user_confirmation · user_confirmed · user_rejected
    #
    # Recusar e um ESTADO COM NOME, nao um erro. Um sistema que so sabe
    # "rodando" e "pronto" nao tem onde guardar "eu poderia, mas nao vou
    # sozinho" — e entao ou ele age, ou ele finge que terminou.
    #
    # A ARQUITETURA.md ja dizia isso em prosa na camada 5 ("nivel de risco,
    # confirmacao, registro e desfazer") e na espinha ("abster-se e
    # resposta"). Nao tinha forma no codigo. Agora tem.
    #
    # E OS DOIS SAO A MESMA COISA VISTA DE DOIS LADOS:
    #     aguardando_voce         nao sei          -> abstencao
    #     aguardando_confirmacao  sei, nao faco so -> freio
    # Em nenhum dos dois o sistema age por conta.
    #
    # ESTADO TRANSITORIO E VISIVEL DE VERDADE, e isso nao e enfeite: o
    # servidor e ThreadingHTTPServer, entao enquanto `receber` esta parado
    # num comando de 30 segundos, OUTRA thread atende o /api/estado. A tela
    # ve "investigando" durante a espera.
    ESTADOS = {
        "parado":                 ("ok",      "esperando você"),
        "pensando":               ("indo",    "classificando"),
        "investigando":           ("indo",    "colhendo evidência"),
        "aguardando_confirmacao": ("freio",   "precisa da sua confirmação"),
        "aguardando_voce":        ("duvida",  "não tenho certeza — escolha"),
        "erro":                   ("erro",    "deu erro"),
    }

    def virar(self, estado):
        if estado not in self.ESTADOS:
            raise ValueError(f"estado desconhecido: {estado}")
        self.estado = estado
        return estado

    def _assentar(self):
        """Para onde o estado CAI quando a resposta termina.

        Estado que não cai vira mentira na tela: o painel ficaria
        "investigando" para sempre depois de um comando que já acabou.

        DOIS TIPOS DE ESTADO, E CONFUNDI-LOS FOI O BUG:

          derivado    `aguardando_confirmacao` é verdade exatamente enquanto
                      existe pendência. Não é escolha — é leitura de
                      `self.pendentes`. Some a pendência, some o estado.
                      (Estava na lista dos que ficam, e depois de recusar a
                      única ação pendente a barra continuava dizendo
                      "precisa da sua confirmação". O teste pegou.)

          de parada   `aguardando_voce` e `erro` valem até a PRÓXIMA frase.
                      Não têm nada em `self` para derivar deles: a pergunta
                      continua aberta até alguém escrever de novo.

        Pendência ganha de tudo: se sobrou coisa esperando, é isso que a
        pessoa precisa ver, e não "esperando você".
        """
        if self.pendentes:
            return self.virar("aguardando_confirmacao")
        if self.estado in ("pensando", "investigando", "aguardando_confirmacao"):
            return self.virar("parado")
        return self.estado

    # ── a tela: a resposta nao e so texto, ela APONTA ────────────────
    #
    # A PESSOA NAO VE O QUE VOCE FEZ SE VOCE NAO MOSTRAR.
    #
    # Ideia lida no Agent Canvas do OpenHands (MIT), em
    # `src/api/canvas-ui-client-tool.ts`. La a IA ganha uma ferramenta cuja
    # unica funcao e dirigir o painel da direita, e a descricao dela avisa,
    # com todas as letras, que a pessoa NAO vera o arquivo escrito nem a
    # saida do comando a menos que a ferramenta seja chamada. Contar que
    # alguem repare sozinho e onde a tela silenciosamente falha.
    #
    # Aqui nao e ferramenta de modelo: e um metodo que a propria acao chama.
    # Quem abriu o arquivo sabe que abriu — ninguem melhor para dizer para
    # onde a tela deve olhar.
    #
    # DUAS REGRAS QUE VIERAM JUNTO, E AS DUAS VALEM:
    #
    #   antes do texto  a tela troca ANTES do cartao de resumo, para a coisa
    #                   estar visivel enquanto a pessoa le sobre ela.
    #
    #   uma por passo   `mostrar` SOBRESCREVE, nao empilha. Dez comandos numa
    #                   resposta apontam para um lugar so.
    ABAS = ("arquivo", "terminal", "projeto")

    @staticmethod
    def _tela_parada():
        # Funcao e nao constante de classe: um dicionario de classe seria o
        # MESMO objeto em toda sessao, e um dia alguem escreveria
        # `self.tela["aba"] = ...` e mudaria a tela de todo mundo.
        return {"aba": "arquivo", "caminho": None, "em": 0.0}

    def mostrar(self, aba, caminho=None):
        """Diz para onde o painel da direita deve olhar."""
        if aba not in self.ABAS:
            raise ValueError(f"aba desconhecida: {aba}")
        # `em` e o que o front-end compara para saber que houve ordem nova.
        # Sem ele, pedir a MESMA aba duas vezes seguidas nao mexeria na tela
        # — e "abre de novo" e justamente quando se quer a tela de volta la.
        self.tela = {"aba": aba, "caminho": caminho, "em": time.time()}
        return self.tela

    # ── o painel da direita ──────────────────────────────────────────
    #
    # DENTRO DA PASTA, E A CONFERÊNCIA É POR CAMINHO RESOLVIDO.
    # Comparar texto ("começa com C:\\...") não serve: `..\..\Windows`
    # começa com a pasta e sai dela. `resolve()` desfaz os `..` e os atalhos
    # antes de comparar, que é a única forma que aguenta caminho torto.
    LIMITE_ABA = 400_000

    def _pede_editor(self, frase):
        """Entende os muitos jeitos de dizer \"abre isso no editor\".

        Ninguém decora sintaxe de comando. \"code X\", \"abre X no vs code\",
        \"pode abrir o projeto X no visual studio\" — todos querem a mesma
        coisa, e exigir a forma exata é transferir para a pessoa o trabalho
        de falar como máquina.
        """
        f = frase.strip()
        b = f.lower()
        vs = any(x in b for x in ("visual studio", " no vs", "devenv")) and "code" not in b
        programa = "devenv" if vs else "code"

        for prefixo in ("code ", "vscode ", "vs code "):
            if b.startswith(prefixo):
                return f[len(prefixo):], programa
        # \"abre/abrir X no vs code\" — a menção ao editor decide, não o começo
        if any(x in b for x in ("vs code", "vscode", "visual code",
                                "visual studio code", "visual studio")):
            for prefixo in ("pode abrir ", "abrir ", "abre ", "abra "):
                if b.startswith(prefixo):
                    return f[len(prefixo):], programa
        return None

    @staticmethod
    def _limpar(bruto):
        """Tira o que é enfeite e não é caminho.

        Aspas, sinais de marcador (`<caminho>` que a pessoa copiou do
        placeholder sem substituir), e palavras de ligação. Sem isto o
        sistema sai procurando uma pasta chamada literalmente `<caminhi>`,
        que foi o que aconteceu.
        """
        t = bruto.strip().strip('"').strip("'").strip()
        if t.startswith("<") and t.endswith(">"):
            t = t[1:-1].strip()
        t = t.lstrip("<").rstrip(">").strip()
        # Path() no Windows trata / como separador, mas uma frase colada
        # com barra invertida no meio precisa chegar inteira, sem o
        # classificador "adivinhar" o que C:\Users é.
        for cola in ("o projeto ", "a pasta ", "o arquivo ", "esse projeto ",
                     "essa pasta ", "esse arquivo ", "projeto ", "pasta ", "arquivo "):
            if t.lower().startswith(cola):
                t = t[len(cola):].strip()
        for fim in (" no vs code", " no vscode", " no visual studio code",
                    " no visual code", " no vs", " no visual studio", " aqui"):
            if t.lower().endswith(fim):
                t = t[: -len(fim)].strip()
        return t

    # C:\Users\..., \\servidor\pasta, /home/dev/proj — a pessoa colou o
    # endereço, não escreveu uma intenção. A rede não foi treinada nisso
    # (cada letra vira peça) e chuta revisar_codigo a 23%. O caminho
    # tem que ser reconhecido ANTES da classificação mandar a conversa.
    _RE_WIN = re.compile(r"[A-Za-z]:[\\/][^\n\"'<>|*?]+")
    _RE_UNC = re.compile(r"\\\\[\w.\-]+\\[^\n\"'<>|*?]+")
    _CANCELA_ESPERA = {
        "ajuda", "help", "cancela", "cancelar", "não", "nao", "esquece",
        "deixa", "nada", "oi", "olá", "ola", "obrigado", "obrigada",
    }

    def _caminho_da_frase(self, frase):
        """O primeiro endereço de arquivo/pasta na frase, ou None."""
        t = self._limpar(frase or "")
        if not t:
            return None
        m = self._RE_WIN.search(t) or self._RE_UNC.search(t)
        if m:
            return m.group(0).rstrip(" \\/")
        if t.startswith("/") and "/" in t[1:] and "\n" not in t and len(t) < 400:
            return t.rstrip("/")
        return None

    def _e_caminho(self, frase):
        return self._caminho_da_frase(frase) is not None

    def _parece_nome_de_alvo(self, frase):
        """Depois de 'me diz a pasta', um nome curto sem interrogação é o alvo."""
        t = self._limpar(frase or "")
        if not t or self._alvo_pendente is None:
            return False
        b = t.lower().strip("!.")
        if b in self._CANCELA_ESPERA or t.startswith(">") or "?" in t:
            return False
        if "\n" in t or len(t) > 220:
            return False
        # Frase inteira de conversa, não um nome de pasta.
        if " " in t and not any(s in t for s in ("\\", "/", ":")):
            palavras = t.split()
            if len(palavras) > 4:
                return False
        return True

    def abrir_projeto_caminho(self, frase):
        cam = self._caminho_da_frase(frase) or self._limpar(frase)
        self._alvo_pendente = None
        return self.abrir(cam)

    def abrir(self, caminho):
        caminho = self._limpar(caminho)
        alvo = Path(caminho)
        if not alvo.is_absolute():
            alvo = self.pasta / alvo
        try:
            alvo = alvo.resolve()
        except OSError as erro:
            return self.cartao("ela", texto=f"Caminho inválido: {erro}")

        # NÃO EXISTE COMO CAMINHO? ENTÃO É UM NOME. Desistir aqui joga para
        # a pessoa o trabalho de lembrar o caminho inteiro — que é justamente
        # o que a máquina faz melhor que gente.
        if not alvo.exists():
            return self.procurar(caminho, motivo=f"`{caminho}` não é um caminho, então procurei")
        if alvo.is_dir():
            return self.trocar_pasta(alvo)

        bytes_ = alvo.stat().st_size
        if bytes_ > self.LIMITE_ABA:
            return self.cartao("ela", texto=(
                f"`{alvo.name}` tem {bytes_/1024/1024:.1f} MB — grande demais para o "
                f"painel. Use `> type \"{alvo}\"` para ver um pedaço."))
        try:
            conteudo = alvo.read_text(encoding="utf-8", errors="replace")
        except OSError as erro:
            return self.cartao("ela", texto=f"Não consegui ler: {erro}")

        self.abas = [a for a in self.abas if a["caminho"] != str(alvo)]
        self.abas.append({"caminho": str(alvo), "nome": alvo.name,
                          "conteudo": conteudo, "linhas": conteudo.count("\n") + 1,
                          "bytes": bytes_})
        self.abas = self.abas[-8:]      # oito abas bastam; a mais velha sai
        self.mostrar("arquivo", str(alvo))
        return self.cartao("abriu", caminho=str(alvo), nome=alvo.name,
                           linhas=conteudo.count("\n") + 1, bytes=bytes_)

    # ── trocar de projeto sem fechar o programa ──────────────────────
    #
    # A pasta era decidida no `python painel/app.py <pasta>` e nunca mais
    # mudava: para olhar outro projeto era fechar e abrir de novo. E abrir
    # uma pasta só respondia "isso é uma pasta, não um arquivo" — que é
    # verdade e não ajuda em nada.
    #
    # Trocar a pasta move QUATRO coisas de uma vez, e é bom saber quais:
    #   a aba Projeto     passa a mostrar a árvore dela
    #   `> comando`       roda dentro dela
    #   a busca           parte dela (e da pasta acima, para achar os irmãos)
    #   a máquina         `status_sistema` mede o disco e os arquivos dela
    #
    # O que NÃO muda é o cerco do gravar — esse agora é por aba aberta, e
    # não por pasta. Ver `_esta_aberto`.
    def trocar_pasta(self, caminho):
        alvo = Path(caminho)
        try:
            alvo = alvo.resolve()
        except OSError as erro:
            return self.cartao("ela", texto=f"Caminho inválido: {erro}")
        if not alvo.is_dir():
            return self.cartao("ela", texto=f"`{alvo}` não é uma pasta.")
        if alvo == self.pasta:
            self.mostrar("projeto", str(alvo))
            return self.cartao("projeto", caminho=str(alvo), nome=alvo.name, jaestava=True)

        antes = self.pasta
        self.pasta = alvo
        self.mostrar("projeto", str(alvo))
        return self.cartao("projeto", caminho=str(alvo), nome=alvo.name,
                           antes=str(antes), jaestava=False)

    # ── FECHAR O PROJETO ─────────────────────────────────────────────
    #
    # Abrir uma pasta tinha caminho; fechar não tinha nenhum. Quem abria
    # um projeto para olhar uma coisa ficava dentro dele até reiniciar o
    # programa — foi assim que apareceu.
    #
    # FECHAR AQUI QUER DIZER VOLTAR PARA A PASTA DE CASA, e não ficar sem
    # pasta. Sem pasta, `dir`, procurar, a árvore e o gravar não teriam
    # onde olhar, e cada um deles teria de aprender a lidar com o vazio —
    # cinco lugares novos para dar errado, em troca de nada.
    #
    # As abas vão junto: são arquivos DAQUELE projeto. Deixar o
    # `index.html` do jogo aberto depois de fechar o jogo é mostrar na
    # tela uma coisa que não está mais aqui.
    def fechar_projeto(self):
        antes = self.pasta
        if antes == self.pasta_inicial and not self.abas:
            return self.cartao("ela", texto=(
                "Nenhum projeto aberto — já estou na pasta de casa, "
                f"`{self.pasta}`."))
        self.pasta = self.pasta_inicial
        self.abas = []
        self.tela = self._tela_parada()
        return self.cartao("ela", texto=(
            f"Fechei **{antes.name}** e voltei para `{self.pasta}`. "
            f"As abas que eram dele foram junto."))

    def fechar(self, caminho):
        self.abas = [a for a in self.abas if a["caminho"] != caminho]
        try:
            self.guardar()      # não cria cartão, mas mudou o que se guarda
        except OSError:
            pass

    # ── gravar: a única escrita que não pede confirmação ─────────────
    #
    # E ESTÁ CERTO QUE NÃO PEÇA.
    #
    # O freio existe para o que o SISTEMA propõe: ele monta um comando e,
    # antes de rodar, alguém de fora precisa dizer sim. Quando você digita
    # no editor e aperta Ctrl+S, a confirmação JÁ FOI o Ctrl+S. Perguntar
    # de novo transforma o freio em pedágio — e freio que atrapalha todo
    # dia é freio que alguém desliga.
    #
    # O que a escrita precisa não é de porteiro, é de CAMINHO DE VOLTA,
    # que é o que a camada 5 da ARQUITETURA.md pede. Então: guarda o que
    # estava lá, grava, e devolve um cartão com botão de desfazer.
    #
    # E o desfazer vale enquanto esta conversa estiver aberta — o cartão
    # diz isso com todas as letras. Depois disso o caminho de volta é o
    # git. Prometer mais do que se cumpre é pior que não prometer.
    def _esta_aberto(self, alvo):
        """Só grava em arquivo que está ABERTO numa aba.

        O cerco anterior era geográfico — "dentro da pasta que reúne os
        projetos" — e tinha dois defeitos que só apareceram quando a pasta
        do projeto passou a poder mudar:

          movia junto    abrir `Projetos_Eduardo` como projeto faria a raiz
                         subir para a pasta pessoal inteira. O cerco crescia
                         justamente quando devia apertar.

          recusava certo procurar um arquivo num projeto vizinho, abrir,
                         corrigir e levar um "não gravo fora de..." é o
                         programa brigando com quem está usando ele.

        Aba aberta é um cerco melhor porque é sobre INTENÇÃO e não sobre
        geografia: não existe aba que você não tenha mandado abrir. Um
        caminho inventado, vindo torto pela rede ou por engano, não tem aba
        — e por isso não grava.
        """
        return any(a["caminho"] == str(alvo) for a in self.abas)

    def gravar(self, caminho, conteudo):
        alvo = Path(caminho)
        try:
            alvo = alvo.resolve()
        except OSError as erro:
            return self.cartao("ela", texto=f"Caminho inválido: {erro}")

        if not self._esta_aberto(alvo):
            return self.cartao("ela", texto=(
                f"Só gravo em arquivo que está aberto numa aba, e `{alvo.name}` "
                f"não está.\n\nAbra ele primeiro — `abrir {alvo}` — e eu gravo."))
        if not alvo.is_file():
            return self.cartao("ela", texto=f"`{alvo.name}` não é um arquivo.")

        try:
            antes = alvo.read_text(encoding="utf-8", errors="replace")
        except OSError as erro:
            return self.cartao("ela", texto=f"Não consegui reler antes de gravar: {erro}")

        # FIM DE LINHA: MANTÉM O QUE O ARQUIVO JÁ USAVA.
        # O editor manda sempre \n. Gravar isso no Windows com tradução
        # automática viraria \r\n em TODAS as linhas, e um arquivo que
        # era \n apareceria no git com cada linha modificada por causa de
        # uma vírgula que você trocou. `newline=""` desliga a tradução, e
        # a conversão explícita respeita o que já estava lá.
        fim = "\r\n" if "\r\n" in antes else "\n"
        texto = conteudo.replace("\r\n", "\n").replace("\n", fim)
        try:
            with open(alvo, "w", encoding="utf-8", newline="") as f:
                f.write(texto)
        except OSError as erro:
            self.virar("erro")
            return self.cartao("ela", texto=f"Não consegui gravar: {erro}")

        self._voltas[str(alvo)] = antes
        for a in self.abas:
            if a["caminho"] == str(alvo):
                a["conteudo"] = texto
                a["linhas"] = texto.count("\n") + 1
                a["bytes"] = len(texto.encode("utf-8"))

        antigas, novas = antes.splitlines(), texto.splitlines()
        mexidas = sum(1 for i in range(max(len(antigas), len(novas)))
                      if (antigas[i:i+1] or [None]) != (novas[i:i+1] or [None]))
        self.mostrar("arquivo", str(alvo))
        return self.cartao("gravou", caminho=str(alvo), nome=alvo.name,
                           linhas=len(novas), mexidas=mexidas,
                           bytes=len(texto.encode("utf-8")))

    def desfazer(self, caminho):
        antes = self._voltas.pop(caminho, None)
        if antes is None:
            return self.cartao("ela", texto=(
                "Não tenho mais o conteúdo anterior desse arquivo guardado — "
                "o desfazer vale enquanto a conversa está aberta. Se o projeto "
                "estiver no git, `git checkout` traz de volta."))
        alvo = Path(caminho)
        fim = "\r\n" if "\r\n" in antes else "\n"
        try:
            with open(alvo, "w", encoding="utf-8", newline="") as f:
                f.write(antes)
        except OSError as erro:
            return self.cartao("ela", texto=f"Não consegui desfazer: {erro}")
        for a in self.abas:
            if a["caminho"] == caminho:
                a["conteudo"] = antes
                a["linhas"] = antes.count("\n") + 1
                a["bytes"] = len(antes.encode("utf-8"))
        for c in self.cartoes:
            if c["tipo"] == "gravou" and c["caminho"] == caminho:
                c["desfeito"] = True
        self.mostrar("arquivo", caminho)
        return self.cartao("ela", texto=f"Desfeito. `{alvo.name}` voltou ao que era.")

    # ── procurar, e abrir no VS Code ─────────────────────────────────
    #
    # POR QUE A BUSCA VEM ANTES DO CAMINHO COMPLETO
    #
    # Ninguém lembra `C:\\Users\\Samsung\\Projetos_Eduardo\\LOJA AUTÔNOMA
    # PRO\\AutonomousStore\\...`. Lembra "o AdminApp". Exigir o caminho exato
    # transfere para a pessoa um trabalho que a máquina faz melhor.
    RAIZES_EXTRA = 1        # sobe uma pasta: acha os projetos irmãos

    def _raiz_da_busca(self):
        raiz = self.pasta
        for _ in range(self.RAIZES_EXTRA):
            if raiz.parent != raiz:
                raiz = raiz.parent
        return raiz

    # A VARREDURA PRECISA DE FREIO, E ISSO NÃO É DETALHE.
    #
    # `rglob("*")` numa pasta de projetos desce por node_modules, obj, bin,
    # .git e pacotes — dezenas de milhares de arquivos — e trava. Medido:
    # a busca por "AdminApp" não terminou em 170 segundos.
    #
    # Três freios, e os três são necessários:
    #   profundidade  um projeto raramente esconde o que interessa a 7 níveis
    #   orçamento     para de olhar depois de N entradas, ache ou não ache
    #   poda          não ENTRA nas pastas de lixo, em vez de entrar e ignorar
    FUNDO = 6
    ORCAMENTO = 25_000

    def _varrer(self, raiz, casa, so_pasta=False, limite=40):
        """Anda na árvore com freio. `casa(nome)` diz se serve."""
        achados, olhados = [], 0
        pilha = [(raiz, 0)]
        while pilha and olhados < self.ORCAMENTO and len(achados) < limite:
            pasta, nivel = pilha.pop()
            if nivel > self.FUNDO:
                continue
            try:
                with os.scandir(pasta) as entradas:
                    for e in entradas:
                        olhados += 1
                        if olhados >= self.ORCAMENTO:
                            break
                        try:
                            ehpasta = e.is_dir()
                        except OSError:
                            continue
                        if ehpasta and (e.name in IGNORA_BUSCA or e.name.startswith(".")):
                            continue
                        if casa(e.name) and (ehpasta or not so_pasta):
                            achados.append((Path(e.path), ehpasta))
                        if ehpasta:
                            pilha.append((e.path, nivel + 1))
            except (OSError, PermissionError):
                continue
        return achados, olhados

    def procurar(self, termo, limite=12, motivo=None):
        termo = self._limpar(termo).lower()
        if len(termo) < 2:
            return self.cartao("ela", texto="Me dê pelo menos duas letras para procurar.")

        raiz = self._raiz_da_busca()
        brutos, olhados = self._varrer(raiz, lambda n: termo in n.lower(),
                                       limite=limite * 3)
        achados = [p for p, _ in brutos]

        if not achados:
            return self.cartao("ela", texto=(
                f"Não achei nada com `{termo}` dentro de `{raiz}`.\n\n"
                f"Se estiver em outro lugar, me dê o caminho inteiro."))

        # Pasta antes de arquivo: quem procura "AdminApp" quer o projeto,
        # não o primeiro .cs que tem AdminApp no nome.
        ehpasta = dict(brutos)
        achados.sort(key=lambda p: (not ehpasta.get(p, False), len(str(p))))
        return self.cartao("achados", termo=termo, raiz=str(raiz), motivo=motivo,
                           itens=[{"caminho": str(p), "nome": p.name,
                                   "pasta": ehpasta.get(p, False),
                                   "onde": str(p.parent)} for p in achados[:limite]],
                           olhados=olhados)

    def no_vscode(self, caminho, programa="code"):
        caminho = self._limpar(caminho)
        alvo = Path(caminho)
        if not alvo.is_absolute():
            alvo = self.pasta / alvo

        if not alvo.exists():
            # Procura sozinho. E se houver UMA pasta só com esse nome, abre
            # direto — perguntar quando não há dúvida é fazer a pessoa
            # trabalhar de graça.
            raiz = self._raiz_da_busca()
            brutos, _ = self._varrer(raiz, lambda n: caminho.lower() in n.lower(),
                                     so_pasta=True, limite=5)
            pastas = [p for p, _ in brutos]
            if len(pastas) == 1:
                alvo = pastas[0]
            else:
                return self.procurar(caminho, motivo=(
                    f"não achei `{caminho}` como caminho" if not pastas
                    else f"achei {len(pastas)} pastas com esse nome — escolha"))
        try:
            subprocess.Popen([programa, str(alvo)], shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as erro:
            return self.cartao("ela", texto=(
                f"Não consegui chamar `{programa}`: {erro}\n\n"
                f"Confira se está no PATH — no VS Code, "
                f"F1 → *Shell Command: Install 'code' command in PATH*."))

        # Abre também aqui no painel, quando for arquivo: assim você vê o
        # conteúdo sem trocar de janela.
        if alvo.is_file():
            self.abrir(str(alvo))            # o abrir já aponta a tela
        else:
            # Mandar uma PASTA para o VS Code é dizer "vou trabalhar aqui".
            # Deixar o DevDesk olhando outra pasta faria as duas janelas
            # discordarem sobre qual é o projeto.
            self.trocar_pasta(alvo)
        return self.cartao("vscode", caminho=str(alvo), nome=alvo.name,
                           pasta=alvo.is_dir(), programa=programa)

    def ensinar(self, frase, intencao, palpite=""):
        """Você clicou na intenção certa. É aqui que a rede aprende."""
        if not self.cerebro:
            return None
        v = self.cerebro.ensinar(frase, intencao)
        # Correções vão SEMPRE para a pasta do DevDesk, não do projeto inspecionado.
        self.cerebro.guardar_correcao(frase, intencao, palpite, v["resultado"],
                                      str(self.CASA / "dados" / "correcoes.jsonl"))
        for c in self.cartoes:
            if c["tipo"] == "cerebro" and c.get("frase") == frase:
                c["ensinado"] = intencao
        return self.cartao("aprendeu", frase=frase, intencao=intencao, **v)

    def tarefas(self):
        """O que está esperando alguém: ações pendentes de confirmação."""
        return [{"id": c["id"], "comando": c["comando"], "porque": c["porque"]}
                for c in self.cartoes
                if c["tipo"] == "pendente" and not c.get("resolvido")]

    def limpar(self):
        """Mantido pelo nome antigo; hoje ele GUARDA antes de começar outra."""
        return self.nova()

    # ══════════════════════════════════════════════════════════════
    #  AS CONVERSAS, EM DISCO
    #
    #  Uma conversa por arquivo, em `dados/conversas/`. Não é banco: é
    #  JSON que se abre no bloco de notas, se copia e se apaga na mão.
    #  Para uma coisa que roda numa máquina só, banco seria peso sem
    #  troco.
    #
    #  E FICAM NA PASTA DO DEVDESK, NÃO NA PASTA INSPECIONADA. O
    #  assistente pode estar olhando a LOJA AUTÔNOMA hoje e o SO-Espacial
    #  amanhã; o histórico é dele, não do projeto que ele foi ver. Salvar
    #  dentro do projeto sujaria o repositório de outra pessoa com o meu
    #  histórico de conversa.
    # ══════════════════════════════════════════════════════════════
    CASA = Path(__file__).resolve().parent.parent      # a pasta do DevDesk
    LIMITE_NOME = 60

    @property
    def pasta_conversas(self):
        return self.CASA / "dados" / "conversas"

    def _vale_guardar(self):
        """Conversa sem nenhuma fala sua não vira arquivo.

        Sem isto, abrir e fechar o programa três vezes deixaria três
        arquivos vazios no histórico — e um histórico cheio de nada é o
        mesmo que histórico nenhum.
        """
        return any(c["tipo"] == "voce" for c in self.cartoes)

    def _nome_automatico(self):
        """O nome sai da primeira coisa que VOCÊ disse, não do que eu respondi."""
        for c in self.cartoes:
            if c["tipo"] == "voce":
                n = re.sub(r"\s+", " ", c["texto"]).strip()
                return (n[: self.LIMITE_NOME - 1] + "…") if len(n) > self.LIMITE_NOME else n
        return "Conversa nova"

    def guardar(self):
        if not self._vale_guardar():
            return None
        self.pasta_conversas.mkdir(parents=True, exist_ok=True)
        if not self.nome:
            self.nome = self._nome_automatico()
        dado = {"id": self.id, "nome": self.nome, "criada": self.criada,
                "mexida": time.time(), "pasta": str(self.pasta),
                "cartoes": self.cartoes, "abas": self.abas, "proximo": self._proximo,
                "pedido_projeto": self.pedido_projeto,
                "pedidos_parados": self.pedidos_parados}
        alvo = self.pasta_conversas / f"{self.id}.json"
        # Grava num temporário e RENOMEIA. Se faltar luz no meio da escrita,
        # o que se perde é o arquivo temporário — a conversa antiga continua
        # inteira, em vez de virar meio JSON que não abre.
        tmp = alvo.with_suffix(".json.escrevendo")
        tmp.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
        tmp.replace(alvo)
        return alvo

    def conversas(self):
        """A lista para a barra da esquerda, da mexida mais recente."""
        saida = []
        if not self.pasta_conversas.is_dir():
            return saida
        for f in self.pasta_conversas.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue        # arquivo estragado não derruba a lista
            saida.append({"id": d.get("id", f.stem), "nome": d.get("nome", f.stem),
                          "mexida": d.get("mexida", 0),
                          "falas": sum(1 for c in d.get("cartoes", []) if c["tipo"] == "voce"),
                          "aqui": d.get("id") == self.id})
        return sorted(saida, key=lambda x: x["mexida"], reverse=True)

    def nova(self):
        """Guarda a de agora e começa outra, do zero."""
        self.guardar()
        self.id = self._novo_id()
        self.nome = ""
        self.criada = time.time()
        self.cartoes, self.pendentes, self._proximo = [], {}, 1
        self.abas, self._voltas = [], {}
        self.tela = self._tela_parada()
        self.estado = "parado"
        self._alvo_pendente = None
        self.pedido_projeto = None       # conversa nova, pedido novo
        self.pedidos_parados = []
        self._primeiro_pedido = True     # a primeira pergunta ganha o prelúdio
        self.cartao("ela", texto=self.abertura())
        return self.id

    def carregar(self, ident):
        """Volta para uma conversa antiga, do jeito que ela estava."""
        alvo = self.pasta_conversas / f"{self._so_id(ident)}.json"
        if not alvo.is_file():
            return self.cartao("ela", texto="Essa conversa não existe mais.")
        try:
            d = json.loads(alvo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            return self.cartao("ela", texto=f"Não consegui abrir essa conversa: {erro}")

        self.guardar()                      # não perde a que estava aberta
        self.id = d["id"]
        self.nome = d.get("nome", "")
        self.criada = d.get("criada", time.time())
        self.cartoes = d.get("cartoes", [])
        self.abas = d.get("abas", [])
        self._proximo = d.get("proximo", len(self.cartoes) + 1)
        self.pedido_projeto = d.get("pedido_projeto")
        self.pedidos_parados = d.get("pedidos_parados", [])
        # A PASTA VOLTA JUNTO. Uma conversa sobre a LOJA AUTÔNOMA reaberta
        # com o projeto do DevDesk carregado seria meia volta: os cartões
        # falam de uma pasta e os comandos rodariam em outra.
        antiga = d.get("pasta")
        if antiga and Path(antiga).is_dir():
            self.pasta = Path(antiga)

        # AS PENDÊNCIAS SÃO REMONTADAS DOS CARTÕES, e não guardadas à parte.
        # Duas listas dizendo a mesma coisa saem de sincronia no dia em que
        # alguém mexer numa e esquecer da outra; o cartão é a verdade.
        # Duas formas de pendência, e as duas remontam do cartão: o comando
        # de shell guarda `comando`, a criação de projeto guarda `plano`.
        # O plano vai INTEIRO no cartão — com o conteúdo dos arquivos — e
        # isso engorda a conversa salva em alguns KB. É o preço de poder
        # fechar o programa, abrir amanhã e o "criar" ainda valer. Guardar
        # só um resumo faria o botão existir e não funcionar.
        self.pendentes = {}
        for c in self.cartoes:
            if c.get("resolvido"):
                continue
            if c["tipo"] == "pendente":
                self.pendentes[c["id"]] = c["comando"]
            elif c["tipo"] == "projeto" and c.get("plano"):
                self.pendentes[c["id"]] = {"acao": "criar_projeto",
                                           "plano": c["plano"]}
        # O desfazer NÃO atravessa: ele guarda o texto anterior na memória
        # desta execução. Reabrir amanhã e "desfazer" um salvamento de hoje
        # seria prometer o que não temos. Daqui para trás o caminho é o git.
        self._voltas = {}
        self.tela = self._tela_parada()
        self._alvo_pendente = None
        self._assentar()
        return self.id

    def apagar(self, ident):
        alvo = self.pasta_conversas / f"{self._so_id(ident)}.json"
        era_a_aberta = self._so_id(ident) == self.id
        try:
            alvo.unlink(missing_ok=True)
        except OSError as erro:
            return self.cartao("ela", texto=f"Não consegui apagar: {erro}")
        if era_a_aberta:
            # Apagar a conversa em que você está não pode deixar a tela num
            # limbo com cartões que não existem mais em lugar nenhum.
            self.id = self._novo_id()
            self.nome = ""
            self.criada = time.time()
            self.cartoes, self.pendentes, self._proximo = [], {}, 1
            self.abas, self._voltas = [], {}
            self.tela = self._tela_parada()
            self.estado = "parado"
            self.cartao("ela", texto="Conversa apagada. Esta aqui é nova.")
        return True

    def renomear(self, ident, nome):
        nome = re.sub(r"\s+", " ", (nome or "")).strip()[: self.LIMITE_NOME]
        if not nome:
            return False
        ident = self._so_id(ident)
        if ident == self.id:
            self.nome = nome
            self.guardar()
            return True
        alvo = self.pasta_conversas / f"{ident}.json"
        if not alvo.is_file():
            return False
        try:
            d = json.loads(alvo.read_text(encoding="utf-8"))
            d["nome"] = nome
            alvo.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        except (OSError, ValueError):
            return False
        return True

    @staticmethod
    def _so_id(ident):
        """O id vira nome de arquivo, então nada de `..` nem de barra.

        Um id que chega da tela é entrada de fora como qualquer outra:
        `../../../algo` como id apagaria um arquivo em outro lugar.
        """
        return re.sub(r"[^0-9A-Za-z\-_]", "", str(ident or ""))[:40]

    @staticmethod
    def _novo_id():
        return datetime.now().strftime("%Y%m%d-%H%M%S-") + str(int(time.time() * 1000) % 1000)

    # ── a saudação ───────────────────────────────────────────────────
    #
    # As faixas de hora ficam em UM lugar só. Dois métodos precisam delas
    # e, escritas duas vezes, um dia alguém ajusta uma e esquece a outra —
    # e o programa passa a dar bom dia às onze num lugar e às onze e meia
    # no outro.
    @staticmethod
    def _hora_do_dia():
        h = datetime.now().hour
        if 5 <= h < 12:  return "Bom dia"
        if 12 <= h < 18: return "Boa tarde"
        if 18 <= h < 24: return "Boa noite"
        return None      # madrugada não é "boa" coisa nenhuma

    def saudacao_da_hora(self):
        s = self._hora_do_dia()
        return s if s else "Ainda de pé"

    def seu_nome(self):
        """O primeiro nome da pessoa — ou "desenvolvedor", se não achamos."""
        return quem_e_voce(self.CASA)

    def abertura(self):
        """A primeira linha da tela. Curta de propósito.

        Ela não conta o que o programa faz nem lista comandos: quem abre
        um programa quer começar, não ler um manual. O que ele sabe fazer
        aparece quando for perguntado, e a caixa de texto logo abaixo já
        diz que existe o `/`.

        Saudação não é cartaz: usa o nome, a hora, e devolve a palavra
        para a pessoa — quem abre a tela é quem tem o que contar.
        """
        nome = quem_e_voce(self.CASA)
        s = self._hora_do_dia()
        # a meia-noite não tem boa-noite decente; o jeito é zoeira mansa
        if s is None:
            return f"Ainda de pé a essa hora, {nome}? Pode falar — o que você precisa?"
        return f"{s}, {nome}! Estou por aqui. Me diz o que você precisa."

    # ── cartões ──────────────────────────────────────────────────────
    def cartao(self, tipo, **campos):
        c = {"id": self._proximo, "tipo": tipo, "em": time.time(), **campos}
        self._proximo += 1
        self.cartoes.append(c)
        # GRAVA AQUI, E NÃO EM DEZ LUGARES. Todo mexer na conversa cria um
        # cartão, então este é o único ponto por onde tudo passa. Espalhar
        # `guardar()` por receber/confirmar/recusar/gravar/ensinar daria o
        # mesmo resultado até o dia em que alguém acrescentasse o décimo
        # primeiro caminho e esquecesse.
        try:
            self.guardar()
        except OSError:
            pass    # disco cheio ou pasta sem permissão não derruba a conversa
        return c

    # ── a decisão de o que fazer com uma frase ───────────────────────
    SIM = {"sim", "s", "pode", "manda", "vai", "ok", "beleza", "isso",
           "claro", "confirmo", "confirma", "certo", "aceito", "positivo",
           "yes", "y", "bora", "faz", "pode ser", "pode sim", "sim pode",
           "isso mesmo", "ta certo", "esta certo", "eh isso", "e isso"}
    NAO = {"nao", "n", "cancela", "cancelar", "para", "pare", "deixa",
           "espera", "melhor nao", "agora nao", "no", "negativo",
           "nao quero", "deixa pra la", "esquece", "nem"}

    def _sim_ou_nao(self, frase):
        """True, False, ou None se a frase não é uma resposta de sim/não.

        Sem acento e sem pontuação porque "não", "nao" e "não!" são a
        mesma resposta. Até quatro palavras: passou disso, a pessoa está
        dizendo outra coisa e quem decide é a rede.
        """
        t = unicodedata.normalize("NFD", (frase or "").strip().lower())
        t = "".join(c for c in t if unicodedata.category(c) != "Mn")
        t = " ".join(re.sub(r"[^a-z0-9\s]", " ", t).split())
        if not t or len(t.split()) > 4:
            return None
        if t in self.SIM:
            return True
        if t in self.NAO:
            return False
        # "sim, pode criar" / "nao, deixa" — a primeira palavra decide
        primeira = t.split()[0]
        if primeira in self.SIM:
            return True
        if primeira in self.NAO:
            return False
        return None

    def _quer_rever_o_entendido(self, frase):
        """"ocê entendeu alguma coisa errada?" é CONFERÊNCIA, não resposta.

        Quando há um pedido de projeto aberto, "o que você entendeu do meu
        pedido?" / "me mostra o que você entendeu" quer ver o resumo do que
        foi capturado — não uma ação. Detectar por palavras, como os
        comandos diretos (`abrir`, `procurar`): a rede de intenção não é
        treinada para "conferir o pedido", e mandar a pergunta para ela é
        pedir que ela adivinhe.
        """
        baixa = (frase or "").lower().strip("?.!, ")
        return (
            ("entendeu" in baixa or "entende" in baixa
             or "compreendeu" in baixa or "viu o pedido" in baixa)
            and ("oq" in baixa or "o que" in baixa or "qu " in baixa
                 or "como" in baixa or "vc" in baixa or "você" in baixa
                 or "mostra" in baixa or "resumo" in baixa
                 or "entendeu" in baixa and len(baixa.split()) <= 8)
        )

    def _tem_projeto_pendente(self):
        """Há uma proposta de criação na tela esperando o sim?"""
        for pend in self.pendentes.values():
            if isinstance(pend, dict) and pend.get("acao") == "criar_projeto":
                return True
        return False

    def _revisar_pedido(self):
        """Mostra o que foi entendido do pedido — o aberto ou o proposto."""
        p = dict(self.pedido_projeto or {})
        plano = None
        for pend in self.pendentes.values():
            if isinstance(pend, dict) and pend.get("acao") == "criar_projeto":
                plano = pend.get("plano") or {}
                break
        if plano:
            # a proposta já foi montada: o plano tem tudo
            p.setdefault("linguagem", plano.get("linguagem"))
            p.setdefault("tipo", plano.get("tipo") or plano.get("tipo_projeto"))
            p.setdefault("nome", plano.get("nome"))
            p.setdefault("fazer", plano.get("fazer"))
        linhas = []
        mapa = (("linguagem", "linguagem"), ("tipo", "tipo"),
                ("nome", "nome"), ("fazer", "finalidade/propósito"))
        for chave, rotulo in mapa:
            valor = p.get(chave)
            if valor:
                linhas.append(f"- **{valor}** ({rotulo})")
        texto = "Do seu pedido, entendi até aqui:\n\n"
        if linhas:
            texto += "\n".join(linhas)
        else:
            texto += "_(ainda não tenho campos — me diz a linguagem, o tipo, o nome e a finalidade.)_"
        if p.get("fazer"):
            texto += f"\n\nEle servirá para isto: _{p['fazer']}_."
        if plano:
            texto += "\n\nEstá certo? Se sim, me confirma que eu crio — se não, me diz o que mudar."
        else:
            faltando = [c for c in ("linguagem", "tipo", "nome") if not p.get(c)]
            if faltando:
                texto += ("\n\nAinda não tenho: " + ", ".join(faltando) + f".\n"
                          "Se algum campo estiver errado, me diz o certo — "
                          "ou responde o que falta.")
            else:
                texto += "\n\nEstá certo? Se sim, me confirma que eu monto a proposta."
        return texto

    def _continua_o_projeto(self, frase, pensou=None):
        """A frase responde à pergunta do projeto, ou mudou de assunto?

        Curta é resposta: "console", "python", "estoque". Frase inteira com
        a rede CONFIANTE em outra intenção é assunto novo — e aí o pedido
        pela metade é largado, porque ficar preso num pedido antigo é pior
        do que ter perguntado duas vezes.
        """
        if len((frase or "").split()) <= 3:
            return True
        # SINAL DE RESPOSTA AO PROJETO. Uma resposta completa ("csharp,
        # console, agenda, para guardar minhas tarefas") também pode passar
        # de três palavras, e a rede às vezes a classifica NÃO como
        # `criar_projeto` — o que até aqui largava o pedido pela metade
        # exatamente quando a pessoa tinha acabado de responder tudo. Se o
        # que está na frase parece campo do projeto, é campo do projeto:
        # linguagem, tipo, ou um "para …" (finalidade) — sem pedir a opinião
        # da rede sobre algo que eu mesmo estava perguntando.
        curtos = (frase or "").lower()
        linguagens = {"csharp", "html", "javascript", "php", "python"}
        tipos = {"console", "api", "biblioteca", "site", "web"}
        parece_resposta = (
            linguagens & set(curtos.replace(",,", ",").replace(",", " ").split())
            or tipos & set(curtos.replace(",,", ",").replace(",", " ").split())
            or " para " in curtos or " pra " in curtos
            or " que " in curtos and "calcula" in curtos)
        if parece_resposta:
            return True
        cand = [x["nome"] for x in ((pensou or {}).get("candidatos") or [])]
        # NÃO uso `confiavel` aqui, e o motivo é medido: com o limiar em
        # 92% quase nada é "confiável", então a saída nunca disparava e ele
        # ficava preso no pedido antigo — "me mostra o que tem nessa pasta"
        # virava o nome do projeto. O que vale é a POSIÇÃO: se
        # `criar_projeto` nem está entre os três primeiros, esta frase é
        # sobre outra coisa.
        if cand and "criar_projeto" not in cand[:3]:
            self.parar_pedido_projeto()
            return False
        return True

    # ── PARAR NÃO É APAGAR ───────────────────────────────────────────
    #
    # A primeira versão fazia `self.pedido_projeto = None` e pronto: o que
    # já tinha sido entendido evaporava. Aqui ele vai para a garagem, e a
    # garagem serve a duas coisas ao mesmo tempo:
    #
    #   · VOLTAR. Basta falar de projeto de novo — com o mesmo nome, ou
    #     sem nome nenhum — que ele retoma de onde parou.
    #   · APRENDER. Cada linha do `dados/pedidos.jsonl` é uma frase real,
    #     dita por uma pessoa de verdade, com os campos que saíram dela.
    #     Isso é corpus melhor que qualquer molde que eu escreva.
    def parar_pedido_projeto(self, motivo="mudou de assunto"):
        p = self.pedido_projeto
        self.pedido_projeto = None
        if not p or not any(p.get(k) for k in ("linguagem", "tipo", "nome")):
            return None
        p = dict(p)
        p["parado_em"] = time.time()
        p["motivo"] = motivo
        # o mesmo nome não entra duas vezes na garagem
        self.pedidos_parados = [q for q in self.pedidos_parados
                                if (q.get("nome") or "") != (p.get("nome") or "")]
        self.pedidos_parados.append(p)
        self.pedidos_parados = self.pedidos_parados[-5:]   # cinco bastam
        self._anotar_pedido(p)
        falta = [k for k in ("linguagem", "tipo", "nome") if not p.get(k)]
        como = p.get("nome") or p.get("linguagem") or "aquele"
        self.cartao("ela", texto=(
            f"_(guardei o pedido do projeto **{como}** pela metade — "
            f"falta {', '.join(falta) if falta else 'só confirmar'}. "
            f"É só falar dele de novo que eu continuo de onde parei.)_"))
        return p

    def _anotar_pedido(self, p):
        """Grava o pedido parado em `dados/pedidos.jsonl`, para virar treino.

        Uma linha por pedido, no mesmo formato solto do `correcoes.jsonl`:
        acrescenta no fim, nunca reescreve, e falhar aqui não pode derrubar
        a conversa — é registro, não é o trabalho.
        """
        try:
            alvo = self.CASA / "dados" / "pedidos.jsonl"
            alvo.parent.mkdir(parents=True, exist_ok=True)
            linha = {"quando": time.strftime("%Y-%m-%dT%H:%M:%S"),
                     "conversa": self.id,
                     "frase": p.get("frase", ""),
                     "linguagem": p.get("linguagem"), "tipo": p.get("tipo"),
                     "nome": p.get("nome"), "motivo": p.get("motivo", "")}
            with open(alvo, "a", encoding="utf-8") as f:
                f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def retomar_pedido(self, nome=None):
        """Tira da garagem o pedido que combina, e o devolve.

        Com nome: o que tem aquele nome. Sem nome: o último parado — que é
        o que "volta pro projeto" quer dizer quando só há um assunto em
        aberto.
        """
        if not self.pedidos_parados:
            return None
        if nome:
            baixo = nome.strip().lower()
            for i, q in enumerate(self.pedidos_parados):
                if (q.get("nome") or "").strip().lower() == baixo:
                    return self.pedidos_parados.pop(i)
            return None
        return self.pedidos_parados.pop()

    def _volta_a_um_pedido(self, frase, pensou=None):
        """Esta frase volta a um pedido guardado na garagem?

        Duas provas, as duas conservadoras — ter algo na garagem NÃO basta,
        senão qualquer frase solta viraria continuação de um projeto de
        meia hora atrás:

          · a frase CITA o nome de um pedido parado; ou
          · `criar_projeto` está entre os três primeiros palpites da rede.
        """
        baixa = (frase or "").lower()
        for q in self.pedidos_parados:
            nome = (q.get("nome") or "").strip().lower()
            if nome and nome in baixa:
                return True
        cand = [x["nome"] for x in ((pensou or {}).get("candidatos") or [])]
        return bool(cand) and "criar_projeto" in cand[:3]

    def receber(self, frase):
        self.virar("pensando")
        try:
            return self._receber(frase)
        except Exception:
            self.virar("erro")
            raise
        finally:
            self._assentar()

    def _receber(self, frase):
        self.ultima_mensagem = frase  # armazena para as funções de resposta
        self.cartao("voce", texto=frase)

        pensou = None
        if self.cerebro:
            pensou = self.cerebro.pensar(frase)
            self.cartao("cerebro", frase=frase, **pensou)

        # ── EU PERGUNTEI SIM OU NÃO; UMA PALAVRA É A RESPOSTA ────────
        #
        # Isto entra ANTES do classificador pelo mesmo motivo que a
        # resposta curta do projeto entra: quem tem o contexto sou eu, que
        # acabei de perguntar "Confirma que eu crio isso em ...?".
        #
        # Medido, com a rede: "sim" dá 98,7% e passa; "não" dá 38,4%,
        # "cancela" 63,6% — abaixo do limiar de 92%. Ou seja: o programa
        # perguntava, a pessoa recusava, e ele respondia "não tenho
        # certeza" deixando a criação pendurada. O sim funcionava e o não
        # não, que é o pior dos dois mundos.
        #
        # A CONDIÇÃO É `pendentes`, E NÃO O ESTADO — porque o estado já
        # mudou quando esta linha roda: `receber()` faz `virar("pensando")`
        # antes de chamar `_receber`. Conferir `aguardando_confirmacao`
        # aqui era conferir uma coisa que nunca ia ser verdade, e o ramo
        # inteiro nunca disparava.
        #
        # `pendentes` cheio já é a condição certa por si: só tem coisa lá
        # dentro porque eu perguntei e estou esperando.
        if self.pendentes and self._sim_ou_nao(frase) is not None:
            ident = max(self.pendentes)
            if self._sim_ou_nao(frase):
                self.confirmar(ident)
            else:
                self.recusar(ident)
            return

        # Uma frase que começa com > é comando direto — é como o técnico
        # pede uma investigação sem depender de a rede entender a intenção.
        if frase.startswith(">"):
            self.rodar(frase[1:].strip())
        elif self._pede_editor(frase):
            alvo, programa = self._pede_editor(frase)
            self.no_vscode(alvo, programa)
        elif self._e_caminho(frase):
            self.abrir_projeto_caminho(frase)
        elif self._parece_nome_de_alvo(frase):
            # A pergunta anterior foi "me diz a pasta" — este nome é a resposta.
            self.abrir_projeto_caminho(frase)
        elif frase.lower().startswith(("procurar ", "procura ", "achar ", "cade ", "cadê ")):
            self.procurar(frase.split(" ", 1)[1])
        elif frase.lower().startswith(("abrir ", "abre ", "ver ")):
            self.abrir(frase.split(" ", 1)[1])
        elif self.pedido_projeto and self.pedido_projeto.get("aguardando_fazer"):
            # EU perguntei "o que ele deve fazer?" — esta frase é a
            # resposta, e ela não passa pelo classificador: o assunto é
            # meu, eu é que acabei de perguntar.
            self.cartao("ela", texto=respostas.criar_projeto(self, frase))
        elif (self.pedido_projeto or self._tem_projeto_pendente()) \
            and self._quer_rever_o_entendido(frase):
            # "O QUE VOCÊ ENTENDEU DO MEU PEDIDO?" Medido na conversa real:
            # a pessoa pergunta isto depois de um pedido (ou da proposta na
            # tela) e a rede chuta `ver_logs`/`git_diferenca` — nada a ver.
            # O que ela quer é CONFERIR: mostra o que foi entendido até
            # agora, campo por campo, para ela ver onde eu errei. Não é o
            # classificador que responde — é o pedido que está aberto na
            # conversa.
            self.cartao("ela", texto=self._revisar_pedido())
        elif self.pedido_projeto and self._continua_o_projeto(frase, pensou):
            # UMA CONVERSA COMEÇADA CONTINUA.
            #
            # Falta um campo do projeto e você acabou de responder. Mandar
            # essa resposta para o classificador seria recomeçar do zero —
            # e medido: "console" sozinho cai em `nao_abre` com 56%, porque
            # o classificador foi treinado em FRASES e uma palavra solta
            # não tem contexto nenhum. Quem tem o contexto sou eu, que fiz
            # a pergunta.
            self.cartao("ela", texto=respostas.criar_projeto(self, frase))
        elif self.pedidos_parados and self._volta_a_um_pedido(frase, pensou):
            # VOLTAR AO QUE FICOU PELA METADE. Sem esta linha a garagem
            # existia e ninguém conseguia chegar nela: "volta pro projeto
            # agenda" dá 83% na rede, abaixo do limiar de 92%, e caía no
            # "não tenho certeza". O nome do projeto na frase é prova
            # melhor do que qualquer probabilidade.
            self.cartao("ela", texto=respostas.criar_projeto(self, frase))
        elif frase.lower().startswith(("criar projeto", "cria projeto",
                                       "novo projeto", "create project")):
            # O CAMINHO DIRETO, do mesmo jeito que `> comando` e `abrir x`
            # já eram. Não é a rede entendendo — é você mandando com todas
            # as letras, e serve para duas horas: quando a rede de intenção
            # ainda não foi treinada com `criar_projeto`, e quando ela ficou
            # em dúvida e você não quer discutir.
            self.cartao("ela", texto=respostas.criar_projeto(self, frase))
        else:
            texto = self._resposta(frase)
            if texto:
                self.cartao("ela", texto=texto)
        return self.cartoes[-1]

    def _resposta(self, frase):
        if not self.cerebro:
            return "Cérebro não carregado."
        p = self.cerebro.pensar(frase)
        if not p["candidatos"]:
            self.virar("aguardando_voce")   # tambem e nao saber
            return ("Não reconheci nenhuma peça dessa frase — ela está fora do que a "
                    "rede viu no treino. Escreva de outro jeito, ou mande `ajuda`.")

        v = p["candidatos"][0]

        # ACIMA DO LIMIAR: age. Abaixo: oferece e não chuta.
        if p["confiavel"]:
            feito = respostas.responder(self, v["nome"], frase)
            if feito and feito[0]:
                if (self._primeiro_pedido
                        and v["nome"] not in _CONVERSA_PURA):
                    # A PRIMEIRA RESPOSTA DA PRIMEIRA PERGUNTA. Um passo
                    # antes da resposta técnica faz a conversa parecer
                    # conversa — mas só uma vez, e nunca diante de uma
                    # saudação ou de um pedido de criação (que já tem a
                    # mensagem dele).
                    self._primeiro_pedido = False
                    return respostas.preludio(self) + "\n\n" + feito[0]
                return feito[0]
            return (f"Entendi como **{v['nome']}**, mas essa intenção ainda não tem ação "
                    f"ligada. O que já funciona: `ajuda`, perguntas sobre a máquina, "
                    f"`abrir <caminho>` e `> comando`.")

        self.virar("aguardando_voce")     # nao sei: a bola esta com voce
        opcoes = "\n".join(f"· **{c['nome']}** ({c['probabilidade']:.0%})"
                           for c in p["candidatos"])
        return (f"Ainda não tenho certeza do que te entender — meu melhor "
                f"palpite deu {v['probabilidade']:.1%} e eu só falo com "
                f"segurança acima de {p['limiar']:.0%}.\n\n"
                f"Me ajuda a te entender: era algo deste tipo?\n{opcoes}\n\n"
                f"Se nenhum encaixar, me explica de outro jeito o que você "
                f"quer — eu sou bom em aprender com a sua resposta.")

    # ── execução ─────────────────────────────────────────────────────
    def so_le(self, comando):
        partes = comando.strip().split()
        if not partes:
            return False
        base = partes[0].lower().lstrip("./")
        if base not in SO_LEITURA:
            return False
        if base == "git":
            return len(partes) > 1 and partes[1] in LEITURA_DE_GIT
        # Redirecionamento escreve, mesmo com comando de leitura.
        return not any(s in comando for s in (">", ">>", "|", "&&", ";", "rm ", "del "))

    def rodar(self, comando):
        if not self.so_le(comando):
            c = self.cartao("pendente", comando=comando, risco="precisa de confirmação",
                            porque="não está na lista de comandos que só leem")
            self.pendentes[c["id"]] = comando
            return c
        return self._executar(comando)

    def _executar(self, comando, confirmado=False):
        # Fica ligado durante a espera de verdade. O comando pode levar ate
        # 30 segundos, e nesses 30 segundos a tela precisa dizer o que esta
        # acontecendo em vez de parecer travada.
        self.virar("investigando")
        inicio = time.time()
        try:
            r = subprocess.run(comando, shell=True, cwd=self.pasta, capture_output=True,
                               text=True, timeout=30, errors="replace")
            saida = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
            codigo = r.returncode
        except subprocess.TimeoutExpired:
            saida, codigo = "(passou de 30 segundos e foi interrompido)", -1
        except Exception as erro:
            saida, codigo = f"({erro})", -1

        self.mostrar("terminal")
        return self.cartao("comando", comando=comando, saida=saida.rstrip()[:8000],
                           codigo=codigo, confirmado=confirmado,
                           segundos=round(time.time() - inicio, 2))

    # ── criar projeto ────────────────────────────────────────────────
    def ultimo_codigo_colado(self, minimo=40):
        """O último trecho de código que você colou, se colou algum.

        SERVE PARA O DETECTOR: quando a frase não diz a linguagem mas veio
        um exemplo junto, é o exemplo que responde. Procura de trás para
        frente porque o que vale é o mais recente.
        """
        for c in reversed(self.cartoes):
            if c.get("tipo") != "voce":
                continue
            texto = c.get("texto", "")
            if "```" in texto:
                partes = texto.split("```")
                if len(partes) >= 3:
                    corpo = partes[1]
                    # tira a marca de linguagem da primeira linha, se houver
                    if "\n" in corpo:
                        primeira, resto = corpo.split("\n", 1)
                        if len(primeira.split()) <= 1:
                            corpo = resto
                    if len(corpo.strip()) >= minimo:
                        return corpo
            elif texto.count("\n") >= 2 and len(texto) >= minimo * 3:
                return texto
        return None

    def propor_projeto(self, plano, arvore):
        """Mostra a árvore e PENDURA a criação, esperando o seu sim.

        A criação entra em `self.pendentes` igual a um comando que escreve
        no disco entra — e é o mesmo motivo: as duas coisas mexem na sua
        máquina. Reaproveitar a mesma trava é melhor do que inventar uma
        segunda que amanhã esquece de travar.
        """
        if "erro" in plano:
            self.virar("aguardando_voce")
            return f"Não consegui planejar: {plano.get('erro')}"
        # `tipo_projeto` e não `tipo`: `cartao(self, tipo, **campos)` já usa
        # `tipo` para dizer que ESPÉCIE de cartão é. Passar o tipo do projeto
        # com o mesmo nome bate de frente — o Python reclamou na hora e foi
        # bom que reclamou, senão o cartão sairia com a espécie errada.
        c = self.cartao("projeto", nome=plano["nome"],
                        linguagem=plano["linguagem"],
                        tipo_projeto=plano["tipo"],
                        arvore=arvore, arquivos=len(plano["arquivos"]),
                        perguntas=plano["perguntas"], plano=plano,
                        risco="vai criar pastas e arquivos",
                        porque="escrever na sua máquina precisa do seu sim")
        self.pendentes[c["id"]] = {"acao": "criar_projeto", "plano": plano}
        self.virar("aguardando_confirmacao")
        melhor = {
            "console": "programa de linha de comando",
            "api": "serviço (API/host)",
            "biblioteca": "biblioteca de código",
            "site": "página/site",
        }.get(plano["tipo"], plano["tipo"])
        partes = [f"Entendi: um **{melhor}** em **{plano['linguagem']}** "
                  f"chamado **{plano['nome']}**.\n",
                  "```", arvore, "```"]
        if plano.get("fazer"):
            partes[0] += (f"Ele vai servir para isto: "
                          f"_{plano['fazer'].strip()}_.\n")
        if plano["perguntas"]:
            partes.append("\nAntes de escrever, o que eu não tenho certeza:\n"
                          + "\n".join(f"- {q}" for q in plano["perguntas"]))
        partes.append(f"\nConfirma que eu crio isso em `{self.pasta}`? "
                      f"(só `sim` basta)")
        return "\n".join(partes)

    def _criar_projeto(self, plano):
        from painel.criar import Criador

        self.virar("investigando")
        feito = Criador().escrever(plano, self.pasta)
        self.mostrar("projeto")
        c = self.cartao("projeto_criado", raiz=feito["raiz"],
                        criados=feito["criados"], pulados=feito["pulados"])
        dica = _proximo_passo(plano)
        if dica:
            self.cartao("ela", texto=dica)
        return c

    def confirmar(self, ident):
        pendente = self.pendentes.pop(int(ident), None)
        if pendente is None:
            return None
        for c in self.cartoes:
            if c["id"] == int(ident):
                c["resolvido"] = "confirmado"
        try:
            # O pendente é um COMANDO (texto) ou uma AÇÃO (dicionário). Um
            # `isinstance` aqui é feio, e a alternativa era pôr toda criação
            # de projeto atrás de uma linha de shell — o que seria pior:
            # some a árvore que você acabou de conferir.
            if isinstance(pendente, dict):
                if pendente.get("acao") == "criar_projeto":
                    return self._criar_projeto(pendente["plano"])
                return None
            return self._executar(pendente, confirmado=True)
        finally:
            self._assentar()

    def recusar(self, ident):
        self.pendentes.pop(int(ident), None)
        for c in self.cartoes:
            if c["id"] == int(ident):
                c["resolvido"] = "recusado"
        # O cartao guarda "recusado" para sempre; a SESSAO volta a esperar.
        # Confundir os dois deixaria o sistema preso no "nao" de ontem.
        self._assentar()
        return self.cartao("ela", texto="Não fiz nada.")

    # ── a pasta ──────────────────────────────────────────────────────
    def arvore(self, sub="", limite=600):
        """UM nível da pasta — o resto vem quando você abre a pasta.

        Antes isto descia a árvore inteira até seis níveis e parava em 300
        itens. Duas coisas erradas nisso: gastava tempo lendo pasta que
        ninguém ia olhar, e o limite cortava no meio, escondendo arquivo
        sem avisar.

        Um nível por vez não tem limite que importe, não tem profundidade
        para escolher, e é sempre rápido — porque é exatamente o que a
        tela está mostrando.
        """
        alvo = (self.pasta / sub).resolve() if sub else self.pasta
        # `sub` vem da tela: `../../..` sairia da pasta do projeto.
        if alvo != self.pasta and self.pasta not in alvo.parents:
            return []
        if not alvo.is_dir():
            return []

        def eh_pasta(x):
            try:
                return x.is_dir()
            except OSError:
                return False

        try:
            with os.scandir(alvo) as e:
                filhos = [x for x in e if not (x.name in IGNORA_BUSCA
                                               or x.name.startswith("."))]
        except (OSError, PermissionError):
            return []

        filhos.sort(key=lambda x: (not eh_pasta(x), x.name.lower()))
        saida = []
        for x in filhos[:limite]:
            p = eh_pasta(x)
            try:
                tam = 0 if p else x.stat().st_size
            except OSError:
                tam = 0
            rel = f"{sub}/{x.name}" if sub else x.name
            saida.append({"caminho": rel, "nome": x.name, "pasta": p, "bytes": tam})
        return saida
