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
        string.rjust(length,padding)
    elif function == "rpad" or function == "rightpad":
        length = 0
        padding= ' '
        if ',' in argument:
            length = int(argument.split(",")[0])
            padding = argument.split(",")[1]
        else:
            length = int(argument)
        string.ljust(length,padding)
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
    return step[0] , step[1].split(',')

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

available_processing_steps = {
    "add_torrent" : step_add_torrent,
    "increment_torrent_var" : step_increment_torrent_var,
    "increment_feed_var" : step_increment_feed_var,
    "increment_group_var" : step_increment_group_var,
    "increment_global_var" : step_increment_global_var,
    "post_processing_steps" : step_post_processing_steps,
    "processing_steps_variable" : step_processing_steps_variable,
    "set_label" : step_set_label,
    "wait_for_torrent_complete" : step_wait_for_torrent_complete
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

    ready_to_yield = False
    while not ready_to_yield:
        #string, [strings] =
        process_name,args = get_processing_step_data(defaults,group,feed,torrent)

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
