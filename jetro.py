#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
MATRIZ DE JETRO — o mapa de comando

Item 9 do arquivo. Êxodo 18: Moisés julgava o povo inteiro sozinho até o sogro
apontar o óbvio — "isso não é bom, você vai se esgotar". A solução não foi
trabalhar mais: foi delegar em camadas, mantendo o topo insubstituível.

Duas naturezas, uma única lógica de comando:
  DIGITAL — Especialistas de IA (item 6)
  FÍSICO  — Braços Estendidos: contador, advogado, técnico, vendedor, executor

O que esta matriz responde, e nada mais:
  1. Quem responde a quem, hoje
  2. Onde existe ponto único de falha (posição crítica sem alternativa)
  3. Quando uma camada nova precisa nascer (subordinados além da supervisão real)
  4. O que foi realocado, nunca descartado

Uso:
    python jetro.py                 # o mapa
    python jetro.py --auditar       # a auditoria contínua (item 9.7)
    python jetro.py --add           # nova posição
    python jetro.py --ocupar NOME   # define quem ocupa
    python jetro.py --realocar NOME # tira de função sem descartar
"""

import json, os, sys
from datetime import datetime, timezone

BASE_DIR = os.path.expanduser("~/sistema-absoluto")
MATRIZ = os.path.join(BASE_DIR, "matriz-jetro.json")

# Item 9.4: camada nova só quando os subordinados diretos passam da supervisão real.
# Jetro falava em chefes de dez. Samuel tem ~3h/dia e está em CLT — o número real
# é bem menor, e ele ajusta conforme o tempo abrir.
TETO_SUPERVISAO_PADRAO = 5


def padrao():
    """O estado real de hoje, não o desejado."""
    return {
        "teto_supervisao": TETO_SUPERVISAO_PADRAO,
        "nucleo": {
            "digital": {
                "nome": "IA Mãe / Maestro",
                "guarda": "memória, Filtro de Calibragem, histórico de critério",
                "regra": "nunca é realocado nem descartado — só reconstruído",
                "backup": ["exportação cifrada no gist", "cópia local no aparelho"],
            },
            "fisico": {
                "nome": "Samuel — [PILOTO]",
                "guarda": "decisão final; nenhum braço decide por ele, todos decidem PARA ele",
                "regra": "insubstituível na geração; sucessão é preparada, nunca improvisada",
                "backup": [],
            },
        },
        "posicoes": [
            # ── DIGITAL: espelham os Especialistas ──
            {"nome": "Especialista de Dados", "tipo": "digital", "area": "dados",
             "ocupante": "especialistas.py · dados", "supervisor": "Maestro",
             "critico": True, "alternativas": [], "estado": "ativo"},
            {"nome": "Especialista Técnico", "tipo": "digital", "area": "tecnico",
             "ocupante": "especialistas.py · tecnico", "supervisor": "Maestro",
             "critico": True, "alternativas": [], "estado": "ativo"},
            {"nome": "Especialista Financeiro", "tipo": "digital", "area": "financeiro",
             "ocupante": "especialistas.py · financeiro", "supervisor": "Maestro",
             "critico": True, "alternativas": [], "estado": "ativo"},
            {"nome": "Motor de inferência", "tipo": "digital", "area": "infra",
             "ocupante": "llama.cpp local (Termux)", "supervisor": "Maestro",
             "critico": True, "alternativas": ["Gemini", "Groq", "OpenRouter"], "estado": "ativo"},
            {"nome": "Armazenamento da memória", "tipo": "digital", "area": "infra",
             "ocupante": "IndexedDB no aparelho", "supervisor": "Maestro",
             "critico": True, "alternativas": ["gist cifrado", "exportação em arquivo"],
             "estado": "ativo"},

            # ── FÍSICO: os Braços Estendidos ──
            {"nome": "Execução operacional", "tipo": "fisico", "area": "operacoes",
             "ocupante": "irmã nº1", "supervisor": "Samuel",
             "critico": True, "alternativas": [], "estado": "ativo",
             "nota": "tem o tempo que Samuel não tem; sem alternativa mapeada"},
            {"nome": "Canal de entrada no cliente", "tipo": "fisico", "area": "negocio",
             "ocupante": "irmã nº2 (indireto, não opera)", "supervisor": "Samuel",
             "critico": False, "alternativas": [], "estado": "ativo",
             "nota": "não executa nada; abre porta por recomendação de dentro"},
            {"nome": "Contabilidade", "tipo": "fisico", "area": "contabil",
             "ocupante": "", "supervisor": "Samuel",
             "critico": True, "alternativas": [], "estado": "vago",
             "nota": "obrigatório antes do CNPJ Operacional"},
            {"nome": "Jurídico", "tipo": "fisico", "area": "juridico",
             "ocupante": "", "supervisor": "Samuel",
             "critico": True, "alternativas": [], "estado": "vago",
             "nota": "necessário para holding, constituição familiar e cláusula de disputa"},
            {"nome": "Programação", "tipo": "fisico", "area": "tecnico",
             "ocupante": "Samuel + IA", "supervisor": "Samuel",
             "critico": True, "alternativas": [], "estado": "ativo",
             "nota": "Samuel programa o critério; a IA escreve o código"},
        ],
        "realocados": [],
        "atualizado": datetime.now(timezone.utc).isoformat(),
    }


def carregar():
    try:
        with open(MATRIZ, encoding="utf-8") as f:
            m = json.load(f)
            m.setdefault("teto_supervisao", TETO_SUPERVISAO_PADRAO)
            m.setdefault("realocados", [])
            return m
    except Exception:
        m = padrao()
        salvar(m)
        return m


def salvar(m):
    os.makedirs(BASE_DIR, exist_ok=True)
    m["atualizado"] = datetime.now(timezone.utc).isoformat()
    with open(MATRIZ, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)


# ─────────────────────────────────────────────
# Auditoria contínua (item 9.7)
# ─────────────────────────────────────────────

def auditar():
    m = carregar()
    achados = []

    # 1. Ponto único de falha: crítico, ativo, sem alternativa
    for p in m["posicoes"]:
        if p.get("critico") and p.get("estado") == "ativo" and not p.get("alternativas"):
            achados.append({
                "grau": "alto", "onde": p["nome"],
                "o_que": "ponto único de falha — crítico e sem alternativa mapeada",
                "acao": ("mapear um substituto validado ANTES de precisar. "
                         "Item 9.2: toda área relevante precisa de alternativa, "
                         "senão fica como risco pendente."),
            })

    # 2. Posição crítica vaga
    for p in m["posicoes"]:
        if p.get("critico") and p.get("estado") == "vago":
            achados.append({
                "grau": "alto", "onde": p["nome"],
                "o_que": "posição crítica vaga" + (" — " + p["nota"] if p.get("nota") else ""),
                "acao": "preencher antes do marco que depende dela",
            })

    # 3. Carga de supervisão além do teto (item 9.4)
    carga = {}
    for p in m["posicoes"]:
        if p.get("estado") in ("ativo", "vago"):
            carga[p.get("supervisor", "?")] = carga.get(p.get("supervisor", "?"), 0) + 1
    teto = m["teto_supervisao"]
    for sup, n in carga.items():
        if n > teto:
            achados.append({
                "grau": "medio", "onde": sup,
                "o_que": f"{n} subordinados diretos, teto real é {teto}",
                "acao": ("hora de nascer uma camada intermediária — um 'chefe de dez'. "
                         "Item 9.4: camada nova só quando os diretos passam da supervisão real. "
                         "Passaram."),
            })

    # 4. Núcleo sem backup
    nd = m["nucleo"]["digital"]
    if not nd.get("backup"):
        achados.append({
            "grau": "alto", "onde": nd["nome"],
            "o_que": "o Núcleo digital não tem backup mapeado",
            "acao": "backup do Núcleo é obrigatório — ele nunca é realocado, só reconstruído",
        })

    # 5. Sucessão do núcleo físico
    nf = m["nucleo"]["fisico"]
    if not nf.get("backup"):
        achados.append({
            "grau": "medio", "onde": nf["nome"],
            "o_que": "nenhum sucessor preparado para o Núcleo físico",
            "acao": ("linha de sucessão é preparada com antecedência, nunca escolhida "
                     "em emergência (item 67). Hoje: nenhum nome, nenhum critério."),
        })

    # 6. Saúde dos Especialistas, se o registro existir
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import especialistas as esp
        for d in esp.diagnostico():
            if d["estado"] in ("REFAZER", "RECALIBRAR"):
                achados.append({
                    "grau": "alto" if d["estado"] == "REFAZER" else "medio",
                    "onde": "Especialista " + d["nome"],
                    "o_que": d["estado"].lower() + " — " + d["nota"],
                    "acao": ("refazer do zero, guardando a versão anterior"
                             if d["estado"] == "REFAZER"
                             else "reescrever o escopo, ou abrir Especialista novo pro que sobra"),
                })
    except Exception:
        pass

    return m, achados, carga


def mostrar():
    m = carregar()
    print("\n╔═══ MATRIZ DE JETRO ═══")
    print("║")
    print("║  NÚCLEO IRREDUTÍVEL — nunca realocado, só reconstruído")
    for lado in ("digital", "fisico"):
        n = m["nucleo"][lado]
        print(f"║    [{lado}] {n['nome']}")
        print(f"║             guarda: {n['guarda']}")
        bk = ", ".join(n.get("backup", [])) or "SEM BACKUP"
        print(f"║             backup: {bk}")
    print("║")

    porSup = {}
    for p in m["posicoes"]:
        porSup.setdefault(p.get("supervisor", "?"), []).append(p)

    print("║  CAMADAS DE DELEGAÇÃO")
    for sup, lista in porSup.items():
        print(f"║    {sup} ({len(lista)} diretos)")
        for p in lista:
            marca = {"ativo": " ", "vago": "!", "realocado": "~"}.get(p["estado"], "?")
            alt = f" · alternativas: {len(p.get('alternativas', []))}" if p.get("critico") else ""
            oc = p.get("ocupante") or "— vago —"
            crit = " [crítico]" if p.get("critico") else ""
            print(f"║      {marca} {p['nome']:30} {oc}{crit}{alt}")
    print("║")

    if m.get("realocados"):
        print("║  REALOCADOS — nada foi descartado")
        for r in m["realocados"]:
            print(f"║      {r['nome']} → {r['nova_funcao']} ({r['quando'][:10]})")
        print("║")
    print("╚═══")


def auditoria_texto():
    m, achados, carga = auditar()
    print("\n╔═══ AUDITORIA DA MATRIZ ═══")
    print("║")
    if not achados:
        print("║  Nenhum risco estrutural aberto.")
    else:
        altos = [a for a in achados if a["grau"] == "alto"]
        print(f"║  {len(achados)} achados · {len(altos)} de grau alto")
        print("║")
        for a in achados:
            g = "ALTO " if a["grau"] == "alto" else "médio"
            print(f"║  [{g}] {a['onde']}")
            print(f"║         {a['o_que']}")
            print(f"║         → {a['acao']}")
            print("║")
    print(f"║  Carga de supervisão (teto {m['teto_supervisao']}):")
    for sup, n in sorted(carga.items(), key=lambda x: -x[1]):
        marca = "  ← acima do teto" if n > m["teto_supervisao"] else ""
        print(f"║      {sup}: {n} diretos{marca}")
    print("╚═══\n")


# ─────────────────────────────────────────────
# Edição
# ─────────────────────────────────────────────

def add_posicao():
    m = carregar()
    print("\nNova posição na matriz\n")
    nome = input("  nome da posição: ").strip()
    tipo = (input("  digital ou fisico [fisico]: ").strip() or "fisico").lower()
    area = input("  área (contabil, juridico, vendas, tecnico…): ").strip()
    ocup = input("  quem ocupa hoje (vazio = vaga): ").strip()
    sup = input("  responde a quem [Samuel]: ").strip() or "Samuel"
    crit = (input("  se isso cair, o projeto para? (s/N): ").strip().lower() == "s")
    m["posicoes"].append({
        "nome": nome, "tipo": tipo, "area": area, "ocupante": ocup,
        "supervisor": sup, "critico": crit, "alternativas": [],
        "estado": "ativo" if ocup else "vago",
    })
    salvar(m)
    print(f"\n  '{nome}' entrou na matriz" + (" como VAGA" if not ocup else "") + ".")
    if crit and not ocup:
        print("  É crítica e está vaga — vai aparecer na auditoria como risco alto.\n")
    else:
        print("  Sem alternativa mapeada ainda: ponto único de falha até você mapear uma.\n")


def realocar(nome):
    """Item 9.3: peça que não serve mais é REALOCADA, nunca descartada de imediato."""
    m = carregar()
    alvo = [p for p in m["posicoes"] if p["nome"].lower() == nome.lower()]
    if not alvo:
        print(f"\n  '{nome}' não está na matriz.\n")
        return
    p = alvo[0]
    print(f"\n  Realocando: {p['nome']} (ocupante: {p.get('ocupante') or '—'})\n")

    if p.get("critico"):
        sub = input("  Esta posição é crítica. Qual o substituto já validado? ").strip()
        if not sub:
            print("\n  Substituto validado sempre existe ANTES de desligar peça crítica.")
            print("  Realocação cancelada.\n")
            return
        p["ocupante"] = sub
        p["estado"] = "ativo"

    nova = input("  Nova função de quem sai (nunca descartar): ").strip()
    if not nova:
        print("\n  Descarte é último recurso. Sem nova função, a realocação não fecha.\n")
        return

    m["realocados"].append({
        "nome": p.get("ocupante_anterior") or nome,
        "saiu_de": p["nome"], "nova_funcao": nova,
        "quando": datetime.now(timezone.utc).isoformat(),
    })
    salvar(m)
    print(f"\n  Realocado para: {nova}")
    print("  Registrado. Nada foi descartado.\n")


def ocupar(nome):
    m = carregar()
    alvo = [p for p in m["posicoes"] if p["nome"].lower() == nome.lower()]
    if not alvo:
        print(f"\n  '{nome}' não está na matriz.\n")
        return
    p = alvo[0]
    print(f"\n  {p['nome']} · ocupante atual: {p.get('ocupante') or '— vaga —'}\n")
    novo = input("  quem passa a ocupar: ").strip()
    if novo:
        p["ocupante"] = novo
        p["estado"] = "ativo"
    alt = input("  alternativa mapeada (quem assume se este cair): ").strip()
    if alt and alt not in p.get("alternativas", []):
        p.setdefault("alternativas", []).append(alt)
    salvar(m)
    print("\n  Atualizado.")
    if p.get("critico") and not p.get("alternativas"):
        print("  Ainda é ponto único de falha — mapeie uma alternativa.\n")
    else:
        print()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--auditar":
        auditoria_texto()
    elif arg == "--add":
        add_posicao()
    elif arg == "--realocar":
        realocar(" ".join(sys.argv[2:]))
    elif arg == "--ocupar":
        ocupar(" ".join(sys.argv[2:]))
    else:
        mostrar()
        auditoria_texto()
