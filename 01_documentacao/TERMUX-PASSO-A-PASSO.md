# TERMUX — passo a passo, do zero

Você nunca mexeu no Termux. Faça um passo por vez e confira a saída antes de ir pro
próximo. Se algum passo der erro, pare nele — não adianta seguir.

---

## PARTE 1 — Instalar (uma vez só)

**1.1** Instale o Termux pela **F-Droid**, não pela Play Store.
A versão da Play Store está abandonada e vai falhar nos passos seguintes.

- Abra `f-droid.org` no navegador → baixe o F-Droid → instale
- No F-Droid, procure e instale: **Termux**, **Termux:API** e **Termux:Boot**

**1.2** Abra o Termux. Vai aparecer uma tela preta com `$`. Digite:

```
pkg update -y && pkg upgrade -y
```

Se perguntar algo, aperte Enter. Demora alguns minutos.

**1.3** Instale o que o sistema usa:

```
pkg install -y python git curl termux-api
```

**1.4** Dê acesso à pasta de Downloads:

```
termux-setup-storage
```

O Android vai pedir permissão. Aceite.

---

## PARTE 2 — Colocar seus arquivos no lugar

**2.1** Baixe o `sistema-absoluto.zip` (o do chat) no celular. Ele cai em Downloads.

**2.2** No Termux:

```
mkdir -p ~/sa && cd ~/sa
unzip -o ~/storage/downloads/sistema-absoluto.zip
ls
```

Deve listar `ponte.py`, `coletor.py`, `orquestrador.py`, `index.html` e outros.
**Se não listar, pare aqui** — o zip não chegou.

---

## PARTE 3 — Ligar a Ponte

**3.1** Pegue o token:

```
cd ~/sa && python ponte.py --token
```

Vai imprimir uma linha embaralhada. **Copie ela** (segure o dedo → Copiar).

**3.2** Ligue a Ponte:

```
termux-wake-lock
python ~/sa/ponte.py &
```

Deve aparecer `PONTE ligada em http://127.0.0.1:8099`.

**3.3** Confira que respondeu:

```
curl -s http://127.0.0.1:8099/saude
```

Esperado: `{"ok": true, "servico": "ponte", "versao": 1}`

**3.4** No app: **Ajustes → Termux** → cole o token → **Salvar e conectar**.
Deve dizer "conectada · N comandos disponíveis".

A partir daqui você roda coletor e motor pelo app. Não precisa mais abrir o Termux.

---

## PARTE 4 — Fazer tudo subir sozinho (o passo que falta)

Sem isto, cada reinício do celular exige repetir a Parte 3 na mão.

**4.1** Crie a pasta que o Termux:Boot lê e ponha o arranque nela:

```
mkdir -p ~/.termux/boot
cp ~/sa/arranque.sh ~/.termux/boot/
chmod +x ~/.termux/boot/arranque.sh ~/sa/arranque.sh ~/sa/rodar-coleta.sh
```

**4.2** Teste agora, sem reiniciar:

```
bash ~/sa/arranque.sh
```

Esperado:
```
trava de sono ligada
Ponte no ar em 127.0.0.1:8099
motor deixado desligado — o piloto sobe quando precisar
coleta agendada a cada 3h
arranque concluído
```

**4.3** Abra o app **Termux:Boot** uma vez. Só abrir já registra.

**4.4** Android → Configurações → Apps → Termux → Bateria → **Sem restrição**.
Sem isso o Android mata o processo com a tela apagada e nada disso funciona.

**4.5** Reinicie o celular e confira que voltou sozinho:

```
curl -s http://127.0.0.1:8099/saude
tail -5 ~/sa/arranque.log
```

---

## PARTE 5 — Quem faz o quê, das 24h

Você não aperta nada. A divisão é esta:

| Quem | O que faz | Quando |
|---|---|---|
| Termux:Boot | sobe a Ponte e a trava de sono | ao ligar o celular |
| Agendador do Android | coleta + baixa artigos inteiros | a cada 3h, tela apagada |
| Piloto do app | análise, dicionário, gravação, liga/desliga o motor | a cada 5 min, checando o que está atrasado |
| Você | decide o que o plantão marcou como seu | quando quiser |

O motor **não** sobe no boot de propósito: ele consome bateria. O piloto liga
quando a análise precisa e desliga 10 minutos depois de ociosa.

Para acompanhar sem abrir o Termux: **Ajustes → Piloto automático** mostra o que
já rodou, o que falta e o diário de bordo.

---

## Comandos do dia a dia

| Para quê | Comando |
|---|---|
| Ver se está tudo de pé | `bash ~/sa/arranque.sh` |
| Ver o que aconteceu no boot | `tail -20 ~/sa/arranque.log` |
| Ver o log da coleta | `tail -30 ~/sa/coleta.log` |
| Ver o token de novo | `python ~/sa/ponte.py --token` |
| Parar tudo | `pkill -f ponte.py && termux-wake-unlock` |
| Ver agendamentos | `termux-job-scheduler --pending` |

---

## Se der errado

**"command not found"** → faltou a Parte 1.3.

**A Ponte cai sozinha** → falta `termux-wake-lock` ou a bateria do Termux está
restrita (Parte 4.4).

**O app diz "não achei a Ponte"** → se o app estiver aberto pelo Chrome em
`https://`, o navegador bloqueia chamada a `127.0.0.1`. Isso some no APK.

**`termux-job-scheduler: not found`** → falta o app **Termux:API** pela F-Droid;
o pacote `termux-api` sozinho não basta.

**Nada é analisado** → o analista precisa do motor. Ajustes → Motor → Testar.
