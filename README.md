# DevDesk AI 🤖

> **Assistente de suporte técnico e desenvolvimento com rede neural própria, rodando local**

![DevDesk AI](https://img.shields.io/badge/DevDesk-AI-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 Sobre

DevDesk AI é um assistente inteligente que recebe problemas do jeito que eles chegam na vida real — um print, um áudio de alguém reclamando, um vídeo da tela travando, um texto torto — e ajuda a resolver: do N1 (procedimento conhecido) até o N3 (achar o defeito no código).

**Roda inteiro na máquina.** Sem nuvem, sem API de terceiro, sem chave. A rede é escrita do zero, com NumPy, e o que ela não souber ela aprende aqui dentro.

## ✨ Características

- **🧠 Rede Neural Própria**: CNN e redes densas escritas do zero com NumPy
- **👁️ Percepção Multimodal**: Texto, imagens (prints), áudio e vídeo
- **🔍 Investigação Inteligente**: Coleta evidências do sistema sem alterações
- **⚡ Ação Controlada**: Executa comandos com confirmação e capacidade de desfazer
- **📚 Aprendizado Contínuo**: Cada caso resolvido vira exemplo para melhorias
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
| **Humano** | O sistema não conclui, e diz exatamente o que já descartou | Registro de tudo |

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
# Rodar provas numéricas do gradiente
python programas/conferir_gradiente.py

# Testar modelos
python testar_modelos.py

# Validar CNN no MNIST
python visao/mnist/testar_cnn.py
```

## 📊 Progresso do Projeto

| # | Degrau | Status |
|---|--------|--------|
| 0 | Motor mudado de casa + provas passando | ✅ |
| 1 | Corpus e classificador do domínio de suporte | 🚧 |
| 2 | Base de casos + N1 ponta a ponta, só texto | 🚧 |
| 3 | Investigação só leitura | 🚧 |
| 4 | CNN do zero no MNIST | 🚧 |
| 5 | OCR de print de tela | ⏳ |
| 6 | Ação com risco, confirmação e desfazer | ⏳ |
| 7 | Áudio: FFT → espectrograma → CNN | ⏳ |
| 8 | Painel web completo | ✅ |
| 9 | Integração VS Code | ⏳ |
| 10 | Vídeo e Visual Studio | ⏳ |

## 🛠️ Stack Tecnológica

- **Python 3.8+**: Linguagem principal
- **NumPy**: Computação numérica e redes neurais
- **OpenCV**: Processamento de imagens
- **HTTP Server**: Servidor web (biblioteca padrão)
- **PowerShell**: Integração com sistema Windows

## 📝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 👨‍💻 Autor

**Eduardo Lopes** - 2026

## 🙏 Agradecimentos

- Inspirado na arquitetura do SO-Espacial e AutonomousStore
- Desenvolvido com foco em privacidade e processamento local
- Rede neural escrita do zero para máximo controle e transparência

---

**DevDesk AI** - O assistente técnico que realmente entende o seu sistema.