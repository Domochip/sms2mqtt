FROM python:3.6.13-alpine3.12

RUN echo 'http://dl-cdn.alpinelinux.org/alpine/v3.12/community' >> /etc/apk/repositories
RUN apk update
RUN apk add --no-cache gammu-dev

RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
     && pip install python-gammu paho-mqtt \
     && apk del .build-deps gcc musl-dev

WORKDIR /app

COPY newsms2mqtt.py .

ENTRYPOINT ["python", "/app/newsms2mqtt.py"]