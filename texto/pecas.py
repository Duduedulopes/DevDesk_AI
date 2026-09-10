"""BPE: o segmentador que aprende as peças do próprio corpus.

A IDEIA, QUE É SIMPLES E FOI O QUE DESTRAVOU OS MODELOS DE VERDADE

Começa com o alfabeto: cada caractere é uma peça. Depois, repetidamente:
conta qual PAR de peças vizinhas aparece mais vezes no corpus, e funde esse
par numa peça nova. Faça isso 500 vezes e o vocabulário vira uma mistura de
letras, sílabas, sufixos e palavras inteiras — todos descobertos do texto,
sem ninguém dizer o que é palavra.

Em português, as primeiras fusões costumam ser "de", "qu", "ção", "ent". Em
código, "def ", "self.", "return", "();". O segmentador aprende os dois
porque o nosso corpus tem os dois.

POR QUE ISSO IMPORTA PARA O MODELO

Com caracteres, prever "compressão" são 10 decisões. Com peças, pode ser 2
("compres" + "são"). Menos decisões por texto, e cada uma carregando mais
significado — e a janela de contexto passa a alcançar muito mais texto pelo
mesmo número de posições.

A ARMADILHA DE MEDIÇÃO, E ELA É SÉRIA

A entropia cruzada de um modelo de peças sai em BITS POR PEÇA. Uma peça vale
vários caracteres. Comparar "6 bits/peça" com os "2,9 bits/car" do gzip
pareceria uma vitória esmagadora e seria fraude — são unidades diferentes.

    A conta honesta é sempre:  total de bits ÷ total de CARACTERES

É por isso que `Pecas` guarda quantos caracteres cada peça tem, e por que
todo relatório deste projeto divide por caractere. Trocar o denominador é a
forma mais fácil de mentir num projeto de compressão.

POR QUE APRENDER SOBRE PALAVRAS, E NÃO SOBRE O TEXTO CORRIDO

Contar pares no corpus inteiro a cada fusão custaria caro demais em Python.
O truque do artigo original: quebrar em "palavras" (por espaço), contar
quantas vezes cada palavra única aparece, e fazer as fusões sobre esse
inventário — que é muito menor — com peso pela frequência. O resultado é o
mesmo, com uma ressalva declarada: fusões que atravessam o espaço nunca
acontecem. Perde-se "de " como peça única; ganha-se poder rodar.
"""
import json
import re
from collections import Counter


class Pecas:
    """Vocabulário de peças aprendido do corpus por fusão de pares."""

    # Mantém o espaço colado no INÍCIO da palavra seguinte. Sem isso,
    # "casa" no meio da frase e "casa" começando linha viram a mesma peça —
    # e o modelo perde a informação de onde a palavra começa.
    QUEBRA = re.compile(r"\s+|\S+")

    def __init__(self, fusoes=None, alfabeto=None):
        self.fusoes = fusoes or []                 # lista de (a, b) em ordem
        self.alfabeto = alfabeto or []
        self._reconstruir()

    def _reconstruir(self):
        self.vocab = list(self.alfabeto)
        for a, b in self.fusoes:
            self.vocab.append(a + b)
        self.indice = {p: i for i, p in enumerate(self.vocab)}
        self.ordem = {(a, b): i for i, (a, b) in enumerate(self.fusoes)}
        # Quantos caracteres cada peça vale. É isto que permite converter
        # bits/peça em bits/caractere sem chutar.
        self.tamanho = [len(p) for p in self.vocab]

    # ── aprendizado ──────────────────────────────────────────────────
    @classmethod
    def treinar(cls, texto, n_fusoes=400, aviso=None):
        alfabeto = sorted(set(texto))
        palavras = Counter(cls.QUEBRA.findall(texto))
        # cada palavra vira tupla de peças; começa como tupla de caracteres
        corpo = {tuple(p): n for p, n in palavras.items()}

        fusoes = []
        for passo in range(n_fusoes):
            pares = Counter()
            for pecas, n in corpo.items():
                for i in range(len(pecas) - 1):
                    pares[(pecas[i], pecas[i + 1])] += n
            if not pares:
                break
            par, quantas = pares.most_common(1)[0]
            if quantas < 2:
                break                      # nada mais se repete: parar
            fusoes.append(par)

            novo = par[0] + par[1]
            corpo = {cls._fundir(pecas, par, novo): n for pecas, n in corpo.items()}

            if aviso and (passo + 1) % 50 == 0:
                aviso(passo + 1, novo, quantas)

        return cls(fusoes, alfabeto)

    @staticmethod
    def _fundir(pecas, par, novo):
        if len(pecas) < 2:
            return pecas
        saida, i = [], 0
        while i < len(pecas):
            if i < len(pecas) - 1 and (pecas[i], pecas[i + 1]) == par:
                saida.append(novo)
                i += 2
            else:
                saida.append(pecas[i])
                i += 1
        return tuple(saida)

    # ── uso ──────────────────────────────────────────────────────────
    def segmentar_palavra(self, palavra):
        """Aplica as fusões na ORDEM em que foram aprendidas.

        A ordem é o que torna a segmentação determinística: a fusão nº 3
        sempre acontece antes da nº 40, independentemente de qual par
        apareça mais nesta palavra específica.
        """
        pecas = tuple(palavra)
        while len(pecas) > 1:
            candidatos = [(self.ordem[p], p) for p in
                          zip(pecas, pecas[1:]) if p in self.ordem]
            if not candidatos:
                break
            _, par = min(candidatos)
            pecas = self._fundir(pecas, par, par[0] + par[1])
        return pecas

    def codificar(self, texto):
        """Texto → lista de índices de peça. Caractere desconhecido é pulado."""
        cache, saida = {}, []
        for palavra in self.QUEBRA.findall(texto):
            if palavra not in cache:
                cache[palavra] = [self.indice[p] for p in self.segmentar_palavra(palavra)
                                  if p in self.indice]
            saida.extend(cache[palavra])
        return saida

    def decodificar(self, indices):
        return "".join(self.vocab[i] for i in indices)

    def caracteres_de(self, indices):
        """Quantos caracteres esta sequência de peças representa.

        O denominador da medição honesta.
        """
        return sum(self.tamanho[i] for i in indices)

    # ── disco ────────────────────────────────────────────────────────
    def guardar(self, caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"alfabeto": self.alfabeto, "fusoes": self.fusoes}, f)

    @classmethod
    def carregar(cls, caminho):
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        return cls([tuple(x) for x in d["fusoes"]], d["alfabeto"])

    def __len__(self):
        return len(self.vocab)

    def __repr__(self):
        return f"Pecas({len(self.vocab)} peças = {len(self.alfabeto)} caracteres + {len(self.fusoes)} fusões)"
