FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip python3.11-venv \
    nodejs npm \
    git curl wget zip unzip nano \
    chromium-browser \
    xvfb x11vnc websockify novnc openbox \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install playwright dependencies
RUN pip3 install playwright && playwright install chromium

# Create ubuntu user with passwordless sudo
RUN useradd -m ubuntu && echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Working directory
WORKDIR /home/ubuntu
USER ubuntu

CMD ["/bin/bash"]
