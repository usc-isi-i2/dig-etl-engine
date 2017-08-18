# mydig-webservice
FROM ubuntu:16.04

# all packages and environments are in /app
WORKDIR /app

## install required command utils
RUN apt-get update && apt-get install -y \
    build-essential \
    python \
    python-dev \
    git \
    wget \
    curl \
    default-jdk

# install pip
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py

# install conda
RUN wget https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh && \
    chmod +x Miniconda2-latest-Linux-x86_64.sh && \
    ./Miniconda2-latest-Linux-x86_64.sh -p /app/miniconda -b && \
    rm Miniconda2-latest-Linux-x86_64.sh
ENV PATH=/app/miniconda/bin:${PATH}
RUN conda update -y conda

# download etk
RUN git clone https://github.com/usc-isi-i2/etk.git && \
    cd etk && \
    git checkout development
# create and config conda-env (install flask) for etk
RUN cd etk && conda-env create .
# set etk_env as default env
ENV PATH /app/miniconda/envs/etk_env/bin:$PATH
RUN /bin/bash -c "python -m spacy download en && pip install flask"

# download kafka (for command tools)
RUN wget "http://apache.claz.org/kafka/0.11.0.0/kafka_2.11-0.11.0.0.tgz" && \
    tar -xvzf "kafka_2.11-0.11.0.0.tgz" && rm "kafka_2.11-0.11.0.0.tgz" && \
    mv "kafka_2.11-0.11.0.0" kafka

# install logstash
RUN pip install python-logstash

# persistent data
VOLUME /shared_data

EXPOSE 9999

# add current dir to image at last (or it will break the cache of docker)
RUN mkdir /app/dig-etl-engine
WORKDIR /app/dig-etl-engine
ADD . /app/dig-etl-engine

CMD /bin/bash -c "python manager.py"
