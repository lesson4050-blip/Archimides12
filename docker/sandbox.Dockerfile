FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip python3.11-venv \
    git curl wget zip unzip nano \
    chromium-browser \
    xvfb x11vnc websockify novnc openbox \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS via NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node --version \
    && npm --version

# Install playwright (pip package + system deps as root)
RUN pip3 install playwright
RUN playwright install-deps chromium || true
RUN apt-get update && apt-get install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 || true

# Create ubuntu user with passwordless sudo
RUN useradd -m ubuntu && echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Working directory
WORKDIR /home/ubuntu
USER ubuntu

# Install Chromium browser for ubuntu user (not root)
RUN playwright install chromium

CMD ["/bin/bash"]
