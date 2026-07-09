FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install build deps (keeps wheels working for packages that need them)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY vendorai/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY vendorai /app

EXPOSE 8000 8501

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
