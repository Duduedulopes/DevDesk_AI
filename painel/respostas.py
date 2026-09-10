"""O que cada intenção FAZ. É aqui que a rede deixa de só classificar.

TRÊS TIPOS DE RESPOSTA

  fala        só texto. `saudacao` não precisa investigar nada; a resposta
              É a fala.

  investiga   lê o sistema e responde com o que achou: arquivos mexidos,
              logs, disco, versões, portas, processos.

  pergunta    a intenção é clara mas falta o essencial — pede informação
              antes de agir.

DOMÍNIO: ASSISTENTE DE DESENVOLVEDOR

Este arquivo cobre as 52 intenções do domínio de suporte a desenvolvedores.
Cada grupo tem ações proporcionais ao risco:

  - Conversa, navegação, entendimento → resposta direta
  - Diagnóstico → investiga e aponta o que encontrou
  - Ação destrutiva (apagar, editar, refatorar) → fala o que faria e para
  - Execução → fala o comando exato; quem confirma sabe o que vai rodar

O QUE NÃO ESTÁ AQUI, DE PROPÓSITO

Nenhuma intenção que ESCREVE tem ação automática. `criar_arquivo`,
`editar_codigo`, `renomear`, `apagar`, `refatorar` devolvem o que fariam
e param — quem escreve passa pela confirmação, sempre.
"""
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from painel import consultas as _consultas
from modelo.gerador_codigo import GeradorDeCodigo
from modelo.arquiteturas import obter_arquitetura, explicar_conceito
from modelo.analise_codigo import analisar_codigo_completo, NivelGravidade

IGNORA = {".git", "__pycache__", ".venv", "obj", "bin", "node_modules",
          ".vs", "packages", ".gradle", "AppData"}


def _tamanho(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {u}"
        n /= 1024
    return f"{n:.0f} PB"


def _eh_ignorado(p):
    return any(x in p.parts for x in IGNORA)


# ══════════════════════════════════════════════════════════════════════
#  INVESTIGAÇÕES — leitura pura, sem subprocesso destrutivo
# ══════════════════════════════════════════════════════════════════════

def maquina(s):
    """Estado geral: disco, Python, arquivos."""
    try:
        livre = shutil.disk_usage(s.pasta)
        arquivos = [p for p in s.pasta.rglob("*")
                    if p.is_file() and not _eh_ignorado(p)]
        ocupado = sum(p.stat().st_size for p in arquivos)
        aperto = livre.free / livre.total
        aviso = "  ⚠ apertado" if aperto < 0.10 else ""
        dica = (
            "Espaço em disco abaixo de 10% é causa comum de lentidão e falha "
            "de build — eu começaria por aí."
            if aperto < 0.10
            else "Nada gritante no básico. Me diga o que está lento e eu procuro no lugar certo."
        )
        return (
            f"**Olhei a máquina agora:**\n\n"
            f"- sistema: {platform.system()} {platform.release()}\n"
            f"- python: {sys.version.split()[0]}\n"
            f"- disco: {_tamanho(livre.free)} livres de {_tamanho(livre.total)} "
            f"({aperto:.0%}){aviso}\n"
            f"- pasta: {len(arquivos)} arquivos, {_tamanho(ocupado)}\n\n"
            f"{dica}"
        )
    except Exception as e:
        return f"Não consegui ler o estado da máquina: {e}"


def procurar_logs(s):
    """Localiza arquivos de log e mostra os mais recentes."""
    achados = []
    try:
        for p in s.pasta.rglob("*"):
            if (p.is_file() and not _eh_ignorado(p)
                    and p.suffix.lower() in (".log", ".txt")
                    and ("log" in p.name.lower() or p.suffix.lower() == ".log")):
                achados.append(p)
    except Exception:
        pass
    if not achados:
        return (
            "Não achei nenhum arquivo de log nesta pasta.\n\n"
            "Se o log estiver em outro lugar, me passe o caminho com "
            "`abrir C:\\caminho\\arquivo.log`."
        )
    achados.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    linhas = [
        f"- `{p.relative_to(s.pasta)}` — {_tamanho(p.stat().st_size)}, "
        f"mexido {time.strftime('%d/%m %H:%M', time.localtime(p.stat().st_mtime))}"
        for p in achados[:8]
    ]
    return (
        "**Logs que achei, do mais recente:**\n\n" + "\n".join(linhas) +
        "\n\nMande `abrir <caminho>` que eu trago para o painel."
    )


def mexidos_agora(s):
    """Os arquivos mexidos mais recentemente — ponto de partida para diagnóstico."""
    try:
        arquivos = [p for p in s.pasta.rglob("*")
                    if p.is_file() and not _eh_ignorado(p)]
    except Exception:
        arquivos = []
    if not arquivos:
        return "A pasta está vazia."
    arquivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    linhas = [
        f"- `{p.relative_to(s.pasta)}` — "
        f"{time.strftime('%d/%m %H:%M', time.localtime(p.stat().st_mtime))}"
        for p in arquivos[:8]
    ]
    return (
        "Para achar a causa eu preciso saber **o que mudou**. "
        "Arquivos mexidos por último:\n\n" + "\n".join(linhas) +
        "\n\nMe conte o que parou de funcionar e desde quando — "
        "com isso eu sei onde procurar."
    )


def listar_pasta(s):
    """Lista o conteúdo da pasta atual do projeto."""
    try:
        itens = sorted(s.pasta.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except Exception as e:
        return f"Não consegui listar a pasta: {e}"
    if not itens:
        return "A pasta está vazia."
    linhas = []
    for p in itens[:40]:
        if p.is_dir():
            linhas.append(f"📁 `{p.name}/`")
        else:
            linhas.append(f"📄 `{p.name}` — {_tamanho(p.stat().st_size)}")
    return f"**Conteúdo de `{s.pasta.name}`:**\n\n" + "\n".join(linhas)


def estrutura_projeto(s):
    """Mostra a estrutura de pastas do projeto (2 níveis)."""
    def _arvore(pasta, nivel=0, max_nivel=2):
        if nivel > max_nivel:
            return []
        linhas = []
        try:
            itens = sorted(pasta.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except Exception:
            return []
        for p in itens:
            if _eh_ignorado(p):
                continue
            prefixo = "  " * nivel
            if p.is_dir():
                linhas.append(f"{prefixo}📁 `{p.name}/`")
                linhas.extend(_arvore(p, nivel + 1, max_nivel))
            else:
                linhas.append(f"{prefixo}📄 `{p.name}`")
        return linhas

    linhas = _arvore(s.pasta)
    if not linhas:
        return "A pasta está vazia ou não consigo listá-la."
    return f"**Estrutura de `{s.pasta.name}`:**\n\n" + "\n".join(linhas[:60])


def estado_disco(s):
    """Quanto espaço resta em disco."""
    try:
        uso = shutil.disk_usage(s.pasta)
        pct_livre = uso.free / uso.total
        barra = "█" * int(pct_livre * 20) + "░" * (20 - int(pct_livre * 20))
        aviso = ""
        if pct_livre < 0.05:
            aviso = "\n\n⛔ **Disco quase cheio** — isso pode causar falha de build, erro ao gravar e comportamento imprevisível."
        elif pct_livre < 0.10:
            aviso = "\n\n⚠ **Pouco espaço** — considere liberar espaço antes de continuar."
        return (
            f"**Espaço em disco:**\n\n"
            f"- total: {_tamanho(uso.total)}\n"
            f"- usado: {_tamanho(uso.used)} ({uso.used/uso.total:.0%})\n"
            f"- livre: {_tamanho(uso.free)} ({pct_livre:.0%})\n"
            f"- [{barra}]{aviso}"
        )
    except Exception as e:
        return f"Não consegui verificar o disco: {e}"


def processos_rodando(s):
    """Lista processos rodando — usa 'tasklist' no Windows, 'ps' no Linux."""
    try:
        if platform.system() == "Windows":
            r = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=10
            )
            linhas_raw = r.stdout.strip().splitlines()[:20]
            procs = []
            for linha in linhas_raw:
                partes = [p.strip('"') for p in linha.split('","')]
                if len(partes) >= 5:
                    procs.append(f"- `{partes[0]}` (PID {partes[1]}) — {partes[4]}")
            return "**Processos rodando (primeiros 20):**\n\n" + "\n".join(procs)
        else:
            r = subprocess.run(
                ["ps", "aux", "--sort=-%cpu"],
                capture_output=True, text=True, timeout=10
            )
            linhas = r.stdout.strip().splitlines()[1:16]
            return "**Processos (por CPU):**\n\n```\n" + "\n".join(linhas) + "\n```"
    except Exception as e:
        return (
            f"Não consegui listar processos automaticamente: {e}\n\n"
            "Tente `> tasklist` (Windows) ou `> ps aux` (Linux) para ver o que está rodando."
        )


def versoes_ferramentas(s):
    """Verifica versões das ferramentas de desenvolvimento instaladas."""
    ferramentas = [
        (["python", "--version"],   "Python"),
        (["python3", "--version"],  "Python3"),
        (["dotnet", "--version"],   ".NET"),
        (["node", "--version"],     "Node.js"),
        (["npm", "--version"],      "npm"),
        (["git", "--version"],      "Git"),
        (["pip", "--version"],      "pip"),
        (["pytest", "--version"],   "pytest"),
    ]
    linhas = []
    for cmd, nome in ferramentas:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            saida = (r.stdout or r.stderr).strip().splitlines()[0]
            linhas.append(f"- **{nome}**: `{saida}`")
        except FileNotFoundError:
            linhas.append(f"- **{nome}**: não encontrado no PATH")
        except Exception:
            pass
    if not linhas:
        return "Não consegui verificar nenhuma ferramenta."
    return "**Ferramentas instaladas:**\n\n" + "\n".join(linhas)


def git_status(s):
    """Roda git status na pasta do projeto."""
    try:
        r = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10, cwd=str(s.pasta)
        )
        if r.returncode != 0:
            return (
                "Não é um repositório git ou o git não está no PATH.\n\n"
                "Se quiser, tente `> git status` para ver o resultado direto."
            )
        saida = r.stdout.strip()
        if not saida:
            return "✅ Tudo commitado — nenhuma alteração pendente."
        linhas = saida.splitlines()
        modificados = [l for l in linhas if l.startswith(" M") or l.startswith("M")]
        novos      = [l for l in linhas if l.startswith("?")]
        deletados  = [l for l in linhas if l.startswith(" D") or l.startswith("D")]
        partes = []
        if modificados:
            partes.append(f"**Modificados ({len(modificados)}):**\n" +
                          "\n".join(f"  `{l[3:]}`" for l in modificados))
        if novos:
            partes.append(f"**Novos / não rastreados ({len(novos)}):**\n" +
                          "\n".join(f"  `{l[3:]}`" for l in novos))
        if deletados:
            partes.append(f"**Deletados ({len(deletados)}):**\n" +
                          "\n".join(f"  `{l[3:]}`" for l in deletados))
        return "\n\n".join(partes) or f"```\n{saida}\n```"
    except Exception as e:
        return f"Erro ao rodar git status: {e}"


def git_log(s):
    """Últimos commits do repositório."""
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "--decorate", "-15"],
            capture_output=True, text=True, timeout=10, cwd=str(s.pasta)
        )
        if r.returncode != 0:
            return "Não é um repositório git, ou sem commits ainda."
        saida = r.stdout.strip()
        if not saida:
            return "Nenhum commit ainda neste repositório."
        return f"**Últimos commits:**\n\n```\n{saida}\n```"
    except Exception as e:
        return f"Erro ao rodar git log: {e}"


def git_diff(s):
    """Mostra o diff das alterações não commitadas."""
    try:
        r = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10, cwd=str(s.pasta)
        )
        if r.returncode != 0:
            return "Não é um repositório git."
        saida = r.stdout.strip()
        if not saida:
            return "Nenhuma alteração não commitada."
        return f"**Alterações (git diff --stat):**\n\n```\n{saida}\n```\n\nMande `> git diff` para ver o diff completo."
    except Exception as e:
        return f"Erro ao rodar git diff: {e}"


# ══════════════════════════════════════════════════════════════════════
#  DIAGNÓSTICO TÉCNICO — aponta causa provável com base no sintoma
# ══════════════════════════════════════════════════════════════════════

def diagnosticar_compilacao(s):
    """Erro de compilação: aponta onde estão os logs de build."""
    logs = []
    try:
        for p in s.pasta.rglob("*"):
            if p.is_file() and not _eh_ignorado(p):
                nome = p.name.lower()
                if "build" in nome or "msbuild" in nome or "compile" in nome:
                    if p.suffix.lower() in (".log", ".txt", ".binlog"):
                        logs.append(p)
    except Exception:
        pass
    logs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    base = (
        "**Erro de compilação — o que verificar:**\n\n"
        "1. A mensagem de erro exata está no painel de saída do editor "
        "(normalmente em vermelho). Me mande o texto com `abrir <log>`.\n"
        "2. Causas comuns:\n"
        "   - **falta de dependência**: `module not found`, `unresolved reference` "
        "→ rode `pip install`, `dotnet restore` ou `npm install`\n"
        "   - **erro de sintaxe**: a linha indicada no erro tem um caractere faltando\n"
        "   - **tipo incompatível**: o compilador aponta a linha exata\n"
        "3. Se acabou de mudar de branch, pode ser que a `obj/` esteja desatualizada: "
        "`dotnet clean` ou apagar a pasta `obj/` costuma resolver.\n"
    )
    if logs:
        base += "\n**Logs de build que achei:**\n" + "\n".join(
            f"- `{p.relative_to(s.pasta)}`" for p in logs[:4])
    return base


def diagnosticar_execucao(s):
    """Erro em execução: orienta a localizar o stack trace."""
    logs_recentes = []
    try:
        arquivos = [p for p in s.pasta.rglob("*")
                    if p.is_file() and not _eh_ignorado(p)
                    and p.suffix.lower() in (".log", ".txt")]
        arquivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        logs_recentes = arquivos[:3]
    except Exception:
        pass

    base = (
        "**Erro em execução — como localizar a causa:**\n\n"
        "O erro em execução sempre vem com um **stack trace** — a pilha de chamadas "
        "que levou ao crash. É o que diz onde o problema está de verdade.\n\n"
        "1. Me mande a mensagem de erro completa (pode copiar e colar).\n"
        "2. A linha que mais importa no stack trace é a **primeira do seu código** "
        "— as de biblioteca ficam abaixo.\n"
        "3. Causas comuns:\n"
        "   - **NullReferenceException / AttributeError**: você está usando um "
        "objeto que pode ser `None` — confere se inicializou antes de usar\n"
        "   - **IndexError / IndexOutOfRange**: lista ou array menor que o índice\n"
        "   - **FileNotFoundError / IOException**: arquivo não existe no caminho esperado\n"
        "   - **ConnectionRefused**: serviço não está rodando ou porta errada\n"
    )
    if logs_recentes:
        base += "\n**Logs mais recentes (podem ter o stack trace):**\n" + "\n".join(
            f"- `{p.relative_to(s.pasta)}` — "
            f"mexido {time.strftime('%d/%m %H:%M', time.localtime(p.stat().st_mtime))}"
            for p in logs_recentes)
    return base


def diagnosticar_nao_abre(s):
    """Programa não abre: verificações básicas."""
    return (
        "**Programa não abre — verificações rápidas:**\n\n"
        "1. **Verifique se compilou**: o executável existe? Procure na pasta `bin/` ou `dist/`.\n"
        "2. **Rode pelo terminal**: abrir pelo terminal mostra a mensagem de erro que "
        "a janela esconde. Tente `> python main.py` ou `> dotnet run`.\n"
        "3. **Verifique as dependências**: `pip install -r requirements.txt`, "
        "`dotnet restore` ou `npm install`.\n"
        "4. **Verifique variáveis de ambiente**: o `.env` ou `appsettings.json` "
        "precisa existir e ter os valores certos.\n\n"
        "Me mande o que aparece no terminal quando tenta rodar — com isso eu "
        "sei exatamente onde está o problema."
    )


def diagnosticar_lentidao(s):
    """Lentidão: colhe info de disco e aponta possíveis causas."""
    try:
        uso = shutil.disk_usage(s.pasta)
        disco_info = f"- disco: {_tamanho(uso.free)} livres ({uso.free/uso.total:.0%})"
    except Exception:
        disco_info = "- disco: não consegui verificar"

    return (
        f"**Lentidão — o que verificar:**\n\n"
        f"{disco_info}\n\n"
        "Causas mais comuns:\n"
        "1. **Disco cheio ou quase** → libere espaço\n"
        "2. **Muitos processos pesados rodando** → `> tasklist` para ver o que "
        "está consumindo CPU/memória\n"
        "3. **Query lenta no banco** → ative o log de queries lentas, ou rode "
        "com `EXPLAIN` para ver o plano\n"
        "4. **Rebuild desnecessário** → configure o watcher corretamente para "
        "não recompilar o projeto inteiro a cada save\n"
        "5. **node_modules ou obj/ corrompidos** → apague e instale de novo\n\n"
        "Me diga: lentidão em que parte — build, resposta da API, abertura do editor, "
        "ou execução do programa?"
    )


def diagnosticar_travou(s):
    """Programa travou: orienta como sair do estado e diagnosticar."""
    return (
        "**Programa travou — o que fazer:**\n\n"
        "1. **Force o encerramento**: `> taskkill /F /IM nome.exe` (Windows) ou "
        "`> kill -9 <PID>` (Linux/Mac).\n"
        "2. **Verifique o log** — pode ter um deadlock ou loop infinito registrado.\n"
        "3. **Causas comuns de travamento:**\n"
        "   - **Deadlock**: duas threads esperando uma pela outra — look for `lock`, "
        "`Monitor.Enter` ou `await` dentro de `lock`\n"
        "   - **Loop infinito**: condição de saída do `while` nunca é verdadeira\n"
        "   - **Espera de I/O**: leitura de arquivo ou socket que nunca responde\n"
        "   - **Thread UI bloqueada**: operação pesada rodando na thread principal\n\n"
        "Me diga: o programa trava sempre no mesmo ponto, ou é aleatório?"
    )


def diagnosticar_porta(s):
    """Porta ocupada: mostra como identificar e liberar."""
    cmd_win = "`> netstat -ano | findstr :PORTA`"
    cmd_lnx = "`> lsof -i :PORTA`"
    return (
        "**Porta já em uso — como resolver:**\n\n"
        f"1. **Identifique qual processo está usando**: {cmd_win} (Windows) "
        f"ou {cmd_lnx} (Linux/Mac). Troque `PORTA` pelo número.\n"
        "2. **Encerre o processo**: `> taskkill /F /PID <numero>` (Windows) "
        "ou `> kill <PID>`.\n"
        "3. **Se for o seu próprio processo de uma execução anterior**: "
        "ele pode estar em estado TIME_WAIT — aguarde ~30s ou troque a porta.\n"
        "4. **Mude a porta na configuração**: em `appsettings.json`, `.env`, "
        "ou nos argumentos de linha de comando do seu servidor.\n\n"
        "Me diga qual porta está ocupada que eu monto o comando exato."
    )


def diagnosticar_permissao(s):
    """Permissão negada: orienta como resolver."""
    return (
        "**Permissão negada — causas e soluções:**\n\n"
        "1. **Arquivo aberto em outro processo**: o editor ou outro programa "
        "está segurando o arquivo. Feche e tente de novo.\n"
        "2. **Pasta protegida** (`C:\\Program Files`, `C:\\Windows`): "
        "mova o projeto para `C:\\Users\\SeuNome\\` ou `C:\\Dev\\`.\n"
        "3. **Atributo somente-leitura**: clique direito → Propriedades → "
        "desmarque *Somente leitura*. No terminal: `> attrib -r arquivo`.\n"
        "4. **Falta de permissão no banco**: o usuário da connection string "
        "precisa ter permissão de leitura/escrita na tabela.\n"
        "5. **Docker ou WSL**: o volume montado pode ter permissões de Linux "
        "— `chmod 755` ou `chown` na pasta.\n\n"
        "Me diga onde deu permissão negada — arquivo, pasta ou banco?"
    )


def diagnosticar_dependencia(s):
    """Dependência faltando: como instalar."""
    # Detecta o tipo de projeto pela presença de arquivos característicos
    tem_requirements = (s.pasta / "requirements.txt").exists()
    tem_csproj       = any(s.pasta.rglob("*.csproj"))
    tem_package_json = (s.pasta / "package.json").exists()

    partes = ["**Dependência faltando — como instalar:**\n"]
    if tem_requirements or any(s.pasta.rglob("*.py")):
        partes.append("**Python:**\n"
                      "```\npip install -r requirements.txt\n```\n"
                      "ou `pip install <nome_do_pacote>`")
    if tem_csproj:
        partes.append("**.NET:**\n"
                      "```\ndotnet restore\n```\n"
                      "ou `dotnet add package <NomeDoPacote>`")
    if tem_package_json:
        partes.append("**Node.js:**\n"
                      "```\nnpm install\n```\n"
                      "ou `npm install <nome-do-pacote>`")
    if len(partes) == 1:
        partes.append(
            "Não identifiquei o tipo de projeto automaticamente. Me diga: "
            "Python, .NET, Node, ou outro? E qual o nome do pacote que faltou."
        )
    partes.append(
        "Depois de instalar, tente compilar de novo. Se o erro continuar, "
        "me mande a mensagem exata — às vezes é um nome de pacote diferente "
        "entre versões."
    )
    return "\n\n".join(partes)


def diagnosticar_conexao(s):
    """Não conecta: orienta o diagnóstico de rede/serviço."""
    return (
        "**Não conecta — verificações em ordem:**\n\n"
        "1. **O serviço está rodando?** Tente `> netstat -an | findstr PORTA` "
        "(Windows) ou `> ss -tlnp | grep PORTA` para confirmar.\n"
        "2. **A URL/host está certa?** Copie a connection string ou URL do config "
        "e tente no browser ou `> curl http://host:porta/`.\n"
        "3. **Erro específico:**\n"
        "   - `Connection refused` → o serviço não está rodando na porta\n"
        "   - `Timeout` → firewall ou rede bloqueando, ou host errado\n"
        "   - `SSL/TLS error` → certificado inválido ou porta HTTPS errada\n"
        "   - `Host not found` → nome de host errado ou DNS não resolve\n"
        "4. **Banco de dados**: verifique se o servidor de banco está iniciado, "
        "e se a connection string tem host, porta, usuário e senha corretos.\n\n"
        "Me mande a mensagem de erro completa — ela diz exatamente onde está quebrando."
    )


# ══════════════════════════════════════════════════════════════════════
#  TEXTOS FIXOS — falas sem investigação
# ══════════════════════════════════════════════════════════════════════

def _ajuda():
    return (
        "**O que eu faço:**\n\n"
        "**Navegar** — `abrir <arquivo>`, `procura <termo>`, estrutura do projeto, "
        "listar pasta\n"
        "**Entender** — o que esse método faz, o que significa esse erro, "
        "onde foi declarado isso\n"
        "**Diagnosticar** — erro de compilação, erro em execução, não abre, "
        "trava, porta ocupada, sem permissão, dependência faltando, não conecta\n"
        "**Git** — status, histórico, diff, enviar, desfazer\n"
        "**Máquina** — disco, logs, processos, versões das ferramentas\n"
        "**Executar** — eu monto o comando; você confirma antes de rodar\n\n"
        "Fala o que está acontecendo — ou `> comando` para rodar qualquer "
        "coisa de leitura direto no terminal."
    )


import random as _random


def _uma(*opcoes):
    """Uma das opções ao acaso — para a fala não repetir sempre igual.

    A pessoa repara quando a máquina responde com a MESMA frase toda vez:
    parece que não ouviu. Variar a mesma informação dá a sensação de quem
    realmente leu — e o conteúdo continua o mesmo.
    """
    return _random.choice(opcoes)


def preludio(s):
    """Um passo antes da primeira resposta técnica da conversa.

    Devolvido só UMA vez por conversa (a Sessão zera a flag); depois a
    pessoa sabe que estou ouvindo, e repetir vira cerimônia. O nome entra
    para a frase não ser genérica.
    """
    n = s.seu_nome()
    return _uma(
        f"Claro, {n}! Deixa eu olhar isso pra você.",
        f"Entendi, {n}. Vou verificar.",
        f"Fechou. Dá um instante que eu vejo isso.",
        f"Pode deixar, {n} — estou olhando.",
    )


def _sistema():
    return (
        "Eu sou o **DevDesk**. Rodo **inteiro nesta máquina** — sem nuvem, "
        "sem chave de API, sem mandar nada para fora.\n\n"
        "O que me faz funcionar é uma rede neural escrita do zero em NumPy: "
        "classificador de intenção com tabela de embutimento, camada oculta "
        "com sigmoide e softmax, treinado com descida do gradiente. "
        "52 intenções de suporte a desenvolvedor.\n\n"
        "Quando fico em dúvida eu mostro o que calculei e peço para você\n"
        "escolher — cada escolha sua é um exemplo rotulado que me ensina."
    )


# ══════════════════════════════════════════════════════════════════════
#  OS MAPAS — intenção → ação
# ══════════════════════════════════════════════════════════════════════

FALAS = {
    # ── Conversa ──────────────────────────────────────────────────────
    "saudacao": lambda s: _uma(
        f"{s.saudacao_da_hora()}, {s.seu_nome()}! Pode falar à vontade — "
        f"o que está acontecendo?",
        f"Oi, {s.seu_nome()}! Tudo certo. Me conta o que você precisa.",
        f"{s.saudacao_da_hora()}, {s.seu_nome()}! Bom te ver. Me mostra o "
        f"que está rolando.",
        f"Fala, {s.seu_nome()}! Estou aqui. O que a gente resolve hoje?",
    ),
    "despedida": lambda s: _uma(
        "Até mais. Se travar alguma coisa, é só chamar.",
        "Até logo. Qualquer dúvida — é só voltar.",
        "Falou! Estou por aqui se precisar.",
    ),
    "agradecimento": lambda s: _uma(
        "De nada. Precisando, é só chamar.",
        "Imagina — para isso eu estou aí.",
        "Por nada. Qualquer coisa, é só falar.",
    ),
    "confirmar": lambda s: _uma(
        "Feito. O que vem agora?",
        "Ok. Prossiga — o que faremos agora?",
        "Beleza. Qual o próximo passo?",
    ),
    "cancelar": lambda s: _uma(
        "Tudo bem. Quando quiser voltar, é só falar.",
        "Sem problema. Deixei quieto.",
        "Ok, cancelei. Precisa de mais alguma coisa?",
    ),
    "ajuda": lambda s: _ajuda(),
    "quem_e_voce": lambda s: _sistema(),
    "reclamacao": lambda s: (
        "Entendido — errei. Pode me dizer o que era para ter feito? "
        "Assim eu aprendo com a correção."
    ),
    "fora_de_escopo": lambda s: (
        "Isso está fora do que eu sei fazer. Meu foco é o projeto nesta pasta: "
        "código, build, dependências, git, e o estado desta máquina."
    ),

    # ── Alterar — fala o que faria e para ─────────────────────────────
    "criar_arquivo": lambda s: (
        "Para criar um arquivo preciso saber o nome e o conteúdo inicial. "
        "Me diga o caminho completo (ex: `src/utils.py`) e o que deve ter dentro "
        "— ou pode me dar só o nome e eu crio vazio para você editar."
    ),
    "editar_codigo": lambda s: (
        "Para editar, abra o arquivo primeiro (`abrir <caminho>`) e me diga "
        "o que precisa mudar — posso sugerir a alteração antes de aplicar, "
        "e você confirma."
    ),
    "renomear": lambda s: (
        "Para renomear preciso do nome atual e do nome novo. Fale os dois e "
        "eu monto o comando — você confirma antes de rodar."
    ),
    "apagar": lambda s: (
        "Apagar é irreversível sem git. Me diga o que quer apagar — "
        "eu mostro o que vai sumir e você confirma."
    ),
    "refatorar": lambda s: (
        "Para refatorar, abra o arquivo (`abrir <caminho>`) e me diga o que "
        "quer reorganizar: extrair método, separar classe, renomear variável? "
        "Eu sugiro e você confirma cada mudança."
    ),

    # ── Executar — monta o comando, não roda por conta ────────────────
    "rodar": lambda s: (
        "Me diz como você roda esse projeto normalmente — `python main.py`, "
        "`dotnet run`, `npm start`? Eu monto o comando e você confirma."
    ),
    "compilar": lambda s: (
        "Me diz o tipo do projeto:\n"
        "- Python: não precisa de compilação explícita\n"
        "- .NET: `dotnet build`\n"
        "- Node: `npm run build`\n"
        "Qual é? Eu monto o comando."
    ),
    "rodar_testes": lambda s: (
        "Me diz qual framework de testes:\n"
        "- Python: `pytest` ou `python -m unittest`\n"
        "- .NET: `dotnet test`\n"
        "- Node: `npm test`\n"
        "Qual é? Eu monto o comando e você confirma."
    ),
    "instalar_dependencia": lambda s: (
        "Me diz o nome do pacote e o gerenciador:\n"
        "- Python: `pip install <pacote>`\n"
        "- .NET: `dotnet add package <Pacote>`\n"
        "- Node: `npm install <pacote>`\n"
        "Qual é?"
    ),
    "parar_processo": lambda s: (
        "Me diz o nome ou PID do processo que quer encerrar — "
        "ou mande `> tasklist` para ver o que está rodando. "
        "Eu monto o comando `taskkill` e você confirma."
    ),
    "comando_livre": lambda s: (
        "Me mande o comando com `> ` na frente e eu rodo. Comandos que só leem "
        "(git, dir, type, python, pip, node) rodam direto. "
        "Comandos que alteram pedem sua confirmação antes."
    ),

    # ── Git — escrita pede confirmação ────────────────────────────────
    "git_enviar": lambda s: (
        "Enviar para o repositório remoto altera o histórico compartilhado. "
        "Me diz: quer só commitar local, ou também fazer push? "
        "E qual mensagem de commit? Eu monto o comando e você confirma."
    ),
    "git_desfazer": lambda s: (
        "Desfazer no git pode ser irreversível dependendo do que for. "
        "Me diz: quer descartar mudanças não commitadas (`git checkout .`), "
        "desfazer o último commit mantendo as mudanças (`git reset HEAD~1`), "
        "ou reverter um commit específico? Eu monto o comando e você confirma."
    ),

    # ── Ambiente ──────────────────────────────────────────────────────
    "abrir_no_editor": lambda s: (
        "Mande `code .` para abrir no VS Code, ou me diz o caminho do arquivo "
        "e eu abro no painel aqui mesmo."
    ),
    "variavel_de_ambiente": lambda s: (
        "Variáveis de ambiente ficam no `.env`, `appsettings.json`, ou nas "
        "variáveis do sistema. Me diz qual variável procura — eu acho o arquivo "
        "de configuração do projeto e mostro onde configurar."
    ),

    # ── Entender — resposta orientativa ──────────────────────────────
    "explicar_codigo": lambda s: (
        "Abra o arquivo com `abrir <caminho>` e me diga qual trecho quer entender. "
        "Pode copiar e colar o código aqui também."
    ),
    "explicar_erro": lambda s: (
        "Cola a mensagem de erro completa aqui — com o stack trace se tiver. "
        "Vou explicar o que significa e apontar onde procurar."
    ),
    "achar_definicao": lambda s: (
        "Me diz o nome da função, classe ou variável — eu procuro na pasta do projeto."
    ),
    "achar_uso": lambda s: (
        "Me diz o nome do símbolo — eu procuro quem usa no código."
    ),
    "revisar_codigo": lambda s: (
        "Abra o arquivo com `abrir <caminho>` ou cole o trecho aqui — "
        "eu dou uma olhada e aponto o que parece errado ou pode melhorar."
    ),

    # ── Achar e Navegar ───────────────────────────────────────────────
    "abrir_projeto": lambda s: (
        "Me diz o nome da pasta do projeto — eu abro no painel. "
        "Ou mande `code <caminho>` para abrir no VS Code."
    ),
    "abrir_arquivo": lambda s: (
        "Me diz o nome do arquivo: `abrir <caminho>` que eu trago para o painel."
    ),
    "procurar_arquivo": lambda s: (
        "Me diz o nome do arquivo que está procurando — eu busco na pasta do projeto."
    ),
    "procurar_no_codigo": lambda s: (
        "Me diz o termo — eu procuro no código com `> grep -r 'termo' .` "
        "(ou `> findstr /s /i 'termo' *` no Windows)."
    ),

    # ── Desenvolvimento de Software ─────────────────────────────────────
    "gerar_codigo": lambda s: _gerar_codigo_resposta(s),
    # `criar_projeto_completo` SAIU DAQUI, e o motivo fica escrito.
    #
    # Era uma segunda intenção para a MESMA coisa que `criar_projeto` faz —
    # e as duas juntas quebravam o pedido de duas maneiras ao mesmo tempo:
    #
    #   · o corpus de treino tinha 109 frases de molde para
    #     `criar_projeto_completo` e ZERO para `criar_projeto`, então a
    #     rede nunca viu a intenção que o `responder` sabe atender;
    #   · e se um dia ela acertasse `criar_projeto_completo`, cairia AQUI,
    #     num texto pronto que só faz três perguntas — em vez de cair na
    #     função `criar_projeto`, que chama o compositor de verdade e
    #     monta a árvore de arquivos.
    #
    # Uma intenção que só existe para responder com texto fixo é um
    # dicionário com nome de rede. Ficou uma só, e é a que trabalha.
    "implementar_funcionalidade": lambda s: (
        "Para implementar uma funcionalidade, preciso saber:\n"
        "- O que a funcionalidade deve fazer?\n"
        "- Em qual arquivo/classe adicionar?\n"
        "- Tem algum requisito específico?\n\n"
        "Me dá esses detalhes que eu implemento."
    ),
    "escrever_classe": lambda s: _escrever_classe_resposta(s),
    "escrever_funcao": lambda s: _escrever_funcao_resposta(s),
    "otimizar_codigo": lambda s: _otimizar_codigo_resposta(s),
    "corrigir_bug": lambda s: _corrigir_bug_resposta(s),
    "explicar_conceito": lambda s: _explicar_conceito_resposta(s),
    "sugerir_arquitetura": lambda s: _sugerir_arquitetura_resposta(s),
}


# ══════════════════════════════════════════════════════════════════════
#  FUNÇÕES AUXILIARES PARA DESENVOLVIMENTO
# ══════════════════════════════════════════════════════════════════════

def _gerar_codigo_resposta(s):
    """Gera código baseado no pedido do usuário."""
    gerador = GeradorDeCodigo()
    texto = s.ultima_mensagem.lower() if hasattr(s, 'ultima_mensagem') else ""

    # Detectar se quer calculadora
    if "calculadora" in texto:
        params = gerador.extrair_parametros(texto)
        codigo = gerador.gerar_calculadora(params.get("linguagem", "csharp"))
        return (
            f"**Aqui está uma calculadora em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Você pode copiar e colar este código em um arquivo "
            f"e executar. Quer que eu crie o arquivo para você?"
        )

    # Detectar se quer CRUD
    if "crud" in texto:
        params = gerador.extrair_parametros(texto)
        entidade = params.get("entidade", "Produto")
        codigo = gerador.gerar_crud(entidade, params.get("linguagem", "csharp"))
        return (
            f"**Aqui está um CRUD básico em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Este é um template de CRUD completo para a entidade `{entidade}`. "
            f"Você pode adaptar para suas necessidades específicas. "
            f"Quer que eu personalize?"
        )

    # Detectar se quer API REST
    if "api" in texto or "rest" in texto or "endpoint" in texto:
        params = gerador.extrair_parametros(texto)
        entidade = params.get("entidade", "Produto")
        namespace = "MinhaAPI"
        codigo = gerador.gerar_api_rest(entidade, params.get("linguagem", "csharp"), namespace)
        return (
            f"**Aqui está uma API REST completa em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Esta API inclui:\n"
            f"- GET /api/{entidade.lower()} - Listar todos\n"
            f"- GET /api/{entidade.lower()}/{{id}} - Obter por ID\n"
            f"- POST /api/{entidade.lower()} - Criar novo\n"
            f"- PUT /api/{entidade.lower()}/{{id}} - Atualizar\n"
            f"- DELETE /api/{entidade.lower()}/{{id}} - Remover\n\n"
            f"Quer que eu adicione autenticação JWT ou Docker?"
        )

    # Detectar se quer autenticação
    if "autenticação" in texto or "jwt" in texto or "login" in texto:
        params = gerador.extrair_parametros(texto)
        namespace = "MinhaAPI"
        codigo = gerador.gerar_autenticacao_jwt(params.get("linguagem", "csharp"), namespace)
        return (
            f"**Aqui está um sistema de autenticação JWT em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Este sistema inclui:\n"
            f"- Endpoint de login (/api/auth/login)\n"
            f"- Geração de tokens JWT\n"
            f"- Validação de tokens\n"
            f"- Proteção de rotas\n\n"
            f"**Importante:** Troque a chave secreta por uma real em produção!"
        )

    # Detectar se quer Docker
    if "docker" in texto or "container" in texto:
        params = gerador.extrair_parametros(texto)
        nome_projeto = "MeuProjeto"
        codigo = gerador.gerar_dockerfile(params.get("linguagem", "csharp"), nome_projeto)
        return (
            f"**Aqui está um Dockerfile para {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Para usar:\n"
            f"1. Salve como `Dockerfile` na raiz do projeto\n"
            f"2. Build: `docker build -t {nome_projeto} .`\n"
            f"3. Run: `docker run -p 80:80 {nome_projeto}`\n\n"
            f"Quer que eu crie também um docker-compose.yml?"
        )

    # Detectar se quer CI/CD
    if "ci" in texto or "cd" in texto or "github actions" in texto or "pipeline" in texto:
        params = gerador.extrair_parametros(texto)
        codigo = gerador.gerar_github_actions(params.get("linguagem", "csharp"))
        return (
            f"**Aqui está um pipeline de CI/CD para GitHub Actions em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Este pipeline inclui:\n"
            f"- Build do projeto\n"
            f"- Execução de testes\n"
            f"- Deploy automático para branch main\n\n"
            f"Para usar:\n"
            f"1. Salve como `.github/workflows/ci-cd.yml`\n"
            f"2. Configure secrets no GitHub (AZURE_WEBAPP_PUBLISH_PROFILE)\n"
            f"3. Commit e push para main"
        )

    # Detectar se quer testes
    if "teste" in texto or "test" in texto or "unitário" in texto:
        params = gerador.extrair_parametros(texto)
        entidade = params.get("entidade", "Produto")
        namespace = "MinhaAPI"
        codigo = gerador.gerar_testes_unitarios(entidade, params.get("linguagem", "csharp"), namespace)
        return (
            f"**Aqui estão testes unitários em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Estes testes incluem:\n"
            f"- Teste de criação válida\n"
            f"- Teste de validação de dados inválidos\n"
            f"- Teste de atualização\n\n"
            f"Para executar:\n"
            f"- C#: `dotnet test`\n"
            f"- Python: `pytest`"
        )

    return (
        "Para gerar código, preciso saber:\n"
        "- Qual linguagem? (C#, Python, JavaScript, etc.)\n"
        "- O que o código deve fazer?\n"
        "- Quer um arquivo completo ou só um trecho?\n\n"
        "Me dá esses detalhes que eu gero o código para você.\n\n"
        "**Templates avançados disponíveis:**\n"
        "- API REST completa\n"
        "- Autenticação JWT\n"
        "- CRUD com repositório\n"
        "- Docker containers\n"
        "- CI/CD pipelines (GitHub Actions)\n"
        "- Testes unitários\n"
        "- Calculadoras e funções\n"
        "- Classes e componentes"
    )


def _otimizar_codigo_resposta(s):
    """Analisa e otimiza código."""
    texto = s.ultima_mensagem if hasattr(s, 'ultima_mensagem') else ""

    # Verificar se há código colado na mensagem
    codigo = None
    linguagem = "python"

    # Tentar detectar código no texto (entre ``` ou blocos grandes)
    if "```" in texto:
        partes = texto.split("```")
        for i, parte in enumerate(partes):
            if i % 2 == 1:  # Código está entre ```
                codigo = parte.strip()
                # Detectar linguagem
                if parte.strip().startswith("c#") or parte.strip().startswith("csharp"):
                    linguagem = "csharp"
                elif parte.strip().startswith("python"):
                    linguagem = "python"
                elif parte.strip().startswith("js") or parte.strip().startswith("javascript"):
                    linguagem = "javascript"
                break
    elif len(texto) > 100:  # Código grande sem ``` pode ser o código em si
        codigo = texto

    if not codigo:
        return (
            "Para otimizar código, preciso ver o código primeiro.\n\n"
            "Cole o código que quer otimizar ou use `abrir <caminho>` "
            "para que eu analise o arquivo.\n\n"
            "**O que eu analiso:**\n"
            "- Code smells (código duplicado, funções longas, etc.)\n"
            "- Complexidade ciclomática\n"
            "- Violações de SOLID\n"
            "- Problemas de performance\n"
            "- Boas práticas de clean code"
        )

    # Analisar o código
    analise = analisar_codigo_completo(codigo, linguagem)

    if analise["total_problemas"] == 0:
        return (
            "✅ **Análise concluída!**\n\n"
            f"Não encontrei problemas significativos no código.\n"
            f"Pontuação de qualidade: {analise['pontuacao_qualidade']}/100\n\n"
            "O código segue boas práticas. Quer que eu faça outra análise?"
        )

    # Montar resposta com problemas encontrados
    resposta = f"🔍 **Análise de Código Completa**\n\n"
    resposta += f"**Pontuação de Qualidade:** {analise['pontuacao_qualidade']}/100\n"
    resposta += f"**Total de Problemas:** {analise['total_problemas']}\n\n"

    # Resumo por gravidade
    resposta += "**Resumo por Gravidade:**\n"
    for gravidade, count in analise["resumo_gravidade"].items():
        emoji = {"CRÍTICO": "🔴", "ALTO": "🟠", "MÉDIO": "🟡", "BAIXO": "🟢", "INFORMAÇÃO": "ℹ️"}
        resposta += f"{emoji.get(gravidade, '⚪')} {gravidade}: {count}\n"
    resposta += "\n"

    # Problemas principais
    resposta += "**Principais Problemas Encontrados:**\n\n"
    for problema in analise["problemas"][:5]:  # Mostrar os 5 principais
        emoji = {"CRÍTICO": "🔴", "ALTO": "🟠", "MÉDIO": "🟡", "BAIXO": "🟢", "INFORMAÇÃO": "ℹ️"}
        gravidade_valor = problema.gravidade.value if hasattr(problema.gravidade, 'value') else str(problema.gravidade)
        resposta += f"{emoji.get(gravidade_valor, '⚪')} **{problema.tipo}** (Linha {problema.linha})\n"
        resposta += f"   {problema.descricao}\n"
        resposta += f"   💡 {problema.sugestao}\n\n"

    # Sugestões de refatoração
    if analise["refatoracoes"]:
        resposta += "**Sugestões de Refatoração:**\n\n"
        for ref in analise["refatoracoes"][:3]:
            resposta += f"📝 **{ref['tipo']}**\n"
            resposta += f"   {ref['descricao']}\n"
            resposta += f"   ✨ Benefício: {ref['beneficio']}\n\n"

    resposta += "Quer que eu implemente alguma dessas sugestões?"

    return resposta


def _corrigir_bug_resposta(s):
    """Analisa e sugere correção para bugs."""
    texto = s.ultima_mensagem if hasattr(s, 'ultima_mensagem') else ""

    # Verificar se há código colado
    codigo = None
    linguagem = "python"
    erro_descrito = ""

    if "```" in texto:
        partes = texto.split("```")
        for i, parte in enumerate(partes):
            if i % 2 == 1:
                codigo = parte.strip()
                # Detectar linguagem
                if parte.strip().startswith("c#") or parte.strip().startswith("csharp"):
                    linguagem = "csharp"
                elif parte.strip().startswith("python"):
                    linguagem = "python"
                break
    elif len(texto) > 100:
        codigo = texto

    # Extrair descrição do erro
    palavras_erro = ["erro", "error", "exception", "falha", "bug", "problema", "não funciona", "travou"]
    for palavra in palavras_erro:
        if palavra in texto.lower():
            erro_descrito = texto
            break

    if not codigo:
        return (
            "Para corrigir um bug, preciso:\n"
            "- Ver o código com o erro\n"
            "- Saber qual erro está acontecendo\n"
            "- Em qual situação o bug ocorre\n\n"
            "Cole o código e descreva o erro, ou use `abrir <caminho>` "
            "para que eu analise o arquivo.\n\n"
            "**Informações úteis:**\n"
            "- Mensagem de erro completa\n"
            "- Stack trace se disponível\n"
            "- Passos para reproduzir o bug"
        )

    # Analisar o código buscando problemas comuns
    analise = analisar_codigo_completo(codigo, linguagem)

    resposta = "🐛 **Análise de Bug**\n\n"

    if analise["total_problemas"] > 0:
        resposta += "Encontrei problemas que podem estar causando o bug:\n\n"
        for problema in analise["problemas"][:3]:
            if problema.gravidade.value in ["CRÍTICO", "ALTO"]:
                resposta += f"🔴 **{problema.tipo}** (Linha {problema.linha})\n"
                resposta += f"   {problema.descricao}\n"
                resposta += f"   💡 {problema.sugestao}\n\n"
    else:
        resposta += "Não encontrei problemas óbvios no código que possam causar bugs.\n\n"

    resposta += "Para ajudar melhor, me diga:\n"
    resposta += "- Qual a mensagem de erro exata?\n"
    resposta += "- O que deveria acontecer e o que acontece?\n"
    resposta += "- Em que situação o bug ocorre?\n\n"
    resposta += "Com essas informações posso ser mais preciso na correção."

    return resposta


def _escrever_classe_resposta(s):
    """Gera código de classe."""
    gerador = GeradorDeCodigo()
    texto = s.ultima_mensagem.lower() if hasattr(s, 'ultima_mensagem') else ""

    # Tentar extrair nome da classe
    nome_classe = "MinhaClasse"
    for palavra in texto.split():
        if palavra[0].isupper() and len(palavra) > 3:
            nome_classe = palavra
            break

    params = gerador.extrair_parametros(texto)
    codigo = gerador.gerar_classe(nome_classe, params.get("linguagem", "csharp"))

    return (
        f"**Aqui está uma classe `{nome_classe}` em {params.get('linguagem', 'C#')}:**\n\n"
        f"```\n{codigo}\n```\n\n"
        f"Você pode adicionar propriedades e métodos conforme necessário. "
        f"Quer que eu adicione algo específico?"
    )


def _escrever_funcao_resposta(s):
    """Gera código de função."""
    gerador = GeradorDeCodigo()
    texto = s.ultima_mensagem.lower() if hasattr(s, 'ultima_mensagem') else ""

    params = gerador.extrair_parametros(texto)

    # Se for soma específica
    if "soma" in texto or "adição" in texto or "somar" in texto:
        codigo = gerador.gerar_funcao_soma(params.get("linguagem", "csharp"))
        return (
            f"**Aqui está uma função de soma em {params.get('linguagem', 'C#')}:**\n\n"
            f"```\n{codigo}\n```\n\n"
            f"Quer que eu crie outras funções matemáticas?"
        )

    return (
        "Para criar uma função, preciso saber:\n"
        "- O que a função deve fazer?\n"
        "- Quais parâmetros?\n"
        "- O que deve retornar?\n"
        "- Qual linguagem?\n\n"
        "Me dá esses detalhes que eu escrevo a função.\n\n"
        "**Exemplos do que posso criar:**\n"
        "- Funções matemáticas (soma, multiplicação, etc.)\n"
        "- Funções de validação (email, CPF, telefone)\n"
        "- Funções de formatação (data, moeda)\n"
        "- Funções de processamento de dados"
    )


def _explicar_conceito_resposta(s):
    """Explica um conceito de programação."""
    texto = s.ultima_mensagem.lower() if hasattr(s, 'ultima_mensagem') else ""

    # Tentar identificar o conceito
    explicacao = explicar_conceito(texto)

    if "não encontrado" in explicacao:
        return (
            f"{explicacao}\n\n"
            "**Conceitos que posso explicar:**\n"
            "- Injeção de dependência\n"
            "- SOLID principles\n"
            "- REST API\n"
            "- MVC\n"
            "- Design patterns\n"
            "- Async/await\n"
            "- Herança\n"
            "- Polimorfismo\n"
            "- Encapsulamento\n"
            "- Abstração\n"
            "- Interfaces\n\n"
            "Me diga qual quer saber!"
        )

    return explicacao


def _sugerir_arquitetura_resposta(s):
    """Sugere arquitetura para um projeto."""
    texto = s.ultima_mensagem.lower() if hasattr(s, 'ultima_mensagem') else ""

    arquitetura = obter_arquitetura(texto)

    if arquitetura is None:
        return (
            "Para sugerir uma arquitetura, preciso saber:\n"
            "- Qual tipo de projeto? (API, web, desktop, mobile)\n"
            "- Qual escala esperada? (pequeno, médio, grande)\n"
            "- Tem algum requisito específico? (performance, segurança, etc.)\n\n"
            "**Tipos de projeto que posso sugerir:**\n"
            "- API REST\n"
            "- Microserviços\n"
            "- E-commerce\n"
            "- Aplicação mobile\n"
            "- Dashboard\n"
            "- Sistema realtime\n"
            "- Serverless\n"
            "- IoT platform\n\n"
            "Me diga o tipo de projeto!"
        )

    resposta = f"**{arquitetura['nome']}**\n\n"
    resposta += f"{arquitetura['descricao']}\n\n"

    if "camadas" in arquitetura:
        resposta += "**Camadas:**\n"
        for camada in arquitetura["camadas"]:
            resposta += f"- {camada}\n"
        resposta += "\n"

    if "componentes" in arquitetura:
        resposta += "**Componentes:**\n"
        for componente in arquitetura["componentes"]:
            resposta += f"- {componente}\n"
        resposta += "\n"

    if "modulos" in arquitetura:
        resposta += "**Módulos:**\n"
        for modulo in arquitetura["modulos"]:
            resposta += f"- {modulo}\n"
        resposta += "\n"

    resposta += "**Vantagens:**\n"
    for vantagem in arquitetura["vantagens"]:
        resposta += f"- {vantagem}\n"
    resposta += "\n"

    if "desafios" in arquitetura:
        resposta += "**Desafios:**\n"
        for desafio in arquitetura["desafios"]:
            resposta += f"- {desafio}\n"
        resposta += "\n"

    resposta += "**Tecnologias sugeridas:**\n"
    for linguagem, tecnologias in arquitetura["tecnologias_sugeridas"].items():
        resposta += f"- **{linguagem}**: {', '.join(tecnologias)}\n"

    return resposta

INVESTIGA = {
    # ── Máquina ───────────────────────────────────────────────────────
    "estado_da_maquina": maquina,
    "status_sistema":    maquina,
    "status_api":        maquina,
    "otimizacao":        maquina,

    # ── Logs ──────────────────────────────────────────────────────────
    "ver_logs":          procurar_logs,
    "logs_sistema":      procurar_logs,

    # ── Navegação ─────────────────────────────────────────────────────
    "listar_pasta":       listar_pasta,
    "estrutura_do_projeto": estrutura_projeto,

    # ── Git (só leitura) ──────────────────────────────────────────────
    "git_estado":         git_status,
    "git_historico":      git_log,
    "git_diferenca":      git_diff,

    # ── Máquina / ferramentas ─────────────────────────────────────────
    "processos":          processos_rodando,
    "espaco_em_disco":    estado_disco,
    "versao_das_ferramentas": versoes_ferramentas,

    # ── Diagnóstico técnico ───────────────────────────────────────────
    "erro_de_compilacao":  diagnosticar_compilacao,
    "erro_em_execucao":    diagnosticar_execucao,
    "nao_abre":            diagnosticar_nao_abre,
    "lentidao":            diagnosticar_lentidao,
    "travou":              diagnosticar_travou,
    "porta_ocupada":       diagnosticar_porta,
    "permissao_negada":    diagnosticar_permissao,
    "dependencia_faltando": diagnosticar_dependencia,
    "nao_conecta":         diagnosticar_conexao,

    # ── Diagnóstico geral ─────────────────────────────────────────────
    "diagnostico_problema": mexidos_agora,
    "furo_sistema":         mexidos_agora,
    "integracao_sistemas":  mexidos_agora,
}


# ══════════════════════════════════════════════════════════════════════
#  INTEGRAÇÃO COM O GerenciadorConhecimento (camada 3 — base de casos)
# ══════════════════════════════════════════════════════════════════════
#
# O GerenciadorConhecimento sabe sobre os projetos Autonomous, SO-Espacial
# e a integração entre eles. Quando o diagnóstico técnico detecta um
# problema que aparece na base de casos, complementa a resposta com a
# solução conhecida — sem substituir o diagnóstico, só enriquecendo.

_conhecimento = None   # carregado uma vez, só se necessário


def _gc():
    """Devolve o GerenciadorConhecimento, carregando na primeira chamada."""
    global _conhecimento
    if _conhecimento is None:
        try:
            from conhecimento.base import GerenciadorConhecimento
            _conhecimento = GerenciadorConhecimento()
        except Exception:
            _conhecimento = False   # falhou — não tenta de novo
    return _conhecimento if _conhecimento else None


def _complementar_com_conhecimento(texto_base, frase_usuario):
    """Tenta enriquecer a resposta com casos conhecidos da base.

    Retorna o texto original se não achar nada relevante — não inventa.
    """
    gc = _gc()
    if gc is None:
        return texto_base

    frase = (frase_usuario or "").lower()
    try:
        from conhecimento.base import Sistema
        # Detecta qual sistema o usuário menciona
        candidatos = []
        if any(t in frase for t in ("autonomous", "loja", "rfid", "adminapp",
                                    "clientapp", "blazor", "dotnet", ".net",
                                    "webapi", "esp32", "sql")):
            candidatos.append(Sistema.AUTONOMOUS)
        if any(t in frase for t in ("so espacial", "espacial", "camera", "câmera",
                                    "yolo", "kalman", "visão", "visao",
                                    "fps", "prateleira")):
            candidatos.append(Sistema.SO_ESPACIAL)
        if any(t in frase for t in ("integr", "monitor espacial", "gerente espacial",
                                    "junto", "comunicar", "os dois")):
            candidatos.append(Sistema.INTEGRACAO)

        if not candidatos:
            return texto_base

        partes_extras = []
        for sistema in candidatos:
            conhecimento = gc.obter_conhecimento(sistema)
            if not conhecimento:
                continue
            # Procura problemas cujo sintoma aparece na frase
            for problema in conhecimento.problemas_comuns:
                sintoma_palavras = problema.get("sintomas", "").lower().split()
                if any(p in frase for p in sintoma_palavras if len(p) > 4):
                    solucao = gc.sugerir_solucao(sistema, problema["problema"])
                    if solucao:
                        partes_extras.append(
                            f"**Caso conhecido no {sistema.value.replace('_', ' ').title()}** "
                            f"— {problema['problema']}:\n"
                            f"{solucao['solucao']}"
                        )
                    break   # um caso por sistema é suficiente

        if partes_extras:
            return texto_base + "\n\n---\n\n" + "\n\n".join(partes_extras)
        return texto_base
    except Exception:
        return texto_base


_ABRIR = ("abrir_projeto", "abrir_arquivo", "abrir_no_editor")

# ══════════════════════════════════════════════════════════════════════
#  CRIAR PROJETO — as três redes do compositor
# ══════════════════════════════════════════════════════════════════════
# Carregado UMA VEZ, e preguiçosamente: o `criar.py` abre três modelos de
# disco, e fazer isso a cada frase deixaria a resposta lenta à toa.
_CRIADOR = None


def _criador():
    global _CRIADOR
    if _CRIADOR is None:
        from painel.criar import Criador
        _CRIADOR = Criador()
    return _CRIADOR


def _extrair_fazer_da_frase(frase):
    """'calculadora em csharp para calcular a média' → 'calcular a média'.

    O `entender` lê linguagem, tipo e nome; a finalidade fica escondida
    no fim da frase, depois de um marcador. Sem isto, o usuário que
    responde tudo de uma vez ("csharp, console, calculadora para medir
    as notas") via o nome inteiro grudado na finalidade, e a pergunta
    volta no círculo. Com isto, `fazer` sai da própria resposta.
    """
    import re
    baixa = (frase or "").strip()
    marcadores = [
        r"\bpara\s+", r"\bpra\s+", r"\bpro\b\s*", r"\bpara\s+que\s+",
        r"\bcom o objetivo de\s+", r"\bcom a finalidade de\s+",
        r"\boa finalidade (é|e) `?\s+", r"\bo objetivo (é|e) `?\s+",
        r"\bque calcula ", r"\bque vai ", r"\bque deve ", r"\bque faz ",
        r"\bserve para\s+", r"\bserve pra\s+", r"\bdestinado a\s+",
        r"\bdestinada a\s+", r"\ba fim de\s+",
    ]
    melhor = ""
    for padrao in marcadores:
        m = re.search(padrao, baixa, re.IGNORECASE)
        if m:
            resto = baixa[m.end():].strip(" .,!?:;\"'")
            if len(resto.split()) >= 2 and len(resto) >= 6:
                melhor = resto
                break
    # "para mim", "para você" não é finalidade de projeto.
    sozinho = {"mim", "você", "voce", "vc", "a gente", "ele", "ela",
               "eles", "elas", "gente", "mim.", "você."}
    if melhor.lower() in sozinho or not melhor:
        return ""
    return melhor


def _pedido_pela_metade(pedido, criador, frase):
    """A mensagem do que já foi entendido e do que ainda falta.

    Antes eram dois blocos crus ("Já tenho isto:" + lista de `faltando`)
    e um fecho robótico sempre igual. A pessoa via o etiquetador falhou
    ("você escreveu 'c#,' e eu ainda não sei escrever nessa linguagem")
    e não tinha ideia de QUANTO já tinha respondido nem do que exatamente
    faltava. Agora: resume o que está na mão, pede só o que falta e sugere
    a resposta em lista — que o `entender` aprendeu a ler campo por campo.

    E o tom importa: se a rede reconheceu `criar_projeto` com confiança e
    o pedido veio sem NENHUM campo ("quero criar um projeto do zero"),
    responder "ainda não entendi o pedido inteiro" é mentir para quem
    acabou de ver 93% na tela. A mensagem acolhe a ideia, pede o esqueleto
    e ainda oferece uma PROPOSTA para começar — sem inventar nada: é uma
    sugestão declarada como sugestão, e quem decide é a pessoa.
    """
    entendido = "; ".join(
        f"**{pedido[campo]}**" for campo in ("linguagem", "tipo", "nome")
        if pedido.get(campo))
    faltando = "\n".join(f"- {q}" for q in pedido["faltando"])

    # A FINALIDADE É SEMPRE UMA PERGUNTA TAMBÉM. Antes ela só aparecia
    # depois de linguagem/tipo/nome fechados — mas o Eduardo quer ver o
    # pedido inteiro desde a primeira pergunta, para saber o que ele vai
    # precisar responder. Se ainda não foi dita, entra na lista.
    if not pedido.get("fazer"):
        falta_fazer = ("- que finalidade vai ter?\n" if not pedido["faltando"]
                       else "\n- que finalidade vai ter?")
        faltando = faltando + falta_fazer if faltando else falta_fazer.strip()

    # AS OPÇÕES NÃO COLAM NAS PERGUNTAS. Lista colada vira resposta colada:
    # o usuário copia "csharp, html, javascript…" e o etiquetador lê
    # "csharp" como nome da lista. Pergunta curta + opções separadas
    # seguem a lição do criar.py ("perguntar em branco é perguntar mal")
    # sem transformar a pergunta num menu.
    opcoes = ""
    if not pedido.get("linguagem"):
        lings = criador.linguagens_que_sei()
        if lings:
            opcoes += f"Linguagens: {', '.join(lings)}\n"
    if not pedido.get("tipo"):
        tipos = criador.tipos_que_sei(pedido.get("linguagem"))
        if tipos:
            opcoes += f"Tipos: {', '.join(tipos)}\n"
    if not pedido.get("nome"):
        opcoes += "Sugestão de nome: algo curto, sem espaço, que diga o que é (ex: `calculadora`)\n"

    fecho = ("Pode responder do seu jeito — uma de cada vez ou tudo junto "
             "separando por vírgula, com a finalidade no fim "
             "(ex: `csharp, console, calculadora para calcular a média`).")
    if entendido:
        corpo = "\n\n".join([
            f"Fechou — já anotei: {entendido}.",
            _conversa_pedido(pedido, faltando, opcoes, fecho),
        ])
        return corpo
    # Pedido sem NENHUM campo (reconhecido como projeto com confiança):
    # além de pedir o esqueleto, fecha com o convite para responder à
    # vontade — sem proposta "palpada" (o Eduardo pediu para tirar o
    # "meu palpite é csharp + console").
    fecho_proposto = ("Me responde com o que tiver (mesmo que falte "
                      "algum campo) que eu preencho o resto.")
    corpo = _conversa_pedido(pedido, faltando, opcoes, fecho_proposto)
    parts = corpo.split("\n\n")
    # Sem campo nenhum, o gancho é acolher a ideia antes das perguntas.
    args = "projeto"
    parts[0] = f"Bora! Vamos desenhar o seu **{args}** juntos.\n\n" + parts[0]
    return "\n\n".join(parts)


def _conversa_pedido(pedido, faltando, opcoes, fecho):
    """Converte a lista de faltas numa conversa — mas sem esconder as opções.

    As perguntas viram o que uma pessoa diria tentando entender o que o
    outro quer ("me conta: que tipo de programa você imagina?"), em vez de
    um formulário. As opções continuam ali, logo abaixo, para quem prefere
    responder olhando — a lição do criar.py.

    `faltando` já veio como texto com "- " na frente; os itens que não são
    uma das quatro perguntas ("a linguagem não sei", "o tipo não conheço")
    são AVISOS do etiquetador e entram antes, pois explicam o obstáculo.
    """
    import re
    itens = [linha[2:] for linha in faltando.splitlines() if linha]
    avisos, perguntas = [], []
    for item in itens:
        baixo = item.lower()
        if any(baixo.startswith(chave) for chave in
               ("em que linguagem", "que tipo", "como o projeto",
                "que finalidade")):
            perguntas.append(item)
        else:
            avisos.append(item)
    bloqueio = (opcoes.strip() + "\n" if opcoes else "") + fecho
    if not perguntas:
        return ("\n".join(f"- {a}" for a in avisos)
                + ("\n\n" if avisos else "") + bloqueio)
    # Pergunta por pergunta, com o tom de quem escuta.
    conv = []
    for p in perguntas:
        chave = p.strip().strip("?").strip().lower()
        conv.append({"em que linguagem": "que linguagem você quer usar",
                     "que tipo de projeto": "que tipo de programa você imagina",
                     "como o projeto vai se chamar": "como ele vai se chamar",
                     "que finalidade vai ter": "o que ele vai fazer por você (a finalidade)"}
                    .get(chave, p))
    aberturas = len(conv) - 1
    fala = "Pra eu montar certinho, me conta: "
    if aberturas > 0:
        fala += ", ".join(conv[:-1]) + " e " + conv[-1] + "."
    else:
        fala += conv[0] + "."
    corpo = fala + "\n\n" + bloqueio
    if avisos:
        corpo = ("- " + "\n- ".join(avisos)) + "\n\n" + corpo
    return corpo


def _pedido_falta_fazer(pedido):
    """Antes do plano, a pergunta do propósito.

    A estrutura sai da MEMÓRIA do compositor; o propósito é a parte que
    só quem pediu sabe. Perguntar não é burocracia — é a conversa que o
    Eduardo pediu: entender o projeto antes de criar, e deixar a pessoa
    ver que a estrutura já está decidida antes do `sim`.
    """
    melhor = {"console": "programa de linha de comando",
              "api": "serviço (API/host)",
              "biblioteca": "biblioteca de código",
              "site": "página/site"}.get(pedido.get("tipo"), pedido.get("tipo"))
    return (
        f"Já tenho a estrutura: um **{melhor}** em **{pedido['linguagem']}** "
        f"chamado **{pedido['nome']}**.\n\n"
        f"Agora me conta o mais importante: **o que ele vai fazer por você?** "
        f"Me diz numa frase — ex: *\"calcular a média das notas dos alunos\"*.")


def criar_projeto(sessao, frase):
    """Entende o pedido, monta o plano, MOSTRA e pergunta.

    NADA VAI PARA O DISCO AQUI. Esta função devolve texto; escrever é
    outra chamada, depois do sim. Um programa que cria dezessete arquivos
    na sua pasta enquanto você ainda está lendo o que ele entendeu não é
    assistente, é acidente.
    """
    c = _criador()
    if not c.pronto:
        return ("Ainda não sei montar projeto: falta treinar o compositor.\n\n"
                "```\npython programas/treinar_compositor.py\n```\n\n"
                + "\n".join(f"- {x}" for x in c.faltou))

    # O QUE JÁ FOI ENTENDIDO NESTA CONVERSA ENTRA JUNTO.
    #
    # Sem isto, responder "console" à pergunta "que tipo?" chegava como
    # uma frase sem linguagem e sem nome, e ele perguntava tudo de novo —
    # em círculo, para sempre. Agora a frase nova só ACRESCENTA.
    antes = getattr(sessao, "pedido_projeto", None)

    # ── VOLTAR AO QUE FICOU PELA METADE ──────────────────────────────
    #
    # Se não há pedido ativo mas há um parado, esta frase provavelmente é
    # a volta. Duas maneiras de casar, e as duas são conservadoras:
    #
    #   · a frase CITA o nome de um pedido parado → é aquele;
    #   · a frase não traz nome nenhum e há um parado → é ele, porque
    #     "faz em php" depois de "cria um projeto agenda" só pode ser
    #     sobre o agenda.
    #
    # Se a frase traz um nome NOVO, é projeto novo, e o parado continua
    # parado — voltar por engano seria pior do que perguntar.
    retomado = None
    if antes is None and getattr(sessao, "pedidos_parados", None):
        baixa = (frase or "").lower()
        for q in list(sessao.pedidos_parados):
            nome = (q.get("nome") or "").strip().lower()
            if nome and nome in baixa:
                retomado = sessao.retomar_pedido(q.get("nome"))
                break
        if retomado is None:
            provisorio = c.entender(frase, codigo=sessao.ultimo_codigo_colado())
            if not provisorio.get("nome"):
                retomado = sessao.retomar_pedido()
        antes = retomado

    pedido = c.entender(frase, codigo=sessao.ultimo_codigo_colado(), antes=antes)
    # O PROPÓSITO SOBREVIVE À RESPOSTA. `entender` só reconhece
    # linguagem, tipo e nome; o `fazer` é contexto meu, e vem de `antes`
    # (guardado quando eu perguntei) ou da frase seguinte.
    if antes and antes.get("fazer"):
        pedido["fazer"] = antes["fazer"]
        pedido["de_onde"]["fazer"] = antes.get("de_onde", {}).get(
            "fazer", "você me contou")
    # A FINALIDADE PODE VIR COLADA NA MESMA RESPOSTA ("csharp, console,
    # calculadora para medir as notas"). O etiquetador lê isso como nome
    # gigante; tirar o trecho da finalidade de volta é ler a frase.
    if not pedido.get("fazer"):
        extraido = _extrair_fazer_da_frase(frase)
        if extraido:
            pedido["fazer"] = extraido
            pedido["de_onde"]["fazer"] = "você me contou"
            if pedido.get("nome"):
                corte = pedido["nome"].lower().split(" para", 1)[0]
                if corte and corte != pedido["nome"].lower():
                    pedido["nome"] = corte
                    pedido["de_onde"]["nome"] = f"você escreveu '{corte}'"

    # EU PERGUNTEI A FINALIDADE E ESTA FRASE É A RESPOSTA. Quem tem o
    # contexto sou eu, que acabei de perguntar — mandar "vai calcular a
    # dieta das pessoas" para o etiquetador de campos é pedir para ele
    # inventar linguagem/tipo/nome de novo (medido: ele lê "dieta das"
    # como linguagem e o pedido roda em círculo). O pedido guardado já
    # tem os campos; o `fazer` vem desta frase, com o "para/pra" cortado,
    # e os avisos do etiquetador não valem mais (a pergunta era minha).
    if (antes or {}).get("aguardando_fazer") and not pedido.get("fazer"):
        baixa = frase.strip().strip("?.!, ")
        import re as _re_ped
        baixa = _re_ped.sub(
            r"^(?:para|pra|para que|pro|pras|pros)\s+",
            "", baixa, flags=_re_ped.IGNORECASE).strip()
        if baixa:
            pedido["fazer"] = baixa
            pedido["de_onde"]["fazer"] = "você me contou"
        pedido["faltando"] = []     # os avisos eram ruído da minha pergunta
    volta = ""
    if retomado:
        como = retomado.get("nome") or retomado.get("linguagem") or "o de antes"
        volta = f"Voltando ao projeto **{como}**, de onde a gente parou.\n\n"

    if pedido["faltando"]:
        # guarda o meio-caminho: é isto que quebra o círculo
        guarda = {
            "linguagem": pedido["linguagem"], "tipo": pedido["tipo"],
            "nome": pedido["nome"], "de_onde": pedido["de_onde"],
            "frase": (retomado or {}).get("frase") or frase}
        if pedido.get("fazer"):
            guarda["fazer"] = pedido["fazer"]
            guarda["de_onde"]["fazer"] = pedido["de_onde"].get("fazer", "você me contou")
        sessao.pedido_projeto = guarda
        sessao.virar("aguardando_voce")
        return (volta
                + _pedido_pela_metade(pedido, c, frase))

    # ── ANTES DO PLANO, O PROPÓSITO ───────────────────────────────────
    #
    # A estrutura já está decidida; o que falta é o "o que faz". Perguntar
    # uma frase e parar é a parte da conversa que não força ninguém a
    # adivinhar, e a resposta entra no plano e na mensagem de confirmação.
    if not pedido.get("fazer"):
        if (antes or {}).get("aguardando_fazer"):
            # você acabou de responder a minha pergunta
            fazer_bruto = frase.strip().strip("?.!, ").strip()
            import re as _re_fazer
            fazer_bruto = _re_fazer.sub(
                r"^(?:para|pra|para que|pro|pras|pros)\s+",
                "", fazer_bruto, flags=_re_fazer.IGNORECASE)
            pedido["fazer"] = fazer_bruto
            pedido["de_onde"]["fazer"] = "você me contou"
        else:
            sessao.pedido_projeto = {
                "linguagem": pedido["linguagem"], "tipo": pedido["tipo"],
                "nome": pedido["nome"], "de_onde": pedido["de_onde"],
                "frase": (retomado or {}).get("frase") or frase,
                "aguardando_fazer": True}
            sessao.virar("aguardando_voce")
            return volta + _pedido_falta_fazer(pedido)

    # tudo na mão: o pedido acabou, e o que vai para a tela é o PLANO.
    # Sai da garagem também — um pedido que virou plano não está mais
    # esperando ninguém.
    sessao.pedido_projeto = None
    if getattr(sessao, "pedidos_parados", None) and pedido.get("nome"):
        alvo = pedido["nome"].strip().lower()
        sessao.pedidos_parados = [q for q in sessao.pedidos_parados
                                  if (q.get("nome") or "").strip().lower() != alvo]
    plano = c.planejar(pedido["linguagem"], pedido["tipo"],
                       c.nome_de_pasta(pedido["nome"]))
    # O propósito não muda a ESTRUTURA — que sai da memória —, mas faz
    # parte do que o usuário vai confirmar, então vai no plano.
    if pedido.get("fazer"):
        plano["fazer"] = pedido["fazer"]
    return sessao.propor_projeto(plano, c.arvore(plano))


def responder(sessao, intencao, frase_usuario=""):
    """Devolve (texto, investigou) — ou None se a intenção não tem ação.

    frase_usuario é usada para enriquecer diagnósticos com a base de casos
    quando o usuário menciona um dos sistemas conhecidos.
    """
    if intencao == "criar_projeto":
        return criar_projeto(sessao, frase_usuario), False

    # "O QUE VOCÊ ENTENDEU DO MEU PEDIDO?" (intenção `revisar_entendimento`)
    # Também não é fala pronta: a resposta é o RESUMO do pedido em aberto,
    # não um texto decorado. Se não há pedido, o resumo não existe — avisar
    # é a resposta honesta.
    if intencao == "revisar_entendimento":
        if getattr(sessao, "pedido_projeto", None) or \
           getattr(sessao, "_tem_projeto_pendente", lambda: False)():
            return sessao._revisar_pedido(), False
        return ("Não tenho nenhum pedido aberto para resumir agora — "
                "me diz o que você precisa e eu começo a anotar."), False

    # A CONSULTA AOS DADOS entra antes das FALAS pelo mesmo motivo do
    # `criar_projeto`: ela não tem resposta pronta para devolver. Precisa
    # ler as classes de um projeto C# e MONTAR a consulta, e isso depende
    # da frase inteira, não só da intenção.
    if intencao == "consultar_dados":
        return _consultas.responder(sessao, frase_usuario), False

    # ── "SIM" ESCRITO NO CHAT VALE TANTO QUANTO O BOTÃO ──────────────
    #
    # Isto era um buraco de verdade, e o Eduardo caiu nele: o programa
    # perguntou "Confirma que eu crio isso em ...?", ele respondeu "sim",
    # a rede acertou a intenção com 98,7% de confiança — e a resposta foi
    # "Ok. Me diga o próximo passo.". A pasta ficou vazia.
    #
    # O motivo: `sessao.pendentes` só era consumido por `/api/confirmar`,
    # que é o BOTÃO do cartão. A intenção `confirmar` caía na fala pronta,
    # que não olha se existe alguma coisa pendurada esperando um sim.
    #
    # Uma pergunta feita em português tem de aceitar resposta em
    # português. O botão continua lá para quem prefere clicar.
    if intencao in ("confirmar", "cancelar") and getattr(sessao, "pendentes", None):
        # o último pendurado é o que a pergunta acabou de citar
        ident = max(sessao.pendentes)
        if intencao == "confirmar":
            sessao.confirmar(ident)
            # `confirmar` já escreve o cartão do que foi feito; devolver
            # texto aqui empilharia uma segunda resposta dizendo o mesmo
            return "", False
        sessao.recusar(ident)
        return "", False

    if intencao in _ABRIR:
        cam = sessao._caminho_da_frase(frase_usuario)
        if cam:
            if intencao == "abrir_no_editor":
                sessao.no_vscode(cam)
            else:
                sessao.abrir(cam)
            return "", False
        sessao._alvo_pendente = intencao
        texto = FALAS[intencao](sessao)
        return texto, False

    if intencao in FALAS:
        texto = FALAS[intencao](sessao)
        return texto, False

    if intencao in INVESTIGA:
        texto = INVESTIGA[intencao](sessao)
        # Para intenções de diagnóstico, tenta enriquecer com a base de casos
        if intencao in ("erro_de_compilacao", "erro_em_execucao", "nao_conecta",
                        "lentidao", "travou", "nao_abre", "diagnostico_problema",
                        "furo_sistema", "integracao_sistemas"):
            texto = _complementar_com_conhecimento(texto, frase_usuario)
        return texto, True

    return None
