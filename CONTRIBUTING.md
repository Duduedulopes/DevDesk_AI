# Contribuindo com o DevDesk AI

Obrigado por se interessar em contribuir com o DevDesk AI! Este documento guia você através do processo de contribuição.

## Como Contribuir

### Relatando Bugs

Antes de relatar um bug:

1. Verifique se o bug já foi relatado [nas issues existentes](https://github.com/Duduedulopes/DevDesk_AI/issues)
2. Se não encontrar, abra uma nova issue com:
   - Título descritivo
   - Descrição detalhada do problema
   - Passos para reproduzir
   - Comportamento esperado vs. comportamento atual
   - Ambiente (SO, versão do Python, etc.)
   - Logs ou capturas de tela relevantes

### Sugerindo Funcionalidades

1. Verifique se a funcionalidade já foi sugerida
2. Abra uma issue com:
   - Título claro
   - Descrição detalhada da funcionalidade
   - Casos de uso
   - Exemplos de como seria útil

### Fazendo Pull Requests

#### Passo 1: Fork o Repositório

1. Clique no botão "Fork" no topo da página do GitHub
2. Clone seu fork localmente:
   ```bash
   git clone https://github.com/SEU_USUARIO/DevDesk_AI.git
   cd DevDesk_AI
   ```

#### Passo 2: Crie uma Branch

Crie uma branch para sua contribuição:

```bash
git checkout -b feature/sua-feature
# ou
git checkout -b fix/seu-bugfix
```

#### Passo 3: Faça suas Mudanças

- Siga o estilo de código existente
- Adicione testes para novas funcionalidades
- Atualize a documentação se necessário
- Commits descritivos:
  ```bash
  git add .
  git commit -m "Adiciona nova funcionalidade X"
  ```

#### Passo 4: Teste suas Mudanças

```bash
# Rodar testes
python programas/conferir_gradiente.py
python testar_modelos.py

# Verificar se o servidor funciona
python painel/servidor.py
```

#### Passo 5: Push e Pull Request

```bash
git push origin feature/sua-feature
```

Depois, abra um Pull Request no GitHub com:
- Título descritivo
- Descrição das mudanças
- Referência a issues relacionadas (se houver)
- Capturas de tela (se for mudança visual)

## Padrões de Código

### Python

- Siga PEP 8
- Use docstrings para funções e classes
- Nomes descritivos em português (como o projeto existente)
- Comentários quando necessário para explicar lógica complexa

### HTML/CSS/JavaScript

- Use indentação consistente
- Nomes descritivos para classes e IDs
- Comente seções complexas
- Mantenha compatibilidade com navegadores modernos

## Estrutura do Projeto

Respeite a estrutura existente de diretórios:

```
DevDesk_AI/
├── nucleo/           # Código core da rede neural
├── texto/            # Processamento de texto
├── visao/            # Processamento de imagens
├── audio/            # Processamento de áudio
├── conhecimento/     # Base de conhecimento
├── acao/             # Sistema de ações
├── painel/           # Interface web
├── dados/            # Dados e logs
├── modelos/         # Modelos treinados
├── programas/        # Scripts utilitários
└── provas/           # Testes e validações
```

## Testes

Antes de submeter um PR, certifique-se de:

1. Todos os testes existentes passam
2. Novas funcionalidades têm testes
3. O servidor web inicia sem erros
4. A interface funciona corretamente

## Documentação

- Atualize o README.md se adicionar funcionalidades principais
- Adicione docstrings em funções novas
- Atualize INSTALACAO.md se mudar o processo de instalação
- Comente código complexo

## Commits

Use mensagens de commit claras e descritivas:

```
Adiciona processamento de áudio com FFT
Corrige bug no gradiente da CNN
Atualiza documentação de instalação
Melhora performance do classificador
```

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a licença MIT do projeto.

## Perguntas?

Se tiver dúvidas sobre como contribuir:

1. Abra uma issue com a tag "question"
2. Entre em contato através das issues do GitHub
3. Consulte a documentação existente

## Código de Conduta

Seja respeitoso e construtivo em todas as interações:
- Respeite opiniões diferentes
- Foque no que é melhor para a comunidade
- Seja empático com outros contribuidores

---

Obrigado por contribuir com o DevDesk AI! 🚀