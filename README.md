# DIG ETL Engine

- Manager for ETK processes, Kafka topic and Logstash.
- Docker image of ETL Engine.
- Docker compose.
- Sample configurations.

# Getting started

Make sure local port 8089, 9200, 9300, 9879, 9880 are not occupied, then all you need to do is:

    docker-compose up -d
    
Access endpoint:

- MyDIG web service GUI: `localhost:9880`
- DIG GUI: `localhost:8089`
- Elastic Search: `localhost:9200`

# Advanced operations

If some of the docker images in docker-compose file are updated, run the following command first.
    
    docker-compose pull

## Manager's endpoints

- `POST /create_project`
    ```
    {
        "project_name" : "new_project"
    }
    ```
    
- `POST /run_etk`
    ```
    {
        "project_name" : "new_project",
        "number_of_workers": 4, // optional
    }
    ```
    
- `POST /kill_etk`
    ```
    {
        "project_name" : "new_project"
    }
    ```

## Docker compose

- Create `.env` file from `.env.example` and change the environment variables.
- Run `docker-compose up` for sandbox version, run `docker-compose -f docker-compose-production.yml up` for production version.

## Docker port mapping

- DIG ETL Engine: 9999 (dig_net)
- Kafka: 9092 (dig_net)
- Zookeeper: 2181 (dig_net)
- ElasticSearch: 9200 (localhost / dig_net), 9300 (localhost / dig_net)
- Sandpaper: 9876 (dig_net)
- DIG App: 8080 (dig_net)
- DIG App Nginx: 8089 (localhost / dig_net)
- myDIG: 9879 (localhost / dig_net), 9880 (localhost / dig_get)

> `dig_net` is the LAN in Docker compose.

## Docker commands for development

build etk base image:

    docker build -t uscisii2/etk:1.0.0 -t uscisii2/etk:latest -f Dockerfile-etk .
    
build etl image:

    docker build -t uscisii2/dig-etl-engine:1.0.0 -t uscisii2/dig-etl-engine:latest .
    
run etl container:

    docker run -d -p 9999:9999 \
    -v $(pwd)/../mydig-projects:/shared_data/projects \
    -v $(pwd)/config_docker_sample.py:/app/dig-etl-engine/config.py \
    uscisii2/dig-etl-engine:1.0.0


## kafka input parameters of interest for Logstash
`auto_offset_resetedit`
- Value type is string
- There is no default value for this setting.

What to do when there is no initial offset in Kafka or if an offset is out of range:  
- earliest: automatically reset the offset to the earliest offset
- latest: automatically reset the offset to the latest offset
- none: throw exception to the consumer if no previous offset is found for the consumer’s group
- anything else: throw exception to the consumer.

`bootstrap_servers`
- Value type is string
- Default value is "localhost:9092"

A list of URLs to use for establishing the initial connection to the cluster. This list should be in the form of host1:port1,host2:port2 These urls are just used for the initial connection to discover the full cluster membership (which may change dynamically) so this list need not contain the full set of servers (you may want more than one, though, in case a server is down).

`consumer_threads`
- Value type is number
- Default value is 1

Ideally you should have as many threads as the number of partitions for a perfect balance — more threads than partitions means that some threads will be idle

`group_id`
- Value type is string
- Default value is "logstash"

The identifier of the group this consumer belongs to. Consumer group is a single logical subscriber that happens to be made up of multiple processors. Messages in a topic will be distributed to all Logstash instances with the same group_id

`topics`
- Value type is array
- Default value is ["logstash"]

A list of topics to subscribe to, defaults to ["logstash"].