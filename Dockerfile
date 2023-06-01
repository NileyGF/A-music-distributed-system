FROM python:3.11.2

WORKDIR /Users/josue/Downloads/Dist/d_system

RUN pip3 install -r requeriments.txt

COPY . /Users/josue/Downloads/Dist/d_system

CMD ["python3.11", "./server_class.py"]