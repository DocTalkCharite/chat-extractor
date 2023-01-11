# file: parse.py

# global imports
import argparse
import os
import time
from datetime import datetime
from itertools import chain

# debug
from pprint import pprint

# local imports
from lib.Extractor import Extractor
import lib.anonymize as anonymize

# constants

# map single letter channel types from database
#  to a more verbose version
CHANNEL_TYPES = {
    'O': 'Open Channel',
    'P': 'Private Channel',
    'D': 'Direct Message Channel',
    'G': 'Group Message Channel'}

# map metadata fields to their corresponding
#  database column name
METADATA = {
    'Channel ID': 'Id',
    'Channel Name': 'DisplayName',
    'Channel Type': 'Type',
    'Team Name': 'TeamName'}

# =========
# functions
# =========

# @channel dict
# @show_empty_channels bool
# @do_not_anonymize bool
# @return dict or False
def parse_channel(channel, show_empty_channels=False, do_not_anonymize=False):
    parsed = dict()
    parsed['Metadata'] = dict()
    # parse channel meta data
    for key, value in METADATA.items():
        if channel.get(value): parsed['Metadata'][key] = channel.get(value)
    # substitute channel type
    parsed['Metadata']['Channel Type'] = CHANNEL_TYPES[parsed['Metadata']['Channel Type']]
    # parse conversation
    conversation = extractor.get_conversation(channel.get('Id'), START_DATE, True)
    if conversation:
        # skip anonymization if told to do so
        if do_not_anonymize:
            # rewrite dictionary keys in conversation to match what anonymize_conversation would produce
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
            if parsed['Metadata']['Channel Type'] == 'Group Message Channel': parsed['Metadata']['Channel Name'] = 'redacted'
            parsed['Metadata']['Anonymized'] = 'True'
    else:
        if show_empty_channels:
            parsed['Conversation'] = 'there are no messages in this channel'
            parsed['Metadata']['Anonymized'] = 'False'
        else:
            return False
    return parsed

# @preparsed dict as provided by parse_channel
# @return dict
def format_csv(preparsed):
    # do not proceed if preparsed is False,
    #  this is the case for empty conversations when parse_channel is called with show_empty_channels=False
    if not preparsed: return False
    parsed = preparsed
    parsed['Metadata']['Format'] = 'CSV'
    parsed['Parsed'] = list()
    # the order of fields in the dict is well known
    #  due to its explicit inititalization in anonymize.py
    separator = [[''], ['date', 'sender position', 'sender name', 'message', 'anonymized']]
    # iterate over Metadata and Conversation and parse linewise to csv
    for line in chain(parsed['Metadata'].items(), separator):
        parsed['Parsed'].append(';'.join(line))
    for line in parsed['Conversation']:
        # escape quotes for csv ( " -> "")
        line['message'] = line['message'].replace('"', '""')
        # replace line breaks
        line['message'] = line['message'].replace('\n', '<enter>')
        # enclose message in quotes to preserve semicolon in the message body
        line['message'] = '"' + line['message'] + '"'
        parsed['Parsed'].append(';'.join([ str(val) for val in line.values()]))
    return parsed

# output parsed channel data, either to a file or to stdout
#  file will be created if destination directory is specified
# @parsed dict
# @destination string empty or directory
def output_parsed(parsed, destination=''):
    if not parsed: return False
    if destination:
        if not os.path.isdir(destination):
            raise ValueError
        channel_id = parsed['Metadata']['Channel ID']
        destfile = open(destination + '/' + channel_id + '.csv', 'w')
        content = [line + '\n' for line in parsed['Parsed']]
        destfile.writelines(content)
        destfile.close()
    else:
        for line in parsed['Parsed']:
            print(line)
        print('---')

# check if provided string is a date of the format YYYY-MM-DD
#  used as validator for the -s argmunent
# @check string
# @return datetime object
def is_valid_date(check):
    try:
        return datetime.strptime(check, "%Y-%m-%d")
    except ValueError:
        message = "not a valid date: {0!r}".format(check)
        raise argparse.ArgumentTypeError(message)

# parse positional arguments
argparser = argparse.ArgumentParser(description = 'Extracts and anonymizes chat content from a Mattermost database')
# only required argument is the mattermost database password
argparser.add_argument('password', help='mattermost database password')
# define a few optional arguments to refine the extraction
argparser.add_argument('-u', '--username', help='mattermost database username', nargs='?', default='mattermost')
argparser.add_argument('-d', '--database', help='mattermost database name', nargs='?', default='mattermost')
argparser.add_argument('-c', '--channel_type', help='channel type to extract', nargs='?', default=None, choices=['D', 'G', 'O', 'P'])
argparser.add_argument('-t', '--team_name', help='team name to extract', nargs='?', default=None)
argparser.add_argument('-w', '--write-to', help='directory to write output to', nargs='?', default=None)
argparser.add_argument('-i', '--channel_id', help='extract single channel by ID', nargs='?', default=None)
argparser.add_argument('-s', '--start_date', help='start extraction at specified date - format YYYY-MM-DD', nargs='?', default=None, type=is_valid_date)
argparser.add_argument('-O', '--show_empty_channels', help='extract and output empty channels', action='store_true')
argparser.add_argument('-X', '--do_not_anonymize', help='do not anonymize conversations', action='store_true')
args = argparser.parse_args()

# set global START_DATE variable if provided
if args.start_date:
    # after validation through argparser, args.start_date contains a datetime object
    # the mattermost database contains unix timestamps with 13 digits
    START_DATE = datetime.timestamp(args.start_date)*1000
# START_DATE needs to be defined, so set it to False if no value is provided
else:
    START_DATE = False

# construct Extractor with database arguments
extractor = Extractor(args.username, args.password, args.database)
# get channels from Extractor as per the supplied selection criteria arguments
#  channels is a list of dictionaries
channels = extractor.get_channels(args.channel_type, args.team_name, args.channel_id)
# read anonymization pattern files from ./patterns directory
anonymize.read_patterns('./patterns')

# iterate over channel list
for channel in channels:
    # parse channel
    parsed = parse_channel(channel, args.show_empty_channels, args.do_not_anonymize)
    # format as CSV
    formatted = format_csv(parsed)
    output_parsed(formatted, args.write_to)

# destruct Extractor
del extractor
