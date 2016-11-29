FROM chilland/pymitie:v0.0.1

MAINTAINER Andy Halterman <ahalterman0@gmail.com>

RUN apt-get update && apt-get install -y build-essential \
        python-setuptools python-dev \
        python-numpy python-scipy

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY app.py /usr/src/
COPY config.ini /usr/src/
ADD /resources /usr/src/resources
WORKDIR /usr/src/

EXPOSE 5000

CMD ["python", "app.py"]
