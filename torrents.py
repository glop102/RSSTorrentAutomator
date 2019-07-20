import xmlrpc.client
from time import sleep
from downloads import queue_file_for_download,check_if_torrent_has_files_queued,queue_remote_path_for_deletion
from variables import get_variable_value_cascaded,expand_string_variables,safe_parse_split

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
    server.load.normal("",url)
    #server.load.start("",url)
    sleep(0.25)
    return server.download_list()[-1]
def __check_if_torrent_complete(defaults,infohash):
    """Returns True or False"""
    connect_to_server(defaults)
    return True if server.d.complete(infohash) == 1 else False
def __set_torrent_label(defaults,infohash,label):
    connect_to_server(defaults)
    server.d.custom1.set(infohash,label)
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


#==========================================================================
#  Torrent Expansion Functions
#==========================================================================

def __expand_processing_steps(defaults,group,feed,torrent,var_name):
    steps = safe_parse_split(torrent[var_name]," ")
    need_expansion = []
    for step in steps:
        if "processing_steps_variable" in step:
            #grab the variable name from the function call
            lidx = step.index("(")
            ridx = step.rindex(")")
            new_var = step[lidx+1:ridx]
            new_steps = get_variable_value_cascaded(defaults,group,feed,torrent,new_var)

            #skip any steps that we have already copied
            if new_var in torrent:
                continue

            torrent[new_var] = new_steps
            need_expansion.append(new_var)

    for proc in need_expansion:
        __expand_processing_steps(defaults,group,feed,torrent,proc)
def expand_processing_steps(defaults,group,feed,torrent):
    #Lets expand the default processing steps
    __expand_processing_steps(defaults,group,feed,torrent,"processing_steps")

    steps = safe_parse_split(torrent["processing_steps"]," ")
    if "post_processing_steps()" in steps:
        torrent["post_processing_steps"] = get_variable_value_cascaded(defaults,group,feed,torrent,"post_processing_steps")
        #Lets expand this extra case of processing steps
        __expand_processing_steps(defaults,group,feed,torrent,"post_processing_steps")

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
            continue
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


available_processing_steps = {
    "add_torrent" : step_add_torrent,
    "increment_torrent_var" : step_increment_torrent_var,
    "increment_feed_var" : step_increment_feed_var,
    "increment_group_var" : step_increment_group_var,
    "increment_global_var" : step_increment_global_var,
    "post_processing_steps" : step_post_processing_steps,
    "processing_steps_variable" : step_processing_steps_variable,
    "set_label" : step_set_label,
    "wait_for_torrent_complete" : step_wait_for_torrent_complete,
    "wait_for_ratio" : step_wait_for_ratio,
    "download_files" : step_download_files,
    "download_files_into_folder" : step_download_files_into_folder,
    "stop_tracking_torrent" : step_stop_tracking_torrent,
    "delete_torrent_only" : step_delete_torrent_only,
    "delete_torrent_and_files" : step_delete_torrent_and_files
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

    #parse through processing_steps and add all sub_process variables
    expand_processing_steps(defaults,group,feed,torrent)

    #parse through all variables and do a string replace
    #do NOT save the result of the parsing back to the variable, we are only parsing to know what variables we need to copy from the parent sections. We want to allow later changes to the string, such as completion time or whatever
    new_keys = True
    keys_checked = []
    while new_keys:
        try:
            new_keys = False
            for key in torrent.keys():
                if key in keys_checked: continue
                expand_string_variables(defaults,group,feed,torrent,torrent[key])
                keys_checked.append(key)
        except:
            new_keys = True

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
