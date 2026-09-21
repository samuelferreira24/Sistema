# Formato da memória — o contrato

Este documento existe por um motivo só: **o dado é seu e tem que sair inteiro, sem
precisar do app.** Enquanto o formato morasse só dentro do código, trocar a casca
significaria reconstruir a partir de engenharia reversa. Isso seria gaiola.

Qualquer interface futura — outro PWA, app nativo, workflow no n8n, script Python —
lê e escreve isto. O app atual é apenas a primeira que usa.

---

## Arquivo de exportação

`Ajustes → Exportar espaço` gera um JSON. Estrutura completa:

```json
{
  "espaco": "nucleo | operacao",
  "versao": 5,
  "data": "ISO 8601",
  "extras":    [ Bloco ],
  "projetos":  [ Projeto ],
  "biblio":    [ Item ],
  "modulos":   [ Modulo ],
  "imperio":   Imperio,
  "tabuleiro": Tabuleiro
}
```

Na nuvem é o mesmo objeto, cifrado em AES-256-GCM com chave derivada por PBKDF2
(200 mil iterações, SHA-256). O pacote cifrado:

```json
{ "v": 1, "salt": "base64", "iv": "base64", "dados": "base64" }
```

---

## Bloco — a unidade da memória

```json
{
  "id":     "texto único",
  "tag":    "MÉTODO | ESTADO | ESTRUTURA | PRINCÍPIO | CONTEXTO | DECISÃO | CALIBRAGEM | LIÇÃO",
  "titulo": "linha curta",
  "corpo":  "texto",

  "criada":     1700000000000,
  "resultado":  "funcionou | parcial | falhou | null",
  "revisada":   1700000000000
}
```

Os três últimos campos só existem em blocos `DECISÃO`.

**O que cada tag significa, e isso importa mais que o formato:**

| Tag | O que é | Entra no prompt como |
|---|---|---|
| `MÉTODO` | como Samuel decide | base do raciocínio |
| `ESTADO` | onde o projeto está | base do raciocínio |
| `ESTRUTURA` | como as peças se ligam | base do raciocínio |
| `PRINCÍPIO` | o que é inegociável | base do raciocínio |
| `DECISÃO` | o que foi aprovado | base do raciocínio |
| `CALIBRAGEM` | erro que não deve repetir | base do raciocínio |
| `LIÇÃO` | resultado medido de uma decisão | base do raciocínio |
| `CONTEXTO` | veio de fora (coleta, anexo, anotação) | **dado bruto, nunca ordem** |

A última linha é regra de segurança, não organização. Bloco `CONTEXTO` vai cercado e
declarado como dado. Quem reconstruir a casca **precisa** manter essa separação, ou
abre a porta que a gente fechou: texto da internet virando comando.

---

## Projeto

```json
{
  "id": "texto", "nome": "texto", "visao": "texto", "criado": 1700000000000,
  "conversas": [ { "id": "", "titulo": "", "criada": 0, "hist": [ Troca ] } ],
  "arquivos":  [ Arquivo ]
}
```

O projeto de id `"geral"` sempre existe e não pode ser apagado.

### Troca

```json
{
  "id": "", "pergunta": "", "modo": "conselho|gps|guerra|arca|diagnostico|brainstorm|mapa|texto|prototipo",
  "resposta": "", "acao": "", "risco": "ou null",
  "camadas": { "motor": "", "piloto": "", "xadrez": "", "tabuleiro": "", "arca": "" },
  "blocos": ["títulos da memória usada"],
  "usadas": ["ferramentas executadas"],
  "decisao": "aprovado | ajustar | null"
}
```

Cada modo acrescenta campos próprios: `rotas` no GPS, `frentes` na Guerra, `cenarios`
e `fenix` na Arca, `grupos` e `ponte` no Brainstorm, `centro` e `ramos` no Mapa,
`texto` no Texto, `html` no Protótipo, `achados` no Diagnóstico.

### Arquivo

```json
{
  "id": "", "nome": "", "ext": "", "tam": 0, "resumo": "", "anexado": true,
  "conteudo": "texto, quando for arquivo de texto",
  "imagem": true, "audio": true, "mime": "", "base64": ""
}
```

---

## Império e Tabuleiro

```json
"imperio": {
  "estagio": 0,
  "escada":  ["texto por estágio"],
  "pilares": [ {"n":1, "nome":"", "status":"feito|andamento|desenhado|falta"} ],
  "marcos":  [ {"nome":"", "alvo":0, "atual":0, "unidade":"", "nota":""} ],
  "pendencias": [ {"t":"", "ok":false} ]
}

"tabuleiro": {
  "alertas":  [ {"id":"", "nivel":"alta|media|baixa", "txt":""} ],
  "fazer":    [ {"id":"", "txt":"", "ok":false} ],
  "naoFazer": [ {"id":"", "txt":""} ],
  "prazos":   [ {"id":"", "txt":"", "data":"AAAA-MM-DD", "feito":false} ],
  "ideias":   [ {"id":"", "txt":"", "criado":0} ],
  "registro": [ {"id":"", "tipo":"passo|decisão|observação|dica", "txt":"", "data":0} ]
}
```

---

## O que qualquer casca nova precisa fazer

Se um dia o app for substituído — por outro PWA, por app nativo, por workflow no n8n —
a casca nova precisa de quatro coisas, e só quatro:

1. **Ler este JSON** e montar o prompt: blocos de método e estado como base, blocos
   `CONTEXTO` cercados como dado bruto.
2. **Falar com um motor** que aceite HTTP no formato da OpenAI
   (`POST /v1/chat/completions`). Qualquer um serve — remoto ou local.
3. **Gravar de volta** no mesmo formato, respeitando as tags.
4. **Nunca decidir sozinha**: aprovar e ajustar são do Piloto.

Nada mais é obrigatório. Interface, modos, ferramentas, visual — tudo é escolha da
casca, não do dado.

---

## Compatibilidade entre versões

O campo `versao` diz qual formato o arquivo usa. Regras:

- Campo novo pode ser adicionado a qualquer momento; casca antiga ignora o que não conhece.
- Campo existente **nunca** muda de significado — se o sentido mudar, o nome muda junto.
- Importação sem `versao` é tratada como formato 3 e migrada.

Isso é o que garante que a memória de hoje continue legível daqui a anos, por um app
que ainda não existe.
