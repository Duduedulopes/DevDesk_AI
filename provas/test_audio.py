"""Testes da percepção de áudio (ASR com faster-whisper).

O modelo `base` é baixado uma vez para `dados/audio/pesos` e depois
roda offline. Se não houver modelo instalado ou o áudio de teste não
existir, os testes se abstêm — o módulo não é culpado por não ter
pesos no disco.

A prova visual está em `provas/conferir_audio.py`.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ARQUIVO_TESTE = Path(__file__).resolve().parents[1] / "dados" / "audio" / "chamado_teste.wav"


def _tem_audio():
    try:
        from faster_whisper import WhisperModel
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _tem_audio() or not ARQUIVO_TESTE.exists(),
    reason="faster-whisper ou audio de teste indisponivel")


def test_transcrever_devolve_dicionario_com_campos_obrigatorios():
    from audio import asr_
    resultado = asr_.transcrever(ARQUIVO_TESTE)
    assert isinstance(resultado, dict)
    for chave in ("texto", "idioma", "duracao"):
        assert chave in resultado, f"chave '{chave}' ausente no retorno"


def test_transcrever_acha_a_impressora():
    from audio import asr_
    resultado = asr_.transcrever(ARQUIVO_TESTE)
    texto = resultado["texto"].lower()
    assert "impressora" in texto
    assert "offline" in texto


def test_mesmo_audio_mesmo_texto():
    from audio import asr_
    a = asr_.transcrever(ARQUIVO_TESTE)
    b = asr_.transcrever(ARQUIVO_TESTE)
    assert a["texto"] == b["texto"]


def test_fator_velocidade_maior_que_um():
    """Tem que ser mais rápido que tempo real em CPU int8."""
    import time
    from audio import asr_
    inicio = time.time()
    resultado = asr_.transcrever(ARQUIVO_TESTE)
    tempo = time.time() - inicio
    duracao_audio = resultado["duracao"]
    if duracao_audio > 0:
        assert duracao_audio / tempo >= 1.0, (
            f"audio de {duracao_audio:.1f}s levou {tempo:.1f}s — mais lento que tempo real")


def test_idioma_pt_br():
    from audio import asr_
    resultado = asr_.transcrever(ARQUIVO_TESTE)
    assert resultado["idioma"] == "pt"