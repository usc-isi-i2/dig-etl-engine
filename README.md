# DIG ETL Engine

- Manager for ETK processes and Kafka topic.
- Docker image.

## Docker Image

Build image

    docker build -t dig_etl_engine .
    
Run instance

    docker run -d -p 9999:9999 \
    -v $(pwd)/../mydig-projects:/projects_data \
    -v $(pwd)/config_docker_sample.py:/app/dig-etl-engine/config.py \
    dig_etl_engine