#!/usr/bin/env bash
# Freeze the FastAPI backend into a standalone sidecar with PyInstaller.
# Output: dist-backend/stockbrain-server/  (onedir: exe + _internal/).
# Electron bundles this folder as an extraResource; it spawns the exe inside.
set -e
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
[ -d .venv ] && source .venv/bin/activate
pip install -q pyinstaller

rm -rf dist-backend build-backend stockbrain-server.spec

# onedir is more reliable than onefile for heavy native deps (onnxruntime, chromadb).
# collect-all pulls each package's submodules + data + binaries + metadata.
pyinstaller backend/server.py \
  --name stockbrain-server --onedir --noconfirm --log-level WARN \
  --distpath dist-backend --workpath build-backend \
  --collect-all chromadb \
  --collect-all fastembed \
  --collect-all onnxruntime \
  --collect-all tokenizers \
  --collect-submodules uvicorn \
  --copy-metadata chromadb --copy-metadata fastembed --copy-metadata tqdm \
  --copy-metadata opentelemetry-sdk --copy-metadata pyyaml --copy-metadata numpy \
  --hidden-import anthropic --hidden-import frontmatter --hidden-import curl_cffi

echo "✓ Backend frozen → dist-backend/stockbrain-server/stockbrain-server"
echo "  (first vault sync downloads the embedding model to your HF cache, ~130MB)"
