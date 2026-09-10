# DevDesk AI — Arquitetura

**Assistente de suporte técnico e desenvolvimento, com rede neural própria, rodando local**

Rede do zero × percepção multimodal × execução com freio

Eduardo Lopes, 2026

---

## O que é

Um assistente que recebe um problema do jeito que ele chega na vida real — um
print, um áudio de alguém reclamando, um vídeo da tela travando, um texto torto —
e ajuda a resolver: do N1 que é procedimento conhecido até o N3 que é achar o
defeito no código.

**Roda inteiro na máquina.** Sem nuvem, sem API de terceiro, sem chave. A rede é
escrita do zero, com NumPy, e o que ela não souber ela aprende aqui dentro.

---

## A espinha: abster-se é resposta

Os dois projetos anteriores chegaram nisto por caminhos diferentes, e é a decisão
que segura este aqui de pé.

No **SO-Espacial**, quando uma câmera não enxerga, o campo chega `None` e ela
**não vota** — nada é inventado para preencher a lacuna. No **AutonomousStore**, o
gerente abaixo do limiar não chuta: mostra os três palpites e pede um clique.

Num assistente de suporte isso deixa de ser elegância e vira segurança. Uma IA
que arrisca um diagnóstico e roda um comando no PowerShell é pior que nenhuma.
Então:

> **Toda camada pode se abster, e abster-se escala o nível.**
>
> N1 não sabe → N2. N2 não conclui → N3. N3 não fecha → humano.
> Em nenhum ponto o sistema inventa para não ficar calado.

Isso dá ao N1/N2/N3 um significado técnico, e não só um rótulo de organograma:

| nível | o que o sistema faz | do que precisa |
|---|---|---|
| **N1** | reconhece o problema e aplica procedimento conhecido | classificador + base de casos |
| **N2** | não reconhece: colhe evidência da máquina e correlaciona | percepção + investigação |
| **N3** | evidência não fecha: entra no código e procura o defeito | leitura de projeto + editor |
| **humano** | o sistema não conclui, e diz exatamente o que já descartou | registro de tudo |

O valor aparece cedo: com o N1 funcionando o assistente já serve, e os outros
níveis crescem em cima.

---

## As sete camadas

```
                            ┌──────────────────────────┐
   texto · print · áudio ──▶│  1. PERCEPÇÃO            │  tudo vira texto+vetor
   · vídeo                  │     CNN do zero · FFT    │
                            └────────────┬─────────────┘
                                         ▼
                            ┌──────────────────────────┐
                            │  2. ENTENDIMENTO         │  qual é o problema?
                            │     classificador        │  ── abstém → N2
                            └────────────┬─────────────┘
                                         ▼
                            ┌──────────────────────────┐
                            │  3. CONHECIMENTO         │  já vimos isso antes?
                            │     base de casos        │  ── abstém → N2
                            └────────────┬─────────────┘
                                         ▼
                            ┌──────────────────────────┐
                            │  4. INVESTIGAÇÃO         │  colher evidência
                            │     PowerShell · arquivos│  (só leitura)
                            │     logs · projeto       │  ── abstém → N3
                            └────────────┬─────────────┘
                                         ▼
                            ┌──────────────────────────┐
                            │  5. AÇÃO                 │  mudar alguma coisa
                            │     risco · confirmação  │
                            │     registro · desfazer  │
                            └────────────┬─────────────┘
                                         ▼
                            ┌──────────────────────────┐
                            │  6. APRENDIZADO          │  cada caso resolvido
                            │     trava · guarda       │  é um exemplo rotulado
                            └────────────┬─────────────┘
                                         ▼
                            ┌──────────────────────────┐
                            │  7. PAINEL               │  a pasta acessível,
                            │     servidor local       │  o histórico, as ações
                            └──────────────────────────┘
```

### 1. Percepção — o que é novo de verdade

O trabalho pesado e a parte que ainda não existe.

| entrada | caminho | estado |
|---|---|---|
| texto | `normalizar` → trigramas → peças | **pronto**, vem do Rede-Neural |
| imagem (print) | CNN → região de texto → caractere → OCR | a construir |
| áudio | janela → FFT → espectrograma de mel → **vira imagem** → CNN | a construir |
| vídeo | quadros → a mesma CNN, mais o que muda entre eles | a construir |

**Áudio e imagem não são dois problemas — são um e meio.** Depois do
espectrograma, som é figura, e cai na mesma convolução. Escrever a CNN uma vez
serve aos dois.

E existe uma linha de base honesta esperando: a rede densa do MNIST já treinada
acerta **95,94%** com 23.860 parâmetros. A CNN tem que bater isso, senão a
convolução não se pagou.

### 2. Entendimento

O classificador que já existe e já é medido, retreinado no domínio novo. Muda o
corpus e as intenções; o motor é o mesmo, com o mesmo limiar e os mesmos botões
quando não tem certeza.

### 3. Conhecimento

Base de casos: **sintoma → diagnóstico → solução → funcionou?**. É a memória do
sistema, e é o que faz o N1 existir.

### 4. Investigação — só leitura

Comandos que **olham** e nada mais: serviços, logs, espaço em disco, versão,
processo travado, conteúdo de arquivo, estrutura do projeto. Como não altera
nada, roda sem perguntar.

### 5. Ação — a única que escreve

Tudo que altera passa por aqui, e por três coisas obrigatórias:

1. **nível de risco** declarado antes
2. **confirmação** explícita de quem está no comando
3. **registro e desfazer** — nenhuma ação entra sem caminho de volta

A máquina é a nossa, não a de um cliente. Isso não afrouxa o freio; muda a
finalidade dele: o freio existe para **auditar e reverter o que nós mesmos
fizemos**, não para nos defender de alguém.

### 6. Aprendizado

Aqui está a diferença em relação ao gerente da loja. Lá o `correcoes.jsonl` ficou
dias com zero bytes porque só uma pessoa clicava. **Num suporte, cada chamado
fechado é um exemplo rotulado** — descrição, classe, solução, funcionou ou não. É
volume de verdade, todo dia.

A trava contra esquecimento catastrófico e o conjunto de guarda já foram
construídos e medidos no projeto anterior. Vêm inteiros.

### 7. Painel

Estilo Devin: a pasta a que o sistema tem acesso, o histórico do que fez, o que
está fazendo agora, e o painel de ações pendentes de confirmação. O
`monitor/servidor.py` do Rede-Neural já serve HTML local e já tem `painel.html` —
é a base.

---

## O que vem pronto, e de onde

Nada aqui é começar do zero de novo. O motor está escrito, provado e medido.

| em DevDesk_AI | vem de | o que é |
|---|---|---|
| `nucleo/camada.py` `rede.py` `ativacao.py` `custo.py` | Rede-Neural `rede/` | o motor: Camada, Rede, Sigmoid, Softmax, EntropiaCruzadaCategorica |
| `nucleo/retropropagacao.py` | Rede-Neural `rede/` | `gradiente`, `gradiente_com_entrada`, **`conferir_numericamente`** |
| `texto/vocabulario.py` | `rede/texto.py` | `normalizar`, `trigramas`, `pedacos`, `Vocabulario` |
| `entendimento/` | `rede/classificador*.py` · `embutimento.py` | o classificador de intenção e a tabela de embutimento |
| `conhecimento/` | `rede/conhecimento.py` · `dados/conhecimento_sistemas.json` | `GerenciadorConhecimento` e as bases por sistema |
| `acao/` | `rede/acao_inteligente.py` | `NivelRisco`, `TipoAcao`, `Acao`, `VerificadorContexto`, `GerenciadorAcoes` |
| `visao/mnist/` | `dados/mnist.pkl.gz` · `modelos/rede_mnist.json` | o conjunto e a rede densa de 95,94% — a linha de base da CNN |
| `visao/captura.py` | SO-Espacial `captura/` · `ferramentas/abrir_camera.py` | leitura de imagem e vídeo com OpenCV |
| `painel/` | `monitor/servidor.py` · `painel.html` | servidor local e a tela |
| `provas/` | `testes/test_rede.py` · `programas/conferir_*` | o método: gradiente conferido contra derivada numérica |
| `caderno/` | `caderno/` | o diário de bordo — um arquivo por dia |

**`acao_inteligente.py` e `conhecimento.py` são a surpresa boa**: 1.110 linhas que
já resolvem a camada 3 e a camada 5, escritas antes de existir um projeto que
precisasse delas.

---

## O que é novo

| peça | por que é trabalho de verdade |
|---|---|
| **convolução do zero** | conv, pooling, e retropropagação **através** da convolução — pesos compartilhados mudam o gradiente |
| **OCR de print** | achar onde tem texto numa tela cheia, antes de reconhecer o caractere |
| **FFT e espectrograma** | do sinal cru ao mel, para o som virar figura |
| **ponte com o shell** | PowerShell e cmd, saída capturada, código de retorno, tempo limite |
| **VS Code** | extensão — é o caminho que a ferramenta oferece |
| **Visual Studio** | mais fechado que o VS Code; caminho a pesquisar antes de escolher |
| **o painel** | a tela estilo Devin sobre o servidor local |

---

## Os degraus

Cada degrau é uma coisa que **funciona sozinha** e pode ser mostrada. A ordem
segue o SO-Espacial: nada de estágio que só faz sentido quando o próximo ficar
pronto.

| # | degrau | prova que ele funcionou |
|---|---|---|
| 0 | o motor mudado de casa + as provas passando | `conferir_numericamente` reprova um gradiente errado de propósito |
| 1 | corpus e classificador do domínio de suporte | acerto medido em validação cruzada **agrupada** |
| 2 | base de casos + N1 ponta a ponta, só texto | um problema conhecido entra e sai resolvido |
| 3 | investigação só leitura | o assistente colhe evidência e mostra o que olhou |
| 4 | CNN do zero no MNIST | bate os 95,94% da rede densa, ou explica por que não |
| 5 | OCR de print de tela | lê a mensagem de erro de um print de verdade |
| 6 | ação com risco, confirmação e desfazer | uma alteração é feita e revertida |
| 7 | áudio: FFT → espectrograma → a mesma CNN | entende um áudio curto de chamado |
| 8 | painel | a pasta, o histórico e as ações na tela |
| 9 | VS Code | lê o projeto aberto e propõe a correção |
| 10 | vídeo, e o Visual Studio | — |

---

## Decisões em aberto

Coisas que mudam o desenho e que não são minhas para decidir:

1. **Repositório novo ou continuação do Rede-Neural?** O motor é o mesmo, mas o
   domínio é outro e o Rede-Neural continua sendo o cérebro da loja.
2. **O motor: copiado ou importado?** Copiado deixa o DevDesk independente e sem
   nuvem; o preço é que uma correção feita aqui não chega lá sozinha.
3. **Um assistente com dois modos (suporte e desenvolvedor), ou dois perfis
   separados?** O `PerfilDeQuemFala` da loja resolveu isso com uma lista de
   permissão — o mesmo padrão serve aqui.
