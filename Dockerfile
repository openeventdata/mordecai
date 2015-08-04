FROM python:2-onbuild

MAINTAINER Casey Hilland <chilland@caerusassociates.com>

RUN apt-get update && apt-get install -y git build-essential wget tar \
python-setuptools python-dev gfortran libopenblas-dev liblapack-dev cmake

RUN wget https://s3.amazonaws.com/mordecai-geo/GoogleNews-vectors-negative300.bin.gz; \
gunzip GoogleNews-vectors-negative300.bin.gz

RUN git clone https://github.com/mit-nlp/MITIE.git
RUN cd MITIE; make MITIE-models
RUN mkdir MITIE/mitielib/build
RUN cd MITIE/mitielib/build; cmake ..
RUN cd MITIE/mitielib/build; cmake --build . --config Release --target install
RUN pip install git+https://github.com/caerusassociates/mitie-py.git

EXPOSE 5000

CMD ["python", "./app.py"]
