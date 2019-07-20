#!/usr/bin/env python3

"""
Instructions for myself

pull credentials from netrc file
 - remove current credentials before commiting to git the first time
d.custom1(torrent_hash) is the label assigned in the ruTorrent webpage

Flow - Adding New Torrents
read RSS URLs from a file, and check for updates
 - write out checkpoint info for the RSS feed back into this file or some other file
add the torrent urls to rTorrent and get their hash
 - set their label (use global setting, unless overriden for this feed)
Update the current_torrents file
 - information needed for the associated torrent
    - essentally a copy of the rss feed settings since we lose which rss feed it came from originally
 - torrent hash used to control torrent
 - torrent state (eg rss_init_step, downloading_remote, downloaded_remote, downloading_local, downloaded_local, waiting_for_ratio, deleted)

Flow - Downloading
get the show name and destination folder from the tracked torents file
 - info needed for torrent is added when the torrent is added in the previous flow
 - name will have %val% encoding allowed for dynamic naming
if state == downloaded_remote
  if num_files = 1 - download and name file
  else download files into folder of name
"""

from settings import parse_settings_file, settings_final_sanity_check, save_settings_to_file
from settings import parse_torrents_status_file, save_torrents_to_file
from feeds import check_for_new_links
from torrents import expand_new_torrent_object,process_torrent
from downloads import setup_downloads_thread,stop_downloads_thread
from time import sleep

from settings import debug_print_settings_structs
from torrents import debug_print_torrent_name_from_infohash, debug_print_torrents

def parse_configurations():
    defaults = {} #just a list of vars:values
    groups = {}   #2D dictionary with group_name as the key to get the group
    feeds = {}    #2D dictionary with the feed_url as the key to get the feed
    try:
        #start with parsing our settings that we need
        sett = open("rss_feed.conf","r")
        defaults,groups,feeds = parse_settings_file(sett)
        sett.close()
        #After all config files are parsed, we need to do sanity checking
        settings_final_sanity_check(defaults,groups,feeds)
    except:
        print("Error: unable to open rss_feed.conf")
        exit(-1)

    torrents = [] #an array of dictionaries
    try:
        sett = open("current_torrents.conf","r")
        torrents = parse_torrents_status_file(sett)
        sett.close()
    except:
        print("Unable to open current_torrents.conf - likely no torrents being watched right now")

    return defaults,groups,feeds,torrents

def update_feeds(defaults,groups,feeds,torrents):
    for feed_url in feeds:
        feed = feeds[feed_url]
        links = check_for_new_links(feed)
        if len(links) == 0 : continue

        #Update the last entry information so we only grab newer entries
        feed["last_seen_link"] = links[-1]["link"]
        feed["last_seen_link_date"] = links[-1]["published"]
        if len(links) > 0:
            print("\nFound {} new links for {}".format(len(links),feed_url) )

        #Add the new links onto the pile for us to process
        torrents.extend(links)

def update_torrents(defaults,groups,feeds,torrents):
    #Tech Note - Torrent expansion must happen one at a time after some processing has occured to allow the increment_*() to happen before the next torrent is processed
    removal_list = []
    for torrent in torrents:
        group={"group_name":"DummyGroup"}
        feed=feeds[ torrent["feed_url"] ]
        if "group_name" in feed:
            group = groups[feed["group_name"]]

        #Lets check if this torrent is new, and expand variables from the parrent sections
        if not "current_processing_step" in torrent:
            expand_new_torrent_object(defaults,group,feed,torrent)

        #Now lets run the processing steps on the torrent
        process_torrent(defaults,group,feed,torrent)
        if torrent["current_processing_step"] == "ready_for_removal 0":
            removal_list.append(torrents.index(torrent))

    # reversed so we delete items from the end to front to not mess up indices
    removal_list.reverse()
    for idx in removal_list:
        del torrents[idx]


def save_configurations(defaults,groups,feeds,torrents):
    sett = open("rss_feed.conf","w")
    save_settings_to_file(sett,defaults,groups,feeds)
    sett.close()

    sett = open("current_torrents.conf","w")
    save_torrents_to_file(sett,torrents)
    sett.close()

def main_loop_sleep(defaults):
    delay_time = 30*60 #30 minutes default period
    try:
        delay_time = int(defaults["feed_check_period"])
    except: pass
    sleep(delay_time)

def main():
    try:
        defaults,groups,feeds,torrents = parse_configurations()

        #lets get the file downloads going
        setup_downloads_thread(defaults)

        while True:
            #Now we have sane settings, so lets update our RSS feeds
            #update_feeds(defaults,groups,feeds,torrents)

            #Now that we have checked all our feeds, lets tend to our torrents
            #This includes starting the newly added torrents from the feeds
            update_torrents(defaults,groups,feeds,torrents)

            # Since we made the rounds, lets rest for a short while
            main_loop_sleep(defaults)
    except KeyboardInterrupt:
        print("Caught Keyboard Interupt")
    finally:
        #debug_print_torrents(torrents)
        #debug_print_settings_structs(defaults,groups,feeds)

        print("Shutting Down Service...")
        save_configurations(defaults,groups,feeds,torrents)
        stop_downloads_thread()

if __name__ == "__main__":
    main()








