FROM eclipse-temurin:17-jre-jammy

ENV SPARK_VERSION=3.5.1
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark
ENV PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -y python3 python3-pip curl postgresql-client sqlite3 && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fSL https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    | tar -xz -C /opt/ && \
    mv /opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME}

ENV PATH=$SPARK_HOME/bin:$PATH

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir pydantic==1.10.15

COPY . .

# Default entrypoint - can be overridden in docker-compose or at runtime
CMD ["/bin/bash"]
