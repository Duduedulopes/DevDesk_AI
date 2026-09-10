# -*- coding: utf-8 -*-
"""A PONTE entre o chat e a rede que escreve LINQ.

    "soma o valor das transações concluídas"
        → transacoes.Where(t => t.Status == StatusTransacao.Concluida)
                    .Sum(t => t.Valor)

O QUE ESTE ARQUIVO RESOLVE, QUE A REDE NÃO RESOLVE SOZINHA

A rede sabe pontuar um pedido contra os nomes de UM projeto. Para
funcionar dentro do painel faltavam três coisas mundanas:

    1. QUAL projeto. O aberto na sessão, ou o que a pessoa nomear na
       frase — e o nomeado ganha.
    2. O MODELO daquele projeto, que talvez ainda não exista.
    3. Não fazer a pessoa esperar dois minutos olhando para o nada.

O TREINO RODA EM SEGUNDO PLANO, E ISSO É DECISÃO DE ENGENHARIA

Ler um projeto novo custa ~2 minutos. Fazer isso dentro da requisição do
chat congelaria a interface inteira — e o navegador provavelmente
desistiria antes. Então a primeira pergunta num projeto novo dispara o
treino numa linha de execução separada e responde na hora dizendo o que
está acontecendo; as seguintes já encontram o modelo pronto.

Ninguém é perguntado se pode treinar (foi o que o Eduardo pediu). O que
se evita é a interface travada, que é outra coisa.
"""
import sys
import threading
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from modelo.consulta_linq import (Consultor, caminho_do_modelo,  # noqa: E402
                                  guardar, treinar)
from modelo.leitor_csharp import ProjetoCSharp                   # noqa: E402

# projeto (texto do caminho) -> Consultor já aberto
_ABERTOS = {}
# projeto -> "treinando" | "pronto" | mensagem de erro
_ESTADO = {}
_TRAVA = threading.Lock()

FORA = {"bin", "obj", ".vs", ".git", "node_modules", "packages", "__pycache__"}


def _plano(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ══════════════════════════════════════════════════════════════════════
#  1. QUAL PROJETO
# ══════════════════════════════════════════════════════════════════════
def _tem_csharp(pasta, teto=4000):
    """Tem `.cs` aqui dentro? — com o passeio LIMITADO.

    Isto roda a cada mensagem do chat, para decidir se a pasta serve. Um
    `rglob` sem teto na pasta errada (a raiz do usuário, um `node_modules`
    grande) faria o chat pensar por segundos antes de responder qualquer
    coisa. 4.000 entradas é muito mais do que qualquer projeto de estudo e
    é rápido em qualquer disco.
    """
    vistos = 0
    try:
        for f in Path(pasta).rglob("*.cs"):
            vistos += 1
            if vistos > teto:
                return False
            if not any(x in FORA for x in f.parts):
                return True
    except OSError:
        pass
    return False


def achar_projeto(sessao, frase):
    """A pasta do projeto C#: a nomeada na frase, senão a aberta na sessão.

    O NOMEADO GANHA, e é o que a pessoa espera: se ela escreveu "no
    projeto Linq", ela não está falando da pasta que por acaso está
    aberta. Um caminho inteiro ("C:\\...\\Linq") também vale, e para isso
    a sessão já tem o extrator que o `abrir` usa.
    """
    # (a) um caminho escrito por extenso
    cam = None
    try:
        cam = sessao._caminho_da_frase(frase)
    except Exception:
        cam = None
    if cam and Path(cam).is_dir() and _tem_csharp(cam):
        return Path(cam).resolve()

    # (b) um NOME solto — procurado ao lado da pasta de casa e dentro dela
    palavras = {p.strip(".,;:!?\"'") for p in _plano(frase).split() if len(p) > 2}
    if palavras:
        casa = Path(getattr(sessao, "pasta_inicial", ".")).resolve()
        for onde in (casa.parent, casa, Path(getattr(sessao, "pasta", casa)).resolve()):
            try:
                vizinhas = [d for d in onde.iterdir() if d.is_dir()]
            except OSError:
                continue
            for d in vizinhas:
                if d.name in FORA:
                    continue
                if _plano(d.name) in palavras and _tem_csharp(d):
                    return d.resolve()

    # (c) a pasta aberta na sessão, ou a de casa
    for cand in (getattr(sessao, "pasta", None), getattr(sessao, "pasta_inicial", None)):
        if cand and _tem_csharp(cand):
            return Path(cand).resolve()
    return None


# ══════════════════════════════════════════════════════════════════════
#  2. O MODELO DAQUELE PROJETO
# ══════════════════════════════════════════════════════════════════════
def _treinar_ao_fundo(pasta):
    chave = str(pasta)
    try:
        proj = ProjetoCSharp(pasta)
        rede, peneira, _ = treinar(proj)
        if rede is None:
            with _TRAVA:
                _ESTADO[chave] = "esse projeto não tem nenhuma lista para consultar"
            return
        guardar(caminho_do_modelo(RAIZ, pasta), rede, peneira,
                {"projeto": Path(pasta).name, "treinado_pelo_painel": True})
        with _TRAVA:
            _ESTADO[chave] = "pronto"
    except Exception as e:                       # noqa: BLE001
        # o erro fica GUARDADO e vira resposta na próxima pergunta. Uma
        # linha de execução que morre calada é um programa que responde
        # "estou treinando" para sempre.
        with _TRAVA:
            _ESTADO[chave] = f"não consegui ler esse projeto: {e}"


def consultor_de(pasta):
    """(Consultor, aviso). Um dos dois é None."""
    chave = str(pasta)
    with _TRAVA:
        if chave in _ABERTOS:
            return _ABERTOS[chave], None
        estado = _ESTADO.get(chave)
    if estado == "treinando":
        return None, ("Ainda estou lendo o projeto "
                      f"{Path(pasta).name} — leva uns 2 minutos. "
                      "Pergunta de novo daqui a pouco.")
    if estado and estado != "pronto":
        return None, estado

    caminho = caminho_do_modelo(RAIZ, pasta)
    if caminho.exists():
        try:
            c = Consultor(caminho, pasta)
        except ValueError as e:
            # modelo de uma versão anterior da rede: treina de novo em vez
            # de morrer com um erro que a pessoa não pode consertar
            with _TRAVA:
                _ESTADO[chave] = "treinando"
            threading.Thread(target=_treinar_ao_fundo, args=(pasta,),
                             daemon=True).start()
            return None, (f"O modelo de {Path(pasta).name} é de uma versão "
                          f"anterior da rede ({e}). Estou refazendo — "
                          "uns 2 minutos.")
        if not c.pronto():
            return None, (f"Li {Path(pasta).name}, mas não achei nenhuma "
                          "List<T> lá dentro — não há o que consultar.")
        with _TRAVA:
            _ABERTOS[chave] = c
            _ESTADO[chave] = "pronto"
        return c, None

    with _TRAVA:
        _ESTADO[chave] = "treinando"
    threading.Thread(target=_treinar_ao_fundo, args=(pasta,), daemon=True).start()
    return None, (f"Nunca li o projeto {Path(pasta).name} — estou lendo as "
                  "classes dele e treinando agora, leva uns 2 minutos. "
                  "Pergunta de novo daqui a pouco.")


# ══════════════════════════════════════════════════════════════════════
#  3. A RESPOSTA
# ══════════════════════════════════════════════════════════════════════
NOME_DA_OPERACAO = {
    "filtrar": "filtrar (Where)", "contar": "contar (Count)",
    "existe": "existe algum (Any)", "todos": "todos têm (All)",
    "primeiro": "o primeiro (FirstOrDefault)", "somar": "somar (Sum)",
    "projetar": "só uma coluna (Select)", "agrupar": "agrupar (GroupBy)",
    "ordenar_asc": "ordenar crescente (OrderBy)",
    "ordenar_desc": "ordenar decrescente (OrderByDescending)",
}


def responder(sessao, frase):
    """O texto que vai para o chat."""
    pasta = achar_projeto(sessao, frase)
    if pasta is None:
        return ("Para escrever a consulta eu preciso de um projeto C# — é de "
                "lá que saem os nomes das classes e das propriedades.\n\n"
                "Abre o projeto no painel, ou diz o nome dele na frase "
                "(\"no projeto Linq, soma o valor das transações\").")

    consultor, aviso = consultor_de(pasta)
    if consultor is None:
        return aviso

    d = consultor.explicar(frase)
    linq = d.get("linq")
    if not linq:
        # A REDE DIZ "NÃO SEI", E ISSO SE MOSTRA. Devolver uma consulta
        # inventada que compila é pior do que não responder: a pessoa
        # colaria no projeto e o erro só apareceria no resultado.
        return ("Entendi que você quer "
                f"{NOME_DA_OPERACAO.get(d.get('operacao'), d.get('operacao'))} "
                f"em `{d.get('lista')}`, mas não achei com que valor comparar.\n\n"
                "Diz o valor com todas as letras — por exemplo "
                f"\"{d.get('propriedade', 'status')} igual a ...\".")

    linhas = [f"```csharp\n{linq}\n```", "",
              f"  lista        {d['lista']}  ({d['classe']})",
              f"  operação     {NOME_DA_OPERACAO.get(d['operacao'], d['operacao'])}",
              f"  propriedade  {d['propriedade']}  ({d['tipo']})"]
    if d.get("filtro"):
        linhas.append(f"  filtro       {d['filtro']}")
    linhas.append("")
    linhas.append(f"Li as classes de `{pasta.name}`. Se eu errei a propriedade, "
                  "escreve o nome dela na frase que eu acerto.")
    return "\n".join(linhas)


def esquecer(pasta=None):
    """Solta o que está em memória — usado quando o projeto muda no disco."""
    with _TRAVA:
        if pasta is None:
            _ABERTOS.clear()
            _ESTADO.clear()
        else:
            _ABERTOS.pop(str(pasta), None)
            _ESTADO.pop(str(pasta), None)
