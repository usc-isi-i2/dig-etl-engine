# Processing Data in myDIG

This guide will explain how to process data in the latest version of myDIG. This version of myDIG provides a lot of freedom and 
flexibility to users.
The guide assumes that you already read the [User Guide](index.md) and that you have already defined a project and used the 
processing pipeline to build a search engine for corpus of documents.

We will cover the following topics in this guide:

- ETK modules - a new way to process your data
- Ingesting different file types (csv, xls, xlsx, html etc)
- Tying everything together in myDIG

## ETK modules

[ETK](https://github.com/usc-isi-i2/etk) modules are python scripts, which are used by myDIG to process data. We have moved on from config based extraction pipeline
to etk modules. This is a significantly big change as compared to the previous version of myDIG. We no longer supply 
supplementary config files to define the extractions, instead the users are given flexibility to write code.

The [etk documentation](https://usc-isi-i2.github.io/etk/) explains the classes and available extractors.

The structure of an ETK module:
```
from etk.etk_module import ETKModule
from etk.document import Document
import ...

class CustomETKModule(ETKModule):
    def __init__(self, etk):
        # initialize extractors and other relevant variables

    def process_document(self, doc: Document):
        """
          The knowledge graph is built in this function.
          Extract values/entities and add them to the Knowledge Graph, extensive examples are in the 
          etk repository.
          Depending on the file type, etk modules vary in their structure, 
          this is discussed later in this guide
        """
        
    def document_selector(self, doc) -> bool:
        """
        Boolean function for selecting document. 
        The purpose of this function is to determine whether the input record, 
        belonging to a particular dataset, should be processed by this ETK module. 
        There maybe numerous datasets in your project and each of them could be 
        processed by a dedicated ETK module
        
        Returns true or false based on some condition, for eg:
          - if url starts with certain string ?
          - if a particular field exists in the input Document?
          - if value of a particular field matches a string ?
        """
        return DefaultDocumentSelector().select_document(doc)

```
### ETK Module with an example
Let's take a look at the elicit events data from the [User Guide](index.md) and the 
corresponding etk module used to process it.

> When we imported the project settings, we imported the etk module as well.

One record from event data has the following structure:

```
  {
    "url": "http://www.ce_news_article.org/2016/01/01/201601010124.html",
    "doc_id": "4371C3A9FDB4BA949C7B895D091957E74E4903EA251AD430F39076024F647AF4",
    "raw_content" : "<html>event related html data in html structure</html>"
  }
```
> This one json line is converted to a [Document](https://github.com/usc-isi-i2/etk/blob/master/etk/document.py) 
object in myDIG and this object is passed to the `process_document` function

Lets dissect the [etk module](https://github.com/usc-isi-i2/dig-etl-engine/blob/development/datasets/etk_modules/em_elicit.py)
for this dataset.

#### Import Statements
```
# Importing the extractors we are going to use
from etk.extractors.html_content_extractor import HTMLContentExtractor, Strategy
from etk.extractors.html_metadata_extractor import HTMLMetadataExtractor
from etk.extractors.date_extractor import DateExtractor
from etk.extractors.glossary_extractor import GlossaryExtractor

# Import etk module related classes
from etk.etk_module import ETKModule
```

#### Define custom class and initialization
```
class DemoElicitETKModule(ETKModule):
    def __init__(self, etk):
        # initialize super class
        ETKModule.__init__(self, etk)
        
        # initialize metadata extractor (extracts metadata from html pages)
        self.metadata_extractor = HTMLMetadataExtractor()
        
        # initialize content extractor (extracts `content` from html page. Tries to identify main text in the html)
        self.content_extractor = HTMLContentExtractor()
        
        # initialize a date extractor (can normalize a variety of date formats)
        self.date_extractor = DateExtractor(self.etk, 'demo_date_parser')
        
        # initialize a glossary extractor for countries with a bunch of extractor level parameters
        self.country_extractor = GlossaryExtractor(
            self.etk.load_glossary(
                "${GLOSSARY_PATH}/countries.txt"),
            "country_extractor",
            self.etk.default_tokenizer,
            case_sensitive=False, ngrams=3)
            
        # initialize a glossary extractor for cities
        self.cities_extractor = GlossaryExtractor(
            self.etk.load_glossary(
                "${GLOSSARY_PATH}/cities.txt"),
            "cities_extractor",
            self.etk.default_tokenizer,
            case_sensitive=False, ngrams=3)
```
> These glossaries should be present in your project.

***Exercise: Find the glossary page in myDIG UI and see if the glossaries match the ones used in this etk module***

#### process_document function (this is where the Knowledge Graph is built)
```
    def process_document(self, doc):
        """
        Add your code for processing the document
        """

        # define a segment of the document on which on run extractors
        raw = doc.select_segments("$.raw_content")[0]
        
        # extract text from the segment using the strategies: `ALL_TEXT`, `MAIN_CONTENT_STRICT` and `MAIN_CONTENT_RELAXED`
        # and store the output in document itself
        doc.store(doc.extract(self.content_extractor, raw, strategy=Strategy.ALL_TEXT), "etk2_text")
        doc.store(doc.extract(self.content_extractor, raw, strategy=Strategy.MAIN_CONTENT_STRICT),
                  "etk2_content_strict")
        doc.store(doc.extract(self.content_extractor, raw, strategy=Strategy.MAIN_CONTENT_RELAXED),
                  "etk2_content_relaxed")
        
        # extract metadata from the segment
        doc.store(doc.extract(self.metadata_extractor,
                              raw,
                              extract_title=True,
                              extract_meta=True,
                              extract_microdata=True,
                              extract_rdfa=True,
                              ), "etk2_metadata")
        
        # start building the knowledge graph, add title and description from 
        # previously extracted description and title
        doc.kg.add_value("description", json_path="$.etk2_content_strict")
        doc.kg.add_value("title", json_path="$.etk2_metadata.title")

        description_segments = doc.select_segments(jsonpath='$.etk2_content_strict')
        for segment in description_segments:
            extractions = doc.extract(extractor=self.date_extractor, extractable=segment)
            for extraction in extractions:
                # extract date and add to KG
                doc.kg.add_value("event_date", value=extraction.value)
    
                extracted_countries = doc.extract(
                    self.country_extractor, segment)
                
                # extract country and add to KG
                doc.kg.add_value('country', value=extracted_countries)

                extracted_cities = doc.extract(self.cities_extractor, segment)
                
                # extract city and add to KG
                doc.kg.add_value('city', value=extracted_cities)
        
        # return empty list if no additional Documents were created in this function
        return list()
```

There is a lot to unpack in this etk module. First we initialize some extractors, please refer the [documentation](https://usc-isi-i2.github.io/etk/).

Next we define a Segment, which is basically subpart of the document. We then proceed to extract text from the segment followed by extracting entities like title, description, city, country etc. Then we build the knowledge graph by calling the
function `doc.kg.add_value('some_field', extractions)`.

While building the knowledge graph, we can only use fields which already exist in myDIG fields menu.

***Exercise: Find the fields page in myDIG and confirm that all the fields in the knowledge graph are present in myDIG***

Users don't have to follow the above etk module's structure. They have the flexibility to write an etk modules in a lot of ways.

For example, they can extract entities without defining a segment first. Or they don't have to store intermittent results in the document. The results can be added to the KG at any point.

Examples of ETK modules are available [here](https://github.com/usc-isi-i2/etk/tree/master/examples)

#### document_selector function, returns a boolean if the current Document should be processed by this etk module
```
 def document_selector(self, doc) -> bool:
        return doc.cdr_document.get("url").startswith("http://www.ce_news_article.org")
```

We are checking if the value of field `url` starts with `http://www.ce_news_article.org`, you can scroll up and confirm yourself. myDIG calls this function to check whether the input record should be processed by the this ETK module.

## Ingesting different file types
myDIG can now process a various file types.

All supported file types are: csv, tsv, xls, xlsx, html, json, and json lines

From the myDIG UI, only json lines file (.jl) can be uploaded, and if the file size is huge (> 200 MB), you can gzip the file. Please note that only .gz files are accepted, any other compression format will result in myDIG throwing an error.

However, you can programmatically upload other file types as explained below.

### Uploading files to myDIG
```
    def upload_files_mydig(file_path, url, dataset, file_type):
        file_name = os.path.basename(file_path)
        payload = {
            'file_name': file_name,
            'file_type': file_type,
            'dataset': dataset
        }
        files = {
            'file_data': (file_name, open(file_path, mode='rb'), 'application/octet-stream')
        }
        
        resp = requests.post(url, data=payload, files=files)

        return resp.status_code
```
The parameters to the function:
`file_path`: local file path to the file you are trying to upload to myDIG.

`url`: URL for the myDIG file upload endpoint, for local installations it is - 
http://{USERNAME}:{PASSWORD}@localhost:12497/mydig/projects/{project_name}/data?sync=false&log=true

`dataset`: a string describing your file. This will appear in the `ACTIONS` view of your myDIG project page under the column `TLD`.

`file_type`: file type is determined by the following function. It can be one of the three values : `csv` or `html` or `json_lines`

```
def determine_file_type(file_type):
    if file_type in ['csv', 'xls', 'xlsx']:
        return 'csv'
    if file_type in ['html', 'shtml', 'htm']:
        return 'html'
    if file_type in ['json', 'jl']:
        return 'json_lines'
    return file_type
```

### ETK Modules for different file types

The way the data is processed by myDIG and fed to `process_document` varies slightly, depending on the uploaded file type. The structure of ETK module changes accordingly. In this section we will discuss the variations in the ETK modules.

#### JSON lines file
This is the simplest scenario and we have already covered it with the introductory example.

#### CSV, TSV or Excel file
Lets go behind the scenes in myDIG and try to understand what happens when we upload this file type.
When myDIG receives such a file, we store the uploaded file at this location,

`{DIG_PROJECTS_DIR_PATH}/{project_name}/user_uploaded_files`,

where `DIG_PROJECTS_DIR_PATH` is defined in the .env file and `project_name` is the name of the project.

Then we create a json object with the following structure,
```
{
	"raw_content_path": "path as described above, where myDIG stores the file",
	"dataset": "the string as described in the section `Uploading files to myDIG`",
	...
}
```
This json is then passed to ETK module. Users should read the file using the `raw_content_path` field and process the file appropriately.

Example ETK module,
```
...
from etk.csv_processor import CsvProcessor
...

class SampleETKModule(self, etk):
 def __init__(self, etk):
        ...
        self.csv_processor = CsvProcessor(etk=etk, heading_row=1) # More details in the etk documentation
        ...

def process_document(self, doc: Document):
        doc_json = doc.cdr_document
        if 'raw_content_path' in doc_json and doc_json['raw_content_path'].strip() != '':
            try:
                docs = self.csv_processor.tabular_extractor(filename=doc_json['raw_content_path'],
                                                            dataset=doc_json['dataset'])
                ...
                # build Knowledge Graph
                ...
```
A full ETK module to process a csv file is [here](https://github.com/usc-isi-i2/etk/blob/development/examples/acled/em_acled.py)

#### HTML file
In this case, when we receive a html file, we read the contents of the html file, create a json object and store it in the field `raw_content`.
Like so,
```
{
	"raw_content": "html content of the uploaded file",
	"dataset": "the string as described in the section `Uploading files to myDIG`",
	...
}
```

This object is passed to the `process_document` function and can be processed in a similar fashion as discussed in the introductory example.

This concludes our section of ETK Modules for different file types.

***Important: the etk module file names should start with `em_` to be picked up by myDIG***

## Tying everything together in myDIG

In this section we will explain what to do after you have written an ETK module.

Copy the etk module at this location,

`{DIG_PROJECTS_DIR_PATH}/{project_name}/working_dir/additional_ems/`

myDIG reads all the etk modules from this location and processes the datasets using these modules. Herein comes the role of the `document_selector` function. An ETK modules will process a dataset, if the `document_selector` returned true for that particular dataset.

Suppose you already have some datasets and corresponding ETK modules, the pipeline is running and data is being processed.
Now if you want to add another dataset to the mix and have one more etk module.

You should do the following, in order:

1. Upload the dataset to myDIG, keep the `Desired` to 0.
2. Copy the ETK module to the correct path as described above.
3. Stop the pipeline, and then start the pipeline.
4. Update the `Desired` to a non zero number for that dataset.

If there are no errors, the data should be processed in couple of seconds.


