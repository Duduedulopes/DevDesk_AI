# -*- coding: utf-8 -*-
"""RASCUNHO das falas das PARTES — a minha metade.

Combinamos meio a meio: eu escrevo as falas de COMANDO ("atua"), que são
as de imitar sem errar muito, e você escreve as de CONVERSA ("aprende" e
"tela"), que são as difíceis — porque são a sua voz, e eu só consigo
chutar como você fala.

POR QUE ESTAS FALAS PRECISAM EXISTIR

Medido no corpus atual, contando as 22.709 frases:

    pagamento      0 vezes   ← a rede nunca viu
    login          0
    vitrine        0
    carrinho       0
    produtos       0
    valores        0
    preço          0
    modelagem      0
    mvc            0
    c#             0         ← e você usa isso o tempo todo
    ---
    projeto    1.260 vezes
    criar        268

Nove das palavras da sua frase de exemplo não existem no mundo dela. Não
é a rede sendo burra: é ela respondendo sobre coisas que nunca lhe foram
apresentadas. Quando ela pôs `apagar` em 100% no seu pedido de pagamento,
foi porque "pagamento" e "apagar" dividem os pedaços `pag` e `aga`, e o
pedaço "pagamento" inteiro não está no vocabulário. Ela agarrou o que
tinha.

COMO USAR ISTO

Leia, corte o que soar a robô, e escreva as listas `aprende` e `tela` —
que estão vazias de propósito. Depois eu junto no `dados/falas.py`,
regenero o corpus e treino.

E CORTE MESMO. Fala que você nunca diria é pior que fala faltando: a rede
aprende a esperar aquilo, e aí erra no que você diz de verdade.

Os buracos `{nome}`, `{ling}` e `{tipo}` são preenchidos pelo
`gerar_corpus_dev.py`, como nas suas outras falas.
"""

PARTES = {
    # ══════════════════════════════════════════════════════════════════
    #  ENTRAR NO SISTEMA
    # ══════════════════════════════════════════════════════════════════
    "parte_login": {
        "atua": [
            "faz um login pro sistema",
            "cria a tela de login",
            "poe login e senha no {nome}",
            "adiciona autenticacao no projeto",
            "quero uma area logada",
            "faz o cadastro e o login dos usuarios",
            "cria login com email e senha",
            "monta a autenticacao do {nome}",
            "acrescenta uma tela de entrada",
            "faz a parte de usuario e senha",
            "quero que o usuario entre com conta",
            "cria a tela de cadastro de usuario",
            "poe recuperacao de senha",
            "faz logout tambem",
            "adiciona controle de acesso",
            "quero perfil de administrador e de cliente",
            "cria os papeis de usuario",
            "faz a sessao do usuario",
            "poe autenticacao no {ling}",
            "adiciona login no site",
        ],
        "aprende": [],   # ← sua metade
        "tela": [],      # ← sua metade
    },

    # ══════════════════════════════════════════════════════════════════
    #  MOSTRAR OS PRODUTOS
    # ══════════════════════════════════════════════════════════════════
    "parte_vitrine": {
        "atua": [
            "faz uma vitrine dos produtos",
            "cria a listagem dos produtos",
            "quero mostrar os produtos com preco",
            "monta o catalogo do {nome}",
            "faz a pagina que lista os itens",
            "poe os produtos numa grade",
            "cria a vitrine com foto e valor",
            "quero uma galeria dos meus trabalhos",
            "faz a pagina de detalhe do produto",
            "adiciona a lista de produtos no site",
            "monta a home com os produtos em destaque",
            "cria a tela de produtos",
            "quero filtro por categoria",
            "poe busca na lista de produtos",
            "faz a paginacao da listagem",
            "cria o cadastro dos produtos",
            "quero editar e apagar produto pelo painel",
            "monta a vitrine em {ling}",
            "faz a exibicao dos itens com valores",
            "adiciona ordenacao por preco",
        ],
        "aprende": [],
        "tela": [],
    },

    # ══════════════════════════════════════════════════════════════════
    #  RECEBER O DINHEIRO
    # ══════════════════════════════════════════════════════════════════
    "parte_pagamento": {
        "atua": [
            "cria uma forma de pagamento",
            "faz o checkout do {nome}",
            "quero receber pagamento pelo site",
            "adiciona pagamento por cartao",
            "poe pix como forma de pagamento",
            "monta a tela de finalizar compra",
            "faz o fechamento do pedido",
            "cria a parte de cobranca",
            "quero gerar boleto",
            "adiciona a confirmacao de pagamento",
            "faz a tela de pagamento",
            "poe o resumo do pedido antes de pagar",
            "cria o registro dos pedidos pagos",
            "quero calcular o frete",
            "monta o pagamento em {ling}",
            "faz a pagina de obrigado depois da compra",
            "adiciona status do pedido",
            "cria a nota do pedido",
        ],
        "aprende": [],
        "tela": [],
    },

    # ══════════════════════════════════════════════════════════════════
    #  JUNTAR ANTES DE PAGAR
    # ══════════════════════════════════════════════════════════════════
    "parte_carrinho": {
        "atua": [
            "faz um carrinho de compras",
            "cria o carrinho do {nome}",
            "quero que o cliente junte varios itens",
            "adiciona botao de por no carrinho",
            "monta a tela do carrinho",
            "faz o carrinho somar o total",
            "poe quantidade no carrinho",
            "quero remover item do carrinho",
            "cria a sacola de compras",
            "faz o carrinho guardar entre visitas",
            "adiciona o subtotal e o total",
            "monta o carrinho em {ling}",
            "quero um mini carrinho no topo",
            "faz o carrinho lembrar do usuario logado",
            "cria a lista de itens escolhidos",
        ],
        "aprende": [],
        "tela": [],
    },
}


# ══════════════════════════════════════════════════════════════════════
#  O QUE FALTA ALÉM DAS FALAS — e é você quem decide
# ══════════════════════════════════════════════════════════════════════
#
# 1. A LISTA DAS PARTES É SUA, NÃO MINHA. Escrevi quatro porque foram as
#    quatro que a sua frase pediu. Se o assistente tem de saber montar
#    relatório, upload de imagem, painel de administração, envio de
#    e-mail, exportar planilha — cada uma dessas é outra parte, e o
#    escopo é seu.
#
# 2. AS PALAVRAS DA LINGUAGEM TAMBÉM FALTAM. "c#" e "mvc" aparecem ZERO
#    vezes no corpus, e você usa as duas o tempo todo. Isso não é parte,
#    é o etiquetador: as falas de linguagem precisam de "em c#", "com
#    mvc", "asp.net core", "entity framework", "blazor".
#
# 3. E TEM UMA PERGUNTA DE PROJETO ATRÁS DISSO. Uma parte não é uma
#    intenção como "rodar" ou "compilar": ela não é uma AÇÃO, é um
#    PEDAÇO de um projeto. Talvez o certo seja uma rede separada — a
#    intenção continua sendo `criar_projeto`, e as partes saem de uma
#    segunda cabeça multi-rótulo em cima do mesmo pedido. Foi assim que
#    o compositor já faz com os papéis (principal, teste, rota).
#
#    Não vou decidir isso sozinho. Mas a medida diz que separar tem
#    vantagem: `criar_projeto` sozinho já vai a 96%, e não quero
#    estragar isso enfiando quatro classes irmãs que competem com ele no
#    mesmo softmax.
