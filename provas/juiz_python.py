# -*- coding: utf-8 -*-
"""O JUIZ DO PYTHON — e o que ele pode e não pode julgar.

O `juiz_csharp` tem o `dotnet build`: uma resposta seca, sim ou não, para
qualquer arquivo. Em Python não existe esse botão, e fingir que existe
seria a pior coisa que este arquivo poderia fazer. Então ele é explícito
sobre as três faixas:

    SINTAXE      `ast.parse`. Julga com a MESMA autoridade do compilador:
                 ou o arquivo é Python válido ou não é. Sem risco nenhum
                 — nada roda.

    IMPORTAÇÃO   importar o módulo. Pega `ModuleNotFoundError`, nome que
                 não existe no corpo do arquivo, erro de indentação que
                 só aparece ao carregar. Mas IMPORTAR EXECUTA O CÓDIGO do
                 corpo do módulo, e por isso não é o padrão: é preciso
                 pedir. Um `os.remove` solto no topo de um arquivo roda
                 quando você importa, e o juiz não tem como saber antes.

    EXECUÇÃO     um `KeyError` na linha 300, dentro de uma função que só
                 é chamada com certos dados. AQUI NÃO HÁ JUIZ. Dá para
                 ler o traceback e dizer qual é o problema; não dá para
                 PROVAR que o conserto resolveu sem rodar o programa com
                 os dados que quebraram — e esses dados são seus, não
                 meus.

POR QUE A DIFERENÇA ESTÁ ESCRITA EM VEZ DE ESCONDIDA

Porque um conserto "provado" e um conserto "achado" valem coisas
diferentes na hora de você decidir se grava. Misturar os dois numa lista
só faria o segundo pegar carona na confiança do primeiro.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

# o que cada faixa vale quando a resposta chega
PROVADO = "provado"       # o juiz rodou e disse
DIAGNOSTICO = "achado"    # li o erro, não tenho como provar o conserto


class Erro:
    """Um erro, no mesmo formato para C# e para Python.

    `codigo` é o que faz as duas linguagens caberem na mesma rede:
    `CS1002` de um lado, `SyntaxError`/`NameError` do outro. São rótulos
    de famílias diferentes, mas são rótulos — e é disso que a cabeça da
    operação precisa.
    """

    __slots__ = ("arquivo", "linha", "coluna", "codigo", "mensagem",
                 "texto", "faixa")

    def __init__(self, arquivo, linha, coluna, codigo, mensagem,
                 texto="", faixa=PROVADO):
        self.arquivo = str(arquivo)
        self.linha = int(linha or 0)
        self.coluna = int(coluna or 0)
        self.codigo = codigo
        self.mensagem = (mensagem or "").strip()
        self.texto = texto            # a linha do código, como está escrita
        self.faixa = faixa

    def __repr__(self):
        return (f"{Path(self.arquivo).name}({self.linha},{self.coluna}): "
                f"{self.codigo}: {self.mensagem}")

    def como_dicionario(self):
        return {k: getattr(self, k) for k in self.__slots__}


def _linha_de(caminho, n):
    try:
        ls = Path(caminho).read_text(encoding="utf-8", errors="replace").splitlines()
        return ls[n - 1] if 1 <= n <= len(ls) else ""
    except OSError:
        return ""


# ══════════════════════════════════════════════════════════════════════
#  SINTAXE — o juiz de verdade
# ══════════════════════════════════════════════════════════════════════
def erros_de_sintaxe(caminho):
    """[] quando o arquivo é Python válido. Nada é executado.

    O `ast.parse` para no PRIMEIRO erro de sintaxe — não existe "lista de
    erros de sintaxe" em Python como existe em C#. Isso na verdade ajuda:
    o primeiro é o verdadeiro, e os outros, se houvesse, seriam cascata.
    """
    caminho = Path(caminho)
    try:
        fonte = caminho.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [Erro(caminho, 0, 0, type(e).__name__, str(e))]
    try:
        ast.parse(fonte, filename=str(caminho))
        return []
    except SyntaxError as e:
        return [Erro(caminho, e.lineno or 0, e.offset or 0,
                     type(e).__name__, e.msg,
                     texto=(e.text or _linha_de(caminho, e.lineno or 0)).rstrip())]


def compila(caminho):
    """True quando o arquivo é Python válido. É este o veredito do juiz."""
    return not erros_de_sintaxe(caminho)


# ══════════════════════════════════════════════════════════════════════
#  IMPORTAÇÃO — julga, mas EXECUTA
# ══════════════════════════════════════════════════════════════════════
_TRACE = re.compile(r'File "(?P<arq>[^"]+)", line (?P<ln>\d+)')


def erros_de_importacao(caminho, raiz=None, tempo=30):
    """Importa o módulo num processo à parte e devolve o que estourou.

    NUM PROCESSO À PARTE, e isso não é detalhe: o código do corpo do
    módulo roda de verdade. Num subprocesso, um `sys.exit()` ou um
    `while True` no topo do arquivo derrubam o subprocesso e não o
    DevDesk — e o tempo limite corta o que travar.
    """
    caminho = Path(caminho).resolve()
    raiz = Path(raiz).resolve() if raiz else caminho.parent
    try:
        modulo = caminho.relative_to(raiz).with_suffix("").as_posix().replace("/", ".")
    except ValueError:
        modulo, raiz = caminho.stem, caminho.parent
    try:
        r = subprocess.run([sys.executable, "-c", f"import {modulo}"],
                           cwd=str(raiz), capture_output=True, text=True,
                           timeout=tempo)
    except subprocess.TimeoutExpired:
        return [Erro(caminho, 0, 0, "Travou",
                     f"importar o módulo passou de {tempo}s sem terminar")]
    if r.returncode == 0:
        return []
    saida = (r.stderr or "").strip()
    # a ÚLTIMA linha do traceback é o erro; a última posição citada é onde
    ultima = saida.splitlines()[-1] if saida else "erro sem mensagem"
    m = re.match(r"(\w+(?:Error|Exception|Warning))\s*:?\s*(.*)", ultima)
    tipo, msg = (m.group(1), m.group(2)) if m else ("Erro", ultima)
    lugares = list(_TRACE.finditer(saida))
    # o último lugar que é DO PROJETO, e não da biblioteca padrão: o erro
    # quase sempre é do código de quem chamou, não de dentro do `json`
    arq, ln = str(caminho), 0
    for g in reversed(lugares):
        p = Path(g.group("arq"))
        if raiz in p.parents or p == caminho:
            arq, ln = str(p), int(g.group("ln"))
            break
    return [Erro(arq, ln, 0, tipo, msg, texto=_linha_de(arq, ln).rstrip())]


# ══════════════════════════════════════════════════════════════════════
#  TRACEBACK COLADO — sem juiz, mas com diagnóstico
# ══════════════════════════════════════════════════════════════════════
def do_traceback(texto, raiz=None):
    """O traceback que a pessoa colou no chat vira um `Erro` `achado`.

    Marcado como DIAGNÓSTICO e não como PROVADO, porque não há como
    reproduzir: o erro aconteceu com dados que eu não tenho. O conserto
    que sair daqui é uma opinião fundamentada, e a tela vai dizer isso.
    """
    if not texto or "Traceback" not in texto and "Error" not in texto:
        return []
    linhas = [x for x in texto.strip().splitlines() if x.strip()]
    ultima = linhas[-1]
    m = re.match(r"\s*(\w+(?:Error|Exception))\s*:?\s*(.*)", ultima)
    if not m:
        return []
    lugares = list(_TRACE.finditer(texto))
    arq, ln = ("", 0)
    if lugares:
        g = lugares[-1]
        arq, ln = g.group("arq"), int(g.group("ln"))
    return [Erro(arq, ln, 0, m.group(1), m.group(2),
                 texto=_linha_de(arq, ln).rstrip() if arq else "",
                 faixa=DIAGNOSTICO)]


# ══════════════════════════════════════════════════════════════════════
#  A PORTA
# ══════════════════════════════════════════════════════════════════════
FORA = {"__pycache__", ".git", ".venv", "venv", "node_modules", "bin", "obj"}


def julgar(alvo, importar=False, raiz=None):
    """Um arquivo ou uma pasta → a lista de erros. Sintaxe sempre; import só se pedir.

    A SINTAXE VEM PRIMEIRO E SOZINHA. Um arquivo que nem parseia não tem
    como ser importado, e mandar importar só produziria o mesmo erro com
    um traceback em volta.
    """
    alvo = Path(alvo)
    arquivos = ([alvo] if alvo.is_file() else
                sorted(p for p in alvo.rglob("*.py")
                       if not any(x in FORA for x in p.parts)))
    raiz = raiz or (alvo if alvo.is_dir() else alvo.parent)
    achados = []
    for f in arquivos:
        erros = erros_de_sintaxe(f)
        if erros:
            achados += erros
            continue
        if importar:
            achados += erros_de_importacao(f, raiz)
    return achados


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python provas/juiz_python.py <arquivo ou pasta> [--importar]")
        raise SystemExit(1)
    erros = julgar(sys.argv[1], importar="--importar" in sys.argv)
    if not erros:
        print("nenhum erro — o juiz não achou o que reclamar")
    for e in erros:
        print(f"  [{e.faixa}] {e}")
        if e.texto:
            print(f"      {e.texto.strip()}")
    print(f"\n  {len(erros)} erro(s)")
