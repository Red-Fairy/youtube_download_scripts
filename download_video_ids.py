import os
from turtle import down

import yt_dlp
import pandas as pd
import argparse
import json
import glob

class Logger:
    def __init__(self, log_path):
        self.log_path = log_path
        self.log_file = open(log_path, 'a')
    
    def log(self, message):
        print(message)
        self.log_file.write(message + '\n') 
        self.log_file.flush()

    def log_silent(self, message):
        self.log_file.write(message + '\n') 
        self.log_file.flush()

    def __del__(self):
        self.log_file.close()

def download_video(video_ids, output_root, cookie_path, logger: Logger):

    # Set yt-dlp options
    ytdlp_options = {
        'outtmpl': os.path.join(output_root, '%(id)s.%(ext)s'), 
        'format': (
            'bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[vcodec^=avc1]+bestaudio/best[vcodec^=avc1]'
        ),
        'merge_output_format': 'mp4',
        'ignoreerrors': False,
        'quiet': True,
    }

    if cookie_path is not None:
        ytdlp_options['cookies'] = cookie_path

    with yt_dlp.YoutubeDL(ytdlp_options) as ydl:
      for video_id in video_ids:
        print(f"Downloading video with ID {video_id}")
        output_path = os.path.join(output_root, video_id + '.mp4')
        
        if not os.path.exists(output_path):
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            try:
                ydl.download([video_url])
                # os.rename(os.path.join(output_root, f"{video_id}.mp4"), output_path)
                logger.log(f"Downloaded video with ID {video_id}")
            except Exception as e:
                # check the traceback error message
                message = str(e)
                import pdb; pdb.set_trace()
                if "not a bot" in message:
                    logger.log(f"IP is blocked. Terminating the script.")
                    exit(1)
                else:
                    logger.log(f"Error downloading video with ID {video_id}: {e}")
        else:
            logger.log(f"Video with ID {video_id} already exists in the specified output path.")
                

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Download videos from YouTube')
    parser.add_argument('--start', type=int, default=0, help='Start index')
    parser.add_argument('--end', type=int, default=-1, help='End index')
    parser.add_argument('--output_root', type=str, required=True, help='Root directory to save the downloaded videos')
    parser.add_argument('--id_file_path', type=str, required=True, help='Path to the file containing video IDs')
    parser.add_argument('--cookie_path', type=str, default=None, help='Path to the cookie file')
    parser.add_argument('--log_path', type=str, default=None, help='Path to the log file')
    args = parser.parse_args()
    
    id_file_path = args.id_file_path
    log_path = args.log_path
    logger = Logger(log_path)

    video_ids = []
    # each line is a json object
    with open(id_file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
      json_data = json.loads(line)
      if 'id' in json_data:
        video_ids.append(json_data['id'])
      elif 'videos' in json_data:
        for video in json_data['videos']:
          video_ids.append(video['videoId'])
      else:
        logger.log(f"Video ID not found in the file {id_file_path}")
        exit(1)

    video_ids = video_ids[args.start: args.end if args.end != -1 else len(video_ids)]
    logger.log(f"Number of videos to download: {len(video_ids)}")
    download_video(video_ids, args.output_root, args.cookie_path, logger)
