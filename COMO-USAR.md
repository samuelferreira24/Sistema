# Sistema Absoluto — como colocar no ar

Quatro arquivos, tudo o que existe:

- `index.html` — o app inteiro
- `manifest.json` — faz virar app instalável
- `sw.js` — faz abrir offline
- `icon-192.png` e `icon-512.png` — ícone

Nenhum deles precisa de instalação, compilação ou servidor especial.

---

## 1. Subir (pelo celular, sem PC)

1. Abra `github.com` no navegador e crie uma conta (se ainda não tiver)
2. Toque em **+** → **New repository**
3. Nome: `sistema` · marque **Public** · **Create repository**
4. Toque em **uploading an existing file** e envie os cinco arquivos
5. **Commit changes**
6. Vá em **Settings** → **Pages** → em *Branch* escolha `main` → **Save**

Em um ou dois minutos o endereço aparece na mesma página:
`https://SEU-USUARIO.github.io/sistema/`

Precisa ser HTTPS para instalar como app — o GitHub Pages já entrega assim.

---

## 2. Instalar na tela inicial

- **Android (Chrome):** abra o endereço → menu ⋮ → *Adicionar à tela inicial*
- **iPhone (Safari):** abra o endereço → botão compartilhar → *Adicionar à Tela de Início*

O ícone aparece junto dos outros apps. Abre em tela cheia, sem barra de navegador.

---

## 3. Ligar o motor

Primeira vez que abrir: aba **Motor** → escolha o fornecedor → cole a chave → **Testar conexão**.

Onde pegar a chave, todos sem cartão de crédito:

| Fornecedor | Onde |
|---|---|
| Google Gemini | aistudio.google.com → Get API key |
| Groq | console.groq.com → API Keys |
| OpenRouter | openrouter.ai → Keys |

A chave fica salva só no seu aparelho, dentro do app. Trocar de fornecedor depois não afeta a memória — o motor é peça substituível, a memória é o que é seu.

---

## 4. Cópia de segurança

Aba **Memória** → **Exportar memória** gera um arquivo `.json`. Guarde de vez em quando.

Se trocar de celular, ou se algo quebrar, **Importar memória** traz tudo de volta — decisões aprovadas, blocos e histórico.

A memória vive neste aparelho. Sincronização entre dispositivos é a próxima versão.

---

## O que roda offline

Abre e funciona sem internet: a memória inteira, os blocos, o histórico de decisões.

Precisa de internet: só o motor (a resposta em si), porque o cérebro ainda é alugado por API. Quando você tiver o modelo local no PC, nem isso.
