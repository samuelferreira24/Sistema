# Do web ao nativo — sem PC

O app nativo **carrega o mesmo `index.html`**. Nada é reescrito. O envelope nativo
empilha por cima do que já existe, e as duas versões seguem vivas ao mesmo tempo.

---

## O que muda

| | Web instalado (hoje) | Nativo (com o envelope) |
|---|---|---|
| Código | o mesmo | o mesmo |
| Armazenamento | cota do navegador, pode ser descartada | limite é o disco, nunca descartado |
| Atualizar | publica e já está no ar | precisa gerar APK novo |
| Rodar em segundo plano | não | sim, com plugin |
| Notificação | limitada no iPhone | completa no Android |
| Compartilhar arquivo | download | folha nativa do sistema |
| Biometria pra abrir | não | sim, com plugin |
| Play Store | não | sim |

**A jogada:** manter os dois. O web continua sendo onde você testa e publica em segundos.
O nativo é a versão sólida, com armazenamento sem teto. Mesmo código, dois destinos.

---

## Os quatro arquivos

Suba pro mesmo repositório, junto do `index.html`:

- `package.json` — as dependências
- `capacitor.config.json` — a configuração do app
- `.github/workflows/build-android.yml` — quem compila
- este guia

O `index.html` já sabe quando está rodando nativo: o selo no topo mostra "nativo",
o painel de armazenamento muda, e exportar passa a usar a folha de compartilhamento
do sistema em vez de baixar arquivo.

---

## Compilar, pelo celular

1. Suba os arquivos no repositório (mesmo lugar do app)
2. Abra a aba **Actions**
3. Escolha **Montar APK** na lista da esquerda
4. Toque em **Run workflow** → **Run workflow**
5. Espere entre cinco e dez minutos
6. Abra a execução → role até **Artifacts** → baixe `sistema-absoluto-apk`
7. Descompacte e instale o `.apk`

O Android vai pedir permissão pra instalar de fonte desconhecida. É esperado — o app
é seu, não veio de loja.

Da segunda vez em diante, cada mudança no `index.html` dispara a compilação sozinha.

---

## O que ainda não está ligado

O `package.json` já traz três plugins, mas eles só entram em ação quando você pedir:

- **Filesystem** — já usado na exportação; pode virar armazenamento sem limite nenhum
- **Share** — já usado; pode receber arquivo de outros apps direto no seu
- **Preferences** — guarda chave de API no cofre do sistema, mais seguro que o navegador

---

## As camadas do Android, por valor real

Existe uma escada de integração no Android. Cada degrau dá mais acesso e custa mais
trabalho. A ordem abaixo não é por poder — é por **quanto cada um resolve do seu
gargalo real hoje**, que é fechar o primeiro cliente.

| Camada | O que destrava pra você | Custo | Vale agora? |
|---|---|---|---|
| **Leitor de notificação** | a IA lê o WhatsApp do cliente e responde — isto **é** a automação de clínica | plugin Kotlin, permissão manual | **o de maior valor** |
| **Segundo plano nativo** | o orquestrador roda sem depender do Termux | plugin, mínimo de 15 min entre execuções | alto, depois do primeiro |
| **Bolha flutuante** | a IA acessível de qualquer tela, sobre qualquer app | plugin, permissão de sobreposição | médio — conforto, não receita |
| **Receber compartilhamento** | manda a planilha de outro app direto pro seu | plugin pequeno | médio |
| **Assistente padrão** | chamada por gesto, como o Assistente do Google | complexo, Samsung e Xiaomi restringem | baixo |
| **Palavra de ativação** | "Ok, Sistema" sem tocar na tela | Porcupine, funciona offline | baixo |
| **Acessibilidade** | a IA lê e clica em qualquer app | permissão perigosa, Play Store exige justificativa | só com uso claro |
| **App de sistema** | permissões elevadas automáticas | exige root ou ROM própria | não |
| **ROM própria (a IA É o Android)** | controle total do aparelho | anos, equipe, bootloader aberto | não |

Nenhuma delas existe pronta — todas exigem escrever um plugin em Kotlin. Faz sentido
depois que o APK estiver rodando e o caminho nativo tiver se pago.

---

## O que a última camada NÃO resolve

Isso é o mais importante da escada, e é fácil errar.

Estar no nível mais alto muda o **acesso** da IA, não a **inteligência** dela. Uma IA
dona do sistema inteiro continua raciocinando exatamente igual — quem decide isso é o
modelo, não a posição no Android.

E não dá superpoder de compilação: mesmo dona do sistema, ela não ganha compilador.
Gerar um `.apk` continua exigindo SDK e Gradle, que rodam num PC ou na nuvem.

É a sua própria regra: o carro melhora em eficiência, design e potência, mas não vira
foguete trocando de garagem. Trocar de camada no Android é trocar de garagem.

Onde a inteligência melhora de verdade: modelo maior, mais contexto, memória melhor
calibrada. Nada disso depende de permissão do Android.

---

## Por que a aplicação web já está certa

App nativo precisa compilar, assinar e instalar. App web é texto que o navegador
interpreta — a IA gera e roda na hora, sem nada disso.

É por isso que a Oficina funciona: você pede a ferramenta, ela nasce funcionando na
tela, você aprova, e ela fica guardada. Sem loja, sem build, sem espera.

O envelope nativo não substitui isso. Ele **soma** acesso ao aparelho por baixo, mantendo
a velocidade de criação por cima.

---

## iPhone

O Android compila na nuvem porque o Linux do GitHub dá conta. O iPhone exige um Mac
para compilar — não tem volta por software. As saídas reais:

1. **Ficar no web instalado** — funciona hoje, sem custo, quase tudo igual
2. **Mac na nuvem** (Codemagic, Ionic Appflow) — free tier existe, mais exige conta de
   desenvolvedor da Apple paga por ano
3. **Um Mac emprestado por algumas horas** — só pra gerar, depois instala e pronto

Enquanto o caixa não justificar, o web instalado no iPhone resolve.

---

## Play Store, depois

O APK acima é de teste (debug): serve pra instalar nos seus aparelhos, não pra loja.
Pra publicar precisa de assinatura — uma chave que prova que o app é seu.

Quando chegar a hora: gera a chave, guarda como segredo no GitHub, troca
`assembleDebug` por `bundleRelease` no workflow. Cinco linhas a mais.

Antes disso não faz sentido: loja serve pra estranho achar seu app, e este app é seu.
