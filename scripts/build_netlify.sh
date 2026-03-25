#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/netlify_site"
APP_NAME="${NETLIFY_APP_NAME:-Voice-First Task App}"
API_BASE_URL="${NETLIFY_API_BASE_URL:-}"

mkdir -p "${OUTPUT_DIR}"

cp "${ROOT_DIR}/app/static/app.js" "${OUTPUT_DIR}/app.js"
cp "${ROOT_DIR}/app/static/styles.css" "${OUTPUT_DIR}/styles.css"

cat > "${OUTPUT_DIR}/config.js" <<EOF
window.APP_CONFIG = Object.assign({}, window.APP_CONFIG, {
    API_BASE_URL: "${API_BASE_URL}"
});
EOF

sed \
    -e "s|{{ app_name }}|${APP_NAME}|g" \
    -e 's|href="/static/styles.css"|href="/styles.css"|g' \
    -e 's|src="/static/config.js"|src="/config.js"|g' \
    -e 's|src="/static/app.js"|src="/app.js"|g' \
    "${ROOT_DIR}/app/templates/index.html" > "${OUTPUT_DIR}/index.html"

echo "Netlify site generated in ${OUTPUT_DIR}"
