FROM docker.uclv.cu/python:3.11-slim as build

WORKDIR /Users/josue/Downloads/Dist/d_system

RUN pip3 install -r /A-music-distributed-system/requirements.txt

COPY . /Users/josue/Downloads/Dist/d_system

CMD ["python3.11", "./server_class.py"]