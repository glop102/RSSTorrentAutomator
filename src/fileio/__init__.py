from.ioqueue import FileIO

from .debugtasks import Debug10SDelay,Debug10SDelayFail
from .sftpdownload import SFTPDownload,SFTPServerConfig

# How to use:
# 1) import FileIO from this module and make a new object of it or import a yaml file with it
# 2) add any server hosts you need for remote IO (eg sftp)
# 3) create your specific IO handler and use addNewJob()