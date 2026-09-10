# -*- coding: utf-8 -*-
"""Gera o corpus de CRIAR PROJETO — com as etiquetas de campo por peça."""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    python programas/gerar_corpus_criar.py

POR QUE AS ETIQUETAS SAEM DE GRAÇA

Anotar 20 mil frases à mão, marcando onde está a linguagem e onde está o
nome, seria semanas de trabalho. Não precisa: quem MONTA a frase sabe onde
pôs cada coisa. O gerador escreve "cria um projeto {ling} chamado {nome}" e
já sabe que a peça na posição do {ling} é LINGUAGEM.

O rótulo não é uma opinião sobre a frase — é a receita que a construiu.

AS QUATRO ETIQUETAS

    LING   a linguagem      python · c# · java · html
    TIPO   o que é          console · api · site · biblioteca · jogo
    NOME   como se chama    calculadora · MeuApp · loja-online
    O      o resto          "cria", "um", "projeto", "chamado", "pra mim"

O TESTE QUE SEPARA APRENDIZADO DE DECORAR

Se o corpus tem as mesmas linguagens no treino e no teste, uma rede pode
gabaritar decorando a lista — e aí ela é um dicionário com passos a mais,
que é exatamente o que a gente não quer.

Por isso este gerador separa as linguagens em dois grupos:

    LINGUAGENS_TREINO   entram no corpus de treino
    LINGUAGENS_NOVAS    NÃO entram. Só aparecem no corpus de teste.

Uma rede que etiqueta `rust` como LINGUAGEM sem nunca ter visto a palavra
aprendeu o LUGAR — "aquilo que vem depois de 'em' numa frase de criar
projeto" — e não a palavra. É a diferença entre entender e consultar.

O NOME É O CAMPO DIFÍCIL, E DE PROPÓSITO

Linguagem e tipo são vocabulário quase fechado. Nome é aberto: pode ser
qualquer coisa que a pessoa inventar. Por isso os nomes do treino e os do
teste também são conjuntos separados — o mesmo teste, aplicado ao campo
onde ele é mais difícil.
"""
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ── as linguagens ─────────────────────────────────────────────────────
# Escritas como a pessoa escreve, e não como o site oficial escreve.
LINGUAGENS_TREINO = {
    "python":     ["python", "py", "pyton", "phyton", "python3"],
    "csharp":     ["c#", "csharp", "c sharp", "dotnet", ".net", "c-sharp"],
    "javascript": ["javascript", "js", "java script", "node", "nodejs"],
    "html":       ["html", "htm", "html5"],
    "css":        ["css", "css3"],
    "php":        ["php", "php8"],
    # SQL e LINQ entram como qualquer outra: uma linha de DADO.
    # Foi para isto que o desenho não tem dicionário no código — se
    # tivesse, acrescentar linguagem seria mexer em lógica.
    "sql":        ["sql", "t-sql", "tsql", "mysql", "postgres", "postgresql",
                   "sql server", "sqlserver", "banco de dados", "database",
                   "script sql", "consulta sql"],
    # LINQ não é linguagem de projeto — é consulta dentro do C#. Ela entra
    # aqui porque a REDE precisa reconhecer a peça; o que o molde faz com
    # isso (um projeto C# com exemplos de LINQ) é decisão da camada de
    # baixo, e está anotada lá.
    "linq":       ["linq", "linq to sql", "linq to objects", "linq to entities",
                   "consulta linq"],
}
LINGUAGENS_NOVAS = {          # NUNCA entram no treino
    "java":       ["java", "jav"],
    "cpp":        ["c++", "cpp", "c mais mais"],
    "rust":       ["rust"],
    "go":         ["go", "golang"],
    "kotlin":     ["kotlin", "kt"],
    "ruby":       ["ruby", "rb"],
}

# IDIOMA É DADO, NÃO CÓDIGO.
# Português e inglês são duas listas de moldes, e nada além disso muda.
# Acrescentar espanhol é acrescentar uma chave aqui e uma em MOLDES —
# nenhuma linha de lógica. Foi por isso que os campos viraram marcas
# ({L}, {T}, {N}) em vez de posições fixas: a ordem das palavras muda de
# um idioma para o outro, mas a marca acompanha.
TIPOS = {
    "console":    ["console", "de console", "terminal", "de linha de comando", "cli",
                   "command line", "console app", "terminal app"],
    "api":        ["api", "web api", "rest", "api rest", "servico",
                   "rest api", "service", "backend"],
    "site":       ["site", "pagina", "pagina web", "web", "front",
                   "website", "web page", "landing page", "front end"],
    "biblioteca": ["biblioteca", "lib", "pacote", "modulo",
                   "library", "package", "module"],
    "jogo":       ["jogo", "game", "joguinho", "little game"],
}

NOMES_TREINO = [
    "calculadora", "agenda", "loja", "MeuApp", "controle-de-estoque", "blog",
    "conversor", "todo", "cadastro", "financeiro", "api-pedidos", "portfolio",
    "chat", "relatorios", "estudo", "teste1", "sistema_escola", "quiz",
    "cronometro", "bloco-de-notas", "clima", "receitas", "biblioteca-livros",
]
NOMES_TESTE = [                # nomes que o treino nunca viu
    "oficina", "veterinaria", "PontoDigital", "gestao-frota", "diario",
    "conta_luz", "sorteador", "pomodoro", "leilao", "cardapio",
]

# ── os moldes de frase ────────────────────────────────────────────────
# {L} linguagem · {T} tipo · {N} nome. O que não está entre chaves é O.
MOLDES_POR_IDIOMA = {
"pt": [
    "cria um projeto em {L}",
    "cria um projeto {L} chamado {N}",
    "criar projeto {L}",
    "faz um projeto novo em {L} chamado {N}",
    "faz pra mim um projeto {T} em {L}",
    "quero um projeto {L} do tipo {T}",
    "quero criar um {T} em {L} chamado {N}",
    "monta um {T} em {L}",
    "monta um projeto {L} {T} com o nome {N}",
    "novo projeto {L}",
    "novo projeto em {L} chamado {N}",
    "comeca um projeto {L} pra mim",
    "preciso de um {T} em {L}",
    "abre um projeto novo de {L}",
    "gera um projeto {L} de nome {N}",
    "cria a estrutura de um projeto {L}",
    "me cria um {T} {L} chamado {N}",
    "inicia um projeto em {L} chamado {N}",
    "queria comecar um projeto {L}",
    "faz um {T} em {L} chamado {N} por favor",
    "cria projeto {L} {T} {N}",
    "sobe um projeto novo em {L}",
    "monta a base de um {T} em {L}",
    "cria um {T} novo em {L} com o nome {N}",
    "projeto novo {L} chamado {N}",
    "quero começar um {T} em {L}",
    "prepara um projeto {L} pra mim chamado {N}",
    "arma um projeto {T} em {L}",
    "cria um programa em {L}",
    "cria um programa {L} chamado {N}",
    "escreve um programa em {L} chamado {N}",
    "faz um programinha em {L}",
],
"en": [
    "create a project in {L}",
    "create a {L} project called {N}",
    "new {L} project",
    "new project in {L} named {N}",
    "make me a {T} in {L}",
    "i want a {L} project of type {T}",
    "i want to create a {T} in {L} called {N}",
    "set up a {T} in {L}",
    "set up a {L} {T} project named {N}",
    "start a new {L} project",
    "start a project in {L} called {N}",
    "please create a {L} project",
    "i need a {T} in {L}",
    "open a new {L} project",
    "generate a {L} project named {N}",
    "create the structure of a {L} project",
    "build me a {L} {T} called {N}",
    "initialize a project in {L} called {N}",
    "i would like to start a {L} project",
    "make a {T} in {L} called {N} please",
    "create {L} {T} project {N}",
    "spin up a new {L} project",
    "scaffold a {T} in {L}",
    "create a new {T} in {L} with the name {N}",
    "new project {L} called {N}",
    "i want to start a {T} in {L}",
    "prepare a {L} project for me called {N}",
    "bootstrap a {T} project in {L}",
    "write a program in {L}",
    "write a {L} program called {N}",
    "code me a program in {L} named {N}",
    "small program in {L}",
],
}

ENCHIMENTO = {
"pt": (["", "", "", "", "por favor ", "rapaz ", "entao ", "olha ", "ei ",
        "bom dia ", "cara ", "eh ", "ó ", "tipo assim "],
       ["", "", "", "", "", " por favor", " agora", " pra mim", " valeu",
        " rapidinho", " se der", " obrigado", " ai"]),
"en": (["", "", "", "", "please ", "hey ", "so ", "look ", "ok ",
        "good morning ", "man ", "uh ", "hi ", "quick one "],
       ["", "", "", "", "", " please", " now", " for me", " thanks",
        " real quick", " if you can", " thank you", " ok"]),
}


# ── as variações que imitam gente digitando ───────────────────────────
def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn")


VIZINHAS = {"a": "sq", "e": "wr", "i": "ou", "o": "ip", "u": "yi", "c": "xv",
            "s": "ad", "n": "bm", "r": "et", "t": "ry", "l": "k", "m": "n"}


def erro_de_dedo(t, rng):
    """Erro com forma de teclado, e não ruído aleatório.

    Dobrar letra, comer letra, trocar por vizinha no teclado. Um erro
    sorteado de todo o alfabeto não se parece com o que gente digita.
    """
    if len(t) < 4:
        return t
    i = rng.randrange(len(t))
    c = t[i]
    if not c.isalpha():
        return t
    qual = rng.random()
    if qual < 0.34:
        return t[:i] + c + c + t[i:]
    if qual < 0.67:
        return t[:i] + t[i + 1:]
    return t[:i] + rng.choice(VIZINHAS.get(c.lower(), c)) + t[i + 1:]


def etiquetar(molde, ling_txt, tipo_txt, nome_txt):
    """Monta a frase E as etiquetas, peça por peça.

    Substitui os campos por marcas de uma palavra, monta a frase, e depois
    troca cada marca pelas palavras do campo — assim uma linguagem escrita
    com duas palavras ("c sharp", "java script") vira DUAS peças com a
    etiqueta LING, e não uma peça com espaço no meio.
    """
    texto = molde.replace("{L}", "\x01").replace("{T}", "\x02").replace("{N}", "\x03")
    pecas, etiquetas = [], []
    for palavra in texto.split():
        if palavra == "\x01":
            for p in ling_txt.split():
                pecas.append(p); etiquetas.append("LING")
        elif palavra == "\x02":
            for p in tipo_txt.split():
                pecas.append(p); etiquetas.append("TIPO")
        elif palavra == "\x03":
            for p in nome_txt.split():
                pecas.append(p); etiquetas.append("NOME")
        else:
            pecas.append(palavra); etiquetas.append("O")
    return pecas, etiquetas


def gerar(linguagens, nomes, semente, por_molde=8):
    rng = random.Random(semente)
    saida, vistos = [], set()
    for idioma, moldes in sorted(MOLDES_POR_IDIOMA.items()):
      ANTES, DEPOIS = ENCHIMENTO[idioma]
      for ling, escritas in sorted(linguagens.items()):
        for i, molde in enumerate(moldes):
            for _ in range(por_molde):
                ling_txt = rng.choice(escritas)
                tipo_chave = rng.choice(list(TIPOS))
                tipo_txt = rng.choice(TIPOS[tipo_chave])
                nome_txt = rng.choice(nomes)

                pecas, etiquetas = etiquetar(molde, ling_txt, tipo_txt, nome_txt)
                frase = " ".join(pecas)

                # As mesmas variações do corpus de intenção: sem acento,
                # erro de dedo, maiúscula, enchimento antes e depois.
                if rng.random() < 0.30:
                    frase = sem_acento(frase)
                if rng.random() < 0.18:
                    frase = erro_de_dedo(frase, rng)
                    pecas = frase.split()
                    if len(pecas) != len(etiquetas):
                        continue          # o erro mudou a contagem: descarta
                if rng.random() < 0.06:
                    frase = frase.upper()
                    pecas = frase.split()

                antes, depois = rng.choice(ANTES), rng.choice(DEPOIS)
                if antes:
                    extra = antes.split()
                    pecas = extra + pecas; etiquetas = ["O"] * len(extra) + etiquetas
                if depois:
                    extra = depois.split()
                    pecas = pecas + extra; etiquetas = etiquetas + ["O"] * len(extra)

                frase = " ".join(pecas)
                if frase in vistos:
                    continue
                vistos.add(frase)
                saida.append({
                    "frase": frase, "pecas": pecas, "etiquetas": etiquetas,
                    "idioma": idioma,
                    "linguagem": ling, "tipo": tipo_chave, "nome": nome_txt,
                    # `base` = o molde. Serve para a divisão agrupada, do mesmo
                    # jeito que no corpus de intenção: variantes de um molde
                    # não podem cair dos dois lados.
                    "base": f"{idioma}:{ling}:{i}",
                })
    return saida


def main():
    treino = gerar(LINGUAGENS_TREINO, NOMES_TREINO, semente=11)
    novas = gerar(LINGUAGENS_NOVAS, NOMES_TESTE, semente=22)

    conf = lambda d: len({p for e in d for p, t in zip(e["pecas"], e["etiquetas"]) if t == "LING"})
    print(f"\n  corpus de treino : {len(treino):>6,} frases · "
          f"{len(LINGUAGENS_TREINO)} linguagens · {conf(treino)} formas de escrevê-las")
    print(f"  corpus NOVO      : {len(novas):>6,} frases · "
          f"{len(LINGUAGENS_NOVAS)} linguagens que o treino nunca vê")
    print(f"  idiomas          : {', '.join(sorted(MOLDES_POR_IDIOMA))}"
          f"   ({sum(len(m) for m in MOLDES_POR_IDIOMA.values())} moldes)   "
          f"tipos: {len(TIPOS)}")
    for idi in sorted(MOLDES_POR_IDIOMA):
        n = sum(1 for e in treino if e["idioma"] == idi)
        print(f"    {idi}: {n:>6,} frases no treino")

    for nome, dados in (("criar_treino", treino), ("criar_novas", novas)):
        alvo = RAIZ / "dados" / f"{nome}.jsonl"
        with open(alvo, "w", encoding="utf-8") as f:
            for e in dados:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"  ✓ {alvo}")

    print("\n  amostra do treino:")
    for e in random.Random(3).sample(treino, 4):
        marcas = " ".join(f"{p}[{t}]" if t != "O" else p
                          for p, t in zip(e["pecas"], e["etiquetas"]))
        print(f"    {marcas}")
    print("\n  amostra das NOVAS (nenhuma linguagem daqui entra no treino):")
    for e in random.Random(5).sample(novas, 4):
        marcas = " ".join(f"{p}[{t}]" if t != "O" else p
                          for p, t in zip(e["pecas"], e["etiquetas"]))
        print(f"    {marcas}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
