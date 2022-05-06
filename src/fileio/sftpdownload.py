import yaml
import paramiko
import paramiko.hostkeys
from paramiko.ssh_exception import SSHException
import threading
import time
#import netrc  #to be added in the future - for now, bah humbug, cleartext in the config file
from pathlib import Path
from .exceptions import DownloadStopFlagException,UnknownHostException

class SFTPServerConfig(yaml.YAMLObject):
    yaml_tag = u"!SFTPServerConfig"
    yaml_loader = yaml.SafeLoader #whitelist it for being allowed to be parsed with the safe loader
    def __init__(self,hostname:str,username,port=22,privatekey=None,hostkey=None,key_filename=None,password=None,timeout=3):
        self.hostname = hostname
        self.username = username
        self.port = port
        self.privatekey = privatekey
        self.hostkey = hostkey # fingerprint of the server to validate against
        self.key_filename = key_filename
        self.password = password
        self.timeout = timeout
    def __repr__(self) -> str:
        return "{}({}:{})".format(self.__class__.__name__,self.hostname,self.port)

class SFTPDownload(yaml.YAMLObject):
    yaml_tag = u"!SFTPDownload"
    yaml_loader = yaml.SafeLoader #whitelist it for being allowed to be parsed with the safe loader
    def __init__(self,host:str,remoteLocation:str,localLocation:str):
        self.host = host
        self.remoteLocation = remoteLocation
        self.localLocation = localLocation
        self.stopFlag = threading.Event()
    def __repr__(self):
        return "{}({},{},{})".format(
            self.__class__.__name__,
            self.host,
            self.remoteLocation,
            self.localLocation
        )
    
    #============================================================================================
    # Connection and download
    #============================================================================================
    def start(self):
        self.stopFlag.clear()
        serverData = None #TODO have it get the host data from the default store location, and if it fails, it does the following exception
        raise UnknownHostException()
        connection = paramiko.SSHClient()
        sftp_client = None
        try:
            #connect to server
            self.__connect(serverData,connection)
            #perform download
            sftp_client = connection.open_sftp()
            sftp_client.get(
                self.remoteLocation,
                self.localLocation,
                self.__progress_callback
            )
        finally:
            if sftp_client is not None: sftp_client.close()
            connection.close()
    
    def __connect(self,serverData:SFTPServerConfig,connection:paramiko.SSHClient):
        #hostkeys are fingerprints of servers for security purposes
        connection.load_system_host_keys()
        keystore=connection.get_host_keys()
        if serverData.hostkey is not None and type(serverData.hostkey) is str and len(serverData.hostkey) > 0:
            #There is a hostkey associated with our host, so lets add that to the list of signatures
            try:
                hostkey=paramiko.hostkeys.HostKeyEntry.from_line(serverData.hostkey)
                for name in hostkey.hostnames:
                    keystore.add(name,hostkey.key.get_name(),hostkey.key)
            except SSHException:
                print("Fingerprint hostkey for the host {} is not valid. It will be ignored and generated fresh upon connection.".format(serverData.hostname))
                pass #if it is not a valid key, then just ignore it
        if keystore.lookup(serverData.hostname) is None:
            #we will assume this is the first time connecting and so we assume it is connecting to the right machine
            connection.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        # NETRC Lookup - this will be something added later
        # try:
        #     #if no password was given, they may have put it in their .netrc file
        #     #only look it up if both username and password are missing or they have directly asked to use netrc
        #     if (username is None and password is None) or username == "netrc":
        #         #TODO Make the netrc file location configurable
        #         #TODO Make a second location that lives next to the settings file that we also parse to keep accoutn info seperate from settings
        #         username,_,password = netrc.netrc().hosts[hostname]
        # except:
        #     pass #we don't really care if it errors from not finding a file or the host not being in the netrc file - this is a backup after all
        connection.connect(
            hostname = serverData.hostname,
            port = serverData.port,
            username = serverData.username,
            pkey = serverData.privatekey,
            key_filename = serverData.key_filename,
            password = serverData.password,
            timeout = serverData.timeout
        )

        #Cleanup of saving the hostkey if the server config did not have the host key saved
        if serverData.hostkey == None or len(serverData.hostkey)==0:
            #We know that we started without a public hostkey to verify the remote host, so lets save the hostkey to ensure security of being the same machine next time we connect
            keys = keystore.lookup(serverData.hostname)
            if keys is None: return #i guess we didn't connect or something?
            key = keys[keys.keys()[0]]
            serverData.hostkey = paramiko.hostkeys.HostKeyEntry([serverData.hostname],key).to_line().strip()


    #============================================================================================
    # Progress Reporting
    #============================================================================================
    def __progress_callback(self,currentBytes:int,totalBytes:int) -> None:
        """
        This gets called from paramiko to report when another chunk has been downloaded and saved to disk.
        This is where we save the progress elsewhere and update timestamps for speed approximations.
        """
        if self.stopFlag.is_set():
            raise DownloadStopFlagException()
    def getPercentage(self)->float:
        """Returns a number between 0 and 1 as a float. It is calculated off of currentCount and maxCount"""
        pass