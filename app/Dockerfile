FROM python:3.12-slim

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 5000

ENV FLASK_APP=src.app
ENV FLASK_RUN_HOST=0.0.0.0

CMD ["python", "-u", "src/app.py"]
