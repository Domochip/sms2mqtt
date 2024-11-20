FROM python:3.6.13-alpine3.12

RUN apk add --no-cache gammu-dev

RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
     && pip install python-gammu paho-mqtt certifi\
     && apk del .build-deps gcc musl-dev

WORKDIR /app

COPY sms2mqtt.py .

ENTRYPOINT ["python", "/app/sms2mqtt.py"]