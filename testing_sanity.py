import yaml
import time
from src import fileio

queue = fileio.FileIO(autosaveFilename="iotest.yml")
queue.hosts["whatbox"] = fileio.SFTPServerConfig(hostname="",username="",password="")
job = fileio.SFTPDownload("whatbox","files/[Erai-raws] Kaizoku Oujo - 12 END [1080p][Multiple Subtitle][BF50E67A].mkv","/tmp/test.mkv")
uuid = queue.addNewJob(job)
time.sleep(3)
print(queue.currentJobs[uuid].getProcessingStatus())
print("stopping queue")
queue.stopQueue()
time.sleep(3)
print("loading queue")
queue = yaml.safe_load(open("iotest.yml","r"))
while(uuid in queue.currentJobs):
    print(queue.currentJobs[uuid].getProcessingStatus())
    time.sleep(2)
# print(yaml.dump(queue))