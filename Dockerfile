FROM python:3-slim

ENV TZ="Europe/Amsterdam"

COPY requirements.txt /

RUN apt-get update && apt-get install -y build-essential libffi-dev tzdata wget \
    && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xvf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && python3 -m pip install --upgrade pip \
    && pip3 install --no-cache-dir -U -I -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

VOLUME /config

WORKDIR /app
COPY *.py .
COPY config.ini .

CMD [ "python", "-u", "./3cqsbot.py" ]