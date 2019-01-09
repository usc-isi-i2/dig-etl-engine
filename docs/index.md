# myDIG User Guide

This guide takes you through the steps to build a simple application starting with a collection of event records.
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

This guide will show you how to build a KG and search application for an event dataset. 

Your objective is to build a KG of event records.
The KG will include information about the events (title, date, city, country, description).

[add-project-button]: assets/add-project-button.png
[create-project]: assets/create-project.png
[open-project]: assets/open-project.png 
[new-project]: assets/1-new-project.png
[load-data]: assets/2-load-museum-data.png
[run-pipeline-1]: assets/3-run-pipeline.png
[search]: assets/4-search-screen.png
[fields]: assets/5-fields.png
[date-creation]: assets/6-date_creation.png
[import-project]: assets/import-project.png
[import-project-dialog]: assets/import-project-dialog.png
[hamburger-menu]: assets/open-actions-fields-fields-glossaries.png
[dig-ui-home]: assets/dig-ui-home.png
[add-field]: assets/add-field.png


## Creating A New Project

From the `All Projects` page, click on the `+` button to add a new project.

![Add Project Dialog][add-project-button]

            Screenshot 1

> Project names should be lowercase, contain only letters, numbers and `_`

Click on the `SAVE` button to create the project.

![Create Project Dialog][create-project]
                                                                                                    
            Screenshot 2

Click on the project or the `>` button to go to the project configuration page.

![Open Project][open-project]

            Screenshot 3
## Import Existing Project Settings
For this guide, we are going to use existing project settings, which include pre defined fields and glossaries.
Click on the `Import Project` button from the top right corner menu

![import-project]

            Screenshot 4
                                                                                                    
Select `elicit_20181113185140.tar.gz` from the `datasets` folder, click `SUBMIT` and then click `OVERWRITE` button in the confirmation dialog.

![import-project-dialog]

            Screenshot 5                          
There should be 5 new fields and 2 glossaries created.     

![hamburger-menu]

            Screenshot 6                                                                                                                                                                       
 

## Loading Data

The new project screen contains options to configure your project.

![New Project][new-project]

            Screenshot 7

Use `Import JSON lines File` to import data in your project and select the `elicit_20.jl` file, which contains a sample of 20 pages from the event dataset.
This file is part of the myDIG installation, in `datasets/elicit_20.jl`.
After a few seconds, myDIG will load the data, and show that it has loaded 20 pages:

![Data Loaded][load-data]

            Screenshot 8

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
Use the `Desired` field to tell myDIG how many documents from each TLD you want to have in your KG. You can either update desired documents for all the TLDs or update each TLD individually.
Update the number to 10 in the textbox in the `Desired` and click outside the box. If there are multiple TLDs, you could update all of them by clicking the `Desired Docs per TLD` button (see Screenshot 7) and clicking `Update`
The table of TLDs now shows 10 in the `Desired` column.

To create the KG, click the red `Recreate Knowledge Graph` button.
myDIG will first delete your current KG, it will turn on the extraction pipeline, and it will add the desired number of documents to the pipeline.
You need to wait for about 1 minute before the number of documents in the KG updates.
The reason for the wait is that myDIG needs to load several very large files such as a list of all cities in the world with population over 15,000, and an English language model that includes all words in the English dictionary.
After a couple of minutes, the documents will move through the extraction pipeline, and get loaded in the KG:

![Run Pipeline][run-pipeline-1]

            Screenshot 9

## Testing The KG

As soon as the number of documents in the KG is more than zero, you can click on the `DIG UI` (see Screenshot 7)  button to show the DIG page to search the KG you just created.
Go ahead and click it.

In the DIG UI, click the wrench icon (see Screenshot 10) to open the search form:
![dig-ui-home]

            Screenshot 10

Enter `nigeria` in the `Country` field to tell DIG that you want to search for events from Nigeria:

![Search][search]

            Screenshot 11

Click `Search` and take a look at the data.
Your KG so far is simple, but it is already functional.
Not bad for a few minutes of work.

## Adding More Documents

You can easily add more documents to an existing KG.
Enter `20` in the `Desired` field, click outside the textbox to tell myDIG that you want more documents, If `Pipeline` is in `ON` state, myDIG will add 10 more documents to the processing queue. `
After a few seconds the number of documents in the KG starts increasing.
This time it is much faster because you didn't have to recreate the KG and restart the processing pipeline.

## Defining Fields For Your KG

By default myDIG does not create any fields in a new project. The fields in your project exist because we imported a project with already defined fields.


Select the `Fields` option (see Screenshot 6) to view the fields in your project:

![Fields][fields]

            Screenshot 12
Let's add a new dummy field, for demo purposes. Click on the `+` button at the top right corner.


![add-field]

            Screenshot 13
Fill in the fields as shown in the picture above and click `SAVE`. There are more fields in the add field form, we'll discuss these later.
### Deleting Fields

To delete a field, click the delete button on the right.
We don't need the `dummy` field in our KG, so go ahead and delete it.

> Deleting fields in not undoable.


# Detailed function introduction

- `Recreate Knowledge Graph` is used to recreate the index in elastic search and regenerate ETK config. Desired number of data will be added and run automatically. This function will also turn pipeline on. Only use it after you did some incompatible changes.

  > Incompatible changes: upload new glossaries, update fields, update tags, update Landmark rules.

- `Turn on Pipleine` is used to fire up ETK processes with existing etk modules. If you only want to add some new data, use this function. ETK processes will exit after idle for an hour. Then this button will turn into enable.

