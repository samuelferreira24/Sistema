#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
ORQUESTRADOR — Sistema Absoluto
Item 32.4: o Filtro de Calibragem virando regra que executa sozinha.

Roda no Termux, com a tela apagada, sem VPS. Faz o ciclo do Loop Fechado
(item 27) enquanto Samuel não está olhando: coleta → decide → executa →
registra → aprende → repete.

O que ele faz a cada rodada:
  1. Roda o coletor e traz o que mudou nas fontes
  2. Pergunta ao motor local o que isso muda para o projeto
  3. Aplica o Filtro de Calibragem a cada achado
  4. Grava um plantão e serve para o app buscar

Uso:
    python orquestrador.py            # uma rodada agora
    python orquestrador.py --servir   # roda e fica servindo na porta 8081
    python orquestrador.py --agendar  # agenda para rodar sozinho
    python orquestrador.py --status   # mostra o último plantão
"""

import json, os, sys, subprocess, time, traceback
import urllib.request, urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.expanduser("~/sistema-absoluto")
PLANTAO = os.path.join(BASE, "plantao.json")
DIARIO = os.path.join(BASE, "diario.log")
ESTADO = os.path.join(BASE, "estado.json")   # exportado pelo app
COLETOR = os.path.expanduser("~/coletor.py")
MOTOR = "http://127.0.0.1:8080/v1/chat/completions"
PORTA = 8081

# O Filtro de Calibragem (item 6) — as perguntas que decidem o que merece atenção
FILTRO = """Ao avaliar cada achado, aplique estas perguntas antes de dizer que importa:
1. Qual defesa competitiva isso fortalece? Qual enfraquece?
2. É raro e protegível, ou qualquer um replica?
3. É peça da Fábrica, ou ferramenta que a Fábrica produz?
4. Alimenta o caixa, ou consome sem retorno mapeado?
5. É composição segura, ou risco que só se corre com capital já conquistado?
6. Roda dentro do sistema próprio, ou depende de decisão de terceiro?
Achado que não passa em nenhuma dessas é ruído. Diga que é ruído e siga."""


# ═══════════════════════════════════════════════════════════
# A MALHA — item 2 do arquivo, virando agentes que executam
#
# Cada um tem escopo fechado e não invade o do outro. O despachante
# decide quem chamar. O que sobe pro PILOTO é só o que exige o salto.
# ═══════════════════════════════════════════════════════════

# Toda a cadeia precisa da trava, não só a primeira porta. Se um dado envenenado
# passar pelo [PESQUISA], os agentes seguintes recebem o veneno como se fosse fato.
# ═══════════════════════════════════════════════════════════
# O MAESTRO — item 7 do arquivo
#
# Recebe o pedido, classifica o domínio, chama os Especialistas certos,
# integra as respostas e resolve conflito pelo Filtro. É o único que fala
# com Samuel. Nunca executa a tarefa fim — roteia e integra.
#
# Falha de um Especialista nunca trava os outros: o sistema não é
# tudo-ou-nada.
# ═══════════════════════════════════════════════════════════

def carregar_especialistas():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import especialistas as esp
        return esp
    except Exception as e:
        anotar(f"  especialistas.py não carregou: {str(e)[:100]}")
        return None


def chamar_especialista(esp, nome, pedido, contexto, dados):
    """Um Especialista responde só do seu escopo. Se cair, os outros seguem."""
    import time as _t
    t0 = _t.time()
    try:
        bruto = perguntar(esp.montar_prompt(nome, pedido, contexto, dados),
                          limite=700, especialista=nome)
        texto = bruto.replace("```json", "").replace("```", "").strip()
        i, f = texto.find("{"), texto.rfind("}")
        if i >= 0 and f > i:
            texto = texto[i:f + 1]
        r = json.loads(texto)
        ms = int((_t.time() - t0) * 1000)
        fora = bool(r.get("fora_do_escopo") and r["fora_do_escopo"] != "null")
        vazio = not r.get("achados") and not r.get("resposta")
        esp.registrar(nome, chamado=True, fora_do_escopo=fora, sem_resposta=vazio, ms=ms)
        r["_especialista"] = nome
        r["_ms"] = ms
        return r
    except json.JSONDecodeError:
        esp.registrar(nome, chamado=True, sem_resposta=True, ms=int((_t.time() - t0) * 1000))
        return {"_especialista": nome, "_erro": "respondeu fora do formato"}
    except Exception as e:
        esp.registrar(nome, chamado=True, sem_resposta=True, ms=int((_t.time() - t0) * 1000))
        return {"_especialista": nome, "_erro": str(e)[:120]}


def rodar_malha(pergunta, contexto, dados):
    """Maestro: classifica, chama os Especialistas certos, integra e decide o que sobe."""
    esp = carregar_especialistas()
    if not esp:
        return {"trilha": [], "sobe": [], "restricao": "",
                "lacuna": "especialistas.py não encontrado"}

    escolhidos = esp.escolher(pergunta, teto=3)
    anotar(f"  [MAESTRO] domínio: {', '.join(escolhidos)}")

    trilha, respostas, suspeitas, lacunas, foras = [], [], [], [], []
    for nome in escolhidos:
        anotar(f"  [{nome.upper()}] respondendo…")
        r = chamar_especialista(esp, nome, pergunta, contexto, dados)
        trilha.append({"agente": nome, "saida": r})
        if r.get("_erro"):
            anotar(f"    falhou: {r['_erro']} — os outros seguem")
            continue
        respostas.append(r)
        if r.get("suspeita") and r["suspeita"] != "null":
            suspeitas.append(f"{nome}: {r['suspeita']}")
        if r.get("lacuna") and r["lacuna"] != "null":
            lacunas.append(f"{nome}: {r['lacuna']}")
            # Lacuna de dado não morre no relatório: vira busca por fonte que a preencha.
            if nome in ("pesquisa", "dados"):
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import governanca as gov
                    gov.anotar_lacuna_dado(r["lacuna"], pergunta)
                except Exception:
                    pass
        if r.get("fora_do_escopo") and r["fora_do_escopo"] != "null":
            foras.append(f"{nome}: {r['fora_do_escopo']}")

    if not respostas:
        return {"trilha": trilha, "sobe": [], "restricao": "",
                "lacuna": "nenhum Especialista respondeu", "suspeitas": suspeitas}

    anotar(f"  [MAESTRO] integrando {len(respostas)} respostas…")
    resumo = "\n\n".join(
        f"[{r['_especialista'].upper()}] {r.get('resposta','')}\n" +
        "\n".join(f"  - {a.get('o_que','')} (confiança {a.get('confianca','?')}, "
                  f"apoiado em {a.get('apoiado_em','?')})"
                  for a in (r.get("achados") or [])[:3])
        for r in respostas)

    p = (
        "Você é o MAESTRO da malha de Samuel. Você NÃO executa tarefa: roteia, integra e "
        "decide o que merece o tempo dele.\n\n"
        "Cada Especialista abaixo respondeu só do próprio escopo. Sua função é juntar, "
        "resolver contradição entre eles e decidir o que sobe pro Piloto.\n\n"
        "ESTADO DO PROJETO:\n" + (contexto or "(sem estado)") +
        "\n\nRESPOSTAS DOS ESPECIALISTAS:\n" + resumo +
        (("\n\nFORA DO ESCOPO relatado: " + " · ".join(foras)) if foras else "") +
        "\n\n" + FILTRO +
        "\n\nSamuel tem cerca de 3 horas por dia e nenhum cliente pagando ainda. "
        "Ataque a restrição única antes de espalhar esforço. Achado apoiado em fonte fraca "
        "ou confiança baixa não sobe sem ressalva. Se dois Especialistas se contradizem, "
        "diga qual prevalece e por quê. Termine num ponto de decisão, nunca numa ordem.\n\n"
        "Responda SOMENTE com JSON, sem markdown:\n"
        '{"sobe":[{"o_que":"","por_que_agora":"","primeira_acao":"","veio_de":"qual especialista"}],'
        '"conflito":"contradição entre especialistas e qual prevaleceu, ou null",'
        '"represado":"o que fica pra depois e sob qual gatilho",'
        '"restricao":"o gargalo único agora",'
        '"falta_especialista":"domínio que apareceu e ninguém cobre bem, ou null"}'
    )

    try:
        bruto = perguntar(p, limite=800)
        texto = bruto.replace("```json", "").replace("```", "").strip()
        i, f = texto.find("{"), texto.rfind("}")
        if i >= 0 and f > i:
            texto = texto[i:f + 1]
        m = json.loads(texto)
    except Exception as e:
        anotar(f"  [MAESTRO] não integrou: {str(e)[:100]}")
        m = {"sobe": [], "restricao": "", "conflito": None}

    trilha.append({"agente": "MAESTRO", "saida": m})

    if suspeitas:
        anotar(f"  ⚠ comando disfarçado sinalizado: {suspeitas[0][:80]}")
    if m.get("falta_especialista") and m["falta_especialista"] != "null":
        # A lacuna não some no ar: é contada, e vira Especialista quando se repete.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import governanca as gov
            n = gov.anotar_lacuna(m["falta_especialista"], pergunta)
            anotar(f"  ↑ domínio sem cobertura: {m['falta_especialista']} "
                   f"({n}ª vez — vira Especialista na {gov.LACUNA_PRA_CRIAR}ª)")
        except Exception as e:
            anotar(f"  ↑ domínio sem cobertura: {m['falta_especialista']} "
                   f"(não registrei: {str(e)[:60]})")

    return {
        "trilha": trilha,
        "sobe": m.get("sobe", []),
        "represado": m.get("represado", ""),
        "restricao": m.get("restricao", ""),
        "conflito": m.get("conflito"),
        "falta_especialista": m.get("falta_especialista"),
        "lacuna": " · ".join(lacunas),
        "suspeitas": suspeitas,
        "consultados": escolhidos,
    }


def agora():
    return datetime.now(timezone.utc).astimezone().strftime("%d/%m %H:%M")


def anotar(msg):
    os.makedirs(BASE, exist_ok=True)
    linha = f"[{agora()}] {msg}"
    print(linha)
    with open(DIARIO, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def motor_vivo():
    try:
        req = urllib.request.Request(MOTOR.replace("/v1/chat/completions", "/health"))
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception:
        try:
            perguntar("ok", limite=5)
            return True
        except Exception:
            return False


def motores():
    """Vários motores configurados. Cada Especialista pode usar o que resolve
       melhor o problema dele — é o 'pegar emprestado' aplicado ao motor.
       Formato de ~/sa/motores.json:
         {"padrao": {...}, "codigo": {...}, "busca": {...}}
       Cada um: {"url":"", "chave":"", "modelo":"", "tipo":"openai|gemini"}"""
    caminho = os.path.join(BASE, "motores.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Sem o arquivo, o motor único de sempre vira o padrão
        try:
            with open(os.path.join(BASE, "motor.json"), encoding="utf-8") as f:
                return {"padrao": json.load(f)}
        except Exception:
            return {"padrao": {"url": MOTOR, "modelo": "local"}}


def motor_de(especialista=None):
    """Qual motor este Especialista usa. Cai no padrão se não tiver o dele."""
    M = motores()
    if especialista:
        esp_cfg = carregar_especialistas()
        if esp_cfg:
            e = esp_cfg.todos().get(especialista, {})
            nome = e.get("motor")
            if nome and nome in M:
                return M[nome], nome
    return M.get("padrao", {"url": MOTOR, "modelo": "local"}), "padrao"


def perguntar(texto, limite=700, especialista=None):
    """Fala com o motor. Se o do Especialista falhar, cai no padrão —
       um motor fora do ar não pode derrubar a malha inteira."""
    cfg, nome = motor_de(especialista)
    tentativas = [(cfg, nome)]
    if nome != "padrao":
        tentativas.append((motores().get("padrao", {}), "padrao (reserva)"))

    ultimo_erro = None
    for c, quem in tentativas:
        try:
            url = c.get("url") or MOTOR
            # Gemini fala outro formato
            if c.get("tipo") == "gemini" or "generativelanguage" in url:
                alvo = url if "generateContent" in url else (
                    "https://generativelanguage.googleapis.com/v1beta/models/" +
                    (c.get("modelo") or "gemini-3.5-flash") + ":generateContent")
                if c.get("chave"):
                    alvo += ("&" if "?" in alvo else "?") + "key=" + c["chave"]
                corpo = {"contents": [{"parts": [{"text": texto}]}],
                         "generationConfig": {"temperature": 0.6, "maxOutputTokens": limite * 2}}
                req = urllib.request.Request(alvo, data=json.dumps(corpo).encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    d = json.loads(r.read().decode("utf-8"))
                return "".join(p.get("text", "")
                               for p in d["candidates"][0]["content"]["parts"])

            # formato OpenAI: quase todo o resto
            corpo = {"model": c.get("modelo", "local"),
                     "messages": [{"role": "user", "content": texto}],
                     "max_tokens": limite, "temperature": 0.6, "stream": False}
            cab = {"Content-Type": "application/json"}
            if c.get("chave"):
                cab["Authorization"] = "Bearer " + c["chave"]
            req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"),
                                         headers=cab)
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "choices" in d:
                return d["choices"][0]["message"]["content"]
            return d.get("content", "")
        except Exception as e:
            ultimo_erro = e
            if quem != "padrao (reserva)":
                anotar(f"    motor '{quem}' falhou ({str(e)[:60]}) — tentando o padrão")
    raise ultimo_erro or RuntimeError("nenhum motor respondeu")


def ler_json(caminho, padrao):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def rodar_coletor():
    """Traz o que mudou nas fontes. O funil trabalha sem ninguém olhar."""
    if not os.path.exists(COLETOR):
        return {"ok": False, "msg": "coletor.py não está em ~/"}
    try:
        p = subprocess.run([sys.executable, COLETOR], capture_output=True,
                           text=True, timeout=600)
        saida = p.stdout or ""
        novos = 0
        for linha in saida.splitlines():
            if "total:" in linha:
                try:
                    novos = int(linha.split("total:")[1].split()[0])
                except Exception:
                    pass
        return {"ok": True, "novos": novos, "saida": saida[-600:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": "coletor demorou demais"}
    except Exception as e:
        return {"ok": False, "msg": str(e)[:200]}


def resumo_do_estado():
    """Lê o que o app exportou. Sem isso, o orquestrador trabalha às cegas."""
    e = ler_json(ESTADO, {})
    if not e:
        return None
    imp = e.get("imperio", {}) or {}
    tab = e.get("tabuleiro", {}) or {}
    extras = e.get("extras", []) or []

    pend = [p["t"] for p in imp.get("pendencias", []) if not p.get("ok")]
    marcos = [f"{m['nome']}: {m.get('atual',0)}/{m.get('alvo',0)} {m.get('unidade','')}"
              for m in imp.get("marcos", [])]
    alertas = [a["txt"] for a in tab.get("alertas", [])]
    nao_fazer = [n["txt"] for n in tab.get("naoFazer", [])]
    prazos = [f"{p['txt']} até {p['data']}" for p in tab.get("prazos", []) if not p.get("feito")]
    decisoes = [b["titulo"] for b in extras if b.get("tag") == "DECISÃO"][-6:]
    licoes = [b["corpo"] for b in extras if b.get("tag") in ("LIÇÃO", "CALIBRAGEM")][-5:]

    partes = []
    if marcos:     partes.append("MARCOS: " + " · ".join(marcos))
    if pend:       partes.append("PENDÊNCIAS: " + " · ".join(pend[:8]))
    if alertas:    partes.append("ALERTAS: " + " · ".join(alertas[:5]))
    if prazos:     partes.append("PRAZOS: " + " · ".join(prazos[:5]))
    if nao_fazer:  partes.append("NÃO FAZER: " + " · ".join(nao_fazer[:5]))
    if decisoes:   partes.append("DECIDIU: " + " · ".join(decisoes))
    if licoes:     partes.append("APRENDEU: " + " · ".join(l[:120] for l in licoes))
    return "\n".join(partes)


def ler_coleta_recente(limite=14):
    """O que a coleta trouxe. Prefere a base indexada; cai nos arquivos se ela não existir."""
    itens = consultar_base(limite)
    if itens:
        return itens
    return ler_arquivos_do_dia(limite)


def consultar_base(limite=14):
    """Busca na base: FTS5 mais semântica, com fonte primária pesando mais.
       É o que separa 'li os arquivos de hoje' de 'perguntei à base'."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import base as bd
    except Exception:
        return []
    if not os.path.exists(bd.BANCO):
        return []

    # Busca guiada pelo estado real do projeto, não por termo genérico
    termos = []
    e = ler_json(ESTADO, {})
    imp = e.get("imperio", {}) or {}
    for p in imp.get("pendencias", [])[:4]:
        if not p.get("ok"):
            termos.append(p["t"])
    tab = e.get("tabuleiro", {}) or {}
    for a in tab.get("alertas", [])[:2]:
        termos.append(a["txt"])
    if not termos:
        termos = ["renda recorrente cliente", "ia local motor próprio", "custo infraestrutura"]

    vistos, saida = set(), []
    for t in termos[:5]:
        try:
            for x in bd.buscar(t[:90], n=4):
                if x["id"] in vistos:
                    continue
                vistos.add(x["id"])
                grau = {1: "fonte primária", 2: "especializada"}.get(x["tier"], "agregador")
                marca = " [neutralizado]" if x.get("suspeito") else ""
                saida.append(f"[{x['dominio']} · {grau} · {x['fonte'][:28]}]{marca} "
                             f"{x['titulo'][:110]}")
        except Exception:
            continue
    if saida:
        anotar(f"  base consultada: {len(saida)} itens, guiado por {len(termos)} pendências")
    return saida[:limite]


def ler_arquivos_do_dia(limite=14):
    """Reserva: os arquivos crus do coletor, quando a base ainda não foi montada."""
    raiz = os.path.expanduser("~/biblioteca")
    if not os.path.isdir(raiz):
        return []
    hoje = datetime.now().strftime("%Y-%m-%d")
    itens = []
    for dominio in os.listdir(raiz):
        pasta = os.path.join(raiz, dominio)
        if not os.path.isdir(pasta):
            continue
        arq = os.path.join(pasta, f"{hoje}.json")
        if os.path.exists(arq):
            for it in ler_json(arq, [])[:6]:
                grau = {1: "fonte primária", 2: "especializada"}.get(it.get("tier", 3), "agregador")
                itens.append(f"[{dominio} · {grau}] {it.get('titulo','')[:110]}")
    return itens[:limite]


def atualizar_base():
    """Depois de coletar, joga o que veio para dentro da base e vetoriza o que der."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import base as bd
        bd.criar()
        bd.importar()
        try:
            bd.vetorizar(60)      # aos poucos, para não travar o aparelho
        except Exception:
            anotar("  vetorização pulada (motor ocupado ou sem suporte a embeddings)")
        return True
    except Exception as e:
        anotar(f"  base não atualizou: {str(e)[:120]}")
        return False


def rodada():
    anotar("─── rodada iniciada ───")
    inicio = time.time()
    resultado = {
        "quando": datetime.now(timezone.utc).isoformat(),
        "coleta": None, "leitura": None, "achados": [], "erro": None,
    }

    # 1. Coleta
    c = rodar_coletor()
    resultado["coleta"] = c
    anotar(f"coleta: {c.get('novos', 0)} itens novos" if c["ok"] else f"coleta falhou: {c.get('msg')}")

    # 1b. O que veio entra na base indexada
    if c.get("ok"):
        resultado["base"] = atualizar_base()

    # 2. Motor de pé?
    if not motor_vivo():
        resultado["erro"] = "motor local não respondeu — rode 'motor' no Termux"
        anotar(resultado["erro"])
        salvar(resultado)
        return resultado

    # 3. A malha decide o que sobe
    estado = resumo_do_estado()
    coletados = ler_coleta_recente()

    if not estado and not coletados:
        resultado["erro"] = ("sem estado e sem coleta: exporte o app para "
                             f"{ESTADO} e confira o coletor")
        anotar(resultado["erro"])
        salvar(resultado)
        return resultado

    pergunta = ("O que mudou hoje que exige atenção de Samuel, e o que ele deveria fazer "
                "primeiro? Considere o estado do projeto e o que a coleta trouxe.")

    try:
        m = rodar_malha(pergunta, estado, "\n".join(coletados) or "(nada novo hoje)")
        resultado["malha"] = m["trilha"]
        resultado["achados"] = [
            {"o_que": s.get("o_que", ""),
             "por_que_importa": s.get("por_que_agora", ""),
             "acao": s.get("primeira_acao", ""),
             "filtro": "aprovado pela malha"}
            for s in m.get("sobe", [])][:3]
        resultado["restricao"] = m.get("restricao", "")
        resultado["ruido"] = m.get("represado", "")
        resultado["lacuna"] = m.get("lacuna", "")
        resultado["leitura"] = (
            f"A malha rodou: {len(m['trilha'])} agentes. "
            + (f"{len(resultado['achados'])} coisa(s) subiram pro seu julgamento."
               if resultado["achados"] else "Nada exigiu sua atenção nesta rodada.")
            + (f" Lacuna na base: {m['lacuna']}" if m.get("lacuna") else ""))
        anotar(f"malha concluída: {len(resultado['achados'])} subiram")
    except Exception as e:
        resultado["erro"] = f"a malha falhou: {str(e)[:180]}"
        anotar(resultado["erro"])

    resultado["duracao"] = round(time.time() - inicio, 1)
    salvar(resultado)

    # A cada 6 rodadas (~6 horas), a malha cuida de si mesma: expande onde falta,
    # caça fonte pro que não sabe, audita o Maestro e propõe jogada.
    # Não roda toda hora de propósito — governar custa tokens e tempo.
    try:
        historico = ler_json(PLANTAO, {}).get("historico", [])
        if len(historico) % 6 == 0:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import governanca as gov
            anotar("── hora da governança ──")
            gov.ciclo()
    except Exception as e:
        anotar(f"governança não rodou: {str(e)[:120]}")

    anotar(f"─── rodada concluída em {resultado['duracao']}s ───")
    return resultado


def salvar(resultado):
    os.makedirs(BASE, exist_ok=True)
    historico = ler_json(PLANTAO, {}).get("historico", [])
    historico.append({"quando": resultado["quando"],
                      "achados": len(resultado.get("achados", [])),
                      "erro": resultado.get("erro")})
    with open(PLANTAO, "w", encoding="utf-8") as f:
        json.dump({"atual": resultado, "historico": historico[-30:]},
                  f, ensure_ascii=False, indent=1)


# ─────────────────────────────────────────────
# Servidor: o app busca o plantão aqui
# ─────────────────────────────────────────────
class Entrega(BaseHTTPRequestHandler):
    def _responder(self, dados, codigo=200):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_OPTIONS(self):
        self._responder({})

    def do_GET(self):
        if self.path.startswith("/plantao"):
            self._responder(ler_json(PLANTAO, {"atual": None, "historico": []}))
        elif self.path.startswith("/rodar"):
            self._responder(rodada())
        elif self.path.startswith("/vivo"):
            self._responder({"vivo": True, "motor": motor_vivo(), "quando": agora()})
        else:
            self._responder({"erro": "use /plantao, /rodar ou /vivo"}, 404)

    def do_POST(self):
        # O app manda o estado pra cá, pro orquestrador não trabalhar às cegas
        if self.path.startswith("/estado"):
            n = int(self.headers.get("Content-Length", 0))
            try:
                dados = json.loads(self.rfile.read(n).decode("utf-8"))
                os.makedirs(BASE, exist_ok=True)
                with open(ESTADO, "w", encoding="utf-8") as f:
                    json.dump(dados, f, ensure_ascii=False)
                anotar("estado recebido do app")
                self._responder({"ok": True})
            except Exception as e:
                self._responder({"ok": False, "erro": str(e)[:150]}, 400)
        else:
            self._responder({"erro": "rota desconhecida"}, 404)

    def log_message(self, *a):
        pass


def servir():
    anotar(f"servindo em http://127.0.0.1:{PORTA}")
    print(f"  /plantao  o último plantão")
    print(f"  /rodar    força uma rodada agora")
    print(f"  /vivo     confere se está de pé")
    print(f"  Ctrl+C para parar\n")
    HTTPServer(("127.0.0.1", PORTA), Entrega).serve_forever()


def agendar():
    """Usa o agendador do Android: sobrevive a tela apagada e a reinício."""
    script = os.path.abspath(__file__)
    try:
        subprocess.run([
            "termux-job-scheduler",
            "--script", script,
            "--period-ms", "3600000",        # de hora em hora
            "--persisted", "true",           # continua depois de reiniciar
            "--network", "any",
        ], check=True)
        anotar("agendado: roda de hora em hora, mesmo com a tela apagada")
        print("\n  Para conferir:  termux-job-scheduler --pending")
        print("  Para cancelar:  termux-job-scheduler --cancel-all\n")
    except FileNotFoundError:
        print("\n  Falta o Termux:API. Instale assim:")
        print("    pkg install termux-api")
        print("  E o app Termux:API do F-Droid.\n")
    except subprocess.CalledProcessError as e:
        print(f"\n  O agendador recusou: {e}\n")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if arg == "--servir":
            rodada()
            servir()
        elif arg == "--agendar":
            agendar()
        elif arg == "--status":
            p = ler_json(PLANTAO, None)
            if not p or not p.get("atual"):
                print("Nenhum plantão ainda. Rode: python orquestrador.py")
            else:
                a = p["atual"]
                print(f"\nÚltimo plantão — {a['quando'][:16].replace('T',' ')}")
                print(f"  {a.get('leitura') or a.get('erro') or '(sem leitura)'}\n")
                for x in a.get("achados", []):
                    print(f"  • {x.get('o_que','')}")
                    print(f"    porquê: {x.get('por_que_importa','')}")
                    print(f"    ação:   {x.get('acao','')}\n")
                if a.get("restricao"):
                    print(f"  restrição única: {a['restricao']}\n")
        else:
            rodada()
    except KeyboardInterrupt:
        print("\nparado.")
    except Exception:
        anotar("erro inesperado:\n" + traceback.format_exc()[:600])
        sys.exit(1)
