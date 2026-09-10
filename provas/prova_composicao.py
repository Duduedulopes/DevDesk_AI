# -*- coding: utf-8 -*-
"""A PROVA: montar combinações que nunca foram ensinadas.

    python provas/prova_composicao.py
    python provas/prova_composicao.py --escrever /tmp/saida    cria de verdade

POR QUE ESTA PROVA EXISTE

Um sistema que monta `python+console` depois de ter visto `python+console`
não provou nada — provou que sabe copiar. A pergunta que vale é outra:

    javascript+api nunca foi ensinado. javascript foi (em console e
    biblioteca) e api foi (em python, php e csharp). Ele junta as duas
    metades, ou devolve vazio?

As guardadas estão em `dados/ensino.py`, de propósito com dificuldade
diferente:

    python+biblioteca   todo (linguagem, papel) já visto em python.
                        Só a ESTRUTURA é nova. O caso fácil.
    javascript+api      rota em javascript nunca vista.
    javascript+site     pagina e estilo em javascript nunca vistos.
                        O caso difícil.

(csharp+api era uma delas; a junção dela depois de C#+console e
python+api é que ensinou ao sistema que C# escreve api, então ela
entrou para o ENSINO e saiu da prova.)

QUEM JULGA É O COMPILADOR, NÃO EU

Não existe gabarito escrito para estas — se existisse, elas estariam no
ensino. Então o que se mede é o que dá para medir sem opinião: a árvore
saiu? os caminhos fazem sentido para a linguagem? o que for código
compila?
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dados.ensino import COMBINACOES_NOVAS, ENSINO
from modelo.compositor import Compositor

RAIZ = Path(__file__).resolve().parent.parent
COMPILAVEIS = {".py": "python", ".js": "javascript", ".cs": "csharp",
               ".php": "php"}


def julgar(arquivo, pasta, irmaos_plano=None):
    """(veredito, motivo). None = não há compilador que julgue isto."""
    from programas.colher_erros import compilar
    corpo = arquivo["conteudo"]
    ext = Path(arquivo["caminho"]).suffix.lower()
    if not corpo.strip():
        return False, "vazio"
    ling = COMPILAVEIS.get(ext)
    if ling is None:
        return None, f"'{ext or 'sem extensão'}' não tem compilador"
    if ling == "csharp" and "Main(" not in corpo:
        return None, "C# sem ponto de entrada"
    outros = None
    if ling == "csharp" and irmaos_plano:
        # igual ao `dotnet build`: os .cs do MESMO projeto vão juntos —
        # Program.cs pode chamar Rotas.cs sem depender de ordem de arquivo.
        outros = {irm["caminho"]: irm["conteudo"] for irm in irmaos_plano
                  if irm is not arquivo
                  and Path(irm["caminho"]).suffix.lower() == ".cs"
                  and irm["conteudo"].strip()}
    ok, msg = compilar(corpo, ling, pasta, outros=outros)
    primeira = (msg or "").strip().splitlines()
    return ok, (primeira[0][:80] if primeira else "")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modelo", default=str(RAIZ / "modelos" / "compositor.json"))
    p.add_argument("--escrever", default=None,
                   help="cria a árvore de verdade nesta pasta")
    p.add_argument("--nome", default="oficina")
    p.add_argument("--gerar", action="store_true",
                   help="usa a rede 3 (geração) em vez da memória")
    a = p.parse_args()

    c = Compositor(a.modelo)
    print("\n" + "═" * 70)
    print(f"  PROVA DE COMPOSIÇÃO — {len(COMBINACOES_NOVAS)} combinações que nunca foram ensinadas")
    print("═" * 70)
    m = c.medido
    if m:
        print(f"\n  o modelo diz de si mesmo:")
        print(f"    estrutura inteira certa (deixa-um-fora): "
              f"{m.get('estrutura_inteira_certa', '?')}")
        print(f"    caminho exato (deixa-um-fora):           "
              f"{m.get('caminho_exato', '?')}")
        print(f"    conteúdo, bits/car no que não treinou:   "
              f"{m.get('conteudo_bits_fora', '?')}  "
              f"(teto {m.get('conteudo_teto_bits', '?')})")

    pasta = Path(tempfile.mkdtemp(prefix="prova_"))
    resumo = []
    for linguagem, tipo in COMBINACOES_NOVAS:
        ensinada = any(e["linguagem"] == linguagem and e["tipo"] == tipo
                       for e in ENSINO)
        print("\n" + "─" * 70)
        print(f"  {linguagem} + {tipo}"
              + ("   ← ATENÇÃO: esta ESTÁ no ensino, não vale como prova"
                 if ensinada else ""))
        print("─" * 70)
        # UM NOME POR COMBINAÇÃO. Com o mesmo nome para as quatro, os
        # quatro projetos caem na mesma pasta e um sobrescreve o outro —
        # aconteceu, e o relatório ainda dizia que tinha criado quatro.
        plano = c.planejar(linguagem, tipo, f"{a.nome}_{linguagem}_{tipo}",
                           gerar_conteudo=a.gerar)
        if "erro" in plano:
            print(f"    {plano}")
            continue
        print(f"\n    pastas: {', '.join(plano['pastas']) or '(só a raiz)'}")
        print(f"\n    {'arquivo':<30}{'papel':<12}{'conf':>6}  "
              f"{'origem':<22}{'compila'}")
        certos = julgados = 0
        irmaos_cs = [outr for outr in plano["arquivos"]
                     if Path(outr["caminho"]).suffix.lower() == ".cs"]
        for arq in plano["arquivos"]:
            ok, motivo = julgar(arq, pasta, irmaos_plano=irmaos_cs)
            if ok is not None:
                julgados += 1
                certos += bool(ok)
            estado = ("sim" if ok else "NÃO — " + motivo) if ok is not None else "—"
            print(f"    {arq['caminho']:<30}{arq['papel']:<12}"
                  f"{arq['confianca']:>6.2f}  {arq['origem']:<22}{estado}")
        if plano["perguntas"]:
            print(f"\n    ele pergunta:")
            for q in plano["perguntas"]:
                print(f"      · {q}")
        resumo.append((linguagem, tipo, len(plano["arquivos"]), certos, julgados,
                       len(plano["perguntas"])))

        if a.escrever:
            feito = c.escrever_no_disco(plano, a.escrever)
            print(f"\n    escrito em {feito['raiz']}: "
                  f"{len(feito['criados'])} arquivos")
            for cam, por in feito["pulados"]:
                print(f"      pulado {cam}: {por}")

    shutil.rmtree(pasta, ignore_errors=True)
    print("\n" + "═" * 70)
    print("  RESUMO")
    print("═" * 70)
    print(f"\n  {'combinação':<26}{'arquivos':>9}{'compila':>10}{'perguntas':>11}")
    for l, t, n, c_, j, q in resumo:
        print(f"  {l+'+'+t:<26}{n:>9}{f'{c_}/{j}':>10}{q:>11}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
