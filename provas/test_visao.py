"""Testes da percepção visual (CLIP) — vetores e zero-shot.

A prova de verdade é `provas/conferir_visao.py`, que imprime o ranking
visto. Aqui ficam as invariantes que o motor de percepção promete:

  * o vetor de imagem tem `DIMENSAO` números e é unitário;
  * a mesma imagem SEMPRE dá o mesmo vetor (determinismo);
  * `reconhecer` se abstém (devolve None) quando nada bate.

Os pesos são baixados uma vez para `dados/visao/pesos`. Se o ambiente
não tem torch/open_clip ou os pesos, os testes se abstêm (skip) — não é
uma falha do módulo, é o ambiente decidindo cortar a rede por baixo.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _tem_visao():
    try:
        from visao import clip_
        return clip_._estado is not None
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _tem_visao(), reason="torch/open_clip indisponíveis neste ambiente")


def _print_de_teste():
    """Um print sintético com cor e texto legível, como no conferir_visao."""
    from provas.conferir_visao import montar_print
    return montar_print(
        "Erro de teste", ["linha um do corpo", "linha dois do corpo"],
        "#c00000")


def test_vetor_imagem_tem_a_dimensao_prometida():
    from visao import clip_
    vetor = clip_.embutir_imagem(_print_de_teste())
    assert vetor.shape == (clip_.DIMENSAO,)
    assert vetor.dtype == np.float32
    assert np.isclose(np.linalg.norm(vetor), 1.0, atol=1e-4)


def test_a_mesma_imagem_da_o_mesmo_vetor():
    from visao import clip_
    imagem = _print_de_teste()
    assert np.array_equal(clip_.embutir_imagem(imagem),
                          clip_.embutir_imagem(imagem))


def test_texto_vira_matriz_de_vectores_unitarios():
    from visao import clip_
    textos = ["um erro", "uma tela de espera"]
    matriz = clip_.embutir_texto(textos)
    assert matriz.shape == (2, clip_.DIMENSAO)
    normas = np.linalg.norm(matriz, axis=1)
    assert np.allclose(normas, 1.0, atol=1e-4)


def test_ranking_ordena_da_melhor_para_a_pior():
    from visao import clip_
    print_erro = _print_de_teste()
    ranking = clip_.pontuar(print_erro, [
        "um erro de impressora offline no Windows",
        "a configuracao de rede de um computador",
        "a instalacao de um driver do Windows",
    ])
    probs = [p for _, p in ranking]
    assert probs == sorted(probs, reverse=True)
    melhor = ranking[0][0]
    assert "erro" in melhor


def test_reconhecer_se_abstem_sem_categoria():
    """Imagem desconhecida não vira chute: é None, como a espinha manda."""
    from visao import clip_
    from PIL import Image
    ruido = Image.new("RGB", (1024, 700), (120, 60, 40))
    resultado = clip_.reconhecer(ruido, ["uma mesa de escritorio",
                                         "uma janela de navegador"],
                                 limiar=0.8)
    assert resultado is None