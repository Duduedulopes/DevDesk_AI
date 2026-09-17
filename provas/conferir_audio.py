# -*- coding: utf-8 -*-
"""Prova da percepção de áudio: um chamado falado vira texto.

O áudio `dados/audio/chamado_teste.wav` foi sintetizado com a voz
pt-BR do Windows (Maria) — contém a fala de um chamado real de
suporte: impressora offline. A prova:

    1. transcreve o áudio inteiro;
    2. confere que o texto capturou as palavras que importam
       ("impressora", "offline", "tentei", "erro");
    3. roda duas vezes e confere que o resultado é o mesmo —
       o ouvido não pode divergir entre duas escutas do mesmo som.

A medição honesta: quanto o tempo de transcrição divide o tempo de
áudio (fator > 1 significa mais rápido que tempo real).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audio import asr_

ARQUIVO = Path(__file__).resolve().parents[1] / "dados" / "audio" / "chamado_teste.wav"
PALAVRAS_QUE_IMPORTAM = ["impressora", "offline", "tentei", "erro", "ligar"]


def conferir_audio():
    if not ARQUIVO.exists():
        print("sem audio de teste em", ARQUIVO)
        return 1

    t0 = time.time()
    primeira = asr_.transcrever(ARQUIVO)
    segunda = asr_.transcrever(ARQUIVO)
    tempo = time.time() - t0

    print("idioma:", primeira["idioma"])
    print("duracao do audio: %.1f s" % primeira["duracao"])
    print("texto:")
    print("  ", primeira["texto"])
    print("tempo (duas transcricoes): %.1f s" % tempo)

    falhas = []
    texto_baixo = primeira["texto"].lower()
    for palavra in PALAVRAS_QUE_IMPORTAM:
        if palavra not in texto_baixo:
            falhas.append(f"'{palavra}' sumiu da transcricao")

    if primeira["texto"] != segunda["texto"]:
        falhas.append("duas escutas do mesmo audio divergiram")

    if primeira["duracao"]:
        fator = primeira["duracao"] / (tempo / 2)
        if fator < 1:
            falhas.append(f"mais lento que tempo real (fator {fator:.2f})")

    if falhas:
        print("\nFALHAS:")
        for f in falhas:
            print(" -", f)
        return 1

    print("\nouvido conferido: transcricao fiel e deterministica.")
    return 0


if __name__ == "__main__":
    sys.exit(conferir_audio())