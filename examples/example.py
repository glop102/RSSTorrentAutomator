#!/usr/bin/env python3
# Import the XMLRPC library
# Note: It used to be called xmlrpclib
import xmlrpc.client

# Create an object to represent our server. Use the login information in the XMLRPC Login Details section here.
server_url = "https://giotto.whatbox.ca:443/xmlrpc";
server = xmlrpc.client.Server(server_url);

print( server.system.getCapabilities() )
exit()

# Get torrents in the main view
#mainview = server.download_list("", "main")
mainview = server.download_list()
#mainview = server.download_list("","completed")

print(mainview)
exit()

# For each torrent in the main view
for torrent in mainview:

    # Print the name of torrent
    print(server.d.get_name(torrent))
    # Print the directory of torrent
    print(server.d.get_directory(torrent))
