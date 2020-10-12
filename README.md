# RSSTorrentAutomator

Watches a list of RSS feeds and adds the links to rTorrent.
It then will tend to the torrents acording to the processing steps you give.
I personally use it to grab seasonal anime and auto add to my Plex library.

I wrote this originally over 3 days and let the feature sprawl just happen.
It is a little bit of a mess due to absolutly 0 planning and kindof recomend using something else.

## Runtime Dependencies

python3.4+

### Gentoo

* py-xmlrpc
* feedparser
* paramiko

## Basic Setup

* Install the dependencies for your system
* clone this repo
* make your rss_feed.conf
* run the python script main.py
* (optional) add the script to a systemd service file


### Most Basic rss_feed.conf

```
server_url : https://giotto.whatbox.ca:443/xmlrpc
credentials_type : plain
credentials : username:password
download_host : giotto.whatbox.ca
download_credentials_type : plain
download_credentials : username:password
download_destination : ../NewVideos/

=====RSSFeed
feed_url : https://nyaa.si/?page=rss&q=one+punch+man+S2+[1080p]+[HorribleSubs]+-batch
```

## Advanced Configuration

Basic concepts:
* You have variables in conf files
* You expand variables as %varname%
* RSSFeeds generate torrents which copy all the variables they need

There are 3 conf files:
* rss_feed.conf is where all things start and specifies feeds. This is where you will concentrate on configuring your setup.
* current_torrents.conf is a listing of torrents that are being tracked. You likely will never need to mess with this config unless you are trying to change processing steps or something.
* queued_downloads.conf which is a very simple and dumb conf file for the downlaod thread. You should probably never mess with this file unless you are cleaning up a broken system.
You should probably never mess with the queued_downloads.conf, it will take care of itself. The current_torrents.conf should be fine on its own, but you can change it without much trouble of breaking things. The rss_feed.conf is what you should speed your time dealing with.

There are different sections in the conf files.
* Global/Defaults - rss_conf.conf - Either name works for this section. This is where some variables are directly pulled from (such as credentials) or is the last place to get a varaibles value if nothing else specifies it.
* Group - rss_feed.conf - This is intended to let you have common paramenters for a group of feeds so that they act the same. You can have a group where process Movies different from TvShows, and instead of copy/pasting the same things everywhere, you just tell the feeds that they are part of either the Movie or TvShow group
* RSSFeed - rss_feed.conf - This section is what actually gets updated in the code. You must have a feed_url specified for it grab links from.
* Torrent - current_torrents.conf - These are 'fat' sections that are a 1:1 representation of a torrent currently running inside rTorrent. These keep track of where they are in processing the torrent, and also have a copy of all the variables they need from the parent sections (RSSFeed,Group,Defaults).


### Special Variables

These varaibles are the ones with already determined uses within the program. Make sure you understand them before you try defining them yourself.

Var Name | Section | Description
------------------------- |:--------:| ---
credentials_type          | Defaults | What type of credentials is required. If set to 'plain', then you must also specify the variable credentials. If set to netrc, then you must have a valid entry in your ~/.netrc file. If set to none, then no extra work is done for determining credentials.
credentials               | Defaults | The username and password used to connect to rTorrent. It must be in the form username:password.
server_url                | Defaults | The url to use for connecting to rTorrent.
download_host             | Defualts | The hostname for conencting the sftp downloader to. This can have a port also specified with :port on the end of the hostname. Do not include a protocol specifier.
download_credentials      | Defualts | Similar to the credentials variable, but is for conencting to the sftp server.
download_credentials_type | Defaults | Similar to the credentials_type variable, but is for connecting to the sftp server.
feed_check_period         | Defaults | How many seconds to wait between checking the rss feeds (30 minutes default)
torrent_check_period      | Defaults | How many seconds to wait between checking the currently tracked torrents (4 minutes default)
processing_steps          | Any      | The steps that are taken for each torrent. Refer to the table of processing steps below. It has default processing steps if not specified by the user in the Defaults section.
post_processing_steps     | Any      | Steps that are taken for a torrent if the post_processing_steps() function is used. Has a default of simply stop_tracking_torrent()
download_destination      | Defaults | This variable is used in the defualt processing_steps. Default value of "./"
group_name                | Group    | The name of the group you are creating. Use this name to reference from a RSSFeed section.
group_name                | RSSFeed  | The name of the group that this feed inherits from. Gets applied when a torrent is added.
feed_url                  | RSSFeed  | The url used for getting new torrents.
last_seen_link            | RSSFeed  | The last link that was added to the torrents from the feed_url. This get automattically updated when new links are found and turned into torrents.
last_seen_link_date       | RSSFeed  | The timestamp of the entry from the last link the feed has seen. This is not the date taht the link was added to our program, but the date reported by the feed itself. (date of when the link was added to the feed)
remove_feed_if_equal      | RSSFeed  | This will remove the feed from the list of things been watched if the two strings are the same. You specify the two strings with a space between them. Variables will be expanded for this entry.
current_processing_step   | Torrent  | An automatically updated variable that tracks the state of which processing step the torrent is currently doing. It is in the form of "varaible_name number", where the variable_name has a list of steps, and the number is which step in that variable it is in (starts at 0).
feed_url                  | Torrent  | A copy of the feed_url from the feed that generated this torrent. (Used in processing)
link                      | Torrent  | The link that was given to rTorrent.
title                     | Torrent  | The title of the entry from the rss feed where we got this torrent.
published                 | Torrent  | The timestamp of when the entry was added to the rss feed. (Not when the link was added to rTorrent)
processing_steps          | Torrent  | A copy from its parent sections, and almost certainly the starting point of processing.
infohash                  | Torrent  | The hash string used to represent the torrent in rTorrent. This is how we control/ask what the torrent is doing in rTorrent.


### Processing Steps

The default processing steps are the following:
* add the torrent
* wait for the torrent to complete
* download the files of the torrent into %download_destination%
* do the post_processing steps
  * default post_processing is to just stop tracking the torrent in rTorrent

Function Name | Arguments | Description
------------------------- |:------:| ---
add_torrent               |        | Adds the torrent entry into rTorrent. This should be the first processing step you ever do
wait_for_torrent_complete |        | Waits for the torrent to finish downloading in rTorrent before moving to the next step
wait_for_ratio            | float  | Waits for the torrent to reach a seeding ratio given as an argument
set_label                 | string | Set the label of the torrent to the string given. (Label is reflected in ruTorrent)
stop_tracking_torrent     |        | Remove this torrent entry from the program, but leave it untouched in rTorrent in whatever state it is in
delete_torrent_only       |        | Remove the torrent from rTorrent and also stop tracking the torrent. Leaves the files wherever rTorrent downloaded them to
delete_torrent_and_files  |        | Removes the torrent from rTorrent, stops tracking the torrent, and queues the remote files to be deleted. This is the recomended way to get rid of torrents.
download_files            | string | Queue all the files to download from the remote rTorrent location to the local machine. The given string is the destination. Will be a folder if multiple files, or the filename if only a single file. (uses variable name current_file_download_status)
download_files_into_folder| string | Queue all the files to download from the remote rTorrent location to the local machine. The given string is the destination. Destination string is always a folder, even if only a single file. (uses variable name current_file_download_status)
increment_torrent_var     | string | Will increment an integer variable in the current torrent structure. The given string is the name of the variable.
increment_feed_var        | string | Will increment an integer variable in the parent feed structure. Useful for giving unique names to torrents grabed by the same feed. (Not valid if the feed has been deleted)
increment_group_var       | string | Will increment an integer variable in the parent group structure that the feed inherited from. (Not valid if the feed has been delted or if the feed does not inherit from a group)
increment_global_var      | string | Will increment an integer variable in the parent global structure.
addition_torrent_var      | float,float,string | Add the two numbers together and store the result in the variable that is the last argument. Stores the value in the current torrent structure.  You can dereference a variable for either integers with %var% like normal.
addition_feed_var         | float,float,string | Add the two numbers together and store the result in the variable that is the last argument. Stores the value in the parent feed structure. You can dereference a variable for either integers with %var% like normal.
addition_group_var        | float,float,string | Add the two numbers together and store the result in the variable that is the last argument. Stores the value in the parent group structure. You can dereference a variable for either integers with %var% like normal.
addition_global_var       | float,float,string | Add the two numbers together and store the result in the variable that is the last argument. Stores the value in the global structure. You can dereference a variable for either integers with %var% like normal.
post_processing_steps     |        | Switch to processing the step list in the varaible called post_processing_steps. (Be carefule of recursion)
processing_steps_variable | string | Switch to processing the step list in the varaible name given as the argument. (Be carefule of recursion)
retrieve_torrent_name     |        | Gets the name of the torrent from the server and stores it in variable named "torrent_name"
regex_parse               |string,string,string | Applies a regular expression to a variable and stores it in another variable. The order of arguments is (SourceVarName,RegularExpression,DestinationVarName), The source variable must exist, but the destination can be new. It sets the variable regex_matched to true or false based on if it matched anything.
set_feed_var              | string,string | Save a value when processing a torrent to the feed that a torrent came from. First string is the variable name. Second string is the value to set. (eg set_feed_var(last_downloaded_epNum,%episode_num%) )
branch_if_vars_equal      | string,string,string | It compares the values of two variabless and if they are the same, it will jump to the processing steps in the variable of the third argument. If a variable name does not exist, then it will not take the branch.
branch_if_values_equal    | string,string,string | It compares the values of two strings and if they are the same, it will jump to the processing steps in the variable of the third argument
get_file_info             | string | List some filepath info about a given file. It will add to the torrent state the following: absolute_filepath, absolute_folderpath, filename, basename, extension
populate_next_file_info   | string | Given a folder, it will find some random file and then get the same information about it as get_file_info does. It also adds the the variable foundfile and sets it to either "true "or "false"
rename_file               | string,string | Given a source file or folder, it will attempt to rename it to the destination string. Both must reference the location as this can move a file on the same file system
move_file                 | string,string | Given a source file or folder, it will move it SAFELY to the new location, even across filesystems. This can rename the item during the move. If it is across filesystems, it will uses the downlaod thread to make the copy safely before deleting the original


### String Varaible Expansion

Variables are referenced with %var_name%, and for certain parts on the conf files, these variables get expanded.

When varaibles are expanded, you can modify how they get expanded. The syntax is %var_name:mod(arg1,arg2)%

Modification Name | Arguments | Description
-------- |:-----------:| ---
leftpad  | int [,char] | Makes the expanded variable longer with a minimum length of the int given. Optionally, you can also specify which character is used to make the string longer (defualt is space). Useful if you want to make a number for a season or something (eg ShowName.s02.e05.mkv). This always put the extra characters on the left side of the string.
rightpad | int [,char] | Makes the expanded variable longer with a minimum length of the int given. Optionally, you can also specify which character is used to make the string longer (defualt is space). This always put the extra characters on the right side of the string.
lpad     | int [,char] | Same as leftpad
rpad     | int [,char] | Same as rightpad
replace  | string,string\* | Every 2 arguments given specify a pair. The first of the pair is what will be replace. The second of the pair is what it will be replaced with.
sanitizeFilename | | A convience function that has a hardcoded string that it gives to replace so that filesystems do not complain about illegal characters.
