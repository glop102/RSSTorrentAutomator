import xmlrpc.client
import re
from time import sleep
from downloads import queue_file_for_download,check_if_torrent_has_files_queued,queue_remote_path_for_deletion,queue_file_for_local_copy
from variables import get_variable_value_cascaded,expand_string_variables,safe_parse_split
import os

#This is a global variable that holds our connection to rtorrent
global server 
server = None

def connect_to_server(defaults):
    #check if we are already connected
    global server
    if not server == None: return

    url = defaults["server_url"]
    credentials = defaults["credentials"]

    if credentials == None or credentials == "":
        pass #nothing special to do
    else: # we need to integrate the credentials into the url
        idx = 0 # assume no protocol specifier is in the URL
        if "://" in url:
            idx = url.index("://")+3 #well, the specifier is there, so we need to insert after it
        left = url[:idx]
        right = url[idx:]
        url = left+credentials+"@"+right

    server = xmlrpc.client.Server(url)

def __add_torrent_to_rtorrent(defaults,url):
    """Give a list of urls or magnet links and we will ask rtorrent to add and start it. We return the torrent hash that rtorrent uses"""
    connect_to_server(defaults)
    num_torrents = len(server.download_list())
    #server.load.normal("",url)
    server.load.start("",url)
    hashlist = server.download_list()
    while len(hashlist) == num_torrents:
        sleep(0.25)
        hashlist = server.download_list()
    return hashlist[-1]
def __check_if_torrent_complete(defaults,infohash):
    """Returns True or False"""
    connect_to_server(defaults)
    return True if server.d.complete(infohash) == 1 else False
def __set_torrent_label(defaults,infohash,label):
    connect_to_server(defaults)
    server.d.custom1.set(infohash,label)
def __get_torrent_name(defaults,infohash):
    connect_to_server(defaults)
    return server.d.name(infohash)
def __get_torrent_ratio(defaults,infohash):
    connect_to_server(defaults)
    return float( server.d.ratio(infohash) )
def __get_torrent_filecount(defaults,infohash):
    connect_to_server(defaults)
    return server.d.size_files(infohash)
def __get_torrent_files_abs_paths(defaults,infohash,filename_glob=""):
    # filename_glob - glob based filename filtering
    connect_to_server(defaults)
    paths = server.f.multicall(
        infohash,
        filename_glob,
        [ "f.frozen_path=" ]
    )
    return [path[0] for path in paths]
def __get_torrent_files_relative_paths(defaults,infohash,filename_glob=""):
    # filename_glob - glob based filename filtering
    connect_to_server(defaults)
    paths = server.f.multicall(
        infohash,
        filename_glob,
        [ "f.path=" ]
    )
    return [path[0] for path in paths]
def __delete_torrent_only(defaults,infohash):
    connect_to_server(defaults)
    server.d.delete_tied(infohash)
    server.d.erase(infohash)
def __is_torrent_multifile(defaults,infohash):
    connect_to_server(defaults)
    res = int(server.d.is_multi_file(infohash))
    if res == 1: return True
    return False
def __get_torrent_basepath(defaults,infohash):
    connect_to_server(defaults)
    return server.d.base_path(infohash)

def __filepaths_will_be_on_same_filesystem(p1,p2):
    #make sure it is absolute and sane for a starting point
    #we rely on implicitly running into the root disk at some point which does not happen if it is a relative path
    p1 = os.path.normpath(os.path.abspath(p1))
    p2 = os.path.normpath(os.path.abspath(p2))
    #find the largest segment of the path that already exists, which might end up being the root disk
    while not os.path.exists(p1):
        p1 = os.path.normpath( os.path.join(p1,"..") )
    while not os.path.exists(p2):
        p2 = os.path.normpath( os.path.join(p2,"..") )
    #both paths are guarenteed to exist now so we can get what FS it will be on
    if os.stat(p1).st_dev == os.stat(p2).st_dev:
        return True
    return False

#==========================================================================
#  Processing Functions
#==========================================================================
def __get_next_step_name(steps_orig):
    idx = -1
    try:
        idx = steps_orig.index('(')
    except:
        print("Error: Unable to find '(' in a processing varaible")
        print("Please let the author know, this is likely an internal error")
        exit(-1)
    name = steps_orig[:idx]
    steps_orig = steps_orig[idx+1:]
    return name,steps_orig
def __get_next_step_args(steps_orig):
    idx = 0
    paren_stack = 0
    skip_next = False
    for c in steps_orig:
        if skip_next:
            skip_next = False
        elif c == "(":
            paren_stack = paren_stack + 1
        elif c == ")":
            if paren_stack == 0:
                break
            else:
                paren_stack = paren_stack - 1
        elif c == "\\":
            skip_next = True
        idx = idx + 1

    if idx == len(steps_orig):
        print("Error: Unable to find a ')' in processing - likely an unmatched paren")
        exit(-1)

    args = steps_orig[:idx]
    steps_orig = steps_orig[idx+1:]
    return args,steps_orig.strip()
def get_processing_step_data(defaults,group,feed,torrent):
    var_name,cur_step_num = torrent["current_processing_step"].split()
    cur_step_num = int(cur_step_num)

    steps_orig = get_variable_value_cascaded(defaults,group,feed,torrent,var_name).strip()
    steps = [] #2d array of [ ["processing_name","args"] ]
    
    while len(steps_orig) > 0:
        step_name,steps_orig = __get_next_step_name(steps_orig)
        step_args,steps_orig = __get_next_step_args(steps_orig)
        steps.append([step_name,step_args])

    step = steps[cur_step_num]
    return step[0] , safe_parse_split(step[1],',')

def step_add_torrent(defaults,group,feed,torrent,args):
    if len(args) > 0 and not args[0] == '':
        print("Error: add_torrent does not take arguments")
        exit(-1)
    if "title" in torrent :
        print("Adding Torrent to Server : "+torrent["title"])
    infohash = __add_torrent_to_rtorrent(defaults,torrent["link"])
    torrent["infohash"] = infohash
    return False,True # ready_to_yield, do_next_step
def step_increment_torrent_var(defaults,group,feed,torrent,args):
    if len(args) == 0 or args[0] == "":
        print("Error: An argument must be given to increment_torrent_var")
        exit(-1)
    for var in args:
        if not var in torrent:
            print("Error: cannot find variable {} in current torrent".format(var))
            exit(-1)
        try:
            torrent[var] = str(int(torrent[var]) + 1)
        except:
            print("Error: variable {} does not seem to be a number".format(var))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_increment_feed_var(defaults,group,feed,torrent,args):
    if len(args) == 0 or args[0] == "":
        print("Error: An argument must be given to increment_feed_var")
        exit(-1)
    for var in args:
        if not var in feed:
            print("Error: cannot find variable {} in feed".format(var))
            exit(-1)
        try:
            feed[var] = str(int(feed[var]) + 1)
        except:
            print("Error: variable {} does not seem to be a number".format(var))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_increment_group_var(defaults,group,feed,torrent,args):
    if len(args) == 0 or args[0] == "":
        print("Error: An argument must be given to increment_group_var")
        exit(-1)
    for var in args:
        if not var in group:
            print("Error: cannot find variable {} in group {}".format(var,group["group_name"]))
            exit(-1)
        try:
            group[var] = str(int(group[var]) + 1)
        except:
            print("Error: variable {} does not seem to be a number".format(var))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_increment_global_var(defaults,group,feed,torrent,args):
    if len(args) == 0 or args[0] == "":
        print("Error: An argument must be given to increment_global_var")
        exit(-1)
    for var in args:
        if not var in defaults:
            print("Error: cannot find variable {} in global scope".format(var))
            exit(-1)
        try:
            defaults[var] = str(int(defaults[var]) + 1)
        except:
            print("Error: variable {} does not seem to be a number".format(var))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_addition_torrent_var(defaults,group,feed,torrent,args):
    if len(args) != 3 or "" in args:
        print("Error: 3 arguments must be given to addition_torrent_var : float,float,destinationName")
        exit(-1)
    left = args[0]
    right = args[1]
    dest = args[2]
    if "." in left or "." in right:
        try:
            torrent[dest] = str(float(left) + float(right))
        except:
            print("Error: The given arguments do not seem to be floats : {} , {}".format(left,right))
            exit(-1)
    else:
        try:
            torrent[dest] = str(int(left) + int(right))
        except:
            print("Error: The given arguments do not seem to be ints : {} , {}".format(left,right))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_addition_feed_var(defaults,group,feed,torrent,args):
    if len(args) != 3 or "" in args:
        print("Error: 3 arguments must be given to addition_feed_var : float,float,destinationName")
        exit(-1)
    left = args[0]
    right = args[1]
    dest = args[2]
    if "." in left or "." in right:
        try:
            feed[dest] = str(float(left) + float(right))
        except:
            print("Error: The given arguments do not seem to be floats : {} , {}".format(left,right))
            exit(-1)
    else:
        try:
            feed[dest] = str(int(left) + int(right))
        except:
            print("Error: The given arguments do not seem to be ints : {} , {}".format(left,right))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_addition_group_var(defaults,group,feed,torrent,args):
    if len(args) != 3 or "" in args:
        print("Error: 3 arguments must be given to addition_group_var : float,float,destinationName")
        exit(-1)
    left = args[0]
    right = args[1]
    dest = args[2]
    if "." in left or "." in right:
        try:
            group[dest] = str(float(left) + float(right))
        except:
            print("Error: The given arguments do not seem to be floats : {} , {}".format(left,right))
            exit(-1)
    else:
        try:
            group[dest] = str(int(left) + int(right))
        except:
            print("Error: The given arguments do not seem to be ints : {} , {}".format(left,right))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_addition_global_var(defaults,group,feed,torrent,args):
    if len(args) != 3 or "" in args:
        print("Error: 3 arguments must be given to addition_global_var : float,float,destinationName")
        exit(-1)
    left = args[0]
    right = args[1]
    dest = args[2]
    if "." in left or "." in right:
        try:
            defaults[dest] = str(float(left) + float(right))
        except:
            print("Error: The given arguments do not seem to be floats : {} , {}".format(left,right))
            exit(-1)
    else:
        try:
            defaults[dest] = str(int(left) + int(right))
        except:
            print("Error: The given arguments do not seem to be ints : {} , {}".format(left,right))
            exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_post_processing_steps(defaults,group,feed,torrent,args):
    torrent["current_processing_step"] = "post_processing_steps 0"
    #we are special because we changed the step so we do not want to increment it
    return False,False # ready_to_yield, do_next_step
def step_processing_steps_variable(defaults,group,feed,torrent,args):
    if len(args) == 0 or args[0] == "":
        print("Error: An argument must be given to processing_steps_variable")
        exit(-1)
    torrent["current_processing_step"] = args[0] + " 0"
    #we are special because we changed the step so we do not want to increment it
    return False,False # ready_to_yield, do_next_step
def step_wait_for_torrent_complete(defaults,group,feed,torrent,args):
    complete = __check_if_torrent_complete(defaults,torrent["infohash"])
    if complete:
        return False,True # ready_to_yield, do_next_step
    else:
        return True,False # ready_to_yield, do_next_step
def step_set_label(defaults,group,feed,torrent,args):
    if len(args) != 1 or args[0] == "":
        print("Error: set_label requires a string argument")
        exit(-1)
    __set_torrent_label(defaults,torrent["infohash"],args[0])
    return False,True # ready_to_yield, do_next_step
def step_wait_for_ratio(defaults,group,feed,torrent,args):
    if len(args) != 1 or args[0] == "":
        print("Error: wait_for_ratio requires a number")
        exit(-1)
    try:
        wanted = float(args[0])
        has = __get_torrent_ratio(defaults,torrent["infohash"])
        if wanted > has:
            return True,False # ready_to_yield, do_next_step
        else:
            return False,True # ready_to_yield, do_next_step
    except:
        print("Error: wait_for_ratio requires a number")
        exit(-1)
def step_download_files(defaults,group,feed,torrent,args):
    if len(args) != 1 or args[0] == "":
        print("Error: download_files requires a path to save to")
        exit(-1)
    if not "current_file_download_status" in torrent:
        remote_file_paths = __get_torrent_files_abs_paths(defaults,torrent["infohash"])
        local_base_dir = args[0]
        if len(remote_file_paths) == 1:
            #special case, we assume the given local path is the name the file we want to write locally
            queue_file_for_download(torrent["infohash"],remote_file_paths[0],local_base_dir)
        else:
            remote_file_paths_relative = __get_torrent_files_relative_paths(defaults,torrent["infohash"])
            for path_abs,path_rel in zip(remote_file_paths,remote_file_paths_relative):
                queue_file_for_download(
                    torrent["infohash"], path_abs,
                    local_base_dir+'/'+path_rel
                    )
        torrent["current_file_download_status"] = "queued_files_for_download"
        return True,False # ready_to_yield, do_next_step
    elif torrent["current_file_download_status"] == "queued_files_for_download":
        if check_if_torrent_has_files_queued(torrent["infohash"]):
            return True,False # ready_to_yield, do_next_step
        else:
            torrent["current_file_download_status"] = "files_downloaded"
            return False,True # ready_to_yield, do_next_step
    else:
        print("Error: Unknown torrent download state")
        exit(-1)
def step_download_files_into_folder(defaults,group,feed,torrent,args):
    if len(args) != 1 or args[0] == "":
        print("Error: download_files requires a path to save to")
        exit(-1)
    if not "current_file_download_status" in torrent:
        remote_file_paths = __get_torrent_files_abs_paths(defaults,torrent["infohash"])
        local_base_dir = args[0]
        remote_file_paths_relative = __get_torrent_files_relative_paths(defaults,torrent["infohash"])
        for path_abs,path_rel in zip(remote_file_paths,remote_file_paths_relative):
            queue_file_for_download(
                torrent["infohash"], path_abs,
                local_base_dir+'/'+path_rel
                )
        torrent["current_file_download_status"] = "queued_files_for_download"
        return True,False # ready_to_yield, do_next_step
    elif torrent["current_file_download_status"] == "queued_files_for_download":
        if check_if_torrent_has_files_queued(torrent["infohash"]):
            return True,False # ready_to_yield, do_next_step
        else:
            torrent["current_file_download_status"] = "files_downloaded"
            return False,True # ready_to_yield, do_next_step
    else:
        print("Error: Unknown torrent download state")
        exit(-1)
def step_stop_tracking_torrent(defaults,group,feed,torrent,args):
    torrent["current_processing_step"] = "ready_for_removal 0"
    return True,False # ready_to_yield, do_next_step
def step_delete_torrent_only(defaults,group,feed,torrent,args):
    __delete_torrent_only(defaults,torrent["infohash"])
    torrent["current_processing_step"] = "ready_for_removal 0"
    return True,False # ready_to_yield, do_next_step
def step_delete_torrent_and_files(defaults,group,feed,torrent,args):
    basepath = __get_torrent_basepath(defaults,torrent["infohash"])
    queue_remote_path_for_deletion(basepath)
    __delete_torrent_only(defaults,torrent["infohash"])
    torrent["current_processing_step"] = "ready_for_removal 0"
    return True,False # ready_to_yield, do_next_step
def step_retrieve_torrent_name(defaults,group,feed,torrent,args):
    name = __get_torrent_name(defaults,torrent["infohash"])
    torrent["torrent_name"] = name
    return False,True # ready_to_yield, do_next_step
def step_regex_parse(defaults,group,feed,torrent,args):
    if len(args)<3:
        print("3 Arguments required for regex parsing")
        exit(-1)
    if not args[0] in torrent:
        print("Cannot find variable '{}' in torrent to parse with regex".format(args[0]))
        exit(-1)
    if args[1] == "":
        print("An empty regex is not valid")
        exit(-1)
    if args[2] == "":
        print("You need to have a non-empty variable name for regex to store into")
        exit(-1)
    orig_val = get_variable_value_cascaded(defaults,group,feed,torrent,args[0])
    regex_string = args[1]
    search = re.search(regex_string,orig_val)
    if search == None:
        #found no match
        torrent[args[2]] = ""
        torrent["regex_matched"] = "false"
    else:
        #found a match
        torrent[args[2]] = search[0]
        torrent["regex_matched"] = "true"
    return False,True # ready_to_yield, do_next_step
def step_set_feed_var(defaults,group,feed,torrent,args):
    if len(args) < 2:
        print("Error: Two arguments must be given to set_feed_var (var_name,var_value)")
        exit(-1)
    if args[0] == "":
        print("Error: Var Name passed to set_feed_var is empty")
        exit(-1)

    var_name = args[0]
    var_value = args[1]
    feed[var_name] = var_value

    return False,True # ready_to_yield, do_next_step
def step_branch_if_vars_equal(defaults,group,feed,torrent,args):
    if not len(args) == 3:
        print("Error: Three arguments must be given to branch_if_vars_equal (var_name,var_name,processing_steps_varname)")
        exit(-1)
    for x in [0,1,2]:
        if args[x] == "":
            print("Error: Var Name {} passed to branch_if_vars_equal is empty".format(x+1))
            exit(-1)

    v1n = args[0]
    v2n = args[1]
    stepsName = args[2]

    try:
        v1v = get_variable_value_cascaded(defaults,group,feed,torrent,v1n)
        v1v = expand_string_variables(defaults,group,feed,torrent,v1v)

        v2v = get_variable_value_cascaded(defaults,group,feed,torrent,v2n)
        v2v = expand_string_variables(defaults,group,feed,torrent,v2v)
        if v1v == v2v:
            # special return becuase of auto-incrementing breaking the next steps
            return step_processing_steps_variable(defaults,group,feed,torrent,[stepsName])
    except:
        # print("branch had a missing conditional var so skipping")
        pass

    return False,True # ready_to_yield, do_next_step
def step_branch_if_values_equal(defaults,group,feed,torrent,args):
    if not len(args) == 3:
        print("Error: Three arguments must be given to branch_if_values_equal (value,value,processing_steps_varname)")
        exit(-1)
    for x in [0,1,2]:
        if args[x] == "":
            print("Error: Var Name {} passed to branch_if_values_equal is empty".format(x+1))
            exit(-1)

    v1v = args[0]
    v2v = args[1]
    stepsName = args[2]

    try:
        v1v = expand_string_variables(defaults,group,feed,torrent,v1v)

        v2v = expand_string_variables(defaults,group,feed,torrent,v2v)
        if v1v == v2v:
            # special return becuase of auto-incrementing breaking the next steps
            return step_processing_steps_variable(defaults,group,feed,torrent,[stepsName])
    except:
        pass

    return False,True # ready_to_yield, do_next_step
def step_get_file_info(defaults,group,feed,torrent,args):
    # absolute_filepath
    # absolute_folderpath
    # filename
    # basename
    # extension
    if not len(args) == 1:
        print("Error: need a path as an argument for get_file_info (%path%)")
        exit(-1)
    if os.path.exists(args[0]):
        torrent["absolute_filepath"] = os.path.abspath( os.path.realpath(args[0]) ) #https://stackoverflow.com/questions/37863476/why-would-one-use-both-os-path-abspath-and-os-path-realpath
        torrent["absolute_folderpath"],torrent["filename"] = os.path.split(torrent["absolute_filepath"])
        torrent["basename"],torrent["extension"] = os.path.splitext(torrent["filename"])
        #quick cleanup to remove the period on the front of file extensions
        if len(torrent["extension"]) > 0 and torrent["extension"][0] == '.':
            torrent["extension"] = torrent["extension"][1:]
    return False,True # ready_to_yield, do_next_step
def step_populate_next_file_info(defaults,group,feed,torrent,args):
    #gets the info of the first file it comes accros and puts it into the variables of the torrent
    #it sets foundfile to "true" if there was something to find and "false" if there was nothing to find
    if not len(args) == 1:
        print("Error: need a path as an argument for populate_next_file_info (%path%)")
        exit(-1)
    for root,dirs,files in os.walk(args[0]):
        if len(files) > 0:
            torrent["foundfile"] = "true"
            return step_get_file_info(defaults,group,feed,torrent,[os.path.join(root,files[0])] )

    # for loop found no file so there is nothing left - lets do cleanup
    torrent["foundfile"] = "false"
    del torrent["absolute_filepath"]
    del torrent["absolute_folderpath"]
    del torrent["filename"]
    del torrent["basename"]
    del torrent["extension"]
    return False,True # ready_to_yield, do_next_step
def step_rename_file(defaults,group,feed,torrent,args):
    #renames a given file to the new name
    #Warning : this is not intended to move files between different file systems
    if not len(args) == 2:
        print("Error: need to pass two arguments to rename_file (%oldName% , %newName%)")
        print("    Note: not intended to move file accross different file systems")
        exit(-1)
    old = os.path.abspath( os.path.realpath( args[0] ) )
    new = os.path.abspath( os.path.realpath( args[1] ) )
    if not os.path.exists(old):
        print("Error: Unable to find the source file for rename_file")
        print("    "+old)
        exit(-1)
    if not __filepaths_will_be_on_same_filesystem(old,new):
        print("Error: attempting to move a file between different filesystems with rename_file. Perhaps you mean to use move_file()?")
        print("    oldName: "+old)
        print("    newName: "+new)
        exit(-1)
    try:
        os.renames(old,new)
    except Exception as e:
        print("Exception caught when attempting to rename a file in rename_file()")
        print("    oldName: "+old)
        print("    newName: "+new)
        print(e)
        exit(-1)
    return False,True # ready_to_yield, do_next_step
def step_move_file(defaults,group,feed,torrent,args):
    #Note: if the source is a file, the destination will be assumed to be a filename if there is not a folder already there by that name
    #if the source is a directory, the destination will always be assumed to be a folder
    #Note: the arg parsing removes the trailing slash if the person wanted to specify a destination directory
    if not len(args) == 2:
        print("Error: need to pass two arguments to move_file (%oldName% , %newName%)")
        exit(-1)
    old = os.path.abspath( os.path.realpath( args[0] ) )
    new = os.path.abspath( os.path.realpath( args[1] ) )
    if not os.path.exists(old):
        print("Error: Unable to find the source file for move_file")
        print("    "+old)
        exit(-1)
    if __filepaths_will_be_on_same_filesystem(old,new):
        try:
            if os.path.exists(new) and os.path.isdir(new):
                #handle if we want to shove it inside a folder but didn't care to change the filename
                new = os.path.join(new, s.path.basename(old) )
            os.renames(old,new)
        except Exception as e:
            print("Exception caught when attempting to rename a file in move_file() (same filesystem assumed)")
            print("    oldName: "+old)
            print("    newName: "+new)
            print(e)
            exit(-1)
        torrent["current_file_move_status"] = "files_moved"
    else:
        print("Not implemented yet - need to add to 'download manager' to do the copy operation")
        exit(-1)

        if not "current_file_move_status" in torrent or torrent["current_file_move_status"] == "files_moved":
            #The files to be moved across to a different file system are not already queued, so we need to add them
            #to the second thread for the copy+delete operation.
            #We can either have been handed a single file or a whole directory that needs to be moved
            source_files = []
            dest_files = []

            if os.path.isfile(old):
                source_files = [old]
                if os.path.exists(new) and os.path.isdir(new):
                    dest_files = [os.path.join( new, os.path.basename(old) )]
                else:
                    dest_files = [new] #overwrite the file if required
            elif os.path.isdir(old):
                #we need to list all the files in the source folder and then preserve their
                #name and relative location during the copy
                source_files = [ os.path.abspath( os.path.realpath( os.path.join(root,f) ) ) for root,dirs,files in os.walk(old) for f in files ]
                relative_paths = [ path.replace(old,"") for path in source_files ]
                dest_files = [ os.path.join(new,path) for path in relative_paths ]
            else:
                print("Error: passed source is neither a file nor a directory")
                print("    "+old)
                exit(-1)

            for source_file,dest_file in zip(source_files,dest_files):
                queue_file_for_local_copy(
                    torrent["infohash"],
                    source_file,
                    dest_file
                    )
            torrent["current_file_move_status"] = "queued_files_for_move"
            return True,False # ready_to_yield, do_next_step
        elif torrent["current_file_move_status"] == "queued_files_for_move":
            if check_if_torrent_has_files_queued(torrent["infohash"]):
                return True,False # ready_to_yield, do_next_step
            else:
                #it is not a move if the source files stick around - delete them
                if os.path.isdir(old):
                    shutil.rmtree(old)
                elif os.path.isfile(old):
                    os.remove(old)
                torrent["current_file_move_status"] = "files_moved"
                return False,True # ready_to_yield, do_next_step
        else:
            print("Error: Unknown state for current_file_move_status in move_file()")
            exit(-1)

    return False,True # ready_to_yield, do_next_step


available_processing_steps = {
    "add_torrent" : step_add_torrent,
    "increment_torrent_var" : step_increment_torrent_var,
    "increment_feed_var" : step_increment_feed_var,
    "increment_group_var" : step_increment_group_var,
    "increment_global_var" : step_increment_global_var,
    "addition_torrent_var" : step_addition_torrent_var,
    "addition_feed_var" : step_addition_feed_var,
    "addition_group_var" : step_addition_group_var,
    "addition_global_var" : step_addition_global_var,
    "post_processing_steps" : step_post_processing_steps,
    "processing_steps_variable" : step_processing_steps_variable,
    "set_label" : step_set_label,
    "wait_for_torrent_complete" : step_wait_for_torrent_complete,
    "wait_for_ratio" : step_wait_for_ratio,
    "download_files" : step_download_files,
    "download_files_into_folder" : step_download_files_into_folder,
    "stop_tracking_torrent" : step_stop_tracking_torrent,
    "delete_torrent_only" : step_delete_torrent_only,
    "delete_torrent_and_files" : step_delete_torrent_and_files,
    "retrieve_torrent_name" : step_retrieve_torrent_name,
    "regex_parse" : step_regex_parse,
    "set_feed_var" : step_set_feed_var,
    "branch_if_vars_equal" : step_branch_if_vars_equal,
    "branch_if_values_equal" : step_branch_if_values_equal,
    "get_file_info" : step_get_file_info,
    "populate_next_file_info" : step_populate_next_file_info,
    "rename_file" : step_rename_file,
    "move_file" : step_move_file
}

#==========================================================================
#  Standard API Functions
#==========================================================================

def expand_new_torrent_object(defaults,group,feed,torrent):
    """Expands the torrent object in place so that it includes all the enviroment variables from when it was first processed"""
    #Lets start with making sure the most basic thing we need is actually there
    torrent["processing_steps"] = get_variable_value_cascaded(defaults,group,feed,torrent,"processing_steps")
    if not "processing_steps" in torrent:
        print("Error: processing_steps not defined for torrent being added. This is required so that we know what we are doing with this torrent.")
        exit(-1)
    if "title" in torrent:
        print("Expanding new torrent : "+torrent["title"])

    #we do not check if it already exists because we assume this is a new torrent
    torrent["current_processing_step"] = "processing_steps 0"

def process_torrent(defaults,group,feed,torrent):
    if torrent["current_processing_step"] == "ready_for_removal 0":
        print("Error (Non-Fatal): torrent is in state ready_for_removal")
        print("A torrent should not be in this state and get processed")
        print("Contact the developer to fix this error")
        return

    ready_to_yield = False
    while not ready_to_yield:
        #string, [strings] =
        process_name,args = get_processing_step_data(defaults,group,feed,torrent)
        args = [expand_string_variables(defaults,group,feed,torrent,arg) for arg in args]

        if not process_name in available_processing_steps:
            print("Error: Unable to find processing step "+process_name)
            exit(-1)
        ready_to_yield,do_next_step = available_processing_steps[process_name](defaults,group,feed,torrent,args)

        if do_next_step:
            name,num= torrent["current_processing_step"].strip().split()
            num = int(num) + 1
            torrent["current_processing_step"] = name+' '+str(num)

#==========================================================================
#  Debug Functions Below
#==========================================================================

def debug_print_torrent_name_from_infohash(infohash):
    print(server.d.name(infohash))
def debug_print_torrent_data(torrent):
    print("=====Torrent")
    for key in torrent:
        print("{} : {}".format(key,torrent[key]) )
def debug_print_torrents(torrents):
    for tor in torrents:
        debug_print_torrent_data(tor)
        print()
