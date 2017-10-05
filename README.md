# DIG ETL Engine

- Manager for ETK processes, Kafka topic and Logstash.
- Docker image of ETL Engine.
- Docker compose of myDIG.
- Sample configurations.

Part of the project [DIG](http://usc-isi-i2.github.io/dig/).

# Getting started

Install [Docker](https://docs.docker.com/engine/installation/) and [Docker Compose](https://docs.docker.com/compose/install/). 

> If you are working on [Mac](https://docs.docker.com/docker-for-mac/#advanced) or [Windows](https://docs.docker.com/docker-for-windows/#advanced), **make sure you allocate enough memory (5GB or more is recommended) to docker virtual machine**. In Linux, Docker is built on LXC of kernel, the latest version of kernel and enough memory on host are required.

> If the memory is not enough, some service processes may not be fired up, or they will be killed by OS.

Clone this repository.

    git clone https://github.com/usc-isi-i2/dig-etl-engine.git
    
Create environment file from example environment file.
 
    cp ./dig-etl-engine/.env.example ./dig-etl-engine/.env
    
Create projects' directory.

    mkdir ./mydig-projects

Make sure local port 12497 is not occupied, then all you need to do is:

    docker-compose up -d
    
> Docker commands acquire high privilege in some of the OS, add `sudo` before them.

> Wait a couple of minutes to ensure all the services are up.
    
Access endpoint:

- MyDIG web service GUI: `http://localhost:12497/mydig/ui/`
- Elastic Search: `http://localhost:12497/es`

To stop docker containers, run following command

    docker-compose stop
    
# Verify installation

The file `./datasets/elicit_20.jl` can be used for verification, it is formatted in [JSON LINES](http://jsonlines.org/) and includes 20 documents. Each document at least contains `doc_id` (unique string), `url`, `raw_content` (encoded in UTF-8), meanwhile can not contain `type` (will be converted to `original_type`).

In web browser, open up `MyDIG web service GUI` at `http://localhost:12497/mydig/ui/`, create a project named `test`, then click `open` to open project detail configuration page.

Click `import json lines file` button on right, upload `elicit_20.jl`, then you will see `ce_news_article.org` shows up in TLD (top level domain) table. Enter `15` in the `Desired number of docs to run` input box and click `update` button. Then the desired number of this TLD will be update to `15`.

Click red button named `recreate knowledge graph` to create a new knowledge graph and upload the data. Wait a few seconds, you should see updates in the column `ES` (this number will be less than or equal to desired number).
 
Finally, click `DIG GUI` button to open and test on DIG.

# Detailed function introduction

- `recreate knowledge` is used to recreate the index in elastic search and regenerate ETK config. All the desired data marked previously will be re-added and re-run automatically. This function will also turn on pipeline. Only use it after you did some incompatible changes.

> Incompatible changes: upload new glossaries, update fields, update tags, update Landmark rules.

- `turn on pipleine` is used to fire up ETK processes with previous config. If you only want to add some new data, use this function. ETK processes will exit after idle for 1 hour. Then this button will turn into enable.

# Advanced operations

If some of the docker images in docker-compose file are updated, run the following command first.
    
    docker-compose pull <service name>
    
Defaultly, 4 process of ETK will run, if you want to run multi ETK processes, please refer to `./mydig-webservice/config_docker.py`, set the value of `etl.number_of_workers` (less or equal to the value of`input_partitions` in `config_docker_sandbox.py`) and restart docker-compose.

The data in kafka queue will be cleaned after two days.

On Linux, if logstash is not up, do `chmod 666 logstash/sandbox/settings/logstash.yml`.

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

- dig_net:
    - DIG ETL Engine: 9999
    - Kafka: 9092
    - Zookeeper: 2181
    - ElasticSearch: 9200, 9300
    - Sandpaper: 9876
    - DIG UI: 8080
    - myDIG: 9879, 9880
    - Landmark Tool: 3333, 5000, 3306
    - Logstash: 5044, 9600
    - Nginx: 80
- localhost:
    - Nginx: 12497

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
