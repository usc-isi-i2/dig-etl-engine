# myDIG User Guide

This guide takes you through the steps to build a simple application starting with a collection of web pages.
Before continuing, install myDIG by following the instructions in the [README.md](https://github.com/usc-isi-i2/dig-etl-engine/blob/master/README.md) file.
Once the installation completes, visit the page [http://localhost:12497/mydig/ui/](http://localhost:12497/mydig/ui/) to bring up the home page.

The steps include:

- creating a new project
- loading data
- defining fields
- using the Inferlink took to extract data from all pages in a web site
- using glossaries to extract terms from any page
- using rules to extract data based on patterns
- organizing and customizing the appearance of the search page

This guide will show you how to build a KG and search application for artworks in a museum. 
The following page shows an example page [https://americanart.si.edu/artwork/sir-thomas-heath-9890](https://americanart.si.edu/artwork/sir-thomas-heath-9890).
Your objective is to build a KG of artworks in the Smithsonian American Art Museum.
The KG will include information about the artworks (title, medium, size, etc.) and the artists who created them.

[create-project]: assets/create-project.png 
[new-project]: assets/1-new-project.png
[load-data]: assets/2-load-museum-data.png
[run-pipeline-1]: assets/3-run-pipeline.png
[search]: assets/4-search-screen.png
[fields]: assets/5-fields.png
[date-creation]: assets/6-date_creation.png


## Creating A New Project

Click the `All Projects` button to display the dialog to create new projects, type the name of your project and click `Save`.

> Project names should be lowecase, contain only letters, numbers and `_`

![Create Project Dialog][create-project]

Once the project gets created, click on the `Open` button to go to the page to configure your project.

## Loading Data

Your new project screen contains several tabs to configure your project.

![New Project][new-project]

Use `Import JSON lines File` to import data in your project and select the `museum-200.jl` file, which contains a sample of 200 pages from the museum.
This file is part of the myDIG installation, in `datasets/museum-200.jl`.
After a few seconds, myDIG will load the data, and show that it has loaded 200 pages:

![Data Loaded][load-data]

> myDIG scans the files you load identifying TLDs and will show the number of documents you have from each TLD (Our file has documents from a single TLD).

## Building The KG

Creating a KG is an iterative process.
You start with a simple KG and then create information extractors to populate the KG with the data you want.
You can can build the KG with the extractors you have, test it in the GUI and then go define more extractors or fine tune the ones you have.

myDIG comes with a set of predefined extractors, so you can build a simple KG before you define any extractors.
Before you do that, you need to understand a little bit about the _extraction pipleline_.
Think of the extraction pipeline as a queue. 
If you put documents in the queue, myDIG will process them a few at a time, incrementally loading them in the kG until the queue is empty.

When you import documents, myDIG **doesn't** put them in the queue automatically, but rather puts them in a holding area so that you can add them to the queue whenever you want.
Use the `Desired number of documents` field to tell myDIG how many documents from each TLD you want to have in your KG.
Set it to `25` so that they process quickly, then press `Update`.
The table of TLDs now shows 25 in the `Desired` column.

To create the KG, click the red `Recreate Knowledge Graph` button.
myDIG will first delete your current KG, it will turn on the extraction pipeline, and it will add the desired number of documents to the pipeline.
You need to wait for about 1 minute before the number of documents in the KG updates.
The reason for the wait is that myDIG needs to load several very large files such as a list of all cities in the world with population over 15,000, and an English language model that includes all words in the English dictionary.
After a couple of minutes, the documents will move through the extraction pipeline, and get loaded in the KG:

![Run Pipeline][run-pipeline-1]

## Testing The KG

As soon as the number of documents in the KG is more than zero, you can click on the `DIG UI` button to show the DIG page to search the KG you just created.
Go ahead and click it.

In the DIG UI, click `Click To Enter Search Terms`, and enter `landscape` in the description field to tell DIG that you want to search for landscape artworks:

![Search][search]

Click `Search` and take a look at the data.
Your KG so far is simple, but it is already functional.
Not bad for a few minutes of work.

## Adding More Documents

You can easily add more documents to an existing KG.
Enter `100` in the `Desired Number of Documents` field, click `Update` to tell myDIG that you want more documents, and then click `Add Data To Queue` to add more documents to the processing pipeline.
After a few seconds the number of documents in the KG starts increasing.
This time it is much faster because you didn't have to recreate the KG and restart the processing pipeline.

## Defining Fields For Your KG

When you define a new project, myDIG creates several generic fields for your KG.
Select the `Fields` tab to view the fields in your project:

![Fields][fields]

The table below shows the fields that we want in the museum KG. The ones with `yes` in the `custom` column are fields that you need to add to your sample project.

| field | description | custom |
| :----- | :--- | :-- |
| birth\_info | Information about the birth of a person, including location and year | yes |
| city | default field, don't change or delete |
| city\_name | default field, don't change or delete | |
| country | default field, don't change or delete | |
| credit | person or organization who provided an artwork | yes |
| date\_birth | birth date of an artist | yes|
| date\_creation | creation date of an artwork | yes |
| date\_death | death date of an artist | yes |
| description | default field, don't change or delete | |
| dimensions | dimensions of an artwork | yes |
| email | email addresses present in the text | | 
| identifier_object | the identifier of an artwork | yes |
| keywords | keywords associated with an artwork or artist | yes |
| medium | medium used to create an artwork | yes |
| name | name of an artist | |
| phone | phone numbers present in the text | |
| state | default field, don't change or delete | |
| states\_usa\_codes | default field, don't change or delete | |
| title | default field, don't change or delete | |
| website | default field, don't change or delete | |

### Deleting Fields

To delete a field, click the delete button on the right.
We don't need and `address` field in our KG, so go ahean and delete it.

> Deleting fields in not undoable.

For our sample project, delete all fields that are not in the table above.

> Note: deleting the fields is optional, as extra fields don't do harm

### Adding Fields

To add a field, use the `Add Field` button at the top-right corner in the `Fields` tab.
Let's add the `date_creation` field, which will hold the date when an artwork was created.
Fill in the form as follows:

![Date Creation][date-creation]

There are several attributes to fill in for every field.
The following attributes specify features related to how the field is stored in the KG:

| field | description |
| :----- | :--- |
| Name | Information about the birth of a person, including location and year |
| Type | Select `date` from the menu |
| Predefined Extractor | one of the myDIG built in extractors, leave in our example |
| Search Importance | Contribution of this field to the overall ranking results, set to high number when the field is an important selector in your domain |

The other attributes in the field dialog control the appearance of the field and can be changed after you load data in the KG.
We discuss these attributes later.

Once you fill in the form for `date_creation`, click `Save` and proceed to add the other fields listed in the table above.

> Note: you can add fields at any time, so you don't have to add all of them right now.

# To Do: Add to docs:

# Detailed function introduction

- `recreate knowledge graph` is used to recreate the index in elastic search and regenerate ETK config. Desired number of data will be added and run automatically. This function will also turn pipeline on. Only use it after you did some incompatible changes.

  > Incompatible changes: upload new glossaries, update fields, update tags, update Landmark rules.

- `turn on pipleine` is used to fire up ETK processes with previous config. If you only want to add some new data, use this function. ETK processes will exit after idle for an hour. Then this button will turn into enable.

- `Add to queue`: if you updated desired number, you need to click this button to actually invoke backend to push data. However, data will be automatically pushed to queue in two conditions: 1) if your desired number is greater than your total document numbers and you are going to add more new documents 2) recreate the knowledge graph.



| Screen Label | The label that appears in the DIG page for end users |
| Screen Label Plural | Plural of the screen label |
| Show in Facets | Select to make the field appear in the facets

