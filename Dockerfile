FROM python:3.14-slim

WORKDIR /app

COPY src/ /app/src/
COPY static/ /app/static/
COPY deploy/ /app/deploy/
COPY package.json /app/

ENV PYTHONPATH=/app/src
ENV ZLUNA_HOST=0.0.0.0
ENV ZLUNA_PORT=9581

EXPOSE 9581

CMD ["python", "src/app.py"]
