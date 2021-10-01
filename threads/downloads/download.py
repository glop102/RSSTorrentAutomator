import threading
import paramiko
import paramiko.hostkeys
import time
import netrc
from pathlib import Path

from paramiko.ssh_exception import SSHException

from .taskprogress import TaskProgress
from .exceptions import DownloadStopFlagException

taskType = "download"
protocols_available = ["sftp","http"]

def validate(hosts:dict,item:dict):
    if item["host"] not in hosts:
        return "Remote Download Host \"{}\" is not known.".format(item["host"])
    host = hosts[item["host"]]
    
    #remoteLocation
    if "remoteLocation" not in item:
        return "Does not have a remote location; aka what am I downloading?"
    if type(item["remoteLocation"]) != str or len(item["remoteLocation"]) == 0:
        return "Remote location does not look valid : \"{}\"".format(item["remoteLocation"])

    #localLocation
    if "localLocation" not in item:
        return "Does not have a local location; aka what am I putting the download?"
    if type(item["localLocation"]) != str or len(item["localLocation"]) == 0:
        return "Local location does not look valid : \"{}\"".format(item["localLocation"])
    
    #protocol
    if "protocol" not in host:
        return "Remote host does not list a protocol to use."
    if host["protocol"] not in protocols_available:
        return "Remote host protocol '{}' is not known".format(host["protocol"])
    
    #no problems found
    return None
def process(hosts:dict,item:dict,stopFlag:threading.Event):
    TaskProgress.reset()
    host = hosts[item["host"]]
    #make sure the folder exists for us to put the file in
    p = Path(item["localLocation"])
    p.parent.mkdir(parents=True,exist_ok=True)
    #decide on which protocol is going to be used based on the host
    if host["protocol"] == "sftp":
        __sftp_download(host,item["remoteLocation"],item["localLocation"],stopFlag)
    elif host["protocol"] == "http":
        __http_download(host,item["remoteLocation"],item["localLocation"])
    else:
        raise(Exception("Unknown download protocol {}".format(host["protocol"])))

#========================================================================================
#  Progress Report Wrapper that handles checking if the stop flag has been set
#========================================================================================
def __download_report_wrapper(function,stopFlag:threading.Event):
    def __download_report_wrapper_inner(*args,**kwargs):
        if stopFlag.is_set():
            raise DownloadStopFlagException()
        function(*args,**kwargs)
    return __download_report_wrapper_inner
#========================================================================================
#  HTTP Specific Functions
#========================================================================================
def __http_download(host:dict,remoteLocation:str,localLocation:str):
    #TODO HTTP Download Support
    print("Sorry, but HTTP is not implemented yet.")
#========================================================================================
#  SFTP Specific Functions
#========================================================================================

__attempt = lambda host,parm,default=None : host[parm] if parm in host else default
def __ssh_connect(host:dict, connection:paramiko.SSHClient):
    """Extracts the information from the passed host dict{} and then opens the connection to the server."""
    
    hostname=host["hostname"]
    port=__attempt(host,"port",22)
    username=__attempt(host,"username")
    privatekey=__attempt(host,"privatekey") #direct plain text private key
    key_filename=__attempt(host,"key_filename") #filename that contains a private key
    password=__attempt(host,"password") #plain text password
    timeout=__attempt(host,"timeout",3)

    try:
        #if no password was given, they may have put it in their .netrc file
        #only look it up if both username and password are missing or they have directly asked to use netrc
        if (username is None and password is None) or username == "netrc":
            #TODO Make the netrc file location configurable
            #TODO Make a second location that lives next to the settings file that we also parse to keep accoutn info seperate from settings
            username,_,password = netrc.netrc().hosts[hostname]
    except:
        pass #we don't really care if it errors from not finding a file or the host not being in the netrc file - this is a backup after all

    #print("sftp://{}:{}@{}:{}".format(username,password,hostname,port))
    connection.connect(
        hostname = hostname,
        port = port,
        username = username,
        pkey = privatekey,
        key_filename = key_filename,
        password = password,
        timeout = timeout
    )
def __ssh_connect_with_hostkeys(host:dict,connection:paramiko.SSHClient):
    """Opens the ssh connection to the host while also handling the logic around known host keys."""
    hostname=host["hostname"]

    #Add all the host key we can - either from the user file on the system or the hostkey line in the settings file
    connection.load_system_host_keys()
    hostkey=__attempt(host,"hostkey")
    keystore=connection.get_host_keys()
    if hostkey is not None and type(hostkey) is str and len(host) > 0:
        #There is a hostkey associated with our host, so lets add that to the list of signitures
        try:
            hostkey=paramiko.hostkeys.HostKeyEntry.from_line(hostkey)
            for name in hostkey.hostnames:
                keystore.add(name,hostkey.key.get_name(),hostkey.key)
        except SSHException:
            print("Added key for the host {} is not valid.".format(hostname))
            pass #if it is not a valid key, then just ignore it
    
    hasHostKey = True
    if keystore.lookup(hostname) is None:
        #we will assume this is the first time connecting and so we assume it is connecting to the right machine
        connection.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        hasHostKey = False

    __ssh_connect(host,connection)
    
    if hasHostKey is False:
        #We know that we started without a public hostkey to verify the remote host, so lets save the hostkey to ensure security of being the same machine next time we connect
        keys = keystore.lookup(hostname)
        if keys is None: return #i guess we didn't connect or something?
        key = keys[keys.keys()[0]]
        host["hostkey"] = paramiko.hostkeys.HostKeyEntry([hostname],key).to_line().strip()

def __sftp_download(host:dict,remoteLocation:str,localLocation:str,stopFlag:threading.Event):
    #TODO check if compression is a good idea for this
    connection = paramiko.SSHClient()
    sftp_client = None

    try:
        #connect to server
        __ssh_connect_with_hostkeys(host,connection)
        #perform download
        sftp_client = connection.open_sftp()
        sftp_client.get(remoteLocation,localLocation,__download_report_wrapper(TaskProgress.reportFileProgress,stopFlag))
    finally:
        if sftp_client is not None: sftp_client.close()
        connection.close()