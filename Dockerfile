FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY data/ data/
COPY evals/ evals/
COPY scripts/ scripts/
COPY input_examples/ input_examples/
COPY run.py README.md ./
RUN mkdir -p logs

ENV SAMPLE_MODE=true
EXPOSE 8000
CMD ["python", "run.py", "--serve"]
