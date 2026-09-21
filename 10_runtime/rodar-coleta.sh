#!/data/data/com.termux/files/usr/bin/bash
# Chamado pelo agendador do Android a cada 3h, com a tela apagada.
# Coleta e completa; a análise fica com o piloto do app, que sabe
# ligar o motor e desligar depois.
SA="$HOME/sa"
cd "$SA" || exit 1
echo "─── $(date '+%d/%m %H:%M') ───" >> coleta.log
python coletor.py >> coleta.log 2>&1
python coletor.py --completar >> coleta.log 2>&1
# mantém o log num tamanho civilizado
tail -n 2000 coleta.log > coleta.tmp && mv coleta.tmp coleta.log
