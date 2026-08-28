FROM python:3.13-slim-trixie

ARG UID=1000
ARG GID=1000

ENV TZ=UTC

RUN pip install --no-cache-dir --upgrade pip setuptools "wheel>=0.46.2"

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN groupadd -g "${GID}" devgroup && \
    useradd --create-home --no-log-init -s /bin/bash -u "${UID}" -g "${GID}" devuser

RUN mkdir -p /vscode && \
    chown devuser:root /vscode && \
    chmod 770 /vscode

USER devuser

WORKDIR /home/devuser

COPY --chown=devuser:devgroup requirements.txt /home/devuser/requirements.txt

ENV PYTHONPATH="/project/backend:${PYTHONPATH}"

ENV PATH="/home/devuser/.local/bin:${PATH}"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

WORKDIR /project


