FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/crawler/

RUN cd /app/crawler && npm install --omit=dev --silent

ENV PYTHONUNBUFFERED=1

VOLUME ["/data"]

ENTRYPOINT ["python", "-m", "crawler"]
CMD ["--accounts-dir", "/data/accounts", "--db", "/data/crawler.db"]
