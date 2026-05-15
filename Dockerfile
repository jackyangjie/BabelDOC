# ============================================================
# BabelDOC Docker Image
# ============================================================
# Build:
#   docker build -t babeldoc .
#
# Run (CLI mode):
#   docker run --rm -v $(pwd):/data babeldoc \
#     --files /data/input.pdf \
#     --openai --openai-api-key sk-xxx
#
# Run (HTTP Executor mode):
#   docker run --rm -p 7860:7860 \
#     -v executor-data:/app/workroot \
#     babeldoc executor
# ============================================================

# --------------- builder stage ---------------
FROM python:3.12-slim AS builder

ENV UV_VERSION=0.6.14 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==${UV_VERSION}

WORKDIR /app
COPY pyproject.toml README.md README_zh.md ./
COPY babeldoc/ babeldoc/

# Install runtime deps into a stashed `.venv`
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev


# --------------- runtime stage ---------------
FROM python:3.12-slim

# System dependencies
#   - libgl1 / libglib2.0-0 : OpenCV / onnxruntime
#   - libzstd1              : pyzstd
#   - fonts-noto-cjk        : CJK font for image text overlay
#   - fontconfig            : fc-cache for font discovery
#   - libreoffice-writer    : convert old .ppt → .pptx (uncomment if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libzstd1 \
    fonts-noto-cjk \
    fontconfig \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# Copy the stashed virtual environment and source code
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Executor workroot (runtime state)
RUN mkdir -p /app/workroot
VOLUME /app/workroot

WORKDIR /data

# Executor server listens on 7860 by default
EXPOSE 7860

# Default: CLI mode (babeldoc)
ENTRYPOINT ["babeldoc"]
CMD ["--help"]

# Override with "executor" to start HTTP server:
#   docker run ... babeldoc executor --host 0.0.0.0 --port 7860
