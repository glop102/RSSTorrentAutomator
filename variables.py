def mod_lpad(args,string):
    length = 0
    padding= ' '
    if len(args)>=2:
        length = int(args[0])
        padding= args[1]
    elif len(args) == 1:
        length = int(args[0])
    else:
        print("Error: string variable modification leftpad needs 1+ parameters")
        exit(-1)
    return string.rjust(length,padding)
def mod_rpad(args,string):
    length = 0
    padding= ' '
    if len(args)>=2:
        length = int(args[0])
        padding= args[1]
    elif len(args) == 1:
        length = int(args[0])
    else:
        print("Error: string variable modification rightpad needs 1+ parameters")
        exit(-1)
    return string.ljust(length,padding)
def mod_replace(args,string):
    if len(args) % 2 != 0:
        print("Error: string variable modification replace() needs an even number of parameters (ie 2 or 4 or 10)")
        exit(-1)
    #lets get the arguments into a sane view by making it a bunch of size 2 arrays of match+replace strings
    replacePairs = zip(args[0::2],args[1::2])
    for pair in replacePairs:
        string = string.replace(pair[0],pair[1])
    return string
def mod_sanitizeFilename(args,string):
    #we ignore the args because we have no settings for this at the moment
    #lets just use the mod_replace with a hard coded replace string
    return mod_replace(
            ["/",":",  "|",":",  "\"",""],
            string )

string_modifications = {
    "lpad" : mod_lpad,
    "leftpad" : mod_lpad,
    "rpad" : mod_rpad,
    "rightpad" : mod_rpad,
    "replace" : mod_replace,
    "sanitizeFilename" : mod_sanitizeFilename
}

def safe_parse_split(arguments,delim):
    output = [""]
    idx=0
    escape_whitelist = ["\\",",","%"]
    while idx < len(arguments):
        c = arguments[idx]
        if c == "\\" and arguments[idx+1] in escape_whitelist:
            idx = idx+1
            output[-1] = output[-1]+arguments[idx]
        elif c == delim:
            output.append("")
        else:
            output[-1] = output[-1]+arguments[idx]
        idx = idx+1
    return output

#=========================================================================================
#  General String Varaible Expansion
#=========================================================================================

def __modify_string_value(string,modifier):
    if modifier == "":
        return string

    modifier = modifier.strip()
    idx = modifier.index("(")
    function = modifier[:idx]
    arguments = modifier[idx+1:-1] #skips the last paren
    arguments = safe_parse_split(arguments,",")
    if function in string_modifications:
        string = string_modifications[function](arguments,string)
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
    val = get_variable_value_cascaded(defaults,group,feed,torrent,name)

    for mod in sections:
        val = __modify_string_value(val,mod)
    return val
def expand_string_variables(defaults,group,feed,torrent,string):
    """
    Recursive function that replaces %variables% with their values
    Uses the most specific group to get the value and then saves it to the torrent object
    """
    #Special knowledge '%abc%'.split('%') --> ['','abc',''] so every odd index is a variable
    sections = safe_parse_split(string,"%")

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

def get_variable_value_cascaded(defaults,group,feed,torrent,var_name,printSearchOnFailure=True):
    """
    Trys to get the variable value from the most specific group possible.
    The Last defaulted parameter is set to preserve the previous behavior of printing on failure.
    """
    if var_name in torrent:
        return torrent[var_name]
    elif var_name in feed:
        return feed[var_name]
    elif var_name in group:
        return group[var_name]
    elif var_name in defaults:
        return defaults[var_name]
    else:
        if printSearchOnFailure:
            print("Error: variable '{}' is not defined".format(var_name))
            print("Searched\n\tFeed : {}\n\tGroup {}\n\tdefaults".format(feed["feed_url"],group["group_name"]))
        raise KeyError("Variable name not found : "+var_name)
