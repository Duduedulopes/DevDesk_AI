# -*- coding: utf-8 -*-
"""Treina as três redes que montam um projeto, e mede cada uma separado.

    python programas/treinar_compositor.py
    python programas/treinar_compositor.py --so-medir      não grava nada
    python programas/treinar_compositor.py --rapido        pula o deixa-um-fora

O QUE ESTE PROGRAMA MEDE, E POR QUE ASSIM

Com a quantidade de exemplos de ensino que cabe por mão não dá para
separar 60/20/20: 20% viraria um exemplo e meio, e a medição viraria
sorte. A medida honesta aqui é DEIXA-UM-FORA (leave-one-out): treina
uma vez por combinação, cada uma escondendo uma, e pergunta se a rede
recupera aquela que ela nunca viu.

É a mesma pergunta da divisão 60/20/20 — "quanto ela acerta no que não
viu" — feita do jeito que cabe no tamanho do dado. E é mais duro que o
60/20/20, porque cada teste é sobre um caso inteiro, não sobre frases
que se parecem com outras do treino.

AS COMBINAÇÕES GUARDADAS são o teste de composição de verdade. Para
elas não existe gabarito escrito — quem julga é o compilador.
"""
import argparse
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dados.ensino import ENSINO, COMBINACOES_NOVAS
from modelo.compositor import (FIM, Compositor, EscritorCondicionado,
                               RedeDaEstrutura, trocar)

RAIZ = Path(__file__).resolve().parent.parent
NOME_DE_TESTE = "oficina"


def titulo(t):
    print("\n" + "=" * 70 + f"\n  {t}\n" + "=" * 70)


# ══════════════════════════════════════════════════════════════════════
#  O DADO
# ══════════════════════════════════════════════════════════════════════
def catalogo(ensino):
    linguagens = sorted({e["linguagem"] for e in ensino})
    tipos = sorted({e["tipo"] for e in ensino})
    papeis = sorted({a["papel"] for e in ensino for a in e["arquivos"]})
    return linguagens, tipos, papeis


def linhas_estrutura(ensino):
    return [(e["linguagem"], e["tipo"], [a["papel"] for a in e["arquivos"]])
            for e in ensino]


def linhas_caminho(ensino):
    """(linguagem, tipo, papel) -> o caminho SEM a pasta do projeto.

    O `{nome}/` da frente sai fora: ele é sempre o mesmo e a rede
    gastaria metade da capacidade decorando um prefixo constante.
    """
    saida = []
    for e in ensino:
        for a in e["arquivos"]:
            c = a["caminho"]
            c = c[len("{nome}/"):] if c.startswith("{nome}/") else c
            saida.append((e["linguagem"], e["tipo"], a["papel"], c))
    return saida


def linhas_conteudo(ensino):
    return [(e["linguagem"], e["tipo"], a["papel"], a["conteudo"])
            for e in ensino for a in e["arquivos"]]


# ══════════════════════════════════════════════════════════════════════
#  1. ESTRUTURA
# ══════════════════════════════════════════════════════════════════════
def treinar_estrutura(linhas, cat, passos=4000, taxa=0.5, semente=7):
    linguagens, tipos, papeis = cat
    r = RedeDaEstrutura(linguagens, tipos, papeis, semente=semente)
    rng = random.Random(semente)
    for passo in range(1, passos + 1):
        t = taxa if passo <= passos * 0.6 else taxa * 0.3
        r.passo(rng.sample(linhas, min(8, len(linhas))), t)
    return r


def medir_estrutura(ensino, cat, passos):
    """Deixa-um-fora: um treino por combinação, cada um escondendo uma."""
    print(f"\n  {'escondido':<26}{'esperado':<34}{'saiu'}")
    print("  " + "-" * 92)
    exatos = certos = total = 0
    for i, e in enumerate(ensino):
        fora = [x for j, x in enumerate(ensino) if j != i]
        r = treinar_estrutura(linhas_estrutura(fora), cat, passos=passos)
        esperado = sorted(a["papel"] for a in e["arquivos"])
        saiu = sorted(p for p, _ in r.papeis_de(e["linguagem"], e["tipo"]))
        exatos += (saiu == esperado)
        certos += len(set(saiu) & set(esperado))
        total += len(esperado)
        marca = "ok " if saiu == esperado else "≠  "
        print(f"  {marca}{e['linguagem']+'+'+e['tipo']:<23}"
              f"{' '.join(esperado):<34}{' '.join(saiu)}")
    print(f"\n  estrutura inteira certa: {exatos}/{len(ensino)} = {exatos/len(ensino):.0%}")
    print(f"  papéis certos:           {certos}/{total} = {certos/total:.0%}")
    return exatos / len(ensino), certos / total


# ══════════════════════════════════════════════════════════════════════
#  2. CAMINHO
# ══════════════════════════════════════════════════════════════════════
def treinar_caminho(linhas, cat, passos=6000, lote=48, taxa=0.5, semente=7,
                    apagar=0.25):
    """DE TRÁS PARA FRENTE e com apagamento — os dois medidos, não achados.

    Ver `EscritorCondicionado.__init__` e `.passo`: a ordem invertida põe
    a extensão na posição onde só a etiqueta responde, e o apagamento tira
    a muleta do contexto. Juntos levaram a extensão certa de 58% para 79%.
    """
    linguagens, tipos, papeis = cat
    alfabeto = sorted({c for _, _, _, cam in linhas for c in cam} | {FIM})
    e = EscritorCondicionado(
        alfabeto,
        [("linguagem", linguagens), ("tipo", tipos), ("papel", papeis)],
        contexto=8, dimensao=12, oculta=96, semente=semente, ao_contrario=True)
    exemplos = [x for ling, tipo, papel, cam in linhas
                for x in e.exemplos_de(cam, [ling, tipo, papel])]
    rng = random.Random(semente)
    gr = np.random.default_rng(semente)
    for passo in range(1, passos + 1):
        t = taxa if passo <= passos * 0.6 else taxa * 0.3
        e.passo(rng.sample(exemplos, min(lote, len(exemplos))), t,
                apagar_contexto=apagar, r=gr)
    return e, len(exemplos)


def medir_caminho(ensino, cat, passos):
    """Deixa-um-fora por COMBINAÇÃO: esconde (ling, tipo) inteiro.

    DUAS CONTAS, e a segunda é a que vale mais. O caminho exato é uma
    medida dura demais: se `main.py` sai como `app.py`, isso conta como
    erro, mas nem uma pessoa sabe qual dos dois é "o certo" para um api
    python que ela nunca viu — o nome é indeterminado.

    Já a EXTENSÃO é determinada: arquivo python termina em `.py`, ponto.
    Errar a extensão é errar a linguagem, e isso não tem desculpa. Por
    isso as duas contas aparecem separadas.
    """
    print(f"\n  {'escondido':<24}{'papel':<12}{'esperado':<28}{'escreveu'}")
    print("  " + "-" * 92)
    certos = total = ext_certas = 0
    for i, e in enumerate(ensino):
        fora = [x for j, x in enumerate(ensino) if j != i]
        rede, _ = treinar_caminho(linhas_caminho(fora), cat, passos=passos)
        for a in e["arquivos"]:
            esperado = a["caminho"]
            esperado = esperado[len("{nome}/"):] if esperado.startswith("{nome}/") else esperado
            saiu = rede.escrever([e["linguagem"], e["tipo"], a["papel"]], maximo=120)
            ok = saiu == esperado
            ext_ok = Path(esperado).suffix == Path(saiu).suffix
            certos += ok
            ext_certas += ext_ok
            total += 1
            marca = "ok " if ok else ("ext" if ext_ok else "≠  ")
            print(f"  {marca}{e['linguagem']+'+'+e['tipo']:<21}"
                  f"{a['papel']:<12}{esperado:<28}{saiu}")
    print(f"\n  caminho exato:   {certos}/{total} = {certos/total:.0%}"
          "   (o nome é em parte indeterminado)")
    print(f"  extensão certa:  {ext_certas}/{total} = {ext_certas/total:.0%}"
          "   (esta é determinada: errar aqui é errar a linguagem)")
    return certos / total, ext_certas / total


# ══════════════════════════════════════════════════════════════════════
#  3. CONTEÚDO
# ══════════════════════════════════════════════════════════════════════
def treinar_conteudo(linhas, cat, passos=8000, lote=48, taxa=0.5, semente=7,
                     falar=False):
    linguagens, tipos, papeis = cat
    alfabeto = sorted({c for _, _, _, txt in linhas for c in txt} | {FIM})
    e = EscritorCondicionado(
        alfabeto,
        [("linguagem", linguagens), ("tipo", tipos), ("papel", papeis)],
        contexto=10, dimensao=14, oculta=160, semente=semente)
    exemplos = [x for ling, tipo, papel, txt in linhas
                for x in e.exemplos_de(txt, [ling, tipo, papel])]
    rng = random.Random(semente)
    if falar:
        print(f"\n  {len(exemplos):,} posições · {e.n_parametros:,} parâmetros "
              f"· alfabeto {len(alfabeto)}")
        print(f"  teto do chute: {math.log2(len(alfabeto)):.2f} bits/caractere\n")
        print(f"  {'passo':>7}{'bits/car (treino)':>20}{'tempo':>8}")
        print("  " + "-" * 36)
    t0 = time.time()
    for passo in range(1, passos + 1):
        t = taxa if passo <= passos * 0.5 else taxa * 0.3 if passo <= passos * 0.8 else taxa * 0.1
        perda = e.passo(rng.sample(exemplos, min(lote, len(exemplos))), t)
        if falar and passo % max(1, passos // 8) == 0:
            print(f"  {passo:>7}{perda:>20.3f}{time.time()-t0:>7.0f}s", flush=True)
    return e, len(exemplos)


COMPILAVEIS = {".py": "python", ".js": "javascript", ".cs": "csharp",
               ".php": "php", ".java": "java", ".cpp": "cpp"}


def compila(conteudo, extensao, pasta):
    """O compilador de verdade é o juiz. Devolve (ok, primeira_linha_do_erro).

    O ARQUIVO EM BRANCO NÃO PASSA. Na primeira rodada esta função disse
    "COMPILA" quatro vezes para conteúdo VAZIO: `php -l` aceita um
    arquivo só com espaço, e eu contei como acerto. A rede não tinha
    escrito nada e a medição me deu 4/4.

    Medição que aceita o vazio não mede nada. Então antes de chamar o
    compilador: se não tem corpo, é não.
    """
    from programas.colher_erros import compilar

    corpo = (conteudo or "").strip()
    if len(corpo) < 30:
        return False, f"vazio ou quase ({len(corpo)} caracteres)"
    ling = COMPILAVEIS.get(extensao.lower())
    if ling is None:
        return None, f"'{extensao}' não é código — não há compilador que julgue"
    if ling == "csharp" and "Main(" not in conteudo:
        return None, "biblioteca C# sem ponto de entrada — não dá para julgar"
    ok, msg = compilar(conteudo, ling, pasta)
    linha = (msg or "").strip().splitlines()
    return ok, (linha[0][:90] if linha else "")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--saida", default=str(RAIZ / "modelos" / "compositor.json"))
    p.add_argument("--so-medir", action="store_true")
    p.add_argument("--rapido", action="store_true",
                   help="pula o deixa-um-fora (que é a parte cara e a parte honesta)")
    p.add_argument("--passos-estrutura", type=int, default=4000)
    p.add_argument("--passos-caminho", type=int, default=5000)
    p.add_argument("--passos-conteudo", type=int, default=9000)
    p.add_argument("--limiar", type=float, default=0.5)
    a = p.parse_args()
    t0 = time.time()
    cat = catalogo(ENSINO)
    linguagens, tipos, papeis = cat

    titulo("O QUE FOI ENSINADO")
    print(f"\n  {len(ENSINO)} exemplos · {len(linguagens)} linguagens · "
          f"{len(tipos)} tipos · {len(papeis)} papéis")
    print(f"  linguagens: {' '.join(linguagens)}")
    print(f"  tipos:      {' '.join(tipos)}")
    print(f"  papéis:     {' '.join(papeis)}")
    print(f"\n  guardadas fora do ensino (o teste de composição):")
    for l, t in COMBINACOES_NOVAS:
        print(f"    {l}+{t}")

    medidas = {}

    # -- 1 ---------------------------------------------------------------
    titulo("REDE 1 - ESTRUTURA: (linguagem, tipo) -> quais papéis")
    if not a.rapido:
        print(f"\n  DEIXA-UM-FORA: {len(ENSINO)} treinos, cada um escondendo uma combinação.")
        ex, pa = medir_estrutura(ENSINO, cat, a.passos_estrutura)
        medidas["estrutura_inteira_certa"] = round(ex, 4)
        medidas["estrutura_papeis_certos"] = round(pa, 4)
    estrutura = treinar_estrutura(linhas_estrutura(ENSINO), cat,
                                  passos=a.passos_estrutura)
    print(f"\n  rede final treinada nos {len(ENSINO)}: "
          f"{estrutura.n_parametros:,} parâmetros")

    # -- 2 ---------------------------------------------------------------
    titulo("REDE 2 - CAMINHO: (linguagem, tipo, papel) -> onde o arquivo fica")
    if not a.rapido:
        print("\n  DEIXA-UM-FORA de novo, agora escondendo a combinação inteira.")
        ca, ex = medir_caminho(ENSINO, cat, a.passos_caminho)
        medidas["caminho_exato"] = round(ca, 4)
        medidas["caminho_extensao_certa"] = round(ex, 4)
    caminho, n_cam = treinar_caminho(linhas_caminho(ENSINO), cat,
                                     passos=a.passos_caminho)
    print(f"\n  rede final: {caminho.n_parametros:,} parâmetros · "
          f"{n_cam:,} posições de treino")

    # -- 3 ---------------------------------------------------------------
    titulo("REDE 3 - CONTEUDO: (linguagem, tipo, papel) -> o código")
    print("\n  Primeiro a medida honesta: dois exemplos ficam FORA do treino")
    print("  e a rede é medida em bits por caractere sobre eles.")
    fora_nomes = [("php", "biblioteca"), ("python", "site")]
    dentro = [e for e in ENSINO if (e["linguagem"], e["tipo"]) not in fora_nomes]
    fora = [e for e in ENSINO if (e["linguagem"], e["tipo"]) in fora_nomes]
    prova, _ = treinar_conteudo(linhas_conteudo(dentro), cat,
                                passos=a.passos_conteudo, falar=True)
    ex_fora = [x for ling, tipo, papel, txt in linhas_conteudo(fora)
               for x in prova.exemplos_de(txt, [ling, tipo, papel])]
    ex_dentro = [x for ling, tipo, papel, txt in linhas_conteudo(dentro)
                 for x in prova.exemplos_de(txt, [ling, tipo, papel])]
    b_fora = prova.bits_por_caractere(ex_fora, salto=7)
    b_dentro = prova.bits_por_caractere(ex_dentro, salto=37)
    teto = math.log2(len(prova.alfabeto))
    print(f"\n  bits por caractere:")
    print(f"    no que treinou       {b_dentro:>7.3f}")
    print(f"    no que NÃO treinou   {b_fora:>7.3f}   ← a medida que vale")
    print(f"    teto do chute        {teto:>7.3f}")
    print(f"    vão (decoreba)       {b_fora - b_dentro:>7.3f}")
    medidas["conteudo_bits_treino"] = round(b_dentro, 3)
    medidas["conteudo_bits_fora"] = round(b_fora, 3)
    medidas["conteudo_teto_bits"] = round(teto, 3)

    print("\n  E agora a pergunta que importa: o que ela ESCREVE compila?\n")
    pasta = Path(tempfile.mkdtemp(prefix="conteudo_"))
    compilou = tentou = 0
    # A EXTENSÃO VEM DO CAMINHO DO ARQUIVO, não da linguagem. Um README
    # num projeto php é .md, não .php — na primeira versão eu derivava
    # da linguagem e mandava o README para o compilador de PHP.
    for ling, tipo, papel, _ in linhas_conteudo(fora):
        cam = next(a["caminho"] for e in fora
                   if e["linguagem"] == ling and e["tipo"] == tipo
                   for a in e["arquivos"] if a["papel"] == papel)
        ext = Path(cam).suffix
        texto = prova.escrever([ling, tipo, papel], maximo=2500)
        ok, msg = compila(trocar(texto, NOME_DE_TESTE), ext, pasta)
        if ok is not None:
            tentou += 1
            compilou += bool(ok)
        estado = "COMPILA" if ok else ("não julgável" if ok is None else "não compila")
        print(f"    {ling}+{tipo}+{papel:<11} {ext:<6} {len(texto):>5} car · {estado}")
        if msg and ok is False:
            print(f"       {msg}")
        primeira = (texto.strip().splitlines() or [""])[0]
        print(f"       começa com: {primeira[:60]!r}")
    shutil.rmtree(pasta, ignore_errors=True)
    medidas["conteudo_compilou"] = f"{compilou}/{tentou}" if tentou else "0/0"
    print(f"\n  compilou: {compilou}/{tentou}")

    print(f"\n  Agora a rede final, treinada nos {len(ENSINO)}.")
    conteudo, n_con = treinar_conteudo(linhas_conteudo(ENSINO), cat,
                                       passos=a.passos_conteudo, falar=True)

    # -- a memoria --------------------------------------------------------
    memoria = {f"{e['linguagem']}|{e['tipo']}|{a_['papel']}": a_["conteudo"]
               for e in ENSINO for a_ in e["arquivos"]}
    # Onde cada forma morava, e que extensões cada linguagem usa. Sai do
    # ensino, não de lista escrita à mão — e é o que deixa o compositor
    # conferir a si mesmo (ver `Compositor.extensao_bate`).
    caminhos = {f"{e['linguagem']}|{e['tipo']}|{a_['papel']}": a_["caminho"]
                for e in ENSINO for a_ in e["arquivos"]}
    extensoes, extensoes_do_tipo = {}, {}
    for e in ENSINO:
        for a_ in e["arquivos"]:
            ext = Path(a_["caminho"]).suffix.lower()
            extensoes.setdefault(e["linguagem"], set()).add(ext)
            extensoes_do_tipo.setdefault(e["tipo"], set()).add(ext)
    extensoes = {l: sorted(v) for l, v in extensoes.items()}
    extensoes_do_tipo = {t: sorted(v) for t, v in extensoes_do_tipo.items()}
    print("\n  extensões colhidas do ensino — a conferência do compositor:")
    print("    por linguagem:")
    for l, v in sorted(extensoes.items()):
        print(f"      {l:<12}{' '.join(x or '(sem)' for x in v)}")
    print("    por tipo:")
    for t, v in sorted(extensoes_do_tipo.items()):
        print(f"      {t:<12}{' '.join(x or '(sem)' for x in v)}")

    if a.so_medir:
        titulo("NADA FOI GRAVADO (--so-medir)")
        print(f"\n  {time.time()-t0:.0f}s")
        return 0

    d = {"estrutura": estrutura.para_dicionario(),
         "caminho": caminho.para_dicionario(),
         "conteudo": conteudo.para_dicionario(),
         "memoria": memoria,
         "caminhos": caminhos,
         "extensoes": extensoes,
         "extensoes_do_tipo": extensoes_do_tipo,
         "limiar": a.limiar,
         "medido": {**medidas,
                    "protocolo": f"deixa-um-fora sobre as {len(ENSINO)} combinações "
                                 "ensinadas; conteúdo com 2 combinações fora",
                    "n_exemplos_ensino": len(ENSINO),
                    "n_posicoes_conteudo": n_con,
                    "combinacoes_guardadas": [list(x) for x in COMBINACOES_NOVAS],
                    "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S")}}
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    titulo("GRAVADO")
    print(f"\n  {a.saida}")
    print(f"     3 redes · {len(memoria)} formas na memória · "
          f"{time.time()-t0:.0f}s\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
