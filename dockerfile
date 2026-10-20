FROM jenkins/jenkins:lts-jdk17

USER root
RUN sudo apt update && apt-get install -y --no-install-recommends \
        qemu-system-arm ipmtool firefox-esr xvfb curl python3-venv \
        && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install -r /tmp/requirements.txt

USER jenkins