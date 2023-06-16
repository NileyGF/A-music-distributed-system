FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /home/akeso/Documents/VSCode/A-music-distributed-system/client/

RUN pip3 freeze > requirements.txt

RUN pip3 install -r requirements.txt

RUN pip3 install pydub
RUN pip3 install mutagen
RUN sudo apt-get install tk
RUN sudo apt-get install python3-tk


COPY . .

ARG type
ARG ip
CMD python3.11 client_class.py type ip