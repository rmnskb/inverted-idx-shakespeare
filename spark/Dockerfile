# Courtesy of https://karlchris.github.io/data-engineering/projects/spark-docker

FROM python:3.11-bullseye AS spark-base

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  sudo \
  curl \
  vim \
  zip \
  unzip \
  rsync \
  openjdk-11-jdk \
  build-essential \
  software-properties-common \
  awscli \
  ssh && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Optional env variables
ENV SPARK_HOME=${SPARK_HOME:-"/opt/spark"}
ENV HADOOP_HOME=${HADOOP_HOME:-"/opt/hadoop"}

RUN mkdir -p ${HADOOP_HOME} && mkdir -p ${SPARK_HOME}
WORKDIR ${SPARK_HOME}

ENV SPARK_VERSION=3.5.5

# Download spark
RUN mkdir -p ${SPARK_HOME} \
  && curl https://dlcdn.apache.org/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz -o spark-${SPARK_VERSION}-bin-hadoop3.tgz \
  && tar xvzf spark-${SPARK_VERSION}-bin-hadoop3.tgz --directory /opt/spark --strip-components 1 \
  && rm -rf spark-${SPARK_VERSION}-bin-hadoop3.tgz


# Install Python dependencies
COPY requirements.spark.txt .
RUN pip install -r requirements.spark.txt

# Environment variables for Spark
ENV PATH="/opt/spark/sbin:/opt/spark/bin:${PATH}"
ENV SPARK_HOME="/opt/spark"
ENV SPARK_MASTER="spark://spark-master:7077"
ENV SPARK_MASTER_HOST="spark-master"
ENV SPARK_MASTER_PORT="7077"
ENV PYSPARK_PYTHON="python3"

COPY conf/spark-defaults.conf "$SPARK_HOME/conf"

RUN chmod u+x /opt/spark/sbin/* && \
  chmod u+x /opt/spark/bin/*

ENV PYTHONPATH=$SPARK_HOME/python/:$PYTHONPATH

# COPY entrypoint.sh .
# RUN chmod u+x /opt/spark/entrypoint.sh
# 
# ENTRYPOINT [ "./entrypoint.sh" ]
# CMD [ "bash" ]

ENTRYPOINT ["/bin/bash"]

