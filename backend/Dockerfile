FROM python:3.11-slim

# Install Icarus Verilog simulation toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    iverilog \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend dependencies and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy project assets required for hardware verification
COPY rtl/ ./rtl/
COPY tb/ ./tb/
COPY scripts/ ./scripts/
COPY backend/ ./backend/

ENV PORT=8000
ENV FRONTEND_ORIGIN=*

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
