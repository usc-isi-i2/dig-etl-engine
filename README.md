# myDIG Domain-Specific Search
myDIG is a tool to build pipelines that crawl the web, extract information, build a knowledge graph (KG) from the extractions and provide an easy to user interface to query the KG.
The project web page is [DIG](http://usc-isi-i2.github.io/dig/).

You can install myDIG in a laptop or server and use it to build a domain specific search application for any corpus of web pages, CSV, JSON and a variety of other files.

- the installation guide is below
- [user guide](docs/index.md)
- [advanced user guide](docs/advanced.md)

## Installation

### Installation Requirements

- Operating systems: Linux, MacOS or Windows
- System requirements: minimum 8GB of memory

### Installation Instructions

myDIG uses Docker to make installation easy:

Install [Docker](https://docs.docker.com/engine/installation/) and [Docker Compose](https://docs.docker.com/compose/install/). 

> If you are working on [Mac](https://docs.docker.com/docker-for-mac/#advanced) or [Windows](https://docs.docker.com/docker-for-windows/#advanced), **make sure you allocate enough memory to docker virtual machine**. In Linux, Docker is built on LXC of kernel, the latest version of kernel and enough memory on host are required.

> If the memory is not enough, some service processes may not be fired up, or they will be killed by OS.

Clone this repository.

    git clone https://github.com/usc-isi-i2/dig-etl-engine.git
    
myDIG stores your project files on your disk, so you need to tell it where to put the files. You provide this information in the `.env` file in the folder where you installed myDIG. Create the `.env` file by copying the example environment file available in your installation. 
 
    cp ./dig-etl-engine/.env.example ./dig-etl-engine/.env

After you create your `.env` file, open it in a text editor and customize it. Here is a typical `.env` file:

```
COMPOSE_PROJECT_NAME=dig
DIG_PROJECTS_DIR_PATH=/Users/pszekely/Documents/mydig-projects
DOMAIN=localhost
PORT=12497
NUM_ETK_PROCESSES=2
KAFKA_NUM_PARTITIONS=2
DIG_AUTH_USER=admin
DIG_AUTH_PASSWORD=123
```

- `COMPOSE_PROJECT_NAME`: leave this one alone if you only have one myDIG instance. This is the prefix to differentiate docker-compose instances.
- `DIG_PROJECTS_DIR_PATH`: this is the folder where myDIG will store your project files. Make sure the directory exists. The default setting will store your files in `./mydig-projects`, so do `mkdir ./mydig-projects` if you want to use the default folder.
- `DOMAIN`: change this if you install on a server that will be accessed from other machines.
- `PORT`: you can customize the port where myDIG runs.
- `NUM_ETK_PROCESSES`: myDIG uses multi-processing to ingest files. Set this number according to the number of cores you have on the machine. We don't recommend setting it to more than 4 on a laptop.
- `KAFKA_NUM_PARTITIONS`: partition numbers per topic. Set it to the same value as `NUM_ETK_PROCESSES`. It will not affect the existing partition number in Kafka topics unless you drop the Kafka container (you will lose all data in Kafka topics).
- `DIG_AUTH_USER, DIG_AUTH_PASSWORD`: myDIG uses nginx to control access. 

To run myDIG do:

    docker-compose up
    
> Docker commands acquire high privilege in some of the OS, add `sudo` before them.
> You can also run `docker-compose up -d` to run myDIG as a daemon process in the background.
> Wait a couple of minutes to ensure all the services are up.

To stop myDIG do:

    docker-compose stop
    
(Use `docker-compose down` to drop all containers)
    
Once myDIG is running, go to your browser and visit `http://localhost:12497/mydig/ui/`

> Note: myDIG currently works only on Chrome

To use myDIG, look at the [user guide](docs/index.md)

#### Upgrade Issues (16 Nov 2017)

ELK (Elastic Search, LogStash & Kibana) components had been upgraded to 5.6.4 and other services in myDIG also got 
update. What you need to do is:

- Do `docker-compose down`
- Delete directory `DIG_PROJECTS_DIR_PATH/.es`.

You will lose all data and indices in previous Elastic Search and Kibana.

#### Upgrade Issues (20 Oct 2017)

On 20 Oct 2017 there are incompatible changes in Landmark tool (1.1.0), the rules you defined will get deleted when you upgrade to the new system. Please follow these instructions:

- Delete `DIG_PROJECTS_DIR_PATH/.landmark`
- Delete files in `DIG_PROJECTS_DIR_PATH/<project_name>/landmark_rules/*`

There are also incompatible changes in myDIG webservice (1.0.11). Instead of crashing, it will show `N/A`s in TLD table, you need to update the desired number.


### Access Endpoints:

- MyDIG web service GUI: `http://localhost:12497/mydig/ui/`
- Elastic Search: `http://localhost:12497/es/`
- Kibana: `http://localhost:12497/kibana/`
- Kafka Manager: `http://localhost:12497/kafka_manager/`


# Advanced operations and solutions to known issues

- If some of the docker images (which tagged `latest`) in docker-compose file are updated, run `docker-compose pull <service name>` first.

- The data in kafka queue will be cleaned after two days. If you want to delete the data immediately, drop the kafka container.

- If you want to run your own ETK config, name this file to `custom_etk_config.json` and put it in `DIG_PROJECTS_DIR_PATH/<project_name>/working_dir/`. Your `DIG_PROJECTS_DIR_PATH` will be mapped to `/shared_data/projects` in docker, so make sure all the paths you used in config are start with this prefix.

- If you want to clean up all ElasticSearch data, remove `.es` directory in your `DIG_PROJECTS_DIR_PATH`.

- If you want to clean up all Landmark Tool's database data, remove `.landmark` directory in your `DIG_PROJECTS_DIR_PATH`. But this will make published rules untraceable.

- On Linux, if logstash is not up, do `chmod 666 logstash/sandbox/settings/logstash.yml`.

- On Linux, if you can not access docker network from host machine: 1. stop docker containers 2. do `docker network ls` to find out id of `dig_net` and find this id in `ifconfig`, do `ifconfig <interface id> down` to delete this network interface and restart docker service.

- On Linux, if DNS does not work correctly in `dig_net`, please refer to [this post](https://serverfault.com/questions/642981/docker-containers-cant-resolve-dns-on-ubuntu-14-04-desktop-host).

- If there's a docker network conflict, use `docker network rm <network id>` to remove conflicting network.


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
        "number_of_workers": 4
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

## Ports allocation in dig_net

- DIG ETL Engine: 9999
- Kafka: 9092
- Zookeeper: 2181
- ElasticSearch: 9200, 9300
- Sandpaper: 9876
- DIG UI: 8080
- myDIG: 9879 (ws), 9880 (gui), 9881 (spacy ui), 12121 (daemon, bind to localhost)
- Landmark Tool: 3333, 5000, 3306
- Logstash: 5959 (udp, used by etk log)
- Kibana: 5601
- Nginx: 80

> `dig_net` is the LAN in Docker compose.

## Docker commands for development

build Kibana image:

    docker build -t uscisii2/kibana:4.6-sense kibana/.
    
build Nginx image:

    docker build -t uscisii2/nginx:auth-1.0 nginx/.

build ETK base image:

    docker build -t uscisii2/etk:1.0.0 -f Dockerfile-etk .
    
build ETL image:

    docker build -t uscisii2/dig-etl-engine:1.0.0 .
    
run in development mode:

    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up


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
