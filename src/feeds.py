import feedparser
from variables import get_variable_value_cascaded,expand_string_variables,safe_parse_split

def check_for_new_links(feed):
    """Given the normal feed object, return a list of new feed entries. Ordered oldest to newest."""
    #read the feed
    feed_url = feed["feed_url"]
    try:
        feed_data = feedparser.parse(feed_url)
    except http.client.RemoteDisconnected:
        print("HTTP Error, service seems to be busy/down")
        return []

    #parse out entries in the feed for the information we want
    entries = []
    for entry in feed_data.entries:
        parsed_entry = {}
        parsed_entry["title"] = entry["title"]
        parsed_entry["link"] = entry["link"]
        parsed_entry["published"] = entry["published"]
        parsed_entry["feed_url"] = feed_url
        entries.append(parsed_entry)

    #check for new entries since the last known entry
    #chop off all entries starting at the last_seen_link
    if "last_seen_link" in feed:
        last_link = feed["last_seen_link"]
        idx = -1
        for cidx in range(len(entries)):
            if entries[cidx]["link"] == last_link:
                idx = cidx
                break
            #else is a new link
        entries = entries[:idx]

    return list(reversed(entries))

def check_if_feed_marked_for_deletion(defaults,group,feed):
    equaltiy_condition = None
    try:
        equaltiy_condition = get_variable_value_cascaded(defaults,group,feed,{},"remove_feed_if_equal",print=False)
    except:
        return False # no condition specified to delete things

    try:
        args = safe_parse_split(equality_condition," ")
        if len(args) != 2:
            return False # bad format for the equality condition
        args[0] = expand_string_variables(defaults,group,feed,{},args[0])
        args[1] = expand_string_variables(defaults,group,feed,{},args[1])
        if args[0] == args[1]:
            return True
    except Exception as e:
        print(e)
        pass # no specified condition to remove this feed
    return False # not ready to be removed
