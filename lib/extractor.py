# file: lib/Extractor.py
"""
A class representing a MariaDB database cursor to extract conversation data from a Mattermost
 database.
The Extractor is used as part of the chat-extractor command line utility to extract, anonymize and
 format chat content from Mattermost.
"""

# imports
import sys
import mariadb

class Extractor:
    """
    A class representing a MariaDB database cursor to extract conversation data from a Mattermost
     database.

    Attributes
    ----------
    username : str
        MariaDB username to use for the database connection
    password : str
        MariaDB password for the username account
    database : str
        name of the MariaDB database to connect to

    Methods
    -------
    __get_team_id(team_name):
        Private method to get the numeric Mattermost team ID for a given team name.
    get_channels(channel_type=None, team_name=None, channel_id=None):
        Public method to generate a list of dictionaries, each dictionary representing a channel
         from the Mattermost database that matches the selection criteria.
    get_conversation(channel_id, start_date=False, filter_type=False):
        Public method to get all posts within a given channel that match the filter criteria.
    """

    def __init__(self, username, password, database):
        """
        Constructs the Extractor instance, using the provided parameters to connect to the database
         and initializing the db_connection and db_cursor attributes.

        Parameters
        ----------
        username : str
            MariaDB username to use for the database connection
        password : str
            MariaDB password for the username account
        database : str
            name of the MariaDB database to connect to
        """

        self.username = username
        self.password = password
        self.database = database
        # try to connect to MariaDB
        try:
            self.db_connection = mariadb.connect(
                user=self.username,
                password=self.password,
                # We're trying to connect to the MariaDB UNIX Socket at its default location in
                #  Ubuntu Linux.
                unix_socket="/run/mysqld/mysqld.sock",
                database=self.database)
        # exit on connection error
        except mariadb.Error as error:
            print(f"Error connecting to MariaDB: {error}")
            sys.exit(1)
        # get cursor
        self.db_cursor = self.db_connection.cursor(dictionary=True)

    def __del__(self):
        """
        Destructs the instance, closing the MariaDB cursor and connection.
        """

        self.db_cursor.close()
        self.db_connection.close()

    def __get_team_id(self, team_name):
        """
        Private method to get the unique Mattermost team ID for a given team name.

        Parameters
        ----------
        team_name : str
            DisplayName of the team to get the ID for

        Returns
        -------
        result : str
            ID of the team corresponding to DisplayName
            Mattermost uses varchar(26) alphanumeric team IDs
        """

        self.db_cursor.execute("SELECT Id FROM Teams WHERE DisplayName=?;", (team_name,))
        result = self.db_cursor.fetchall()
        # expect exactly one match or raise error
        if len(result) != 1:
            raise ValueError
        return result[0].get('Id')

    def get_channels(self, channel_type=None, team_name=None, channel_id=None):
        """
        Public method to generate a list of dictionaries, each dictionary representing a channel
         from the Mattermost database that matches the selection criteria.
        All parameters are optional and default to 'None', which would get all existing Mattermsot
         channels from the database.

        Parameters
        ----------
        channel_type : str
            Type of the Mattermost channels to get, should be a single char as per Mattermosts
             implementation (D,G,O,P)
        team_name : str
            Name of the Mattermost team to get channels from
        channel_id : str
            Alphanumeric ID of a single specific channel to get

        Returns
        -------
        channels : list of dict
            List of dictionaries with each dictionary representing one channel
            Each dictionary contains the channels unique alphanumeric ID, displayname, type and the
             corresponding teams displaynmae
        """

        # SQL query components as variables to reduce line length and improve readability
        # table fields to select from
        fields = "Channels.Id, Channels.DisplayName, Channels.Type, Teams.DisplayName AS TeamName"
        # table to select from and join on related table
        table = "Channels LEFT JOIN Teams ON Channels.TeamId = Teams.Id"

        # get team_id if team_name is provided
        if team_name:
            team_id = self.__get_team_id(team_name)
        # get a single channel if channel_id is provided
        if channel_id:
            # query condition
            conditions = "Channels.Id=?"
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table} "
                   f"WHERE {conditions};")
            # execute statement, substituting channel_id
            self.db_cursor.execute(sql, (channel_id,))
        # determine query conditions
        elif channel_type and team_name:
            conditions = "Channels.Type=? AND Channels.TeamId=?"
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table} "
                   f"WHERE {conditions};")
            # execute statement, substituting channel_type and team_id
            self.db_cursor.execute(sql, (channel_type, team_id))
        elif channel_type:
            conditions = "Channels.Type=?"
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table} "
                   f"WHERE {conditions};")
            # execute statement, substituting channel_type
            self.db_cursor.execute(sql, (channel_type,))
        elif team_name:
            conditions = "Channels.TeamId=?"
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table} "
                   f"WHERE {conditions};")
            # execute statement, substituting team_id
            self.db_cursor.execute(sql, (team_id,))
        else:
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table};")
            # execute statement without substitutions
            self.db_cursor.execute(sql)
        channels = self.db_cursor.fetchall()
        return channels

    # get mattermost posts for channel_id
    # @return list of dictionaries posts
    def get_conversation(self, channel_id, start_date=False, filter_type=False):
        """
        Public method to get all posts within a given channel that match the filter criteria.
        Posts within the conversation are ordered by their creation date by default.
        Two parameters are optional and default to 'False', which would get all existing posts
         within the channel from the Mattermost database.

        Parameters
        ----------
        channel_id : str
            Unique alphanumeric ID identifying the Mattermost channel
        start_date : int
            Optional 13-digit UNIX timestamp, posts created after start_date will be selected
            Deafults to False, which will select all posts disregarding their creation date
        filter_type : bool
            Optional boolean, if set to True, messages with a non-empty Type value will be filtered
             from the result, this removes Mattermost system messages from the conversation
            Defaults to False, which will select all posts disregarding their type

        Returns
        -------
        conversation : list of dict
            List of dictionaries with each dictionary representing one post within the conversation
            Each dictionary contains the posts username, user position, creation time, post type
             and message
        """

        # SQL query components as variables to reduce line length and improve readability
        # table fields to select from
        fields = "Users.Username, Users.Position, Posts.CreateAt, Posts.Type, Posts.Message"
        # table to select from and join on related table
        table = "Posts INNER JOIN Users ON Posts.UserId = Users.Id"

        if start_date:
            conditions = "Posts.ChannelId=? AND Posts.CreateAt>=?"
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table} "
                   f"WHERE {conditions} "
                   f"ORDER BY Posts.CreateAt;")
            self.db_cursor.execute(sql, (channel_id, start_date))
        else:
            conditions = "Posts.ChannelId=?"
            # build sql statement using f-strings
            sql = (f"SELECT {fields} "
                   f"FROM {table} "
                   f"WHERE {conditions} "
                   f"ORDER BY Posts.CreateAt;")
            self.db_cursor.execute(sql, (channel_id,))
        result = self.db_cursor.fetchall()
        # if filter_type is True, return a list with only the dictionaries,
        #  that have an empty 'Type' value
        #  this removes system notification messages from the conversation
        if filter_type:
            conversation = [d for d in result if d['Type'] in '']
        else:
            conversation = result
        return conversation
