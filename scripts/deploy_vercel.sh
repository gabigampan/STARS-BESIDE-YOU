#!/usr/bin/env bash
# Build the web app key-free from the current working tree and deploy it to Vercel.
#
#   Usage (from the repository root, with the token in the environment, never on the command line):
#     set -a; . /root/.config/stars/vercel.env; set +a
#     bash scripts/deploy_vercel.sh            # production deployment (default)
#     bash scripts/deploy_vercel.sh --preview  # preview deployment (rehearsal)
#
# The script refuses to run when VERCEL_TOKEN is missing, and refuses to deploy when the built
# folder contains the local Cesium ion token, the Vercel token, or any JWT-shaped string that is
# not part of the CesiumJS library itself. It never prints the token.
# Optional: DEPLOY_APP_DIR=/path/to/app builds another checkout of app/ (used for rehearsals).
set -euo pipefail

TARGET=production
case "${1:-}" in
  "" | --prod | --production) TARGET=production ;;
  --preview) TARGET=preview ;;
  *) echo "usage: $0 [--preview|--prod]" >&2; exit 2 ;;
esac

VERCEL_CLI="vercel@65.16.0"
PROJECT="stars-beside-you"
MAX_FILE_BYTES=$((100 * 1024 * 1024))   # Vercel CLI upload limit on the Hobby plan (100 MB)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${DEPLOY_APP_DIR:-$REPO_ROOT/app}"
LOCAL_ENV="$REPO_ROOT/app/.env.local"

fail() { echo "deploy_vercel: REFUSED: $*" >&2; exit 1; }

[ -n "${VERCEL_TOKEN:-}" ] || fail "VERCEL_TOKEN is not set in the environment (set -a; . /root/.config/stars/vercel.env; set +a)."
[ -f "$APP_DIR/package.json" ] || fail "no app at $APP_DIR"
[ -f "$REPO_ROOT/app/vercel.json" ] || fail "app/vercel.json is missing"

echo "== 1/5 install ($APP_DIR)"
cd "$APP_DIR"
npm ci --no-audit --no-fund --loglevel=error

echo "== 2/5 key-free build"
rm -rf dist
# Process variables take precedence over .env.local in Vite: ion stays off and its token empty.
# vite.config.ts also replaces import.meta.env.VITE_CESIUM_ION_TOKEN with '' unless VITE_USE_ION=1.
env VITE_USE_ION=0 VITE_CESIUM_ION_TOKEN= npm run build

echo "== 3/5 token scan"
# a) the local ion token value, anywhere (text or binary)
if [ -f "$LOCAL_ENV" ]; then
  ION_VALUE="$(grep -E '^VITE_CESIUM_ION_TOKEN=' "$LOCAL_ENV" | head -1 | cut -d= -f2- | tr -d "\"' \r")" || true
  if [ -n "${ION_VALUE:-}" ] && grep -rqaF -- "$ION_VALUE" dist; then
    unset ION_VALUE; fail "the Cesium ion token from app/.env.local is in dist/"
  fi
  unset ION_VALUE
fi
# b) the Vercel token itself
if grep -rqaF -- "$VERCEL_TOKEN" dist; then fail "the Vercel token is in dist/"; fi
# c) any JWT-shaped string in text files that the CesiumJS package does not ship itself
#    (CesiumJS embeds its own public default ion token in Ion.js; the app never uses it in key-free mode)
CESIUM_JS="$APP_DIR/node_modules/cesium/Build/Cesium/index.js"
JWT_RE='eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'
TEXT_EYJ=$( (grep -rlI 'eyJ' dist || true) | wc -l)
FOREIGN=0
while IFS= read -r jwt; do
  [ -z "$jwt" ] && continue
  if ! grep -qF -- "$jwt" "$CESIUM_JS"; then FOREIGN=$((FOREIGN + 1)); fi
done < <(grep -rEohI "$JWT_RE" dist | sort -u)
echo "text files containing 'eyJ': $TEXT_EYJ; JWT-shaped strings not from CesiumJS: $FOREIGN"
[ "$FOREIGN" -eq 0 ] || fail "$FOREIGN JWT-shaped string(s) in dist/ that are not part of CesiumJS"

echo "== 4/5 size check"
TOTAL=$(du -sb dist | cut -f1)
FILES=$(find dist -type f | wc -l)
BIG=$(find dist -type f -size +"${MAX_FILE_BYTES}"c)
echo "dist: $((TOTAL / 1024 / 1024)) MB in $FILES files; largest:"
find dist -type f -printf '%s %p\n' | sort -rn | awk 'NR<=5 {printf "  %6.1f MB  %s\n", $1/1048576, $2}'
[ -z "$BIG" ] || fail "file(s) over 100 MB: $BIG"
[ "$FILES" -lt 15000 ] || fail "more than 15000 files"

echo "== 5/5 deploy ($TARGET) to Vercel project $PROJECT"
cp "$REPO_ROOT/app/vercel.json" dist/vercel.json
export VERCEL_TELEMETRY_DISABLED=1
ARGS=(deploy dist --yes --project "$PROJECT" --create-if-missing)
[ "$TARGET" = production ] && ARGS+=(--prod)
# The CLI reads VERCEL_TOKEN from the environment; it is never passed as an argument.
OUT="$(mktemp)"
npx -y "$VERCEL_CLI" "${ARGS[@]}" | tee "$OUT"
URL=$(grep -Eo 'https://[A-Za-z0-9.-]+\.vercel\.app' "$OUT" | head -1 || true)
rm -f "$OUT"
[ -n "$URL" ] || fail "the Vercel CLI did not print a deployment URL (see its output above)"
echo "DEPLOYED ($TARGET): $URL"
[ "$TARGET" = production ] && echo "Production alias: https://$PROJECT.vercel.app"
exit 0
