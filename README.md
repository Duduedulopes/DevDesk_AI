# DevDesk AI 🤖

> **Assistente de suporte técnico e desenvolvimento com rede neural própria, rodando local**

![DevDesk AI](https://img.shields.io/badge/DevDesk-AI-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)

## 🌟 Sobre

DevDesk AI é um assistente inteligente que recebe problemas do jeito que eles chegam na vida real — um print, um áudio de alguém reclamando, um vídeo da tela travando, um texto torto — e ajuda a resolver: do N1 (procedimento conhecido) até o N3 (achar o defeito no código) e o Desenvolvimento de um projeto do zero.

**Roda inteiro na máquina.** Sem nuvem, sem API de terceiro, sem chave — depois da primeira instalação, nada sai daqui.

O **motor** é escrito do zero, em NumPy: camada, ativação, custo e retropropagação são código próprio e auditáveis, com o gradiente conferido contra a derivada numérica. Para os **olhos e os ouvidos** (CLIP e Whisper) o projeto usa pesos pré-treinados, baixados uma vez e rodando offline dali em diante — treinar percepção do zero exige bilhões de exemplos, e esse custo não se repete.

## ✨ Características

- **🧠 Motor Próprio**: redes densas, retropropagação e custo escritos do zero com NumPy, com prova numérica do gradiente
- **👁️ Percepção Pré-treinada**: CLIP (imagem) e Whisper (áudio) com pesos baixados uma vez — offline dali em diante
- **🔍 Investigação Inteligente**: Coleta evidências do sistema sem alterações
- **⚡ Ação Controlada**: Executa comandos com confirmação e capacidade de desfazer
- **📚 Aprendizado Contínuo**: Cada caso resolvido vira exemplo para melhorias
- **🗜️ Compressão Própria**: DEFLATE e gzip escritos do zero, conferidos byte a byte contra o `zlib`
- **🖥️ Interface Retrô**: Painel web local com tema de terminal anos 90
- **🔒 Privacidade Total**: Tudo roda localmente, seus dados nunca saem da máquina

## 🏗️ Arquitetura

O sistema é organizado em 7 camadas, cada uma podendo se abster e escalar o nível:

```
texto · print · áudio · vídeo ──▶ 1. PERCEPÇÃO (CNN do zero · FFT)
                                         ▼
                              2. ENTENDIMENTO (classificador)
                                         ▼
                              3. CONHECIMENTO (base de casos)
                                         ▼
                              4. INVESTIGAÇÃO (PowerShell · arquivos)
                                         ▼
                              5. AÇÃO (risco · confirmação · desfazer)
                                         ▼
                              6. APRENDIZADO (trava · guarda)
                                         ▼
                              7. PAINEL (servidor local)
```

### Níveis de Resolução

| Nível | O que o sistema faz | Do que precisa |
|-------|---------------------|----------------|
| **N1** | Reconhece o problema e aplica procedimento conhecido | Classificador + base de casos |
| **N2** | Não reconhece: colhe evidência da máquina e correlaciona | Percepção + investigação |
| **N3** | Evidência não fecha: entra no código e procura o defeito | Leitura de projeto + editor |
| **Desenvolvimento** | O sistema cria projetos do zero e executa pedidos |

## 🚀 Como Usar

### Instalação

```bash
# Clone o repositório
git clone https://github.com/Duduedulopes/DevDesk_AI.git
cd DevDesk_AI

# Instale as dependências
pip install -r requirements.txt
```

### Iniciar o Servidor

```bash
# Inicie o painel web
python painel/servidor.py

# Acesse no navegador
# http://localhost:8760
```

### Estrutura de Diretórios

```
DevDesk_AI/
├── nucleo/           # Motor da rede neural (Camada, Rede, Ativação, Custo)
├── texto/            # Processamento de texto (vocabulário, trigramas)
├── visao/            # CNN do zero e processamento de imagens
├── audio/            # FFT e espectrograma para áudio
├── conhecimento/     # Base de casos e memória do sistema
├── acao/             # Sistema de ações com risco e confirmação
├── painel/           # Servidor web e interface HTML
├── dados/            # Logs, modelos e dados de treinamento
├── modelos/          # Modelos treinados e checkpoints
├── programas/        # Scripts utilitários e ferramentas
├── provas/           # Testes e validações
└── caderno/          # Diário de bordo do desenvolvimento
```

## 🎯 Funcionalidades Principais

### 1. Percepção Multimodal
- **Texto**: Normalização → trigramas → peças
- **Imagem (print)**: CNN → região de texto → caractere → OCR
- **Áudio**: Janela → FFT → espectrograma de mel → CNN
- **Vídeo**: Quadros → CNN + análise de movimento

### 2. Investigação Segura
Comandos que **apenas leem** o sistema:
- Status de serviços
- Análise de logs
- Espaço em disco
- Versões de software
- Processos travados
- Estrutura de projetos

### 3. Ação Controlada
Toda alteração passa por:
1. **Nível de risco** declarado antes
2. **Confirmação** explícita do usuário
3. **Registro** completo da ação
4. **Capacidade de desfazer**

### 4. Painel Web
Interface estilo Devin com:
- Acesso ao sistema de arquivos
- Histórico de ações
- Monitor de atividades em tempo real
- Terminal integrado
- Visualização de logs

## 🧪 Testes e Validação

```bash
# A suite inteira
python -m pytest provas/ -q

# O motor: gradiente conferido contra a derivada numérica, MNIST, camadas
python -m pytest provas/test_nucleo.py -q

# A compressão: o que eu escrevo o zlib lê, e o contrário também
python provas/conferir_deflate.py

# Os modelos treinados
python testar_modelos.py
```

## 📊 Progresso do Projeto

| # | Degrau | Status |
|---|--------|--------|
| 1 | Painel web completo | ✅ |
| 2 | Integração VS Code | ✅ |
| 3 | Vídeo e Visual Studio | ✅ |
| 4 | Motor mudado de casa + provas passando | ✅ |
| 5 | Corpus e classificador do domínio de suporte | 🚧 |
| 6 | Investigação sobre leitura | ⏳ |
| 7 | CNN do zero no MNIST | 🚧 |
| 8 | OCR de print de tela | ⏳ |
| 9 | Ação com risco, confirmação e desfazer | ⏳ |
| 10 | Áudio: FFT → espectrograma → CNN | ⏳ |

## 🛠️ Stack Tecnológica

- **Python 3.8+**: Linguagem principal
- **NumPy**: o motor da rede — tudo que aprende é escrito aqui
- **OpenCV / Pillow**: leitura e preparo de imagem
- **open-clip-torch + torch**: os pesos do CLIP (percepção visual, pré-treinada)
- **faster-whisper**: os pesos do Whisper (transcrição de áudio, pré-treinada)
- **HTTP Server**: servidor web (biblioteca padrão)
- **PowerShell**: integração com o Windows

> As duas linhas de percepção são a única coisa que o projeto não escreveu:
> são pesos pré-treinados, baixados uma vez e usados offline. O resto —
> motor, classificador, compositor, compressão — é código deste repositório.

## 📝 Contribuindo

Este é um projeto de estudo, escrito para aprender como cada peça funciona
por dentro. Se algo aqui te for útil, use à vontade — e se achar um erro,
abre uma issue: erro medido vale mais que elogio.


## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 👨‍💻 Autor

**Eduardo Lopes** - 2026


**DevDesk AI** - O assistente técnico e desenvolvedor que realmente entende o seu sistema.

## 🌐 Site do Projeto

Conheça o DevDesk AI pelo site publicitário — a tese, as camadas, o estado atual de cada degrau e o painel em ação:

- **https://duduedulopes.github.io/DevDesk_AI/**
