FROM python:3.8-slim-buster

COPY config/requirements.txt requirements.txt
COPY main.py

RUN pip3 install -r requirements.txt

CMD [ "python", "./main.py" ]
