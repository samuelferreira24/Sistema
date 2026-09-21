#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
EXECUTOR — a IA com braços

O que muda daqui pra frente: ela não escreve o código e espera você rodar.
Ela escreve, roda, lê o erro, corrige, e tenta de novo — sozinha, até funcionar
ou até desistir com um relatório do que travou.

A segurança aqui NÃO é pedir permissão a cada passo. Samuel não lê código, então
aprovar comando seria teatro. A segurança real são quatro camadas:

  1. CERCA      — ela só mexe dentro de ~/sa/trabalho. Fora dali, nada existe.
  2. FOTO       — antes de cada tarefa, cópia completa. Uma linha desfaz tudo.
  3. PROIBIDO   — comandos destrutivos nunca rodam, nem se ela insistir.
  4. ESCALAÇÃO  — dinheiro, contrato e o que sai pro mundo param e chamam você.

Uso:
    python executor.py "o que você quer que ela faça"
    python executor.py --reverter        # desfaz a última tarefa
    python executor.py --fotos           # lista o que dá pra desfazer
    python executor.py --diario          # o que ela fez, passo a passo
"""

import json, os, re, shutil, subprocess, sys, tarfile, time
import urllib.request
from datetime import datetime, timezone

BASE = os.path.expanduser("~/sa")
TRABALHO = os.path.join(BASE, "trabalho")      # a cerca: só aqui ela mexe
FOTOS = os.path.join(BASE, "fotos")            # snapshots pra reverter
DIARIO = os.path.join(BASE, "executor.log")
ESTADO = os.path.join(BASE, "executor-estado.json")

MAX_VOLTAS = 25          # teto de tentativas por tarefa
MAX_JULGAMENTOS = 3      # quantas vezes o crítico pode devolver o trabalho
MAX_FOTOS = 10           # quantas reversões ficam guardadas
TIMEOUT_CMD = 120        # segundos por comando


# ═══════════════════════════════════════════════════════════
# CAMADA 3 — o que nunca roda, nem se ela pedir
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# CAMADA 3 — o que nunca roda, nem se ela pedir
#
# Esta lista foi reescrita para o cenário COM privilégio elevado (Shizuku/rish).
# A diferença importa: sem privilégio, `pm uninstall` só falha. Com privilégio,
# desinstala de verdade. Comando que era inofensivo passa a ser destrutivo.
#
# Regra que guiou a lista: a IA constrói dentro da pasta de trabalho.
# Nada que ela faça deveria precisar tocar no sistema, em outro app, ou
# na tela do aparelho. Se precisar, é você quem faz.
# ═══════════════════════════════════════════════════════════

PROIBIDO = [
    # ─── Destruição de dados ───
    (r"\brm\s+(-\w+\s+)*-?\w*[rf]", "apagar em massa"),
    (r"\b(mkfs|fdisk|dd)\b", "mexer em disco"),
    (r">\s*/dev/(sd|block)", "escrever em dispositivo"),
    (r"\b(chmod|chown|rm|mv|cp)\b[^|;&]*\s/(\s|$)", "operar sobre a raiz do sistema"),
    (r"\bchmod\b[^|;&]*\b(777|a\+rwx)", "abrir permissão total"),

    # ─── Pastas do sistema (a de trabalho fica de fora) ───
    (r"\s/(system|vendor|proc|dev|sbin|apex)\b", "tocar em pasta do sistema"),
    (r"/data/data/(?!com\.termux/files/home/sa)", "tocar em dado de outro app"),
    (r"/data/(user|misc|system|vendor)\b", "tocar em dado protegido"),

    # ─── Segredo e identidade ───
    (r"\.ssh|id_rsa|\.gnupg|\.netrc", "tocar em chave de acesso"),
    (r"sa:cfg|sa:nucleo|sa:operacao", "tocar na memória do app"),
    (r"api\.github\.com|GITHUB_TOKEN|ghp_|github_pat_", "usar o token do GitHub"),
    (r"\b(motor|especialistas|governanca)\.json\b", "reescrever configuração da malha"),
    (r"executor-estado|executor\.py", "modificar o próprio executor"),
    (r"\bkeystore\b|\bkeychain\b", "tocar no cofre de credenciais"),

    # ─── Publicar sem você saber ───
    (r"\bgit\s+push\b", "publicar sem você saber"),
    (r"\b(curl|wget)\b.*\|\s*(ba)?sh", "baixar e executar direto"),

    # ═══ A PARTIR DAQUI: só perigoso COM privilégio elevado ═══

    # ─── Controlar o aparelho ───
    (r"\brish\b|\bshizuku\b", "escalar o próprio privilégio"),
    (r"\binput\s+(tap|swipe|text|keyevent|touchscreen)", "simular toque na tela"),
    (r"\buiautomator\b|\bmonkey\b", "automatizar a interface"),
    (r"\bam\s+(start|broadcast|force-stop|kill)", "abrir ou matar aplicativo"),
    (r"\bscreencap\b|\bscreenrecord\b", "capturar a tela"),

    # ─── Mexer em outros apps ───
    (r"\bpm\s+(install|uninstall|disable|enable|clear|grant|revoke)", "instalar ou remover app"),
    (r"\b(pkg|apt|apt-get)\s+(uninstall|remove|purge|autoremove)", "desinstalar pacote do Termux"),
    (r"\bcmd\s+(package|notification|appops|activity)", "controlar app pelo sistema"),
    (r"\bappops\b", "mudar permissão de app"),

    # ─── Mudar o sistema ───
    (r"\bsettings\s+(put|delete)", "alterar configuração do sistema"),
    (r"\bsvc\s+(power|wifi|data|bluetooth)", "controlar hardware do aparelho"),
    (r"\bcontent\s+(insert|update|delete|call)", "escrever em banco do sistema"),
    (r"\b(setprop|resetprop)\b", "alterar propriedade do sistema"),
    (r"\bdevice_config\b", "mudar configuração experimental"),

    # ─── Ler o que não é dele ───
    (r"\bdumpsys\s+(notification|account|user|telephony|wifi)",
     "ler dado sensível de outro app"),
    (r"\blogcat\b", "ler o registro do sistema inteiro"),
    (r"\bsqlite3\b[^|;&]*/data/", "abrir banco de outro app"),

    # ─── Persistência e privilégio ───
    (r"\b(shutdown|reboot|halt|bootloader|fastboot)\b", "desligar ou reiniciar"),
    (r"\bsudo\b|\bsu\b\s|\bmagisk\b", "escalar privilégio"),
    (r"\bcrontab\b|termux-job-scheduler", "mexer no agendamento"),
    (r"\btermux-(sms|call|camera|location|contact|telephony)", "usar sensor ou dado pessoal"),

    # ─── Sair da cerca ───
    (r"\.\./\.\.", "sair da pasta de trabalho"),
]

# Palavras que fazem a tarefa parar e chamar Samuel, em vez de decidir sozinha
ESCALA = [
    "contrato", "assinar", "pagar", "comprar", "cobrar", "preço final",
    "enviar ao cliente", "publicar", "cnpj", "holding", "banco",
    "cartão", "pix", "transferir", "demitir", "contratar",
]


def com_privilegio():
    """Descobre se o Shizuku está ativo. Com privilégio, comando inofensivo
       vira destrutivo — e o executor precisa saber disso."""
    if os.path.exists(os.path.expanduser("~/rish")) or \
       os.path.exists(os.path.expanduser("~/.local/bin/rish")):
        try:
            p = subprocess.run("rish -c 'id'", shell=True, capture_output=True,
                               text=True, timeout=8)
            return "uid=2000" in (p.stdout or "")   # 2000 = shell do ADB
        except Exception:
            return False
    return False


def proibido(cmd):
    """Devolve o motivo se o comando for barrado; None se pode rodar."""
    baixo = cmd.lower()
    for padrao, motivo in PROIBIDO:
        if re.search(padrao, baixo):
            return motivo
    return None


def precisa_de_samuel(texto):
    baixo = (texto or "").lower()
    achou = [p for p in ESCALA if p in baixo]
    return achou


# ═══════════════════════════════════════════════════════════
# CAMADA 2 — foto antes, reversão depois
# ═══════════════════════════════════════════════════════════

def anotar(msg):
    os.makedirs(BASE, exist_ok=True)
    linha = f"[{datetime.now().strftime('%d/%m %H:%M:%S')}] {msg}"
    print(linha, flush=True)
    with open(DIARIO, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def tirar_foto(rotulo):
    """Cópia completa da pasta de trabalho antes de qualquer mudança."""
    os.makedirs(FOTOS, exist_ok=True)
    os.makedirs(TRABALHO, exist_ok=True)
    nome = datetime.now().strftime("%Y%m%d-%H%M%S")
    caminho = os.path.join(FOTOS, f"{nome}.tar.gz")
    with tarfile.open(caminho, "w:gz") as t:
        t.add(TRABALHO, arcname="trabalho")
    with open(caminho + ".txt", "w", encoding="utf-8") as f:
        f.write(rotulo)

    # Guarda só as últimas, pra não encher o aparelho
    fotos = sorted(f for f in os.listdir(FOTOS) if f.endswith(".tar.gz"))
    for velha in fotos[:-MAX_FOTOS]:
        try:
            os.remove(os.path.join(FOTOS, velha))
            os.remove(os.path.join(FOTOS, velha + ".txt"))
        except Exception:
            pass
    anotar(f"foto guardada: {nome} ({os.path.getsize(caminho)//1024} KB)")
    return caminho


def listar_fotos():
    if not os.path.isdir(FOTOS):
        print("\nNenhuma foto ainda.\n")
        return []
    fotos = sorted(f for f in os.listdir(FOTOS) if f.endswith(".tar.gz"))
    print(f"\n{len(fotos)} pontos de retorno:\n")
    for i, f in enumerate(reversed(fotos), 1):
        rot = ""
        try:
            with open(os.path.join(FOTOS, f + ".txt"), encoding="utf-8") as r:
                rot = r.read()[:70]
        except Exception:
            pass
        quando = f[:15].replace("-", " às ")
        print(f"  {i}. {quando} — {rot}")
    print("\n  Para desfazer a última: python executor.py --reverter\n")
    return fotos


def reverter(qual=None):
    fotos = sorted(f for f in os.listdir(FOTOS)) if os.path.isdir(FOTOS) else []
    fotos = [f for f in fotos if f.endswith(".tar.gz")]
    if not fotos:
        print("\nNão há foto pra reverter.\n")
        return
    alvo = fotos[-1] if qual is None else fotos[-int(qual)]
    rot = ""
    try:
        with open(os.path.join(FOTOS, alvo + ".txt"), encoding="utf-8") as r:
            rot = r.read()[:80]
    except Exception:
        pass

    print(f"\nVai voltar para: {alvo[:15]} — {rot}")
    print("Tudo que foi feito depois disso será desfeito.")
    if input("Confirma? (s/N): ").strip().lower() != "s":
        print("Cancelado.\n")
        return

    # Guarda o estado atual antes de reverter — reverter também é reversível
    tirar_foto("antes de reverter")
    shutil.rmtree(TRABALHO, ignore_errors=True)
    with tarfile.open(os.path.join(FOTOS, alvo), "r:gz") as t:
        t.extractall(BASE)
    anotar(f"revertido para {alvo}")
    print(f"\nRevertido. A pasta de trabalho voltou ao estado de {alvo[:15]}.\n")


# ═══════════════════════════════════════════════════════════
# CAMADA 1 — as ferramentas, todas presas à cerca
# ═══════════════════════════════════════════════════════════

def dentro_da_cerca(caminho):
    """Impede qualquer caminho que escape de ~/sa/trabalho."""
    completo = os.path.realpath(os.path.join(TRABALHO, caminho))
    return completo.startswith(os.path.realpath(TRABALHO))


def rodar_comando(cmd):
    motivo = proibido(cmd)
    if motivo:
        return {"ok": False, "saida": f"BLOQUEADO: {motivo}. Esse comando nunca roda. "
                                      f"Resolva de outro jeito."}
    os.makedirs(TRABALHO, exist_ok=True)

    # Se o Shizuku estiver ativo no seu terminal, o executor NÃO herda isso.
    # Ele roda como app comum, sempre. Privilégio elevado é seu, não dele —
    # e a lista de proibições existe justamente porque um vazamento aqui
    # transformaria um erro dele em estrago no aparelho inteiro.
    ambiente = dict(os.environ)
    for v in ("RISH_APPLICATION_ID", "SHIZUKU_APPLICATION_ID", "ADB_VENDOR_KEYS"):
        ambiente.pop(v, None)
    ambiente["PATH"] = ":".join(p for p in ambiente.get("PATH", "").split(":")
                               if "rish" not in p.lower())

    try:
        p = subprocess.run(cmd, shell=True, cwd=TRABALHO, capture_output=True,
                           text=True, timeout=TIMEOUT_CMD, env=ambiente)
        saida = (p.stdout or "") + (("\nERRO:\n" + p.stderr) if p.stderr else "")
        return {"ok": p.returncode == 0, "codigo": p.returncode,
                "saida": saida[-4000:] or "(sem saída)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "saida": f"O comando passou de {TIMEOUT_CMD}s e foi interrompido."}
    except Exception as e:
        return {"ok": False, "saida": f"Falhou: {str(e)[:300]}"}


def escrever(caminho, conteudo):
    if not dentro_da_cerca(caminho):
        return {"ok": False, "saida": "BLOQUEADO: fora da pasta de trabalho."}
    completo = os.path.join(TRABALHO, caminho)
    os.makedirs(os.path.dirname(completo) or TRABALHO, exist_ok=True)
    with open(completo, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return {"ok": True, "saida": f"{caminho} gravado ({len(conteudo)} caracteres)"}


def ler(caminho):
    if not dentro_da_cerca(caminho):
        return {"ok": False, "saida": "BLOQUEADO: fora da pasta de trabalho."}
    completo = os.path.join(TRABALHO, caminho)
    if not os.path.exists(completo):
        return {"ok": False, "saida": f"{caminho} não existe."}
    with open(completo, encoding="utf-8", errors="replace") as f:
        return {"ok": True, "saida": f.read()[:6000]}


def listar(caminho="."):
    if not dentro_da_cerca(caminho):
        return {"ok": False, "saida": "BLOQUEADO: fora da pasta de trabalho."}
    completo = os.path.join(TRABALHO, caminho)
    if not os.path.isdir(completo):
        return {"ok": False, "saida": "não é uma pasta."}
    itens = []
    for n in sorted(os.listdir(completo)):
        p = os.path.join(completo, n)
        itens.append(f"{n}/" if os.path.isdir(p) else
                     f"{n} ({os.path.getsize(p)} bytes)")
    return {"ok": True, "saida": "\n".join(itens) or "(pasta vazia)"}


def buscar_base(termo):
    """Consulta o que o sistema já coletou, com o grau da fonte.
       Vem antes de pesquisar fora: dado seu, já filtrado, custa zero."""
    if not termo:
        return {"ok": False, "saida": "Faltou o termo."}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import base as bd
        if not os.path.exists(bd.BANCO):
            return {"ok": False, "saida": "A base ainda não existe. Rode o coletor primeiro, "
                                          "ou use pesquisar para buscar fora."}
        achados = bd.buscar(termo, n=6)
        if not achados:
            return {"ok": True, "saida": "Nada na base sobre isso. Se precisar do dado, "
                                         "use pesquisar — e avise que veio de fora, não da base."}
        graus = {1: "fonte primária", 2: "especializada", 3: "agregador"}
        linhas = []
        for a in achados:
            marca = " [neutralizado]" if a.get("suspeito") else ""
            linhas.append(f"[{graus.get(a['tier'], '?')}·{a['fonte'][:28]}]{marca} {a['titulo']}\n"
                          f"  {(a.get('corpo') or '')[:220]}")
        return {"ok": True, "saida": f"{len(achados)} itens da sua base:\n\n" + "\n\n".join(linhas)}
    except Exception as e:
        return {"ok": False, "saida": "Não consegui ler a base: " + str(e)[:150]}


def pesquisar(termo):
    """Busca na internet quando ele trava numa dúvida técnica.
       Sem isso, ele chuta ou desiste — e chute vira código quebrado."""
    if not termo:
        return {"ok": False, "saida": "Faltou o termo."}
    c = cfg()
    chave, url = c.get("chave"), (c.get("url") or "")

    # Vaza segredo? Barra antes de sair do aparelho. Ele pesquisa dúvida
    # técnica, não o conteúdo dos seus arquivos.
    baixo = termo.lower()
    for padrao in (r"ghp_|github_pat_|sk-[a-z0-9]{20}|AIza[a-z0-9]", r"senha|password|token|chave de"):
        if re.search(padrao, baixo):
            return {"ok": False, "saida": "BLOQUEADO: não pesquise nada que contenha segredo. "
                                          "Descreva o problema sem colar chave, token ou senha."}
    if len(termo) > 400:
        return {"ok": False, "saida": "Termo longo demais. Pesquise a dúvida, não cole o arquivo."}

    try:
        # Gemini: busca do Google embutida
        if "generativelanguage" in url or c.get("tipo") == "gemini":
            alvo = ("https://generativelanguage.googleapis.com/v1beta/models/" +
                    (c.get("modelo") or "gemini-3.5-flash") +
                    ":generateContent?key=" + (chave or ""))
            corpo = {"contents": [{"parts": [{"text": termo}]}],
                     "tools": [{"google_search": {}}],
                     "generationConfig": {"temperature": 0.3}}
            req = urllib.request.Request(alvo, data=json.dumps(corpo).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read().decode("utf-8"))
            cand = d["candidates"][0]
            texto = "".join(p.get("text", "") for p in cand["content"]["parts"])
            chunks = cand.get("groundingMetadata", {}).get("groundingChunks", [])
            fontes = [c2["web"].get("title", "") for c2 in chunks if "web" in c2][:4]
            return {"ok": True, "saida": texto +
                    ("\n\nFontes: " + " · ".join(fontes) if fontes else "")}

        # Groq: o compound tem busca embutida
        corpo = {"model": "compound-beta", "messages": [{"role": "user", "content": termo}],
                 "max_tokens": 1200, "temperature": 0.3}
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
                                     data=json.dumps(corpo).encode("utf-8"),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + (chave or "")})
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {"ok": True, "saida": d["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"ok": False, "saida": "A busca falhou: " + str(e)[:200] +
                ". Siga com o que você já sabe e avise que não conferiu."}


FERRAMENTAS = {
    "rodar":    {"desc": "Executa um comando no terminal, dentro da pasta de trabalho. args: {cmd}",
                 "fn": lambda a: rodar_comando(a.get("cmd", ""))},
    "escrever": {"desc": "Cria ou substitui um arquivo. args: {caminho, conteudo}",
                 "fn": lambda a: escrever(a.get("caminho", ""), a.get("conteudo", ""))},
    "ler":      {"desc": "Lê um arquivo. args: {caminho}",
                 "fn": lambda a: ler(a.get("caminho", ""))},
    "listar":   {"desc": "Lista o que existe numa pasta. args: {caminho}",
                 "fn": lambda a: listar(a.get("caminho", "."))},
    "base":     {"desc": "Consulta a base que o sistema já coletou, com o grau de cada fonte. "
                         "Use ANTES de pesquisar fora: é dado do Samuel, já filtrado. args: {termo}",
                 "fn": lambda a: buscar_base(a.get("termo", ""))},
    "pesquisar":{"desc": "Busca na internet quando você não sabe algo — erro que não reconhece, "
                         "biblioteca que não conhece, versão que mudou. Use antes de chutar. "
                         "Nunca inclua chave, token ou senha no termo. args: {termo}",
                 "fn": lambda a: pesquisar(a.get("termo", ""))},
}


# ═══════════════════════════════════════════════════════════
# O motor
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# ATOR / CRÍTICO / ADVERSÁRIO
#
# O padrão do ator-crítico sem treinar nada: quem faz não é quem julga.
# O executor (ator) trabalha e diz "pronto". Antes de aceitar, dois outros
# olham com olhos frescos — e não veem a conversa dele, só o resultado.
# Isso importa: quem acompanhou o raciocínio herda os pontos cegos dele.
#
# CRÍTICO    — isso está de fato pronto, ou o ator se convenceu sozinho?
# ADVERSÁRIO — de que jeito isso quebra na mão de quem vai usar?
#
# Não é aprendizado por reforço: nenhum peso muda. É a mesma estrutura
# aplicada em tempo de execução, que é onde ela cabe sem GPU.
# ═══════════════════════════════════════════════════════════

PAPEL_CRITICO = """Você é o CRÍTICO. Outro agente diz que terminou uma tarefa. Seu trabalho é
descobrir se isso é verdade — e o padrão é que não seja inteiramente.

Você não viu o raciocínio dele, de propósito. Julga só pelo que existe: os arquivos e o que
foi testado. Se ele diz que testou, confira se o teste prova mesmo o que ele afirma.

Procure especificamente:
· afirmação sem prova — "funciona" sem ter rodado
· o pedido original que ficou pela metade
· caso comum não tratado (arquivo vazio, campo em branco, sem internet)
· código que roda mas não faz o que a tarefa pedia
· sobra: coisa que ele criou e não serve pra nada

Seja duro, mas específico. "Está ruim" não ajuda; "a função não trata lista vazia" ajuda.
Se estiver realmente bom, diga que está — aprovar coisa boa também é seu trabalho.

Responda SOMENTE com JSON:
{"aprovado":true|false,"nota":0-10,
 "problemas":[{"o_que":"","gravidade":"alta|media|baixa","como_corrigir":""}],
 "veredito":"1 ou 2 frases"}"""

PAPEL_ADVERSARIO = """Você é o ADVERSÁRIO. Sua função é quebrar o que foi construído, antes que
o cliente quebre.

Você não sugere melhoria e não elogia. Você acha onde falha. Pense como usuário desatento,
conexão ruim, dado sujo, celular fraco.

Ataque:
· entrada vazia, gigante, com acento, com aspas, com emoji
· clicar duas vezes, sair no meio, voltar
· sem internet, internet lenta, servidor fora
· número onde esperava texto, texto onde esperava número
· arquivo que não existe, pasta sem permissão

Para cada falha, diga como reproduzir. Falha que não sei repetir, não sei corrigir.

Responda SOMENTE com JSON:
{"quebrou":true|false,
 "falhas":[{"como":"o passo exato","resultado":"o que acontece de errado","gravidade":"alta|media|baixa"}],
 "veredito":"1 frase"}"""


def resumo_do_trabalho():
    """O que o crítico e o adversário enxergam: o resultado, não o caminho."""
    partes = []
    for raiz, _, arquivos in os.walk(TRABALHO):
        for nome in sorted(arquivos)[:12]:
            caminho = os.path.join(raiz, nome)
            rel = os.path.relpath(caminho, TRABALHO)
            try:
                if os.path.getsize(caminho) > 40000:
                    partes.append(f"### {rel}\n(arquivo grande, {os.path.getsize(caminho)//1024} KB)")
                    continue
                with open(caminho, encoding="utf-8", errors="replace") as f:
                    partes.append(f"### {rel}\n{f.read()[:3000]}")
            except Exception:
                partes.append(f"### {rel}\n(não deu pra ler)")
    return "\n\n".join(partes) or "(nada foi criado)"


def julgar(papel, tarefa, entrega):
    """Chama um juiz sem histórico — ele não herda os pontos cegos do ator."""
    msgs = [{"role": "system", "content": papel},
            {"role": "user", "content":
             "TAREFA PEDIDA:\n" + tarefa +
             "\n\nO QUE O AGENTE DIZ QUE ENTREGOU:\n" + json.dumps(entrega, ensure_ascii=False) +
             "\n\nO QUE EXISTE DE FATO:\n" + resumo_do_trabalho()}]
    try:
        bruto, uso = perguntar(msgs)
        texto = bruto.replace("```json", "").replace("```", "").strip()
        i, f = texto.find("{"), texto.rfind("}")
        if i >= 0 and f > i:
            texto = texto[i:f + 1]
        return json.loads(texto), uso
    except Exception as e:
        return {"_erro": str(e)[:120]}, {}


def cfg():
    try:
        with open(os.path.join(BASE, "motor.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def perguntar(mensagens):
    c = cfg()
    url = c.get("url") or "http://127.0.0.1:8080/v1/chat/completions"
    corpo = {"model": c.get("modelo", "local"), "messages": mensagens,
             "max_tokens": 4000, "temperature": 0.3}
    req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    if c.get("chave"):
        req.add_header("Authorization", "Bearer " + c["chave"])
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode("utf-8"))
    uso = d.get("usage", {})
    return d["choices"][0]["message"]["content"], uso


PAPEL = """Você é o executor do Sistema Absoluto de Samuel. Você tem BRAÇOS: pode criar
arquivo, rodar comando e ler o resultado. Use isso.

COMO TRABALHAR
Não descreva o que faria — faça. Escreva o arquivo, rode, leia o erro, corrija, rode de novo.
Repita até funcionar. Se travar na mesma coisa três vezes, pare e explique o que travou em vez
de tentar a mesma coisa pela quarta.

Teste o que você escreve. Código que você nunca rodou não está pronto.

A BASE VEM ANTES DA INTERNET
Samuel tem uma base própria, coletada de fonte primária e já filtrada. Consulte com a
ferramenta base antes de pesquisar fora. Dado que ele já tem vale mais que resultado de busca,
e custa zero.

PESQUISE EM VEZ DE CHUTAR
Erro que você não reconhece, biblioteca que não conhece, versão que mudou, sintaxe que você
não tem certeza: use pesquisar antes de tentar às cegas. Chute vira código quebrado, e código
quebrado custa mais voltas que uma busca.
Nunca coloque chave, token ou senha no termo de busca — descreva o problema sem colar segredo.

A CERCA
Você só existe dentro da pasta de trabalho. Não tente sair dela, não tente instalar coisa no
sistema, não tente tocar em chave, token ou memória do app. Se um comando for bloqueado, o
motivo aparece — resolva de outro jeito, não insista.

QUANDO PARAR E CHAMAR SAMUEL
Dinheiro, contrato, preço final, qualquer coisa que saia para o cliente ou para o mundo: pare
e devolva a decisão para ele. Você constrói e testa; ele decide o que vai pra fora.

COMO RESPONDER
Para usar uma ferramenta, responda SÓ com este JSON, nada mais:
{"ferramenta":"rodar|escrever|ler|listar","args":{}}

Quando a tarefa estiver pronta, responda SÓ com:
{"pronto":true,"resumo":"o que ficou pronto, em 2 a 4 frases","arquivos":["que criou"],
 "testado":"como você confirmou que funciona","proximo":"o que Samuel decide agora"}

Se travar de vez:
{"travou":true,"onde":"o que não passou","tentei":"o que você já tentou","preciso":"o que falta"}
"""


def executar(tarefa):
    escalar = precisa_de_samuel(tarefa)
    if escalar:
        print(f"\n⚠ Essa tarefa toca em: {', '.join(escalar)}.")
        print("  Coisas assim são decisão sua, não minha.")
        if input("  Quer que eu construa mesmo assim, sem decidir nada? (s/N): ").strip().lower() != "s":
            print("  Parado.\n")
            return

    os.makedirs(TRABALHO, exist_ok=True)
    tirar_foto(tarefa[:70])

    if com_privilegio():
        print("\n⚠ Shizuku ativo neste terminal.")
        print("  O executor roda SEM esse privilégio de propósito — ele não herda.")
        print("  Mas se algo escapar, o estrago seria no aparelho, não só na pasta.")
        print("  Para máxima segurança, rode o executor numa aba sem Shizuku.\n")

    anotar(f"── tarefa: {tarefa[:70]} ──")
    mensagens = [{"role": "system", "content": PAPEL},
                 {"role": "user", "content": tarefa}]
    usos = {"ent": 0, "sai": 0}
    repetidos = {}
    julgamentos = 0

    for volta in range(MAX_VOLTAS):
        try:
            bruto, uso = perguntar(mensagens)
        except Exception as e:
            anotar(f"motor falhou: {str(e)[:150]}")
            print("\nO motor não respondeu. Confira ~/sa/motor.json ou ligue o motor local.\n")
            return
        usos["ent"] += uso.get("prompt_tokens", 0)
        usos["sai"] += uso.get("completion_tokens", 0)

        texto = bruto.replace("```json", "").replace("```", "").strip()
        i, f = texto.find("{"), texto.rfind("}")
        if i >= 0 and f > i:
            texto = texto[i:f + 1]
        try:
            obj = json.loads(texto)
        except json.JSONDecodeError:
            mensagens.append({"role": "assistant", "content": bruto[:500]})
            mensagens.append({"role": "user",
                              "content": "Responda SOMENTE com o JSON, sem texto em volta."})
            continue

        if obj.get("pronto"):
            # Antes de aceitar, dois juízes olham com olhos frescos.
            if julgamentos < MAX_JULGAMENTOS:
                julgamentos += 1
                anotar(f"  ator diz pronto — julgamento {julgamentos}")

                cri, u1 = julgar(PAPEL_CRITICO, tarefa, obj)
                adv, u2 = julgar(PAPEL_ADVERSARIO, tarefa, obj)
                for u in (u1, u2):
                    usos["ent"] += u.get("prompt_tokens", 0)
                    usos["sai"] += u.get("completion_tokens", 0)

                graves = []
                if not cri.get("_erro"):
                    nota = cri.get("nota", "?")
                    anotar(f"     crítico: nota {nota} · " +
                           ("aprovou" if cri.get("aprovado") else "reprovou"))
                    graves += [p for p in (cri.get("problemas") or [])
                               if p.get("gravidade") in ("alta", "media")]
                if not adv.get("_erro"):
                    anotar(f"     adversário: " +
                           ("quebrou" if adv.get("quebrou") else "não quebrou"))
                    graves += [{"o_que": f["como"] + " → " + f.get("resultado", ""),
                                "gravidade": f.get("gravidade", "media"),
                                "como_corrigir": "trate esse caso"}
                               for f in (adv.get("falhas") or [])
                               if f.get("gravidade") in ("alta", "media")]

                if graves:
                    anotar(f"     {len(graves)} problema(s) — devolvido ao ator")
                    lista = "\n".join(
                        f"· [{p.get('gravidade','?')}] {p.get('o_que','')}\n"
                        f"  corrigir assim: {p.get('como_corrigir','')}"
                        for p in graves[:6])
                    mensagens.append({"role": "assistant", "content": texto})
                    mensagens.append({"role": "user", "content":
                        "Ainda não está pronto. Dois revisores olharam o resultado sem ver o "
                        "seu raciocínio, e acharam isto:\n\n" + lista +
                        "\n\nCorrija de verdade — rode e confirme. Depois responda pronto de novo."})
                    continue
                anotar("     aprovado pelos dois")

            anotar(f"pronto em {volta+1} voltas")
            print("\n" + "═" * 50)
            print("  PRONTO")
            print("═" * 50)
            print(f"\n{obj.get('resumo','')}\n")
            if obj.get("arquivos"):
                print("  Arquivos: " + ", ".join(obj["arquivos"]))
            if obj.get("testado"):
                print(f"  Testado: {obj['testado']}")
            if obj.get("proximo"):
                print(f"\n  Sua decisão: {obj['proximo']}")
            print(f"\n  Em: {TRABALHO}")
            print(f"  Tokens: {usos['ent']} entrada · {usos['sai']} saída")
            if julgamentos:
                print(f"  Passou por {julgamentos} rodada(s) de revisão")
            print("  Se não gostou: python executor.py --reverter\n")
            salvar_estado(tarefa, "pronto", usos, volta + 1)
            return

        if obj.get("travou"):
            anotar(f"travou: {obj.get('onde','')[:80]}")
            print("\n" + "═" * 50)
            print("  TRAVOU")
            print("═" * 50)
            print(f"\n  Onde: {obj.get('onde','')}")
            print(f"  Já tentou: {obj.get('tentei','')}")
            print(f"  Precisa: {obj.get('preciso','')}\n")
            salvar_estado(tarefa, "travou", usos, volta + 1)
            return

        nome = obj.get("ferramenta")
        if nome not in FERRAMENTAS:
            mensagens.append({"role": "user",
                              "content": "Ferramenta inválida. Use: " + ", ".join(FERRAMENTAS)})
            continue

        args = obj.get("args", {})
        assinatura = nome + json.dumps(args, sort_keys=True)[:120]
        repetidos[assinatura] = repetidos.get(assinatura, 0) + 1
        if repetidos[assinatura] > 3:
            mensagens.append({"role": "user",
                "content": "Você repetiu exatamente isso quatro vezes e não funcionou. "
                           "Tente um caminho diferente, ou responda com travou:true."})
            continue

        r = FERRAMENTAS[nome]["fn"](args)
        marca = "ok" if r["ok"] else "falhou"
        detalhe = args.get("cmd") or args.get("caminho") or ""
        anotar(f"  {volta+1}. {nome} {str(detalhe)[:50]} → {marca}")

        mensagens.append({"role": "assistant", "content": texto})
        mensagens.append({"role": "user",
                          "content": f"Resultado ({marca}):\n{r['saida'][:3000]}"})

        # Não deixa a conversa crescer sem fim
        if len(mensagens) > 24:
            mensagens = mensagens[:2] + mensagens[-18:]

    anotar("teto de voltas atingido")
    print(f"\nParei em {MAX_VOLTAS} tentativas sem concluir.")
    print("O que foi feito está na pasta de trabalho. Para desfazer: --reverter\n")
    salvar_estado(tarefa, "teto", usos, MAX_VOLTAS)


def salvar_estado(tarefa, fim, usos, voltas):
    h = []
    try:
        with open(ESTADO, encoding="utf-8") as f:
            h = json.load(f)
    except Exception:
        pass
    h.append({"quando": datetime.now(timezone.utc).isoformat(), "tarefa": tarefa[:150],
              "fim": fim, "voltas": voltas, "tokens": usos})
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(h[-50:], f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--reverter":
        reverter(sys.argv[2] if len(sys.argv) > 2 else None)
    elif arg == "--fotos":
        listar_fotos()
    elif arg == "--diario":
        try:
            with open(DIARIO, encoding="utf-8") as f:
                linhas = f.readlines()
            print("".join(linhas[-60:]))
        except FileNotFoundError:
            print("\nNada registrado ainda.\n")
    elif arg.startswith("--") or not arg:
        print(__doc__)
    else:
        executar(" ".join(sys.argv[1:]))
