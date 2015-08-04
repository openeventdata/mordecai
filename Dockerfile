FROM ubuntu:14.04

MAINTAINER Casey Hilland <chilland@caerusassociates.com>

RUN echo "deb http://archive.ubuntu.com/ubuntu/ $(lsb_release -sc) main universe" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y git build-essential wget tar \
python-setuptools python-dev gfortran libopenblas-dev liblapack-dev cmake

RUN easy_install pip
RUN pip install --upgrade pip
ADD . /src
RUN pip install -r /src/requirements.txt

RUN mkdir /home/ubuntu

RUN cd /home/ubuntu; wget https://s3.amazonaws.com/mordecai-geo/GoogleNews-vectors-negative300.bin.gz; \
gunzip GoogleNews-vectors-negative300.bin.gz

RUN cd /home/ubuntu; git clone https://github.com/mit-nlp/MITIE.git
RUN cd /home/ubuntu/MITIE; make MITIE-models
RUN mkdir /home/ubuntu/MITIE/mitielib/build
RUN cd /home/ubuntu/MITIE/mitielib/build; cmake ..
RUN cd /home/ubuntu/MITIE/mitielib/build; cmake --build . --config Release --target install
RUN pip install git+https://github.com/caerusassociates/mitie-py.git

EXPOSE 5000

CMD ["python", "/src/app.py"]
