# Intenções do DevDesk — proposta para você cortar

**Isto é rascunho.** Corte, junte, renomeie, acrescente. Nenhuma frase de
treino foi gerada ainda, de propósito: mudar um nome agora custa nada; depois
de 6 mil frases geradas custa tudo.

Marque assim: `~~riscado~~` para tirar, `**negrito**` para juntar com a de
cima, e escreva o nome novo ao lado quando quiser trocar.

---

## O que "vocabulário aberto" quer dizer aqui

O conjunto de intenções é **fechado** — é o que a rede prevê, e precisa ser
finito. O que fica **aberto** é a linguagem que chega até elas.

### Os três registros, e o segundo é o que importa

Meu primeiro rascunho desenhou o corpus só para quem já é da área — build,
crash, timeout, stack trace. **Estava errado, e erraria justamente para quem
mais precisa da ferramenta**: o N1 e quem está aprendendo a programar não têm
a palavra. Descrevem o que estão VENDO.

Cada intenção precisa das duas falas, e às vezes de uma terceira:

| intenção | quem já atua | quem está aprendendo | quem só descreve a tela |
|---|---|---|---|
| `erro_de_compilacao` | o build quebrou | não deixa eu rodar | aparece um monte de coisa vermelha embaixo |
| `dependencia_faltando` | module not found | falta instalar alguma coisa | diz que não achou não sei o quê |
| `porta_ocupada` | address already in use | a porta tá presa | diz que já tem alguma coisa usando |
| `erro_em_execucao` | estourou uma exceção | deu erro quando rodei | abriu uma tela cheia de letra e fechou |
| `nao_conecta` | timeout no endpoint | não conecta no banco | fica rodandinho e não vem nada |
| `permissao_negada` | access denied | não deixa salvar | fala que não tenho permissão |

Gerar só a primeira coluna faria uma ferramenta que serve quem menos precisa
dela.

### E isso tem uma consequência técnica boa

**A fala de quem não sabe o nome é naturalmente menos específica.** "Não
funciona" cabe em seis das nove intenções de diagnóstico. A rede vai ficar
**abaixo do limiar** nessas frases — e isso não é defeito, é o comportamento
certo: ela mostra os candidatos e pergunta.

Ou seja, a abstenção que a gente construiu como trava de segurança vira aqui a
**pergunta de esclarecimento** que todo atendente faz quando a descrição é
vaga. Mesma mecânica, outro uso. E cada resposta dessas é um exemplo rotulado
por quem tinha o problema na frente.

### As três coisas que o corpus da loja não tinha

**Inglês entremeado.** Ninguém diz "sistema de construção falhou". Diz *"o
build quebrou"*. Precisa de build, deploy, commit, push, log, bug, crash,
debug, endpoint, branch, merge — do jeito que aparecem no meio do português.

**Frase pela metade.** Quem está com o erro na tela escreve *"não compila"*,
*"deu 500"*, *"porta em uso"*. Sem verbo, sem sujeito, sem contexto.

**Erro de digitação e falta de acento.** Quem digita com pressa escreve
*"nao ta compilando"*, *"comilar"*, *"dependencia"*. Os trigramas de caractere
existem no modelo exatamente para isso, mas só funcionam se o corpus tiver
o erro dentro.

---

## Conversa — 9

A língua social. É aqui que a fala é mais imprevisível, e é a mais barata de
acertar porque as frases são curtas.

| intenção | como aparece |
|---|---|
| `saudacao` | oi · bom dia · e aí · opa · fala |
| `despedida` | valeu, tchau · até mais · fecho aqui |
| `agradecimento` | obrigado · vlw · isso mesmo, brigado |
| `confirmar` | sim · pode · manda ver · isso · uhum |
| `cancelar` | não · deixa · para · esquece · cancela |
| `ajuda` | o que você faz · me ajuda · quais comandos |
| `quem_e_voce` | você é o quê · como você funciona · usa qual IA |
| `reclamacao` | você errou · não é isso · tá ruim · de novo não |
| `fora_de_escopo` | qual a capital · me conta uma piada |

## Achar e navegar — 6

| intenção | como aparece |
|---|---|
| `abrir_projeto` | abre o AdminApp · carrega esse projeto · quero mexer no X |
| `abrir_arquivo` | abre o Program.cs · mostra esse arquivo · quero ver o csproj |
| `procurar_arquivo` | cadê o appsettings · onde tá o arquivo de config |
| `procurar_no_codigo` | onde tá escrito X · quem usa essa string · procura TODO |
| `listar_pasta` | o que tem aqui · lista os arquivos · mostra a pasta |
| `estrutura_do_projeto` | como esse projeto tá organizado · quais projetos tem na solução |

## Entender — 5

| intenção | como aparece |
|---|---|
| `explicar_codigo` | o que esse método faz · me explica essa classe |
| `explicar_erro` | o que significa esse erro · NullReference no que |
| `achar_definicao` | onde essa função é definida · de onde vem essa classe |
| `achar_uso` | quem chama isso · onde isso é usado |
| `revisar_codigo` | dá uma olhada nisso · tem algo errado aqui · revisa |

## Alterar — 5

Todas escrevem. Todas param e pedem confirmação.

| intenção | como aparece |
|---|---|
| `criar_arquivo` | cria uma classe X · novo controller · adiciona um arquivo |
| `editar_codigo` | troca isso por aquilo · arruma essa linha · corrige |
| `renomear` | renomeia isso · muda o nome da variável |
| `apagar` | apaga esse arquivo · limpa a pasta obj |
| `refatorar` | extrai um método · separa isso em duas classes |

## Executar — 6

| intenção | como aparece |
|---|---|
| `rodar` | roda · executa · sobe a API · dá um run |
| `compilar` | compila · build · dotnet build · faz o build |
| `rodar_testes` | roda os testes · passa nos testes · dotnet test |
| `instalar_dependencia` | instala o pacote X · falta uma lib · pip install |
| `parar_processo` | mata o processo · para o servidor · encerra |
| `comando_livre` | roda esse comando aqui · executa isso no terminal |

## Diagnosticar — 9

O coração do suporte. As mais valiosas e as mais difíceis, porque a pessoa
descreve o **sintoma**, não a causa.

| intenção | como aparece |
|---|---|
| `erro_de_compilacao` | não compila · deu erro no build · quebrou o build |
| `erro_em_execucao` | deu exceção · crashou · estourou erro rodando |
| `nao_abre` | o programa não abre · clico e não acontece nada · nem sobe |
| `lentidao` | tá lento · demora demais · travando |
| `travou` | congelou · não responde · travou de vez |
| `porta_ocupada` | porta em uso · address already in use · a 5000 tá presa |
| `permissao_negada` | access denied · sem permissão · não deixa gravar |
| `dependencia_faltando` | module not found · falta um pacote · não acha a dll |
| `nao_conecta` | não conecta no banco · timeout · a API não responde |

## Máquina — 4

| intenção | como aparece |
|---|---|
| `estado_da_maquina` | como tá a máquina · tá tudo ok · diagnóstico geral |
| `ver_logs` | mostra o log · cadê os logs · o que deu no log |
| `processos` | o que tá rodando · quais processos · quem tá usando CPU |
| `espaco_em_disco` | tem espaço · disco cheio · quanto sobrou |

## Versionamento — 5

| intenção | como aparece |
|---|---|
| `git_estado` | o que mudou · git status · tem coisa não commitada |
| `git_historico` | últimos commits · o que foi feito ontem |
| `git_diferenca` | mostra o diff · o que mudou nesse arquivo |
| `git_enviar` | sobe pro GitHub · push · commita isso |
| `git_desfazer` | desfaz · volta o commit · descarta as mudanças |

## Ambiente — 3

| intenção | como aparece |
|---|---|
| `abrir_no_editor` | abre no VS Code · manda pro Visual Studio |
| `versao_das_ferramentas` | qual versão do dotnet · python --version · o que tá instalado |
| `variavel_de_ambiente` | falta uma variável · o PATH tá certo · onde ponho a chave |

---

## O preço, em número

**52 intenções.** Isso não é de graça, e a conta vem da nossa própria medição:

- a loja tem **42 intenções** com **5.586 frases** — cerca de 133 por intenção
- e mesmo assim acerta **58,2%** no primeiro palpite

Mais intenções com o mesmo corpus **piora**. Medimos isso três vezes neste
projeto: contexto maior, vocabulário maior de peças, e sempre o mesmo
resultado — capacidade sem dado vira decoreba.

E agora some a isso os **três registros**: a mesma intenção precisa ser
reconhecida na fala de quem sabe o nome, na de quem está aprendendo e na de
quem só descreve a tela. Isso não é "mais do mesmo" — são regiões distantes do
espaço de peças apontando para a mesma saída, e a rede precisa de exemplo em
cada uma.

Para 52 intenções nos três registros: **~9.000 frases**. Cortando para 40:
**~7.000**. A loja treinou com 5.586.

**Onde eu cortaria, se fosse cortar:** `refatorar` e `revisar_codigo` pedem
raciocínio que a rede não faz — ela roteia, não analisa. `git_desfazer` e
`apagar` são perigosas e raras. `despedida` quase não aparece.

Mas isso é palpite meu. A decisão é sua.

---

## O que eu preciso de você

1. **A lista final** — o que fica, o que sai, o que muda de nome
2. **As que faltam** — o que você faz no dia a dia e não está aí
3. **Como VOCÊ fala** — as suas palavras valem mais que as minhas. Se você
   diz "tá dando pau" em vez de "deu erro", o corpus tem que ter "tá dando pau"
