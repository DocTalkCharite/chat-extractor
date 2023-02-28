# DocTalk chat_extractor

DocTalk chat_extractor is a command-line utility that allows [Mattermost](https://mattermost.com/) administrators to extract, anonymize and format conversational data from a Mattermost MariaDB database.

The contents of this repository have been developed by [Daniel Hetz](https://github.com/mutex) as part of the research project `DocTalk - Dialog meets Chatbot: Collaborative Learning and Teaching in the Work Process` at the `Department of Psychosomatic Medicine, Charité Universitätsmedizin Berlin`.

## Prerequisites

Before you begin, ensure you have met the following requirements:
* You have an up and running Mattermost installation with a MariaDB database backend. The utility was developed and tested on a Mattermost installation running on a MariaDB database backend, but should also work with a MySQL backend with no or few changes required.
* You have command-line-access to the `Linux` machine hosting the Mattermost database. The utility was developed and tested on `Ubuntu 20.04 LTS` but should run on any OS with the proper python interpreter and required libraries.
* You have the credentials for the Mattermost database and permission to connect to the MariaDB UNIX socket.
* You have the MariaDB development headers installed: `apt-get install libmariadb3 libmariadb-dev`.
* You have a `python3` installation with the `python3 MariaDB connector`: `pip3 install mariadb`.

## Installing chat_extractor

No installation is required, just clone this repository and run chat_extractor.py on the command-line:

```
python3 chat_extractor.py --help
```

For anonymizing relevant pieces of information within the conversations, you might want to add pattern files specific to your use-case to the `./patterns` directory. Pattern files in this directory should contain one word per line, which when found within a conversation, will be substituted with the filename. The name 'pattern file' is a bit misleading here, as the words in the files are not processed as actual regular expression patterns but as literal strings.

```
cat > ./patterns/first-name <<EOF
alice
bob
EOF
```

## Using chat_extractor

To get an overview of required paramters and supported options you can just run the utility on the command-line:

```
python3 chat_extractor.py --help
```

To test functionality, you can run the utility with the Mattermost database password as the only required parameter to extract all conversational data from the database, anonymize it and print it to the command-line stdout:

```
python3 chat_extractor.py my_mattermost_database_password
```

If your Mattermost database name and user differ from the default `mattermost`, you can specify your names like this:

```
python3 chat_extractor.py -d my_mattermost_database_name -u my_mattermost_database_user my_mattermost_database_password
```

To write the extracted and anonymized data to a file instead of stdout, specify a directory to write the conversations to (one file will be created per conversation with the unique channel ID as the filename):

```
python3 chat_extractor.py -w /path/to/my/output/directory/ my_mattermost_database_password
```

## Contact

If you want to contact me you can reach me at <your_email@address.com>.

## License

This project uses the following license: [GNU General Public License v3.0 or later](https://www.gnu.org/licenses/).

See [COPYING](/COPYING) for the full license text.
