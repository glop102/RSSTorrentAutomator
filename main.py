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
State Implementation - Some sort of configurable state machine?
 - How do we let the user expand/customize the behavior?
    - Base behavior of just wait for it to finish, and then download all the files
    - I want the 'delete torrent after hitting X ratio' to be user added behavior
       - would be really 'wait for X ratio' and then 'delete torrent' - aka 2 different new states
    - Probably only predefined available extra bits, but they can add post-processing steps
       - post_processing_steps : wait_for_ratio(5.0) delete_torrent()
       - post_processing_steps : delete_torrent() call_user_script(filename.sh)
          - should we deny allowing anything to happen after the delete_torrent() step?
    - Instead of just post_processing, allow them to override the steps of normal processing
       - That way these steps are just part of the default config so it is a single system to maintain
       - processing_steps : wait_for_torrent_downloaded() set_label(%label_finished%) download_files() post_processing()
          - allow arbitrary values to be used from the RSS config into the processing steps with the %% encoding
"""

default_settings = {} #just a list of vars:values
feed_groups = {}      #2D dictionary with group_name as the key to get the group
feeds = {}            #2D dictionary with the feed_url as the key to get the feed

from settings import parse_settings_file,settings_final_sanity_check,save_settings_to_file
from settings import debug_print_settings_structs
from feeds import check_for_new_links
from torrents import add_torrent_to_rtorrent
from torrents import print_torrent_name_from_infohash

#start with parsing our settings that we need
sett = open("rss_feed.conf")
default_settings,feed_groups,feeds = parse_settings_file(sett)
sett.close()
#TODO- Smooth way to parse a second file and combine the settings

#After all config files are parsed, we need to do sanity checking
settings_final_sanity_check(default_settings,feed_groups,feeds)

#Now we have sane settings, so lets update our RSS feeds
for feed_url in feeds:
    feed_sett = feeds[feed_url]
    links = check_for_new_links(feed_sett)
    if len(links) == 0 : continue

    feed_sett["last_seen_link"] = links[-1]["link"]
    feed_sett["last_seen_link_date"] = links[-1]["published"]
    print("Found {} new links for {}".format(len(links),feed_url) )

    #infohashs = add_torrents_to_rtorrent(default_settings,[link["link"] for link in links])
    for link in links:
        infohash = add_torrent_to_rtorrent(default_settings,link["link"])
        print(infohash)
        print_torrent_name_from_infohash(infohash)


#debug_print_settings_structs(default_settings,feed_groups,feeds)
sett = open("rss_feed.conf","w")
save_settings_to_file(sett,default_settings,feed_groups,feeds)
sett.close()
