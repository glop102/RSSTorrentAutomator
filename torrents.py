import xmlrpc.client
from time import sleep

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

    print(url)
    server = xmlrpc.client.Server(url)

def add_torrent_to_rtorrent(defaults,url):
    """Give a list of urls or magnet links and we will ask rtorrent to add and start it. We return the torrent hash that rtorrent uses"""
    connect_to_server(defaults)
    server.load.normal("",url)
    #server.load.start("",url)
    sleep(0.25)
    return server.download_list()[-1]

#==========================================================================
#  Torrent Expansion Functions
#==========================================================================
def __modify_string_value(string,modifier):
    if modifier == "":
        return string

    modifier = modifier.strip()
    idx = modifier.index("(")
    function = modifier[:idx]
    argument = modifier[idx+1:-1] #skips the last paren
    if function == "lpad" or function == "leftpad":
        length = 0
        padding= ' '
        if ',' in argument:
            length = int(argument.split(",")[0])
            padding = argument.split(",")[1]
        else:
            length = int(argument)
        while len(string) < length:
            string = padding+string
    else:
        print("Error: unknown variable modifier '"+function+"'")
        exit(-1)
    return string
def __expand_single_string_variable(defaults,group,feed,torrent,string):
    """Assumption is that we are given EXACTLY 'variable' - percent signs already stripped """
    if string == "": #
        return "%" #we need to allow percent signs after all

    #modifiers on the variables are split with ":"
    sections = string.split(":")
    #first item is the name of the variable to expand
    name = sections.pop(0)

    #get the initial value that we will modify and then return
    val=""
    if name in torrent:
        val = torrent[name]
    else:
        val = get_variable_value_cascaded(defaults,group,feed,torrent,name)
        torrent[name] = val

    for mod in sections:
        val = __modify_string_value(val,mod)
    return val
def expand_string_variables(defaults,group,feed,torrent,string):
    """
    Recursive function that replaces %variables% with their values
    Uses the most specific group to get the value and then saves it to the torrent object
    """
    #Special knowledge '%abc%'.split('%') --> ['','abc',''] so every odd index is a variable
    sections = string.split("%")

    #the way it splits, we know that we will always have an odd number of indicies
    if len(sections) %2 == 0:
        print("Error: unmatched percent sign in string")
        print("    "+string)
        exit(-1)
    if len(sections) == 1:
        return string # no replacements needed

    final_string = ""
    for idx in range(len(sections)):
        val = sections[idx]
        if idx %2 == 1:
            #is a variable so we must expand the value
            val = __expand_single_string_variable(defaults,group,feed,torrent,val)
            #and we must expand any variables that it references
            val = expand_string_variables(defaults,group,feed,torrent,val)
        #else is not a variable so nothing to expand
        final_string = final_string + val
    return final_string

def get_variable_value_cascaded(defaults,group,feed,torrent,var_name):
    """Trys to get the variable value from the most specific group possible"""
    if var_name in torrent:
        return torrent[var_name]
    elif var_name in feed:
        return feed[var_name]
    elif var_name in group:
        return group[var_name]
    elif var_name in defaults:
        return defaults[var_name]
    else:
        print("Error: variable '{}' is not defined".format(var_name))
        print("Searched\n\tFeed : {}\n\tGroup {}\n\tdefaults".format(feed["feed_url"],group["group_name"]))
        exit(-1)

def __expand_processing_steps(defaults,group,feed,torrent,var_name):
    steps = torrent[var_name].split()
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
            pass
        pass

    for proc in need_expansion:
        __expand_processing_steps(defaults,group,feed,torrent,proc)
def expand_processing_steps(defaults,group,feed,torrent):
    #Lets expand the default processing steps
    __expand_processing_steps(defaults,group,feed,torrent,"processing_steps")

    steps = torrent["processing_steps"].split()
    if "post_processing_steps()" in steps:
        torrent["post_processing_steps"] = get_variable_value_cascaded(defaults,group,feed,torrent,"post_processing_steps")
        #Lets expand this extra case of processing steps
        __expand_processing_steps(defaults,group,feed,torrent,"post_processing_steps")
        pass


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
