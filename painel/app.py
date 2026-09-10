"""O DevDesk: servidor local + janela.

COMO ELE ABRE

Se o `pywebview` estiver instalado, abre numa JANELA nativa do Windows — um
aplicativo de verdade, sem barra de endereço. Se não estiver, serve no
navegador e diz como virar aplicativo. Roda hoje sem instalar nada, e vira
app com um `pip install pywebview`.

POR QUE HTML E NÃO WIDGETS

A tela que queremos é uma coluna de cartões que rola, com uma lista lateral e
uma caixa de texto embaixo. Isso é o que HTML faz naturalmente. E o Devin que
serviu de referência roda dentro do VS Code, que é webview — se um dia o
DevDesk virar extensão, esta tela vai junto. Em Qt, nada disso se aproveita.

NÃO SAI DA MÁQUINA. Escuta em 127.0.0.1, sem nuvem, sem chave, sem API de
terceiro. É o compromisso do projeto inteiro.
"""
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nucleo.cerebro import Cerebro
from nucleo.porteiro import Porteiro
from painel.sessao import Sessao

AQUI = Path(__file__).resolve().parent
VENDOR = (AQUI / "vendor").resolve()
PORTA = 8770

# O editor do VS Code mora aqui dentro, e nao numa CDN.
#
# `painel/vendor/monaco/` sao 4,9 MB do monaco-editor da Microsoft (MIT),
# baixados UMA vez e guardados no projeto. Sem isso, embutir o editor
# significaria buscar script de um servidor de terceiro toda vez que a
# tela abre — e o compromisso do projeto e rodar inteiro nesta maquina.
#
# Ficaram de fora, de proposito, os 7 MB de `vs/language/`: sao os
# servicos de IntelliSense de TypeScript/JSON/CSS/HTML. Nao servem para
# C# nem Python, que e o que se escreve por aqui.
TIPOS = {".js": "text/javascript", ".css": "text/css", ".ttf": "font/ttf",
         ".map": "application/json", ".html": "text/html", ".svg": "image/svg+xml"}


def construir(sessao, porteiro):
    class Alça(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, dado, codigo=200):
            corpo = json.dumps(dado).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _estatico(self, pedido):
            """Serve o Monaco. A conferencia e por caminho RESOLVIDO.

            Comparar texto ("comeca com /vendor/") NAO serve: o pedido
            `/vendor/../../../../Windows/System32/algo` tambem comeca com
            /vendor/. O `resolve()` desfaz os `..` antes de comparar — a
            mesma regra que a Sessao usa para os arquivos do projeto, e
            pela mesma razao.
            """
            rel = unquote(urlparse(pedido).path)[len("/vendor/"):]
            alvo = (VENDOR / rel).resolve()
            if not alvo.is_file() or VENDOR not in alvo.parents:
                return self._json({"erro": "não encontrado"}, 404)
            corpo = alvo.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TIPOS.get(alvo.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(corpo)))
            # Sao 87 arquivos que nunca mudam; sem isto o editor inteiro
            # e rebaixado a cada F5.
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            if self.path.startswith("/vendor/"):
                return self._estatico(self.path)
            if self.path in ("/", "/index.html"):
                corpo = (AQUI / "interface.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            elif self.path == "/api/estado":
                self._json({"pasta": str(sessao.pasta), "cartoes": sessao.cartoes,
                            "conversa": sessao.id, "nome": sessao.nome,
                            "pendentes": len(sessao.pendentes),
                            "abas": sessao.abas,
                            "tela": sessao.tela,
                            "estado": sessao.estado,
                            "estado_como": sessao.ESTADOS[sessao.estado][0],
                            "estado_diz": sessao.ESTADOS[sessao.estado][1],
                            "medido": sessao.cerebro.medido if sessao.cerebro else {}})
            elif self.path.startswith("/api/arvore"):
                # `?sub=<pasta relativa>` pede UM nível: é a aba Projeto
                # abrindo uma pasta, e não a árvore inteira.
                q = parse_qs(urlparse(self.path).query)
                sub = (q.get("sub") or [""])[0]
                self._json({"sub": sub, "itens": sessao.arvore(sub)})
            elif self.path == "/api/porteiro":
                # O QUE A TELA DE ENTRADA PODE SABER ANTES DE VOCÊ DIGITAR:
                # o nome, a foto, o último acesso e se já existe senha.
                # Hash e sal NÃO saem daqui — não há motivo para o
                # navegador ver, e o que não é enviado não vaza.
                self._json(porteiro.cartao())
            elif self.path == "/api/lateral":
                self._json({"conversas": sessao.conversas(), "tarefas": sessao.tarefas(),
                            "aqui": sessao.id})
            else:
                self._json({"erro": "não encontrado"}, 404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            corpo = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/mensagem":
                sessao.receber(corpo.get("texto", ""))
            elif self.path == "/api/confirmar":
                sessao.confirmar(corpo.get("id"))
            elif self.path == "/api/recusar":
                sessao.recusar(corpo.get("id"))
            elif self.path == "/api/abrir":
                sessao.abrir(corpo.get("caminho", ""))
            elif self.path == "/api/fechar":
                sessao.fechar(corpo.get("caminho", ""))
            elif self.path == "/api/gravar":
                sessao.gravar(corpo.get("caminho", ""), corpo.get("conteudo", ""))
            elif self.path == "/api/desfazer":
                sessao.desfazer(corpo.get("caminho", ""))
            elif self.path == "/api/projeto/fechar":
                sessao.fechar_projeto()
            elif self.path == "/api/conversa/nova":
                sessao.nova()
            elif self.path == "/api/conversa/abrir":
                sessao.carregar(corpo.get("id", ""))
            elif self.path == "/api/conversa/apagar":
                sessao.apagar(corpo.get("id", ""))
            elif self.path == "/api/conversa/renomear":
                sessao.renomear(corpo.get("id", ""), corpo.get("nome", ""))
            elif self.path == "/api/limpar":
                sessao.nova()
            elif self.path == "/api/vscode":
                sessao.no_vscode(corpo.get("caminho", ""))
            elif self.path == "/api/lembrar":
                return self._json(porteiro.lembrar())
            elif self.path == "/api/esquecer":
                return self._json(porteiro.esquecer())
            elif self.path == "/api/lembrete":
                return self._json(porteiro.conferir_lembrete(corpo.get("ficha", "")))
            elif self.path == "/api/entrar":
                # A senha chega, é conferida e é ESQUECIDA. Não guardo em
                # variável, não escrevo em log, não volta na resposta.
                return self._json(porteiro.conferir(corpo.get("senha", "")))
            elif self.path == "/api/entrar-lembrado":
                # ENTRAR SEM DIGITAR, quando a ficha existe. A tela de
                # entrada aparece do mesmo jeito; o que muda é que o botão
                # funciona com o campo vazio.
                return self._json(porteiro.entrar_lembrado())
            elif self.path == "/api/cadastrar":
                return self._json(porteiro.cadastrar(corpo.get("senha", ""),
                                                     corpo.get("nome", "")))
            elif self.path == "/api/perfil":
                r = {"ok": True}
                if "foto" in corpo:
                    r = porteiro.guardar_foto(corpo["foto"])
                if r.get("ok") and corpo.get("nome"):
                    r = porteiro.guardar_nome(corpo["nome"])
                return self._json(r)
            elif self.path == "/api/ensinar":
                frase    = corpo.get("frase", "")
                intencao = corpo.get("intencao", "")
                palpite  = corpo.get("palpite", "")
                reescrita = corpo.get("reescrita", "").strip()
                # A RESPOSTA ESCRITA NA FAIXA DE CORREÇÃO. Não veio um clique
                # numa intenção pronta — a pessoa digitou com as próprias
                # palavras o que ela quis dizer. O que ela escreveu pode ser
                # o NOME de uma intenção (ex.: "criar_projeto") — aí é direto
                # — ou uma reescrita da frase ("quero criar um projeto") — aí
                # a rede que ERROU a frase original também reconhece a nova,
                # e a nova vira o rótulo para ensinar a frase velha.
                if not intencao and reescrita and sessao.cerebro:
                    exato = reescrita.lower().replace(" ", "_")
                    if exato in sessao.cerebro.intencoes:
                        intencao = exato
                    else:
                        p = sessao.cerebro.pensar(reescrita)
                        if p["candidatos"]:
                            intencao = p["candidatos"][0]["nome"]
                        else:
                            # A reescrita não tem uma peça sequer conhecida —
                            # não dá para ensinar nada com ela.
                            sessao.cartao("ela", texto=(
                                "Não reconheci nenhuma peça na sua reescrita, "
                                "então não deu para corrigir com ela. Escreva "
                                "de outro jeito, ou clique numa das intenções "
                                "acima."))
                            return self._json({"ok": False})
                if not intencao:
                    sessao.cartao("ela", texto=(
                        "Não recebi a intenção certa — clique numa das "
                        "listadas acima ou escreva o que eu devia ter entendido."))
                    return self._json({"ok": False})
                try:
                    sessao.ensinar(frase, intencao, palpite)
                except Exception as erro:
                    sessao.cartao("ela", texto=f"A correção não pôde ajustar a rede agora: {erro}")
                # Depois de aprender, executa a ação da intenção escolhida.
                # É isso que o usuário esperava quando clicou — não só o
                # registro do aprendizado.
                from painel import respostas as _res
                feito = _res.responder(sessao, intencao, frase)
                if feito and feito[0]:
                    sessao.cartao("ela", texto=feito[0])
                elif not feito:
                    sessao.cartao("ela", texto=(
                        f"Entendi como **{intencao}**. "
                        f"Ainda não tenho uma ação configurada para isso — "
                        f"mas a correção foi registrada e vai me treinar."))
                sessao._assentar()
            else:
                return self._json({"erro": "não encontrado"}, 404)
            self._json({"ok": True})

    return Alça


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else str(AQUI.parent)
    try:
        cerebro = Cerebro(str(AQUI.parent / "modelos" / "intencao.json"))
        cerebro.carregar_guarda(str(AQUI.parent / "modelos" / "guarda.json"))
        aviso = (f"cérebro: {len(cerebro.intencoes)} intenções, "
                 f"{len(cerebro.indice_peca):,} peças, limiar {cerebro.limiar:.0%}")
    except Exception as erro:
        cerebro, aviso = None, f"cérebro NÃO carregou: {erro}"

    sessao = Sessao(pasta, cerebro)
    sessao.cartao("ela", texto=sessao.abertura())

    # O PORTEIRO. Ele guarda o perfil em dados/perfil.json — nome, foto e
    # o hash da senha. Nunca a senha.
    porteiro = Porteiro(AQUI.parent / "dados" / "perfil.json")

    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), construir(sessao, porteiro))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    print(f"\n  DevDesk AI")
    print(f"  {aviso}")
    print(f"  pasta: {sessao.pasta}")
    print(f"  http://127.0.0.1:{PORTA}\n")

    try:
        import webview
        webview.create_window("DevDesk AI", f"http://127.0.0.1:{PORTA}",
                              width=1280, height=820)
        webview.start()
    except ImportError:
        print("  (janela nativa: pip install pywebview — abrindo no navegador)\n")
        webbrowser.open(f"http://127.0.0.1:{PORTA}")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
