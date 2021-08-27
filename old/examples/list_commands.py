#!/usr/bin/env python3
# Import the XMLRPC library
# Note: It used to be called xmlrpclib
import xmlrpc.client
import shutil
term_width = shutil.get_terminal_size((80, 20))[0]

# Create an object to represent our server. Use the login information in the XMLRPC Login Details section here.
server_url = "https://giotto.whatbox.ca:443/xmlrpc";
server = xmlrpc.client.Server(server_url);

commands = server.system.listMethods()
commands.sort()



sigs_str = [ { "methodName":"system.methodSignature", "params":[com] } for com in commands ]
sigs = server.system.multicall( sigs_str )
#sigs = [s[0] for s in sigs]

help_str = [ { "methodName":"system.methodHelp", "params":[com] } for com in commands ]
helps = server.system.multicall( help_str )
helps = [h[0] if not h[0] == "No help is available for this method." else "" for h in helps]

longest_com = 0
for com in commands:
    if len(com) > longest_com:
        longest_com = len(com)
longest_sig = 0
for sig in sigs:
    if len(str(sig)) > longest_sig:
        longest_sig = len(str(sig))

for x in range(len(commands)):
    out_str = ("{0:<"+str(longest_com)+"} - {1:<"+str(longest_sig)+"} - {2}") . format(commands[x],str(sigs[x]),helps[x])
    while len(out_str)>4:
        print(out_str[:term_width])
        out_str="    "+out_str[term_width:]
