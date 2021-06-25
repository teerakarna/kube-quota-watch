FROM python:alpine3.12
LABEL maintainer="Albert Asawaroengchai" \
      email="ateerakarna@gmail.com"

# Setup virtualenv and install Python dependencies
RUN python -m venv /opt/venv
ENV PATH=”/opt/venv/bin:/bin:${PATH}”
COPY requirements.txt .
RUN pip install -r requirements.txt

# Prepare files and directories
RUN mkdir /app
COPY src /app
RUN chmod -R 755 /app
WORKDIR /app

# Create appuser
ARG USER=appuser
ARG UID=1001
RUN addgroup -g ${UID} -S ${USER} && adduser -u ${UID} -S ${USER} -G ${USER} --no-create-home
USER $USER
