FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /Users/josue/Downloads/Dist/d_system/A-music-distributed-system/

RUN pip3 freeze > requirements.txt

RUN pip3 install -r requirements.txt

RUN pip3 install pydub
RUN pip3 install mutagen

COPY . .

ARG type
ARG ip
CMD python3.11 client_class.py type ip