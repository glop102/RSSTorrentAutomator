import paramiko
import socket
import time

global sftp,sftp_transport
sftp_transport = None
sftp = None

sftp_chunk_size = 32768


__start_time = None
def write(string): print(string,end="")
def __periodic_status_print(bytes_done,bytes_total):
    out = "\r\t"
    percentage = int(int(bytes_done*1000)/int(bytes_total))/10.0
    out = out + str(percentage).rjust(6) + "%    "

    elapsed_time = time.time() - __start_time
    speed = float(bytes_done) / elapsed_time
    speed_type = " B/s"
    if speed < 1000: pass #really slow bytes per second
    elif speed < 1000*1000:
        speed_type = "KB/s"
        speed = speed / 1000.0
    elif speed < 1000*1000*1000:
        speed_type = "MB/s"
        speed = speed / (1000*1000.0)
    else:
        speed_type = "GB/s"
        speed = speed / (1000*1000*1000.0)
    speed = int(speed*10.0)/10.0 # limit to 1 decimalpoint
    out = out + str(speed).rjust(7) + " " + speed_type

    print(out,end="")
def __download_single_file(remote_loc,local_loc):
    global __start_time
    __start_time = time.time()
    sftp.get(remote_loc,local_loc,callback=__periodic_status_print)
    print() # clear the progress line

#========================================================================================
#  Standard API Functions
#========================================================================================

def setup_downloads_thread(defaults):
    """
    Given the hostname and the credentials, will get the system setup to download
    and will start a thread that handles downloads in the background.
    If we are not able to connect to the remote machine, then we will simply
    add files to the conf for downloading later.
    """
    if not "download_host" in defaults:
        print("Download Info Not Given - running in buffer mode")
    host = defaults["download_host"]
    port = 22
    if ":" in host:
        host,port = host.split(":")

    username,password = defaults["download_credentials"].split(":")
    global sftp_transport,sftp
    try:
        sftp_transport = paramiko.Transport((host, port))
        sftp_transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(sftp_transport)
    except:
        print("Warning: Unable to connect sftp client to remote server")
        sftp_transport = None
        sftp = None
    #TODO - start the second thread
def queue_file_for_download(remote_loc,local_loc):
    """
    This will add the file to a list of files that are to be downloaded.
    This runs as a seperate thread so that other operations can happen.
    Files queued in this manner will be added to a conf file so that when
    the program starts again, it will resume downloading.
    """
    pass
def stop_downloads_thread():
    """
    It will cancel the current file download, cleanup whatever partial files
    have been made, and then write out the conf file with all the entries.
    """
    pass
