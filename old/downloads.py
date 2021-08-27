import paramiko
import os.path
import time
from io import open,SEEK_END,SEEK_SET
from pathlib import Path
from threading import Thread,Lock,Event

global sftp,sftp_transport
sftp_transport = None
sftp = None

sftp_chunk_size = 32768

global __start_time,__prev_time,__prev_bytes
__start_time = None
__prev_time = None
__prev_bytes = None
def __periodic_status_print(bytes_done,bytes_total):
    now = time.time()
    global __start_time,__prev_time,__prev_bytes
    if bytes_done == bytes_total:
        speed_text = __download_speed_text(bytes_total,now-__start_time)
        print("\tAverage Speed   "+speed_text.rjust(10))
    elif __prev_bytes == -1:
        print("\t         Filesize {}".format(__bytes_count_human_readable(bytes_total)) )
        __prev_bytes = 0
        return
    elif (now - __prev_time) < 5: #only print every 5 seconds
        # Do not spam the logs with extra prints
        return
    else:
        # Incremental percentage/speed update

        # times 100 for percentage and times 10 for an extra decimal point
        percentage = int(int(bytes_done*100*10)/int(bytes_total))/10.0
        percentage = str(percentage).rjust(6)
        elapsed_time = now - __prev_time
        elapsed_bytes = bytes_done - __prev_bytes
        speed_text = __download_speed_text(elapsed_bytes,elapsed_time)
        print("\t{}%         {}".format(percentage,speed_text.rjust(10)))
        __prev_time = now
        __prev_bytes = bytes_done
def __bytes_count_human_readable(nbytes):
    ntype = " B"
    if nbytes < 1000: pass #really slow bytes per second
    elif nbytes < 1000*1000:
        ntype = "KB"
        nbytes = nbytes / 1000.0
    elif nbytes < 1000*1000*1000:
        ntype = "MB"
        nbytes = nbytes / (1000*1000.0)
    else:
        ntype = "GB"
        nbytes = nbytes / (1000*1000*1000.0)
    nbytes = int(nbytes*10.0)/10.0 # limit to 1 decimal point
    return str(nbytes)+" "+ntype
def __download_speed_text(bytes_done,elapsed_time):
    speed = float(bytes_done) / elapsed_time
    text = __bytes_count_human_readable(speed)
    return str(text) + "/s"
def __download_single_file(remote_loc,local_loc):
    __make_folder_parent(local_loc)
    print("Starting File Download : "+local_loc)
    global __start_time,__prev_time,__prev_bytes
    __start_time = time.time()
    __prev_time = __start_time
    __prev_bytes = -1
    sftp.get(remote_loc,local_loc,callback=__periodic_status_print)
    print("\tFile Download Complete")
def __local_copy_single_file(source_loc,dest_loc):
    __make_folder_parent(dest_loc)
    print("Starting File Copy : "+dest_loc)
    global __start_time,__prev_time,__prev_bytes
    __start_time = time.time()
    __prev_time = __start_time
    __prev_bytes = -1
    buf_size = 128*1024
    written_bytes = 0
    src = open(source_loc,"rb")
    dst = open(dest_loc,"wb",buffering=0)
    total_bytes = src.seek(0,SEEK_END)
    src.seek(0,SEEK_SET) #rewind
    while True:
        tmp = src.read(buf_size)
        if not tmp : break
        dst.write(tmp)
        written_bytes += len(tmp)
        __periodic_status_print(written_bytes,total_bytes)
    print("\tFile Copy Complete")
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
        print("Cleaned up remote file : {}".format(path) )
    except IOError: #actually a directory
        __recursive_delete(path)
        print("Cleaned up remote folder : {}".format(path) )

def __setup_sftp():
    global sftp_transport,sftp
    try:
        sftp_transport = paramiko.Transport((host, port))
        sftp_transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(sftp_transport)
        return True
    except Exception as e:
        print(e)
        print("Warning: Unable to connect sftp client to remote server")
        sftp_transport = None
        sftp = None
        return False
def __close_sftp():
    global sftp_transport,sftp
    if sftp is not None:
        sftp.close()
        sftp = None
    if sftp_transport is not None:
        sftp_transport.close()
        sftp_transport = None

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
def get_next_tag_from_queue():
    with queue_lock:
        return tags[0]
def remove_next_item_from_queue():
    with queue_lock:
        items.pop(0)
        tags.pop(0)
def check_if_tag_in_queue(tag):
    with queue_lock:
        return tag in tags
def count_tag_in_queue(tag):
    with queue_lock:
        return tags.count(tag)
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
global download_thread,downloads_stop_flag
download_thread = None
downloads_stop_flag = Event()

def main_thread_function():
    """
    This is meant to be called from the Thread object. (Does not hurt to run on it's own)
    This is a simple loop that pops an item from the queue and then downloads the file.
    It continues the loop until it runs out of items in the queue, then exits.
    """

    try:
        while not downloads_stop_flag.is_set():
            if not __setup_sftp():
                print("Download thread unable to contact server, trying again in 30 seconds")
                downloads_stop_flag.wait(30)
                continue
            remote_loc,local_loc = get_next_item_from_queue()
            tag = get_next_tag_from_queue()
            similar_items_left = count_tag_in_queue(tag)
            protocol = tag.split(":",1)[0]
            print("Download Queue Length : Similar-{} Total-{}".format(similar_items_left,len(items)) )
            if local_loc == "DELETE_RECURSIVLY":
                __delete_path(remote_loc)
            elif protocol == "local-copy":
                __local_copy_single_file(remote_loc,local_loc)
            else: #assume protocol == sftp
                __download_single_file(remote_loc,local_loc)
            remove_next_item_from_queue()
            save_queue_to_file()
            
            __close_sftp()

    except IndexError:
        #print("Download Queue Now Empty")
        pass
    except AssertionError:
        print("\nDownload Daemon exiting...")
def __restart_thread():
    global download_thread,downloads_stop_flag
    if download_thread == None or not download_thread.is_alive():
        downloads_stop_flag.clear()
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
    global host,port
    if not "download_host" in defaults:
        print("Download Info Not Given - running in buffer mode")
    host = defaults["download_host"]
    port = 22
    if ":" in host:
        host,port = host.split(":")

    global username,password
    username,password = defaults["download_credentials"].split(":")

    load_queue_from_file()
    __restart_thread()
def queue_file_for_download(torrent_id,remote_loc,local_loc):
    """
    This will add the file to a list of files that are to be downloaded.
    This runs as a seperate thread so that other operations can happen.
    Files queued in this manner will be added to a conf file so that when
    the program starts again, it will resume downloading.
    """
    add_item_to_queue([remote_loc,local_loc],"sftp:"+torrent_id)
    __restart_thread()
def queue_file_for_local_copy(torrent_id,source_loc,dest_loc):
    """
    This will add the file to a list of files that are to be moved.
    This runs as a seperate thread so that other operations can happen.
    Files queued in this manner will be added to a conf file so that when
    the program starts again, it will resume downloading.
    """
    add_item_to_queue([source_loc,dest_loc],"local-copy:"+torrent_id)
    __restart_thread()
def queue_remote_path_for_deletion(remote_loc):
    """
    This will have the download thread delete the remote location as the next
    task that it does. This does mean it will finish the current download before
    it erases the location, but it should also survive the program getting
    restarted and still be in queue when the it is started again.
    """
    if(remote_loc == ""):
        print("ERROR : Filepath to delete is empty")
        return
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
        global downloads_stop_flag
        downloads_stop_flag.set()
        #download_thread.join() #uncomment if you want downloads to finish before exiting
    save_queue_to_file()

def check_if_torrent_has_files_queued(torrent_id):
    """
    Returns True or False. This lets you know if there are any files in the queue
    so that you can check if it is safe to delete a torrent.
    """
    return check_if_tag_in_queue("sftp:"+torrent_id) or check_if_tag_in_queue("local-copy:"+torrent_id)






