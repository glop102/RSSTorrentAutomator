from fastapi import FastAPI
import yaml

app = FastAPI(
    title="RSS Torrent Automater"
)

@app.on_event("startup")
def startup():
    print("Starting the server...")

@app.on_event("shutdown")
def shutdown():
    print("Stopping the server...")
    print("Signaling threads to stop...")
