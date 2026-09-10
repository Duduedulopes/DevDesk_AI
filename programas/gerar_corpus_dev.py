"""Transforma o banco de falas em corpus de treino.

O QUE ESTE PROGRAMA FAZ, E POR QUE NÃO É SÓ COPIAR

O banco tem 374 falas escritas à mão. Treinar com 374 frases daria uma rede
que só reconhece exatamente aquelas — e ninguém escreve exatamente igual.
Este programa gera as VARIANTES de cada fala: sem acento, com erro de dedo,
abreviada, com enrolação na frente, com e sem interrogação.

A `base` VAI JUNTO EM CADA LINHA, E ISSO NÃO É ENFEITE

Todas as variantes de uma fala compartilham o mesmo campo `base`. A validação
cruzada agrupa por ele, de modo que "nao ta compilando" e "não está
compilando" caem sempre na MESMA dobra.

Sem esse agrupamento a acurácia sobe 27 pontos — medido no projeto da loja.
O modelo pareceria bom porque estaria sendo testado em variantes de frases
que já viu no treino, com outro nome.

O QUE NÃO É GERADO DE PROPÓSITO

Nada de sinônimo automático por dicionário. Trocar "erro" por "equívoco" faz
frase que ninguém diz, e enche o corpus de português de robô — que é
exatamente o que a rede aprenderia a esperar.
"""
import argparse
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, "dados")
from falas import FALAS, BURACOS

# Enrolação que as pessoas põem na frente. Curta, porque frase longa de
# cortesia é rara em quem está com problema na tela.
ANTES = ["", "", "", "", "por favor ", "pfv ", "ei ", "olha ", "cara ", "aí ",
         "rapaz ", "então ", "seguinte "]
DEPOIS = ["", "", "", "", "", " por favor", " pfv", " por gentileza", " aí", " rapidinho"]


def sem_acento(t):
    d = unicodedata.normalize("NFD", t)
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


def erro_de_dedo(t, sorte):
    """Um erro só, e do tipo que o teclado produz — não aleatório.

    Letra dobrada, letra comida, ou duas trocadas de ordem. É o que sai de
    quem digita rápido, e é para isso que os trigramas de caractere existem
    no modelo.
    """
    letras = [i for i, c in enumerate(t) if c.isalpha()]
    if len(letras) < 4:
        return t
    i = sorte.choice(letras[1:-1])
    modo = sorte.choice(("dobra", "come", "troca"))
    if modo == "dobra":
        return t[:i] + t[i] + t[i:]
    if modo == "come":
        return t[:i] + t[i + 1:]
    return t[:i] + t[i + 1] + t[i] + t[i + 2:]


def preencher(fala, sorte):
    """Troca {proj}, {arq}… por valores concretos."""
    for buraco, valores in BURACOS.items():
        alvo = "{" + buraco + "}"
        while alvo in fala:
            fala = fala.replace(alvo, sorte.choice(valores), 1)
    return fala


def variar(fala, sorte, quantas):
    """As formas em que a mesma fala chega."""
    saida = {fala}
    for _ in range(quantas * 3):
        if len(saida) >= quantas:
            break
        t = fala
        if sorte.random() < 0.45:
            t = sem_acento(t)
        if sorte.random() < 0.22:
            t = erro_de_dedo(t, sorte)
        if sorte.random() < 0.30:
            t = sorte.choice(ANTES) + t
        if sorte.random() < 0.22:
            t = t + sorte.choice(DEPOIS)
        if sorte.random() < 0.18:
            t = t + "?"
        if sorte.random() < 0.10:
            t = t.upper()
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            saida.add(t)
    return list(saida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--por_fala", type=int, default=14,
                    help="quantas variantes de cada fala escrita à mão")
    ap.add_argument("--saida", default="dados/perguntas_dev.jsonl")
    ap.add_argument("--semente", type=int, default=7)
    a = ap.parse_args()

    sorte = random.Random(a.semente)
    linhas, por_intencao, por_registro = [], {}, {}

    for intencao, registros in FALAS.items():
        for registro, falas in registros.items():
            for i, crua in enumerate(falas):
                base = f"{intencao}:{registro}:{i}"
                # O buraco é preenchido UMA vez por fala-base, não por
                # variante: senão "abre o AdminApp" e "abre o ClientApp"
                # teriam a mesma base e cairiam na mesma dobra sendo
                # frases diferentes de verdade.
                cheia = preencher(crua, sorte)
                for v in variar(cheia, sorte, a.por_fala):
                    linhas.append({"pergunta": v, "intencao": intencao,
                                   "base": base, "registro": registro})
                por_intencao[intencao] = por_intencao.get(intencao, 0) + a.por_fala
                por_registro[registro] = por_registro.get(registro, 0) + 1

    # Sem duplicata: a mesma frase em duas intenções ensinaria contradição.
    vistas, limpo = {}, []
    for l in linhas:
        chave = l["pergunta"].lower()
        if chave in vistas:
            continue
        vistas[chave] = True
        limpo.append(l)

    sorte.shuffle(limpo)
    saida = Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        for l in limpo:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")

    reais = {}
    for l in limpo:
        reais[l["intencao"]] = reais.get(l["intencao"], 0) + 1

    print(f"\n  {len(FALAS)} intenções · {sum(len(v) for d in FALAS.values() for v in d.values())} "
          f"falas escritas à mão")
    print(f"  → {len(limpo):,} frases ({len(linhas) - len(limpo)} duplicatas removidas)")
    print(f"  → {len(limpo)/len(FALAS):.0f} frases por intenção, em média\n")

    print("  por registro (falas-base):")
    for r, n in sorted(por_registro.items(), key=lambda x: -x[1]):
        print(f"     {r:8} {n:4}")

    magras = sorted(reais.items(), key=lambda x: x[1])[:6]
    print(f"\n  as mais magras — candidatas a ganhar mais falas no banco:")
    for nome, n in magras:
        print(f"     {nome:24} {n:4} frases")

    print(f"\n  gravado: {saida}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
