# -*- coding: utf-8 -*-
"""OS DADOS DE ENSINO — exemplos dos quais a rede tira a regra.

NÃO SÃO MOLDES. A diferença importa e é a razão do desenho.

    molde       arquivo fixo que se copia. Pedir C#+api sem ter o molde
                de C#+api devolve nada.
    ensino      exemplo do qual se extrai (linguagem → sintaxe) e
                (tipo → estrutura), separadamente. Pedir C#+api sem
                nunca ter visto essa combinação COMPÕE a partir das duas.

É a fatoração que faz a diferença, e ela é testável: ensina-se algumas
combinações e pergunta-se por uma que não foi ensinada.

O PAPEL É A ETIQUETA QUE PERMITE COMPOR

Cada arquivo carrega um `papel`, não só um nome:

    principal   o que roda / o ponto de entrada
    leiame      o README
    ignorar     o .gitignore
    teste       o teste do principal
    projeto     o arquivo de projeto (.csproj, package.json)
    rota        onde ficam as rotas, num api
    estilo      o css, num site
    pagina      o html, num site

A rede aprende duas coisas separadas:

    (tipo)              → QUAIS papéis um projeto desse tipo tem
    (linguagem, papel)  → COMO esse papel se escreve nessa linguagem

Com as duas, C#+api sai de C#+console (como se escreve C#) mais
python+api (quais papéis um api tem). Nenhum molde de C#+api precisou
existir.

TODO EXEMPLO AQUI COMPILA — CONFERIDO, NÃO PROMETIDO

`conferir_ensino.py` roda os seis compiladores em cada `principal` antes
de o arquivo ser aceito como dado. Ensinar a partir de exemplo quebrado é
ensinar a quebrar.
"""

# {nome} é trocado pelo que a pessoa pediu; {Nome} é a versão com maiúscula.
ENSINO = [

# ══════════════════════════════════════════════════════════ python
{"linguagem": "python", "tipo": "console", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/main.py", "conteudo": '''"""{nome} — programa de console.

O QUE ELE FAZ, e por quê está escrito aqui em cima: quem abrir este
arquivo daqui a três meses precisa saber o motivo antes do como.
"""


def somar(a, b):
    """Soma dois números e devolve o total."""
    return a + b


def main():
    print("{nome} no ar")
    print("2 + 3 =", somar(2, 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''},
 {"papel": "teste", "caminho": "{nome}/testes/test_main.py", "conteudo": '''# -*- coding: utf-8 -*-
"""Um teste por comportamento, e o nome diz o que se espera."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import somar


def test_somar_dois_positivos():
    assert somar(2, 3) == 5


def test_somar_com_zero_devolve_o_outro():
    assert somar(7, 0) == 7
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

O que é, em uma linha.

## Como rodar

```
python main.py
```

## Como testar

```
python -m pytest testes/
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''__pycache__/
*.pyc
.venv/
.pytest_cache/
'''}]},

{"linguagem": "python", "tipo": "api", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/main.py", "conteudo": '''"""{nome} — servidor local.

ESCUTA EM 127.0.0.1 e não em 0.0.0.0: um servidor de estudo que aceita
conexão de fora da máquina é uma porta aberta que ninguém pediu.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rotas import ROTAS

PORTA = 8000


class Alca(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        tratar = ROTAS.get(self.path)
        if tratar is None:
            return self.responder({"erro": "nao encontrado"}, 404)
        self.responder(tratar())

    def responder(self, dado, codigo=200):
        corpo = json.dumps(dado, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def main():
    print(f"{nome} em http://127.0.0.1:{PORTA}")
    ThreadingHTTPServer(("127.0.0.1", PORTA), Alca).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''},
 {"papel": "rota", "caminho": "{nome}/rotas.py", "conteudo": '''"""As rotas, separadas do servidor.

O servidor sabe FALAR HTTP; as rotas sabem O QUE responder. Misturar os
dois faz com que trocar de servidor obrigue a reescrever as respostas.
"""


def saude():
    return {"estado": "de pe"}


def raiz():
    return {"nome": "{nome}", "rotas": sorted(ROTAS)}


ROTAS = {
    "/": raiz,
    "/saude": saude,
}
'''},
 {"papel": "teste", "caminho": "{nome}/testes/test_rotas.py", "conteudo": '''# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rotas import ROTAS, saude


def test_saude_responde_de_pe():
    assert saude()["estado"] == "de pe"


def test_a_raiz_lista_as_rotas():
    assert "/saude" in ROTAS
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

API local.

## Como rodar

```
python main.py
```

Escuta em `127.0.0.1:8000`.

## Rotas

| rota | devolve |
|---|---|
| `/` | o nome e a lista de rotas |
| `/saude` | se está de pé |
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''__pycache__/
*.pyc
.venv/
'''}]},

# ══════════════════════════════════════════════════════════ csharp
{"linguagem": "csharp", "tipo": "console", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/Program.cs", "conteudo": '''using System;

namespace {Nome}
{
    /// <summary>
    /// {nome} — programa de console.
    /// </summary>
    /// <remarks>
    /// O PORQUÊ vem antes do COMO. Quem abrir isto depois precisa saber
    /// o motivo de a classe existir antes de ler o que ela faz.
    /// </remarks>
    internal class Program
    {
        internal static int Somar(int a, int b) => a + b;

        static void Main()
        {
            Console.WriteLine("{nome} no ar");
            Console.WriteLine($"2 + 3 = {Somar(2, 3)}");
        }
    }
}
'''},
 {"papel": "projeto", "caminho": "{nome}/{nome}.csproj", "conteudo": '''<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>{Nome}</RootNamespace>
  </PropertyGroup>

</Project>
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

O que é, em uma linha.

## Como rodar

```
dotnet run
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''bin/
obj/
.vs/
*.user
'''}]},

{"linguagem": "csharp", "tipo": "biblioteca", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/Calculo.cs", "conteudo": '''using System;

namespace {Nome}
{
    /// <summary>Operações que a biblioteca oferece.</summary>
    public static class Calculo
    {
        /// <summary>Soma dois números.</summary>
        public static int Somar(int a, int b) => a + b;

        /// <summary>Divide, e recusa divisão por zero em vez de estourar depois.</summary>
        public static double Dividir(double a, double b)
        {
            if (b == 0) throw new ArgumentException("divisao por zero", nameof(b));
            return a / b;
        }
    }
}
'''},
 {"papel": "projeto", "caminho": "{nome}/{nome}.csproj", "conteudo": '''<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>{Nome}</RootNamespace>
  </PropertyGroup>

</Project>
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Biblioteca.

## Como usar

```csharp
using {Nome};

int total = Calculo.Somar(2, 3);
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''bin/
obj/
.vs/
'''}]},

# ══════════════════════════════════════════════════════════ javascript
{"linguagem": "javascript", "tipo": "console", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/main.js", "conteudo": '''// {nome} — programa de console.
//
// O PORQUÊ no topo: quem abrir isto depois precisa do motivo antes do como.

function somar(a, b) {
  return a + b;
}

function main() {
  console.log("{nome} no ar");
  console.log("2 + 3 =", somar(2, 3));
}

main();

module.exports = { somar };
'''},
 {"papel": "projeto", "caminho": "{nome}/package.json", "conteudo": '''{
  "name": "{nome}",
  "version": "0.1.0",
  "description": "",
  "main": "main.js",
  "scripts": {
    "start": "node main.js"
  },
  "license": "MIT"
}
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

O que é, em uma linha.

## Como rodar

```
node main.js
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''node_modules/
*.log
'''}]},

# ══════════════════════════════════════════════════════════ html
{"linguagem": "html", "tipo": "site", "arquivos": [
 {"papel": "pagina", "caminho": "{nome}/index.html", "conteudo": '''<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{nome}</title>
  <link rel="stylesheet" href="estilo.css">
</head>
<body>
  <header>
    <h1>{nome}</h1>
  </header>

  <main>
    <p>O que este site é, em uma linha.</p>
  </main>

  <script src="script.js"></script>
</body>
</html>
'''},
 {"papel": "estilo", "caminho": "{nome}/estilo.css", "conteudo": ''':root {
  color-scheme: light dark;
  --tinta: #1a1c22;
  --fundo: #ffffff;
}

@media (prefers-color-scheme: dark) {
  :root { --tinta: #e6e9f0; --fundo: #0f1116; }
}

* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 2rem;
  font: 16px/1.6 system-ui, sans-serif;
  color: var(--tinta);
  background: var(--fundo);
}

main { max-width: 42rem; margin: 0 auto; }
'''},
 {"papel": "principal", "caminho": "{nome}/script.js", "conteudo": '''// {nome} — o que a página faz.

document.addEventListener("DOMContentLoaded", () => {
  console.log("{nome} carregou");
});
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Site.

## Como ver

Abra `index.html` no navegador.
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''.DS_Store
*.log
'''}]},


# ══════════════════════════════════════════════════════════════════════
#  ACRESCENTADOS PARA O TESTE DE COMPOSIÇÃO TER CHÃO
#
#  Com 6 exemplos, quase todo papel aparecia numa linguagem só, e
#  "compor" seria adivinhar. Estes dão a cada papel pelo menos duas
#  linguagens e a cada tipo pelo menos dois — o mínimo para
#
#      (tipo)              → QUAIS papéis
#      (linguagem, papel)  → COMO esse papel se escreve
#
#  terem de onde tirar as duas metades. As 4 combinações guardadas lá
#  embaixo continuam fora, e de propósito com dificuldade diferente:
#
#      python+biblioteca   todo (linguagem, papel) já visto em python.
#                          Só a ESTRUTURA é nova. Se isto falhar, a
#                          ideia toda está errada.
#      csharp+api          rota em C# nunca visto: estrutura composta,
#      javascript+api      conteúdo de um arquivo tem que ser inventado.
#      javascript+site     pagina e estilo em javascript nunca vistos —
#                          o mais difícil dos quatro.
# ══════════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════ php
{"linguagem": "php", "tipo": "console", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/main.php", "conteudo": '''<?php
/**
 * {nome} — programa de console.
 *
 * O QUE ELE FAZ vem antes do como, porque quem abrir isto daqui a três
 * meses precisa do motivo primeiro.
 */
declare(strict_types=1);

function somar(int $a, int $b): int
{
    return $a + $b;
}

function main(): int
{
    echo "{nome} no ar\\n";
    echo "2 + 3 = " . somar(2, 3) . "\\n";
    return 0;
}

exit(main());
'''},
 {"papel": "teste", "caminho": "{nome}/testes/test_main.php", "conteudo": '''<?php
/** Um teste por comportamento, e o nome diz o que se espera. */
declare(strict_types=1);

require_once __DIR__ . '/../main.php';

function conferir(string $nome, bool $passou): void
{
    echo ($passou ? "ok   " : "FALHOU ") . $nome . "\\n";
    if (!$passou) {
        exit(1);
    }
}

conferir('somar dois positivos', somar(2, 3) === 5);
conferir('somar com zero devolve o outro', somar(7, 0) === 7);
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

O que é, em uma linha.

## Como rodar

```
php main.php
```

## Como testar

```
php testes/test_main.php
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''vendor/
composer.lock
*.log
'''}]},

{"linguagem": "php", "tipo": "api", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/index.php", "conteudo": '''<?php
/**
 * {nome} — servidor local.
 *
 * ESCUTA EM 127.0.0.1 e não em 0.0.0.0: um servidor de estudo que aceita
 * conexão de fora da máquina é uma porta aberta que ninguém pediu. Suba
 * com:  php -S 127.0.0.1:8000 index.php
 */
declare(strict_types=1);

require_once __DIR__ . '/rotas.php';

$caminho = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$rotas = rotas();

header('Content-Type: application/json; charset=utf-8');

if (!array_key_exists($caminho, $rotas)) {
    http_response_code(404);
    echo json_encode(['erro' => 'rota nao encontrada', 'caminho' => $caminho]);
    exit;
}

echo json_encode($rotas[$caminho]());
'''},
 {"papel": "rota", "caminho": "{nome}/rotas.php", "conteudo": '''<?php
/**
 * AS ROTAS FICAM SEPARADAS DO SERVIDOR de propósito: quem mexe no que a
 * api responde não precisa entender como o servidor escuta.
 */
declare(strict_types=1);

function rotas(): array
{
    return [
        '/' => fn(): array => ['nome' => '{nome}', 'estado' => 'no ar'],
        '/saude' => fn(): array => ['ok' => true],
        '/itens' => fn(): array => ['itens' => [
            ['id' => 1, 'nome' => 'primeiro'],
            ['id' => 2, 'nome' => 'segundo'],
        ]],
    ];
}
'''},
 {"papel": "teste", "caminho": "{nome}/testes/test_rotas.php", "conteudo": '''<?php
/** Testa as rotas sem subir servidor: a função é que tem que estar certa. */
declare(strict_types=1);

require_once __DIR__ . '/../rotas.php';

function conferir(string $nome, bool $passou): void
{
    echo ($passou ? "ok   " : "FALHOU ") . $nome . "\\n";
    if (!$passou) {
        exit(1);
    }
}

$rotas = rotas();
conferir('a raiz existe', array_key_exists('/', $rotas));
conferir('saude responde ok', $rotas['/saude']()['ok'] === true);
conferir('itens devolve uma lista', count($rotas['/itens']()['itens']) === 2);
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Api local em PHP.

## Como rodar

```
php -S 127.0.0.1:8000 index.php
```

## Rotas

| caminho  | devolve                 |
|----------|-------------------------|
| `/`      | nome e estado           |
| `/saude` | `{"ok": true}`        |
| `/itens` | a lista de itens        |

## Como testar

```
php testes/test_rotas.php
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''vendor/
composer.lock
*.log
'''}]},

{"linguagem": "php", "tipo": "biblioteca", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/src/{Nome}.php", "conteudo": '''<?php
/**
 * {nome} — biblioteca.
 *
 * BIBLIOTECA NÃO TEM PONTO DE ENTRADA: ela é feita para outro programa
 * chamar. Por isso aqui não tem `exit` nem `echo` solto — só a classe.
 */
declare(strict_types=1);

final class {Nome}
{
    /** Soma dois números e devolve o total. */
    public function somar(int $a, int $b): int
    {
        return $a + $b;
    }

    /** Diz se o texto está vazio depois de tirar os espaços das pontas. */
    public function vazio(string $texto): bool
    {
        return trim($texto) === '';
    }
}
'''},
 {"papel": "teste", "caminho": "{nome}/testes/test_{nome}.php", "conteudo": '''<?php
declare(strict_types=1);

require_once __DIR__ . '/../src/{Nome}.php';

function conferir(string $nome, bool $passou): void
{
    echo ($passou ? "ok   " : "FALHOU ") . $nome . "\\n";
    if (!$passou) {
        exit(1);
    }
}

$b = new {Nome}();
conferir('somar dois positivos', $b->somar(2, 3) === 5);
conferir('espaco em branco conta como vazio', $b->vazio('   ') === true);
conferir('texto com letra nao e vazio', $b->vazio(' a ') === false);
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Biblioteca em PHP. Não roda sozinha — é chamada por outro programa.

## Como usar

```php
require_once 'src/{Nome}.php';

$b = new {Nome}();
echo $b->somar(2, 3);
```

## Como testar

```
php testes/test_{nome}.php
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''vendor/
composer.lock
*.log
'''}]},

{"linguagem": "php", "tipo": "site", "arquivos": [
 {"papel": "pagina", "caminho": "{nome}/index.php", "conteudo": '''<?php
$titulo = '{nome}';
$itens = ['primeiro', 'segundo', 'terceiro'];
?>
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= htmlspecialchars($titulo) ?></title>
  <link rel="stylesheet" href="estilo.css">
</head>
<body>
  <header class="topo">
    <h1><?= htmlspecialchars($titulo) ?></h1>
  </header>
  <main class="conteudo">
    <ul class="lista">
      <?php foreach ($itens as $item): ?>
        <li class="item"><?= htmlspecialchars($item) ?></li>
      <?php endforeach; ?>
    </ul>
  </main>
</body>
</html>
'''},
 {"papel": "estilo", "caminho": "{nome}/estilo.css", "conteudo": ''':root {
  --fundo: #101018;
  --texto: #e8e8f0;
  --destaque: #7c8cff;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: var(--fundo);
  color: var(--texto);
}

.topo {
  padding: 24px;
  border-bottom: 1px solid #2a2a3a;
}

.conteudo {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px;
}

.lista {
  list-style: none;
  padding: 0;
}

.item {
  padding: 12px 16px;
  border-radius: 8px;
  background: #1a1a26;
  margin-bottom: 8px;
}

.item:hover {
  outline: 2px solid var(--destaque);
}
'''},
 {"papel": "principal", "caminho": "{nome}/servidor.php", "conteudo": '''<?php
/**
 * {nome} — sobe o site na sua máquina.
 *
 * 127.0.0.1 E NÃO 0.0.0.0: site de estudo aberto para a rede é porta
 * aberta que ninguém pediu.
 */
declare(strict_types=1);

$porta = 8000;
$raiz = __DIR__;

echo "{nome} em http://127.0.0.1:$porta\\n";
echo "para parar: Ctrl+C\\n";

$comando = sprintf(
    'php -S 127.0.0.1:%d -t %s',
    $porta,
    escapeshellarg($raiz)
);
passthru($comando);
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Site em PHP com página, estilo e um servidor local.

## Como rodar

```
php servidor.php
```

Depois abra http://127.0.0.1:8000
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''vendor/
composer.lock
*.log
'''}]},

# ══════════════════════════════════════════════════════════════ python
{"linguagem": "python", "tipo": "site", "arquivos": [
 {"papel": "pagina", "caminho": "{nome}/publico/index.html", "conteudo": '''<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{nome}</title>
  <link rel="stylesheet" href="estilo.css">
</head>
<body>
  <header class="topo">
    <h1>{nome}</h1>
  </header>
  <main class="conteudo">
    <ul class="lista">
      <li class="item">primeiro</li>
      <li class="item">segundo</li>
      <li class="item">terceiro</li>
    </ul>
  </main>
</body>
</html>
'''},
 {"papel": "estilo", "caminho": "{nome}/publico/estilo.css", "conteudo": ''':root {
  --fundo: #101018;
  --texto: #e8e8f0;
  --destaque: #7c8cff;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: var(--fundo);
  color: var(--texto);
}

.topo {
  padding: 24px;
  border-bottom: 1px solid #2a2a3a;
}

.conteudo {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px;
}

.lista {
  list-style: none;
  padding: 0;
}

.item {
  padding: 12px 16px;
  border-radius: 8px;
  background: #1a1a26;
  margin-bottom: 8px;
}

.item:hover {
  outline: 2px solid var(--destaque);
}
'''},
 {"papel": "principal", "caminho": "{nome}/servidor.py", "conteudo": '''# -*- coding: utf-8 -*-
"""{nome} — sobe o site na sua máquina.

ESCUTA EM 127.0.0.1 e não em 0.0.0.0: site de estudo aberto para a rede
é porta aberta que ninguém pediu.
"""
import http.server
import socketserver
from pathlib import Path

PORTA = 8000
RAIZ = Path(__file__).resolve().parent / "publico"


class Entrega(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)


def main():
    with socketserver.TCPServer(("127.0.0.1", PORTA), Entrega) as servidor:
        print(f"{nome} em http://127.0.0.1:{PORTA}")
        print("para parar: Ctrl+C")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\\nparado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Site servido por um programa Python, sem biblioteca de fora.

## Como rodar

```
python servidor.py
```

Depois abra http://127.0.0.1:8000
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''__pycache__/
*.pyc
.venv/
'''}]},

# ══════════════════════════════════════════════════════════════ csharp
{"linguagem": "csharp", "tipo": "site", "arquivos": [
 {"papel": "pagina", "caminho": "{nome}/publico/index.html", "conteudo": '''<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{nome}</title>
  <link rel="stylesheet" href="estilo.css">
</head>
<body>
  <header class="topo">
    <h1>{nome}</h1>
  </header>
  <main class="conteudo">
    <ul class="lista">
      <li class="item">primeiro</li>
      <li class="item">segundo</li>
      <li class="item">terceiro</li>
    </ul>
  </main>
</body>
</html>
'''},
 {"papel": "estilo", "caminho": "{nome}/publico/estilo.css", "conteudo": ''':root {
  --fundo: #101018;
  --texto: #e8e8f0;
  --destaque: #7c8cff;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: var(--fundo);
  color: var(--texto);
}

.topo {
  padding: 24px;
  border-bottom: 1px solid #2a2a3a;
}

.conteudo {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px;
}

.lista {
  list-style: none;
  padding: 0;
}

.item {
  padding: 12px 16px;
  border-radius: 8px;
  background: #1a1a26;
  margin-bottom: 8px;
}

.item:hover {
  outline: 2px solid var(--destaque);
}
'''},
 {"papel": "principal", "caminho": "{nome}/Program.cs", "conteudo": '''using System;
using System.IO;
using System.Net;
using System.Text;

namespace {Nome}
{
    /// <summary>
    /// {nome} — sobe o site na sua máquina.
    ///
    /// ESCUTA EM 127.0.0.1 e não em +: site de estudo aberto para a rede
    /// é porta aberta que ninguém pediu.
    /// </summary>
    public static class Program
    {
        private const int Porta = 8000;

        public static int Main(string[] args)
        {
            string raiz = Path.Combine(AppContext.BaseDirectory, "publico");
            using var ouvinte = new HttpListener();
            ouvinte.Prefixes.Add($"http://127.0.0.1:{Porta}/");
            ouvinte.Start();
            Console.WriteLine($"{nome} em http://127.0.0.1:{Porta}");
            Console.WriteLine("para parar: Ctrl+C");

            while (ouvinte.IsListening)
            {
                HttpListenerContext ctx = ouvinte.GetContext();
                string pedido = ctx.Request.Url?.AbsolutePath ?? "/";
                if (pedido == "/")
                {
                    pedido = "/index.html";
                }

                string arquivo = Path.Combine(raiz, pedido.TrimStart('/'));
                if (File.Exists(arquivo))
                {
                    byte[] corpo = File.ReadAllBytes(arquivo);
                    ctx.Response.ContentType = Tipo(arquivo);
                    ctx.Response.OutputStream.Write(corpo, 0, corpo.Length);
                }
                else
                {
                    ctx.Response.StatusCode = 404;
                    byte[] corpo = Encoding.UTF8.GetBytes("nao encontrado");
                    ctx.Response.OutputStream.Write(corpo, 0, corpo.Length);
                }

                ctx.Response.Close();
            }

            return 0;
        }

        private static string Tipo(string arquivo)
        {
            return Path.GetExtension(arquivo) switch
            {
                ".html" => "text/html; charset=utf-8",
                ".css" => "text/css; charset=utf-8",
                ".js" => "text/javascript; charset=utf-8",
                _ => "application/octet-stream",
            };
        }
    }
}
'''},
 {"papel": "projeto", "caminho": "{nome}/{nome}.csproj", "conteudo": '''<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <RootNamespace>{Nome}</RootNamespace>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>

  <ItemGroup>
    <Content Include="publico\\**" CopyToOutputDirectory="PreserveNewest" />
  </ItemGroup>

</Project>
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Site servido por um programa C#, sem pacote de fora.

## Como rodar

```
dotnet run
```

Depois abra http://127.0.0.1:8000
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''bin/
obj/
*.user
'''}]},

{"linguagem": "csharp", "tipo": "api", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/Program.cs", "conteudo": '''using System;
using System.Net;
using System.Text;
using System.Text.Json;

namespace {Nome}
{
    /// <summary>
    /// {nome} — API local em C#, sem pacote de fora.
    ///
    /// ESCUTA EM 127.0.0.1 e não em +: servidor de estudo aberto para a
    /// rede é porta aberta que ninguém pediu.
    /// </summary>
    public static class Program
    {
        private const int Porta = 8000;

        public static int Main(string[] args)
        {
            using var ouvinte = new HttpListener();
            ouvinte.Prefixes.Add($"http://127.0.0.1:{Porta}/");
            ouvinte.Start();
            Console.WriteLine($"{nome} em http://127.0.0.1:{Porta}");
            Console.WriteLine("para parar: Ctrl+C");

            while (ouvinte.IsListening)
            {
                HttpListenerContext ctx = ouvinte.GetContext();
                string pedido = ctx.Request.Url?.AbsolutePath ?? "/";
                Responder(ctx, pedido);
            }

            return 0;
        }

        private static void Responder(HttpListenerContext ctx, string pedido)
        {
            bool tem = Rotas.Tabela.ContainsKey(pedido);
            object corpoDado = tem ? Rotas.Responder(pedido)
                                   : new { erro = "nao encontrado" };
            byte[] corpo = Encoding.UTF8.GetBytes(
                JsonSerializer.Serialize(corpoDado));
            ctx.Response.StatusCode = tem ? 200 : 404;
            ctx.Response.ContentType = "application/json; charset=utf-8";
            ctx.Response.ContentLength64 = corpo.Length;
            ctx.Response.OutputStream.Write(corpo, 0, corpo.Length);
            ctx.Response.Close();
        }
    }
}
'''},
 {"papel": "rota", "caminho": "{nome}/Rotas.cs", "conteudo": '''using System;
using System.Collections.Generic;

namespace {Nome}
{
    /// <summary>
    /// As rotas, separadas do servidor.
    ///
    /// O servidor sabe FALAR HTTP; as rotas sabem O QUE responder. Misturar
    /// os dois faz com que trocar de servidor obrigue a reescrever as
    /// respostas.
    /// </summary>
    public static class Rotas
    {
        public static readonly Dictionary<string, Func<object>> Tabela =
            new(StringComparer.OrdinalIgnoreCase)
            {
                ["/"] = Raiz,
                ["/saude"] = Saude,
            };

        public static object Responder(string caminho)
        {
            return Tabela[caminho]();
        }

        private static object Raiz()
        {
            return new { nome = "{nome}", rotas = string.Join(", ", Tabela.Keys) };
        }

        private static object Saude()
        {
            return new { estado = "de pe" };
        }
    }
}
'''},
 {"papel": "projeto", "caminho": "{nome}/{nome}.csproj", "conteudo": '''<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>{Nome}</RootNamespace>
  </PropertyGroup>

</Project>
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

API local em C#, sem pacote de fora.

## Como rodar

```
dotnet run
```

Depois, num outro terminal:

```
curl http://127.0.0.1:8000/saude
```

## Rotas

| rota | devolve |
|---|---|
| `/` | o nome e a lista de rotas |
| `/saude` | se está de pé |
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''bin/
obj/
*.user
'''}]},

# ══════════════════════════════════════════════════════════ javascript
{"linguagem": "javascript", "tipo": "biblioteca", "arquivos": [
 {"papel": "principal", "caminho": "{nome}/src/index.js", "conteudo": '''/**
 * {nome} — biblioteca.
 *
 * BIBLIOTECA NÃO TEM PONTO DE ENTRADA: ela é feita para outro programa
 * chamar. Por isso aqui não tem console.log solto — só o que se exporta.
 */

/** Soma dois números e devolve o total. */
function somar(a, b) {
  return a + b;
}

/** Diz se o texto está vazio depois de tirar os espaços das pontas. */
function vazio(texto) {
  return String(texto).trim() === '';
}

module.exports = { somar, vazio };
'''},
 {"papel": "teste", "caminho": "{nome}/testes/test_index.js", "conteudo": '''/** Um teste por comportamento, e o nome diz o que se espera. */
const assert = require('node:assert');
const { test } = require('node:test');

const { somar, vazio } = require('../src/index.js');

test('somar dois positivos', () => {
  assert.strictEqual(somar(2, 3), 5);
});

test('somar com zero devolve o outro', () => {
  assert.strictEqual(somar(7, 0), 7);
});

test('espaco em branco conta como vazio', () => {
  assert.strictEqual(vazio('   '), true);
});

test('texto com letra nao e vazio', () => {
  assert.strictEqual(vazio(' a '), false);
});
'''},
 {"papel": "projeto", "caminho": "{nome}/package.json", "conteudo": '''{
  "name": "{nome}",
  "version": "0.1.0",
  "description": "Biblioteca {nome}.",
  "main": "src/index.js",
  "scripts": {
    "test": "node --test testes/"
  },
  "license": "MIT"
}
'''},
 {"papel": "leiame", "caminho": "{nome}/README.md", "conteudo": '''# {nome}

Biblioteca em JavaScript. Não roda sozinha — é chamada por outro programa.

## Como usar

```js
const { somar } = require('./src/index.js');

console.log(somar(2, 3));
```

## Como testar

```
npm test
```
'''},
 {"papel": "ignorar", "caminho": "{nome}/.gitignore", "conteudo": '''node_modules/
*.log
.env
'''}]},

]

# ── o que fica DE FORA do ensino, para testar composição ──────────────
#
# Estas combinações NÃO estão acima. Se a rede montar uma delas com
# sentido, ela aprendeu a fatoração; se devolver vazio, ela decorou.
# (csharp+api entrou para o ensino; o teste virou "compor 3 combinações".)
COMBINACOES_NOVAS = [
    ("javascript", "api"),
    ("python", "biblioteca"),
    ("javascript", "site"),
]
