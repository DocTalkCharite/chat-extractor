# file: lib/anonymize.py
"""
A collection of constants and functions to anonymize chat content extracted from a
 Mattermost database.
This module is used as part of the chat-extractor command line utility to extract, anonymize and
 format chat content from Mattermost.
"""
# imports
import datetime
import random
import re
from os import listdir
from os.path import isfile, join

# substitution constants
# delimiters for enclosing replaced message content
REPLACE_DELIM = ('<', '>')
# email RegEx patter
#  long pattern string broken into pieces to improve readability
EMAIL_PATTERN = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|" +
                           r"(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|" +
                           r"\[[\t -Z^-~]*])")
# telephone number RegEx pattern
PHONE_PATTERN = re.compile(r"^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$")
# dictionary holding the static patterns and their substitutions to replace
STATIC_PATTERNS = {EMAIL_PATTERN: 'email-address',
                   PHONE_PATTERN: 'phone-number'}
# search patterns and matches for position
#  order matters, first match is used
#  Patterns and substitutions are very specific to the DocTalk projects use-case in a german
#  health-care context and need to be adjusted for other use-cases
POSITIONS = {'assistenz': 'assistenzaerzt*in',
             'weiterbildend' : 'weiterbildende*r aerzt*in',
             r'ober\Srzt': 'oberaerzt*in',
             'rzt': 'aerzt*in'}
# List holding generated substitution functions for pattern-file-based substitutions
#  populated at runtime by read_patterns
SUBSTITUTIONS = list()

def anonymize_conversation(conversation):
    """
    Anonymizes a Mattermost conversation by iteratively replacing known pieces of identifying
     information in the conversation metadata and content.

    Parameters
    ----------
    conversation : list of dict
        List of dictionaries, each representing one message in a conversation and its metadata
         generated at runtime by extractor.get_conversation

    Returns
    -------
    anonymized_conversation : list of dict
        List of dictionaries, each representing one anonymized message and its metadata
    """
    # initialize empty return list
    anonymized_conversation = list()
    # generate list with usernames in conversation
    userlist = list(dict.fromkeys([line['Username'] for line in conversation]))
    # generate list with anonymized aliases
    aliaslist = ['Person' + str(n) for n in range(1, len(userlist) + 1)]
    # randomize order of usernames
    random.shuffle(userlist)
    # merge usernames and aliases
    aliasmap = dict(zip(userlist, aliaslist))
    for line in conversation:
        # DB contains 13-digit UNIX timestamp in miliseconds, divide by 1000 for seconds
        timestamp = line.get('CreateAt') // 1000
        anonymized_date = anonymize_date(timestamp)
        anonymized_user = aliasmap.get(line.get('Username'))
        anonymized_position = anonymize_position(line.get('Position'))
        anonymized_message = anonymize_message(line.get('Message'), aliasmap)
        # append anonymized message to return list
        #  this also normalizes the dict keys
        anonymized_conversation.append({
            'date': anonymized_date,
            'position': anonymized_position,
            'user': anonymized_user,
            'message': anonymized_message})
    return anonymized_conversation

def anonymize_position(position):
    """
    Takes a string representing a users position and returns its normalized, anonymized
     replacement as defined in POSITIONS or 'redacted'

    Parameters
    ----------
    position : str

    Returns
    -------
    anonymized_position : str
        Anonymized match for position, or 'redacted' if no match is found
    """
    for pattern, anonymized_position in POSITIONS.items():
        if re.match(pattern, position.lower()):
            return anonymized_position
    return 'redacted'

def anonymize_date(timestamp):
    """
    Takes a 10-digit UNIX timestamp and returns its corresponding weekday and time (HH:MM)

    Parameters
    ----------
    timestamp : int
        10-digit UNIX timestamp

    Returns
    -------
    anonymized_date : str
        Weekday and time in HH:MM format
    """
    utcdatetime = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
    anonymized_date = utcdatetime.strftime('%A %H:%M')
    return anonymized_date

def anonymize_message(message, aliasmap):
    """
    Takes a string representing a chat message and a dict mapping usernames to anonymous aliases
     and returns an anonymized version of the message by replacing known pieces of identifying
     information within the message

    Parameters
    ----------
    message : str
        message to anonymize
    aliasmap : dict
        dictionary containing usernames within the conversation as keys and corresponding anonymous
         aliases as values

    Returns
    -------
    anonymized_message : str
        anonymized message
    """
    # initialize return value with original message
    #  if nothing is substituted, the anonymized message equals the original
    anonymized_message = message
    # iterate over static patterns and replacements
    for pattern, replacement in [*STATIC_PATTERNS.items(), *aliasmap.items()]:
        ## add delimiters to replacement string
        replacement_delimited = REPLACE_DELIM[0] + replacement + REPLACE_DELIM[1]
        ## find and substitute pattern
        anonymized_message = re.sub(pattern, replacement_delimited, anonymized_message)
    # RegEx pattern to match a single word
    word_pattern = re.compile(r'\w+')
    # iterate over replacement functions containing patterns and replacements from pattern files
    for sub_funct in SUBSTITUTIONS:
        # regex magic here: match every single word,
        #  call replacement function on it and apply to message
        anonymized_message = word_pattern.sub(sub_funct, anonymized_message)
    return anonymized_message

def read_patterns(directory):
    """
    Reads files in given directory and populates SUBSTITUTIONS list with a generated function
     to substitute a set of patterns with a replacement string
    The patterns are read from the files content with one pattern per line, the filename is used
     as substitution string

    Parameters
    ----------
    directory : str
        Path of directory to read pattern files from
    """
    patternfiles = [patternfile for patternfile in listdir(directory)
                    if isfile(join(directory, patternfile))]
    for patternfile in patternfiles:
        print('reading anonymization pattern file ' + patternfile)
        # filename is replace string
        replace = patternfile
        with open(join(directory, patternfile)) as file:
            # generate set of all words in file
            patterns = set(word.strip().lower() for word in file)
        # generate replacement function
        sub_funct = mk_sub_funct(replace, patterns)
        # append new replacement dunction to substitions list
        SUBSTITUTIONS.append(sub_funct)

# helper function to generate replacement functions for regex substitution
# @replace replacement string to return on match
# @patterns set of words to match
def mk_sub_funct(replace, patterns):
    """
    Helper function to generate replacement funtion for RegEx substitution
    Takes a replacement string and a set of patterns and returns a function substituting the
     patterns with the replacement string or returning the word unchanged if no match is found

    Parameters
    ----------
    replace : str
        replacement string for matched patterns
    patterns : set of str
        set containing patterns to replace

    Returns
    -------
    sub_funct_template : function
        generated function, substituting patterns with replacement
    """
    # function template for specific substitution functions
    #  used as regex callable, takes a single regex match object as argument
    def sub_funct_template(matchobj):
        # word from message
        word = matchobj.group(0)
        # check if word is contained in pattern set
        if word.lower() in patterns:
            # if so, return replacement
            return REPLACE_DELIM[0] + replace + REPLACE_DELIM[1]
        # if not, return word unchanged
        return word
    # return generated function
    return sub_funct_template
