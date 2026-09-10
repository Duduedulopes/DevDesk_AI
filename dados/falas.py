# -*- coding: utf-8 -*-
"""O banco de falas: como cada intenção aparece na boca das pessoas.

TRÊS REGISTROS

    atua    quem já é da área e sabe o nome técnico
    aprende quem está aprendendo e descreve o que quis fazer
    tela    quem só descreve o que está vendo na tela

Cada fala está escrita do jeito que as pessoas realmente escrevem:
com erro de digitação, sem acento, inglês no meio do português,
frase pela metade, letra maiúscula gritando.
"""

FALAS = {

# ══════════════════════════════════════════════════════════
# CONVERSA
# ══════════════════════════════════════════════════════════

"saudacao": {
    "atua": [
        "oi", "opa", "e aí", "fala", "salve", "hey", "eai", "oi tudo bem",
        "bom dia", "boa tarde", "boa noite", "olá", "oi sumido",
        "fala dev", "olá tudo certo", "boa", "oi oi", "hello",
        "bom dia meu bom", "boa tarde tudo bem", "oi pode me ajudar",
        "ola", "salve salve", "hey tudo bem", "oi, voltei",
    ],
    "aprende": [
        "olá", "oi, tudo bem?", "bom dia, tudo certo?", "oi, você está aí?",
        "boa noite, posso perguntar algo", "oi, pode me ajudar",
        "oi, estou aqui de novo", "olá, preciso de ajuda",
        "boa tarde, tudo certo?", "oi, pode me atender",
        "ola, tudo bem?", "oi to precisando de ajuda",
        "bom dia, tudo bem por aí", "oi, tem alguem",
    ],
},

"despedida": {
    "atua": [
        "valeu", "falou", "tamo junto", "é isso, valeu", "até", "tchau",
        "abraço", "até mais", "vou indo", "encerrando aqui", "fechando",
        "até logo", "bye", "flw", "vlw tchau", "foi", "saindo",
        "até amanhã", "encerrando o dia", "por hoje é isso",
        "tamo bom, falou", "obg e tchau", "até mais tarde",
    ],
    "aprende": [
        "tchau", "até mais", "obrigado, até logo", "vou fechar aqui",
        "vou embora", "pode fechar", "até a próxima", "boa noite, vou dormir",
        "vou parar por hoje", "era isso, obrigado", "me ajudou muito, tchau",
        "pronto, pode fechar", "vou descansar", "até a próxima vez",
        "ok, vou sair agora", "vou embora, valeu",
    ],
},

"agradecimento": {
    "atua": [
        "vlw", "valeu mesmo", "show", "boa, obrigado", "isso aí",
        "brigado", "obg", "demais, obrigado", "top", "perfeito",
        "boa demais", "valeu mano", "show de bola", "ótimo obrigado",
        "isso era exatamente o que precisava", "mandou bem",
        "excelente", "resolveu", "salvou", "foi isso mesmo",
        "muito bom, obrigado", "funcionou, valeu",
    ],
    "aprende": [
        "obrigado", "muito obrigado", "você me ajudou muito", "era isso mesmo, obrigado",
        "obrigada", "muito obrigada", "me ajudou bastante", "perfeito, obrigado",
        "consegui resolver, obrigado", "era exatamente isso",
        "me salvou", "muito útil, obrigado", "grato",
        "mto obrigado", "obg mesmo", "valeu pela ajuda",
        "brigada", "ajudou demais", "resolveu o problema, obrigado",
    ],
},

"confirmar": {
    "atua": [
        "pode", "manda ver", "bora", "isso", "positivo", "vai",
        "ok", "certo", "afirmativo", "exato", "correto", "beleza",
        "pode fazer", "pode sim", "vai lá", "confirma", "execute",
        "sim pode", "tá bom", "yep", "yes", "confirmo", "aceito",
        "faz", "pode mandar", "vai nessa", "tô dentro", "bora lá",
    ],
    "aprende": [
        "sim", "sim, pode fazer", "está certo", "concordo", "pode sim",
        "pode fazer", "tá bom", "sim pode", "vai lá", "confirmo",
        "sim, faz isso", "tudo certo, pode fazer", "pode executar",
        "concordo, faz aí", "sim, pode mandar",
        "pode ir em frente", "sim, está correto",
        "confirma aí", "tá, pode fazer",
    ],
},

"cancelar": {
    "atua": [
        "deixa", "para", "esquece", "cancela", "não precisa mais",
        "abandona", "desiste", "não faz", "para tudo", "aborta",
        "nvm", "nevermind", "para aí", "cancela isso",
        "não precisa não", "esquece essa", "não vai",
        "não faz não", "pode parar", "deixa pra lá",
    ],
    "aprende": [
        "não", "não, obrigado", "melhor não", "prefiro não fazer isso",
        "não quero mais", "desisto", "esquece isso", "não precisa",
        "para por favor", "não faz não",
        "mudei de ideia", "não preciso mais disso",
        "pode ignorar", "deixa assim mesmo",
        "não, obrigada", "não to mais precisando",
        "pode esquecer o que pedi", "na verdade não precisa",
    ],
},

"ajuda": {
    "atua": [
        "o que você faz", "quais comandos", "lista os comandos",
        "me mostra o que dá pra fazer", "help", "comandos disponíveis",
        "o que posso pedir", "funcionalidades", "o que você sabe fazer",
        "quais são seus recursos", "me passa os comandos",
        "man devdesk", "como funciona", "tutorial",
    ],
    "aprende": [
        "me ajuda", "não sei o que fazer", "como eu uso isso", "por onde eu começo",
        "estou perdido", "o que eu posso te pedir", "como funciona isso aqui",
        "me ensina a usar", "não sei por onde começar",
        "pode me ajudar", "você pode me ajudar", "preciso de ajuda",
        "me dá uma ajuda", "você me ajuda", "precisa de ajuda aqui",
        "como eu peço as coisas", "como você funciona",
        "o que você consegue fazer", "o que você pode fazer",
        "me explica como usar", "não entendo como funciona",
        "como peço pra você fazer algo", "me orienta",
        "me ajuda a entender o que você faz", "nunca usei isso",
        "como eu começo", "que tipo de coisa posso perguntar",
        "vc consegue me ajudar com codigo", "pode me ajudar com programacao",
        "pode me ajudar a programar", "me ajuda com o projeto",
    ],
},

"quem_e_voce": {
    "atua": [
        "você usa qual modelo", "roda local ou na nuvem", "qual IA você usa",
        "qual a sua versão", "você é o chatgpt", "tem api",
        "é open source", "qual o modelo de linguagem", "usa llm",
        "roda offline", "tem chave de api", "manda dado pra fora",
    ],
    "aprende": [
        "quem é você", "o que você é", "como você funciona", "você é uma IA?",
        "você foi treinado como", "me fala sobre você", "como você foi feito",
        "você usa internet", "você manda dados pra fora",
        "você é o chatgpt", "você é o copilot", "você é o gemini",
        "você usa a openai", "você é pago", "você coleta dados",
        "como você foi criado", "quem te criou", "você é seguro",
        "você guarda minhas conversas", "meus dados ficam aqui",
        "vc e uma ia", "o que vc e", "vc usa internet",
        "como voce funciona", "voce manda dados pra fora",
    ],
},

"reclamacao": {
    "atua": [
        "não é isso", "errou", "de novo não", "tá viajando",
        "você errou de novo", "resposta errada", "não acertou",
        "entendeu tudo errado", "errou feio", "resposta inútil",
        "não foi isso que eu perguntei", "péssima resposta",
    ],
    "aprende": [
        "não era isso que eu queria", "você entendeu errado",
        "não foi isso que eu pedi", "acho que você se confundiu",
        "você não entendeu", "não é o que pedi", "entendeu diferente",
        "você interpretou errado", "não é isso não",
        "nao era isso", "voce errou", "nao entendeu nada",
        "isso nao faz sentido", "resposta completamente errada",
        "nao foi isso que eu perguntei", "confundiu tudo",
        "errou a intencao", "nao acertou nao",
    ],
},

"fora_de_escopo": {
    "atua": [
        "qual a capital da frança", "me conta uma piada", "que horas são no japão",
        "quem ganhou a copa", "previsão do tempo", "me faz um poema",
        "qual o melhor celular", "cotação do dólar", "que dia é hoje",
        "me recomenda um livro", "qual a melhor linguagem",
    ],
    "aprende": [
        "quem descobriu o brasil", "me ajuda com meu dever de história",
        "qual a receita de bolo", "me conta uma história",
        "qual o melhor restaurante", "recomenda um filme",
        "me conta uma piada", "o que é amor", "como emagrecer",
        "me ajuda com matemática", "resolve essa equação pra mim",
        "traduz esse texto", "me conta sobre a segunda guerra",
        "qual time vai ganhar", "me diz o horóscopo",
    ],
},

# ══════════════════════════════════════════════════════════
# ACHAR E NAVEGAR
# ══════════════════════════════════════════════════════════

"abrir_projeto": {
    "atua": [
        "abre o projeto {proj}", "carrega o {proj}", "sobe o {proj} aí",
        "manda o {proj} pro editor", "abre a pasta {proj}",
        "carrega projeto {proj}", "open {proj}", "abre o {proj} aqui",
        "importa o projeto {proj}", "acessa o {proj}",
    ],
    "aprende": [
        "quero mexer no {proj}", "pode abrir o projeto {proj}",
        "abre a pasta do {proj} pra mim", "preciso trabalhar no {proj}",
        "quero abrir o projeto {proj}", "como abro o {proj}",
        "quero alterar um projeto", "quero mudar um projeto",
        "preciso mexer num projeto", "quero trabalhar num projeto",
        "pode me ajudar com um projeto", "tenho um projeto pra alterar",
        "quero modificar o projeto", "vou mexer no projeto",
        "quero trabalhar no meu projeto", "preciso editar meu projeto",
        "tenho um projeto aqui", "tem um projeto que preciso abrir",
        "abre meu projeto", "como eu acesso meu projeto",
        "quero continuar meu projeto", "posso abrir um projeto aqui",
        "como carrego meu projeto", "tenho um projeto pra mostrar",
        "abri o proejto", "quer abrir um pojeto", "projeto pra abrir",
        "meu pojeto esta aqui", "tem como abrir o projeto aqui",
    ],
},

"abrir_arquivo": {
    "atua": [
        "abre o {arq}", "mostra o {arq}", "cat {arq}", "quero ver o {arq}",
        "type {arq}", "exibe o {arq}", "abre aqui o {arq}",
        "mostra o conteúdo do {arq}", "traz o {arq}",
        "lê o {arq}", "imprime o {arq}",
    ],
    "aprende": [
        "pode abrir o arquivo {arq}", "queria ver o que tem no {arq}",
        "me mostra o conteúdo do {arq}", "quero ler o {arq}",
        "me abre o {arq} por favor", "mostra o arquivo {arq}",
        "quero ver o que tem no arquivo", "pode mostrar o arquivo",
        "me mostra esse arquivo", "como vejo o conteúdo do arquivo",
        "abre esse arquivo aqui", "quero ver o código do arquivo",
        "me traz o arquivo", "pode ler esse arquivo pra mim",
        "mostar o arqiuvo", "abir o arquivo", "ve o {arq}",
        "cat o {arq}", "ler o arquivo {arq}",
    ],
},

"procurar_arquivo": {
    "atua": [
        "cadê o {arq}", "onde tá o {arq}", "acha o {arq}", "find {arq}",
        "procura o {arq}", "localiza o {arq}", "find . -name {arq}",
        "busca o {arq}", "where is {arq}",
    ],
    "aprende": [
        "não estou achando o arquivo {arq}", "onde fica o {arq}",
        "procura o arquivo {arq} pra mim", "em que pasta está o {arq}",
        "não acho o {arq}", "me ajuda a achar o {arq}",
        "sumiu o arquivo", "não encontro o arquivo",
        "onde está o arquivo de configuração", "não acho o config",
        "cadê o arquivo de settings", "onde fica o arquivo principal",
        "nao acho o arqiuvo", "cade o {arq}", "sumiu o {arq}",
        "nao encontro o arquivo {arq}", "onde ta o {arq}",
        "onde fica o arquvo", "procura o arquvo {arq}",
    ],
},

"consultar_dados": {
    # A INTENÇÃO DA REDE QUE ESCREVE LINQ.
    #
    # O que a distingue de `procurar_no_codigo` é o OBJETO: lá se procura
    # uma palavra DENTRO dos arquivos; aqui se pergunta sobre os DADOS
    # que o código carrega. "onde tá escrito Valor" é uma; "soma o valor
    # das transações" é a outra. Por isso as frases daqui carregam verbo
    # de conta (soma, conta, agrupa, ordena, filtra) e nunca
    # "procura"/"acha", que são de lá.
    "atua": [
        "soma o {campo} das {dados}", "soma o total de {campo} das {dados}",
        "qual o total de {campo} das {dados}",
        "quanto dá a soma do {campo} das {dados}",
        "quanto deu a soma das {dados}",
        "calcula a soma de todas as {campo} das {dados}",
        "conta quantas {dados} estão {estado}",
        "quantas {dados} estão {estado}", "quantos {dados} estão {estado}",
        "quantas {dados} tem {campo} igual a pendente",
        "quantidade de {dados} com {campo} acima de 1000",
        "conta as {dados} {estado}", "me diz quantas {dados} estão {estado}",
        "me mostra as {dados} {estado}", "lista as {dados} {estado}",
        "quero as {dados} {estado}", "traz as {dados} {estado}",
        "filtra as {dados} com {campo} acima de 1000",
        "me mostra as {dados} com {campo} igual a ativo",
        "lista as {dados} com {campo} abaixo de 100",
        "agrupa as {dados} por {campo}", "separa as {dados} por {campo}",
        "quantas {dados} tem de cada {campo}",
        "agrupa {dados} por {campo}",
        "ordena as {dados} por {campo}",
        "ordena as {dados} por {campo} do maior para o menor",
        "me lista as {dados} do maior {campo} para o menor",
        "classifica as {dados} por {campo} decrescente",
        "me mostra só o {campo} das {dados}",
        "quero apenas o {campo} das {dados}",
        "extrai o {campo} das {dados}",
        "pega a primeira {dados} com {campo} igual a Ana",
        "acha a primeira {dados} com {campo} acima de 5000",
        "existe alguma {dados} com {campo} acima de 5000",
        "tem alguma {dados} com {campo} igual a pendente",
        "todas as {dados} tem {campo} acima de zero",
        "confere se todas as {dados} tem {campo} preenchido",
        "escreve o linq que soma o {campo} das {dados}",
        "gera a consulta linq das {dados} {estado}",
        "monta a query das {dados} por {campo}",
        "faz um where nas {dados} com {campo} igual a pendente",
        "linq pra somar o {campo} das {dados}",
        "me dá a consulta pra contar as {dados}",
        "no projeto {proj}, soma o {campo} das {dados}",
        "no {proj} conta quantas {dados} estão {estado}",
        "consulta as {dados} com {campo} abaixo de 100",
        "soma o {campo} das {dados} {estado}",
        "qual o total de {campo} das {dados} {estado}",
        "quantas {dados} tem {campo} acima de 1000",
    ],
    "aprende": [
        "como eu faço uma consulta linq nisso",
        "dá pra somar só as {dados} {estado}",
        "qual o linq pra agrupar por {campo}",
        "você consegue escrever a query pra mim",
        "como eu filtro as {dados} por {campo}",
        "tem como contar quantas {dados} tem",
        "qual a consulta pra pegar a primeira {dados}",
        "como somar um campo de uma lista",
        "que linq eu uso pra ordenar por {campo}",
        "consegue montar a consulta das {dados}",
        "como eu pego só uma coluna da lista",
        "qual método do linq soma",
        "uso where ou count aqui",
        "dá pra fazer isso com linq",
        "preciso de uma query pra essa lista de {dados}",
        "como eu conto os registros filtrados",
        "tem jeito de agrupar essa lista por {campo}",
        "qual a sintaxe do linq pra isso",
        "escreve pra mim a consulta das {dados}",
        "consegue montar um linq com where e sum",
        "quero uma consulta nos dados das {dados}",
        "me mostra como consultar essa lista",
        "como filtrar e somar ao mesmo tempo",
        "qual consulta me dá o total por {campo}",
        "quantas {dados} {estado} eu tenho?",
        "qual o total de {campo} mesmo?",
        "e as {dados} {estado}, quantas são?",
        "quanto deu o total das {campo}?",
        "dá pra ver as {dados} agrupadas por {campo}?",
        "como eu somo o {campo} só das {estado}",
        "me ajuda a montar essa consulta",
        "preciso saber quantas {dados} estão {estado}",
    ],
    "tela": [
        "tô com uma lista de {dados} aqui e preciso filtrar",
        "tenho essa lista de objetos e queria contar",
        "abri o {proj} e preciso somar uma coluna",
        "essa lista tá grande, quero só as {estado}",
        "tenho os dados na memória e queria agrupar por {campo}",
        "essa List<{nome}> precisa de um filtro",
        "carreguei as {dados} e agora preciso do total",
        "tenho {dados} demais, quero só as {estado}",
    ],
},
"procurar_no_codigo": {
    "atua": [
        "grep {termo}", "onde tá escrito {termo}", "procura {termo} no código",
        "quem usa {termo}", "findstr {termo}", "busca {termo} nos arquivos",
        "grep -r {termo}", "search {termo}", "find in files {termo}",
        "onde aparece {termo}", "ctrl+shift+f {termo}",
    ],
    "aprende": [
        "em que arquivo aparece {termo}", "procura a palavra {termo}",
        "onde essa parte do código está escrita",
        "em qual arquivo tem {termo}", "onde está escrito {termo}",
        "procura esse trecho de código", "onde fica essa string",
        "em que arquivo está essa função", "busca no código",
        "acha onde tá escrito isso", "procura esse texto no projeto",
        "qual arquivo tem essa linha", "onde está esse método",
        "procrua o {termo} no codigo", "acha {termo} no projeto",
        "where {termo}", "grep {termo} nos arquivos",
    ],
},

"listar_pasta": {
    "atua": [
        "ls", "dir", "lista aí", "o que tem nessa pasta",
        "lista os arquivos", "mostra o diretório", "get-childitem",
        "ls -la", "dir /b", "list files", "o que tem aqui",
    ],
    "aprende": [
        "me mostra os arquivos", "quais arquivos tem aqui",
        "quero ver o que tem na pasta", "o que tem aqui",
        "lista o conteúdo", "quais arquivos estão aqui",
        "me mostra o que tem nessa pasta", "quais são os arquivos",
        "mostra os arquivos do projeto", "o que tem nessa pasta aqui",
        "me diz o que tem aqui", "lista tudo que tem aqui",
        "mostar os arquivos", "listar a pasta", "o que ta na psta",
        "quais arqiuvos tem aqui", "mostra a lista de arquivos",
    ],
},

"estrutura_do_projeto": {
    "atua": [
        "como esse projeto tá organizado", "quais projetos tem na solução",
        "mostra a estrutura", "quantas camadas tem aqui",
        "mostra as pastas", "tree", "estrutura de pastas",
        "arquitetura do projeto", "como está dividido",
        "mostra a árvore de pastas",
    ],
    "aprende": [
        "não entendi como esse projeto é dividido",
        "o que cada pasta dessas faz", "me explica a organização dos arquivos",
        "como o projeto está organizado", "quais são as pastas do projeto",
        "como esse projeto está estruturado", "me explica a estrutura",
        "quais são as partes do projeto", "me mostra como tá organizado",
        "como o código está dividido", "quais módulos tem aqui",
        "me explica a arquitetura", "como esse sistema é estruturado",
        "como ta organizado o pojeto", "estrutura do pojeto",
        "como ta dividido o projeto", "me mostra a estrutra",
        "como funciona a organizacao do projeto",
    ],
},

# ══════════════════════════════════════════════════════════
# ENTENDER
# ══════════════════════════════════════════════════════════

"explicar_codigo": {
    "atua": [
        "o que esse método faz", "explica essa classe", "o que isso retorna",
        "pra que serve isso", "o que esse bloco faz", "explica esse trecho",
        "o que faz esse código", "explica essa função",
        "what does this do", "explain this code",
        "como esse código funciona", "o que essa linha faz",
    ],
    "aprende": [
        "não entendi esse código", "me explica o que está acontecendo aqui",
        "para que serve essa parte", "o que essa linha faz",
        "não sei o que esse código faz", "me explica esse código",
        "o que é isso aqui", "não entendo o que isso faz",
        "pode me explicar esse trecho", "o que acontece aqui",
        "me explica essa parte do código", "como funciona essa parte",
        "não entendo essa lógica", "o que esse trecho faz",
        "pode me ajudar a entender esse código",
        "esse código faz o quê exatamente",
        "o que essa funçao faz", "nao entendo esse codigo",
        "me explica esse metodo", "o que e esse codigo aqui",
        "consege me explicar esse trcho", "esse metodo faz oq",
    ],
    "tela": [
        "tem um monte de código aqui que eu não sei o que é",
        "apareceu um código que não entendo",
        "tem um trecho que não faço ideia o que faz",
        "essa parte aqui não entendo nada",
        "o código tá cheio de coisa que não conheço",
    ],
},

"explicar_erro": {
    "atua": [
        "o que significa esse erro", "o que é NullReference", "esse stack trace diz o quê",
        "o que quer dizer esse exception", "me explica esse erro",
        "NullPointerException significa o quê", "o que é esse error",
        "what is this error", "explain this exception",
        "o que é IndexOutOfRange", "o que é KeyError",
        "o que é AttributeError",
    ],
    "aprende": [
        "não entendi o erro", "o que esse erro quer dizer",
        "me explica essa mensagem", "por que deu isso",
        "o que significa essa mensagem de erro", "esse erro é sério",
        "o que aconteceu aqui", "não entendo essa mensagem",
        "o que quer dizer isso que apareceu", "me explica o que deu errado",
        "o que é esse erro que apareceu", "o que significa esse aviso",
        "nao entendi o erro", "me explica esse erro aqui",
        "o que quer dizer essa mnesagem de erro",
        "por que deu esse erro", "o que significa isso aqui",
        "esse erro quer dizer o que", "nao entendo essa mnesagem",
        "o que e esse excpetion", "o que é nullreference",
    ],
    "tela": [
        "apareceu uma mensagem aqui e não sei o que é",
        "tem um texto vermelho e não entendo",
        "tem uma mensagem de erro que não entendo",
        "apareceu um negócio escrito aqui que não entendo",
        "tem uma janela com texto que não sei o que significa",
        "saiu uma mensagem estranha",
    ],
},

"achar_definicao": {
    "atua": [
        "onde essa função é definida", "de onde vem essa classe", "go to definition",
        "onde foi declarado isso", "peek definition", "vai pra definição",
        "F12", "ctrl+clique", "where is defined", "find declaration",
    ],
    "aprende": [
        "em que arquivo isso foi criado", "onde foi que declararam isso",
        "em que lugar essa função está", "onde está a definição disso",
        "de onde vem esse método", "onde foi declarada essa variável",
        "em que arquivo está essa classe", "onde fica a definição",
        "onde esse método foi criado", "de onde vem esse objeto",
        "onde e definida essa funcao", "onde foi declardo isso",
        "onde ta a definicao desse metodo", "de onde vem essa clase",
    ],
},

"achar_uso": {
    "atua": [
        "quem chama isso", "onde isso é usado", "find references",
        "quem usa esse método", "find usages", "referências disso",
        "shift+F12", "show usages", "quem depende disso",
    ],
    "aprende": [
        "em que lugares essa função aparece", "quem usa esse método",
        "onde é chamado isso", "em quais arquivos isso é usado",
        "que partes do código usam isso", "onde esse método é chamado",
        "quem chama essa função", "onde essa classe é usada",
        "em que parte do código isso aparece", "quem usa essa variável",
        "onde usam esse metodo", "quem usa essa funcao",
        "onde e chamado isso", "em que lugar isso e usado",
    ],
},

"revisar_codigo": {
    "atua": [
        "dá uma olhada nisso", "revisa esse trecho", "tem algo errado aqui",
        "code review disso", "revisa pra mim", "review esse código",
        "analisa esse trecho", "verifica esse código",
    ],
    "aprende": [
        "será que isso está certo", "você acha que tem problema nesse código",
        "pode conferir se fiz certo", "tem algum erro aqui",
        "está correto isso que eu fiz", "esse código está ok",
        "tem alguma coisa errada aqui", "pode revisar isso pra mim",
        "esse código funciona", "tem algo que posso melhorar aqui",
        "está bom assim", "pode checar se está correto",
        "sera que ta certo", "tem erro aqui", "revisa esse codigo",
        "pode verficar esse codigo", "esse codigo ta ok",
        "tem alogma coisa errada aqui", "verfica pra mim",
    ],
},

# ══════════════════════════════════════════════════════════
# ALTERAR
# ══════════════════════════════════════════════════════════

"criar_projeto": {
    "atua": [
        "cria um projeto {nome} em {ling}", "novo projeto {ling}",
        "scaffold {nome}", "inicia um projeto {ling}", "bootstrap {nome}",
        "cria a estrutura de um projeto em {ling}", "monta um projeto {ling}",
        "novo projeto console em {ling}", "cria uma api em {ling}",
        "cria uma biblioteca em {ling}", "cria um site em {ling}",
        "gera o esqueleto de um projeto {ling}", "new project {ling}",
        "create a project in {ling}", "cria projeto {nome} {ling}",
        "monta a estrutura do {nome}", "starter {ling}",
        "cria um projeto do zero em {ling}", "quero um projeto {ling} novo",
        "estrutura inicial de projeto {ling}",
    ],
    "aprende": [
        # ── o pedido como PERGUNTA, que é como muita gente escreve ──
        "vc pode criar o projeto de uma calculadora?",
        "voce pode criar um projeto pra mim?",
        "você consegue montar um projeto do zero?",
        "da pra vc criar um projeto de agenda?",
        "sera que vc consegue criar um projeto de loja?",
        "tem como criar um projeto de cadastro?",
        "voce cria projeto?", "vc monta projeto do zero?",
        "consegue fazer um projeto de calculadora pra mim?",
        # ── imperativo com objeto indireto ──
        "crie para mim o projeto de um aluguel de carros",
        "cria pra mim um projeto de biblioteca",
        "faz pra mim um projeto de calculadora",
        "monta pra mim o projeto de uma agenda",
        "cria um projeto de controle de estoque para mim",
        "me faz um projeto de cadastro de clientes",
        # ── o pedido descrevendo o CONTEÚDO, não o tipo ──
        "crie um projeto com exemplos de encapsulamento, herança, polimorfismo e interface",
        "quero um projeto que mostre herança e polimorfismo",
        "cria um projeto de exemplo com classes e interfaces",
        "faz um projeto que tenha um crud simples",
        "quero um projeto com um teste rodando",
        "cria um projeto pra eu estudar orientação a objetos",
        # ── os que vieram do criar_arquivo ──
        "pode me ajudar a criar um projeto", "quero criar um projeto novo",
        "como eu crio um projeto", "me ajuda a criar um projeto",
        "preciso criar um projeto do zero", "quero começar um projeto novo",
        "como começo um projeto", "criar projeto novo",
        "me ajuda a montar um projeto", "quero criar uma aplicação",
        "me ajuda a criar o projeto", "quero montar um projeto do zero",
        "como começo uma aplicação", "tenho que criar um projeto",
        "preciso iniciar um projeto", "vou criar um projeto novo",
        # ── com erro de digitação, sem acento, do jeito que sai ──
        "cria um projteo novo pra mim", "quero criar um projeto do zeroo",
        "me ajuda a criar um projeto novo por favor",
        "preciso montar um projeto mas nao sei por onde comecar",
        "como que eu comeco um projeto do zero",
        "quero fazer um programa novo mas nao sei a estrutura",
        # ── inglês, que ele pediu junto com o português ──
        "can you create a project for me?",
        "please create a calculator project",
        "i need a new project from scratch",
        "make me a project with tests",
        "could you build a small api project?",
        "how do i start a new project",
    ],
    "tela": [
        "a pasta ta vazia, preciso comecar um projeto",
        "abri o editor e nao tem nada aqui",
        "tenho uma pasta vazia e preciso montar o projeto",
        "nao tem nenhum arquivo, tenho que criar tudo",
        "comecei do zero e nao sei que arquivos criar",
        "so tenho a pasta, falta o resto",
    ],
},

"criar_arquivo": {
    "atua": [
        "cria uma classe {nome}", "novo controller {nome}", "cria o arquivo {arq}",
        "adiciona o arquivo {arq}", "new file {arq}", "cria {arq}",
        "touch {arq}", "new class {nome}", "adiciona classe {nome}",
    ],
    "aprende": [
        "preciso criar um arquivo novo", "como eu adiciono uma classe",
        "quero fazer um arquivo chamado {arq}", "como crio um arquivo",
        "preciso de um arquivo novo chamado {arq}",
                                                "preciso de uma nova classe", "como crio uma nova classe",
        "quero adicionar um arquivo", "como adiciono um novo arquivo",
        "preciso criar um módulo novo", "como crio um novo módulo",
        "quero criar um componente", "preciso de um novo controller",
        "cria un arquivo pra mim", "novo arquivo aqui",
        "como crio um arqiuvo", "preciso criar um arquvo",
        "como faco pra criar uma classe",                 "pode me ajudar a montar isso",             ],
},

"editar_codigo": {
    "atua": [
        "troca {termo} por {nome}", "arruma essa linha", "corrige isso aqui",
        "modifica essa parte", "altera isso", "muda isso aqui",
        "edita essa linha", "substitui {termo}", "fix isso",
        "patch essa parte", "update essa linha",
    ],
    "aprende": [
        "preciso mudar uma coisa nesse arquivo",
        "como eu altero esse trecho", "quero editar o {arq}",
        "preciso fazer uma mudança aqui", "me ajuda a editar isso",
        "quero alterar o código", "preciso modificar isso aqui",
        "quero fazer uma alteração no código", "como altero o código",
        "me ajuda a alterar essa parte", "preciso trocar uma coisa aqui",
        "como mudo essa linha", "quero modificar esse método",
        "preciso ajustar esse trecho", "como edito isso aqui",
        "quero trocar esse valor", "preciso mudar essa lógica",
        "como troco essa parte do código", "quero atualizar isso",
        "como faço pra alterar isso", "editar o codigo aqui",
        "altear essa parte", "quero muda essa linha",
        "como eu edito o codigo", "preciso altera isso aqui",
        "como faco pra mudar isso", "muda essa parte pra mim",
        "quero alterar um projeto", "quero alterar o projeto",
        "vou alterar o projeto", "alterar o código do projeto",
    ],
},

"renomear": {
    "atua": [
        "renomeia pra {nome}", "muda o nome da variável", "rename isso",
        "renomeia o arquivo", "troca o nome disso", "renomeia {arq}",
        "move {arq}", "mv {arq}", "rename to {nome}",
    ],
    "aprende": [
        "quero trocar o nome desse arquivo", "como eu renomeio essa classe",
        "como troco o nome da variável", "quero renomear isso",
        "preciso mudar o nome disso", "como renomeio esse arquivo",
        "quero dar outro nome pra isso", "como troco o nome da função",
        "preciso renomear essa variável", "como mudo o nome desse método",
        "como renomeo esse arquivo", "quero trocra o nome",
        "preciso mudar o nome desse arquivo", "renomear a varivel",
        "como renomio essa classe", "troca o nome desse arquivo pra mim",
    ],
},

"apagar": {
    "atua": [
        "apaga o {arq}", "limpa a pasta obj", "remove isso", "deleta",
        "delete o {arq}", "rm {arq}", "exclui o {arq}",
        "remove o {arq}", "del {arq}", "drop isso",
    ],
    "aprende": [
        "quero excluir esse arquivo", "posso apagar essa pasta",
        "como apago isso", "quero deletar o {arq}",
        "me ajuda a apagar esse arquivo",
        "preciso deletar esse arquivo", "como excluo isso",
        "quero remover esse arquivo", "pode apagar isso pra mim",
        "como deleto esse arquivo", "preciso limpar essa pasta",
        "como removo esse arquivo", "quero excluir essa classe",
        "apaga esse arquivo pra mim", "como apago essa pasta",
        "deleta o arqiuvo", "apaga ese arquivo",
        "como faço pra deletar isso", "quer apagar o arquivo",
        "preciso rmover esse arquivo",
    ],
},

"refatorar": {
    "atua": [
        "extrai um método", "separa isso em duas classes", "refatora esse trecho",
        "extrai essa função", "reorganiza o código", "simplifica isso",
        "inline isso", "dry isso", "remove duplicação",
        "separa responsabilidades", "quebra essa classe",
    ],
    "aprende": [
        "esse código está muito grande, dá pra melhorar",
        "como eu organizo isso melhor", "esse código está bagunçado",
        "me ajuda a melhorar esse código", "quero refatorar isso aqui",
        "esse código tá repetido demais", "tem muita duplicação aqui",
        "como melhoro esse código", "quero deixar isso mais limpo",
        "esse método tá muito grande", "como simplifico esse código",
        "esse código é confuso, me ajuda", "como organizo melhor isso",
        "quero melhorar a qualidade do código", "isso precisa de refatoração",
        "esse codigo ta feio", "como melhorar esse codigo",
        "codigo bagunçado aqui", "como organizo melhor o codigo",
        "esse metodo ta grande demais", "refatora esse codigo pra mim",
        "esse codigo ta ruim, como melhoro", "quero limpra o codigo",
    ],
},

# ══════════════════════════════════════════════════════════
# EXECUTAR
# ══════════════════════════════════════════════════════════

"rodar": {
    "atua": [
        "roda", "executa", "sobe a API", "dá um run", "dotnet run",
        "python {arq}", "flask run", "node {arq}", "npm start", "yarn start",
        "go run", "cargo run", "java -jar", "mvn spring-boot:run",
        "roda o projeto", "sobe o servidor", "executa o programa",
    ],
    "aprende": [
        "como eu rodo isso", "quero executar o programa", "pode rodar pra mim",
        "como executo esse projeto", "como inicio o servidor",
        "como faço rodar isso", "inicia o programa",
        "como eu inicio isso", "sobe o servidor", "roda o programa",
        "faz rodar", "executa o programa pra mim",
        "como eu rodo o projeto", "como executo isso aqui",
        "como subo a aplicação", "como inicio a aplicação",
        "como rodo esse código", "pode iniciar o servidor",
        "como faço pra rodar", "preciso executar isso",
        "como rodo esse projeto", "como inicio o programa",
        "como roda isso aqui", "como faco rodar",
        "como eu executo o pojeto", "roda o pojeto pra mim",
        "como incio isso", "sobe a apicação pra mim",
        "como executo o pogrma", "como rodo o progama",
    ],
},

"compilar": {
    "atua": [
        "compila", "build", "dotnet build", "faz o build",
        "npm run build", "mvn compile", "go build", "gcc", "g++",
        "make", "cmake --build", "tsc", "webpack",
        "compila o projeto", "build the project",
    ],
    "aprende": [
        "como eu compilo esse projeto", "preciso gerar o programa",
        "como faço o build", "como compilo isso",
        "preciso compilar antes de rodar",
        "como gero o executável", "como compilo o código",
        "preciso buildar isso", "como faço o build do projeto",
        "não sei compilar esse projeto", "como gero os binários",
        "como compilo em release", "preciso gerar a versão final",
        "como faco o build", "como compilo o pojeto",
        "como faço pra compilar", "preciso compilar o pojeto",
        "como buildo isso", "nao sei como compilar",
        "como gero o excutavel", "como compilo esse codigo",
    ],
},

"rodar_testes": {
    "atua": [
        "roda os testes", "dotnet test", "pytest", "passa nos testes",
        "npm test", "jest", "mvn test", "go test", "rspec",
        "mocha", "unittest", "vitest --run", "cypress run",
        "roda a suite de testes", "run tests",
    ],
    "aprende": [
        "quero testar se está funcionando", "como eu executo os testes",
        "como rodo os testes", "quero ver se os testes passam",
        "me ajuda a rodar os testes", "como testo esse código",
        "os testes estão passando", "como executo os unit tests",
        "quero rodar o teste unitário", "como verifico se funciona",
        "preciso testar isso", "como valido o código",
        "como faco os testes rodarem", "como executo os tetes",
        "como rodo os tsetes", "quero ver se os tetes passam",
        "roda os testes pra mim", "como teto esse codigo",
        "como executo o pytest", "roda o pytest aqui",
    ],
},

"instalar_dependencia": {
    "atua": [
        "instala o {pkg}", "pip install {pkg}", "add package {pkg}",
        "npm i {pkg}", "dotnet add package {pkg}", "yarn add {pkg}",
        "gem install {pkg}", "cargo add {pkg}", "go get {pkg}",
        "apt install {pkg}", "brew install {pkg}",
        "instala o pacote {pkg}", "adiciona a lib {pkg}",
    ],
    "aprende": [
        "preciso instalar uma biblioteca", "como eu adiciono o {pkg}",
        "falta um pacote aqui", "como instalo o {pkg}",
        "me ajuda a instalar o {pkg}",
        "preciso de uma lib nova", "como adiciono uma dependência",
        "preciso do pacote {pkg}", "como instalo essa biblioteca",
        "preciso adicionar uma dependência", "como coloco o {pkg} no projeto",
        "falta uma biblioteca aqui", "como instalo o módulo {pkg}",
        "preciso do npm package {pkg}", "como adiciono {pkg} ao projeto",
        "como insatlo o {pkg}", "precisso instalar o {pkg}",
        "falta instalar o {pkg}", "como adicionado o {pkg}",
        "preciso instalar o pacote {pkg}", "como instalo uma lib",
        "falta uma lib aqui", "como adiciono essa depedencia",
        "preciso do pacote", "como instalo as dependencias",
    ],
},

"parar_processo": {
    "atua": [
        "mata o processo", "para o servidor", "kill isso", "encerra a aplicação",
        "taskkill", "pkill", "mata o pid", "kill -9", "ctrl+c",
        "stop the server", "para o serviço", "encerra o processo",
    ],
    "aprende": [
        "como eu paro isso que está rodando", "quero fechar o programa que abri",
        "como encerro o servidor", "como mato o processo",
        "preciso parar o que está rodando", "como paro a aplicação",
        "quero derrubar o servidor", "como encerro isso",
        "preciso matar esse processo", "como fecho o servidor",
        "como paro esse serviço", "quero parar a execução",
        "como paro o servidor que subi", "preciso fechar a aplicação",
        "como mato o serivdor", "para o processo aqui",
        "como encerro o pograma", "preciso parar o servidor",
        "como fecho o pogrma que abri", "mata o porocesso",
    ],
},

"comando_livre": {
    "atua": [
        "roda esse comando", "executa isso no terminal", "manda no powershell",
        "roda no cmd", "executa no bash", "roda no terminal",
        "executa no shell", "roda esse script",
    ],
    "aprende": [
        "pode rodar isso pra mim no terminal", "como eu executo esse comando",
        "me ajuda a rodar esse comando", "preciso executar um comando",
        "roda esse negócio no terminal", "executa esse script pra mim",
        "como rodo esse comando", "pode executar isso no terminal",
        "roda no powershell pra mim", "preciso que execute isso",
        "executa no temrinal", "roda esse comando pra mim",
        "como executo esse cmando", "roda isso no terimnal pra mim",
        "preciso rodar um cmando", "executa esse scrpit",
    ],
},

# ══════════════════════════════════════════════════════════
# DIAGNOSTICAR
# ══════════════════════════════════════════════════════════

"erro_de_compilacao": {
    "atua": [
        "não compila", "o build quebrou", "deu erro no build", "build falhou",
        "erro de compilação", "build error", "compile error",
        "syntax error", "o build não passa", "compilation failed",
        "deu erro de syntax", "deu erro de compilação",
        "build quebrou", "não ta compilando", "erro no build",
    ],
    "aprende": [
        "não deixa eu rodar", "deu erro quando fui compilar",
        "não consigo gerar o programa", "não está compilando",
        "deu um erro que não entendo ao compilar",
        "não consegui compilar", "o código não compila",
        "apareceu erro na compilação", "deu problema no build",
        "não consigo fazer o build", "o projeto não compila",
        "apareceu monte de erro ao compilar", "não ta deixando compilar",
        "deu erro ao tentar compilar", "não deixa eu fazer o build",
        "nao compila", "deu erro no bild", "o biuld quebrou",
        "erro de compilcao", "nao consigo compilar",
        "deu eroo ao compilar", "nao ta compilando",
        "build falohu", "compilation eror",
        "me ajuda a corrigir o erro de compilação",
        "me ajuda a resolver esse erro de compilação",
        "corrige o erro de compilação", "corrige esse erro de build",
        "arruma esse erro de compilação", "arruma o build pra mim",
        "por que não compila", "por que meu código não compila",
        "como resolvo o erro de compilação",
        "o programa está com erro de compilação", "tira esse erro de compilação",
        "me ajuda a corrigir o erro de compilacao", "corrige o erro de compilcao",
        "nao consigo corrigir o erro de compilação",
    ],
    "tela": [
        "aparece um monte de coisa vermelha embaixo",
        "apareceram vários erros na lista",
        "tem uns riscos vermelhos no código",
        "tem sublinhado vermelho em tudo",
        "ficou tudo vermelho no editor",
        "apareceu um monte de erro embaixo",
        "tem uns x vermelhos na lista de erros",
    ],
},

"erro_em_execucao": {
    "atua": [
        "estourou uma exceção", "crashou", "deu unhandled exception",
        "quebrou em runtime", "deu exception", "threw an error",
        "stack overflow", "deu NullPointerException", "segfault",
        "deu crash", "exception não tratada", "runtime error",
    ],
    "aprende": [
        "deu erro quando rodei", "abriu e deu problema",
        "começou a rodar e parou com erro",
        "deu um erro quando tentei executar",
        "não consegui rodar sem erro", "deu problema na execução",
        "apareceu uma exceção", "o programa parou com erro",
        "deu erro durante a execução", "o código rodou mas deu erro",
        "deu erro inesperado", "a aplicação caiu com erro",
        "deu exception quando executei", "o programa travou com erro",
        "deu eror quando rodei", "estourou uma excecao",
        "deu unhandeld exception", "crashou ao rodar",
        "deu eroo na execucao", "quebrou no runtiime",
        "o pogrma parou com erro", "deu excpetion",
        "me ajuda a corrigir o erro de execução",
        "corrige esse erro de runtime", "arruma esse erro de execução",
        "o programa está dando erro de execução",
        "como resolvo o erro de execução", "por que ele cai com erro",
        "me ajuda com esse erro de execucao", "corrige o erro de execução",
    ],
    "tela": [
        "abriu uma tela cheia de letra e fechou",
        "apareceu uma janela de erro",
        "o programa fechou sozinho",
        "abriu e fechou na hora",
        "apareceu uma tela preta com texto e fechou",
        "o programa sumiu com uma mensagem",
        "abriu uma janela estranha e fechou",
    ],
},

"nao_abre": {
    "atua": [
        "não sobe", "nem inicia", "morre no start", "não abre de jeito nenhum",
        "não inicia", "crash on startup", "não abre",
        "morre na inicialização", "falha ao iniciar",
    ],
    "aprende": [
        "o programa não abre", "não está abrindo", "não consigo abrir",
        "tentei abrir mas não abre", "o programa não inicia",
        "não consigo iniciar o programa", "o aplicativo não abre",
        "não está subindo", "o servidor não sobe",
        "não consegui abrir a aplicação",
        "o pograma nao abre", "nao consegui abrir",
        "nao ta abrindo", "nao inicia",
        "o programa nao consegeu abrir", "nao sobe",
        "nao abre de jeito nenhum",
        "me ajuda, o programa não abre", "corrige o problema do programa que não abre",
        "o que faço quando o programa não abre", "ajuda a abrir o programa",
        "por que não abre", "não consigo fazer o programa abrir",
    ],
    "tela": [
        "clico e não acontece nada",
        "aparece e some na hora",
        "fica carregando e não abre",
        "fico clicando e não faz nada",
        "clico duas vezes e não abre",
        "aparece o ícone e some",
        "fica girando e não abre",
    ],
},

"lentidao": {
    "atua": [
        "tá lento", "performance ruim", "demora demais pra responder",
        "high latency", "lag", "lento demais", "latência alta",
        "response time alto", "throughput baixo",
    ],
    "aprende": [
        "está muito devagar", "demora muito pra abrir", "ficou lento hoje",
        "está demorando mais que o normal", "ficou lento do nada",
        "a resposta está muito lenta", "está travando muito",
        "demora demais pra processar", "o tempo de resposta aumentou",
        "está muito mais lento que antes",
        "to lento", "ficou mto lento", "ta demorando mto",
        "demora pra caramba", "lento demais hoje",
        "ficou lerdo", "ta lerdo demais", "muito lerdo",
        "demora muito pra respoinder", "ta mto lento",
        "me ajuda, está muito lento", "corrige o problema de lentidão",
        "por que está tão lento", "o que ta travando o sistema",
        "ajuda com a lentidão", "como deixo o sistema mais rápido",
        "o que está deixando lento", "me ajuda com o lag",
    ],
    "tela": [
        "fica rodandinho um tempão",
        "a bolinha fica girando",
        "fica carregando e não termina",
        "a barra de progresso não avança",
        "fica travando a todo momento",
        "a tela fica piscando",
    ],
},

"travou": {
    "atua": [
        "travou", "congelou", "não responde", "freezou",
        "hanging", "deadlock", "loop infinito", "stuck",
        "não processa mais", "parou de responder",
    ],
    "aprende": [
        "parou de responder", "travou tudo aqui",
        "o programa parou de funcionar", "não está respondendo",
        "ficou travado", "não consigo fazer nada", "parou de processar",
        "o sistema travou", "não clica em nada",
        "travou completamente",
        "travou", "froze", "congelou tudo",
        "nao responde mais", "ficou preso",
        "o pograma travou", "nao consegue fazer nada",
        "trvou tudo", "nao ta respondendo",
        "me ajuda, meu programa travou", "o programa travou, o que eu faço",
        "me ajuda, travou aqui", "o que faço com o programa travado",
        "como resolvo um programa travado", "ajuda, congelou tudo",
    ],
    "tela": [
        "a tela ficou branca",
        "não clica em nada",
        "ficou parado",
        "a tela não muda",
        "o cursor fica girando",
        "nada funciona na tela",
        "ficou branco e não faz nada",
    ],
},

"porta_ocupada": {
    "atua": [
        "porta em uso", "address already in use", "a 5000 tá presa",
        "port already bound", "EADDRINUSE", "porta 8080 ocupada",
        "porta já em uso", "bind failed",
    ],
    "aprende": [
        "diz que a porta já está sendo usada",
        "não sobe porque a porta tá ocupada",
        "a porta está ocupada", "não consigo subir na porta",
        "a porta 3000 está em uso", "a porta não está livre",
        "diz que alguém já está usando a porta",
        "não libera a porta", "a porta tá presa",
        "a porta continua ocupada", "diz que a porta ta em uso",
        "a prota ta ocupada", "diz que ja tem algo na porta",
        "a porta 5000 ta ocupdaa", "nao consigo usar a porta",
        "EADRINUSE", "addres already in use",
        "me ajuda a liberar a porta", "o que faço com a porta ocupada",
        "como libero uma porta em uso", "corrige o problema da porta ocupada",
        "preciso liberar a porta",
    ],
    "tela": [
        "diz que já tem alguma coisa usando",
        "apareceu uma mensagem de porta em uso",
        "diz que a porta está ocupada",
        "apareceu address already in use",
    ],
},

"permissao_negada": {
    "atua": [
        "access denied", "permission denied", "sem permissão", "unauthorized",
        "403", "forbidden", "EACCES", "EPERM",
        "acesso negado", "sem autorização",
    ],
    "aprende": [
        "não deixa salvar", "não tenho permissão pra isso",
        "não consigo gravar o arquivo", "diz que não tenho permissão",
        "não posso acessar isso", "está bloqueado",
        "não consigo escrever no arquivo", "diz que acesso negado",
        "não tenho direito de fazer isso", "está protegido",
        "diz que nao tenho permissao", "access deneid",
        "nao deixa gravar", "permition denied",
        "nao consigo salvar", "nao tenho prmissao",
        "diz acesso negdao", "nao consego acessar",
        "me ajuda com permissão negada", "como resolvo acesso negado",
        "corrige o problema de permissão", "o que faço com permission denied",
    ],
    "tela": [
        "fala que não tenho permissão",
        "aparece uma mensagem de acesso negado",
        "apareceu um aviso de permissão",
        "diz forbidden na tela",
        "apareceu 403",
    ],
},

"dependencia_faltando": {
    "atua": [
        "module not found", "não acha a dll", "falta um pacote",
        "unresolved reference", "package não instalado",
        "ModuleNotFoundError", "ImportError", "cannot find module",
        "missing dependency", "library not found",
    ],
    "aprende": [
        "falta instalar alguma coisa", "diz que não encontrou uma biblioteca",
        "não acha o módulo", "diz que falta uma dependência",
        "não encontra a lib", "falta algum pacote",
        "diz que não acha o import", "a dependência não está instalada",
        "o pacote não foi instalado", "falta uma lib",
        "modul not found", "canot find module",
        "falta instala alguma coisa", "diz q nao encontrou a lib",
        "nao acha o modulo", "librari not found",
        "diz que falta um pacote", "nao encontra a dependencia",
        "me ajuda a instalar a dependência", "corrige o erro de dependência",
        "por que não acha o módulo", "o que faço com a dependência faltando",
        "como instalo a biblioteca que falta", "me ajuda a resolver a falta da lib",
        "corrige o module not found",
    ],
    "tela": [
        "diz que não achou não sei o quê",
        "fala de um nome que eu não conheço",
        "apareceu um erro com nome de biblioteca que não conheço",
        "diz que não encontrou algo que não sei o que é",
    ],
},

"nao_conecta": {
    "atua": [
        "timeout", "não conecta no banco", "a API não responde",
        "connection refused", "deu 500", "deu 503",
        "ECONNREFUSED", "ETIMEDOUT", "connection reset",
        "não tem conexão", "host not found",
    ],
    "aprende": [
        "não está conectando", "não consegue acessar o banco de dados",
        "a API não está respondendo", "não consigo conectar",
        "o banco não responde", "não tem acesso ao servidor",
        "está dando timeout", "não consegue se conectar",
        "o endpoint não responde", "perdeu a conexão",
        "nao conecta", "deu tmeout", "conexao recusada",
        "conection refused", "a api nao respodne",
        "nao consigo conectar no banco", "o baco nao responde",
        "ta dando time out", "sem conecao", "nao tem conexao",
        "me ajuda com a conexão", "o que faço quando não conecta",
        "como resolvo o problema de conexão", "corrige o erro de conexão",
        "ajuda, não conecta", "por que não está conectando",
    ],
    "tela": [
        "fica rodandinho e não vem nada",
        "fica esperando e não carrega",
        "fica carregando infinito",
        "o círculo fica girando e não vem resposta",
        "fica no loading e não termina",
    ],
},

# ══════════════════════════════════════════════════════════
# MÁQUINA
# ══════════════════════════════════════════════════════════

"estado_da_maquina": {
    "atua": [
        "como tá a máquina", "diagnóstico geral", "status do sistema",
        "tá tudo ok aqui", "verifica a máquina", "health check",
        "system status", "como está o ambiente",
    ],
    "aprende": [
        "está tudo certo por aí", "dá uma olhada geral na máquina",
        "tem alguma coisa errada no computador", "a máquina tá bem",
        "me faz um diagnóstico", "tá tudo funcionando",
        "como está a máquina", "tem problema no ambiente",
        "tá tudo ok", "tem algo errado na máquina",
        "como ta a maquina", "ta tudo ok aqui",
        "tem algo erando no ambiente", "verifica a maquina pra mim",
        "diagnostico geral aqui", "como ta o sistema",
        "como está o sistema agora", "qual o estado atual da máquina",
        "me faz um diagnóstico da máquina", "me conta como tá o sistema",
        "faz um checkup na máquina", "o que você acha do estado atual",
        "como esta o sistema", "da uma olhada no sistema pra mim",
    ],
},

"ver_logs": {
    "atua": [
        "mostra o log", "cadê os logs", "tail do log", "o que deu no log",
        "abre o log", "log do sistema", "tail -f log.txt",
        "cat error.log", "journalctl", "event viewer",
    ],
    "aprende": [
        "onde vejo o que aconteceu", "tem algum arquivo que registra os erros",
        "quero ver os registros", "onde ficam os logs",
        "me mostra o arquivo de log", "quero ver o que foi registrado",
        "onde estão os logs de erro", "quero ver os erros registrados",
        "tem log disso", "me mostra o que foi logado",
        "onde esta o log", "mostra o log pra mim",
        "cade os logs", "onde ficam os lgs",
        "me mostra os registros", "onde vejo o log de erro",
        "tem algum log aqui", "log do sistema aqui",
    ],
},

"processos": {
    "atua": [
        "o que tá rodando", "lista os processos", "quem tá comendo CPU",
        "ps aux", "tasklist", "quem usa memória", "top", "htop",
        "task manager", "o que consome mais CPU",
    ],
    "aprende": [
        "quais programas estão abertos", "o que está usando a máquina",
        "tem muita coisa rodando", "o que está consumindo CPU",
        "quais processos estão rodando", "o que usa mais memória",
        "tem processo pesado rodando", "o que tá consumindo recurso",
        "o que está aberto", "quais serviços estão rodando",
        "o que ta rodando aqui", "quais pograms estao abertos",
        "o que consome CPU", "lista os procesoss",
        "o que usa memria", "ta consumindo muito",
        "quais processos estão rodando agora", "e agora, o que ocupa mais memória",
        "o que consumiu mais memória", "me mostra o que tá rodando agora",
        "quem está rodando agora", "listar os processos que estão abertos",
        "como vejo o que está rodando", "o que está pesado na máquina",
        "cara o que ta rodando agora", "quais processos estao rodando agora",
    ],
},

"espaco_em_disco": {
    "atua": [
        "tem espaço", "disco cheio", "quanto sobrou de disco",
        "df -h", "du", "quanto tem livre", "disk usage",
        "free space", "espaço em disco",
    ],
    "aprende": [
        "o computador está sem espaço", "quanto de memória sobrou no disco",
        "tem espaço suficiente", "vai ter espaço pra isso",
        "o disco está cheio", "não tem espaço no disco",
        "quanto tem livre no HD", "o armazenamento está cheio",
        "falta espaço no disco", "o SSD está cheio",
        "tem espaco no disco", "quanto sobrou de esapco",
        "disco cheo", "nao tem espaco",
        "quanto tem livre no dicsco", "falta espaco",
        "quanto espaço ainda tem no disco", "cara, quanto sobrou de espaço",
        "me diz quanto falta de espaço", "o disco tem espaço livre",
    ],
    "tela": [
        "apareceu um aviso de disco cheio",
        "apareceu uma notificação de armazenamento cheio",
        "diz que não tem espaço",
        "apareceu aviso de disco",
    ],
},

# ══════════════════════════════════════════════════════════
# VERSIONAMENTO
# ══════════════════════════════════════════════════════════

"git_estado": {
    "atua": [
        "git status", "o que mudou", "tem coisa não commitada",
        "status do git", "o que está pendente no git", "git st",
        "git status --short", "o que não foi commitado",
    ],
    "aprende": [
        "quais arquivos eu alterei", "o que eu mexi desde ontem",
        "tem alteração não salva no git", "o que mudou no projeto",
        "me mostra o que não foi commitado", "tem mudança pendente",
        "o que ainda não foi salvo no git", "tem algo pra commitar",
        "o que mudou desde o último commit", "quais arquivos foram alterados",
        "git stauts", "o que to mudou",
        "tem coisa pra commitar", "o que mudou no git",
        "me mostra o status do git", "o que ta pendente no git",
        "tem alteracao nao commitada", "o que nao foi commitado",
    ],
},

"git_historico": {
    "atua": [
        "git log", "últimos commits", "histórico",
        "log do git", "histórico de commits", "git log --oneline",
        "git log --graph", "quem commitou", "últimas mudanças",
    ],
    "aprende": [
        "o que foi feito nesse projeto", "quem mexeu por último",
        "me mostra os últimos commits", "histórico do que foi feito",
        "o que aconteceu no projeto", "quem alterou isso",
        "o que foi mudado recentemente", "me mostra o histórico",
        "o que foi commitado ultimamente", "quais foram os últimos commits",
        "git lgo", "histoico do git",
        "os ultimos commits", "me mostra o historico",
        "o que foi feito recentemente", "historico de mudancas",
        "quem fez os ultimos commits", "o que mudou ultimamente",
    ],
},

"git_diferenca": {
    "atua": [
        "git diff", "mostra o diff", "o que mudou nesse arquivo",
        "diff do git", "diferença entre versões", "quais linhas mudaram",
        "git diff HEAD", "compara versões",
    ],
    "aprende": [
        "quero ver o que eu alterei", "qual a diferença do que estava antes",
        "o que mudou desde o último commit", "me mostra o que eu mudei",
        "quero ver as mudanças", "qual a diferença entre as versões",
        "o que foi alterado nesse arquivo", "me mostra o diff",
        "o que mudou aqui exatamente", "quais linhas foram alteradas",
        "git dif", "mostra as mudancas",
        "o que mudou nesse arqiuvo", "me mostra o que eu mudei",
        "quero ver o dif", "qual diferença do que tava antes",
        "o que foi mudado aqui", "compara o que mudou",
    ],
},

"git_enviar": {
    "atua": [
        "push", "sobe pro github", "commita isso", "manda pro repositório",
        "git push", "git commit", "faz o commit e push",
        "git commit -m", "git push origin", "sobe o código",
    ],
    "aprende": [
        "quero salvar isso no github", "como eu envio as alterações",
        "quero commitar", "como mando pro github",
        "como salvo no repositório", "como faço o commit",
        "como envio o código pro git", "como subo pro repositório",
        "como faço push", "como commito o código",
        "git psuh", "commita isso aqui",
        "como mando pro repositorio", "sobe pro gith hub",
        "como faço o git push", "como faco commit",
        "manda pro repositório", "como subo o codigo",
        "como salvo no git", "faz o push aqui",
    ],
},

"git_desfazer": {
    "atua": [
        "desfaz", "reverte", "git checkout .", "descarta as mudanças",
        "git reset", "git revert", "volta o commit",
        "git stash", "git reset --hard", "desfaz o commit",
    ],
    "aprende": [
        "quero voltar como estava antes", "como eu desfaço o que fiz",
        "desfaz o que eu fiz", "como reverto as mudanças",
        "quero cancelar as alterações", "como volto ao estado anterior",
        "quero desfazer as mudanças", "como descarto as alterações",
        "como volto ao último commit", "quero cancelar o que fiz",
        "git reest", "desaz as mudancas",
        "como vouto o que fiz", "quero reverter",
        "como descarto as mudancas", "como cancelo as alteracoes",
        "volta pro que tava antes", "desfaz o que eu mexi",
    ],
},

# ══════════════════════════════════════════════════════════
# AMBIENTE
# ══════════════════════════════════════════════════════════

"abrir_no_editor": {
    "atua": [
        "abre no vs code", "manda pro visual studio", "code .", "abre no editor",
        "open in vscode", "code {arq}", "abre no vscode",
        "open with vscode", "editor aqui",
    ],
    "aprende": [
        "quero abrir isso no visual studio code",
        "pode abrir esse projeto no editor",
        "como abro no vscode", "me abre no editor",
        "abre no visual studio code", "quero ver no vscode",
        "como abro o projeto no vs code", "abre no ide",
        "como edito isso no vs code", "abre no editor de código",
        "abre no vscoe", "como abro no vs code",
        "abre no visual studio", "abri no vscode",
        "quero ver no editor", "abre no IDE",
        "como abro no vsocde", "manda pro vscode",
    ],
},

"versao_das_ferramentas": {
    "atua": [
        "qual versão do dotnet", "python --version", "que versão tá instalada",
        "node --version", "git --version", "pip --version",
        "java --version", "npm --version", "go version",
    ],
    "aprende": [
        "como eu sei qual versão eu tenho", "o que está instalado na máquina",
        "qual versão do python eu tenho", "tenho a versão certa instalada",
        "qual versão do node está instalada", "qual o dotnet instalado",
        "que versão do java tem aqui", "tem o node instalado",
        "qual a versão do npm", "que versão é essa que tá instalada",
        "que versao ta instalada", "qual versao do python",
        "que versao do node tenho", "tem o python instalado",
        "que versao do dotnet ta ai", "verifica as versoes instaladas",
        "que verrsao ta instalada", "qual versao ta aqui",
    ],
},

"variavel_de_ambiente": {
    "atua": [
        "falta uma variável de ambiente", "o PATH tá certo", "cadê o appsettings",
        "set a variável", ".env", "export a variável",
        "PYTHONPATH", "DATABASE_URL", "API_KEY",
        "configura a variável de ambiente",
    ],
    "aprende": [
        "onde eu ponho a chave", "onde configuro a conexão do banco",
        "como configuro as variáveis de ambiente",
        "onde fica o arquivo de configuração",
        "onde coloco as credenciais", "como configuro o ambiente",
        "onde fica o .env", "como defino as variáveis",
        "onde coloco a chave de API", "como configuro a conexão",
        "onde ponho as cofigurações", "como configuro o .env",
        "onde fica o arquivo de config", "como configuro as credenciais",
        "onde colco a chave de api", "como cofiguro as variaveis",
        "onde ponho a configuracao do banco", "cadê o arquivo de config",
        "onde fica o apisettings", "como seto a variavel de ambiente",
    ],
},

# ── revisar o que foi entendido ────────────────────────────────────
# Veio de uma conversa real: depois de um pedido de projeto pela
# metade, a pessoa pergunta "oque foi que vc entendeu?" e a rede dava
# `ver_logs`/`git_diferenca` — nada a ver. Conferir o entendido NÃO é
# uma ação de código: é checar o que o assistente capturou até agora.
"revisar_entendimento": {
    "atua": [],
    "aprende": [
        "o que voce entendeu do meu pedido",
        "oque foi que vc entendeu",
        "me mostra o que voce entendeu",
        "o que você entendeu",
        "o que foi que você entendeu do projeto",
        "me diz o que voce entendeu",
        "o que vc entendeu do que eu pedi",
        "resume o que vc entendeu",
        "me resume o pedido",
        "mostra o resumo do que entendi",
        "como voce esta entendendo meu pedido",
        "o que ficou entendido",
        "o que voce captou do projeto",
        "você entendeu o que eu pedi?",
        "me confirma o que voce entendeu",
        "revisa o que voce entendeu",
        "o que voce anotou do projeto",
        "o que registrou do pedido",
        "conta pra mim o que voce entendeu",
        "mostra o pedido como voce ta vendo",
    ],
    "tela": [],
},

}  # fim de FALAS


# ── buracos ──────────────────────────────────────────────────────────
# Os valores que preenchem os {placeholders} nas frases.
# Mantém as frases concretas sem escrever uma por nome de arquivo.

BURACOS = {
    # OS TRÊS DE BAIXO SÃO DO `consultar_dados`, E EXISTEM POR UM NÚMERO.
    #
    # Na primeira tentativa eu escrevi as frases com {nome} (Cliente,
    # Produto, Helper) e o classificador acertou 1 de 7 pedidos reais.
    # "quantas transações estão pendentes" ia para `git_diferenca`;
    # "agrupa os logs por severidade" ia para `ver_logs`, puxada pela
    # palavra "logs".
    #
    # As palavras-chave (soma, total, agrupa, linq) já eram exclusivas
    # desta intenção — o que faltava eram os SUBSTANTIVOS. A rede nunca
    # tinha visto "transações", "lançamentos" ou "faturas" no meio de uma
    # pergunta de consulta, e sem eles a frase não parecia nada.
    #
    # É o mesmo erro que este projeto já mediu uma vez: nove palavras do
    # exemplo real dele apareciam ZERO vezes no corpus.
    "dados": ["transações", "logs", "pedidos", "produtos", "clientes",
              "usuários", "vendas", "itens", "registros", "notas",
              "contas", "lançamentos", "movimentações", "chamados",
              "tarefas", "alunos", "funcionários", "faturas", "compras",
              "entregas", "transacoes", "pagamentos"],
    "campo": ["valor", "status", "data", "categoria", "tipo", "nome",
              "total", "preço", "quantidade", "severidade", "situação",
              "código", "descrição", "saldo", "taxa", "data hora",
              "cliente nome", "taxa processamento", "código erro"],
    "estado": ["concluídas", "pendentes", "canceladas", "ativas",
               "aprovadas", "pagas", "atrasadas", "abertas", "fechadas",
               "recusadas", "entregues", "críticos"],
    "proj": [
        "AdminApp", "ClientApp", "SO-Espacial", "Rede-Neural", "DevDesk",
        "AutonomousStore", "WebApi", "o da loja", "esse aqui", "meu projeto",
        "aluguel-carros", "MinhaApi", "Frontend", "Backend", "o projeto",
        "EcommerceApp", "StockApp", "TaskManager", "ChatApp",
    ],
    "arq": [
        "Program.cs", "appsettings.json", "index.html", "main.py", "README.md",
        "servidor.py", "app.py", "o csproj", "o log", "package.json",
        "requirements.txt", "Dockerfile", "docker-compose.yml", ".env",
        "config.py", "settings.py", "models.py", "views.py", "urls.py",
        "index.js", "App.tsx", "styles.css", "schema.sql",
    ],
    "termo": [
        "TODO", "conexão", "senha", "GetAll", "usuario", "erro",
        "login", "token", "database", "config", "password",
        "api_key", "secret", "endpoint", "repository", "service",
    ],
    "nome": [
        "Cliente", "Produto", "Servico", "Helper", "Teste",
        "Usuario", "Pedido", "Pagamento", "Relatorio", "Dashboard",
        "AuthController", "ProductService", "UserRepository",
    ],
    "pkg": [
        "numpy", "opencv", "EntityFramework", "requests", "pytest", "newtonsoft",
        "pandas", "matplotlib", "flask", "django", "fastapi", "sqlalchemy",
        "axios", "lodash", "moment", "express", "react", "vue",
        "AutoMapper", "Dapper", "MediatR", "Serilog",
    ],
}
