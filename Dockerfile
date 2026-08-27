FROM python:3.14-slim

WORKDIR /app

COPY app.py games.py tests/ /app/
COPY static/ /app/static/
COPY deploy/ /app/deploy/

RUN pip install --no-cache-dir -r /dev/null || true

EXPOSE 9581

CMD ["python", "app.py"]
