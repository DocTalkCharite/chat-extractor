# file: chat_extractor.py
"""
A tool extracting, anonymizing and formatting conversation data from a Mattermost MariaDB/MySQL
 database. It is very specific to its intended use case and might need modification to be fit for
 your spefific needs.
This module was developed as part of the 'DocTalk' research project at Charité Universitätsmedizin
 Berlin.
"""

# global imports
import argparse
import os
from datetime import datetime
from itertools import chain

# local imports
from lib.extractor import Extractor
import lib.anonymize as anonymize

# constants
# dict to map single letter channel types from Mattermost database to a more verbose string
CHANNEL_TYPES = {
    'O': 'Open Channel',
    'P': 'Private Channel',
    'D': 'Direct Message Channel',
    'G': 'Group Message Channel'}
# dict to map metadata fields to their corresponding Mattermost database column name
METADATA = {
    'Channel ID': 'Id',
    'Channel Name': 'DisplayName',
    'Channel Type': 'Type',
    'Team Name': 'TeamName'}

# @channel dict
# @show_empty_channels bool
# @do_not_anonymize bool
# @return dict or False
def parse_channel(channel, show_empty_channels=False, do_not_anonymize=False):
    """
    Coordinates the extrraction and anonymization of a conversation from a given channel and
     parses the results for subsequent formatting

    Parameters
    ----------
    channel : dict
        Dictionary representing a Mattermost channel to parse (supplied by Extractor.get_channels)
    show_empty_channels : Bool
        If set, function call will return parsed channels not containing any messages
         defaults to False
    do_not_anonymize : Bool
        If set, function call will will pass conversational data on to the anonymizing function and
         return parsed, anonymized result
         defaults to False

    Returns
    -------
    parsed : dict
        Dictionary representing the channel, the key 'Metadata' contains another dictionary
         containing the channel metadata (ID, type, anonymization) and the key 'Conversation'
         contains a list of dicts, each representing one message within the conversation and its
         metadata
    """
    parsed = dict()
    parsed['Metadata'] = dict()
    # parse channel meta data
    for key, value in METADATA.items():
        if channel.get(value):
            parsed['Metadata'][key] = channel.get(value)
    # substitute channel type
    parsed['Metadata']['Channel Type'] = CHANNEL_TYPES[parsed['Metadata']['Channel Type']]
    # parse conversation
    conversation = EXTRACTOR.get_conversation(channel.get('Id'), START_DATE, True)
    if conversation:
        # skip anonymization if told to do so
        if do_not_anonymize:
            # rewrite dictionary keys in conversation to what anonymize_conversation would return
            #  parse_csv expects specific keys to format the message lines
            for line in conversation:
                line['date'] = line.pop('CreateAt')
                line['position'] = line.pop('Position')
                line['user'] = line.pop('Username')
                line['message'] = line.pop('Message')
                # Type is not required for output and can be deleted
                del line['Type']
            parsed['Conversation'] = conversation
            parsed['Metadata']['Anonymized'] = 'False'
        # anonymize by default
        else:
            parsed['Conversation'] = anonymize.anonymize_conversation(conversation)
            # group message channel names contain usernames and have to be redacted
            if parsed['Metadata']['Channel Type'] == 'Group Message Channel':
                parsed['Metadata']['Channel Name'] = 'redacted'
            parsed['Metadata']['Anonymized'] = 'True'
    else:
        if show_empty_channels:
            parsed['Conversation'] = 'there are no messages in this channel'
            parsed['Metadata']['Anonymized'] = 'False'
        else:
            return False
    return parsed

def format_csv(parsed):
    """
    Takes a parsed channel as provided by parse_channel and returns it, adding a key 'Formatted'
     containing the conversation formatted using comma-separated values (csv)

    Parameters
    ----------
    parsed : dict
        Dictionary representing a channel, as provided by parse_channel

    Returns
    -------
    formatted : dict
        Dictionary representing a channel identical to the parsed parameter with an added key
         'Formatted' containing the conversation in a csv format
    """
    # do not proceed if parsed is False (parse_channel is called with show_empty_channels=False)
    if not parsed:
        return False
    formatted = parsed
    formatted['Metadata']['Format'] = 'CSV'
    formatted['Formatted'] = list()
    # the order of fields in the dict is well known
    #  due to its explicit inititalization in anonymize.py
    separator = [[''], ['date', 'sender position', 'sender name', 'message', 'anonymized']]
    # iterate over Metadata and Conversation and parse linewise to csv
    for line in chain(formatted['Metadata'].items(), separator):
        formatted['Formatted'].append(';'.join(line))
    for line in formatted['Conversation']:
        # escape quotes for csv ( " -> "")
        line['message'] = line['message'].replace('"', '""')
        # replace line breaks
        line['message'] = line['message'].replace('\n', '<enter>')
        # enclose message in quotes to preserve semicolon in the message body
        line['message'] = '"' + line['message'] + '"'
        formatted['Formatted'].append(';'.join([str(val) for val in line.values()]))
    return formatted

def output_channel(channel, destination=''):
    """
    Outputs the parsed and formatted data of a given channel to either stdout if no destination
     folder is supplied, or to a file in the supplied destination folder

    Parameters
    ----------
    channel : dict
        Parsed and formatted dict representing a channel, as provided by format_csv
    destination : str
        String representing a directory in the local filesystem to write output file to
         If no destination is specified, will wirte to stdout instead
         defaults to an empty string (stdout)
    """
    # don't do anything if channel is False, this is the case for empty channels when parse_channel
    #  is called with show_empty_channels=False
    if not channel:
        return False
    # if destination is provided, try to write to file
    if destination:
        # raise error if destination string is not a valid directory path
        if not os.path.isdir(destination):
            raise ValueError
        channel_id = channel['Metadata']['Channel ID']
        # destination file is channel id with a .csv extension
        destfile = open(destination + '/' + channel_id + '.csv', 'w')
        # add newlines and write to file
        content = [line + '\n' for line in channel['Formatted']]
        destfile.writelines(content)
        destfile.close()
    # if destination is not provided, write to stdout
    else:
        for line in channel['Formatted']:
            print(line)
        # print a separator at the end of each channel to help distinguish between channels
        print('---')
    return True

def is_valid_date(check):
    """
    Checks if the supplied string is a date of the format YYYY-MM-DD, used as validator for the -s
     argument

    Parameters
    ----------
    check : str
        string to be checked

    Returns
    -------
    datetime obejct
        datetime object of the format YYYY-MM-DD created from the provided string
    """
    # try creating a datetime object from the provided string and return it if possible
    try:
        return datetime.strptime(check, "%Y-%m-%d")
    # if that fails, the string doesn't represent a date of the format YYYY-MM-DD
    except ValueError:
        # create an error message and raise an argparse error
        message = "not a valid date: {0!r}".format(check)
        raise argparse.ArgumentTypeError(message)

# parse positional arguments
ARGPARSER = argparse.ArgumentParser(description='Extracts and anonymizes chat content' \
                                    ' from a Mattermost database')
# only required argument is the mattermost database password
ARGPARSER.add_argument('password', help='mattermost database password')
# define a few optional arguments to refine the extraction
ARGPARSER.add_argument('-u', '--username', help='mattermost database username',
                       nargs='?', default='mattermost')
ARGPARSER.add_argument('-d', '--database', help='mattermost database name',
                       nargs='?', default='mattermost')
ARGPARSER.add_argument('-c', '--channel_type', help='channel type to extract',
                       nargs='?', default=None, choices=['D', 'G', 'O', 'P'])
ARGPARSER.add_argument('-t', '--team_name', help='team name to extract', nargs='?', default=None)
ARGPARSER.add_argument('-w', '--write-to', help='directory to write output to',
                       nargs='?', default=None)
ARGPARSER.add_argument('-i', '--channel_id', help='extract single channel by ID',
                       nargs='?', default=None)
ARGPARSER.add_argument('-s', '--start_date', help='start extraction at specified date' \
                       ' - format YYYY-MM-DD', nargs='?', default=None, type=is_valid_date)
ARGPARSER.add_argument('-O', '--show_empty_channels', help='extract and output empty channels',
                       action='store_true')
ARGPARSER.add_argument('-X', '--do_not_anonymize', help='do not anonymize conversations',
                       action='store_true')
ARGS = ARGPARSER.parse_args()

# set global START_DATE variable if provided
if ARGS.start_date:
    # after validation through argparser, ARGS.start_date contains a datetime object
    # the mattermost database contains unix timestamps with 13 digits
    START_DATE = datetime.timestamp(ARGS.start_date)*1000
# START_DATE needs to be defined, so set it to False if no value is provided
else:
    START_DATE = False

# construct Extractor with database arguments
EXTRACTOR = Extractor(ARGS.username, ARGS.password, ARGS.database)
# get channels from Extractor as per the supplied selection criteria arguments
#  channels is a list of dictionaries
CHANNELS = EXTRACTOR.get_channels(ARGS.channel_type, ARGS.team_name, ARGS.channel_id)
# read anonymization pattern files from ./patterns directory
anonymize.read_patterns('./patterns')

# iterate over channel list
for c in CHANNELS:
    # parse channel
    parsed_channel = parse_channel(c, ARGS.show_empty_channels, ARGS.do_not_anonymize)
    # format as CSV
    formatted_channel = format_csv(parsed_channel)
    output_channel(formatted_channel, ARGS.write_to)

# destruct Extractor
del EXTRACTOR
