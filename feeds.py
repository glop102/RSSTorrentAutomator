import feedparser
from variables import get_variable_value_cascaded,expand_string_variables,safe_parse_split

def check_for_new_links(feed):
    """Given the normal feed object, return a list of new feed entries. Ordered oldest to newest."""
    #read the feed
    feed_url = feed["feed_url"]
    feed_data = feedparser.parse(feed_url)

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
    try:
        condition = feed["remove_feed_if_equal"]
        args = safe_parse_split(condition," ")
        args[0] = expand_string_variables(defaults,group,feed,{},args[0])
        args[1] = expand_string_variables(defaults,group,feed,{},args[1])
        if args[0] == args[1]:
            return True
    except:
        pass # no specified condition to remove this feed
    return False # not ready to be removed
