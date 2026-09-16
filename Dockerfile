FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY fuera_gatos ./fuera_gatos
RUN pip install --no-cache-dir ".[mqtt]"
CMD ["fuera-gatos", "run", "-c", "config.yaml"]
