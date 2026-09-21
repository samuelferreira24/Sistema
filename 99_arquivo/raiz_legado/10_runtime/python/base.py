#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
BASE — Infraestrutura de dados do Sistema Absoluto

Sem isso, todo agente trabalha às cegas. Arquivo JSON por dia serve pra guardar;
não serve pra perguntar. Aqui o dado vira base consultável.

Zero dependência externa: SQLite e FTS5 já vêm no Python. Os vetores semânticos
saem do motor local, que já está no aparelho.

Três camadas de busca, da mais barata pra mais cara:
  1. Palavra exata   — FTS5, instantâneo, funciona sem motor
  2. Semântica       — vetores do motor local, acha o que o texto não diz igual
  3. Combinada       — as duas, com o grau da fonte pesando no resultado

Uso:
    python base.py --criar          # monta a base
    python base.py --importar       # traz a biblioteca de arquivos pra dentro
    python base.py --vetorizar      # calcula os vetores do que falta
    python base.py --buscar "termo"
    python base.py --status
"""

import json, os, sqlite3, sys, math, struct, hashlib, time
import urllib.request
from datetime import datetime, timezone

BASE_DIR = os.path.expanduser("~/sistema-absoluto")
BANCO = os.path.join(BASE_DIR, "base.db")
BIBLIOTECA = os.path.expanduser("~/biblioteca")
MOTOR_EMB = "http://127.0.0.1:8080/v1/embeddings"


# ─────────────────────────────────────────────
# Estrutura
# ─────────────────────────────────────────────

ESQUEMA = """
CREATE TABLE IF NOT EXISTS itens (
  id         INTEGER PRIMARY KEY,
  chave      TEXT UNIQUE,          -- impressão digital, evita repetido
  dominio    TEXT NOT NULL,
  fonte      TEXT,
  tier       INTEGER DEFAULT 3,    -- 1 primária, 2 especializada, 3 agregador
  titulo     TEXT NOT NULL,
  corpo      TEXT,
  url        TEXT,
  coletado   TEXT,
  suspeito   INTEGER DEFAULT 0,    -- tinha comando embutido, foi neutralizado
  vetor      BLOB,                 -- posição semântica, quando calculada
  usos       INTEGER DEFAULT 0,    -- quantas vezes serviu de fato
  criado_em  TEXT
);

CREATE INDEX IF NOT EXISTS idx_dominio  ON itens(dominio);
CREATE INDEX IF NOT EXISTS idx_tier     ON itens(tier);
CREATE INDEX IF NOT EXISTS idx_coletado ON itens(coletado);

-- Busca por palavra: instantânea e sem depender de motor nenhum
CREATE VIRTUAL TABLE IF NOT EXISTS itens_fts USING fts5(
  titulo, corpo, fonte,
  content='itens', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS itens_ai AFTER INSERT ON itens BEGIN
  INSERT INTO itens_fts(rowid, titulo, corpo, fonte)
  VALUES (new.id, new.titulo, new.corpo, new.fonte);
END;
CREATE TRIGGER IF NOT EXISTS itens_ad AFTER DELETE ON itens BEGIN
  INSERT INTO itens_fts(itens_fts, rowid, titulo, corpo, fonte)
  VALUES ('delete', old.id, old.titulo, old.corpo, old.fonte);
END;
CREATE TRIGGER IF NOT EXISTS itens_au AFTER UPDATE ON itens BEGIN
  INSERT INTO itens_fts(itens_fts, rowid, titulo, corpo, fonte)
  VALUES ('delete', old.id, old.titulo, old.corpo, old.fonte);
  INSERT INTO itens_fts(rowid, titulo, corpo, fonte)
  VALUES (new.id, new.titulo, new.corpo, new.fonte);
END;

-- Qual fonte realmente entrega valor, e qual só faz volume
CREATE TABLE IF NOT EXISTS fontes (
  nome       TEXT PRIMARY KEY,
  dominio    TEXT,
  tier       INTEGER,
  trazidos   INTEGER DEFAULT 0,
  uteis      INTEGER DEFAULT 0,    -- itens que a IA de fato usou
  ultima     TEXT
);

-- O que a IA perguntou, pra saber onde a base está cega
CREATE TABLE IF NOT EXISTS buscas (
  id       INTEGER PRIMARY KEY,
  termo    TEXT,
  achados  INTEGER,
  quando   TEXT
);
"""


def conectar():
    os.makedirs(BASE_DIR, exist_ok=True)
    c = sqlite3.connect(BANCO)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")     # aguenta leitura durante escrita
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def criar():
    c = conectar()
    c.executescript(ESQUEMA)
    c.commit()
    n = c.execute("SELECT COUNT(*) n FROM itens").fetchone()["n"]
    c.close()
    print(f"Base pronta em {BANCO} · {n} itens")


def impressao(titulo, url):
    return hashlib.sha1((str(titulo) + str(url)).encode("utf-8")).hexdigest()[:20]


# ─────────────────────────────────────────────
# Entrada de dados
# ─────────────────────────────────────────────

def guardar_item(c, it, dominio):
    chave = impressao(it.get("titulo", ""), it.get("url", ""))
    try:
        c.execute("""INSERT INTO itens
            (chave, dominio, fonte, tier, titulo, corpo, url, coletado, suspeito, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (chave, dominio, it.get("fonte", ""), int(it.get("tier", 3)),
             it.get("titulo", "")[:400], (it.get("corpo") or "")[:2000],
             it.get("url", ""), it.get("coletado", ""),
             1 if it.get("suspeito") else 0,
             datetime.now(timezone.utc).isoformat()))
        return True
    except sqlite3.IntegrityError:
        return False   # já estava aqui


def importar():
    """Traz os arquivos que o coletor gerou pra dentro da base."""
    if not os.path.isdir(BIBLIOTECA):
        print("Biblioteca vazia. Rode o coletor primeiro.")
        return
    c = conectar()
    c.executescript(ESQUEMA)
    novos = repetidos = 0
    fontes = {}

    for dominio in sorted(os.listdir(BIBLIOTECA)):
        pasta = os.path.join(BIBLIOTECA, dominio)
        if not os.path.isdir(pasta):
            continue
        for arq in sorted(os.listdir(pasta)):
            if not arq.endswith(".json"):
                continue
            try:
                with open(os.path.join(pasta, arq), encoding="utf-8") as f:
                    itens = json.load(f)
            except Exception:
                continue
            for it in itens:
                if not it.get("titulo"):
                    continue
                if guardar_item(c, it, dominio):
                    novos += 1
                    f_nome = it.get("fonte", "?")
                    fontes.setdefault(f_nome, {"d": dominio, "t": it.get("tier", 3), "n": 0})
                    fontes[f_nome]["n"] += 1
                else:
                    repetidos += 1

    for nome, d in fontes.items():
        c.execute("""INSERT INTO fontes (nome, dominio, tier, trazidos, ultima)
                     VALUES (?,?,?,?,?)
                     ON CONFLICT(nome) DO UPDATE SET
                       trazidos = trazidos + excluded.trazidos,
                       ultima = excluded.ultima""",
                  (nome, d["d"], d["t"], d["n"], datetime.now(timezone.utc).isoformat()))
    c.commit()
    total = c.execute("SELECT COUNT(*) n FROM itens").fetchone()["n"]
    c.close()
    print(f"{novos} itens novos · {repetidos} já estavam · {total} na base")


# ─────────────────────────────────────────────
# Camada semântica
# ─────────────────────────────────────────────

def vetor_de(texto):
    """Pede ao motor local a posição semântica do texto."""
    corpo = json.dumps({"model": "local", "input": texto[:1800]}).encode("utf-8")
    req = urllib.request.Request(MOTOR_EMB, data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    v = d["data"][0]["embedding"]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]          # normalizado: comparar vira multiplicar


def empacotar(v):
    return struct.pack(f"{len(v)}f", *v)


def desempacotar(b):
    return list(struct.unpack(f"{len(b)//4}f", b))


def proximidade(a, b):
    return sum(x * y for x, y in zip(a, b))   # ambos normalizados


def vetorizar(limite=200):
    c = conectar()
    faltando = c.execute(
        "SELECT id, titulo, corpo FROM itens WHERE vetor IS NULL LIMIT ?", (limite,)
    ).fetchall()
    if not faltando:
        print("Todos os itens já têm vetor.")
        c.close()
        return

    print(f"Calculando {len(faltando)} vetores…")
    feitos = falhas = 0
    t0 = time.time()
    for i, linha in enumerate(faltando, 1):
        texto = (linha["titulo"] or "") + ". " + (linha["corpo"] or "")
        try:
            v = vetor_de(texto)
            c.execute("UPDATE itens SET vetor=? WHERE id=?", (empacotar(v), linha["id"]))
            feitos += 1
        except urllib.error.URLError:
            print("  motor local não respondeu — ligue com 'motor' e rode de novo")
            break
        except Exception:
            falhas += 1
        if i % 25 == 0:
            c.commit()
            print(f"  {i}/{len(faltando)}…")
    c.commit()
    c.close()
    print(f"{feitos} vetorizados · {falhas} falharam · {round(time.time()-t0)}s")


# ─────────────────────────────────────────────
# Busca
# ─────────────────────────────────────────────

def buscar(termo, n=10, dominio=None, so_primaria=False):
    """Palavra exata primeiro. Se houver vetores, a semântica entra junto."""
    c = conectar()
    filtros, args = [], []
    if dominio:
        filtros.append("i.dominio = ?"); args.append(dominio)
    if so_primaria:
        filtros.append("i.tier = 1")
    onde = (" AND " + " AND ".join(filtros)) if filtros else ""

    # 1. palavra exata
    achados = {}
    try:
        termo_fts = " OR ".join(p for p in termo.split() if len(p) > 2) or termo
        linhas = c.execute(f"""
            SELECT i.*, bm25(itens_fts) AS nota
            FROM itens_fts JOIN itens i ON i.id = itens_fts.rowid
            WHERE itens_fts MATCH ?{onde}
            ORDER BY nota LIMIT ?""", [termo_fts] + args + [n * 3]).fetchall()
        for L in linhas:
            achados[L["id"]] = {"linha": L, "texto": -float(L["nota"]), "sem": 0.0}
    except sqlite3.OperationalError:
        pass

    # 2. semântica, quando existe vetor e motor
    try:
        tem_vetor = c.execute("SELECT COUNT(*) n FROM itens WHERE vetor IS NOT NULL").fetchone()["n"]
        if tem_vetor:
            alvo = vetor_de(termo)
            cand = c.execute(
                f"SELECT i.* FROM itens i WHERE i.vetor IS NOT NULL{onde.replace(' AND ',' AND ',1) if filtros else ''}",
                args).fetchall()
            for L in cand:
                p = proximidade(alvo, desempacotar(L["vetor"]))
                if L["id"] in achados:
                    achados[L["id"]]["sem"] = p
                elif p > 0.35:
                    achados[L["id"]] = {"linha": L, "texto": 0.0, "sem": p}
    except Exception:
        pass   # sem motor, fica só a busca por palavra

    # 3. nota final: texto + semântica + peso do grau da fonte
    saida = []
    maior_texto = max([a["texto"] for a in achados.values()] + [1.0])
    for a in achados.values():
        L = a["linha"]
        peso_tier = {1: 1.0, 2: 0.75, 3: 0.5}.get(L["tier"], 0.5)
        nota = (a["texto"] / maior_texto) * 0.5 + a["sem"] * 0.5
        saida.append({
            "id": L["id"], "titulo": L["titulo"], "corpo": L["corpo"],
            "fonte": L["fonte"], "tier": L["tier"], "dominio": L["dominio"],
            "url": L["url"], "coletado": L["coletado"], "suspeito": L["suspeito"],
            "nota": round(nota * peso_tier, 4),
            "por": "texto+semântica" if a["texto"] and a["sem"] else ("semântica" if a["sem"] else "texto"),
        })
    saida.sort(key=lambda x: -x["nota"])
    saida = saida[:n]

    c.execute("INSERT INTO buscas (termo, achados, quando) VALUES (?,?,?)",
              (termo, len(saida), datetime.now(timezone.utc).isoformat()))
    for s in saida:
        c.execute("UPDATE itens SET usos = usos + 1 WHERE id = ?", (s["id"],))
        c.execute("UPDATE fontes SET uteis = uteis + 1 WHERE nome = ?", (s["fonte"],))
    c.commit()
    c.close()
    return saida


def status():
    if not os.path.exists(BANCO):
        print("Base não existe. Rode: python base.py --criar")
        return
    c = conectar()
    n = c.execute("SELECT COUNT(*) n FROM itens").fetchone()["n"]
    v = c.execute("SELECT COUNT(*) n FROM itens WHERE vetor IS NOT NULL").fetchone()["n"]
    s = c.execute("SELECT COUNT(*) n FROM itens WHERE suspeito=1").fetchone()["n"]
    tam = os.path.getsize(BANCO) / 1048576

    print(f"\nBASE DE DADOS — {n} itens · {tam:.1f} MB")
    print(f"  com vetor semântico: {v} ({round(v/n*100) if n else 0}%)")
    if s:
        print(f"  neutralizados: {s} (tinham comando embutido)")

    print("\n  Por domínio:")
    for L in c.execute("""SELECT dominio, COUNT(*) n,
                          SUM(CASE WHEN tier=1 THEN 1 ELSE 0 END) p
                          FROM itens GROUP BY dominio ORDER BY n DESC"""):
        print(f"    {L['dominio']:14} {L['n']:>5} itens · {L['p']} de fonte primária")

    print("\n  Fontes que mais servem:")
    for L in c.execute("""SELECT nome, trazidos, uteis FROM fontes
                          ORDER BY uteis DESC, trazidos DESC LIMIT 6"""):
        # 'uteis' conta quantas vezes um item daquela fonte apareceu numa busca —
        # pode passar do número de itens, porque o mesmo item serve várias vezes.
        print(f"    {L['nome'][:42]:44} {L['trazidos']:>4} itens · serviu {L['uteis']}x")

    ult = c.execute("SELECT termo, achados FROM buscas ORDER BY id DESC LIMIT 5").fetchall()
    if ult:
        print("\n  Últimas buscas:")
        for L in ult:
            marca = "" if L["achados"] else "   ← a base está cega aqui"
            print(f"    '{L['termo'][:38]}' → {L['achados']} achados{marca}")
    print()
    c.close()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--status"
    if arg == "--criar":
        criar()
    elif arg == "--importar":
        importar()
    elif arg == "--vetorizar":
        vetorizar(int(sys.argv[2]) if len(sys.argv) > 2 else 200)
    elif arg == "--buscar":
        termo = " ".join(sys.argv[2:]) or "ia local"
        r = buscar(termo)
        print(f"\n{len(r)} achados para '{termo}':\n")
        graus = {1: "fonte primária", 2: "especializada", 3: "agregador"}
        for x in r:
            print(f"  [{graus[x['tier']]:15}] {x['titulo'][:70]}")
            print(f"   {x['dominio']} · {x['fonte'][:34]} · nota {x['nota']} ({x['por']})\n")
    else:
        status()
