FROM python:3.12-slim

ARG APT_MIRROR=http://mirrors.tencent.com
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# Install runtime dependencies for WeasyPrint, Matplotlib and CJK font support.
RUN sed -i "s|http://deb.debian.org|${APT_MIRROR}|g; s|http://security.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    tzdata \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-noto-cjk \
    fonts-wqy-zenhei \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/logs /app/data

# Copy requirements and install
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" \
    && pip install --no-cache-dir --timeout 120 -r requirements.txt \
    -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}"

# Copy backend code
COPY . .

# Expose port and start
EXPOSE 8888
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8888/api/health', timeout=5)"
CMD ["python", "main.py"]
