# Processing Data in myDIG

This guide will explain how to process data in the latest version of myDIG. This version of myDIG provides a lot of freedom and 
flexibility to users.
The guide assumes that you already read the [User Guide](index.md) and that you have already defined a project and used the 
processing pipeline to build a search engine for corpus of documents.

We will cover the following topics in this guide:

- ETK modules - a new way to process your data
- Ingesting different file types (csv, xls, xlsx, html etc)
- Defining DIG fields and their correlation to Knowledge Graph
- Tying everything together in myDIG

## ETK modules

[ETK](https://github.com/usc-isi-i2/etk) modules are python scripts, which are used by myDIG to process data. We have moved on from config based extraction pipeline
to etk modules. This is a significantly big change as compared to the previous version of myDIG. We no longer supply 
supplementary config files to define the extractions, instead the users are given flexibility to write code.

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

