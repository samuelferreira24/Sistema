#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
# ARRANQUE — tudo de pé sozinho, sem ninguém abrir o Termux
#
# Vai em ~/.termux/boot/ e o Termux:Boot roda quando o celular liga.
# Também serve pra rodar na mão: bash ~/sa/arranque.sh
#
# Regra: só sobe o que não está de pé. Rodar duas vezes não duplica nada.
# ═══════════════════════════════════════════════════════════════

SA="$HOME/sa"
LOG="$SA/arranque.log"
mkdir -p "$SA"

reg(){ echo "$(date '+%d/%m %H:%M:%S')  $1" >> "$LOG"; echo "$1"; }

# ── 1. impedir o Android de matar tudo enquanto a tela está apagada
if ! pgrep -f termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock 2>/dev/null && reg "trava de sono ligada"
fi

# ── 2. a Ponte: sem ela o app não alcança nada daqui
if pgrep -f "ponte.py" >/dev/null 2>&1; then
  reg "Ponte já estava de pé"
else
  cd "$SA" && nohup python ponte.py >> "$SA/ponte.log" 2>&1 &
  sleep 2
  if curl -s -m 3 http://127.0.0.1:8099/saude | grep -q '"ok"'; then
    reg "Ponte no ar em 127.0.0.1:8099"
  else
    reg "ERRO: a Ponte não respondeu — veja $SA/ponte.log"
  fi
fi

# ── 3. o motor NÃO sobe aqui de propósito.
#      Ele come bateria e só serve quando há análise pra fazer.
#      Quem decide ligar e desligar é o piloto automático do app.
reg "motor deixado desligado — o piloto sobe quando precisar"

# ── 4. agendamento da coleta, caso ainda não exista
if command -v termux-job-scheduler >/dev/null 2>&1; then
  if ! termux-job-scheduler --pending 2>/dev/null | grep -q "rodar-coleta"; then
    termux-job-scheduler \
      --script "$SA/rodar-coleta.sh" \
      --period-ms 10800000 \
      --persisted true \
      --network any >/dev/null 2>&1 && reg "coleta agendada a cada 3h"
  else
    reg "coleta já estava agendada"
  fi
else
  reg "aviso: termux-job-scheduler ausente — instale o app Termux:API pela F-Droid"
fi

reg "arranque concluído"
