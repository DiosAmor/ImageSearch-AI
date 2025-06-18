FROM postgres:17

# postgis 설치
RUN apt-get update && \
    apt-get install -y postgresql-17-postgis-3

# pgvector 설치
RUN apt-get install -y postgresql-17-pgvector
