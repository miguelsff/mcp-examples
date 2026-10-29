FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=azure \
    AUTH_MODE=entra

WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.lock \
    && groupadd --gid 10001 mcp \
    && useradd --uid 10001 --gid mcp --no-create-home mcp
COPY --chown=mcp:mcp bank_mcp ./bank_mcp
COPY --chown=mcp:mcp config ./config
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "bank_mcp"]
