#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COLETOR — Sistema Absoluto
Funil de captura: fonte -> filtro -> formato -> destino.

Roda no Termux, no celular, sem instalar nada além do Python.
Sem chave de API, sem cartão, sem custo. Só fontes abertas e legítimas.

Uso:
    python coletor.py              # coleta só o que está ATIVO
    python coletor.py --status     # mostra o mapa completo, ativo e represado
    python coletor.py --memoria    # gera bloco de memória pro app
"""

import hashlib
import json, os, sys, re, time, hashlib
import urllib.request
import urllib.parse, urllib.error
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

# ──────────────────────────────────────────────────────────────
# MAPA DE FONTES — ABERTURA TOTAL
# Toda porta fica cadastrada. "ativo" controla só a vazão de agora.
# Ligar uma fonte represada = trocar False por True. Sem retrabalho.
# ──────────────────────────────────────────────────────────────

FONTES = {
    "mundo": [
        # ── GDELT: notícia de ~100 países, traduzida automaticamente. A porta principal.
        {"nome": "GDELT — mundo, últimas 24h", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(world%20OR%20government%20OR%20policy)%20sourcelang:english&mode=artlist&maxrecords=25&format=json&timespan=24h",
         "ativo": True},
        {"nome": "GDELT — economia global", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(economy%20OR%20inflation%20OR%20trade)&mode=artlist&maxrecords=25&format=json&timespan=24h",
         "ativo": True},
        {"nome": "GDELT — inteligência artificial no mundo", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(%22artificial%20intelligence%22)&mode=artlist&maxrecords=25&format=json&timespan=24h",
         "ativo": True},
        # Idiomas específicos — ligar conforme a necessidade
        {"nome": "GDELT — em chinês", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(%E6%94%BF%E5%BA%9C)%20sourcelang:chinese&mode=artlist&maxrecords=20&format=json&timespan=24h",
         "ativo": False},
        {"nome": "GDELT — em russo", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(%D0%BF%D1%80%D0%B0%D0%B2%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D1%81%D1%82%D0%B2%D0%BE)%20sourcelang:russian&mode=artlist&maxrecords=20&format=json&timespan=24h",
         "ativo": False},
        {"nome": "GDELT — em árabe", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(%D8%AD%D9%83%D9%88%D9%85%D8%A9)%20sourcelang:arabic&mode=artlist&maxrecords=20&format=json&timespan=24h",
         "ativo": False},
        {"nome": "GDELT — em espanhol", "tier": 2, "tipo": "gdelt",
         "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=(gobierno)%20sourcelang:spanish&mode=artlist&maxrecords=20&format=json&timespan=24h",
         "ativo": False},
    ],
    "ciencia": [
        # ── OpenAlex: ~250 milhões de trabalhos científicos, todo país, toda língua
        {"nome": "OpenAlex — trabalhos recentes de IA", "tier": 1, "tipo": "openalex",
         "url": "https://api.openalex.org/works?filter=concepts.id:C154945302&sort=publication_date:desc&per-page=20",
         "ativo": True},
        {"nome": "OpenAlex — mais citados do ano", "tier": 1, "tipo": "openalex",
         "url": "https://api.openalex.org/works?filter=from_publication_date:2026-01-01&sort=cited_by_count:desc&per-page=20",
         "ativo": False},
        {"nome": "Europe PMC — biomédica mundial", "tier": 1, "tipo": "json",
         "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=machine%20learning&format=json&pageSize=20",
         "campos": {"lista": "resultList", "titulo": "title", "corpo": "abstractText"},
         "ativo": False},
        {"nome": "DOAJ — periódicos abertos, todas as línguas", "tier": 1, "tipo": "json",
         "url": "https://doaj.org/api/search/articles/artificial%20intelligence?pageSize=20",
         "campos": {"lista": "results", "titulo": "title", "corpo": "abstract"},
         "ativo": False},
    ],
    "referencia": [
        # ── Wikipédia: dicionário do mundo, uma entrada por língua
        {"nome": "Wikipédia PT", "tier": 2, "tipo": "wikipedia", "idioma": "pt",
         "url": "https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch=intelig%C3%AAncia%20artificial&srlimit=15&format=json",
         "ativo": True},
        {"nome": "Wikipédia EN", "tier": 2, "tipo": "wikipedia", "idioma": "en",
         "url": "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=artificial%20intelligence&srlimit=15&format=json",
         "ativo": False},
        {"nome": "Wikipédia ZH", "tier": 2, "tipo": "wikipedia", "idioma": "zh",
         "url": "https://zh.wikipedia.org/w/api.php?action=query&list=search&srsearch=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&srlimit=15&format=json",
         "ativo": False},
    ],
    "global_economia": [
        {"nome": "Banco Mundial — indicadores globais", "tier": 1, "tipo": "json",
         "url": "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=20&mrnev=1",
         "campos": {"lista": None, "titulo": "country", "corpo": "value"},
         "ativo": False, "nota": "Resposta vem em lista dupla; confirmar formato no primeiro uso."},
    ],
    "ia": [
        {"nome": "arXiv — IA e aprendizado de máquina", "tier": 1, "tipo": "arxiv",
         "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=15",
         "ativo": True},
        {"nome": "Hugging Face — modelos em alta", "tier": 1, "tipo": "json",
         "url": "https://huggingface.co/api/models?sort=trendingScore&limit=15",
         "campos": {"titulo": "id", "extra": "downloads"},
         "ativo": True},
        {"nome": "Google Research — blog", "tier": 1, "tipo": "rss",
         "url": "https://research.google/blog/rss/", "ativo": True},
        {"nome": "arXiv — papers profundos de treinamento", "tier": 1, "tipo": "arxiv",
         "url": "http://export.arxiv.org/api/query?search_query=cat:cs.NE&max_results=15",
         "ativo": False},
    ],
    "programacao": [
        {"nome": "GitHub — repositórios de IA em alta", "tier": 1, "tipo": "json",
         "url": "https://api.github.com/search/repositories?q=topic:ai+pushed:>2026-01-01&sort=stars&order=desc&per_page=15",
         "campos": {"lista": "items", "titulo": "full_name", "corpo": "description", "extra": "stargazers_count"},
         "ativo": True},
        {"nome": "Python — anúncios oficiais", "tier": 1, "tipo": "rss",
         "url": "https://blog.python.org/feeds/posts/default", "ativo": True},
        {"nome": "Hacker News — front page", "tier": 3, "tipo": "hn", "url": "top", "ativo": True},
        {"nome": "Rust / Go / C++", "tier": 1, "tipo": "rss",
         "url": "https://blog.rust-lang.org/feed.xml", "ativo": False},
    ],
    "sistemas": [
        {"nome": "Linux Kernel — novidades", "tier": 1, "tipo": "rss",
         "url": "https://www.kernel.org/feeds/kdist.xml", "ativo": False},
    ],
    "celular": [
        {"nome": "llama.cpp — releases", "tier": 1, "tipo": "json",
         "url": "https://api.github.com/repos/ggerganov/llama.cpp/releases?per_page=5",
         "campos": {"titulo": "tag_name", "corpo": "name"},
         "ativo": True},
        {"nome": "Termux — releases", "tier": 1, "tipo": "json",
         "url": "https://api.github.com/repos/termux/termux-app/releases?per_page=5",
         "campos": {"titulo": "tag_name", "corpo": "name"},
         "ativo": False},
    ],
    "computador": [
        {"nome": "Hardware — benchmarks pra IA local", "tier": 2, "tipo": "rss",
         "url": "https://www.phoronix.com/rss.php", "ativo": False},
    ],
    "financas": [
        {"nome": "Banco Central — SELIC e câmbio", "tier": 1, "tipo": "bcb", "url": "", "ativo": True},
        {"nome": "Câmbio BRL — Banco Central Europeu", "tier": 1, "tipo": "json",
         "url": "https://api.frankfurter.dev/v1/latest?base=BRL&symbols=USD,EUR,GBP",
         "campos": {"dict": "rates"},
         "ativo": True},
        {"nome": "Cripto — day trade e execução", "tier": 2, "tipo": "json",
         "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=brl",
         "ativo": False},
    ],
    "tendencias": [
        {"nome": "Hacker News — o que sobe hoje", "tier": 3, "tipo": "hn", "url": "best", "ativo": True},
    ],
    "negocios": [
        {"nome": "IBGE — indicadores do Brasil", "tier": 1, "tipo": "json",
         "url": "https://servicodados.ibge.gov.br/api/v3/agregados",
         "ativo": False},
    ],
    "clinicas": [
        {"nome": "Excel e PPT do cliente — entrada manual", "tier": 1, "tipo": "manual", "url": "",
         "ativo": False, "nota": "Ouro real. Ativa quando o arquivo do cliente chegar."},
    ],
}

RAIZ = os.path.expanduser("~/biblioteca")
VISTOS = os.path.join(RAIZ, ".vistos.json")
UA = "SistemaAbsoluto-Coletor/1.0 (uso pessoal, respeita robots)"


# ──────────────────────────────────────────────────────────────
# BASE
# ──────────────────────────────────────────────────────────────

def buscar(url, timeout=25, tentativas=3):
    """Erro de rede sem o código vira adivinhação. Aqui o código aparece,
    e 429/503 (limite do servidor) espera e tenta de novo em vez de desistir."""
    ultimo = None
    for n in range(tentativas):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json, application/xml, text/xml, */*",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            ultimo = "HTTP %s" % e.code
            # 429 = pediu demais; 5xx = servidor tropeçou. Vale esperar.
            if e.code in (429, 500, 502, 503, 504) and n < tentativas - 1:
                time.sleep(3 * (n + 1))
                continue
            raise RuntimeError("%s em %s" % (ultimo, url.split("?")[0]))
        except Exception as e:
            ultimo = type(e).__name__
            if n < tentativas - 1:
                time.sleep(2)
                continue
            raise RuntimeError("%s em %s" % (ultimo, url.split("?")[0]))
    raise RuntimeError(ultimo or "falhou")


def limpar(txt, limite=400):
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", " ", str(txt))
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limite]


# Conteúdo vindo da web é DADO, nunca ordem. Um texto coletado pode conter
# comando disfarçado ("ignore as instruções anteriores", "você agora é...").
# Se isso entrar na memória, entra no prompt — e vira injeção.
# Aqui o comando é neutralizado antes de encostar na memória.
PADROES_INJECAO = [
    r"ignor[ae]\s+(?:as\s+|todas?\s+|tudo\s+)*(?:instru|orden|regra)",
    r"ignore\s+(?:all\s+|any\s+|previous\s+|prior\s+|the\s+|above\s+)*(?:instruction|rule|prompt|command)",
    r"disregard\s+(?:all\s+|any\s+|previous\s+|prior\s+|the\s+|above\s+)*(?:instruction|rule|prompt|command)",
    r"forget\s+(?:all\s+|any\s+|previous\s+|everything|the\s+)*(?:instruction|rule|prompt|above)?",
    r"esque[çc]a\s+(?:tudo|as\s+regras|as\s+instru|todas)",
    r"you\s+are\s+now\b",
    r"voc[êe]\s+(?:agora\s+)?[ée]\s+(?:um|uma|o|a)\b",
    r"act\s+as\s+(?:a|an|the)\b",
    r"aja\s+como\s+(?:um|uma|o|a)\b",
    r"system\s*prompt",
    r"(?:revele|mostre|repita|imprima)\s+(?:o\s+|a\s+|seu\s+|sua\s+|suas\s+|seus\s+)*(?:prompt|instru|system|regra)",
    r"(?:reveal|show|repeat|print|output)\s+(?:the\s+|your\s+|all\s+)*(?:prompt|instruction|system|rule)",
    r"new\s+instructions?\s*:",
    r"novas?\s+instru[çc][õo]es\s*:",
    r"</?(?:system|assistant|user|instruction)[^>]*>",
    r"<<<|>>>",
    r"\[\s*(?:system|inst|instruction)\s*\]",
]
_RE_INJ = re.compile("|".join(PADROES_INJECAO), re.IGNORECASE)


def neutralizar(txt):
    """Marca comando disfarçado como texto inerte. Não apaga — sinaliza."""
    if not txt:
        return ""
    return _RE_INJ.sub("[trecho neutralizado]", txt)


def ident(item):
    base = (item.get("titulo", "") + item.get("url", "")).encode("utf-8")
    return hashlib.sha1(base).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────
# PARSERS — um por tipo de fonte
# ──────────────────────────────────────────────────────────────

def ler_rss(url):
    raiz = ET.fromstring(buscar(url))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    itens = []

    for it in raiz.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        def campo(*nomes):
            for n in nomes:
                el = it.find(n) if "}" not in n else it.find(n, ns)
                if el is None:
                    for filho in it:
                        if filho.tag.split("}")[-1] == n:
                            el = filho
                            break
                if el is not None:
                    return el.get("href") or el.text or ""
            return ""
        itens.append({
            "titulo": limpar(campo("title"), 200),
            "corpo": limpar(campo("description", "summary", "content")),
            "url": limpar(campo("link"), 300),
        })
        if len(itens) >= 15:
            break
    return itens


def ler_arxiv(url):
    raiz = ET.fromstring(buscar(url))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    itens = []
    for e in raiz.findall("a:entry", ns):
        t = e.find("a:title", ns)
        s = e.find("a:summary", ns)
        l = e.find("a:id", ns)
        itens.append({
            "titulo": limpar(t.text if t is not None else "", 200),
            "corpo": limpar(s.text if s is not None else ""),
            "url": limpar(l.text if l is not None else "", 300),
        })
    return itens


def ler_json(fonte):
    dados = json.loads(buscar(fonte["url"]))
    c = fonte.get("campos", {})

    if c.get("dict"):
        d = dados.get(c["dict"], dados)
        return [{"titulo": f"{k}: {v}", "corpo": "", "url": fonte["url"]} for k, v in d.items()]

    lista = dados.get(c["lista"], []) if c.get("lista") else dados
    if not isinstance(lista, list):
        lista = [lista]

    itens = []
    for o in lista[:15]:
        if not isinstance(o, dict):
            continue
        titulo = str(o.get(c.get("titulo", "name"), ""))[:200]
        corpo = limpar(o.get(c.get("corpo", "description"), ""))
        extra = o.get(c.get("extra", ""), "")
        if extra:
            corpo = f"[{extra}] {corpo}".strip()
        itens.append({
            "titulo": titulo,
            "corpo": corpo,
            "url": o.get("html_url") or o.get("url") or fonte["url"],
        })
    return itens


def ler_hn(qual):
    ids = json.loads(buscar(f"https://hacker-news.firebaseio.com/v0/{qual}stories.json"))[:12]
    itens = []
    for i in ids:
        try:
            o = json.loads(buscar(f"https://hacker-news.firebaseio.com/v0/item/{i}.json"))
            itens.append({
                "titulo": limpar(o.get("title", ""), 200),
                "corpo": f"[{o.get('score', 0)} pontos]",
                "url": o.get("url") or f"https://news.ycombinator.com/item?id={i}",
            })
            time.sleep(0.1)
        except Exception:
            continue
    return itens


def ler_bcb():
    """Banco Central do Brasil — série histórica aberta, sem chave."""
    series = {"SELIC meta": 432, "IPCA mensal": 433, "Dólar PTAX venda": 1}
    itens = []
    for nome, cod in series.items():
        try:
            url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}"
                   f"/dados/ultimos/1?formato=json")
            d = json.loads(buscar(url))
            if d:
                itens.append({
                    "titulo": f"{nome}: {d[-1].get('valor')}",
                    "corpo": f"data {d[-1].get('data')}",
                    "url": url,
                })
        except Exception as e:
            itens.append({"titulo": f"{nome}: falhou", "corpo": str(e)[:100], "url": ""})
    return itens



def ler_gdelt(fonte):
    """GDELT monitora notícia de ~100 países e traduz o que não é inglês.
    Cada item já vem com o idioma e o país de origem — é a porta do 'mundo inteiro'."""
    # GDELT devolve o nome da língua por extenso; a memória guarda o código ISO
    ISO = {"english":"en","portuguese":"pt","spanish":"es","chinese":"zh","russian":"ru",
           "arabic":"ar","french":"fr","german":"de","japanese":"ja","korean":"ko",
           "italian":"it","hindi":"hi","turkish":"tr","dutch":"nl","persian":"fa",
           "indonesian":"id","vietnamese":"vi","thai":"th","hebrew":"he","polish":"pl",
           "ukrainian":"uk","swedish":"sv","greek":"el","bengali":"bn","urdu":"ur"}
    dados = json.loads(buscar(fonte["url"]))
    itens = []
    for o in dados.get("articles", [])[:20]:
        bruto = (o.get("language") or "").strip().lower()
        idioma = ISO.get(bruto, bruto[:2] if bruto else "—")
        pais = o.get("sourcecountry") or ""
        itens.append({
            "titulo": limpar(o.get("title", ""), 200),
            "corpo": limpar(f"{pais} · {o.get('domain','')}", 300),
            "url": o.get("url", ""),
            "idioma": idioma,
        })
    return itens


def ler_openalex(fonte):
    """OpenAlex indexa produção científica do mundo todo, sem chave e sem limite prático."""
    dados = json.loads(buscar(fonte["url"]))
    itens = []
    for o in dados.get("results", [])[:20]:
        # o resumo vem como índice invertido; remonta na ordem
        inv = o.get("abstract_inverted_index") or {}
        resumo = ""
        if inv:
            pos = {}
            for palavra, ondes in inv.items():
                for p in ondes:
                    pos[p] = palavra
            resumo = " ".join(pos[k] for k in sorted(pos))
        itens.append({
            "titulo": limpar(o.get("title") or o.get("display_name") or "", 200),
            "corpo": limpar(resumo, 400),
            "url": (o.get("primary_location") or {}).get("landing_page_url") or o.get("id", ""),
            "idioma": (o.get("language") or "—")[:2],
        })
    return itens


def ler_wikipedia(fonte):
    """Wikipédia em qualquer uma das ~300 línguas. Serve de dicionário do mundo."""
    dados = json.loads(buscar(fonte["url"]))
    lg = fonte.get("idioma", "—")
    itens = []
    for o in (dados.get("query", {}).get("search", []) or [])[:15]:
        itens.append({
            "titulo": limpar(o.get("title", ""), 200),
            "corpo": limpar(o.get("snippet", ""), 400),
            "url": f"https://{lg}.wikipedia.org/wiki/" + urllib.parse.quote(o.get("title", "")),
            "idioma": lg,
        })
    return itens


def coletar_fonte(fonte):
    t = fonte["tipo"]
    if t == "rss":
        return ler_rss(fonte["url"])
    if t == "arxiv":
        return ler_arxiv(fonte["url"])
    if t == "json":
        return ler_json(fonte)
    if t == "hn":
        return ler_hn(fonte["url"])
    if t == "bcb":
        return ler_bcb()
    if t == "gdelt":
        return ler_gdelt(fonte)
    if t == "openalex":
        return ler_openalex(fonte)
    if t == "wikipedia":
        return ler_wikipedia(fonte)
    return []


# ──────────────────────────────────────────────────────────────
# EXECUÇÃO
# ──────────────────────────────────────────────────────────────

def carregar_vistos():
    try:
        with open(VISTOS, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def salvar_vistos(v):
    os.makedirs(RAIZ, exist_ok=True)
    with open(VISTOS, "w", encoding="utf-8") as f:
        json.dump(sorted(v), f)


def fontes_proprias():
    """Fontes que a governança descobriu sozinha, ou que Samuel adicionou.
       Ficam em arquivo separado: o mapa original nunca é reescrito por máquina."""
    caminho = os.path.expanduser("~/sa/fontes-proprias.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def mapa_completo():
    """O mapa de fábrica somado ao que foi descoberto depois."""
    todas = {d: list(fs) for d, fs in FONTES.items()}
    for dominio, lista in fontes_proprias().items():
        todas.setdefault(dominio, [])
        existentes = {f.get("url") for f in todas[dominio]}
        for f in lista:
            if f.get("url") not in existentes:
                f["propria"] = True
                todas[dominio].append(f)
    return todas


def rodar():
    vistos = carregar_vistos()
    novos_total = 0
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resumo = []

    for dominio, fontes in mapa_completo().items():
        ativos = [f for f in fontes if f.get("ativo")]
        if not ativos:
            continue

        novos_dom = []
        for fonte in ativos:
            try:
                itens = coletar_fonte(fonte)
            except Exception as e:
                print(f"  ! {fonte['nome']}: {type(e).__name__} {str(e)[:70]}")
                continue

            frescos = []
            for it in itens:
                if not it.get("titulo"):
                    continue
                h = ident(it)
                if h in vistos:
                    continue
                vistos.add(h)
                # Toda entrada vinda de fora passa pela neutralização.
                bruto = (it.get("titulo", "") + " " + it.get("corpo", ""))
                it["titulo"] = neutralizar(it["titulo"])
                it["corpo"] = neutralizar(it.get("corpo", ""))
                if _RE_INJ.search(bruto):
                    it["suspeito"] = True
                    print(f"    ⚠ conteúdo com comando embutido neutralizado: {it['titulo'][:60]}")
                it["fonte"] = fonte["nome"]
                it["tier"] = fonte.get("tier", 3)
                it["dominio"] = dominio
                it["origem"] = "externa-nao-confiavel"
                it["coletado"] = hoje
                frescos.append(it)

            novos_dom.extend(frescos)
            print(f"  · {fonte['nome']}: {len(frescos)} novos")

        if novos_dom:
            pasta = os.path.join(RAIZ, dominio)
            os.makedirs(pasta, exist_ok=True)
            arq = os.path.join(pasta, f"{hoje}.json")

            antigos = []
            if os.path.exists(arq):
                try:
                    with open(arq, encoding="utf-8") as f:
                        antigos = json.load(f)
                except Exception:
                    pass

            with open(arq, "w", encoding="utf-8") as f:
                json.dump(antigos + novos_dom, f, ensure_ascii=False, indent=1)

            novos_total += len(novos_dom)
            resumo.append((dominio, len(novos_dom)))

    salvar_vistos(vistos)

    print("\n" + "─" * 46)
    for d, n in resumo:
        print(f"  {d:<14} {n:>4} itens novos")
    print("─" * 46)
    print(f"  total: {novos_total} · biblioteca em {RAIZ}")
    if not novos_total:
        print("  nada novo desde a última rodada — o atualizador está fazendo o trabalho.")


def status():
    print("\nMAPA DE FONTES — todas as portas cadastradas\n")
    a = r = 0
    for dominio, fontes in mapa_completo().items():
        print(f"  {dominio}")
        for f in fontes:
            marca = "ATIVO   " if f.get("ativo") else "represado"
            print(f"    [{marca}] {f['nome']}")
            if f.get("nota"):
                print(f"                {f['nota']}")
            if f.get("ativo"):
                a += 1
            else:
                r += 1
        print()
    print(f"  {a} ativos · {r} represados")
    print("  liberar o funil = trocar ativo: False por True. Sem retrabalho.\n")


def gerar_memoria():
    """Condensa a biblioteca num bloco importável pelo app."""
    if not os.path.isdir(RAIZ):
        print("Biblioteca vazia. Rode o coletor primeiro.")
        return

    partes = []
    for dominio in sorted(os.listdir(RAIZ)):
        pasta = os.path.join(RAIZ, dominio)
        if not os.path.isdir(pasta):
            continue
        arquivos = sorted(os.listdir(pasta))[-3:]
        titulos = []
        for a in arquivos:
            try:
                with open(os.path.join(pasta, a), encoding="utf-8") as f:
                    for it in json.load(f)[:8]:
                        titulos.append(it["titulo"])
            except Exception:
                continue
        if titulos:
            partes.append(f"{dominio.upper()}: " + " | ".join(titulos[:10]))

    bloco = {
        "id": "coleta-" + datetime.now().strftime("%Y%m%d"),
        "tag": "CONTEXTO",
        "titulo": "Coleta da biblioteca — " + datetime.now().strftime("%d/%m/%Y"),
        "corpo": "\n".join(partes)[:4000],
    }
    saida = os.path.join(RAIZ, "memoria-para-o-app.json")
    with open(saida, "w", encoding="utf-8") as f:
        json.dump({"extras": [bloco], "hist": [], "versao": 1}, f, ensure_ascii=False, indent=1)

    print(f"\nBloco de memória gerado: {saida}")
    print("No app: aba Memória → Importar memória.\n")


def exportar_biblioteca():
    """Gera o arquivo estruturado que o app importa na aba Biblioteca."""
    if not os.path.isdir(RAIZ):
        print("Biblioteca vazia. Rode o coletor primeiro.")
        return

    itens = []
    for dominio in sorted(os.listdir(RAIZ)):
        pasta = os.path.join(RAIZ, dominio)
        if not os.path.isdir(pasta):
            continue
        for arq in sorted(os.listdir(pasta)):
            if not arq.endswith(".json"):
                continue
            try:
                with open(os.path.join(pasta, arq), encoding="utf-8") as f:
                    for it in json.load(f):
                        it.setdefault("dominio", dominio)
                        # Sem id o app não consegue apontar pro item (traduzir,
                        # abrir, marcar). Hash da url+título é estável: o mesmo
                        # item recoletado amanhã continua com o mesmo id.
                        if not it.get("id"):
                            semente = (it.get("url") or "") + "|" + (it.get("titulo") or "")
                            it["id"] = "b" + hashlib.sha1(semente.encode("utf-8")).hexdigest()[:12]
                        itens.append(it)
            except Exception:
                continue

    itens.sort(key=lambda x: (x.get("tier", 3), x.get("coletado", "")))
    saida = os.path.join(RAIZ, "biblioteca-para-o-app.json")
    with open(saida, "w", encoding="utf-8") as f:
        json.dump({"biblioteca": itens, "versao": 2,
                   "gerado": datetime.now(timezone.utc).isoformat()}, f,
                  ensure_ascii=False, indent=1)

    por_tier = {}
    for i in itens:
        t = i.get("tier", 3)
        por_tier[t] = por_tier.get(t, 0) + 1
    nomes = {1: "fonte primária", 2: "especializada", 3: "agregador"}

    print(f"\nBiblioteca exportada: {saida}")
    print(f"  {len(itens)} itens")
    for t in sorted(por_tier):
        print(f"    {nomes[t]:<16} {por_tier[t]:>4}")
    print("\nNo app: Ajustes → Importar biblioteca.\n")


# ═══════════════════════════════════════════════════════════════
# DICIONÁRIO DO MUNDO — tradução embutida, sem motor e sem chave
#
# A Wikidata guarda o MESMO conceito rotulado em ~200 línguas. Buscar
# "inteligência artificial" devolve o Q-id, e o Q-id devolve 人工智能,
# искусственный интеллект, الذكاء الاصطناعي de uma vez só.
#
# Colhido uma vez, vira arquivo local. Depois disso a busca multilíngue
# do app funciona offline, sem depender de motor nenhum.
# ═══════════════════════════════════════════════════════════════

# Línguas que valem guardar. Mais que isso incha o arquivo sem uso real.
LINGUAS_DIC = ["pt", "en", "es", "zh", "ru", "ar", "fr", "de", "ja", "ko",
               "it", "hi", "tr", "nl", "fa", "id", "vi", "pl", "uk", "he"]

# Sementes: os conceitos que a busca de Samuel encosta o tempo todo.
# A lista cresce sozinha com os termos que aparecem na própria biblioteca.
SEMENTES = [
    "inteligência artificial", "aprendizado de máquina", "rede neural",
    "modelo de linguagem", "algoritmo", "dados", "banco de dados",
    "regulamentação", "lei", "contrato", "privacidade", "segurança da informação",
    "criptografia", "código-fonte", "programação", "software", "servidor",
    "computação em nuvem", "telefone celular", "processador", "memória",
    "economia", "inflação", "taxa de juros", "mercado financeiro", "imposto",
    "empresa", "empreendedorismo", "investimento", "produtividade",
    "saúde", "medicina", "clínica médica", "odontologia",
    "energia", "mudança climática", "guerra", "eleição", "governo",
    "pesquisa científica", "universidade", "patente", "propriedade intelectual",
    "automação", "robótica", "agente inteligente", "tradução automática",
]


def _wd(url):
    return json.loads(buscar(url, timeout=20))


def termos_da_biblioteca(limite=40):
    """Puxa os termos mais repetidos nos títulos já coletados. Assim o
    dicionário acompanha o que Samuel realmente guarda, não uma lista fixa."""
    conta = {}
    vazias = set("""de da do que com para por uma um os as the and of in to a o e
        sobre como com new for with from this that are which um dos das no na""".split())
    for dominio in os.listdir(RAIZ) if os.path.isdir(RAIZ) else []:
        pasta = os.path.join(RAIZ, dominio)
        if not os.path.isdir(pasta):
            continue
        for arq in os.listdir(pasta):
            if not arq.endswith(".json"):
                continue
            try:
                with open(os.path.join(pasta, arq), encoding="utf-8") as f:
                    for it in json.load(f):
                        for w in re.findall(r"[A-Za-zÀ-ÿ]{5,}", it.get("titulo", "")):
                            w = w.lower()
                            if w not in vazias:
                                conta[w] = conta.get(w, 0) + 1
            except Exception:
                continue
    ordenado = sorted(conta, key=lambda k: -conta[k])
    return ordenado[:limite]


def montar_dicionario():
    """Um termo → um Q-id → rótulos em todas as línguas guardadas."""
    alvos = list(dict.fromkeys(SEMENTES + termos_da_biblioteca()))
    dic = {}
    achados = 0
    print("\n  DICIONÁRIO DO MUNDO — %d termos a resolver" % len(alvos))

    for i, termo in enumerate(alvos, 1):
        try:
            q = _wd("https://www.wikidata.org/w/api.php?action=wbsearchentities"
                    "&format=json&language=pt&uselang=pt&limit=1&search="
                    + urllib.parse.quote(termo))
            achado = (q.get("search") or [])
            if not achado:
                continue
            qid = achado[0]["id"]

            ent = _wd("https://www.wikidata.org/w/api.php?action=wbgetentities"
                      "&format=json&props=labels|aliases&ids=" + qid)
            e = (ent.get("entities") or {}).get(qid) or {}
            rotulos = []
            for lg in LINGUAS_DIC:
                lab = (e.get("labels") or {}).get(lg)
                if lab and lab.get("value"):
                    rotulos.append(lab["value"])
                # apelidos ajudam: "IA" é apelido de "inteligência artificial"
                for al in ((e.get("aliases") or {}).get(lg) or [])[:2]:
                    if al.get("value"):
                        rotulos.append(al["value"])
            rotulos = [r for r in dict.fromkeys(rotulos) if 1 < len(r) < 60]
            if len(rotulos) > 1:
                dic[termo] = rotulos
                achados += 1
        except Exception as e:
            print("    ! %s: %s" % (termo[:28], str(e)[:40]))
            continue
        if i % 10 == 0:
            print("    %d/%d — %d resolvidos" % (i, len(alvos), achados))
        time.sleep(0.4)   # a Wikidata é gratuita; não convém martelar

    saida = os.path.join(RAIZ, "dicionario.json")
    with open(saida, "w", encoding="utf-8") as f:
        json.dump({"dicionario": dic, "linguas": LINGUAS_DIC, "versao": 1,
                   "gerado": datetime.now(timezone.utc).isoformat()}, f,
                  ensure_ascii=False, indent=1)
    total = sum(len(v) for v in dic.values())
    print("\n  %d conceitos · %d termos em %d línguas" % (len(dic), total, len(LINGUAS_DIC)))
    print("  salvo em %s" % saida)
    print("  No app: Ajustes → Termux → dicionario\n")
    return dic


def extrair_texto(html):
    """Texto legível de uma página, sem biblioteca externa."""
    html = re.sub(r"(?is)<(script|style|nav|header|footer|aside|form|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>", "\n\n", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", html)
    for a, b in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&mdash;", "—"), ("&ndash;", "–"),
                 ("&rsquo;", "'"), ("&ldquo;", '"'), ("&rdquo;", '"'), ("&hellip;", "…")]:
        txt = txt.replace(a, b)
    txt = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), txt)
    linhas = []
    for ln in txt.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if len(ln) >= 40 or (ln and len(linhas) and len(linhas[-1]) >= 40):
            linhas.append(ln)
    fora = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
    return fora[:60000]


def completar_textos(limite=60):
    """Resumo de RSS costuma ter duas linhas. O artigo inteiro está no link.
    Aqui ele é baixado e guardado junto do item — depois disso, a leitura no
    app funciona offline, sem depender do site continuar no ar."""
    if not os.path.isdir(RAIZ):
        print("Biblioteca vazia. Rode o coletor primeiro.")
        return

    feitos = falhos = pulados = 0
    print("\n  COMPLETANDO ARTIGOS (até %d)" % limite)

    for dominio in sorted(os.listdir(RAIZ)):
        pasta = os.path.join(RAIZ, dominio)
        if not os.path.isdir(pasta):
            continue
        for arq in sorted(os.listdir(pasta)):
            if not arq.endswith(".json") or feitos + falhos >= limite:
                continue
            caminho = os.path.join(pasta, arq)
            try:
                with open(caminho, encoding="utf-8") as f:
                    itens = json.load(f)
            except Exception:
                continue

            mudou = False
            for it in itens:
                if feitos + falhos >= limite:
                    break
                # já tem texto longo? não gasta rede de novo
                if len(it.get("texto") or "") > 400:
                    pulados += 1
                    continue
                url = it.get("url") or ""
                if not url.startswith("http") or url.endswith(".pdf"):
                    continue
                try:
                    bruto = buscar(url, timeout=25, tentativas=2)
                    texto = extrair_texto(bruto)
                    if len(texto) > 300:
                        # o mesmo filtro anti-injeção que já protege o resumo
                        it["texto"] = neutralizar(texto) if "neutralizar" in globals() else texto
                        mudou = True
                        feitos += 1
                        print("    + %s" % (it.get("titulo", "")[:52]))
                    else:
                        falhos += 1
                except Exception as e:
                    falhos += 1
                    print("    ! %s: %s" % (it.get("titulo", "")[:34], str(e)[:34]))
                time.sleep(1.0)   # não martelar os sites

            if mudou:
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(itens, f, ensure_ascii=False, indent=1)

    print("\n  %d artigos baixados · %d falharam · %d já tinham" % (feitos, falhos, pulados))
    exportar_biblioteca()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--status":
        status()
    elif arg == "--memoria":
        gerar_memoria()
    elif arg == "--exportar":
        exportar_biblioteca()
    elif arg == "--dicionario":
        montar_dicionario()
    elif arg == "--completar":
        completar_textos()
    else:
        print("\nCOLETOR — Sistema Absoluto")
        print(f"{datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        rodar()
        exportar_biblioteca()
