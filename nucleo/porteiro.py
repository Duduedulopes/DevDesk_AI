# -*- coding: utf-8 -*-
"""O PORTEIRO — quem entra, e como se prova que é você.

O QUE ELE FAZ HOJE, E O QUE ELE AINDA NÃO FAZ

    faz          confere a senha. Guarda um HASH, nunca a senha.
    não faz      criptografar as conversas.

Essa segunda linha é a mais importante deste arquivo, e por isso está no
alto. Uma senha que só confere é uma MAÇANETA: ela segura quem senta no
seu computador de passagem, e não segura quem sabe abrir uma pasta — os
JSON das conversas estão ali do lado, em texto puro.

A CAIXA DE AVISO SAIU DA TELA a pedido, e o fato NÃO saiu com ela. Por
isso ele está aqui em cima, na primeira coisa que se lê ao abrir este
arquivo, e continua saindo na resposta de `cartao()`. Enquanto estas
linhas existirem, as conversas estão em texto puro no disco. Elas saem no
dia em que a criptografia entrar — e aí saem porque viraram mentira, que
é o único motivo bom para apagar um aviso.

POR QUE scrypt, E POR QUE ELE É LENTO DE PROPÓSITO

Guardar a senha é o erro mais antigo do mundo. Guardar um SHA-256 dela é
o segundo: uma placa de vídeo boa faz 10 bilhões de SHA-256 por segundo, e
uma senha comum cai em minutos.

`scrypt` é feito para ser caro em TEMPO e em MEMÓRIA. Medido nesta
máquina, com N=2^15 (32 MB por tentativa):

    hash rápido      ~10.000.000.000 tentativas por segundo
    scrypt N=2^15                 ~10 tentativas por segundo

Um bilhão de vezes mais difícil, e você paga 101 milissegundos uma vez,
ao entrar. A lentidão é o produto.

O SAL É ALEATÓRIO E FICA GUARDADO JUNTO

Sal não é segredo — ele é lixo público misturado antes do hash, e serve
para uma coisa só: fazer com que duas pessoas com a MESMA senha tenham
hashes diferentes. Sem ele, quem rouba o arquivo compara com uma tabela
pronta e acabou. Guardar o sal ao lado do hash é o certo, e não um
descuido.

A COMPARAÇÃO É EM TEMPO CONSTANTE

`hmac.compare_digest` em vez de `==`. O `==` do Python para de comparar no
primeiro byte diferente, e o tempo que ele leva conta quantos bytes
acertaram. Medindo isso muitas vezes dá para descobrir o hash byte a
byte. Aqui é ataque de laboratório e o nosso caso é local — mas é uma
linha, e não usar a linha certa por preguiça é como aprende-se errado.
"""
import base64
import hmac
import json
import os
import time
from pathlib import Path

CUSTO_N = 2 ** 15      # 32 MB por tentativa · 101 ms medidos
CUSTO_R = 8
CUSTO_P = 1
TAMANHO_SAL = 16
TAMANHO_CHAVE = 32
MINIMO_DA_SENHA = 8


class Porteiro:
    """Lê e escreve `dados/perfil.json`. Não guarda senha em lugar nenhum."""

    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.dado = {}
        self.carregar()

    # ── disco ────────────────────────────────────────────────────────
    def carregar(self):
        try:
            self.dado = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.dado = {}
        return self.dado

    def _gravar(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        # Grava num temporário e RENOMEIA, como o resto do projeto já faz:
        # faltar luz no meio da escrita não pode deixar o perfil pela
        # metade, senão você fica trancado para fora da sua própria casa.
        tmp = self.caminho.with_suffix(".json.escrevendo")
        tmp.write_text(json.dumps(self.dado, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self.caminho)

    # ── o que a tela precisa saber ANTES de você digitar ──────────────
    def cartao(self):
        """O que a tela de entrada mostra. Nunca inclui hash nem sal."""
        return {
            "existe": bool(self.dado.get("hash")),
            "nome": self.dado.get("nome", ""),
            "foto": self.dado.get("foto", ""),
            "ultimo_acesso": self.dado.get("ultimo_acesso", ""),
            "lembrete": self.dado.get("lembrete", ""),
            # A TELA NÃO MOSTRA MAIS ESTA CAIXA — mas o campo FICA, e fica
            # com o valor certo. Quem perguntar ao servidor recebe a
            # verdade; tirar o campo junto com a caixa seria transformar
            # uma escolha de tela numa mentira de API.
            "cripto": False,
            "aviso": "a senha confere quem entra, mas as conversas ainda "
                     "estão em texto puro no disco",
        }

    # ── a conta ──────────────────────────────────────────────────────
    @staticmethod
    def _derivar(senha, sal):
        import hashlib
        return hashlib.scrypt(senha.encode("utf-8"), salt=sal,
                              n=CUSTO_N, r=CUSTO_R, p=CUSTO_P,
                              dklen=TAMANHO_CHAVE,
                              maxmem=int(128 * CUSTO_N * CUSTO_R * 1.3))

    def cadastrar(self, senha, nome=""):
        """Primeira vez: cria o perfil. Recusa senha curta, e diz por quê.

        O NOME É PERGUNTADO, não adivinhado. A versão anterior usava a
        variável USERNAME do Windows e escreveu "SAMSUNG" na tela — que é
        o nome da máquina que veio de fábrica, não o nome de ninguém. O
        computador sabe o login do sistema; ele não sabe como você quer
        ser chamado, e essa é justamente a informação que interessa aqui.
        """
        if self.dado.get("hash"):
            return {"ok": False, "porque": "já existe uma senha aqui"}
        if not (nome or "").strip():
            return {"ok": False, "porque": "me diga como quer ser chamado"}
        if len(senha or "") < MINIMO_DA_SENHA:
            return {"ok": False,
                    "porque": f"senha de pelo menos {MINIMO_DA_SENHA} caracteres"}
        sal = os.urandom(TAMANHO_SAL)
        self.dado.update({
            "nome": nome.strip()[:40],
            "sal": base64.b64encode(sal).decode(),
            "hash": base64.b64encode(self._derivar(senha, sal)).decode(),
            "custo": {"n": CUSTO_N, "r": CUSTO_R, "p": CUSTO_P},
            "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        self._gravar()
        return {"ok": True}

    # ══════════════════════════════════════════════════════════════════
    #  LEMBRAR DE MIM — e o que isso custa, dito na cara
    #
    #  O "lembrete" é um número aleatório de 32 bytes guardado nos DOIS
    #  lados: aqui no perfil e no navegador. Se os dois baterem, a tela de
    #  entrada é pulada.
    #
    #  E ISSO QUER DIZER QUE, ENQUANTO ESTIVER LEMBRADA, A SENHA NÃO
    #  PROTEGE NADA. Quem abrir o programa entra. É assim em todo lugar
    #  que tem "lembrar de mim", e a diferença é que aqui está escrito.
    #
    #  Não guardo a senha para isso — guardo uma ficha. A senha continua
    #  existindo só como hash, e "esquecer" é apagar a ficha dos dois
    #  lados, o que não mexe na senha.
    # ══════════════════════════════════════════════════════════════════
    def lembrar(self):
        import base64 as b64
        ficha = b64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
        self.dado["lembrete"] = ficha
        self._gravar()
        return {"ok": True, "lembrete": ficha}

    def esquecer(self):
        self.dado.pop("lembrete", None)
        self._gravar()
        return {"ok": True}

    def entrar_lembrado(self):
        """Entra pela ficha guardada, sem senha — e sem fingir que confere.

        A TELA DE ENTRADA CONTINUA APARECENDO. Isto aqui não a pula: ele
        só faz o botão ENTRAR funcionar com o campo da senha vazio, que é
        o que "lembrar de mim" quer dizer num programa de uma pessoa só.

        E SEJAMOS EXATOS SOBRE O QUE ISTO É. Não é a senha sendo conferida
        — a senha não está guardada em lugar nenhum, só o hash dela, e
        hash não volta a ser senha. O que existe é uma FICHA no
        `perfil.json` dizendo "esta máquina pode entrar". Quem tem o
        arquivo, entra; e quem tem o arquivo já tinha o computador.

        Por isso não há comparação nenhuma aqui, e seria pior se houvesse:
        um `compare_digest` da ficha contra ela mesma pareceria uma
        conferência e não conferiria nada. O gate é o arquivo estar lá.
        """
        if not self.dado.get("lembrete"):
            return {"ok": False, "porque": "não há senha lembrada neste computador"}
        self.dado["ultimo_acesso"] = time.strftime("%d/%m · %H:%M")
        self._gravar()
        return {"ok": True, "lembrado": True}

    def conferir_lembrete(self, ficha):
        guardada = self.dado.get("lembrete") or ""
        if not guardada or not ficha:
            return {"ok": False}
        return {"ok": hmac.compare_digest(str(ficha), guardada)}

    def conferir(self, senha):
        """Devolve {ok, segundos}. Não diz se o erro foi de usuário ou senha."""
        if not self.dado.get("hash"):
            return {"ok": False, "porque": "ainda não existe senha"}
        t0 = time.perf_counter()
        sal = base64.b64decode(self.dado["sal"])
        c = self.dado.get("custo", {})
        import hashlib
        tentativa = hashlib.scrypt(
            (senha or "").encode("utf-8"), salt=sal,
            n=c.get("n", CUSTO_N), r=c.get("r", CUSTO_R), p=c.get("p", CUSTO_P),
            dklen=TAMANHO_CHAVE,
            maxmem=int(128 * c.get("n", CUSTO_N) * c.get("r", CUSTO_R) * 1.3))
        # TEMPO CONSTANTE: ver o cabeçalho. Uma linha, e é a linha certa.
        bate = hmac.compare_digest(
            tentativa, base64.b64decode(self.dado["hash"]))
        gasto = time.perf_counter() - t0
        if bate:
            self.dado["ultimo_acesso"] = time.strftime("%d/%m · %H:%M")
            self._gravar()
        return {"ok": bool(bate), "segundos": round(gasto, 3)}

    # ── a foto ───────────────────────────────────────────────────────
    def guardar_foto(self, data_uri, limite=400_000):
        """A foto vem como data: URI do próprio navegador e fica no perfil.

        Não sai da máquina, porque não existe para onde sair: o servidor é
        127.0.0.1. Fica no JSON em vez de virar arquivo solto para o perfil
        ser UMA coisa que se copia ou se apaga inteira.
        """
        if not isinstance(data_uri, str) or not data_uri.startswith("data:image/"):
            return {"ok": False, "porque": "isso não é uma imagem"}
        if len(data_uri) > limite:
            return {"ok": False,
                    "porque": f"imagem grande demais ({len(data_uri)//1024} KB); "
                              "o limite é 390 KB"}
        self.dado["foto"] = data_uri
        self._gravar()
        return {"ok": True}

    def guardar_nome(self, nome):
        nome = (nome or "").strip()[:40]
        if not nome:
            return {"ok": False, "porque": "nome vazio"}
        self.dado["nome"] = nome
        self._gravar()
        return {"ok": True}
