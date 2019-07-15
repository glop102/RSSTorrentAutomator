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
    sleep(0.25)
    return server.download_list()[-1]
    #return server.load.start("",url)

#==========================================================================
#  Debug Functions Below
#==========================================================================

def print_torrent_name_from_infohash(infohash):
    print(server.d.name(infohash))
