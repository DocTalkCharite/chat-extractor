# file: extract.py
# extractor class to retrieve conversation data from mattermost database
#  implemented object oriented because connection reusing is required
#  which is easier to implement in OOP

# imports
import sys
import mariadb

class Extractor:
    """
    A class representing a MariaDB database cursor to extract conversation data from a Mattermost database.

    ...

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
        Public method to generate a list of dictionaries, each dictionary representing a channel from the
        Mattermost database that matches the selection criteria.
    get_conversation(channel_id, start_date=False, filtertype=False):
        Public method to generate a list of dictionaries, each dictionary representing a post in the given
        channel that matches the selection critera.
    """

    def __init__(self, username, password, database):
        """
        Constructs the Extractor instance, using the provided parameters to connect to the database and
        initializing the db_connection and db_cursor attributes.

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
                # We're trying to connect to the MariaDB UNIX Socket at its default location in Ubuntu Linux.
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
        if len(result) != 1: raise ValueError
        return result[0].get('Id')

    # get mattermost channels with channel ID, channel displayname, channel type and team displayname
    # @return list of dictionaries channels
    def get_channels(self, channel_type=None, team_name=None, channel_id=None):
        """
        Public method to generate a list of dictionaries, each dictionary representing a channel from the
        Mattermost database that matches the selection criteria.

        Parameters
        ----------
        channel_type : str

        team_name : str

        channel_id : str

        Returns
        -------
        channels : list of dict
        
        """

        # get only single channel if channel_id is provided
        if channel_id:
            self.db_cursor.execute("SELECT Channels.Id,Channels.DisplayName,Channels.Type,Teams.DisplayName AS TeamName FROM Channels LEFT JOIN Teams ON Channels.TeamId = Teams.Id WHERE Channels.Id=?;", (channel_id,))
            return self.db_cursor.fetchall()
        # get team_id if team_name is provided
        if team_name: team_id = self.__get_team_id(team_name)
        # determine query to execute
        if channel_type and team_name:
            self.db_cursor.execute("SELECT Channels.Id,Channels.DisplayName,Channels.Type,Teams.DisplayName AS TeamName FROM Channels LEFT JOIN Teams ON Channels.TeamId = Teams.Id WHERE Channels.Type=? AND Channels.TeamId=?;", (channel_type,team_id))
        elif channel_type:
            self.db_cursor.execute("SELECT Channels.Id,Channels.DisplayName,Channels.Type,Teams.DisplayName AS TeamName FROM Channels LEFT JOIN Teams ON Channels.TeamId = Teams.Id WHERE Channels.Type=?;", (channel_type,))
        elif team_name:
            self.db_cursor.execute("SELECT Channels.Id,Channels.DisplayName,Channels.Type,Teams.DisplayName AS TeamName FROM Channels LEFT JOIN Teams ON Channels.TeamId = Teams.Id WHERE Channels.TeamId=?;", (team_id,))
        else:
            self.db_cursor.execute("SELECT Channels.Id,Channels.DisplayName,Channels.Type,Teams.DisplayName AS TeamName FROM Channels LEFT JOIN Teams ON Channels.TeamId = Teams.Id;")
        channels = self.db_cursor.fetchall()
        return channels

    # get mattermost posts for channel_id
    # @return list of dictionaries posts
    def get_conversation(self, channel_id, start_date=False, filtertype=False):
        if start_date:
            self.db_cursor.execute("SELECT Users.Username,Users.Position,Posts.CreateAt,Posts.Type,Posts.Message FROM Posts INNER JOIN Users ON Posts.UserId = Users.Id WHERE Posts.ChannelId=? AND Posts.CreateAt>=? ORDER BY Posts.CreateAt;", (channel_id,start_date))
        else:    
            self.db_cursor.execute("SELECT Users.Username,Users.Position,Posts.CreateAt,Posts.Type,Posts.Message FROM Posts INNER JOIN Users ON Posts.UserId = Users.Id WHERE Posts.ChannelId=? ORDER BY Posts.CreateAt;", (channel_id,))
        result = self.db_cursor.fetchall()
        # if filtertype is True, return a list with only the dictionaries,
        #  that have an empty 'Type' value
        #  this removes system notification messages from the conversation
        if filtertype:
            return [d for d in result if d['Type'] in '']
        return result
