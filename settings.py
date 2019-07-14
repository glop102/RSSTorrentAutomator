"""
Use the function parse_settings_file(sett)
It takes a single already open file object
It returns 3 objects - default settings, group settings, feed settings
"""

import netrc

def group_vars_sanity_check(section_vars,groups):
    if not "group_name" in section_vars:
        print("Error: Group #{} does not have group_name specified".format(len(groups)) )
        exit(-1)
    name = section_vars["group_name"]
    #it does not make sense to have 2 groups of the same name
    #nor to specify the values of a group in two places
    if name in groups:
        print("Error: Group name {} was already defined".format(name))
        exit(-1)

def feed_vars_sanity_check(section_vars,feeds):
    if not "feed_url" in section_vars:
        print("Error: feed #{} does not have feed_url specified".format(len(feeds)) )
        exit(-1)
    name = section_vars["feed_url"]
    #it does not make sense to have 2 groups of the same name
    #nor to specify the values of a group in two places
    if name in feeds:
        print("Error: Feed URL {} was already defined".format(name))
        exit(-1)

def parse_section(section_body):
    body = section_body #Just and easier name to type
    var_dict = {}
    for line in body:
        #variable names are before a colon, values are after
        idx = line.find(":")
        if idx == -1:
            print(line)  # Tell them that we don't understand
            print("Error: line is malformed - missing a colon")
            exit(-1)
        var_name = line[:idx].strip()
        var_value = line[idx+1:].strip()
        if var_name in var_dict:
            print("Error: Attempting to redefine a variable in the same section")
            print("var_name  : {}".format(var_name) )
            print("orig_value: {}".format(var_dict[var_name]) )
            print("new_value : {}".format(var_value) )
            exit(-1)
        var_dict[var_name] = var_value
    return var_dict

def parse_settings_file(sett):
    """sett - input - an open file object"""

    sections = [{"section_name":"","section_body":[]}]

    for line in sett:
        #first check if the line is a section header
        if line[:5] == "=====":
            sections.append({
                "section_name":line[5:].strip(),
                "section_body":[]
                })
            continue

        #otherwise is part of the body of the current section
        line=line.strip()
        if len(line) == 0 : continue  #ignore blank lines
        if line[0] == "#" : continue  #ignore comments

        #The line has been cleaned so is ready to be added
        sections[-1]["section_body"].append(line)

    #The sections have now been seperated by detecting the "=====" at the start of lines
    #The lines inbetween these section markers have bee wrapped together into an array
    #The name after the "=====" has been grabbed and associated with it's own body of lines

    defaults = {}
    groups = {}
    feeds = {}

    for section in sections:
        section_vars = parse_section(section["section_body"])
        name = section["section_name"].lower()

        if name in ["","global","default","defaults"]:
            #defaults is special - we mix the defaults together without any errors
            for key in section_vars:
                if key in defaults:
                    print("Warning: Changing a global variable value that was already defined")
                    print("var_name  : {}".format(key))
                defaults[key] = section_vars[key]
        elif name == "group":
            group_vars_sanity_check(section_vars,groups)
            name = section_vars["group_name"]
            groups[name] = section_vars
        elif name == "rssfeed":
            feed_vars_sanity_check(section_vars,feeds)
            name = section_vars["feed_url"]
            feeds[name] = section_vars
        else:
            print("Error: unknown section type {}".format(name))

    return defaults,groups,feeds

#=================================================================
#  Post Parsing Functions
#=================================================================

def parse_hostname_from_url(url):
    #remove the left protocol specifier if it is there
    if "://" in url:
        idx = url.index("://")
        url = url[idx+3:]
    #remove the port number on the right if it is there
    if ":" in url:
        idx = url.index(":")
        url = url[:idx]
    #remove any subdirectory in the URL
    if "/" in url:
        idx = url.index("/")
        url = url[:idx]

    return url

def parse_login_credentials_netrc(server_url):
    host = parse_hostname_from_url(server_url)
    net = netrc.netrc()
    creds = net.authenticators(host)
    if creds is None:
        print("Error: unable to find '{}' machine in the netrc file".format(host))
        exit(-1)
    #creds tuple in format of (login, account, password)
    return creds[0]+":"+creds[2]

def settings_final_sanity_check(defaults,groups,feeds):
    error_found = False
    if not "server_url" in defaults:
        print("Error: server_url is not specified")
        error_found=True

    if not "credentials_type" in defaults:
        error_found=True
        print("Error: credentials_type is not specified")
    elif defaults['credentials_type'] == 'plain' and not 'credentials' in defaults:
        error_found=True
        print("Error: credentials is not specified when credentials_type is plain")
    elif defaults['credentials_type'] == 'netrc':
        defaults['credentials'] = parse_login_credentials_netrc(defaults['server_url'])
    elif defaults['credentials_type'] == 'none':
        #Either there really is no credential checking, or they put it in the URL
        pass

    if error_found == True:
        exit(-1)

#=================================================================
#  Debug Functions
#=================================================================

def debug_print_settings_structs(defaults,groups,feeds):
    for key in defaults:
        print("{} : {}".format(key,defaults[key]) )
    for group_name in groups:
        print("=====Group")
        group = groups[group_name]
        for key in group:
            print("    {} : {}".format(key,group[key]) )
    for feed_url in feeds:
        print("=====RSSFeed")
        feed = feeds[feed_url]
        for key in feed:
            print("    {} : {}".format(key,feed[key]) )









