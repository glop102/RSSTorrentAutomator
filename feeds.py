import feedparser

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
