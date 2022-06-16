from ..serialize import Serializable
import paramiko
import paramiko.hostkeys
from paramiko.ssh_exception import SSHException
import time
from pathlib import Path
from collections import deque
from typing import List
from enum import Enum
import stat
#import netrc  #to be added in the future - for now, bah humbug, cleartext in the config file

from ..utils import humanReadableSpeed,humanReadableFilesize
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
    def __repr__(self) -> str:
        return "{}({}:{})".format(self.__class__.__name__,self.hostname,self.port)

class SFTPDownloadProcessingStages(Enum):
        HAS_NOT_STARTED = 0
        CONNECTING = 1
        ENUMERATING_FILES = 2
        REPORTING_TOTAL_JOB_SIZE = 3
        DOWNLOADING_FILES = 4
        DONE = 5

class SFTPDownload(FileIOHandlerInterface):
    yaml_tag = u"!SFTPDownload"
    def __init__(self,host:str,remoteLocation:str,localLocation:str):
        super().__init__()
        self.host = host
        self.remoteLocation = remoteLocation
        self.localLocation = localLocation

        self.__resetProgressCounters(SFTPDownloadProcessingStages.HAS_NOT_STARTED)
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
        self.__resetProgressCounters(SFTPDownloadProcessingStages.CONNECTING)
        if not self.host in fileioParent.hosts:
            raise UnknownHostException("Cannot find the host config for {} in the FileIO list".format(self.host))
        serverData = fileioParent.hosts[self.host]
        if type(serverData) is not SFTPServerConfig:
            raise UnknownHostException("The host config {} is not of the type SFTPServerConfig".format(self.host))

        connection = paramiko.SSHClient()
        sftp_client = None
        try:
            #connect to server
            self.__connect(serverData,connection)
            #perform download
            sftp_client = connection.open_sftp()

            # find all remote files in case the remote location is a directory
            self.__resetProgressCounters(SFTPDownloadProcessingStages.ENUMERATING_FILES)
            files = self.__recursiveDiscoverFiles(sftp_client,self.remoteLocation,self.localLocation)

            # update the progress counters to know how many files there are and the total number of bytes to be downloaded
            self.__resetProgressCounters(SFTPDownloadProcessingStages.REPORTING_TOTAL_JOB_SIZE,
                numFiles=len(files),
                totalSize=sum(f["filesize"] for f in files)
                )

            # perform the download of every file
            for f_num,f_info in enumerate(files):
                self.__resetProgressCounters(SFTPDownloadProcessingStages.DOWNLOADING_FILES,
                    numFiles=f_num+1,
                    totalSize=f_info["filesize"],
                    fileRemoteLoc=f_info["remoteLocation"],
                    fileLocalLoc=f_info["localLocation"]
                    )

                #Make sure the folder exists for us to save the file into
                Path(f_info["localLocation"]).parent.mkdir(parents=True,exist_ok=True)

                sftp_client.get(
                    f_info["remoteLocation"],
                    f_info["localLocation"],
                    self.__progress_callback
                )
        finally:
            if sftp_client is not None: sftp_client.close()
            connection.close()
            self.__resetProgressCounters(SFTPDownloadProcessingStages.DONE)
    
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
    def __recursiveDiscoverFiles(self,sftp_client,remoteLocation:str,localLocation:str) -> List[dict]:
        """Returns a dicts that describe the remote files. The following keys are provided:
        remoteLocation - the location on the remote system
        localLocation - the corresponding local location if it were to be downloaded to preserve the file structure
        filesize - the size in bytes of this file
        """
        files = []
        for f in sftp_client.listdir(remoteLocation):
            fRemoteLocation = remoteLocation+"/"+f
            fLocalLocation = localLocation+"/"+f
            try:
                f_stats = sftp_client.stat(fRemoteLocation)
            except Exception as e:
                print(e)
                raise e
            if stat.S_ISDIR(f_stats.st_mode):
                files.extend(self.__recursiveDiscoverFiles(sftp_client,fRemoteLocation,fLocalLocation))
            else:
                f_info = {}
                f_info["remoteLocation"] = fRemoteLocation
                f_info["localLocation"] = fLocalLocation
                f_info["filesize"] = f_stats.st_size
                files.append(f_info)
        return files


    #============================================================================================
    # Progress Reporting
    #============================================================================================
    def __resetProgressCounters(self,processingStage=SFTPDownloadProcessingStages.HAS_NOT_STARTED,numFiles=0,totalSize=0,fileRemoteLoc="",fileLocalLoc=""):
        """Note: numFiles and totalSize are used for two different things based on context of what step we are on"""
        self.__progress_stage = processingStage

        if processingStage in [SFTPDownloadProcessingStages.HAS_NOT_STARTED, SFTPDownloadProcessingStages.CONNECTING, SFTPDownloadProcessingStages.ENUMERATING_FILES]:
            #nothing to bother setting up yet
            return
        elif processingStage == SFTPDownloadProcessingStages.REPORTING_TOTAL_JOB_SIZE:
            #Stats for the total processing job
            self.__progress_total_bytesDone = 0
            self.__progress_total_bytesTotal = totalSize
            self.__progress_total_currentFileNum = 0
            self.__progress_total_numFiles = numFiles
            self.__progress_timeStart = time.monotonic()
            #placeholder for the individual file
            self.__progress_file_bytesTotal = 0
        elif processingStage == SFTPDownloadProcessingStages.DOWNLOADING_FILES:
            #the previous file finished so add that to the total number of bytes done
            self.__progress_total_bytesDone += self.__progress_file_bytesTotal
            #Stats for the currently downloading file
            self.__progress_total_currentFileNum = numFiles
            self.__progress_file_bytesDone = 0
            self.__progress_file_bytesTotal = totalSize
            self.__progress_file_remoteLocation = fileRemoteLoc
            self.__progress_file_localLocation = fileLocalLoc

            # This is a sliding window of speeds For every time slice within this window.
            # To get the ongoing speed, use the average of the deque so that it is more robust to random variation
            self.__progress_speedWindow_speeds = deque(maxlen=10)
            self.__progress_speedWindow_prevtime = time.monotonic()
            self.__progress_speedWindow_prevbytes = 0
        elif processingStage == SFTPDownloadProcessingStages.DONE:
            self.__progress_timeStop = time.monotonic()

    def __progress_callback(self,currentBytes:int,totalBytes:int) -> None:
        """
        This gets called from paramiko to report when another chunk has been downloaded and saved to disk.
        This is where we save the progress elsewhere and update timestamps for speed approximations.
        """
        # note to future me - this stop flag works as optimally as it can
        # paramiko must still wait on queued up reads to finish before it will actually let us disconnect from the server
        # it can queue up to 100 read requests which can take a little while to flush - by my testing ~1.5 minutes
        self.checkStopFlags()

        self.__progress_file_bytesDone = currentBytes
        if not totalBytes == self.__progress_file_bytesTotal:
            print("Warning: paramiko reports {} bytes but sftp stat reports {} bytes".format(totalBytes,self.__progress_total_bytesTotal))
            print(self.__progress_file_remoteLocation)

        now = time.monotonic()
        timediff = now - self.__progress_speedWindow_prevtime
        if timediff > 1.0:
            speed = float(currentBytes - self.__progress_speedWindow_prevbytes) / timediff
            self.__progress_speedWindow_speeds.append(speed)
            self.__progress_speedWindow_prevtime = now
            self.__progress_speedWindow_prevbytes = currentBytes
            
    def getProcessingPercentage(self)->float:
        """Returns a number between 0 and 1 as a float. It is calculated off of the number of bytes downloaded versus total bytes for a file."""
        if self.__progress_stage in [SFTPDownloadProcessingStages.HAS_NOT_STARTED, SFTPDownloadProcessingStages.CONNECTING, SFTPDownloadProcessingStages.ENUMERATING_FILES, SFTPDownloadProcessingStages.REPORTING_TOTAL_JOB_SIZE]:
            # no downloading has happened yet
            return 0.0
        elif self.__progress_stage == SFTPDownloadProcessingStages.DOWNLOADING_FILES:
            # give a realisitc percentage of how much of the overall download job is done
            return float(self.__progress_file_bytesDone + self.__progress_total_bytesDone) / self.__progress_total_bytesTotal
        elif self.__progress_stage == SFTPDownloadProcessingStages.DONE:
            return 1.0

        print("Warning: somehow reached the end of SFTPDownload getProcessingPercentage")
        return 0.0
    def getProcessingStatus(self,verbose:bool=False)-> str:
        if self.__progress_stage == SFTPDownloadProcessingStages.HAS_NOT_STARTED:
            if not verbose : return "SFTP Download has not started yet"
            return "SFTP Download has not started yet\nhost : {}\nremote location : {}\nlocal location : {}".format(self.host,self.remoteLocation,self.localLocation)
        elif self.__progress_stage == SFTPDownloadProcessingStages.CONNECTING:
            if not verbose : return "Connecting to server..."
            return "SFTP Download is connecting to the server...\nhost : {}\nremote location : {}\nlocal location : {}".format(self.host,self.remoteLocation,self.localLocation)
        elif self.__progress_stage == SFTPDownloadProcessingStages.ENUMERATING_FILES or self.__progress_stage == SFTPDownloadProcessingStages.REPORTING_TOTAL_JOB_SIZE:
            if not verbose : return "Enumerating files to download..."
            return "SFTP Download is enumerating files to download...\nhost : {}\nremote location : {}\nlocal location : {}".format(self.host,self.remoteLocation,self.localLocation)
        elif self.__progress_stage == SFTPDownloadProcessingStages.DOWNLOADING_FILES:
            filePercentage = float(self.__progress_file_bytesDone) / self.__progress_file_bytesTotal
            if len(self.__progress_speedWindow_speeds) > 0:
                downloadSpeed = humanReadableSpeed(sum(self.__progress_speedWindow_speeds) / len(self.__progress_speedWindow_speeds))
            else: downloadSpeed = humanReadableSpeed(0)
            currentFilesize = humanReadableFilesize(self.__progress_file_bytesDone)
            totalFilesize = humanReadableFilesize(self.__progress_file_bytesTotal)

            totalPercentage = self.getProcessingPercentage()
            fileNum = self.__progress_total_currentFileNum
            filesTotal = self.__progress_total_numFiles
            currentJobSize = humanReadableFilesize(self.__progress_file_bytesDone + self.__progress_total_bytesDone)
            totalJobSize = humanReadableFilesize(self.__progress_total_bytesTotal)

            status = f"{filePercentage:6.1%} {downloadSpeed}  ({currentFilesize}/{totalFilesize}) : File {fileNum}/{filesTotal} Total {totalPercentage:6.1%}  ({currentJobSize}/{totalJobSize})"
            if verbose:
                status += "\nhost : "+self.host
                status += "\nremote : "+self.__progress_file_remoteLocation
                status += "\nlocal : "+self.__progress_file_localLocation
            return status
        elif self.__progress_stage == SFTPDownloadProcessingStages.DONE:
            filesTotal = self.__progress_total_numFiles
            totalJobSize = humanReadableFilesize(self.__progress_total_bytesTotal)
            totalJobSpeed = humanReadableSpeed( float(self.__progress_total_bytesTotal) / (self.__progress_timeStop - self.__progress_timeStart) )
            status = f"SFTP Download Complete: {filesTotal} Files, {totalJobSize} Downloaded, {totalJobSpeed} Average speed"
            if verbose:
                status += "\nhost : "+self.host
                status += "\nremote : "+self.remoteLocation
                status += "\nlocal : "+self.localLocation
            return status

        s = "Warning: somehow reached the end of SFTPDownload getProcessingStatus. Unknown state of this job."
        print(s)
        return s