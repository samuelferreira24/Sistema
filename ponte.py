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
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTA = 8099
CASA = os.path.expanduser("~")
SA = os.path.join(CASA, "sa")
BIBLIOTECA = os.path.join(CASA, "biblioteca")
ARQ_TOKEN = os.path.join(CASA, ".sa-ponte-token")


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

        if self.path.split("?")[0] != "/rodar":
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
