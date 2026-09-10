"""
Reúne num arquivo só todo o texto que os três projetos produziram.

POR QUE ISSO É O PASSO ZERO, E NÃO BUROCRACIA.

A tese do projeto é que comprimir é entender: se a rede aprende a prever o
próximo caractere, ela está guardando a estrutura da língua e do domínio em
84 mil pesos em vez de em 7 megabytes. A entropia cruzada que ela minimiza,
medida em bits por caractere, É a taxa de compressão — não é uma analogia.

Então antes de treinar qualquer coisa é preciso saber DUAS coisas:
  1. quanto texto nós temos de verdade
  2. quanto um compressor comum já consegue

Sem a segunda, "a rede comprimiu para 2,8 bits" não quer dizer nada.
"""
import io
import os, sys, json, gzip, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path

# As fontes, e o que cada uma ensina. A ordem importa: o que vem primeiro
# pesa mais na hora de cortar o corpus para experimentos rápidos.
FONTES = [
    ("caderno",  "Projetos_Eduardo/Rede-Neural/caderno",  {".md"},   "prosa técnica: o que quebrou e por quê"),
    ("docs",     "SO-Espacial/docs",                      {".md"},   "prosa técnica: decisões de arquitetura"),
    ("leiame",   "Projetos_Eduardo/LOJA AUTÔNOMA PRO",    {".md"},   "prosa técnica: os READMEs"),
    ("perguntas","Projetos_Eduardo/Rede-Neural/dados",    {".jsonl"},"linguagem natural imperfeita, rotulada"),
    ("python",   "Projetos_Eduardo/Rede-Neural",          {".py"},   "código: o motor da rede"),
    ("python",   "SO-Espacial",                           {".py"},   "código: visão computacional"),
    ("csharp",   "Projetos_Eduardo/LOJA AUTÔNOMA PRO",    {".cs", ".razor"}, "código: a loja"),
]

IGNORAR = {".git", "__pycache__", "obj", "bin", ".venv", "node_modules",
           "packages", ".vs", "dust3r", "notebooks"}


def varrer(base: Path, exts) -> list[Path]:
    achados = []
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in IGNORAR]
        for f in fn:
            if Path(f).suffix in exts:
                achados.append(Path(dp) / f)
    return sorted(achados)


def texto_de(p: Path) -> str:
    """JSONL vira só as frases; o resto vai como está."""
    try:
        cru = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if p.suffix != ".jsonl":
        return cru
    # Num .jsonl de corpus o que interessa é a frase humana, não a
    # pontuação do JSON — treinar a rede a prever aspas e chaves seria
    # gastar capacidade com a embalagem em vez do conteúdo.
    linhas = []
    for l in cru.splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if isinstance(d, dict):
            for chave in ("pergunta", "texto", "frase", "resposta"):
                if isinstance(d.get(chave), str):
                    linhas.append(d[chave])
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=os.path.expanduser("~/mnt"))
    ap.add_argument("--saida", default="dados/corpus.txt")
    args = ap.parse_args()

    raiz = Path(args.raiz)
    partes, resumo = [], []

    for nome, rel, exts, porque in FONTES:
        base = raiz / rel
        if not base.exists():
            print(f"  ! não achei {base}", file=sys.stderr)
            continue
        arquivos = varrer(base, exts)
        bloco = "\n".join(texto_de(p) for p in arquivos)
        if not bloco.strip():
            continue
        partes.append(bloco)
        resumo.append((nome, len(arquivos), len(bloco), porque))

    corpus = "\n".join(partes)
    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(corpus, encoding="utf-8")

    print(f"\n  {'fonte':10} {'arqs':>6} {'caracteres':>12}   o que ensina")
    print("  " + "─" * 74)
    for nome, n, c, porque in resumo:
        print(f"  {nome:10} {n:6} {c:12,}   {porque}")
    print("  " + "─" * 74)
    print(f"  {'TOTAL':10} {'':6} {len(corpus):12,}")

    alfabeto = sorted(set(corpus))
    print(f"\n  alfabeto: {len(alfabeto)} caracteres distintos")
    print(f"  gravado : {saida}  ({saida.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
