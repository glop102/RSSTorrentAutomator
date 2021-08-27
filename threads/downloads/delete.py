import paramiko

taskType = "remote deletion"

def validate(hosts,item):
    if item["host"] not in hosts:
        return "Remote Delete Host \"{}\" is not known.".format(item["host"])
    
    #remoteLocation
    if "remoteLocation" not in item:
        return "Does not have a remote location; aka what am I deleting?"
    if type(item["remoteLocation"]) != str or len(item["remoteLocation"]) == 0:
        return "Remote location does not look valid : \"{}\"".format(item["remoteLocation"])
    
    #no problems found
    return None
def process(hosts,item):
    print(hosts)
    print(item)