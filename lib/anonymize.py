# file: anonymize.py

# global imports
import datetime
import random
import re
from os import listdir
from os.path import isfile, join

# debug
from pprint import pprint

### Substitution Constants
# tuple
# delimiters for enclosing replaced message content
REPLACE_DELIM = ('<', '>')
# email RegEx patter
EMAIL_PATTERN = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")
PHONE_PATTERN = re.compile(r"^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$")
# dictionary
STATIC_PATTERNS = {EMAIL_PATTERN: 'email-address',
                   PHONE_PATTERN: 'phone-number'}
# dictionary
#  search patterns and matches for position
#  order matters, first match is used
POSITIONS = {'assistenz': 'assistenzaerzt*in',
             'weiterbildend' : 'weiterbildende*r aerzt*in',
             r'ober\Srzt': 'oberaerzt*in',
             'rzt': 'aerzt*in'}
# list
#  populated with replacement functions at runtime by read_patterns
substitutions = list()
###

# @conversation list of dictionaries, as provided by extract.mm_get_conversation
# @return list of dictionaries
def anonymize_conversation(conversation):
    # initialize empty return list
    anonymized = list()
    # generate list with usernames in conversation
    userlist = list(dict.fromkeys([line['Username'] for line in conversation]))
    # generate list with anonymized aliases
    aliaslist = ['Person' + str(n) for n in range(1, len(userlist) + 1)]
    # randomize order of usernames
    random.shuffle(userlist)
    # merge usernames and aliases
    aliasmap = dict(zip(userlist, aliaslist))
    for line in conversation:
        # DB contains UNIX timestamp in miliseconds, divide by 1000 for seconds
        timestamp = line.get('CreateAt') // 1000
        anondate = anonymize_date(timestamp)
        user = aliasmap.get(line.get('Username'))
        position = anonymize_position(line.get('Position'))
        anonymized_message = anonymize_message(line.get('Message'), aliasmap)
        anonymized.append({
            'date': anondate,
            'position': position,
            'user': user,
            'message': anonymized_message})
    return anonymized

def anonymize_position(position):
    for pattern, anonposition in POSITIONS.items():
        if re.match(pattern, position.lower()):
            return anonposition
    return 'redacted'

# @date timestamp UNIX timestamp in seconds
# @return string anonymized date (weekday HH:MM)
def anonymize_date(timestamp):
    utcdatetime = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
    anondate = utcdatetime.strftime('%A %H:%M')
    return anondate

# @message string line
# @aliasmap dict user and alias mapping
# @return tuple anonline, replace count
def anonymize_message(line, aliasmap):
    anonymized_line = line
    # iterate over static patterns and replacements
    for pattern, replacement in [*STATIC_PATTERNS.items(), *aliasmap.items()]:
        ## add delimiters to replacement string
        replacement_delimited = REPLACE_DELIM[0] + replacement + REPLACE_DELIM[1]
        ## find and substitute pattern
        anonymized_line = re.sub(pattern, replacement_delimited, anonymized_line)
    # replace patterns from pattern files
    ## re pattern to match a single word
    word_pattern = re.compile(r'\w+')
    ## iterate over replacement functions containing patterns and replacements
    for sub_funct in substitutions:
        ## regex magic here: match every single word,
        ##  call replacement function on it and apply to message
        anonymized_line = word_pattern.sub(sub_funct, anonymized_line)
    return anonymized_line

# read patterns for substitution from files
#  files contain one pattern (e.g. names) per line
#  filename is used as replacement string
# @directory path of directory containing pattern files
# @return none
def read_patterns(directory):
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
        substitutions.append(sub_funct)

# helper function to generate replacement functions for regex substitution
# @replace replacement string to return on match
# @patterns set of words to match
def mk_sub_funct(replace, patterns):
    ## function template for specific substitution functions
    ##  used as regex callable, takes a single regex match object as argument
    def sub_funct_template(matchobj):
        ### word from message
        word = matchobj.group(0)
        ### check if word is contained in pattern set
        if word.lower() in patterns:
            ### if so, return replacement
            return REPLACE_DELIM[0] + replace + REPLACE_DELIM[1]
        ### if not, return word unchanged
        return word
    ## return generated function
    return sub_funct_template
