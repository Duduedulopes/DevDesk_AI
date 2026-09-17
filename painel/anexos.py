# -*- coding: utf-8 -*-
"""ANEXOS: o que chega pelo clipe e pelo microfone.

O chamado real não vem só em texto. Vem um print da tela, vem um áudio
de alguém reclamando, vem um log que a pessoa arrastou para a janela.
Este arquivo é a porta desses três, e a regra é uma só:

    O ANEXO VIRA TEXTO, E O TEXTO CAI NA CAIXA PARA A PESSOA CONFERIR.

Ou seja: nada aqui responde nada, e nada aqui ENVIA nada. A imagem vira
"no print aparece um erro de compilação"; o áudio vira a transcrição; e
essa frase volta para a tela, dentro da caixa de texto, onde a pessoa lê,
corrige e só então aperta Enviar. Daí em diante é o caminho de sempre —
as sete camadas continuam existindo uma vez só.

POR QUE PASSA PELA CAIXA, E NÃO DIRETO PARA A CONVERSA

Porque a transcrição é um PALPITE. O Whisper ouve "Csharp" onde você
disse "C#", ouve "lambda" onde você disse "LINQ", e uma pergunta enviada
com a palavra errada é uma resposta errada que parece culpa da rede. A
caixa é o lugar de consertar antes, e custa um clique.

E POR QUE TODA FRASE AQUI ESTÁ NA PRIMEIRA PESSOA DE QUEM MANDOU

Porque ela vai aparecer escrita na SUA caixa de texto, com o seu nome no
cartão. "Recebi o vídeo e guardei" é fala dela — lida no seu cartão, fica
como se você tivesse dito. Toda frase deste arquivo é sua.

O QUE CADA TIPO VIRA, HOJE

    imagem      → `visao.categorias` diz qual das 20 categorias o print
                  parece. NÃO lê o texto do print — OCR ainda não existe
                  neste projeto, e fingir que lê seria pior que não ler.
    áudio       → `audio.asr_` transcreve. É o caminho mais completo dos
                  três: o que a pessoa falou vira exatamente a mensagem.
    vídeo, doc  → ficam guardados e ela DIZ que ainda não sabe ler. Um
                  botão que aceita o arquivo e finge que entendeu é pior
                  que um botão que não existe.

POR QUE O ARQUIVO É GRAVADO, E NÃO SÓ LIDO DE PASSAGEM

Porque a leitura de hoje é pior que a de amanhã. Quando existir OCR, os
prints que você mandou esta semana ainda estarão em `dados/anexos` para
serem lidos de novo — e cada um deles é dado real, do seu dia, que
nenhum molde meu imita.
"""
import base64
import mimetypes
import re
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "dados" / "anexos"

# 25 MB. Cabe print, cabe áudio de vários minutos, cabe log grande — e não
# cabe o vídeo de 4K de meia hora que travaria o servidor lendo tudo para a
# memória de uma vez. Limite desta rota, não do resto: afrouxar o geral por
# causa de uma porta abriria as outras junto.
LIMITE = 25 * 1024 * 1024

IMAGEM = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
AUDIO = {".wav", ".mp3", ".m4a", ".ogg", ".oga", ".opus", ".webm", ".flac", ".aac"}
VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v"}
# documentos cujo texto A GENTE CONSEGUE ler agora, sem camada nova
TEXTO = {".txt", ".md", ".log", ".csv", ".json", ".xml", ".yml", ".yaml",
         ".py", ".cs", ".js", ".ts", ".html", ".css", ".sql", ".sh", ".ps1",
         ".java", ".cpp", ".c", ".h", ".go", ".rb", ".php", ".ini", ".cfg"}


def _seguro(nome):
    """Um nome de arquivo que não escapa da pasta nem quebra o Windows."""
    nome = unicodedata.normalize("NFKD", str(nome or "anexo"))
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    nome = re.sub(r"[^A-Za-z0-9._-]+", "_", nome).strip("._") or "anexo"
    return nome[-60:]


def como_veio(caminho):
    """O nome SEM o carimbo de hora — o nome que a pessoa reconhece.

    O carimbo é do disco: existe para dois prints chamados `Captura.png`
    não se sobrescreverem. Mas estas frases vão para a CAIXA DE TEXTO e
    daí para a conversa, e `20260914-201039-tela.mp4` no meio de uma frase
    só atrapalha quem lê. O arquivo continua guardado com o carimbo.
    """
    return re.sub(r"^\d{8}-\d{6}-", "", Path(caminho).name)


def _familia(caminho, tipo_dito=""):
    """imagem · audio · video · texto · outro — pela extensão, depois pelo MIME.

    A EXTENSÃO PRIMEIRO, e não o MIME que o navegador manda. O
    MediaRecorder devolve `audio/webm;codecs=opus`, e `.webm` também é
    extensão de vídeo: quem sabe a diferença aqui é quem gravou, e isso
    vem no nome que o navegador escolheu.
    """
    ext = caminho.suffix.lower()
    if ext in IMAGEM:
        return "imagem"
    if ext in AUDIO:
        return "audio"
    if ext in VIDEO:
        return "video"
    if ext in TEXTO:
        return "texto"
    tipo = (tipo_dito or mimetypes.guess_type(caminho.name)[0] or "").lower()
    for prefixo, familia in (("image/", "imagem"), ("audio/", "audio"),
                             ("video/", "video"), ("text/", "texto")):
        if tipo.startswith(prefixo):
            return familia
    return "outro"


def guardar(nome, dados, tipo_dito=""):
    """Grava em `dados/anexos` e devolve (caminho, família).

    O carimbo de hora na frente resolve dois problemas de uma vez: dois
    prints chamados `Captura.png` não se sobrescrevem, e a pasta fica em
    ordem cronológica sem precisar de banco.
    """
    PASTA.mkdir(parents=True, exist_ok=True)
    alvo = PASTA / f"{time.strftime('%Y%m%d-%H%M%S')}-{_seguro(nome)}"
    alvo.write_bytes(dados)
    return alvo, _familia(alvo, tipo_dito)


def de_data_uri(uri):
    """`data:audio/webm;base64,AAAA…` → (bytes, tipo). Ou (None, "")."""
    if not isinstance(uri, str) or not uri.startswith("data:"):
        return None, ""
    cabeca, _, corpo = uri.partition(",")
    if not corpo:
        return None, ""
    tipo = cabeca[5:].split(";")[0]
    try:
        return base64.b64decode(corpo), tipo
    except (ValueError, TypeError):
        return None, ""


# ══════════════════════════════════════════════════════════════════════
#  A LEITURA DE CADA FAMÍLIA
# ══════════════════════════════════════════════════════════════════════
def _ler_ocr(caminho):
    """As letras do print, quando dá para ler. `None` quando não dá.

    LER GANHA DE RECONHECER, e o print que motivou isto mostra por quê: o
    CLIP disse "stack trace ou exceção no terminal (65%)" para uma tela
    do DevDesk VAZIA. Ele viu letra verde em fundo preto e escolheu a
    categoria mais parecida com isso entre as 20 que conhece — com
    confiança suficiente para passar pelo limiar.

    Quem lê as letras não cai nessa: o que estava escrito na imagem era
    "Boa tarde Eduardo! como posso ajudar?".
    """
    modelo = RAIZ / "modelos" / "ocr.json"
    if not modelo.exists():
        return None
    try:
        from PIL import Image
        from visao.ocr import Leitor
        texto = Leitor(modelo).ler(Image.open(caminho))
    except Exception:                                        # noqa: BLE001
        return None
    # POUCO TEXTO NÃO É TEXTO. Num print sem letra nenhuma o leitor
    # devolve o ruído que achou; três linhas de duas letras não são
    # leitura, são sujeira com forma de palavra.
    linhas = [l for l in texto.splitlines() if len(l.strip()) >= 4]
    return "\n".join(linhas) if len("".join(linhas)) >= 20 else None


def _ler_imagem(caminho):
    from visao import categorias
    lido = _ler_ocr(caminho)
    try:
        achado = categorias.reconhecer_dominio(caminho, modo="auto")
    except Exception:                                        # noqa: BLE001
        achado = None

    if lido:
        # AS DUAS COISAS, NESTA ORDEM. O que está ESCRITO vale mais que a
        # categoria — mas a categoria ainda ajuda quando o texto sai
        # picado, e escondê-la quando as duas discordam seria esconder
        # informação de quem lê.
        cabeca = "No print que eu mandei está escrito isto"
        if achado:
            cabeca += f" (parece {achado[0]}, {achado[1]:.0%})"
        return (f"{cabeca}:\n\n```\n{lido}\n```\n\n"
                "(a leitura de imagem erra letras — se alguma palavra "
                "estiver estranha, é isso.)")

    if achado is None:
        # ABSTER-SE É RESPOSTA. O CLIP tem limiar; abaixo dele ele não
        # sabe, e dizer a categoria mais provável mesmo assim seria dar
        # um palpite com cara de leitura.
        return ("Mandei um print, mas você não reconheceu o que é. "
                "Vou descrever com palavras: ")
    descricao, prob = achado
    return (f"No print que eu mandei aparece {descricao} ({prob:.0%}) — "
            f"não consegui ler as letras dele. Vou descrever: ")


def _ler_audio(caminho):
    from audio import asr_
    r = asr_.transcrever(caminho)
    texto = (r.get("texto") or "").strip()
    if not texto:
        return "Mandei um áudio, mas não saiu fala nenhuma dele. "
    return texto


def _ler_texto(caminho, teto=8000):
    """O documento vira texto — mas com TETO, e o teto é a parte honesta.

    Um log de 40 MB colado inteiro na conversa não ajuda ninguém: estoura
    a tela, estoura a janela do classificador e esconde o que importa. As
    primeiras 8 mil letras dão o começo do erro, que é onde ele quase
    sempre está — e o arquivo inteiro continua guardado.
    """
    try:
        bruto = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Mandei o arquivo {como_veio(caminho)}, mas não consegui abrir: {e}"
    corte = bruto[:teto].strip()
    resto = len(bruto) - len(corte)
    aviso = f"\n\n(são mais {resto:,} letras — o arquivo inteiro está guardado)" if resto > 0 else ""
    return f"Segue o conteúdo de {como_veio(caminho)}:\n\n{corte}{aviso}"


NAO_SEI_LER = {
    "video": "Mandei o vídeo **{nome}** (está guardado em `dados/anexos`). "
             "Sei que você ainda não lê vídeo, então vou contar o que "
             "acontece nele: ",
    "outro": "Mandei o arquivo **{nome}** (está guardado em "
             "`dados/anexos`). Sei que você não abre esse tipo. ",
}


def receber(nome, dados, tipo_dito=""):
    """De bytes a uma frase para a conversa.

    Devolve `(frase, ficha)`. A ficha é o que a tela mostra no cartão:
    nome, família e caminho — e é o que permite ver a miniatura do print
    junto da mensagem, em vez de só o texto que ele virou.
    """
    caminho, familia = guardar(nome, dados, tipo_dito)
    ficha = {"nome": caminho.name, "familia": familia,
             "caminho": str(caminho), "bytes": len(dados)}
    try:
        if familia == "imagem":
            frase = _ler_imagem(caminho)
        elif familia == "audio":
            frase = _ler_audio(caminho)
        elif familia == "texto":
            frase = _ler_texto(caminho)
        else:
            frase = NAO_SEI_LER[familia if familia in NAO_SEI_LER else "outro"] \
                .format(nome=como_veio(caminho))
            ficha["so_guardou"] = True
    except ImportError as e:
        # A CAMADA NÃO ESTÁ INSTALADA, e isso se DIZ. Sem este ramo o
        # servidor devolvia 500 e a tela ficava muda — a pessoa não tem
        # como adivinhar que faltou um `pip install`.
        frase = (f"Mandei **{como_veio(caminho)}**, mas a camada que lê esse tipo "
                 f"não está instalada aí ({e.name}) — "
                 f"`pip install -r requirements.txt` resolve. "
                 f"Enquanto isso, vou escrever: ")
        ficha["so_guardou"] = True
    except Exception as e:                                   # noqa: BLE001
        frase = (f"Mandei **{como_veio(caminho)}**, mas deu erro ao ler: "
                 f"{type(e).__name__}: {e}. Vou escrever: ")
        ficha["so_guardou"] = True
    return frase, ficha
