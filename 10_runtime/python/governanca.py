#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
GOVERNANÇA — a malha cuidando de si mesma

O problema que isto resolve: uma malha fixa perde tudo que não bate com um
gatilho. Aparece assunto novo, ninguém cobre, e a pergunta cai no vazio.

Aqui o Maestro deixa de ser só roteador e passa a governar:

  EXPANSOR    — achou domínio descoberto? Abre Especialista novo, sozinho.
  AUDITOR     — revisa as decisões do próprio Maestro. Quem vigia o vigia.
  MANUTENÇÃO  — varre o sistema, acha o que quebrou, propõe conserto.
  APRENDIZ    — o que deu certo e o que deu errado vira regra permanente.

As travas que impedem isso de virar avalanche:
  · Especialista novo nasce NÃO VERIFICADO e só é confiável depois de provar
  · Teto de especialistas — a malha não cresce sem limite
  · Conserto que mexe em código passa pelo executor, com foto antes
  · Decisão estrutural para e chama Samuel; a máquina não decide sozinha

Uso:
    python governanca.py --ciclo       # roda o ciclo completo
    python governanca.py --expandir    # só procura lacuna e cria
    python governanca.py --auditar     # só revisa o Maestro
    python governanca.py --manutencao  # só varre e propõe conserto
    python governanca.py --aprender    # só destila o aprendizado
    python governanca.py --relatorio   # o que a malha fez por si mesma
"""

import json, os, sys, time
from datetime import datetime, timezone

BASE = os.path.expanduser("~/sa")
LACUNAS = os.path.join(BASE, "lacunas.json")        # domínios que apareceram sem dono
GOVERNO = os.path.join(BASE, "governanca.json")     # o que a malha fez por si
DIARIO = os.path.join(BASE, "governanca.log")

TETO_ESPECIALISTAS = 20      # a malha não cresce sem limite
LACUNA_PRA_CRIAR = 3         # quantas vezes o assunto precisa aparecer antes de virar dono
USOS_PRA_CONFIAR = 5         # chamadas até um NÃO VERIFICADO virar confiável


def agora():
    return datetime.now(timezone.utc).astimezone().strftime("%d/%m %H:%M")


def anotar(msg):
    os.makedirs(BASE, exist_ok=True)
    linha = f"[{agora()}] {msg}"
    print(linha, flush=True)
    with open(DIARIO, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def ler_json(caminho, padrao):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def salvar_json(caminho, dados):
    os.makedirs(BASE, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


def registrar(acao, detalhe, precisa_samuel=False):
    h = ler_json(GOVERNO, [])
    h.append({"quando": datetime.now(timezone.utc).isoformat(), "acao": acao,
              "detalhe": detalhe, "pendente": precisa_samuel})
    salvar_json(GOVERNO, h[-200:])


def carregar(nome):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        return __import__(nome)
    except Exception as e:
        anotar(f"não carreguei {nome}: {str(e)[:100]}")
        return None


def perguntar(prompt, limite=900):
    """Usa o mesmo motor do orquestrador. Ele devolve só o texto."""
    orq = carregar("orquestrador")
    if not orq:
        raise RuntimeError("orquestrador.py não encontrado")
    return orq.perguntar(prompt, limite)


def json_da_resposta(bruto):
    t = bruto.replace("```json", "").replace("```", "").strip()
    i, f = t.find("{"), t.rfind("}")
    if i >= 0 and f > i:
        t = t[i:f + 1]
    return json.loads(t)


# ═══════════════════════════════════════════════════════════
# EXPANSOR — a malha cresce quando precisa
# ═══════════════════════════════════════════════════════════

def anotar_lacuna(assunto, pedido):
    """Chamado pelo orquestrador quando o Maestro diz que ninguém cobre algo."""
    L = ler_json(LACUNAS, {})
    chave = assunto.strip().lower()[:60]
    if chave not in L:
        L[chave] = {"vezes": 0, "exemplos": [], "primeira": datetime.now(timezone.utc).isoformat()}
    L[chave]["vezes"] += 1
    if len(L[chave]["exemplos"]) < 4:
        L[chave]["exemplos"].append(pedido[:160])
    salvar_json(LACUNAS, L)
    return L[chave]["vezes"]


PAPEL_EXPANSOR = """Você é o EXPANSOR da malha de Samuel. Um assunto apareceu várias vezes e
nenhum Especialista cobre bem. Sua função é desenhar o Especialista que faltava.

Regras que não se quebram:
· Escopo FECHADO. "Resolve exatamente ___, nada além." Especialista genérico é inútil.
· Não invada o escopo de quem já existe. Se o assunto na verdade cabe num existente, diga isso
  em vez de criar duplicata.
· Gatilhos são as palavras que Samuel usaria de verdade, não termos técnicos que ele nunca digita.
· O papel diz o que ele faz E o que ele NÃO faz. A segunda parte importa tanto quanto a primeira.

Responda SOMENTE com JSON:
{"criar":true|false,
 "ja_coberto_por":"nome do especialista existente, se for o caso, ou null",
 "id":"nome curto, minúsculo, sem espaço",
 "resolve":"resolve exatamente o quê, uma linha",
 "gatilhos":["palavra","palavra"],
 "papel":"o que faz e o que NÃO faz, 3 a 5 frases",
 "porque":"por que isso merece Especialista próprio"}"""


def expandir():
    esp = carregar("especialistas")
    if not esp:
        return
    L = ler_json(LACUNAS, {})
    maduras = {k: v for k, v in L.items() if v["vezes"] >= LACUNA_PRA_CRIAR}
    if not maduras:
        anotar("expansor: nenhuma lacuna madura ainda")
        return

    atuais = esp.todos()
    if len(atuais) >= TETO_ESPECIALISTAS:
        anotar(f"expansor: teto de {TETO_ESPECIALISTAS} atingido — nenhum novo será criado")
        registrar("teto_atingido", f"{len(atuais)} especialistas; revise antes de crescer mais", True)
        return

    for assunto, dados in list(maduras.items())[:2]:   # no máximo dois por ciclo
        anotar(f"expansor: '{assunto}' apareceu {dados['vezes']}x sem dono")
        existentes = "\n".join(f"· {n}: {e['resolve']}" for n, e in atuais.items())
        p = (PAPEL_EXPANSOR +
             f"\n\nASSUNTO SEM DONO: {assunto}\n"
             f"Apareceu {dados['vezes']} vezes. Exemplos do que Samuel pediu:\n" +
             "\n".join("· " + x for x in dados["exemplos"]) +
             f"\n\nESPECIALISTAS QUE JÁ EXISTEM:\n{existentes}")
        try:
            bruto = perguntar(p)
            r = json_da_resposta(bruto)
        except Exception as e:
            anotar(f"  falhou: {str(e)[:120]}")
            continue

        if not r.get("criar"):
            dono = r.get("ja_coberto_por")
            anotar(f"  não criou — já cabe em '{dono}'")
            registrar("lacuna_resolvida", f"'{assunto}' cabe em {dono}")
            L.pop(assunto, None); salvar_json(LACUNAS, L)
            continue

        ok, msg = esp.abrir_novo(r["id"], r["resolve"], r.get("papel", ""),
                                 r.get("gatilhos", []))
        anotar(f"  {msg}")
        if ok:
            registrar("especialista_criado",
                      f"{r['id']} — {r['resolve']} · motivo: {r.get('porque','')[:100]}")
            L.pop(assunto, None); salvar_json(LACUNAS, L)


# ═══════════════════════════════════════════════════════════
# AUDITOR — quem vigia o Maestro
# ═══════════════════════════════════════════════════════════

PAPEL_AUDITOR = """Você é o AUDITOR. Sua função é revisar as decisões do MAESTRO — o agente que
roteia pedidos e integra respostas na malha de Samuel.

Você não executa nada. Você julga se ele decidiu bem, e o padrão é desconfiar.

Procure especificamente:
· chamou o Especialista errado, ou deixou de chamar quem devia
· deixou subir achado apoiado em fonte fraca
· represou algo que era urgente, ou subiu algo que era ruído
· resolveu contradição entre Especialistas de forma frouxa
· decidiu no lugar de Samuel algo que era decisão dele

Se as decisões estiverem boas, diga. Auditor que só acha defeito é tão inútil quanto o que
nunca acha.

Responda SOMENTE com JSON:
{"nota":0-10,
 "acertos":["o que ele fez bem"],
 "erros":[{"o_que":"","gravidade":"alta|media|baixa","regra_nova":"a regra que evitaria isso"}],
 "veredito":"2 frases"}"""


def auditar():
    plantao = ler_json(os.path.join(BASE, "plantao.json"), {})
    hist = plantao.get("historico", [])
    atual = plantao.get("atual")
    if not atual:
        anotar("auditor: nada pra revisar ainda")
        return

    resumo = json.dumps({"ultima": atual, "rodadas_recentes": hist[-8:]},
                        ensure_ascii=False)[:5000]
    try:
        bruto = perguntar(PAPEL_AUDITOR + "\n\nDECISÕES DO MAESTRO:\n" + resumo)
        r = json_da_resposta(bruto)
    except Exception as e:
        anotar(f"auditor falhou: {str(e)[:120]}")
        return

    nota = r.get("nota", "?")
    anotar(f"auditor: nota {nota} ao Maestro — {r.get('veredito','')[:90]}")

    graves = [e for e in (r.get("erros") or []) if e.get("gravidade") in ("alta", "media")]
    for e in graves:
        anotar(f"  erro: {e.get('o_que','')[:80]}")
        if e.get("regra_nova"):
            virar_calibragem(f"Maestro: {e['regra_nova']}", e.get("o_que", ""))
    registrar("auditoria_maestro",
              f"nota {nota} · {len(graves)} erro(s) grave(s) · {r.get('veredito','')[:120]}",
              precisa_samuel=(isinstance(nota, (int, float)) and nota < 5))


# ═══════════════════════════════════════════════════════════
# MANUTENÇÃO — varre, acha o que quebrou, propõe conserto
# ═══════════════════════════════════════════════════════════

def diagnostico_bruto():
    """O que a máquina consegue medir sozinha, sem opinião."""
    d = {"quando": agora()}

    esp = carregar("especialistas")
    if esp:
        saude = esp.diagnostico()
        d["especialistas"] = {
            "total": len(saude),
            "sem_uso": [x["nome"] for x in saude if x["estado"] == "sem uso"],
            "recalibrar": [x["nome"] for x in saude if x["estado"] == "RECALIBRAR"],
            "refazer": [x["nome"] for x in saude if x["estado"] == "REFAZER"],
        }

    jt = carregar("jetro")
    if jt:
        try:
            _, achados, carga = jt.auditar()
            d["matriz"] = {"riscos": len(achados),
                           "altos": len([a for a in achados if a["grau"] == "alto"]),
                           "carga": carga}
        except Exception:
            pass

    try:
        bd = carregar("base")
        if bd and os.path.exists(bd.BANCO):
            c = bd.conectar()
            d["base"] = {
                "itens": c.execute("SELECT COUNT(*) n FROM itens").fetchone()["n"],
                "buscas_vazias": c.execute(
                    "SELECT COUNT(*) n FROM buscas WHERE achados = 0").fetchone()["n"],
            }
            c.close()
    except Exception:
        pass

    L = ler_json(LACUNAS, {})
    d["lacunas_abertas"] = len(L)

    p = ler_json(os.path.join(BASE, "plantao.json"), {})
    h = p.get("historico", [])
    d["rodadas"] = {"total": len(h),
                    "com_erro": len([x for x in h if x.get("erro")])}
    return d


PAPEL_MANUTENCAO = """Você é a MANUTENÇÃO do sistema de Samuel. Recebe a medição bruta e decide
o que está quebrado e o que fazer.

Você propõe conserto; não executa nada sozinho. Separe com clareza:
· o que a própria malha resolve (recalibrar especialista, ajustar gatilho, abrir novo)
· o que exige Samuel (mapear um contador, decidir gasto, preencher posição crítica vaga)

Não invente problema pra parecer útil. Se o sistema está saudável, diga que está.
Prioridade sempre pela restrição única: o que trava mais coisa vem primeiro.

Responda SOMENTE com JSON:
{"saude_geral":"boa|atencao|ruim",
 "consertos_automaticos":[{"o_que":"","como":"","urgencia":"alta|media|baixa"}],
 "precisa_samuel":[{"o_que":"","porque":"","primeira_acao":""}],
 "restricao_unica":"o gargalo que trava mais coisa agora",
 "veredito":"2 frases"}"""


def manutencao():
    d = diagnostico_bruto()
    anotar("manutenção: medindo o sistema…")
    try:
        bruto = perguntar(PAPEL_MANUTENCAO + "\n\nMEDIÇÃO:\n" +
                             json.dumps(d, ensure_ascii=False, indent=1))
        r = json_da_resposta(bruto)
    except Exception as e:
        anotar(f"manutenção falhou: {str(e)[:120]}")
        return

    anotar(f"manutenção: saúde {r.get('saude_geral','?')} — {r.get('veredito','')[:80]}")

    for c in (r.get("consertos_automaticos") or []):
        if c.get("urgencia") == "alta":
            anotar(f"  conserto: {c.get('o_que','')[:70]}")
            registrar("conserto_proposto", f"{c.get('o_que','')} → {c.get('como','')}")

    pend = r.get("precisa_samuel") or []
    for p in pend:
        anotar(f"  ↑ Samuel: {p.get('o_que','')[:70]}")
        registrar("precisa_samuel",
                  f"{p.get('o_que','')} · porque: {p.get('porque','')} · "
                  f"primeiro passo: {p.get('primeira_acao','')}", precisa_samuel=True)

    if r.get("restricao_unica"):
        registrar("restricao_unica", r["restricao_unica"])
    return r


# ═══════════════════════════════════════════════════════════
# APRENDIZ — o que aconteceu vira regra
# ═══════════════════════════════════════════════════════════

def virar_calibragem(titulo, corpo):
    """Grava no formato que o app lê — a calibragem entra na memória de verdade."""
    caminho = os.path.join(BASE, "calibragens-da-malha.json")
    lista = ler_json(caminho, [])
    lista.append({"id": "cal-" + str(int(time.time() * 1000)),
                  "tag": "CALIBRAGEM", "titulo": titulo[:90], "corpo": corpo[:600],
                  "origem": "governança automática"})
    salvar_json(caminho, lista[-60:])
    anotar(f"  calibragem gravada: {titulo[:60]}")


PAPEL_APRENDIZ = """Você é o APRENDIZ. Olha o que o sistema fez nas últimas rodadas e extrai a
regra que evita repetir erro — ou que repete o acerto de propósito.

Uma boa calibragem é específica e acionável. "Ser mais cuidadoso" não serve.
"Achado de fonte agregadora não sobe sem cruzar com fonte primária" serve.

Não invente lição. Se as rodadas não ensinam nada novo, diga que não ensinam.

Responda SOMENTE com JSON:
{"aprendeu":true|false,
 "calibragens":[{"titulo":"","corpo":"o erro que aconteceu e a regra pra não repetir"}],
 "porque":"1 frase"}"""


def aprender():
    gov = ler_json(GOVERNO, [])[-25:]
    plantao = ler_json(os.path.join(BASE, "plantao.json"), {})
    if not gov:
        anotar("aprendiz: histórico curto demais")
        return
    material = json.dumps({"governanca": gov,
                           "ultimo_plantao": plantao.get("atual", {})},
                          ensure_ascii=False)[:5000]
    try:
        bruto = perguntar(PAPEL_APRENDIZ + "\n\nO QUE ACONTECEU:\n" + material)
        r = json_da_resposta(bruto)
    except Exception as e:
        anotar(f"aprendiz falhou: {str(e)[:120]}")
        return

    if not r.get("aprendeu"):
        anotar(f"aprendiz: nada novo — {r.get('porque','')[:70]}")
        return
    for c in (r.get("calibragens") or [])[:3]:
        virar_calibragem(c.get("titulo", ""), c.get("corpo", ""))
    registrar("aprendizado", f"{len(r.get('calibragens') or [])} calibragem(ns) nova(s)")


# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# CAÇADOR DE FONTES — o sistema vai atrás do que não sabe
#
# O [PESQUISA] reporta lacuna: "não sei quanto clínicas pagam por automação".
# Isso não some. Vira busca por uma fonte que responda, e a fonte entra
# no coletor — daí em diante o dado chega sozinho, toda hora.
# ═══════════════════════════════════════════════════════════

LACUNAS_DADO = os.path.join(BASE, "lacunas-dado.json")
FONTES_PROPRIAS = os.path.join(BASE, "fontes-proprias.json")
TETO_FONTES = 40


def anotar_lacuna_dado(o_que_falta, contexto=""):
    L = ler_json(LACUNAS_DADO, {})
    chave = o_que_falta.strip().lower()[:80]
    if chave not in L:
        L[chave] = {"vezes": 0, "contexto": contexto[:200],
                    "primeira": datetime.now(timezone.utc).isoformat()}
    L[chave]["vezes"] += 1
    salvar_json(LACUNAS_DADO, L)
    return L[chave]["vezes"]


PAPEL_CACADOR = """Você é o CAÇADOR DE FONTES da malha de Samuel. Existe um dado que o sistema
precisa e não tem. Sua função é descobrir DE ONDE esse dado vem — de forma que chegue sozinho,
todo dia, sem ninguém buscar de novo.

O que serve como fonte, em ordem de preferência:
1. RSS ou Atom de instituição que produz o dado (banco central, órgão, universidade, empresa)
2. API pública sem chave e sem cadastro
3. Blog oficial de quem gera a informação

O que NÃO serve, e você não deve propor:
· agregador de opinião como se fosse fato
· site que exige login, cadastro ou chave paga
· busca em mecanismo de pesquisa — isso não é assinatura, é consulta
· endereço que você não tem certeza que existe: é melhor dizer que não sabe

Grau da fonte: 1 = a instituição que produz o dado · 2 = especializada no assunto ·
3 = agregador. Seja honesto: chamar agregador de primária envenena a base inteira.

Responda SOMENTE com JSON:
{"achou":true|false,
 "fontes":[{"nome":"","url":"endereço completo do feed ou API","tipo":"rss|json",
            "tier":1|2|3,"dominio":"ia|financas|negocios|tendencias|clinicas|programacao|sistemas",
            "porque":"que pergunta isso responde"}],
 "nao_achou_porque":"se não achou, o motivo — e o que Samuel teria que buscar à mão"}"""


def cacar_fontes():
    L = ler_json(LACUNAS_DADO, {})
    maduras = {k: v for k, v in L.items() if v["vezes"] >= 2}
    if not maduras:
        anotar("caçador: nenhuma lacuna de dado madura")
        return

    proprias = ler_json(FONTES_PROPRIAS, {})
    total = sum(len(v) for v in proprias.values())
    if total >= TETO_FONTES:
        anotar(f"caçador: teto de {TETO_FONTES} fontes próprias — não vou crescer mais")
        registrar("teto_fontes", f"{total} fontes descobertas; revise antes de crescer", True)
        return

    for falta, dados in list(maduras.items())[:2]:
        anotar(f"caçador: procurando fonte para '{falta[:60]}'")
        p = (PAPEL_CACADOR +
             f"\n\nDADO QUE FALTA: {falta}\n"
             f"Apareceu {dados['vezes']} vezes. Contexto: {dados.get('contexto','')}\n\n"
             "Proponha no máximo 2 fontes. Se não souber de nenhuma que exista de verdade, "
             "responda achou:false — chutar endereço quebra o coletor.")
        try:
            bruto = perguntar(p)
            r = json_da_resposta(bruto)
        except Exception as e:
            anotar(f"  falhou: {str(e)[:120]}")
            continue

        if not r.get("achou"):
            anotar(f"  não achou: {r.get('nao_achou_porque','')[:90]}")
            registrar("fonte_nao_encontrada",
                      f"'{falta[:60]}' — {r.get('nao_achou_porque','')[:120]}", True)
            L.pop(falta, None); salvar_json(LACUNAS_DADO, L)
            continue

        novas = 0
        for f in (r.get("fontes") or [])[:2]:
            if not f.get("url", "").startswith("http"):
                continue
            dom = f.get("dominio", "tendencias")
            proprias.setdefault(dom, [])
            if any(x.get("url") == f["url"] for x in proprias[dom]):
                continue
            # Nasce ATIVA mas marcada: se não trouxer nada, a manutenção percebe.
            proprias[dom].append({
                "nome": f.get("nome", "fonte nova")[:70],
                "url": f["url"], "tipo": f.get("tipo", "rss"),
                "tier": int(f.get("tier", 3)), "ativo": True,
                "descoberta": datetime.now(timezone.utc).isoformat(),
                "porque": f.get("porque", "")[:150],
            })
            novas += 1
            anotar(f"  + {f.get('nome','')[:50]} (grau {f.get('tier',3)}) → {dom}")

        if novas:
            salvar_json(FONTES_PROPRIAS, proprias)
            registrar("fontes_descobertas",
                      f"{novas} fonte(s) para '{falta[:50]}' — o dado passa a chegar sozinho")
            L.pop(falta, None); salvar_json(LACUNAS_DADO, L)


def podar_fontes():
    """Fonte que não traz nada há dias é peso morto. Desliga, não apaga —
       realocar antes de descartar, como manda o método."""
    proprias = ler_json(FONTES_PROPRIAS, {})
    if not proprias:
        return
    mudou = 0
    limite = time.time() - 7 * 86400
    for dom, lista in proprias.items():
        for f in lista:
            if not f.get("ativo"):
                continue
            try:
                nasceu = datetime.fromisoformat(f["descoberta"]).timestamp()
            except Exception:
                continue
            if nasceu < limite and f.get("trouxe", 0) == 0:
                f["ativo"] = False
                f["desligada_em"] = datetime.now(timezone.utc).isoformat()
                mudou += 1
                anotar(f"  fonte desligada por não trazer nada: {f['nome'][:50]}")
    if mudou:
        salvar_json(FONTES_PROPRIAS, proprias)
        registrar("fontes_podadas", f"{mudou} fonte(s) desligada(s) por 7 dias sem trazer nada")


# ═══════════════════════════════════════════════════════════
# ESTRATEGISTA — deixa de relatar e passa a propor movimento
# ═══════════════════════════════════════════════════════════

PAPEL_ESTRATEGISTA = """Você é o ESTRATEGISTA da malha de Samuel. Os outros agentes coletam,
filtram e consertam. Você faz outra coisa: olha o acumulado e propõe MOVIMENTO.

Samuel está em CLT, tem cerca de 3 horas por dia, e o Marco 1 é R$5.000/mês recorrentes para
sair do emprego. Hoje não há cliente pagando — essa é a restrição única, e tudo que não ataca
ela é otimização da parte errada.

O que você entrega não é análise. É jogada:
· o que fazer nos próximos 7 dias, que caiba em 3 horas por dia
· por que agora e não depois
· qual dado da base sustenta isso — se nenhum sustenta, diga que é aposta
· o que essa jogada cria de problema depois, e o começo do plano pra isso

Nunca entregue caminho único quando existem vários. Mostre o custo real de cada um: tempo,
dinheiro, atenção. Quem escolhe é Samuel — você não fecha decisão por ele.

Não repita o que ele já sabe. Se a base não trouxe nada que mude o quadro, diga isso em uma
frase e não invente movimento pra parecer útil.

Responda SOMENTE com JSON:
{"mudou_algo":true|false,
 "leitura":"o que o acumulado desta semana diz, em 2 a 3 frases",
 "jogadas":[{"o_que":"","por_que_agora":"","custo":"tempo e dinheiro reais",
             "apoiado_em":"o dado que sustenta, ou 'aposta'","cria_depois":"o problema que gera"}],
 "descartado":"o que você considerou e não vale, em 1 frase",
 "pergunta_aberta":"a coisa que Samuel precisa decidir e só ele pode"}"""


def estrategista():
    """Junta tudo que o sistema sabe e propõe jogada — não relatório."""
    material = {"quando": agora()}

    # o que a base aprendeu de mais relevante
    try:
        bd = carregar("base")
        if bd and os.path.exists(bd.BANCO):
            c = bd.conectar()
            recentes = c.execute(
                "SELECT titulo, fonte, tier, dominio FROM itens "
                "ORDER BY id DESC LIMIT 25").fetchall()
            material["coletado_recente"] = [
                {"t": r["titulo"][:110], "fonte": r["fonte"][:40],
                 "grau": r["tier"], "dominio": r["dominio"]} for r in recentes]
            material["total_base"] = c.execute(
                "SELECT COUNT(*) n FROM itens").fetchone()["n"]
            c.close()
    except Exception:
        pass

    # o estado real do projeto
    orq = carregar("orquestrador")
    if orq:
        try:
            material["estado"] = orq.resumo_do_estado()
        except Exception:
            pass

    # o que a governança viu
    material["governanca"] = ler_json(GOVERNO, [])[-12:]

    anotar("estrategista: lendo o acumulado…")
    try:
        bruto = perguntar(PAPEL_ESTRATEGISTA + "\n\nO QUE O SISTEMA ACUMULOU:\n" +
                             json.dumps(material, ensure_ascii=False)[:6000], limite=1200)
        r = json_da_resposta(bruto)
    except Exception as e:
        anotar(f"estrategista falhou: {str(e)[:120]}")
        return None

    if not r.get("mudou_algo"):
        anotar(f"estrategista: nada mudou o quadro — {r.get('leitura','')[:80]}")
        return r

    anotar(f"estrategista: {len(r.get('jogadas') or [])} jogada(s) propostas")
    for j in (r.get("jogadas") or [])[:3]:
        anotar(f"  · {j.get('o_que','')[:70]}")
    registrar("estrategia",
              r.get("leitura", "")[:150] + " · " +
              " | ".join(j.get("o_que", "")[:60] for j in (r.get("jogadas") or [])[:2]),
              precisa_samuel=True)

    # A estratégia entra no plantão — é o que Samuel vê ao abrir o app
    p = ler_json(os.path.join(BASE, "plantao.json"), {"atual": None, "historico": []})
    p["estrategia"] = {"quando": datetime.now(timezone.utc).isoformat(), **r}
    salvar_json(os.path.join(BASE, "plantao.json"), p)
    return r


# ═══════════════════════════════════════════════════════════

def ciclo():
    anotar("═══ ciclo de governança ═══")
    expandir()
    cacar_fontes()
    podar_fontes()
    manutencao()
    auditar()
    estrategista()
    aprender()
    anotar("═══ fim do ciclo ═══")


def relatorio():
    g = ler_json(GOVERNO, [])
    if not g:
        print("\nA malha ainda não fez nada por si mesma.\n")
        return
    pend = [x for x in g if x.get("pendente")]
    print(f"\n╔═══ O QUE A MALHA FEZ POR SI MESMA ═══")
    print(f"║  {len(g)} ações registradas · {len(pend)} esperando você")
    print("║")
    tipos = {}
    for x in g:
        tipos[x["acao"]] = tipos.get(x["acao"], 0) + 1
    for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"║    {t}: {n}")
    print("║")
    if pend:
        print("║  ESPERANDO SUA DECISÃO:")
        for x in pend[-6:]:
            print(f"║    · {x['detalhe'][:100]}")
        print("║")
    print("║  ÚLTIMAS AÇÕES:")
    for x in g[-8:]:
        q = x["quando"][5:16].replace("T", " ")
        print(f"║    {q}  {x['acao']}: {x['detalhe'][:70]}")
    print("╚═══\n")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--relatorio"
    if arg == "--ciclo":         ciclo()
    elif arg == "--expandir":    expandir()
    elif arg == "--auditar":     auditar()
    elif arg == "--manutencao":  manutencao()
    elif arg == "--aprender":    aprender()
    elif arg == "--fontes":      cacar_fontes()
    elif arg == "--estrategia":  estrategista()
    elif arg == "--relatorio":   relatorio()
    else:                        print(__doc__)
