#!/data/data/com.termux/files/usr/bin/python
# ═══════════════════════════════════════════════════════════════
# PONTE — o Termux vira serviço do app, não uma tela pra abrir
#
# O motor local já usava esse padrão: llama-server escuta em
# 127.0.0.1:8080 e o app conversa com ele por HTTP, sem ninguém
# abrir o Termux. A Ponte faz o mesmo com o RESTO do Termux —
# coletor, orquestrador, arquivos e comandos liberados.
#
# Uso:
#     python ponte.py            sobe na porta 8099
#     python ponte.py --token    só mostra o token e sai
#
# Segurança, em ordem de importância:
#   1. Escuta SÓ em 127.0.0.1 — nada fora do aparelho alcança.
#   2. Exige token. Sem isso, QUALQUER app instalado no celular
#      poderia chamar localhost e mandar no seu Termux.
#   3. Comando não é texto livre: só o que está em PERMITIDOS roda.
# ═══════════════════════════════════════════════════════════════

import json
import os
import re
import secrets
import subprocess
import urllib.request
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTA = 8099
CASA = os.path.expanduser("~")
SA = os.path.join(CASA, "sa")
BIBLIOTECA = os.path.join(CASA, "biblioteca")
ARQ_TOKEN = os.path.join(CASA, ".sa-ponte-token")
# Disco de verdade do aparelho. O IndexedDB do navegador some se alguém
# limpar os dados do Chrome; isto aqui não.
MEMORIA = os.path.join(CASA, "sa-memoria")
# Downloads é visível pelo gerenciador de arquivos: dá pra copiar pro PC,
# mandar por e-mail, subir na nuvem. É a saída de emergência.
ESPELHO = os.path.join(CASA, "storage", "downloads", "sistema-absoluto-memoria")


def token():
    """Gera uma vez e reusa. O app guarda o mesmo valor e manda em toda chamada."""
    if os.path.exists(ARQ_TOKEN):
        t = open(ARQ_TOKEN).read().strip()
        if t:
            return t
    t = secrets.token_urlsafe(24)
    with open(ARQ_TOKEN, "w") as f:
        f.write(t)
    os.chmod(ARQ_TOKEN, 0o600)
    return t


TOKEN = token()

# Lista fechada. Texto livre viraria execução remota de comando —
# mesmo em localhost, com outro app malicioso instalado, seria grave.
PERMITIDOS = {
    "coletar":     [sys.executable, os.path.join(SA, "coletor.py")],
    "status":      [sys.executable, os.path.join(SA, "coletor.py"), "--status"],
    "orquestrar":  [sys.executable, os.path.join(SA, "orquestrador.py")],
    "exportar":    [sys.executable, os.path.join(SA, "coletor.py"), "--exportar"],
    "dicionario":  [sys.executable, os.path.join(SA, "coletor.py"), "--dicionario"],
    "completar":   [sys.executable, os.path.join(SA, "coletor.py"), "--completar"],
    "espaco":      ["df", "-h", CASA],
    "motor_vivo":  ["curl", "-s", "-m", "3", "http://127.0.0.1:8080/health"],
    # O motor é pesado: sobe só quando pedido e desce quando não serve mais.
    # Ligar/desligar daqui não encosta no coletor nem no orquestrador —
    # são processos separados, o sistema continua trabalhando sozinho.
    "motor_ligar":    ["bash", os.path.join(CASA, "motor", "ligar-motor.sh")],
    "motor_desligar": ["pkill", "-f", "llama-server"],
}

# Estado das tarefas longas: o app dispara e depois pergunta como foi,
# em vez de ficar esperando a coleta inteira numa requisição só.
tarefas = {}


def rodar_tarefa(nome, chave):
    tarefas[chave] = {"estado": "rodando", "inicio": time.time(), "saida": ""}
    try:
        p = subprocess.run(PERMITIDOS[nome], capture_output=True, text=True, timeout=1800)
        tarefas[chave].update({
            "estado": "pronto" if p.returncode == 0 else "erro",
            "codigo": p.returncode,
            "saida": (p.stdout or "")[-4000:],
            "erro": (p.stderr or "")[-2000:],
        })
    except subprocess.TimeoutExpired:
        tarefas[chave].update({"estado": "erro", "erro": "passou de 30 min"})
    except Exception as e:
        tarefas[chave].update({"estado": "erro", "erro": str(e)})
    tarefas[chave]["fim"] = time.time()



def extrair_texto(html):
    """Tira o texto legível de uma página. Sem biblioteca externa: o Termux
    não deve depender de instalação extra pra uma coisa dessas."""
    # fora o que nunca é conteúdo
    html = re.sub(r"(?is)<(script|style|nav|header|footer|aside|form|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    # parágrafo e quebra viram quebra de verdade, senão tudo cola
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>", "\n\n", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", html)
    # entidades mais comuns
    for a, b in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&mdash;", "—"), ("&ndash;", "–"),
                 ("&rsquo;", "'"), ("&ldquo;", '"'), ("&rdquo;", '"'), ("&hellip;", "…")]:
        txt = txt.replace(a, b)
    txt = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), txt)
    # linha curta demais quase sempre é menu, botão ou rodapé
    linhas = []
    for ln in txt.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if len(ln) >= 40 or (ln and len(ln) < 40 and len(linhas) and len(linhas[-1]) >= 40):
            linhas.append(ln)
    fora = "\n".join(linhas)
    fora = re.sub(r"\n{3,}", "\n\n", fora).strip()
    return fora[:60000]



def guardar_memoria(nome, dados):
    """Cada gravação vira um arquivo com data. Nunca sobrescreve o anterior:
    se um dia o app gravar lixo, as versões boas continuam lá."""
    os.makedirs(MEMORIA, exist_ok=True)
    carimbo = time.strftime("%Y%m%d-%H%M%S")
    seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", nome)[:60]
    caminho = os.path.join(MEMORIA, "%s-%s.json" % (seguro, carimbo))
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(dados)

    # "mais recente" é um atalho fixo pro app achar sem procurar
    atalho = os.path.join(MEMORIA, "%s-atual.json" % seguro)
    with open(atalho, "w", encoding="utf-8") as f:
        f.write(dados)

    # espelho em Downloads, alcançável fora do Termux
    try:
        os.makedirs(ESPELHO, exist_ok=True)
        with open(os.path.join(ESPELHO, "%s-atual.json" % seguro), "w",
                  encoding="utf-8") as f:
            f.write(dados)
    except Exception:
        pass   # sem permissão de storage não é motivo pra falhar a gravação

    # guarda as 20 últimas de cada nome; o resto sai
    versoes = sorted(g for g in os.listdir(MEMORIA)
                     if g.startswith(seguro + "-") and not g.endswith("-atual.json"))
    for velho in versoes[:-20]:
        try:
            os.remove(os.path.join(MEMORIA, velho))
        except Exception:
            pass
    return caminho, len(versoes)


def listar_memoria():
    if not os.path.isdir(MEMORIA):
        return []
    fora = []
    for g in sorted(os.listdir(MEMORIA), reverse=True):
        if not g.endswith(".json"):
            continue
        c = os.path.join(MEMORIA, g)
        fora.append({"arquivo": g, "bytes": os.path.getsize(c),
                     "quando": time.strftime("%d/%m/%Y %H:%M",
                                             time.localtime(os.path.getmtime(c)))})
    return fora


class Ponte(BaseHTTPRequestHandler):

    def log_message(self, *a):
        pass  # sem poluir o terminal

    def responder(self, codigo, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        # O app roda em outra origem (arquivo local, localhost ou GitHub Pages)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        # O Chrome bloqueia página https chamando 127.0.0.1 (Private Network
        # Access) a menos que o próprio servidor local autorize. Sem esta
        # linha, o app hospedado no GitHub Pages nunca acha a Ponte.
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()
        self.wfile.write(corpo)

    def autorizado(self):
        return self.headers.get("X-Token", "") == TOKEN

    def do_OPTIONS(self):
        self.responder(200, {"ok": True})

    def do_GET(self):
        rota = self.path.split("?")[0]

        # /saude responde sem token: o app usa pra saber se a Ponte existe
        if rota == "/saude":
            return self.responder(200, {"ok": True, "servico": "ponte", "versao": 1})

        if not self.autorizado():
            return self.responder(401, {"erro": "token inválido"})

        if rota == "/tarefas":
            return self.responder(200, {"tarefas": tarefas})

        if rota == "/biblioteca":
            alvo = os.path.join(BIBLIOTECA, "biblioteca-para-o-app.json")
            if not os.path.exists(alvo):
                return self.responder(404, {"erro": "ainda não existe; rode coletar/exportar"})
            with open(alvo, encoding="utf-8") as f:
                return self.responder(200, {"biblioteca": json.load(f)})

        if rota == "/dicionario":
            alvo = os.path.join(BIBLIOTECA, "dicionario.json")
            if not os.path.exists(alvo):
                return self.responder(404, {"erro": "ainda não montado; rode o comando dicionario"})
            with open(alvo, encoding="utf-8") as f:
                return self.responder(200, json.load(f))

        if rota == "/memoria":
            import urllib.parse as _up
            q = _up.parse_qs(self.path.split("?")[1] if "?" in self.path else "")
            nome = (q.get("nome") or ["memoria"])[0]
            seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", nome)[:60]
            alvo = os.path.join(MEMORIA, "%s-atual.json" % seguro)
            if not os.path.exists(alvo):
                return self.responder(404, {"erro": "nada guardado com esse nome ainda"})
            with open(alvo, encoding="utf-8") as f:
                return self.responder(200, {"nome": nome, "dados": f.read()})

        if rota == "/plantao":
            # O orquestrador grava o que descobriu enquanto ninguém olhava.
            # Sem esta rota, o analista trabalha e ninguém lê o relatório.
            alvo = os.path.join(SA, "plantao.json")
            if not os.path.exists(alvo):
                return self.responder(404, {"erro": "o orquestrador ainda não rodou"})
            with open(alvo, encoding="utf-8") as f:
                return self.responder(200, json.load(f))

        if rota == "/memorias":
            return self.responder(200, {"versoes": listar_memoria(), "pasta": MEMORIA,
                                        "espelho": ESPELHO})

        if rota == "/comandos":
            return self.responder(200, {"comandos": sorted(PERMITIDOS)})

        return self.responder(404, {"erro": "rota desconhecida"})

    def do_POST(self):
        if not self.autorizado():
            return self.responder(401, {"erro": "token inválido"})

        tam = int(self.headers.get("Content-Length", 0) or 0)
        try:
            corpo = json.loads(self.rfile.read(tam) or b"{}")
        except Exception:
            corpo = {}

        rota = self.path.split("?")[0]

        if rota == "/memoria":
            nome = str(corpo.get("nome", "memoria"))
            dados = corpo.get("dados")
            if not isinstance(dados, str) or not dados:
                return self.responder(400, {"erro": "sem dados"})
            try:
                caminho, n = guardar_memoria(nome, dados)
                return self.responder(200, {"ok": True, "arquivo": os.path.basename(caminho),
                                            "bytes": len(dados.encode("utf-8")),
                                            "versoes": n, "espelho": ESPELHO})
            except Exception as e:
                return self.responder(500, {"erro": type(e).__name__ + ": " + str(e)[:120]})

        if rota == "/texto":
            # O app abre um item e quer o artigo inteiro. Quem busca é a Ponte:
            # ela não tem as travas de origem que o navegador impõe.
            url = str(corpo.get("url", ""))
            if not url.startswith("http"):
                return self.responder(400, {"erro": "url inválida"})
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Android) SistemaAbsoluto/1.0",
                    "Accept": "text/html,application/xhtml+xml",
                })
                with urllib.request.urlopen(req, timeout=25) as r:
                    bruto = r.read(3_000_000).decode("utf-8", errors="replace")
                texto = extrair_texto(bruto)
                if len(texto) < 120:
                    return self.responder(200, {"texto": "", "aviso":
                        "a página não entregou texto legível (pode exigir login ou ser PDF)"})
                return self.responder(200, {"texto": texto, "tamanho": len(texto)})
            except Exception as e:
                return self.responder(200, {"texto": "", "aviso":
                    type(e).__name__ + ": " + str(e)[:120]})

        if rota != "/rodar":
            return self.responder(404, {"erro": "rota desconhecida"})

        nome = str(corpo.get("comando", ""))
        if nome not in PERMITIDOS:
            return self.responder(400, {"erro": "comando não liberado", "liberados": sorted(PERMITIDOS)})

        chave = nome + "-" + str(int(time.time()))
        threading.Thread(target=rodar_tarefa, args=(nome, chave), daemon=True).start()
        return self.responder(202, {"aceito": True, "tarefa": chave})


def main():
    if "--token" in sys.argv:
        print(TOKEN)
        return
    print("═" * 52)
    print("  PONTE ligada em http://127.0.0.1:%d" % PORTA)
    print("  Token (cole uma vez em Ajustes → Termux):")
    print()
    print("     " + TOKEN)
    print()
    print("  Só o próprio aparelho alcança. Deixe rodando com:")
    print("     termux-wake-lock && python ponte.py &")
    print("═" * 52)
    ThreadingHTTPServer(("127.0.0.1", PORTA), Ponte).serve_forever()


if __name__ == "__main__":
    main()
