import paramiko
import os.path
import time
from pathlib import Path
from threading import Thread,Lock,Condition

global sftp,sftp_transport
sftp_transport = None
sftp = None

sftp_chunk_size = 32768

global __start_time,__last_status_print
__start_time = None
__last_status_print = None
def __periodic_status_print(bytes_done,bytes_total):
    now = time.time()
    global __last_status_print
    if (now - __last_status_print) < 5: #print every 5 seconds
        return
    __last_status_print = now

    out = "\t"
    percentage = int(int(bytes_done*1000)/int(bytes_total))/10.0
    out = out + str(percentage).rjust(6) + "%    "

    elapsed_time = now - __start_time
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

    print(out)
def __download_single_file(remote_loc,local_loc):
    __make_folder_parent(local_loc)
    print("Starting File Download : "+local_loc)
    global __start_time,__last_status_print
    __start_time = time.time()
    __last_status_print = time.time()
    sftp.get(remote_loc,local_loc,callback=__periodic_status_print)
    print("\tFile Download Complete")
def __make_folder_parent(loc):
    #Make sure the folder exists, and touch the file
    p = Path(loc)
    p.parent.mkdir(parents=True,exist_ok=True)

def __recursive_delete(path):
    files = sftp.listdir(path)

    for f in files:
        filepath = os.path.join(path, f)
        try:
            sftp.remove(filepath)
        except IOError:
            __recursive_delete(filepath)

    sftp.rmdir(path)
def __delete_path(path):
    try: #assume it is a file
        sftp.remove(path)
    except IOError: #actually a directory
        __recursive_delete(path)

#========================================================================================
#  Download Queue Functions
#========================================================================================

global items,tags,download_lock
items = []
tags = []
queue_lock = Lock()

def add_item_to_queue(item,tag):
    with queue_lock:
        items.append(item)
        tags.append(tag)
def get_next_item_from_queue():
    with queue_lock:
        return items[0]
def remove_next_item_from_queue():
    with queue_lock:
        items.pop(0)
        tags.pop(0)
def check_if_tag_in_queue(tag):
    with queue_lock:
        return tag in tags
def add_item_to_front_of_queue(item,tag,pos=0):
    with queue_lock:
        pos = min(pos,len(items))
        items.insert(pos,item)
        tags.insert(pos,tag)

def save_queue_to_file():
    with queue_lock:
        f = open("queued_downloads.conf","w")
        for item,tag in zip(items,tags):
            f.write(item[0]+"\n")
            f.write(item[1]+"\n")
            f.write(tag+"\n")
        f.close()
def load_queue_from_file():
    try:
        with queue_lock:
            f = open("queued_downloads.conf","r")
            item = [ f.readline()[:-1] , f.readline()[:-1] ]
            tag = f.readline()[:-1]
            while len(tag) > 0:
                items.append(item)
                tags.append(tag)
                item = [ f.readline()[:-1] , f.readline()[:-1] ]
                tag = f.readline()[:-1]
    except FileNotFoundError:
        #no currently queued files
        pass


#========================================================================================
#  AutoRun Thread Functions
#========================================================================================
global download_thread,downloads_keep_processing
download_thread = None
downloads_keep_processing = True

def main_thread_function():
    """
    This is meant to be called from the Thread object. (Does not hurt to run on it's own)
    This is a simple loop that pops an item from the queue and then downloads the file.
    It continues the loop until it runs out of items in the queue, then exits.
    """
    try:
        while downloads_keep_processing:
            remote_loc,local_loc = get_next_item_from_queue()
            if local_loc == "DELETE_RECURSIVLY":
                __delete_path(remote_loc)
            else:
                __download_single_file(remote_loc,local_loc)
            remove_next_item_from_queue()
            save_queue_to_file()
    except IndexError:
        #print("Download Queue Now Empty")
        pass
    except AssertionError:
        print("\nDownload Daemon exiting...")
def __restart_thread():
    global download_thread,downloads_keep_processing
    if download_thread == None or not download_thread.is_alive():
        downloads_keep_processing = True
        download_thread = Thread(target=main_thread_function)
        download_thread.daemon = True
        download_thread.start()

#========================================================================================
#  Standard API Functions
#========================================================================================

def setup_downloads_thread(defaults):
    """
    Given the hostname and the credentials, will get the system setup to download
    and will intialize components that handles downloads in the background.
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

    load_queue_from_file()
    __restart_thread()
def queue_file_for_download(torrent_id,remote_loc,local_loc):
    """
    This will add the file to a list of files that are to be downloaded.
    This runs as a seperate thread so that other operations can happen.
    Files queued in this manner will be added to a conf file so that when
    the program starts again, it will resume downloading.
    """
    add_item_to_queue([remote_loc,local_loc],torrent_id)
    __restart_thread()
def queue_remote_path_for_deletion(remote_loc):
    """
    This will have the download thread delete the remote location as the next
    task that it does. This does mean it will finish the current download before
    it erases the location, but it should also survive the program getting
    restarted and still be in queue when the it is started again.
    """
    if download_thread.is_alive():
        add_item_to_front_of_queue([remote_loc,"DELETE_RECURSIVLY"],"DELETE_RECURSIVLY",1)
    else:
        add_item_to_front_of_queue([remote_loc,"DELETE_RECURSIVLY"],"DELETE_RECURSIVLY",0)
    __restart_thread()
def stop_downloads_thread():
    """
    It will cancel the current file download, cleanup whatever partial files
    have been made, and then write out the conf file with all the entries.
    """
    if not download_thread == None or download_thread.is_alive():
        #stop the ongoing downloads in the middle of downloading
        global downloads_keep_processing,__current_download_kill
        downloads_keep_processing = False
        #download_thread.join() #uncomment if you want downloads to finish before exiting
    save_queue_to_file()

def check_if_torrent_has_files_queued(torrent_id):
    """
    Returns True or False. This lets you know if there are any files in the queue
    so that you can check if it is safe to delete a torrent.
    """
    return check_if_tag_in_queue(torrent_id)






