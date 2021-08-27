from fastapi import FastAPI
import yaml

from threads import downloads

app = FastAPI()
settings = {} #default to no settings
try:
    #TODO make the settings file parse location configurable
    settings_file = open("settings.yaml","r")
    settings = yaml.safe_load(settings_file)
except FileNotFoundError:
    print("Unable to open the settings file - Is this the first time running the program?")
except Exception as e:
    print(e)

@app.on_event("startup")
def startup():
    print("Starting the server...")
    #Spawn Threads to have other sections of the program ready to run
    #torrent thread
    if "downloads" in settings:
        downloads.start(settings["downloads"])
    else:
        downloads.start({})
    pass

@app.on_event("shutdown")
def shutdown():
    print("Stopping the server...")
    print("Signaling threads to stop...")
    #Signal the threads to stop and then wait on them
    #torrent thread
    downloads.stop()

    global settings
    print("Writing settings to file")
    settings["downloads"] = downloads.serializeSettings()
    
    #TODO make the settings file parse location configurable
    settings_file = open("settings.yaml","w")
    yaml.dump(settings,settings_file)
    #print(yaml.dump(settings))