#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════
# SISTEMA ABSOLUTO — MOTOR PRÓPRIO NO CELULAR
# Resolve os passos 32.1 e 32.2: motor rodando, custo zero, sem VPS.
#
# Uso:  bash motor.sh
# ═══════════════════════════════════════════════════════════

set -e
VERDE=$'\033[0;32m'; AMARELO=$'\033[0;33m'; VERM=$'\033[0;31m'; FIM=$'\033[0m'
ok(){   echo "${VERDE}✓${FIM} $1"; }
aviso(){ echo "${AMARELO}!${FIM} $1"; }
erro(){ echo "${VERM}✗${FIM} $1"; exit 1; }
titulo(){ echo; echo "── $1 ──"; }

BASE="$HOME/motor"
LLAMA="$BASE/llama.cpp"
MODELOS="$BASE/modelos"

echo
echo "SISTEMA ABSOLUTO — instalação do motor próprio"
echo "Motor próprio: sem token pago, sem depender de ninguém."
echo

# ─────────────────────────────────────────────
titulo "1. Conferindo o ambiente"

[ -d "/data/data/com.termux" ] || erro "Isto precisa rodar dentro do Termux."
ok "Termux encontrado"

# Termux da Play Store é abandonado e quebra na compilação
if ! command -v pkg >/dev/null 2>&1; then
  erro "Termux incompleto. Baixe do F-Droid ou do GitHub, nunca da Play Store."
fi

RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
RAM_GB=$((RAM_KB / 1024 / 1024))
ok "Memória do aparelho: ${RAM_GB} GB"

LIVRE=$(df -k "$HOME" | tail -1 | awk '{print $4}')
LIVRE_GB=$((LIVRE / 1024 / 1024))
ok "Espaço livre: ${LIVRE_GB} GB"
[ "$LIVRE_GB" -lt 4 ] && aviso "Menos de 4 GB livres. Pode faltar espaço para o modelo."

NUCLEOS=$(nproc)
ok "Núcleos de processamento: ${NUCLEOS}"

# ─────────────────────────────────────────────
titulo "2. Instalando as ferramentas de compilação"

pkg update -y >/dev/null 2>&1 || true
pkg upgrade -y >/dev/null 2>&1 || true
pkg install -y git cmake clang make libandroid-spawn wget >/dev/null 2>&1
ok "Compilador e utilitários instalados"

# Vulkan deixa a GPU do celular trabalhar junto — quando existe, dobra a velocidade
USA_VULKAN=0
if pkg install -y vulkan-tools vulkan-headers vulkan-loader-android >/dev/null 2>&1; then
  if [ -f /system/lib64/libvulkan.so ] || [ -f /vendor/lib64/libvulkan.so ]; then
    USA_VULKAN=1
    ok "GPU disponível via Vulkan — vai acelerar"
  else
    aviso "Sem driver Vulkan visível. Roda no processador, mais devagar."
  fi
else
  aviso "Vulkan indisponível. Roda no processador."
fi

# ─────────────────────────────────────────────
titulo "3. Baixando o motor"

mkdir -p "$BASE" "$MODELOS"
if [ -d "$LLAMA/.git" ]; then
  cd "$LLAMA" && git pull --quiet || true
  ok "Motor atualizado"
else
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LLAMA" >/dev/null 2>&1
  ok "Motor baixado"
fi

# ─────────────────────────────────────────────
titulo "4. Compilando"
echo "   Isso leva de 10 a 30 minutos. Deixe a tela ligada."
echo

cd "$LLAMA"
FLAGS="-DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_LLAMAFILE=OFF"
[ "$USA_VULKAN" = "1" ] && FLAGS="$FLAGS -DGGML_VULKAN=ON"

cmake -B build $FLAGS >/dev/null 2>&1 || erro "A configuração falhou. Rode 'pkg upgrade' e tente de novo."
cmake --build build --config Release -j"$NUCLEOS" --target llama-server llama-cli 2>&1 | \
  grep -E "^\[|error|Error" | tail -20 || true

[ -f "$LLAMA/build/bin/llama-server" ] || erro "A compilação não gerou o servidor."
ok "Motor compilado"

# ─────────────────────────────────────────────
titulo "5. Escolhendo o modelo"

# Modelo grande demais para a memória do aparelho trava tudo.
# A escolha é pela RAM real, não pelo desejo.
if [ "$RAM_GB" -ge 8 ]; then
  NOME="qwen2.5-3b-instruct-q4_k_m.gguf"
  URL="https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
  TAM="~2 GB"
elif [ "$RAM_GB" -ge 6 ]; then
  NOME="qwen2.5-1.5b-instruct-q4_k_m.gguf"
  URL="https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
  TAM="~1 GB"
else
  NOME="qwen2.5-0.5b-instruct-q4_k_m.gguf"
  URL="https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
  TAM="~400 MB"
  aviso "Pouca memória: modelo pequeno. Segue instrução com dificuldade."
fi

echo "   Escolhido para ${RAM_GB} GB de RAM: ${NOME} (${TAM})"

if [ -f "$MODELOS/$NOME" ]; then
  ok "Modelo já está aqui"
else
  echo "   Baixando… (use Wi-Fi)"
  wget -q --show-progress -O "$MODELOS/$NOME.parcial" "$URL" || erro "Download falhou."
  mv "$MODELOS/$NOME.parcial" "$MODELOS/$NOME"
  ok "Modelo baixado"
fi

# ─────────────────────────────────────────────
titulo "6. Criando os comandos"

CAMADAS_GPU=0
[ "$USA_VULKAN" = "1" ] && CAMADAS_GPU=99

# Contexto: o app manda prompt com método + memória + ferramentas.
# Curto demais trunca a resposta; longo demais estoura a RAM.
if   [ "$RAM_GB" -ge 12 ]; then CTX=16384
elif [ "$RAM_GB" -ge 8 ];  then CTX=8192
elif [ "$RAM_GB" -ge 6 ];  then CTX=6144
else                            CTX=4096
fi
echo "   Contexto: ${CTX} tokens (ajustado à memória)"

cat > "$BASE/ligar.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
# Liga o motor. Deixe o Termux aberto ou minimizado — não feche.
termux-wake-lock 2>/dev/null || true
echo "Motor subindo em http://127.0.0.1:8080"
echo "No app: Ajustes -> Motor local -> Testar"
echo "Para parar: Ctrl+C"
echo
exec "$LLAMA/build/bin/llama-server" \\
  -m "$MODELOS/$NOME" \\
  --host 127.0.0.1 \\
  --port 8080 \\
  -c $CTX \\
  -t $NUCLEOS \\
  -ngl $CAMADAS_GPU \\
  --no-warmup
EOF
chmod +x "$BASE/ligar.sh"
ok "Comando de ligar criado"

cat > "$BASE/testar.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "Perguntando ao motor…"
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local","messages":[{"role":"user","content":"Responda apenas: ok"}],"max_tokens":20}' \
  | head -c 600
echo
EOF
chmod +x "$BASE/testar.sh"
ok "Comando de teste criado"

# atalhos curtos
grep -q "alias motor=" "$HOME/.bashrc" 2>/dev/null || cat >> "$HOME/.bashrc" <<EOF

# Sistema Absoluto
alias motor='bash $BASE/ligar.sh'
alias motor-teste='bash $BASE/testar.sh'
EOF
ok "Atalhos 'motor' e 'motor-teste' criados"

# ─────────────────────────────────────────────
echo
echo "═══════════════════════════════════════════"
echo "  MOTOR PRÓPRIO INSTALADO"
echo "═══════════════════════════════════════════"
echo
echo "  Ligar:    bash $BASE/ligar.sh"
echo "  Testar:   bash $BASE/testar.sh   (em outra aba do Termux)"
echo
echo "  No app, aba Ajustes -> Motor local:"
echo "    endereço: http://127.0.0.1:8080/v1/chat/completions"
echo "    modelo:   local"
echo "    toque em Testar"
echo
echo "  A partir daí o app responde sem internet."
echo "  Nenhum token, nenhuma conta, nenhum terceiro."
echo
