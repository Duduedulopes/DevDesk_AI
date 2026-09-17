"""A percepção de áudio: Whisper transcreve a reclamação falada.

Assim como o `visao.clip_` é o olho, este é o ouvido. O chamado chega
em áudio — o cliente falando — e a mensagem de apoio precisa virar
texto para entrar no mesmo fluxo do suporte. A regra de divisão é a
mesma de todo o projeto:

    O Whisper ouve; o projeto decide o que fazer com o que ouviu.

DUAS DECISÕES QUE DEFINEM ESTE MÓDULO

1. MODELO `base`, NÃO O MENOR. O `tiny` transcreve mais rápido, mas
   erra mais (WER ~7,6% contra ~5,0%). Numa reclamação de suporte, o
   texto certo importa — um número de versão errado ou um nome de
   programa trocado muda o diagnóstico. O `base` cabe em CPU de laptop
   e ainda transcreve mais rápido que o tempo real.

2. INT8, NÃO FLOAT32. Pesos em 8 bits ocupam ~4x menos memória e rodam
   mais rápido em CPU com perda desprezível de acurácia. É a
   configuração padrão de fato do faster-whisper para CPU, e é esta
   que mantemos.

A PRIMEIRA VEZ É A ÚNICA VEZ

Os pesos (~74 MB) são baixados na primeira chamada para
`dados/audio/pesos`; depois a transcrição roda 100% offline — mesmo
contrato dos dados de MNIST e dos pesos do CLIP.
"""

import os
import threading

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_PESOS = os.path.join(_RAIZ, "dados", "audio", "pesos")

MODELO = "base"
DISPOSITIVO = "cpu"
PRECISAO = "int8"
THREADS = 4

_estado = {"travou": threading.Lock(), "carregado": False}
_estado["modelo"] = None


def _carregar():
    """Carrega o modelo uma única vez; threads de CPU = núcleos físicos."""
    estado = _estado
    with estado["travou"]:
        if not estado["carregado"]:
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            from faster_whisper import WhisperModel

            estado["modelo"] = WhisperModel(
                MODELO, device=DISPOSITIVO, compute_type=PRECISAO,
                cpu_threads=THREADS, download_root=PASTA_PESOS)
            estado["carregado"] = True
    return estado["modelo"]


def transcrever(arquivo):
    """Áudio inteiro -> texto da transcrição.

    `arquivo` é caminho de um arquivo de mídia (wav, mp3, m4a, ogg...)
    — o PyAV que vem junto com o faster-whisper decodifica o formato.
    Devolve o texto completo juntando os segmentos; cada segmento traz
    também o intervalo de tempo, que o classificador pode usar depois
    para separar "começou reclamando da tela" de "depois falou do
    cabo".

    O VAD (silêncio) está ligado: trechos sem fala não viram texto.
    """
    modelo = _carregar()
    segmentos, info = modelo.transcribe(
        str(arquivo),
        language="pt",              # o suporte fala português
        vad_filter=True,            # silêncio não vira texto
        beam_size=1,                # decode guloso: mais rápido no CPU
        temperature=0.0,            # determinístico: mesmo áudio, mesmo texto
    )
    falas = list(segmentos)   # o gerador só roda ao percorrer
    texto = " ".join(s.text.strip() for s in falas).strip()
    return {"texto": texto, "idioma": info.language,
            "duracao": info.duration}