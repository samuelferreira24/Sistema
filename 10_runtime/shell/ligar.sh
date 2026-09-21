#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════
# LIGAR — o Termux inteiro num comando
#
# O que ele resolve: hoje você precisa lembrar de ligar o motor, de copiar
# arquivo novo depois de baixar, e de conferir se o agendamento está de pé.
# Aqui é tudo junto, e ele confere antes de agir — não refaz o que já está feito.
#
# Uso:
#     ligar            liga tudo (o que faltar)
#     ligar --parar    desliga o motor
#     ligar --status   só mostra como está, sem mexer
#     ligar --atualiza só busca arquivo novo em Downloads
# ═══════════════════════════════════════════════════════════

SA="$HOME/sa"
MOTOR="$HOME/motor"
BAIXADOS="$HOME/storage/downloads"
V='\033[0;32m'; A='\033[0;33m'; R='\033[0;31m'; F='\033[0m'
ok(){   echo -e "${V}✓${F} $1"; }
aviso(){ echo -e "${A}!${F} $1"; }
erro(){ echo -e "${R}✗${F} $1"; }

# ─────────────────────────────────────────────
# Traz arquivo novo de Downloads, se houver
# ─────────────────────────────────────────────
atualizar_arquivos(){
  mkdir -p "$SA"
  local novos=0

  # A pasta que o Android criou por último — resolve o problema
  # das pastas (1), (2) que aparecem a cada download repetido.
  local origem
  origem=$(ls -dt "$BAIXADOS"/sistema-absoluto* 2>/dev/null | head -1)

  if [ -z "$origem" ]; then
    aviso "nenhuma pasta do sistema em Downloads — nada pra atualizar"
    return
  fi

  for f in "$origem"/*.py "$origem"/motor.sh; do
    [ -f "$f" ] || continue
    local nome
    nome=$(basename "$f")
    # Só copia se for mais novo que o que já está lá
    if [ ! -f "$SA/$nome" ] || [ "$f" -nt "$SA/$nome" ]; then
      cp "$f" "$SA/$nome"
      chmod +x "$SA/$nome" 2>/dev/null
      echo "     atualizado: $nome"
      novos=$((novos + 1))
    fi
  done

  if [ "$novos" -gt 0 ]; then
    ok "$novos arquivo(s) atualizado(s) de $(basename "$origem")"
  else
    ok "arquivos já estavam em dia"
  fi
}

# ─────────────────────────────────────────────
motor_rodando(){
  curl -s --max-time 3 http://127.0.0.1:8080/health >/dev/null 2>&1 && return 0
  # Nem toda versão tem /health; tenta a porta direto
  curl -s --max-time 3 -o /dev/null http://127.0.0.1:8080/ 2>/dev/null && return 0
  return 1
}

ligar_motor(){
  if motor_rodando; then
    ok "motor já está de pé na porta 8080"
    return
  fi
  if [ ! -f "$MOTOR/ligar.sh" ]; then
    aviso "motor local não instalado — rode motor.sh se quiser offline"
    return
  fi
  echo "     subindo o motor em segundo plano…"
  nohup bash "$MOTOR/ligar.sh" > "$SA/motor.log" 2>&1 &
  for i in $(seq 1 20); do
    sleep 2
    if motor_rodando; then
      ok "motor de pé (log em ~/sa/motor.log)"
      return
    fi
  done
  aviso "o motor não respondeu em 40s — veja ~/sa/motor.log"
}

parar_motor(){
  pkill -f llama-server 2>/dev/null && ok "motor parado" || aviso "o motor não estava rodando"
}

# ─────────────────────────────────────────────
agendamento(){
  if ! command -v termux-job-scheduler >/dev/null 2>&1; then
    aviso "Termux:API não instalado — sem automação de hora em hora"
    return
  fi
  if termux-job-scheduler --pending 2>/dev/null | grep -q "orquestrador"; then
    ok "coleta automática já agendada"
    return
  fi
  if [ -f "$SA/orquestrador.py" ]; then
    python "$SA/orquestrador.py" --agendar >/dev/null 2>&1 \
      && ok "coleta automática agendada (de hora em hora)" \
      || aviso "não consegui agendar — rode: python ~/sa/orquestrador.py --agendar"
  fi
}

status(){
  echo
  echo "── COMO ESTÁ ──"
  motor_rodando && ok "motor local respondendo" || aviso "motor local desligado"

  if command -v termux-job-scheduler >/dev/null 2>&1 \
     && termux-job-scheduler --pending 2>/dev/null | grep -q "orquestrador"; then
    ok "coleta automática agendada"
  else
    aviso "coleta automática não agendada"
  fi

  if [ -f "$SA/base.db" ]; then
    local n
    n=$(python -c "import sqlite3;print(sqlite3.connect('$SA/base.db').execute('SELECT COUNT(*) FROM itens').fetchone()[0])" 2>/dev/null)
    ok "base com ${n:-?} itens"
  else
    aviso "base ainda vazia — rode: python ~/sa/coletor.py"
  fi

  if [ -f "$SA/plantao.json" ]; then
    local q
    q=$(python -c "
import json
try:
    d=json.load(open('$SA/plantao.json'))
    a=d.get('atual') or {}
    print(a.get('quando','?')[:16].replace('T',' às '))
except Exception: print('?')" 2>/dev/null)
    ok "último plantão: $q"
  fi
  echo
}

# ─────────────────────────────────────────────
case "${1:-}" in
  --parar)
    parar_motor
    ;;
  --status)
    status
    ;;
  --atualiza)
    echo; echo "── ATUALIZANDO ARQUIVOS ──"
    atualizar_arquivos
    echo
    ;;
  *)
    echo
    echo "── LIGANDO O SISTEMA ──"
    termux-wake-lock 2>/dev/null && ok "aparelho travado acordado"
    atualizar_arquivos
    ligar_motor
    agendamento
    status
    echo "  Para parar o motor:  ligar --parar"
    echo "  Só conferir:         ligar --status"
    echo
    ;;
esac
