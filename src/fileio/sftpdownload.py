from ..serialize import Serializable
import paramiko
import paramiko.hostkeys
from paramiko.ssh_exception import SSHException
import time
#import netrc  #to be added in the future - for now, bah humbug, cleartext in the config file
from pathlib import Path
from .exceptions import UnknownHostException
from .ioqueue import FileIO,FileIOHandlerInterface

class SFTPServerConfig(Serializable):
    yaml_tag = u"!SFTPServerConfig"
    def __init__(self,hostname:str,username:str,port:int=22,privatekey:str=None,hostkey:str=None,key_filename:str=None,password:str=None,timeout:int=3):
        self.hostname = hostname
        self.username = username
        self.port = port
        self.privatekey = privatekey
        self.hostkey = hostkey # fingerprint of the server to validate against
        self.key_filename = key_filename
        self.password = password
        self.timeout = timeout

        # temp vars for progress reporting
        
    def __repr__(self) -> str:
        return "{}({}:{})".format(self.__class__.__name__,self.hostname,self.port)

class SFTPDownload(FileIOHandlerInterface):
    yaml_tag = u"!SFTPDownload"
    def __init__(self,host:str,remoteLocation:str,localLocation:str):
        super().__init__()
        self.host = host
        self.remoteLocation = remoteLocation
        self.localLocation = localLocation
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
    def start(self,fileioParent:FileIO):
        self.checkStopFlags()
        if not self.host in fileioParent.hosts:
            raise UnknownHostException("Cannot find the host config for {} in the FileIO list".format(self.host))
        serverData = fileioParent.hosts[self.host]
        if type(serverData) is not SFTPServerConfig:
            raise UnknownHostException("The host config {} is not of the type SFTPServerConfig".format(self.host))

        connection = paramiko.SSHClient()
        sftp_client = None
        try:
            #connect to server
            print("Connecting...")
            self.__connect(serverData,connection)
            #perform download
            print("Downloading...")
            sftp_client = connection.open_sftp()
            self.__resetProgressCounters()
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
            if keys is None: return #i guess we didn't connect or something? IDK because i am getting connections without this getting filled out
            key = keys[keys.keys()[0]]
            serverData.hostkey = paramiko.hostkeys.HostKeyEntry([serverData.hostname],key).to_line().strip()


    #============================================================================================
    # Progress Reporting
    #============================================================================================
    def __resetProgressCounters(self):
        self.__progress_bytesDone = 0
        self.__progress_bytesTotal = 0
        self.__progress_timeStart = time.monotonic()
    def __progress_callback(self,currentBytes:int,totalBytes:int) -> None:
        """
        This gets called from paramiko to report when another chunk has been downloaded and saved to disk.
        This is where we save the progress elsewhere and update timestamps for speed approximations.
        """
        self.checkStopFlags()
        self.__progress_bytesDone = currentBytes
        self.__progress_bytesTotal = totalBytes
    def getProcessingPercentage(self)->float:
        """Returns a number between 0 and 1 as a float. It is calculated off of the number of bytes downloaded versus total bytes for a file."""
        return float(self.__progress_bytesDone) / self.__progress_bytesTotal
    def getProcessingStatus(self)-> str:
        filesize = self.__progress_bytesTotal
        filesizeSuffix = ["Bytes","KB","MB","GB","TB"]
        filesizeIndex = 0
        while(filesize > 1000):
            filesizeIndex += 1
            filesize /= 1000

        if self.__progress_bytesDone != self.__progress_bytesTotal:
            percent = float(self.__progress_bytesDone)/self.__progress_bytesTotal
            speed = self.__progress_bytesDone / float( time.monotonic() - self.__progress_timeStart )
            speedSuffix = ["Bps","KBps","MBps","GBps","TBps"]
            speedIndex = 0
            while(speed > 1000):
                speedIndex += 1
                speed /= 1000
            return "{:3.1%} - {:3.1f} {}".format(percent,speed,speedSuffix[speedIndex])
        else:
            return "100.0% - {:3.1f} {}".format(filesize,filesizeSuffix[filesizeIndex])