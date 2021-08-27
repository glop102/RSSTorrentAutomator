#!/usr/bin/env python3
import signal
from settings import parse_settings_file, settings_final_sanity_check, save_settings_to_file
from settings import parse_torrents_status_file, save_torrents_to_file
from feeds import check_for_new_links,check_if_feed_marked_for_deletion
from torrents import expand_new_torrent_object,process_torrent
from downloads import setup_downloads_thread,stop_downloads_thread
from threading import Event

#https://stackoverflow.com/a/46346184/3177712
main_loop_conditional = Event()
def signal_program_shutdown(sig,frame):
    print("Caught SIGTERM")
    main_loop_conditional.set()

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
def save_configurations(defaults,groups,feeds,torrents):
    sett = open("rss_feed.conf","w")
    save_settings_to_file(sett,defaults,groups,feeds)
    sett.close()

    sett = open("current_torrents.conf","w")
    save_torrents_to_file(sett,torrents)
    sett.close()

def update_feeds(defaults,groups,feeds,torrents):
    removal_list = []
    config_update= False
    for feed_url in feeds:
        feed = feeds[feed_url]
        links = check_for_new_links(feed)
        if len(links) > 0 :
            #Update the last entry information so we only grab newer entries
            feed["last_seen_link"] = links[-1]["link"]
            feed["last_seen_link_date"] = links[-1]["published"]
            config_update = True
            print("\nFound {} new links for {}".format(len(links),feed_url) )

            #Add the new links onto the pile for us to process
            torrents.extend(links)
        group={"group_name":"DummyGroup"}
        if "group_name" in feed:
            group = groups[feed["group_name"]]
        if check_if_feed_marked_for_deletion(defaults,group,feed):
            print("Removing feed : "+feed_url)
            config_update = True
            removal_list.append(feed_url)
    for feed_url in removal_list:
        del feeds[feed_url]
    if config_update:
        save_configurations(defaults,groups,feeds,torrents)

def update_torrents(defaults,groups,feeds,torrents):
    #Tech Note - Torrent expansion must happen one at a time after some processing has occured to allow the increment_*() to happen before the next torrent is processed
    config_update = False
    for torrent in torrents:
        try:
            group={"group_name":"DummyGroup"}
            feed={"feed_url":"DummyFeedUrl"}
            if "feed_url" in torrent and torrent["feed_url"] in feeds:
                feed = feeds[ torrent["feed_url"] ]
            if "group_name" in feed:
                group = groups[feed["group_name"]]
            elif "group_name" in torrent:
                group = groups[torrent["group_name"]]

            #Lets check if this torrent is new, and expand variables from the parrent sections
            if not "current_processing_step" in torrent:
                expand_new_torrent_object(defaults,group,feed,torrent)
                save_configurations(defaults,groups,feeds,torrents)
            starting_processing_step = torrent["current_processing_step"]

            #Now lets run the processing steps on the torrent
            process_torrent(defaults,group,feed,torrent)

            if starting_processing_step != torrent["current_processing_step"]:
                save_configurations(defaults,groups,feeds,torrents)
        except Exception as err:
            print(err)

    # remove the torrents that are done processing    
    before = len(torrents)
    torrents[:] = [torrent for torrent in torrents if torrent["current_processing_step"] != "ready_for_removal 0"]
    if before != len(torrents):
        save_configurations(defaults,groups,feeds,torrents)


def main():
    try:
        defaults,groups,feeds,torrents = parse_configurations()

        #lets get the file downloads going
        setup_downloads_thread(defaults)

        feed_check_period = 30*60 #30 minutes default
        torrent_check_period = 4*60 #4 minutes default
        try: feed_check_period = int(defaults["feed_check_period"])
        except: pass
        try: torrent_check_period = int(defaults["torrent_check_period"])
        except: pass

        feed_delay_counter = 0
        torrent_delay_counter = 0
        while not main_loop_conditional.is_set():
            #first check the feeds to find any new torrents
            if feed_delay_counter <= 0:
                feed_delay_counter = feed_check_period
                update_feeds(defaults,groups,feeds,torrents)

            #Now that we have checked all our feeds, lets tend to our torrents
            #This includes starting the newly added torrents from the feeds
            if torrent_delay_counter <= 0:
                torrent_delay_counter = torrent_check_period
                update_torrents(defaults,groups,feeds,torrents)
            if len(torrents) == 0:
                #optimization - do not bother waking up and checking torrents if we have none
                torrent_delay_counter = feed_delay_counter

            sleep_amount = min ( feed_delay_counter , torrent_delay_counter )
            feed_delay_counter = feed_delay_counter - sleep_amount
            torrent_delay_counter = torrent_delay_counter - sleep_amount
            main_loop_conditional.wait( sleep_amount )

    except KeyboardInterrupt:
        print("Caught Keyboard Interupt")
    except AssertionError: pass #just catching SIGTERM
    finally:
        print("Shutting Down Service...")
        save_configurations(defaults,groups,feeds,torrents)
        stop_downloads_thread()

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_program_shutdown)
    main()








