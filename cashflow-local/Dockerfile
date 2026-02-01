# Multi-stage build following gemini.md standards
# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Copy requirements first for layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

# Create non-root user (gemini.md requirement)
RUN useradd -m -u 1000 -s /bin/bash cashflow

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/cashflow/.local

# Copy application code
COPY --chown=cashflow:cashflow . .

# Ensure the user's local bin is in PATH
ENV PATH=/home/cashflow/.local/bin:$PATH

# Switch to non-root user
USER cashflow

# Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
