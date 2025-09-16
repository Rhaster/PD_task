
FROM python:3.11-slim


RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app


WORKDIR /app


COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install -r /app/requirements.txt


COPY . /app


EXPOSE 8000


CMD ["uvicorn", "App.main:app", "--host", "0.0.0.0", "--port", "8000"]
