FROM python:3-alpine

RUN echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/community' >> /etc/apk/repositories
RUN apk update
RUN apk add --no-cache gammu-dev=1.39.0-r2

RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
     && pip install python-gammu paho-mqtt \
     && apk del .build-deps gcc musl-dev

WORKDIR /app

COPY sms2mqtt.py .

ENTRYPOINT ["python", "/app/sms2mqtt.py"]