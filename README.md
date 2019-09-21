# woerdle-zehla

A simple way to assess the effort involved in Post-Editing is to count the number of edits required to transform MT output into a publishable translation and vice versa. woerdle-zehla, which is Swabian for "word counter", takes the concept of edit-distance to a document level and creates simple, but intuitive reports for you. Review the results in the GUI directly or save them to disk for subsequent analysis and processing.

## How it works
1. The tool accepts bilingual __SDLXLIFF__ files and __Across HTML previews__ as inputs and extracts the following information:
- Metadata, including:
  - source and target language IDs
  - name of the client/relation, project name, filename (optional)
- String data, including:
  - Source strings
  - Target strings
  - Strings from version history (optional in Across)

2. If no previous MT output is available, woerdle-zehla will create a __sample object__ from your source data and send it for translation with an API call. The default path to your API key is ```data/API_key.txt```. Currently, only the DeepL API is supported.
3. The MT output is compared against the target translations and each segment is assigned an __edit-distance__ score (aka Levenshtein distance). Individual scores are then combined to calculate a score at the document level ([Post-edit density](https://www.taus.net/events/webinars/68-dqf-spotlight-series-the-power-of-edit-distance-in-quantifying-the-translation-effort)).
4. woerdle-zehla offers you three ways for further analysis:
* A __histogram view__ with discrete bins for segments within a certain score range. This is perfect to quickly assess the distribution of your scores (e.g. bell-shaped, logarithmic, flat) and its skewness.
* __Text output__ for a limited number of segments from the low and high ends of the distribution. This is to give you an idea regarding segments that work well with MT and those that do not.
* __JSON exports__ containing metadata, sample segments, aligned translations and scores. Use these files to map scores to project data in your PMIS or to calculate the potential impact of any post-processing steps you wish to introduce to your MT processes.

## Requirements
If you are using Anaconda as a package manager, no additional libraries are required.

## Running the script
```
python gui.py
```
This will start the GUI. Check out the settings options to manage additional aspects of the tool.

## Running the notebook
If you want to run the woerdle-zehla tool on a remote machine, use the accompanying [Jupyter Notebook](woerdle-zehla.ipynb "Woerdle-zehla Jupyter Notebook").

## Questions
Feel free to drop me a line in case of any questions.
