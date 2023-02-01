# DocTalk chat-extractor

This python script was developed within the research project DocTalk to extract, anonymize and format conversation data from a Mattermost database.

## Installation

No installation is required, just clone this repository and run chat-extractor.py on the command-line:

```
python3 chat-extractor.py --help
```

## Requirements

The script requires need the MariaDB development headers and the python3 MariaDB connector to connect to the Mattermost database.

```
apt-get install libmariadb3 libmariadb-dev
pip3 install mariadb
```

## Compatibility

This project is written for python3 and was tested on Ubuntu 20.04, but should run on any OS with the proper python interpreter and required libraries.

The tool is developed for and tested against a Mattermost database on MariaDB, but should work with a MySQL database with no or little changes.

PostgreSQL databases are not supported.

## Usage


