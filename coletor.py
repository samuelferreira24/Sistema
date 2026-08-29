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

import json, os, sys, re, time, hashlib
import urllib.request, urllib.error
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

# ──────────────────────────────────────────────────────────────
# MAPA DE FONTES — ABERTURA TOTAL
# Toda porta fica cadastrada. "ativo" controla só a vazão de agora.
# Ligar uma fonte represada = trocar False por True. Sem retrabalho.
# ──────────────────────────────────────────────────────────────

FONTES = {
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

def buscar(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


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


def rodar():
    vistos = carregar_vistos()
    novos_total = 0
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resumo = []

    for dominio, fontes in FONTES.items():
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
    for dominio, fontes in FONTES.items():
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


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--status":
        status()
    elif arg == "--memoria":
        gerar_memoria()
    elif arg == "--exportar":
        exportar_biblioteca()
    else:
        print("\nCOLETOR — Sistema Absoluto")
        print(f"{datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        rodar()
        exportar_biblioteca()
