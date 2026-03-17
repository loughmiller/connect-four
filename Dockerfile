FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir flask gunicorn

COPY src/ src/

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "src.server:app"]
