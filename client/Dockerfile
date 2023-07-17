FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /home/akeso/Documents/VSCode/A-music-distributed-system/client/

RUN pip3 freeze > requirements.txt

RUN pip3 install -r requirements.txt

RUN pip3 install pydub
RUN pip3 install mutagen
RUN pip3 install ffmpeg
RUN pip3 install ffprobe
RUN pip3 install flask_bootstrap
RUN apt-get update
RUN apt-get -y install ffmpeg
# RUN apt-get update
# RUN apt-get -y install build-essential
# #     apt-get install -y python3-tk
# RUN apt-get -y install git curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0
# # RUN pip install customtkinter
# RUN pip3 install simpleaudio
# RUN apt-get install libglib2.0-dev
RUN pip3 install flask
# ENV DISPLAY=127.0.0.1:0.0
COPY . .
EXPOSE 5000

# CMD python3.11 app.py
