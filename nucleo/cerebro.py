"""O cérebro: a rede treinada respondendo em tempo de uso.

Carrega o `intencao.json` — os mesmos pesos que rodam na loja — e responde
o que uma frase quer dizer, com a confiança e os candidatos.

A TOKENIZAÇÃO PRECISA SER IDÊNTICA À DO TREINO

Palavra + trigramas de caractere, com `<` e `>` marcando início e fim, texto
minúsculo e sem acento. Se aqui a conta for um pouco diferente da que treinou
o modelo, os índices apontam para linhas erradas da tabela e a resposta vira
ruído — sem erro nenhum, só um classificador que erra sempre. Por isso este
arquivo importa `pedacos` de `texto/vocabulario.py` em vez de reescrever.
"""
import json
import time
from pathlib import Path

import numpy as np

from texto.vocabulario import pedacos


class Cerebro:
    def __init__(self, caminho="modelos/intencao.json"):
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        self.intencoes = d["intencoes"]
        self.indice_peca = {p: i for i, p in enumerate(d["pecas"])}
        self.tabela = np.array(d["tabela"], dtype=float)
        self.limiar = float(d.get("limiar", 0.95))
        self.medido = d.get("medido", {})

        # O `indices()` aqui embaixo usa `pedacos()` — palavra + trigramas
        # de caractere, fixo no código. Um modelo treinado com outro
        # tokenizador (peças BPE, por exemplo) carregaria SEM ERRO NENHUM
        # e apontaria para linhas erradas da tabela: um classificador que
        # erra sempre, sem levantar exceção. É o pior tipo de defeito.
        #
        # Modelos antigos não têm o campo; "trigramas" é o que eles são.
        self.tokenizador = d.get("tokenizador", "trigramas")
        if self.tokenizador != "trigramas":
            raise ValueError(
                f"{caminho} foi treinado com tokenizador {self.tokenizador!r}, "
                f"e o Cerebro só sabe ler 'trigramas'. Retreine sem --pecas, "
                f"ou ensine a tokenização nova a esta classe — mas não carregue "
                f"assim, porque ele responderia ruído em silêncio.")
        c = d["camadas"]
        self.w0 = np.array(c[0]["pesos"]); self.b0 = np.array(c[0]["vies"]).reshape(-1, 1)
        self.w1 = np.array(c[1]["pesos"]); self.b1 = np.array(c[1]["vies"]).reshape(-1, 1)

    def indices(self, frase):
        vistos = [self.indice_peca[p] for p in pedacos(frase) if p in self.indice_peca]
        return vistos

    def pensar(self, frase, quantos=3):
        """Devolve o que a rede realmente calculou — não só o vencedor."""
        idx = self.indices(frase)
        if not idx:
            return {"conhecidas": 0, "total": len(pedacos(frase)),
                    "candidatos": [], "confiavel": False}

        media = self.tabela[idx].mean(axis=0).reshape(-1, 1)
        oculta = 1.0 / (1.0 + np.exp(-(self.w0 @ media + self.b0)))
        z = self.w1 @ oculta + self.b1
        e = np.exp(z - z.max())
        p = (e / e.sum()).ravel()

        ordem = np.argsort(-p)[:quantos]
        candidatos = [{"nome": self.intencoes[i], "probabilidade": float(p[i])}
                      for i in ordem]
        return {"conhecidas": len(idx), "total": len(pedacos(frase)),
                "candidatos": candidatos,
                "confiavel": candidatos[0]["probabilidade"] >= self.limiar,
                "limiar": self.limiar}


    # ══════════════════════════════════════════════════════════════════
    #  APRENDER COM A CORREÇÃO — e não estragar o resto no caminho
    # ══════════════════════════════════════════════════════════════════
    #
    # MEDIDO NA LOJA, NÃO SUPOSTO: ensinar uma frase com cinco passos
    # fortes corrigiu aquela frase e QUEBROU OUTRAS QUATORZE. Esquecimento
    # catastrófico numa rede de 84 mil parâmetros não é sutil.
    #
    # A trava não proíbe aprender — ela mede. Tenta com taxa forte, mede o
    # estrago num conjunto de guarda de 764 frases que o Python gerou, e só
    # aceita o passo se as TRÊS coisas forem verdade:
    #
    #   1. a frase ensinada passou a ser respondida certo
    #   2. o acerto na guarda não caiu
    #   3. continua acima do acerto do modelo ORIGINAL
    #
    # O terceiro critério foi aprendido apanhando. Comparar só com o estado
    # atual deixou passar cinco correções que, uma a uma, "não pioravam" — e
    # juntas quebraram onze frases. Medir a inclinação e ignorar a altura
    # deixa um modelo descer um degrau de cada vez, para sempre.

    TAXAS = (0.5, 0.25, 0.1, 0.05, 0.02)
    PASSOS = 5

    def carregar_guarda(self, caminho="modelos/guarda.json"):
        """As frases que a trava usa para medir estrago."""
        try:
            with open(caminho, encoding="utf-8") as f:
                cru = json.load(f)
        except OSError:
            self.guarda = []
            self.acerto_da_base = 0.0
            return 0
        por_nome = {n: i for i, n in enumerate(self.intencoes)}
        self.guarda = [(self.indices(x["pergunta"]), por_nome[x["intencao"]])
                       for x in cru if x.get("intencao") in por_nome]
        self.guarda = [(i, c) for i, c in self.guarda if i]
        self.acerto_da_base = self.acerto_na_guarda()
        return len(self.guarda)

    def _frente(self, idx, tabela=None, w0=None, b0=None, w1=None, b1=None):
        tabela = self.tabela if tabela is None else tabela
        w0 = self.w0 if w0 is None else w0; b0 = self.b0 if b0 is None else b0
        w1 = self.w1 if w1 is None else w1; b1 = self.b1 if b1 is None else b1
        media = tabela[idx].mean(axis=0).reshape(-1, 1)
        oculta = 1.0 / (1.0 + np.exp(-(w0 @ media + b0)))
        z = w1 @ oculta + b1
        e = np.exp(z - z.max())
        return media, oculta, (e / e.sum())

    def acerto_na_guarda(self, pesos=None):
        if not getattr(self, "guarda", None):
            return 0.0
        certos = 0
        for idx, certa in self.guarda:
            _, _, p = self._frente(idx, *(pesos or (None,) * 5))
            certos += int(int(np.argmax(p)) == certa)
        return certos / len(self.guarda)

    def _passo(self, pesos, idx, certa, taxa):
        """Um passo de descida do gradiente. Mesma matemática do treino."""
        tabela, w0, b0, w1, b1 = pesos
        media, oculta, a = self._frente(idx, tabela, w0, b0, w1, b1)

        y = np.zeros_like(a); y[certa] = 1.0
        erro1 = a - y                                   # softmax + entropia cruzada
        erro0 = (w1.T @ erro1) * oculta * (1 - oculta)  # derivada da sigmoide

        w1 -= taxa * (erro1 @ oculta.T);  b1 -= taxa * erro1
        w0 -= taxa * (erro0 @ media.T);   b0 -= taxa * erro0

        # A tabela é PARÂMETRO. O erro chega nela sem derivada de ativação —
        # a entrada não passou por sigmoide nenhuma, ela É o vetor da tabela.
        # E divide por len(idx) porque a entrada foi a MÉDIA das peças.
        erro_entrada = (w0.T @ erro0).ravel() / len(idx)
        np.add.at(tabela, idx, -taxa * erro_entrada)

    def ensinar(self, frase, intencao):
        """Aprende a correção — se der para aprender sem estragar."""
        idx = self.indices(frase)
        if not idx:
            return {"resultado": "recusado", "porque": "nenhuma peça conhecida"}
        if intencao not in self.intencoes:
            return {"resultado": "recusado", "porque": "intenção desconhecida"}
        certa = self.intencoes.index(intencao)

        if not getattr(self, "guarda", None):
            self.carregar_guarda()

        antes = self.acerto_na_guarda()
        _, _, p0 = self._frente(idx)
        if int(np.argmax(p0)) == certa:
            # `.ravel()` NÃO é enfeite. p0 tem forma (52, 1), então
            # p0[certa] é um vetor de um elemento, e o NumPy 2 recusa
            # converter isso em número:
            #     TypeError: only 0-dimensional arrays can be converted
            # Rodava no NumPy antigo e passou a estourar — e como este é
            # o caminho de "você clicou na intenção que eu já dava", ele
            # quebrava justamente quando a pessoa concordava com a rede.
            return {"resultado": "ja_sabia", "confianca": float(p0.ravel()[certa]),
                    "acerto_guarda": antes}

        for taxa in self.TAXAS:
            tentativa = (self.tabela.copy(), self.w0.copy(), self.b0.copy(),
                         self.w1.copy(), self.b1.copy())
            for _ in range(self.PASSOS):
                self._passo(tentativa, idx, certa, taxa)

            _, _, p = self._frente(idx, *tentativa)
            aprendeu = int(np.argmax(p)) == certa
            depois = self.acerto_na_guarda(tentativa)

            if aprendeu and depois >= antes and depois >= self.acerto_da_base:
                self.tabela, self.w0, self.b0, self.w1, self.b1 = tentativa
                self.aceitas = getattr(self, "aceitas", 0) + 1
                return {"resultado": "aceito", "taxa": taxa,
                        "confianca_antes": float(p0.ravel()[certa]),
                        "confianca": float(p.ravel()[certa]),
                        "acerto_guarda": depois, "guarda_antes": antes}

        self.recusadas = getattr(self, "recusadas", 0) + 1
        return {"resultado": "recusado", "acerto_guarda": antes,
                "porque": "nenhuma taxa ensinou sem estragar a guarda"}

    def guardar_correcao(self, frase, escolhida, palpite, veredito,
                         arquivo="dados/correcoes.jsonl"):
        """O dado mais caro do projeto: uma frase real com o rótulo certo.

        Guarda SEMPRE, mesmo quando a trava recusou o passo — a correção
        continua sendo um exemplo verdadeiro, e serve para o retreino
        completo mesmo que não sirva para o ajuste ao vivo.
        """
        Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps({"pergunta": frase, "intencao": escolhida,
                                "palpite": palpite, "veredito": veredito,
                                "em": time.strftime("%Y-%m-%dT%H:%M:%S")},
                               ensure_ascii=False) + "\n")
