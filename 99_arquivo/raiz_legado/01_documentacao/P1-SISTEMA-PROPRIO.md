# P1 — Sistema Próprio

O item 21 do arquivo diz que a restrição única é não existir sistema próprio rodando
sozinho. O P1 bloqueia todo o resto. Este é o caminho para destravar, na ordem em que
uma coisa libera a outra.

---

## Onde está o problema

O app é a cabine. Ele tem memória, método e ferramentas, mas só funciona quando você
abre. O Sistema Próprio é a casa de máquinas: o que roda quando você não está olhando.

Hoje o motor do app é alugado. Motor emprestado tem o limite de quem empresta — é o
diagnóstico do item 29. Enquanto for assim, "IA que antecipa" e "Fábrica autônoma"
seguem sendo descrição, não fato.

---

## A ordem que destrava

| Passo | O que faz | Custo | Destrava |
|---|---|---|---|
| **1. Motor no celular** | llama.cpp + modelo rodando no Termux | zero | app responde sem internet e sem token |
| **2. Validar** | ver o modelo respondendo no hardware real | zero | prova que o caminho existe antes de gastar |
| **3. VPS** | mesma stack, mas ligada 24 horas | R$38–180/mês | o sistema roda sem o celular ligado |
| **4. n8n + Filtro** | orquestrador com o item 6 virado regra | incluso | deixa de ser "n8n instalado" e vira Sistema Próprio |
| **5. MCP** | módulos emprestados plugados com prazo | zero | ferramenta externa vira peça trocável |
| **6. Migrar os apps** | App Pessoal e Cliente viram workflows | zero | a cabine passa a pilotar a casa de máquinas |

Os dois primeiros passos custam zero e resolvem hoje. Os outros só fazem sentido
depois que o primeiro provar que funciona no seu aparelho — item 19: testar, quebrar,
corrigir rápido.

---

## Passo 1 e 2, agora

**Instalar o Termux.** Do F-Droid ou do GitHub, nunca da Play Store — a versão da loja
foi abandonada e quebra na compilação.

**Rodar o instalador.** No Termux:

```
pkg install wget -y
wget SEU-ENDERECO/motor.sh
bash motor.sh
```

Ou cole o conteúdo do `motor.sh` num arquivo e rode `bash motor.sh`.

O que ele faz sozinho: mede sua memória e espaço, instala o compilador, detecta se a
GPU do aparelho serve, compila o llama.cpp, escolhe o modelo do tamanho certo pra sua
RAM, baixa, e cria os atalhos.

Leva de 10 a 30 minutos na compilação. Use Wi-Fi. Deixe a tela ligada.

**Ligar:**

```
motor
```

**Testar, em outra aba do Termux:**

```
motor-teste
```

**Conectar no app:** Ajustes → Motor local

```
endereço: http://127.0.0.1:8080/v1/chat/completions
modelo:   local
```

Toque em Testar. Quando aparecer "motor local respondendo", o item 25 deixou de ser
tese e virou fato no seu aparelho.

---

## O que muda no mesmo instante

O app já sabe usar isso desde a versão passada. Com o motor local ligado:

- Sem internet, ele troca sozinho para o motor local — não fica esperando
- Perguntas feitas offline entram na fila e rodam quando o motor volta
- Imagem funciona offline, se o modelo tiver visão
- Nenhum token, nenhuma conta, nenhum terceiro no caminho

---

## O que o modelo pequeno faz bem, e o que não faz

Modelo de 1 a 3 bilhões de parâmetros dá conta de resumir, classificar, extrair dado
estruturado e conversa comum. É exatamente o que a maior parte do app pede.

Ele erra mais o formato JSON das 5 Camadas que o motor remoto. O app já aceita resposta
fora do formato em vez de quebrar, mas a diferença é real e você vai notar.

O caminho não é escolher um: é ter os dois. Remoto quando há internet e a decisão é
pesada. Local quando não há, ou quando a resposta não precisa ser brilhante.

---

## Passo 3 em diante, quando o primeiro provar

O celular não fica ligado 24 horas rodando modelo — esquenta, gasta bateria, e você
precisa do aparelho. Por isso a VPS existe: mesma coisa, sempre de pé.

Mas ela custa dinheiro todo mês, e o item 6.4 pergunta se isso alimenta o caixa ou
consome sem retorno mapeado. Hoje não há cliente pagando. Subir VPS antes do primeiro
caixa é gasto fixo contra receita zero.

A ordem que respeita seu próprio método: motor no celular agora (zero), primeiro
cliente pago, VPS paga pelo caixa que ela ajuda a gerar.

---

## O que ainda falta para ser Sistema Próprio de verdade

O motor local resolve 32.1 e 32.2. Não resolve o resto.

Falta o orquestrador — algo que decide qual ferramenta chamar e quando, seguindo o
Filtro de Calibragem como regra executável, não como lembrete de conversa. É o item
32.4, e é ele que separa "tenho as peças" de "o sistema roda sozinho".

Isso não dá pra fazer só no celular. Precisa de máquina ligada sempre. Então continua
sendo passo 3 em diante — depois do caixa, não antes.
