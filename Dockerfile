FROM jenkins/jenkins:lts

USER root
RUN apt update && apt-get install -y --no-install-recommends \
        qemu-system-arm ipmitool firefox-esr xvfb xauth curl python3-venv \
        && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install -r /tmp/requirements.txt

USER jenkins