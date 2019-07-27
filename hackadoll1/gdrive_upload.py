import os
import sys

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

try:
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    gdrive = GoogleDrive(gauth)

    vid_filename = sys.argv[1]
    video_file = gdrive.CreateFile({'parents': [{'kind': 'drive#fileLink', 'id': sys.argv[2]}]})
    video_file.SetContentFile(vid_filename)
    video_file.Upload()
    os.remove(vid_filename)
except:
    sys.exit(1)

sys.exit()
