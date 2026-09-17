"""A percepção visual: CLIP vira os olhos do assistente.

A arquitetura manda transformar um print em texto + vetor antes de
entender. É este o primeiro elo — o olho. E a decisão de design cabe
numa frase:

    O CLIP não raciocina sobre o print; ele só vê onde está o texto,
    a mensagem de erro, a janela ativa. Raciocinar é trabalho das
    outras camadas.

DUAS DECISÕES QUE DEFINEM ESTE MÓDULO

1. PESOS PRÉ-TREINADOS, BAIXADOS UMA VEZ. O MobileCLIP2-S0 foi
   treinado com bilhões de (imagem, texto) — é esse o custo que a gente
   não repete. O download acontece na primeira chamada e fica salvo em
   `dados/visao/pesos`; dali em diante a inferência roda OFF-LINE, sem
   rede, sem conta, sem chave. Quem baixou uma vez não precisa de
   internet nunca mais — é o mesmo contrato do `dados/mnist.pkl.gz`.

2. ZERO-SHOT HOJE, CABEÇOTE PRÓPRIO AMANHÃ. `pontuar` compara o print
   contra descrições que damos em linguagem natural — sem precisar
   treinar nada. A regra do projeto continua valendo: quando houver
   exemplos rotulados de verdade, o cabeçote que decide a categoria é
   o mesmo motor NumPy das outras camadas (`nucleo`). O CLIP entrega o
   vetor; o projeto decide a partir dele.

POR QUE MOBILECLIP2-S0

É o menor da família MobileCLIP2 (74,8M de parâmetros) — cabe em CPU de
laptop e entrega vetores de 512 números para imagem e texto. A imagem
entra em 256×256 RGB; o texto em no máximo 77 tokens (frascurta de
uma descrição de categoria).
"""

import os
import threading

import numpy as np

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_PESOS = os.path.join(_RAIZ, "dados", "visao", "pesos")

MODELO = "MobileCLIP2-S0"
PRETREINADO = "dfndr2b"
DIMENSAO = 512
TAMANHO_IMAGEM = 256
MAX_TOKENS = 77
LIMIAR_ABSTENCAO = 0.3   # abaixo disso, reconhecer() se abstém

_estado = {"travou": threading.Lock(), "carregado": False}
_estado["modelo"] = None
_estado["preprocessar"] = None
_estado["tokenizador"] = None


def _carregar():
    """Carrega o modelo uma única vez e aponta cada `_estado` para ele.

    `create_model_and_transforms` devolve três coisas: o modelo, o
    preprocess de TREINO (com aumento aleatório de dados) e o de
    VALIDAÇÃO. Usamos o de validação — a inferência tem que ser
    determinística: o mesmo print tem que dar o mesmo vetor sempre.
    """
    estado = _estado
    with estado["travou"]:
        if not estado["carregado"]:
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            import open_clip

            modelo, _treino, preprocessar = open_clip.create_model_and_transforms(
                MODELO, pretrained=PRETREINADO, cache_dir=PASTA_PESOS)
            modelo.eval()
            estado["modelo"] = modelo
            estado["preprocessar"] = preprocessar
            estado["tokenizador"] = open_clip.get_tokenizer(MODELO)
            estado["carregado"] = True
    return estado["modelo"], estado["preprocessar"], estado["tokenizador"]


def _abrir_imagem(imagem):
    """Aceita caminho (str/Path) ou imagem já aberta, e devolve RGB."""
    from PIL import Image

    if isinstance(imagem, (str, os.PathLike)):
        imagem = Image.open(imagem)
    if imagem.mode != "RGB":
        imagem = imagem.convert("RGB")
    return imagem


def embutir_imagem(imagem):
    """Print -> vetor unitário de `DIMENSAO` números (float32 nativo).

    É o vetor que as outras camadas comparam, guardam e classificam.
    Depois que os pesos estão em cache, isto roda fora da rede.
    """
    import torch

    modelo, preprocessar, _ = _carregar()
    tensores = preprocessar(_abrir_imagem(imagem)).unsqueeze(0)
    with torch.no_grad():
        vetor = modelo.encode_image(tensores)
    vetor = vetor / vetor.norm(dim=-1, keepdim=True)
    return vetor[0].cpu().numpy().astype(np.float32)


def embutir_texto(textos):
    """Lista de descrições -> matriz (N, `DIMENSAO`), linhas unitárias."""
    import torch

    modelo, _, tokenizador = _carregar()
    tokens = tokenizador(list(textos))
    with torch.no_grad():
        vetores = modelo.encode_text(tokens)
    vetores = vetores / vetores.norm(dim=-1, keepdim=True)
    return vetores.cpu().numpy().astype(np.float32)


def pontuar(imagem, descricoes):
    """Print contra descrições: probabilidades por categoria.

    Devolve lista de `(descricao, probabilidade)` em ordem decrescente.
    A temperatura de 100 segue o CLIP original — é a escala em que esses
    modelos nasceram. O `None` de `reconhecer` é a porta de abstenção:
    nenhuma categoria merece a palavra, e não chutamos.
    """
    imagem_vec = embutir_imagem(imagem)
    texto_mat = embutir_texto(descricoes)
    logits = 100.0 * imagem_vec @ texto_mat.T
    exps = np.exp(logits - logits.max())
    probs = exps / exps.sum()
    resultados = [(descricao, float(prob))
                  for descricao, prob in zip(descricoes, probs)]
    return sorted(resultados, key=lambda p: p[1], reverse=True)


def reconhecer(imagem, descricoes, limiar=None):
    """Melhor categoria do print, ou `None` se a confiança fica baixa.

    `limiar=None` usa `LIMIAR_ABSTENCAO`. Segue a espinha do projeto:
    melhor calar e escalar do que afirmar no escuro.
    """
    if limiar is None:
        limiar = LIMIAR_ABSTENCAO
    descricao, prob = pontuar(imagem, descricoes)[0]
    return (descricao, prob) if prob >= limiar else None