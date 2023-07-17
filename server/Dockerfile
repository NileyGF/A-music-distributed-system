FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /home/akeso/Documents/VSCode/A-music-distributed-system/server

RUN pip3 freeze > requirements.txt

RUN pip3 install -r requirements.txt

RUN pip3 install pydub
RUN pip3 install mutagen
RUN pip3 install ffmpeg

RUN apt-get update
RUN apt-get -y install ffmpeg
COPY . .

ARG TYPE_SERVER
ARG IP_ADDRESS

ENV SERVER_TYPE=$TYPE_SERVER
ENV SERVER_IP=$IP_ADDRESS


RUN chmod +x server_class.py
CMD python3.11 server_class.py SERVER_TYPE SERVER_IP