# syntax=docker/dockerfile:1
FROM python:3.11-slim

LABEL maintainer="空白色不语 <https://github.com/kongbai9420>"
LABEL description="云枢 (YunShu) - 多品牌服务器智能温控与混合集群监控运维平台 (Docker Web Edition)"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies: ipmitool, curl, tzdata, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ipmitool \
    curl \
    tzdata \
    ca-certificates \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, default configs and entrypoint
COPY src/ /app/src/
COPY config.ini /app/config.ini.default
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create persistent storage directories
RUN mkdir -p /app/data /app/logs /app/sdr_cache

# Expose default Web UI port
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/healthz || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/web_server.py", "--host", "0.0.0.0", "--port", "8080"]
