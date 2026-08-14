#!/bin/bash
# Put target_repo back to its "before" state so you can run the demo again.
# After this, `pytest` reports 1 failed, 1 passed — test_health is the one the
# agent has to make pass.
cd "$(dirname "$0")/target_repo" || exit 1
cat > main.py <<'EOF'
from fastapi import FastAPI

app = FastAPI(title="Demo API")


@app.get("/")
def root():
    return {"message": "ok"}
EOF
rm -rf __pycache__ .pytest_cache
echo "target_repo reset — /health is gone again, test_health will fail."
