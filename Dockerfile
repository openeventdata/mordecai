FROM ubuntu:14.04

MAINTAINER Casey Hilland <chilland@caerusassociates.com>

RUN echo "deb http://archive.ubuntu.com/ubuntu/ $(lsb_release -sc) main universe" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y git build-essential wget tar \
python-setuptools python-dev gfortran libopenblas-dev liblapack-dev cmake \
python-numpy python-scipy

RUN easy_install pip
RUN pip install --upgrade pip
ADD . /src
RUN pip install -r /src/requirements.txt

RUN mkdir /home/ubuntu
WORKDIR /home/ubuntu

RUN wget https://s3.amazonaws.com/mordecai-geo/GoogleNews-vectors-negative300.bin.gz; \
gunzip GoogleNews-vectors-negative300.bin.gz

RUN git clone https://github.com/mit-nlp/MITIE.git
WORKDIR /home/ubuntu/MITIE

RUN wget http://sourceforge.net/projects/mitie/files/binaries/MITIE-models-v0.2.tar.bz2
RUN tar xjf MITIE-models-v0.2.tar.bz2
RUN mkdir /home/ubuntu/MITIE/mitielib/build
RUN cd mitielib/build; cmake ..
RUN cd mitielib/build; cmake --build . --config Release --target install
RUN pip install git+https://github.com/caerusassociates/mitie-py.git

EXPOSE 5000

CMD ["python", "/src/app.py"]
