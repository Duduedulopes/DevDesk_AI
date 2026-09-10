# -*- coding: utf-8 -*-
"""AS TRÊS REDES QUE MONTAM UM PROJETO DO ZERO.

O PEDIDO

    "cria um projeto de calculadora em C#"

vira, pelas redes que já existem, três coisas: a INTENÇÃO (criar), e da
frase a LINGUAGEM, o TIPO e o NOME (o etiquetador). Daí para frente é
este arquivo: transformar (linguagem, tipo, nome) numa árvore de pastas
e arquivos escritos.

POR QUE TRÊS REDES E NÃO UMA

Porque são três perguntas diferentes, e juntar as três numa só obrigaria
a rede a decorar combinações inteiras — que é exatamente o que a gente
não quer.

    1. ESTRUTURA   (linguagem, tipo) → QUAIS papéis o projeto tem
                   "um api tem rota; um projeto C# tem .csproj"

    2. CAMINHO     (linguagem, tipo, papel) → ONDE esse papel mora
                   (csharp, api, principal) → "Program.cs"

    3. CONTEÚDO    (linguagem, tipo, papel) → COMO esse papel se escreve
                   (csharp, console, principal) → o código de um Program.cs

O TIPO ENTRA NO CONTEÚDO, e eu quase deixei ele de fora. O raciocínio
errado era: "como se escreve um principal em C# é a mesma coisa em todo
lugar". Não é. O `principal` de um site é um servidor; o de um console
imprime e sai. Sem o tipo, a rede teria que escolher um dos dois e errar
o outro.

E o tipo como CAMPO SEPARADO é justamente o que deixa compor: para
(csharp, api, rota) ela nunca viu nada, mas viu (php, api, rota) e
(python, api, rota) — o que é uma rota — e viu csharp em console e
biblioteca — como C# se escreve. As três entradas são fatias distintas
do vetor, não uma chave única.

É essa separação que permite COMPOR. C#+api nunca foi ensinado; a rede
1 sabe que api tem rota (viu em python e php) e que C# tem .csproj (viu
em console e biblioteca), e junta as duas metades.

O QUE É GERAÇÃO E O QUE É MEMÓRIA — DITO NA CARA

As redes 2 e 3 escrevem caractere por caractere: são generativas de
verdade, modelo do Bengio condicionado. Mas conteúdo de arquivo é longo,
e com 13 exemplos de ensino a rede 3 não escreve código que compila —
isso está medido, não suposto, e o número sai no
`programas/treinar_compositor.py`.

Então o compositor tem dois caminhos e ele DIZ qual usou:

    gerado     a rede 3 escreveu o arquivo. Medido por bits/caractere e
               pelo compilador.
    memoria    a rede 1 e a 2 decidiram o quê e onde; o conteúdo veio da
               forma que a rede aprendeu para aquele (linguagem, papel).

Chamar o segundo de "geração" seria mentira, e mentira em medição é a
única coisa que este projeto não aceita. Quando o par (linguagem, papel)
nunca foi visto, não há nem memória nem geração confiável — e aí ele
PERGUNTA, que é a resposta certa para uma pergunta que ele não sabe.
"""
import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np

from nucleo.ativacao import Sigmoid, Softmax
from nucleo.custo import EntropiaCruzada, EntropiaCruzadaCategorica
from nucleo.rede import Rede
from nucleo.retropropagacao import gradiente_com_entrada

LN2 = math.log(2.0)
FIM = "\x00"          # marca o fim de uma geração


# ══════════════════════════════════════════════════════════════════════
#  1. A ESTRUTURA — (linguagem, tipo) → quais papéis
# ══════════════════════════════════════════════════════════════════════
class RedeDaEstrutura:
    """Diz QUAIS arquivos o projeto tem. Multi-rótulo, não escolha única.

    SIGMOID POR PAPEL, E NÃO SOFTMAX SOBRE OS PAPÉIS. A diferença não é
    detalhe: softmax obriga as saídas a somarem 1, ou seja, obriga a
    escolher UM papel. Um projeto tem vários ao mesmo tempo. Cada papel
    é uma pergunta de sim/não independente, e a perda é a entropia
    cruzada binária — a mesma que o `custo.py` já tinha.

    AS DUAS ENTRADAS ENTRAM CONCATENADAS, não somadas. Somar apagaria de
    qual das duas veio o quê; a rede precisa saber que "csharp" está no
    lugar da linguagem e "api" no lugar do tipo.
    """

    def __init__(self, linguagens, tipos, papeis, dimensao=8, ocultos=24,
                 semente=7):
        self.linguagens, self.tipos, self.papeis = list(linguagens), list(tipos), list(papeis)
        self.i_ling = {x: i for i, x in enumerate(self.linguagens)}
        self.i_tipo = {x: i for i, x in enumerate(self.tipos)}
        self.i_papel = {x: i for i, x in enumerate(self.papeis)}
        self.dimensao = dimensao
        g = np.random.default_rng(semente)
        self.tab_ling = g.standard_normal((len(self.linguagens), dimensao)) / np.sqrt(dimensao)
        self.tab_tipo = g.standard_normal((len(self.tipos), dimensao)) / np.sqrt(dimensao)
        self.rede = Rede([2 * dimensao, ocultos, len(self.papeis)],
                         semente=semente, ativacao_saida=Sigmoid)

    def entrada(self, ling, tipo):
        return np.concatenate([self.tab_ling[self.i_ling[ling]],
                               self.tab_tipo[self.i_tipo[tipo]]]).reshape(-1, 1)

    def alvo(self, papeis):
        y = np.zeros((len(self.papeis), 1))
        for p in papeis:
            y[self.i_papel[p]] = 1.0
        return y

    def prever(self, ling, tipo):
        return self.rede.frente(self.entrada(ling, tipo)).ravel()

    def papeis_de(self, ling, tipo, limiar=0.5):
        """Os papéis acima do limiar, na ordem em que a rede acredita."""
        p = self.prever(ling, tipo)
        escolhidos = [(self.papeis[i], float(p[i])) for i in range(len(p))
                      if p[i] >= limiar]
        return sorted(escolhidos, key=lambda x: -x[1])

    def passo(self, lote, taxa):
        gp = [np.zeros_like(c.pesos) for c in self.rede.camadas]
        gv = [np.zeros_like(c.vies) for c in self.rede.camadas]
        gl = np.zeros_like(self.tab_ling)
        gt = np.zeros_like(self.tab_tipo)
        perda = 0.0
        for ling, tipo, papeis in lote:
            x, y = self.entrada(ling, tipo), self.alvo(papeis)
            dp, dv, erro = gradiente_com_entrada(self.rede, x, y, EntropiaCruzada)
            for i in range(len(gp)):
                gp[i] += dp[i]
                gv[i] += dv[i]
            # o erro chega emendado: a primeira metade é da linguagem,
            # a segunda é do tipo — na mesma ordem em que foram juntadas
            meio = self.dimensao
            gl[self.i_ling[ling]] += erro[:meio].ravel()
            gt[self.i_tipo[tipo]] += erro[meio:].ravel()
            perda += float(EntropiaCruzada.fn(
                self.rede.camadas[-1].ultima_ativacao, y))
        n = len(lote)
        for i, c in enumerate(self.rede.camadas):
            c.pesos -= (taxa / n) * gp[i]
            c.vies -= (taxa / n) * gv[i]
        self.tab_ling -= (taxa / n) * gl
        self.tab_tipo -= (taxa / n) * gt
        return perda / n

    @property
    def n_parametros(self):
        return self.tab_ling.size + self.tab_tipo.size + self.rede.n_parametros

    def para_dicionario(self):
        return {"linguagens": self.linguagens, "tipos": self.tipos,
                "papeis": self.papeis, "dimensao": self.dimensao,
                "tab_ling": self.tab_ling.tolist(),
                "tab_tipo": self.tab_tipo.tolist(),
                "camadas": [{"pesos": c.pesos.tolist(),
                             "vies": c.vies.ravel().tolist()}
                            for c in self.rede.camadas]}

    @classmethod
    def de_dicionario(cls, d):
        r = cls(d["linguagens"], d["tipos"], d["papeis"], dimensao=d["dimensao"],
                ocultos=len(d["camadas"][0]["pesos"]))
        r.tab_ling = np.array(d["tab_ling"], dtype=float)
        r.tab_tipo = np.array(d["tab_tipo"], dtype=float)
        for c, cru in zip(r.rede.camadas, d["camadas"]):
            c.pesos = np.array(cru["pesos"], dtype=float)
            c.vies = np.array(cru["vies"], dtype=float).reshape(-1, 1)
        return r


# ══════════════════════════════════════════════════════════════════════
#  2 e 3. ESCREVER TEXTO CONDICIONADO — a mesma forma, dois usos
# ══════════════════════════════════════════════════════════════════════
class EscritorCondicionado:
    """Modelo do Bengio com etiquetas penduradas no contexto.

        [emb(c_-4) emb(c_-3) emb(c_-2) emb(c_-1)] ++ [emb(rótulo1) ...]
                                │
                                ▼
                        oculta sigmoide
                                │
                                ▼
                       softmax no alfabeto

    A ÚNICA COISA NOVA em relação ao `modelo/linguagem.py` são os
    embutimentos de rótulo emendados no fim da janela. É o que faz o
    mesmo modelo escrever `Program.cs` quando a etiqueta diz csharp e
    `main.py` quando diz python: o contexto de caracteres é o mesmo, o
    que muda é a condição.

    Os rótulos são aprendidos junto, como a tabela de caracteres — por
    isso o erro tem que voltar até eles também. Se não voltar, o treino
    roda, a perda cai um pouco, e a condição nunca significa nada.
    """

    def __init__(self, alfabeto, campos, contexto=8, dimensao=12, oculta=96,
                 semente=7, ao_contrario=False):
        """`campos` = [(nome, [valores possíveis]), ...] — ex.:
        [("linguagem", ["csharp", ...]), ("papel", ["principal", ...])]

        ao_contrario=True TREINA E ESCREVE DE TRÁS PARA FRENTE, e isso não
        é esquisitice: é o conserto de um defeito medido no caminho de
        arquivo.

        A extensão (`.py`, `.cs`) é a parte do caminho que depende SÓ da
        linguagem, e ela fica no fim. Escrevendo na ordem normal, quando a
        rede chega no fim ela já tem sete caracteres de contexto gritando
        a resposta — e no treino esse contexto sempre bate com a
        linguagem, então a etiqueta nunca precisou ser consultada. Some a
        combinação no teste e a etiqueta, que era a única fonte que
        restava, não sabia falar.

        De trás para frente, a extensão é a PRIMEIRA coisa a escrever, na
        posição onde não existe contexto nenhum — só as etiquetas. A
        linguagem é obrigada a responder.

        Medido, no deixa-um-fora de quatro combinações:

            ordem normal          extensão certa  58%   caminho exato 42%
            de trás para frente   extensão certa  79%   caminho exato 53%

        E o que sobrou errado mudou de qualidade: `Program.cs` virava
        `main.py` (linguagem errada) e passou a virar `Calculo.cs`
        (linguagem certa, nome discutível). O que sobra é indeterminado
        de verdade — nem uma pessoa sabe se o principal de um api python
        se chama `main.py` ou `app.py`.
        """
        self.ao_contrario = bool(ao_contrario)
        self.alfabeto = list(alfabeto)
        self.indice = {c: i for i, c in enumerate(self.alfabeto)}
        self.contexto, self.dimensao = contexto, dimensao
        self.campos = [(nome, list(vals)) for nome, vals in campos]
        self.i_campo = [{v: i for i, v in enumerate(vals)}
                        for _, vals in self.campos]
        g = np.random.default_rng(semente)
        self.tabela = g.standard_normal((len(self.alfabeto), dimensao)) / np.sqrt(dimensao)
        self.tab_campo = [g.standard_normal((len(vals), dimensao)) / np.sqrt(dimensao)
                          for _, vals in self.campos]
        n_entrada = (contexto + len(self.campos)) * dimensao
        self.rede = Rede([n_entrada, oculta, len(self.alfabeto)],
                         semente=semente, ativacao_saida=Softmax)

    # ── conversão ────────────────────────────────────────────────────
    def codificar(self, texto):
        return [self.indice[c] for c in texto if c in self.indice]

    def entrada(self, janela, rotulos):
        pedacos = [self.tabela[list(janela)].reshape(-1)]
        for tab, i_de, valor in zip(self.tab_campo, self.i_campo, rotulos):
            pedacos.append(tab[i_de[valor]])
        return np.concatenate(pedacos).reshape(-1, 1)

    def alvo(self, i):
        y = np.zeros((len(self.alfabeto), 1))
        y[i] = 1.0
        return y

    def exemplos_de(self, texto, rotulos):
        """O texto vira (janela, rótulos, próximo) para cada posição.

        Começa com a janela cheia de FIM, para o modelo aprender também
        COMO SE COMEÇA — senão ele só sabe continuar, e na hora de
        escrever do zero não tem por onde.
        """
        if self.ao_contrario:
            texto = texto[::-1]
        idx = self.codificar(FIM * self.contexto + texto + FIM)
        return [(idx[i - self.contexto:i], rotulos, idx[i])
                for i in range(self.contexto, len(idx))]

    # ── uso ──────────────────────────────────────────────────────────
    def prever(self, janela, rotulos):
        return self.rede.frente(self.entrada(janela, rotulos))

    def bits_do_proximo(self, janela, rotulos, certo):
        a = self.prever(janela, rotulos)
        return -math.log2(max(float(a.ravel()[certo]), 1e-15))

    def bits_por_caractere(self, exemplos, salto=1):
        total, n = 0.0, 0
        for i in range(0, len(exemplos), salto):
            janela, rotulos, certo = exemplos[i]
            total += self.bits_do_proximo(janela, rotulos, certo)
            n += 1
        return total / n if n else float("nan")

    def escrever(self, rotulos, maximo=2000, temperatura=0.0, semente=None):
        """Escreve do zero até o modelo dizer FIM (ou bater o teto).

        temperatura 0 = sempre o mais provável. Para caminho de arquivo é
        o que se quer: não há criatividade a exercer em `Program.cs`.
        """
        r = np.random.default_rng(semente)
        janela = self.codificar(FIM * self.contexto)
        saida = []
        for _ in range(maximo):
            p = np.clip(self.prever(janela, rotulos).ravel().astype(float), 1e-12, None)
            if temperatura <= 0:
                k = int(np.argmax(p))
            else:
                p = np.exp(np.log(p) / temperatura)
                k = int(r.choice(len(p), p=p / p.sum()))
            c = self.alfabeto[k]
            if c == FIM:
                break
            saida.append(c)
            janela = janela[1:] + [k]
        escrito = "".join(saida)
        return escrito[::-1] if self.ao_contrario else escrito

    # ── treino ───────────────────────────────────────────────────────
    def passo(self, lote, taxa, apagar_contexto=0.0, r=None):
        """Um passo. `apagar_contexto` é o conserto de um defeito MEDIDO.

        O DEFEITO: a rede aprendia a extensão pelo CONTEXTO DE CARACTERES
        e ignorava a etiqueta de linguagem. Ela podia: no treino os dois
        estão perfeitamente casados — cada caminho aparece numa linguagem
        só, então "o que costuma vir depois de `rotas.`" já responde tudo
        e a etiqueta nunca precisa ser consultada.

        Aí some a combinação inteira no teste, o contexto de caracteres
        não tem mais a resposta, e só a etiqueta teria — a etiqueta que a
        rede nunca aprendeu a usar. Medido: `rotas.py` virava `rotas.php`;
        e triplicar o treino de 5.000 para 15.000 passos deu exatamente o
        mesmo 43%. Treinar mais não conserta o que a rede não precisa
        aprender.

        O CONSERTO: apagar caracteres da janela, POSIÇÃO A POSIÇÃO. Onde
        apagou, a resposta não está no contexto e só a etiqueta responde.

        E POSIÇÃO A POSIÇÃO, não a janela inteira — este foi o meu
        segundo erro. Apagando a janela toda, todo exemplo apagado vira um
        "começo de texto", e o que se ensina é só etiqueta -> primeira
        letra. Só que a extensão fica no FIM do caminho. Medido: apagando
        tudo, o `principal` melhorou (parou de responder `index.php` para
        python e passou a `servidor.py`, linguagem certa) e a extensao nao
        mexeu — `rotas.py` continuou virando `rotas.php`, porque aquela
        posicao nunca aparecia no treino apagado.

        Apagando por posicao, a janela continua no meio do caminho e
        continua faltando informacao: e ai que a etiqueta entra.
        """
        gp = [np.zeros_like(c.pesos) for c in self.rede.camadas]
        gv = [np.zeros_like(c.vies) for c in self.rede.camadas]
        gt = np.zeros_like(self.tabela)
        gc = [np.zeros_like(t) for t in self.tab_campo]
        perda = 0.0
        corte = self.contexto * self.dimensao
        for janela, rotulos, certo in lote:
            x, y = self.entrada(janela, rotulos), self.alvo(certo)
            vivas = None
            if apagar_contexto > 0 and r is not None:
                apagadas = r.random(self.contexto) < apagar_contexto
                if apagadas.any():
                    x = x.copy()
                    for pos in np.flatnonzero(apagadas):
                        x[pos * self.dimensao:(pos + 1) * self.dimensao] = 0.0
                    vivas = ~apagadas
            dp, dv, erro = gradiente_com_entrada(self.rede, x, y,
                                                 EntropiaCruzadaCategorica)
            for i in range(len(gp)):
                gp[i] += dp[i]
                gv[i] += dv[i]
            # Posicao apagada = aquele caractere nao participou desta
            # previsao, entao ele nao recebe erro dela. Somar ali
            # ensinaria a letra a partir de uma entrada que ela nao deu.
            por_posicao = erro[:corte].reshape(self.contexto, self.dimensao)
            if vivas is None:
                # ACUMULA: o mesmo caractere pode aparecer duas vezes na
                # janela, e as duas contribuicoes sao da MESMA linha.
                np.add.at(gt, list(janela), por_posicao)
            elif vivas.any():
                indices = [j for j, viva in zip(janela, vivas) if viva]
                np.add.at(gt, indices, por_posicao[vivas])
            for j, (tab_g, i_de, valor) in enumerate(zip(gc, self.i_campo, rotulos)):
                fatia = erro[corte + j * self.dimensao:
                             corte + (j + 1) * self.dimensao].ravel()
                tab_g[i_de[valor]] += fatia
            perda += float(EntropiaCruzadaCategorica.fn(
                self.rede.camadas[-1].ultima_ativacao, y))
        n = len(lote)
        for i, c in enumerate(self.rede.camadas):
            c.pesos -= (taxa / n) * gp[i]
            c.vies -= (taxa / n) * gv[i]
        self.tabela -= (taxa / n) * gt
        for tab, g in zip(self.tab_campo, gc):
            tab -= (taxa / n) * g
        return perda / n / LN2

    @property
    def n_parametros(self):
        return (self.tabela.size + sum(t.size for t in self.tab_campo)
                + self.rede.n_parametros)

    def para_dicionario(self):
        return {"alfabeto": self.alfabeto, "contexto": self.contexto,
                "dimensao": self.dimensao, "ao_contrario": self.ao_contrario,
                "campos": [[n, v] for n, v in self.campos],
                "tabela": self.tabela.tolist(),
                "tab_campo": [t.tolist() for t in self.tab_campo],
                "camadas": [{"pesos": c.pesos.tolist(),
                             "vies": c.vies.ravel().tolist()}
                            for c in self.rede.camadas]}

    @classmethod
    def de_dicionario(cls, d):
        e = cls(d["alfabeto"], [(n, v) for n, v in d["campos"]],
                contexto=d["contexto"], dimensao=d["dimensao"],
                oculta=len(d["camadas"][0]["pesos"]),
                ao_contrario=d.get("ao_contrario", False))
        e.tabela = np.array(d["tabela"], dtype=float)
        e.tab_campo = [np.array(t, dtype=float) for t in d["tab_campo"]]
        for c, cru in zip(e.rede.camadas, d["camadas"]):
            c.pesos = np.array(cru["pesos"], dtype=float)
            c.vies = np.array(cru["vies"], dtype=float).reshape(-1, 1)
        return e


# ══════════════════════════════════════════════════════════════════════
#  O NOME QUE A PESSOA PEDIU
# ══════════════════════════════════════════════════════════════════════
def limpar_nome(bruto):
    """"uma calculadora!" → "calculadora". Nome de pasta, não frase.

    Isto NÃO é a rede pensando: é higiene de sistema de arquivos. Uma
    barra no nome vira uma pasta que ninguém pediu, e um acento vira
    dor de cabeça em três sistemas operacionais diferentes.
    """
    t = unicodedata.normalize("NFKD", str(bruto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Za-z0-9_\- ]+", "", t).strip()
    t = re.sub(r"\s+", "_", t)
    return t[:60] or "projeto"


def trocar(texto, nome):
    return texto.replace("{nome}", nome).replace("{Nome}", nome[:1].upper() + nome[1:])


# ══════════════════════════════════════════════════════════════════════
#  O COMPOSITOR — junta as três e escreve no disco
# ══════════════════════════════════════════════════════════════════════
class Compositor:
    """De (linguagem, tipo, nome) para uma árvore de pastas e arquivos.

    Nada aqui escreve no disco sem `escrever=True`. O padrão é planejar e
    devolver o plano, para o programa poder mostrar a árvore e perguntar
    "é isso mesmo?" antes de criar coisa nenhuma na máquina de ninguém.
    """

    def __init__(self, caminho_modelo, ensino=None):
        with open(caminho_modelo, encoding="utf-8") as f:
            d = json.load(f)
        self.estrutura = RedeDaEstrutura.de_dicionario(d["estrutura"])
        self.caminho = EscritorCondicionado.de_dicionario(d["caminho"])
        self.conteudo = EscritorCondicionado.de_dicionario(d["conteudo"])
        self.medido = d.get("medido", {})
        self.limiar = float(d.get("limiar", 0.5))
        # A MEMÓRIA: a forma que a rede aprendeu para cada (linguagem,
        # papel). Não é dicionário de projetos prontos — é a lembrança
        # de como aquele papel foi escrito, e o compositor DIZ quando
        # usou ela em vez da geração.
        self.memoria = d.get("memoria", {})
        # AS EXTENSÕES QUE CADA LINGUAGEM USA, colhidas do ensino. Não é
        # dicionário escrito à mão: é o que os exemplos mostraram, e serve
        # de CONFERÊNCIA sobre a rede do caminho.
        #
        # Fez falta na primeira prova: para csharp+api a rede do caminho
        # escreveu `script.js` — nome de arquivo JavaScript num projeto
        # C# — e a memória enfiou código C# lá dentro. O arquivo saiu
        # incoerente consigo mesmo e só o compilador percebeu.
        self.extensoes = {l: set(v) for l, v in d.get("extensoes", {}).items()}
        self.extensoes_do_tipo = {t: set(v)
                                  for t, v in d.get("extensoes_do_tipo", {}).items()}
        # onde cada forma da memória morava — usado para saber se dá para
        # emprestar de outra linguagem (só empresta se a extensão bate)
        self.caminhos_vistos = d.get("caminhos", {})

    def conhece(self, ling, tipo, papel):
        return f"{ling}|{tipo}|{papel}" in self.memoria

    def extensao_bate(self, ling, tipo, caminho):
        """O arquivo que a rede do caminho escreveu faz sentido aqui?

        VALE SE A LINGUAGEM USA **OU** SE O TIPO USA — e o "ou" é o
        conserto de uma versão minha estreita demais.

        Na primeira tentativa eu conferia só contra a linguagem, e o
        guarda barrou `estilo.css` num site JavaScript: os exemplos de
        javascript que eu escrevi são console e biblioteca, então
        javascript "nunca usou" `.css`. Só que todo SITE usa — html, php,
        python e csharp todos têm `.css` no site deles. A extensão vinha
        do tipo, e eu estava perguntando só para a linguagem.

        É a mesma fatoração de sempre, aplicada à conferência: parte da
        resposta mora na linguagem, parte mora no tipo. Perguntar só a uma
        das duas reprova o certo.

        O que continua reprovado é o que nenhuma das duas conhece:
        `script.js` num api C# — csharp não usa `.js`, e nenhum api de
        nenhuma linguagem usa `.js`. Aí é a rede do caminho errando mesmo.
        """
        da_ling = self.extensoes.get(ling) or set()
        do_tipo = self.extensoes_do_tipo.get(tipo) or set()
        if not da_ling and not do_tipo:
            return True          # sem dado para conferir, não acusa
        return Path(caminho).suffix.lower() in (da_ling | do_tipo)

    def tipo_de_referencia(self, ling, tipo, papeis):
        """Quando falta o tipo exato, de qual tipo ENSINADO copiar tudo.

        ISTO NASCEU DE UM PROJETO QUE NÃO RODAVA. Para javascript+api ele
        pegou o `principal` do exemplo de console (que exporta só `somar`)
        e o `teste` do exemplo de biblioteca (que testa `somar` e
        `vazio`). Cada arquivo, sozinho, estava certo. Juntos não: o teste
        chamava uma função que o principal não exportava, e `node --test`
        deu 2 de 4.

        Arquivo por arquivo eu estava escolhendo bem; o PROJETO é que
        saía incoerente, porque ninguém estava olhando para o conjunto.

        Então a escolha passa a ser uma só para o projeto inteiro: entre
        os tipos que essa linguagem tem ensinados, o que mais se PARECE
        com o pedido.

        E "parece" é cobrir os papéis pedidos E NÃO TRAZER SOBRA — este
        foi o meu segundo tropeço aqui. Contando só a cobertura, para
        python+biblioteca deu empate entre console e api (os dois cobrem
        principal, teste, leiame e ignorar), e o desempate alfabético
        escolheu api. Aí o `teste` veio do api e começava com
        `from rotas import ROTAS` — só que `rota` não estava no plano da
        biblioteca. Projeto criado, `pytest` quebrando na coleta.

        A sobra importa tanto quanto a cobertura: o exemplo de console
        cobre os mesmos quatro papéis e não traz nenhum a mais. Então o
        critério é cobertura primeiro, menor sobra depois, e o nome só
        no fim — para dar o mesmo resultado em toda máquina.
        """
        cobertura = {}
        for chave in self.memoria:
            l, t, pa = chave.split("|")
            if l == ling and t != tipo:
                cobertura.setdefault(t, set()).add(pa)
        if not cobertura:
            return None
        alvo = set(papeis)
        return min(sorted(cobertura),
                   key=lambda t: (-len(cobertura[t] & alvo),
                                  len(cobertura[t] - alvo)))

    def lembrar(self, ling, tipo, papel, caminho=None, referencia=None):
        """O conteúdo que a rede aprendeu, com a origem DECLARADA.

        QUATRO NÍVEIS, e o nome de cada um é o que impede o programa de
        prometer mais do que tem:

            memoria                    viu exatamente este (ling, tipo, papel)
            memoria_de_outro_tipo      viu este papel nesta linguagem, mas
                                       noutro tipo. Ponto de partida, PRECISA
                                       de conferência — um `principal` de
                                       console posto num site está errado.
            memoria_de_outra_linguagem viu este papel noutra linguagem, e a
                                       extensão do arquivo é a MESMA.
            nao_sei                    nunca viu. Não inventa em silêncio:
                                       devolve vazio e o programa pergunta.

        O TERCEIRO NÍVEL SAIU DE UM ERRO DA PRIMEIRA PROVA. Para
        javascript+site ele deixou `estilo.css` e `publico/index.html`
        VAZIOS, dizendo "nunca vi estilo em javascript". Só que um
        `.css` não é javascript coisa nenhuma — é css, e é igual em todo
        projeto. O que estava errado era eu amarrar o conteúdo do arquivo
        à linguagem do PROJETO.

        A regra que conserta sem virar chute: só empresta de outra
        linguagem quando a EXTENSÃO é a mesma. `.css` de um projeto
        python serve num projeto javascript; um `.gitignore` não serve,
        porque ali dentro está escrito `__pycache__`. A extensão é o que
        separa os dois casos, e ela está no dado.
        """
        exato = self.memoria.get(f"{ling}|{tipo}|{papel}")
        if exato is not None:
            return exato, "memoria"
        # O tipo de referência primeiro: os arquivos têm que combinar
        # ENTRE SI, e para isso precisam vir todos do mesmo lugar.
        if referencia:
            de_ref = self.memoria.get(f"{ling}|{referencia}|{papel}")
            if de_ref is not None:
                return de_ref, f"memoria_de_{referencia}"
        for chave, corpo in self.memoria.items():
            l, _, p = chave.split("|")
            if l == ling and p == papel:
                return corpo, "memoria_de_outro_tipo"
        if caminho:
            alvo = Path(caminho).suffix.lower()
            if alvo:
                for chave, corpo in self.memoria.items():
                    l, t, p = chave.split("|")
                    if p != papel:
                        continue
                    outro = self.caminhos_vistos.get(chave, "")
                    if Path(outro).suffix.lower() == alvo:
                        return corpo, "memoria_de_outra_linguagem"
        return "", "nao_sei"

    def planejar(self, linguagem, tipo, nome, gerar_conteudo=False):
        """Devolve o plano: a lista de (caminho, papel, conteúdo, origem).

        `origem` é 'gerado' ou 'memoria' ou 'nao_sei' — e é essa palavra
        que impede o programa de dizer que escreveu o que só lembrou.
        """
        nome = limpar_nome(nome)
        if linguagem not in self.estrutura.i_ling:
            return {"erro": "linguagem_desconhecida", "linguagem": linguagem,
                    "conhecidas": self.estrutura.linguagens}
        if tipo not in self.estrutura.i_tipo:
            return {"erro": "tipo_desconhecido", "tipo": tipo,
                    "conhecidos": self.estrutura.tipos}

        papeis = self.estrutura.papeis_de(linguagem, tipo, self.limiar)
        referencia = self.tipo_de_referencia(linguagem, tipo,
                                             [p for p, _ in papeis])
        arquivos, perguntas, usados = [], [], {}
        for papel, confianca in papeis:
            caminho = self.caminho.escrever([linguagem, tipo, papel], maximo=120)
            if not caminho.strip():
                perguntas.append(f"não sei onde fica o {papel} num {tipo} {linguagem}")
                continue
            # DOIS PAPÉIS NÃO CABEM NO MESMO ARQUIVO. Na primeira prova a
            # rede do caminho devolveu `testes/test_index.js` tanto para
            # `teste` quanto para `rota`, e o plano saiu com o mesmo
            # arquivo duas vezes — o segundo apagaria o primeiro.
            if caminho in usados:
                perguntas.append(
                    f"eu quis pôr o {papel} e o {usados[caminho]} no mesmo "
                    f"arquivo ({caminho}) — onde deve ficar o {papel}?")
                continue
            usados[caminho] = papel
            # A EXTENSÃO TEM QUE COMBINAR COM A LINGUAGEM. `script.js` num
            # projeto C# é a rede do caminho errando, e criar o arquivo
            # assim só empurra o erro para o compilador.
            if not self.extensao_bate(linguagem, tipo, caminho):
                perguntas.append(
                    f"escrevi `{caminho}` para o {papel}, mas isso não parece "
                    f"arquivo de {linguagem} — qual é o nome certo?")
                arquivos.append({"caminho": trocar(caminho, nome), "papel": papel,
                                 "confianca": round(confianca, 3), "conteudo": "",
                                 "origem": "extensao_estranha"})
                continue
            if gerar_conteudo:
                corpo = self.conteudo.escrever([linguagem, tipo, papel],
                                               maximo=4000)
                origem = "gerado"
            else:
                corpo, origem = self.lembrar(linguagem, tipo, papel,
                                             caminho=caminho,
                                             referencia=referencia)
                if origem == "nao_sei":
                    perguntas.append(
                        f"nunca vi um {papel} escrito em {linguagem} — "
                        f"me mostra um exemplo, ou eu tento inventar?")
                elif origem == "memoria_de_outra_linguagem":
                    perguntas.append(
                        f"o {papel} eu nunca vi em {linguagem}, mas o arquivo "
                        f"é {Path(caminho).suffix} e isso eu já vi — confere")
                elif origem.startswith("memoria_de_"):
                    perguntas.append(
                        f"o {papel} eu peguei do seu exemplo de "
                        f"{origem[len('memoria_de_'):]} em {linguagem} — "
                        f"confere se serve para um {tipo}")
            arquivos.append({"caminho": trocar(caminho, nome),
                             "papel": papel,
                             "confianca": round(confianca, 3),
                             "conteudo": trocar(corpo, nome),
                             "origem": origem})
        return {"nome": nome, "linguagem": linguagem, "tipo": tipo,
                "arquivos": arquivos, "perguntas": perguntas,
                "pastas": sorted({str(Path(a["caminho"]).parent)
                                  for a in arquivos} - {"."})}

    def escrever_no_disco(self, plano, raiz):
        """Cria as pastas e os arquivos. Não sobrescreve nada que já existe.

        TUDO CAI DENTRO DE raiz/<nome do projeto>/ — e isto foi um erro
        meu que só apareceu escrevendo de verdade. Os caminhos do plano
        são relativos ao projeto (`main.py`, não `loja/main.py`), porque
        é assim que a rede aprendeu e é assim que se mostra numa árvore.
        Na hora de escrever eu esquecia de pôr a pasta de volta: os
        quatro projetos da prova caíram todos na MESMA pasta, um por
        cima do outro, e a função ainda devolvia `raiz/loja` como se
        tivesse criado a pasta. Relatório certo, disco errado — o pior
        tipo de bug.
        """
        raiz = Path(raiz) / plano["nome"]
        feitos, pulados = [], []
        for a in plano["arquivos"]:
            if a["origem"] == "nao_sei":
                pulados.append((a["caminho"], "não sei escrever este"))
                continue
            if a["origem"] == "extensao_estranha":
                pulados.append((a["caminho"], "o nome não combina com a linguagem"))
                continue
            destino = raiz / a["caminho"]
            if destino.exists():
                pulados.append((a["caminho"], "já existe, não sobrescrevi"))
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(a["conteudo"], encoding="utf-8")
            feitos.append(str(destino))
        return {"criados": feitos, "pulados": pulados, "raiz": str(raiz)}
