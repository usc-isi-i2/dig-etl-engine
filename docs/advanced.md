# myDIG Advanced User Guide

This guide explains how to use features of the DIG processing pipeline that you cannot access from the myDIG user interface.
The guide assumes that you already read the [User Guide](index.md) and that you have already defined a project and used the processing pipeline to build a search engine for corpus of documents.

The guide covers the following topics:

- ingesting JSON documents
- targetting extractors to specific document segments
- defining new extractors (to be written)

I encourage you to build the example shown in this guide. It will take about 30 minutes and you will have a working application as a starting point for importing files into your own project.

> Hands-on: start myDIG and define a new project called `events`.
> 
> You can follow along and build the project step by step, or you can import the premade `sample-projects/events.tar.gz` and see the complete project.
> 
> Note: to import a project, first define an empty project, then use the `Import Project` command to import the `events.tar.gz`. The data for the project is in `datasets/events/`, import both files, set desire docs to 100 and click the red button to run the project.

[search-screen]: assets/events/1-search-screen.png 
[boko-haram]: assets/events/boko-haram.png 

## Ingesting JSON Documents

A common use-case, not currently supported in the myDIG user interface, is one where you have a collection of JSON documents, and you want to ingest them into DIG so that you can search them using DIG.
The procedure to ingest JSON documents involves the following steps:

- Preparing JSON documents for ingestion
- Define DIG fields to store values
- Define supplementary ETK configuration files
- Run the extraction pipeline

### Preparing JSON Documents For Ingestion In DIG

DIG can ingest arbutrary JSON documents that have the following attributes:

- `doc_id`: an arbitrary string to identify each document. Each distinct document should have different `doc_id`s. When multiple documents have the same `doc_id`, only the last one processed will appear in the search engine. 
- `url`: a possbily made-up URL for the document. DIG groups documents based on the domain name in the `url`, so every document must have a `url`. It is not necessary that the `url` can be fetched.
- `raw_cpntent`: an optional HTML rendition of the document, used for display. The attribute must be present even if it's value is empty.

The documents must be stored in a JSON lines file with `.jl` extension ([http://jsonlines.org/](http://jsonlines.org/)), one document per line.
If the resulting file is large, you can compress it using `gzip` (DIG only recognizes `gz` files and will report an error with any other compression format).

> Hands on: in myDIG, load the `acled.jl` and `pitf.jl` files found in `dig-etl-engine/datasets/events`

The example files are typical JSON document containing attributes, lists and nested objects:

```
{
  "event_type": [
    "Incident",
    "Targeted Assassination",
    "Firearms"
  ],
  "title": "Armed men shot dead the village chief of...",
  "url": "http://eventdata.parusanalytics.com/data.dir/atrocities.html",
  "raw_content": ".",
  "death_count": 1,
  "injured_count": 0,
  "actors": [
    {
      "id": "gunmenunknownunknownunclearother",
      "description": "Unknown/Unclear/Other",
      "title": "Unknown gunmen"
    },
    {
      "id": "assertedchiefcontestednoncombatantnoncombatantnotstatusstatusvillage",
      "description": "Noncombatant Status Asserted",
      "title": "Noncombatant Status Not Contested village chief"
    }
  ],
  "location": "Afghanistan AFG Jowzjan Mangajek Chahar Shanghoy village",
  "references": [
    "BBC",
    "International"
  ],
  "event_date": "2016-01-06T00:00:00",
  "doc_id": "88f4c4fa-bae7-11e7-b53a-94dbc9484288",
  "@type": "event",
  "description": "Armed men shot dead the village chief of Chahar Shanghoy of Mangajek District in [northern] Jowzjan Province"
}
```

### Define DIG Fields To Store Values

The DIG search inteface shows fields that you define in your myDIG project. You must define the fields where you want to store the values you get from your JSON file.
Sometimes, you may want to define fields with identical names as the attributes in your JSON file, but sometimes you may already have fields in your project where you want to store the data.
Also, you may want to use different names, and often you may want to extract information from the values in your JSON document before you put these values in fields.

> Hands-on: go to the `Fields` tab in your `events` project and define the following fields:

| field | description | type |
| :----- | :--- | :-- |
| event_date | to hold the `event_date` values | string |
| event_type | to hold the `event_type` values | string |
| actor_description | to hold the `description` of `actors` | string |
| location | to hold the `location` | string |
| actor_title | to hold the `title` of `actors` | string |
| death_count | to hold the `death_count` | string |
| injured_count | to hold the `injured_count` | string |
| _actor_kg_id | to hold the `id` of `actors` | string |
| references | to hold `references` | string |

> Hands-on: delete the fields `address`, `email`, `phone`, `stock_ticker`, `posting_date`

Note: the current version of the DIG user interface does not support nested object. In the example, you will map all attributes of `actors` to separate fields. When there are multiple `actors` the knowledge graph (KG) will have a list in each field. This is not ideal, but the best possible in this version of DIG.

Note: you are defining a new date field called `event_date` and deleting the `posting_date` that gets crated by default. This is not strictly necessary, but I recommend that you use good names for your fields so that others can understand your project.

### Define Supplementary ETK Config Files

To ingest uour JSON file in DIG, you need to tell DIG how to populate the fields in your project using data fromyour JSON file. 
You need to define a confguration file with the following structure:

```
{
  "content_extraction": {
    "json_content": [
    ]
  },
  "data_extraction": [
  ]
}
```

The configuration file has two sections, corresponding to two stages in the processing pipeline.

The first stage, called *content extraction* segments input files into pieces called *segments*. When the pipeline processes an HTML files, the typical segements are url, title and content; when processing processing tables the segments are rows and cells; when processing JSON files, the segments correspond to pieces of your JSON file that you define usng JSON paths.

The second stage, called *data extraction* applies extractors to segments and stores the results of the extraction in fields.

You use a configuration file to tell the pipeline how to construct segments and what extractors you want to apply to each segment.
You can give this file any name you want. It must have a `.json` extension, and you must store this file in `mydig-projects/<project-name>/working_dir/additional_etk_config/`

> Hands-on: create the file `events/working_dir/additional_etk_config/etk_config_supplement.json` in the folder you configured in your `.env` file.
> Put the following document in this file:
> 
```
{
  "content_extraction": {
    "json_content": [
      {
        "input_path": "title",
        "segment_name": "event_title"
      },
      {
        "input_path": "description",
        "segment_name": "description_1"
      },
      {
        "input_path": "url",
        "segment_name": "url"
      },
      {
        "input_path": "event_type",
        "segment_name": "event_type"
      },
      {
        "input_path": "death_count",
        "segment_name": "death_count"
      },
      {
        "input_path": "injured_count",
        "segment_name": "injured_count"
      },
      {
        "input_path": "references",
        "segment_name": "references"
      },
      {
        "input_path": "location",
        "segment_name": "location"
      },
      {
        "input_path": "event_date",
        "segment_name": "event_date"
      },
      {
        "input_path": "actors[*].id",
        "segment_name": "_actor_kg_id"
      },
      {
        "input_path": "actors[*].title",
        "segment_name": "actor_title"
      },
      {
        "input_path": "actors[*].description",
        "segment_name": "actor_description"
      }
    ]
  },
  "data_extraction": [
    {
      "input_path": "content_extraction.event_title[*]",
      "fields": {
        "title": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.description_1[*]",
      "fields": {
        "description": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.url[*]",
      "fields": {
        "url": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.event_type[*]",
      "fields": {
        "event_type": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.death_count[*]",
      "fields": {
        "death_count": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.injured_count[*]",
      "fields": {
        "injured_count": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.references[*]",
      "fields": {
        "references": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.location[*]",
      "fields": {
        "location": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.event_date[*]",
      "fields": {
        "event_date": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction._actor_kg_id[*]",
      "fields": {
        "_actor_kg_id": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.actor_description[*]",
      "fields": {
        "actor_description": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.actor_title[*]",
      "fields": {
        "actor_title": {
          "extractors": {
            "extract_as_is": {}
          }
        }
      }
    },
    {
      "input_path": "content_extraction.location[*]",
      "fields": {
        "country": {
          "extractors": {
            "extract_using_dictionary": {
              "config": {
                "ngrams": 3,
                "dictionary": "countries",
                "case_sensitive": false
              }
            }
          }
        },
        "city_name": {
          "extractors": {
            "extract_using_dictionary": {
              "config": {
                "ngrams": 3,
                "dictionary": "cities",
                "case_sensitive": false
              }
            }
          }
        }
      }
    }
  ]
}
```




#### Content Extraction Section

The `content_extraction` section consists of an list of objects with two attributes each:

- `input_path`: a JSON path to select values in your JSON file (see ([http://goessner.net/articles/JsonPath/](http://goessner.net/articles/JsonPath/) for details on the syntax of JSON paths)
- `segment_name`: the name of a segement to store the values fetched using the `input_path`; you can choose arbutary names.

> In the current version of DIG, the JSON path must select literal values (string,  number, Boolean). Selecting objects or lists will produce an error.

The `content_extraction` section for JSON files often mirrors the structure of the JSON file, i.e., there is a segment for each attribute.
Note the more complex JSON paths used for the `_actor_kg_id`, `actor_title` and `actor_description` segments. These JSON paths select all the values of selected attributes from the nested objects, producing a list of values.


#### Data Extraction Section

The `data_extraction` section consists of a list of objects with two attributes:

- `input_path`: a JSON path to select a segment
- `fields`: a dictionary to specify the fields that will be populated using the information in the selected segment. Note that the segment may contain a list of values, so the fields will be populated all the segment values.

The fields dictionary has the following structure:

```
{ <field-name-1>: 
  {
    "extractors": {
      <extractor-1>: {
        <extractor-1 arguments>
      },
      <extractor-2>: {
        <extractor-2 arguments>
      },
      ...
    }
  },
  <field-name-2>: 
   { ... },
  <field-name-3>: 
   { ... }, 
  ...
}
```

From each segment, you can populate multiple fields, and for each field you can specify multiple extractors to extract values from the segment to populate the field.

In the example for events, many of the data extraction objects are simple, they populate a single field, and use an extractor called `extract_as_is`, which returns the value of the segment without modification.

The data extraction section for the `location` segment is more interesting as it is used to populate two fields, `country` and `city_name`. The reason for this is that the location field contains values such as 
"Afghanistan AFG Jowzjan Mangajek Chahar Shanghoy village", text that contains the names of countries and cities. The configuration file uses glossaries of country and city names to pull these values from the location strings.

### Run The Extraction Pipeline

Once you define the configuration file, you are ready to run the extraction pipeline. Click on the red `Recreate Knowledge Graph` button to rebuild the knowledge graph using you new configuration file.

> Note: you can define multiple supplemental configuration files to keep your work organized. It is a good idea to create separate configuration files for each kind of JSON file you have.

If all goes well, in the DIG search user interface you will see a screen that looks something like this. Note that I defined nice icons, colors and placement for the fields to produce a nice looking screen:

![Events Search Screen][search-screen]

Once the project gets created, click on the `Open` button to go to the page to configure your project.

## Handling Titles and Descriptions

THe DIG screens require that you define `title` and `description` fields. You config file should define `data_extraction` sections that populate `title` and `description`

## Creating Maps

Maps are created from fields whose `type` is `location` as defined in the field editor in my DIG. 

By default, when you create a new project, it will have fields `city`, `city_name`, `state` and `country`. In addition, DIG includes an entity resolution algorithm that resolves city_name/state/country fields to geonames, and stores the resolved cities in field `city`. 

To take advantage of this capability, you should define `data_extraction` sections to populate the values of `city_name`, `state` and `country`.

> **Super important**: **never** define extractions for field `city`. if you have city names, put them in field `city_name`. Otherwise you will mess things up, and the cities will not be displayed on the map.

> Note: in the week of November 12 we will release a version of DIG that can ingest latitude/longitude values from JSON files and create locations that can appear on maps.

Here is an example of a page that shows a map. It is the page for entity "boko haram":

![Boko Haram Entity Page][boko-haram]
