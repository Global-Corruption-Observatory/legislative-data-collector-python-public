## Overview
This is a standalone Python repository to scrape French, German and Portugese parliamentary bills for the Legislative project. It has no dependency on the [Java codebase](https://github.com/Global-Corruption-Observatory/legislative-data-collector-java-public) for the same project. 

## Requirements
- Python 3.11
- Desktop environment required (to allow starting of browsers): `sudo apt install xfce4`
- Chromium browser: `sudo apt-get install chromium-browser`
- A running MongoDB instance (tested with version 7.0.4)
- `ghostscript` and `python3-tk` libraries installed on the system for PDF text extraction (`apt install ghostscript python3-tk` on Linux)

## Running
1. Install the required packages by running `pip install -r requirements.txt`
2. Run the scraping for your chosen country - run the `main.py` script in the country's folder)
3. Export the dataset with the `common/json_flattener.py` script. The results will be saved in the `data_handover` folder, labeled by country and date.

## Environment variables
- `COUNTRY`: Two-letter code of the country to scrape 
- `MONGO_URL`: MongoDB connection string (required)

## Explanation of source code
### Significant classes

#### common/record.py
This represents a bill record. 

#### main.py under all countries
This contains the scraping steps for each country. 

## Troubleshooting
Run the command `export PYTHONPATH=.` from the project's root folder in case you get module not found errors for the local modules.

## Rough collection times for each country:
- France: 5 days
- Germany: 1 week 
- Portugal: 5 days 
