FROM python:3.9.13-slim

COPY . /App/
RUN python -m pip install --upgrade pip \
    && pip install -r /App/requirements.txt

WORKDIR /App

ENTRYPOINT ["./start.sh", ""]
