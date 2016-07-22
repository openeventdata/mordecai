FROM ubuntu:14.04

MAINTAINER Andy Halterman <ahalterman0@gmail.com>

RUN echo "deb http://archive.ubuntu.com/ubuntu/ $(lsb_release -sc) main universe" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y git build-essential wget tar \
python-setuptools python-dev gfortran libopenblas-dev liblapack-dev cmake \
python-numpy python-scipy curl

RUN mkdir /home/ubuntu
WORKDIR /home/ubuntu

RUN wget https://s3.amazonaws.com/mordecai-geo/GoogleNews-vectors-negative300.bin.gz

RUN git clone https://github.com/mit-nlp/MITIE.git
WORKDIR /home/ubuntu/MITIE

RUN wget http://sourceforge.net/projects/mitie/files/binaries/MITIE-models-v0.2.tar.bz2
RUN tar --no-same-owner -xjf MITIE-models-v0.2.tar.bz2
RUN mkdir /home/ubuntu/MITIE/mitielib/build
RUN cd mitielib/build; cmake ..
RUN cd mitielib/build; cmake --build . --config Release --target install

RUN easy_install pip
RUN pip install --upgrade pip
RUN pip install git+https://github.com/openeventdata/mitie-py.git
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
ADD . /src

EXPOSE 5000

CMD ["python", "/src/app.py"]
