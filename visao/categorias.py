"""As categorias do domínio — o que os prints de suporte e dev mostram.

O `clip_.pontuar` só sabe o que a gente der para comparar: a descrição
é o molde. E o CLIP zero-shot casa por SOBREPOSIÇÃO DE PALAVRAS entre
o print e a descrição — um print de erro de impressora tem "offline",
"impressora", "driver"; um stack trace tem "Traceback", "Error",
"line". Então cada categoria aqui cita as palavras que esse print
costuma conter, em português e inglês (a tela do Windows fala os
dois).

DUAS LISTAS, UM CONTINUUM

  SUPORTE — o chamado do dia a dia: impressora, rede, login,
  atualização, antivírus. É o N1 do projeto, reconhecer e aplicar
  procedimento conhecido.

  DESENVOLVIMENTO — o dev quebrou algo e a tela mostra o motor
  girando: build, teste, exceção, git, banco. Aqui o olho aponta o
  tipo de defeito para as camadas de investigação entrarem.

As categorias são texto comum. O dia em que houver prints rotulados de
verdade, o cabeçote que decide é o `nucleo` — estas listas viram só a
memória de quais categorias existem.
"""

SUPORTE = [
    "um erro de impressora offline, papel atascado ou tinta esgotada",
    "a instalacao de um driver ou do Windows, com barra de progresso",
    "a configuracao de rede de um computador, com IP, gateway e DNS",
    "uma tela de login ou de senha",
    "uma atualizacao ou reinicializacao pendente do Windows",
    "um aviso de antivirus, firewall ou seguranca ameacando bloquear",
    "uma tela azul de erro critico (blue screen) ou de desligamento",
    "um aviso de espaço em disco insuficiente ou de armazenamento cheio",
    "o gerenciador de tarefas mostrando um processo travado ou usando muita memoria",
    "um aviso de backup ou de restauracao do sistema",
]

DESENVOLVIMENTO = [
    "um stack trace ou excecao no terminal, com Traceback, Error e File, linea de codigo",
    "um erro de compilacao ou de build, com Build FAILED, error CS e linha:coluna no arquivo",
    "uma falha de teste, com FAILED, AssertionError, assertion e test",
    "um erro de importacao, com ModuleNotFoundError, ImportError ou erro de sintaxe no arquivo",
    "um prompt de terminal ou painel de comandos executando um comando, com $ ou >",
    "uma operacao de git, com Unmerged paths, conflict, merge, push, Git e branch",
    "o editor de codigo (VS Code) com marcador de erro vermelho no arquivo, com cursor e numero de linha",
    "uma conexao ou consulta de banco de dados, com Falha de login, database, Sql e Msg numero 18456",
    "uma resposta de API ou requisicao HTTP, com status code 500, 404, error de servidor ou de endpoint",
    "uma instalacao de pacote, com pip install, venv, Requirement already satisfied ou erro de pacote Python",
]


def pontuar_dominio(imagem, modo="desenvolvimento"):
    """`modo='suporte'` ou `'desenvolvimento'`: ranking das categorias.

    Devolve a mesma forma de `clip_.pontuar` — lista de
    `(descricao, probabilidade)` em ordem decrescente — para o conjunto
    que interessa. `modo='auto'` junta as duas listas.
    """
    from . import clip_

    if modo == "suporte":
        categorias = SUPORTE
    elif modo == "desenvolvimento":
        categorias = DESENVOLVIMENTO
    elif modo == "auto":
        categorias = SUPORTE + DESENVOLVIMENTO
    else:
        raise ValueError(f"modo desconhecido: {modo}")
    return clip_.pontuar(imagem, categorias)


def reconhecer_dominio(imagem, modo="desenvolvimento", limiar=None):
    """Melhor categoria no domínio escolhido, ou `None` (abstenção)."""
    from . import clip_

    if limiar is None:
        limiar = clip_.LIMIAR_ABSTENCAO
    ranking = pontuar_dominio(imagem, modo)
    descricao, prob = ranking[0]
    return (descricao, prob) if prob >= limiar else None