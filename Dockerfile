FROM python:3.9 as builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential libcairo2-dev libgirepository1.0-dev \
    gir1.2-ostree-1.0 flatpak

ADD requirements.txt /requirements.txt
RUN python -m venv /venv && \
    /venv/bin/pip install -r requirements.txt \
    && rm -f /requirements.txt

FROM python:3.9-slim

EXPOSE 8000

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libcairo2 gir1.2-ostree-1.0 flatpak && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    flatpak --user remote-add flathub https://flathub.org/repo/flathub.flatpakrepo

COPY ./app /app
COPY ./data /data
COPY --from=builder /venv /venv

ENTRYPOINT ["/venv/bin/uvicorn", "--app-dir", "/", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app", "--reload-dir", "/data"]
