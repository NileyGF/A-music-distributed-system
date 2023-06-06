FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /Users/josue/Downloads/Dist/d_system/A-music-distributed-system/server/

RUN pip3 freeze > requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD ["python3.11", "server_class.py"]