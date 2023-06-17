FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /home/akeso/Documents/VSCode/A-music-distributed-system/client/

RUN pip3 freeze > requirements.txt

RUN pip3 install -r requirements.txt

RUN pip3 install pydub
RUN pip3 install mutagen
RUN apt-get update && \
    apt-get install -y python3-tk
RUN pip install customtkinter
RUN pip install pygame
RUN apt-get install libglib2.0-dev

ENV DISPLAY=127.0.0.1:0.0

COPY . .

ARG type
ARG ip
CMD python3.11 client_class.py type ip