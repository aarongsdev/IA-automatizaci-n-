#!/usr/bin/env bash
# setup_fork.sh — Aplica la adaptación MoneyPrinterTurbo en un solo comando.
#
# Uso:
#   chmod +x setup_fork.sh
#   GH_TOKEN=ghp_xxxx ./setup_fork.sh
#
# Qué hace:
#   1. Hace fork de harry0703/MoneyPrinterTurbo en tu cuenta GitHub
#   2. Clona el fork localmente
#   3. Copia todos los archivos de adaptación encima
#   4. Crea un commit y hace push
#
# Requisitos: git, curl, jq  (en GitHub Actions ya están disponibles)

set -euo pipefail

# ── Configuración ──────────────────────────────────────────────────────────────
UPSTREAM="harry0703/MoneyPrinterTurbo"
ADAPTATION_REPO="https://github.com/aarongsdev/IA-automatizaci-n-"
ADAPTATION_BRANCH="claude/dale-analysis-jqg5dx"
TARGET_BRANCH="main"
WORK_DIR="${TMPDIR:-/tmp}/mpt_setup_$$"

# Token de GitHub (necesita permisos: repo, workflow)
GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$GH_TOKEN" ]]; then
  echo "❌  ERROR: define GH_TOKEN=ghp_xxxx antes de ejecutar este script."
  exit 1
fi

# Detectar usuario de GitHub desde el token
GH_USER=$(curl -fsSL -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/user | jq -r '.login')
if [[ -z "$GH_USER" || "$GH_USER" == "null" ]]; then
  echo "❌  ERROR: token inválido o sin acceso a la API de GitHub."
  exit 1
fi
echo "✅  Usuario GitHub: $GH_USER"

FORK_REPO="$GH_USER/MoneyPrinterTurbo"
FORK_URL="https://x-access-token:${GH_TOKEN}@github.com/${FORK_REPO}.git"

# ── 1. Fork ────────────────────────────────────────────────────────────────────
echo ""
echo "── 1/4  Creando fork de $UPSTREAM …"
FORK_RESPONSE=$(curl -fsSL -X POST \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${UPSTREAM}/forks" \
  -d '{"default_branch_only":true}')

FORK_HTML=$(echo "$FORK_RESPONSE" | jq -r '.html_url // empty')
if [[ -z "$FORK_HTML" ]]; then
  # El fork puede ya existir — verificar
  FORK_HTML=$(curl -fsSL -H "Authorization: token $GH_TOKEN" \
    "https://api.github.com/repos/${FORK_REPO}" | jq -r '.html_url // empty')
  if [[ -z "$FORK_HTML" ]]; then
    echo "❌  No se pudo crear ni encontrar el fork: $FORK_RESPONSE"
    exit 1
  fi
  echo "   (fork ya existía) $FORK_HTML"
else
  echo "   Fork creado: $FORK_HTML"
fi

# GitHub tarda unos segundos en preparar el fork
echo "   Esperando que el fork esté listo…"
for i in $(seq 1 12); do
  STATUS=$(curl -fsSL -H "Authorization: token $GH_TOKEN" \
    "https://api.github.com/repos/${FORK_REPO}" | jq -r '.size // 0')
  if [[ "$STATUS" -gt 0 ]]; then break; fi
  sleep 5
done

# ── 2. Clonar fork ─────────────────────────────────────────────────────────────
echo ""
echo "── 2/4  Clonando fork …"
mkdir -p "$WORK_DIR"
git clone --depth=1 "$FORK_URL" "$WORK_DIR/MoneyPrinterTurbo"
cd "$WORK_DIR/MoneyPrinterTurbo"
git checkout -b adaptation-oficial 2>/dev/null || git checkout adaptation-oficial

# ── 3. Descargar y aplicar archivos de adaptación ──────────────────────────────
echo ""
echo "── 3/4  Aplicando archivos de adaptación …"

ADAPT_RAW="https://raw.githubusercontent.com/aarongsdev/IA-automatizaci-n-/${ADAPTATION_BRANCH}"

download() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  curl -fsSL "${ADAPT_RAW}/${src}" -o "$dst"
  echo "   ✓ $dst"
}

# Workflow de GitHub Actions
download ".github/workflows/daily_episode.yml" ".github/workflows/daily_episode.yml"

# Servicios nuevos
download "app/services/official_publish.py"  "app/services/official_publish.py"
download "app/services/github_asset_host.py" "app/services/github_asset_host.py"

# task.py modificado (reemplaza el original)
download "app/services/task.py" "app/services/task.py"

# Scripts de orquestación
download "scripts/render_config.py" "scripts/render_config.py"
download "scripts/pick_topic.py"    "scripts/pick_topic.py"
download "scripts/publish_video.py" "scripts/publish_video.py"

# Contenido de temas
download "content/topics_queue.txt" "content/topics_queue.txt"

# Documentación
download "README_ADAPTACION.md"          "README_ADAPTACION.md"
download "APPLY_INSTRUCTIONS.md"         "APPLY_INSTRUCTIONS.md"
download "TECHNICAL_FEASIBILITY.md"      "TECHNICAL_FEASIBILITY.md"
download "ONLINE_AUTOMATION_ANALYSIS.md" "ONLINE_AUTOMATION_ANALYSIS.md"

# config.example.toml con las nuevas claves de official_publish
download "config.example.toml" "config.example.toml"

# ── 4. Commit y push ───────────────────────────────────────────────────────────
echo ""
echo "── 4/4  Commit y push …"
git config user.email "setup-fork@noreply"
git config user.name  "MoneyPrinterTurbo Setup"
git add -A
git commit -m "feat: apply zero-cost GitHub Actions adaptation

- GitHub Actions daily workflow (cron 4 AM UTC + manual trigger)
- official_publish.py: YouTube/TikTok/Instagram official APIs (free)
- github_asset_host.py: temporary public URL via GitHub Releases for Instagram
- task.py: toggle between upload_post and official_publish via config flag
- scripts/render_config.py, pick_topic.py, publish_video.py
- content/topics_queue.txt with 10 starter topics
- Full documentation and setup guide"

git push "$FORK_URL" adaptation-oficial

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅  Listo. Tu fork adaptado está en:"
echo "    https://github.com/${FORK_REPO}/tree/adaptation-oficial"
echo ""
echo "Próximos pasos:"
echo "  1. Ve a https://github.com/${FORK_REPO}/settings/secrets/actions"
echo "     y añade los Secrets descritos en README_ADAPTACION.md"
echo "  2. En tu fork, activa GitHub Actions:"
echo "     Settings → Actions → Allow all actions"
echo "  3. Prueba: Actions → Daily Episode → Run workflow"
echo "════════════════════════════════════════════════════════════════"

# Limpieza
cd /
rm -rf "$WORK_DIR"
