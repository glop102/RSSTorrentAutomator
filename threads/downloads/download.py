import paramiko
import paramiko.hostkeys
import time

taskType = "download"

def validate(hosts:dict,item:dict):
    if item["host"] not in hosts:
        return "Remote Download Host \"{}\" is not known.".format(item["host"])
    
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
    
    #no problems found
    return None
def process(hosts:dict,item:dict):
    host = hosts[item["host"]]
    #decide on which protocol is going to be used based on the host
    if host["protocol"] == "sftp":
        __sftp_download(host,item["remoteLocation"],item["localLocation"])
    #elif host["protocol"] == "http":
        #__http_download(host,item["remoteLocation"],item["localLocation"])
    else:
        raise(Exception("Unknown download protocol {}".format(host["protocol"])))


#========================================================================================
#  HTTP Specific Functions
#========================================================================================
#========================================================================================
#  SFTP Specific Functions
#========================================================================================

"""
GOAL : Get all settings saved to a single yaml file and not have random other settings files hanging around places
"""

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
    connection.load_system_host_keys()
    hostkey=__attempt(host,"hostkey")
    if hostkey is not None:
        hostkey=paramiko.hostkeys.HostKeyEntry.from_line(hostkey)
        keystore=connection.get_host_keys()
        for name in hostkey.hostnames:
            keystore.add(name)
    # try:
    #     connection.load_host_keys("known_hosts")
    # except IOError:
    #     print("Warning: Unable to open local known_host file. Connection may fail.")


    __ssh_connect(host,connection)
    #TODO remove this section below after getting the parsed hostkey entry added to the knownhosts key store
    # try:
    #     __ssh_connect(host,connection)
    # except paramiko.SSHException as e:
    #     if "not found in known_hosts" in str(e):
    #         connection.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    #         __ssh_connect(host,connection)
    #         connection.save_host_keys("known_hosts")
    #     else:
    #         raise(e)  #propogate the unkown error

def __sftp_progress_callback(currentBytes:int,totalBytes:int):
    pass

def __sftp_download(host:dict,remoteLocation:str,localLocation:str):
    #TODO check if compression is a good idea for this
    connection = paramiko.SSHClient()
    sftp_client = None

    try:
        __ssh_connect_with_hostkeys(host,connection)
        #perform download
        sftp_client = connection.open_sftp()
        sftp_client.get(remoteLocation,localLocation,__sftp_progress_callback)
    finally:
        if sftp_client is not None: sftp_client.close()
        connection.close()