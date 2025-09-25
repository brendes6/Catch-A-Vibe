FROM python:3.11-slim

WORKDIR /app

ENV FASTEMBED_CACHE_DIR=/app/model_cache 

RUN mkdir -p ${FASTEMBED_CACHE_DIR}

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from fastembed import TextEmbedding; TextEmbedding()"


COPY src/ .

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]