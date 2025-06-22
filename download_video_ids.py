import os
from turtle import down

import yt_dlp
import pandas as pd
import argparse
import json
import glob

def download_video(video_ids, output_root, cookie_path):

    # Set yt-dlp options
    ytdlp_options = {
        'outtmpl': os.path.join(output_root, '%(id)s.%(ext)s'), 
        'format': (
            'bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[vcodec^=avc1]+bestaudio/best[vcodec^=avc1]'
        ),
        'merge_output_format': 'mp4',
    }

    if cookie_path is not None:
        ytdlp_options['cookies'] = cookie_path

    with yt_dlp.YoutubeDL(ytdlp_options) as ydl:
      for video_id in video_ids:
        print(f"Downloading video with ID {video_id}")
        output_path = os.path.join(output_root, video_id + '.mp4')
        if not os.path.exists(output_path):
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            # ydl.params['format'] = video_format
            ydl.download([video_url])
            os.rename(os.path.join(output_root, f"{video_id}.mp4"), output_path)
        else:
            print(f"Video with ID {video_id} already exists in the specified output path.")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Download videos from YouTube')
    parser.add_argument('--output_root', type=str, required=True, help='Root directory to save the downloaded videos')
    parser.add_argument('--id_file_path', type=str, required=True, help='Path to the file containing video IDs')
    parser.add_argument('--cookie_path', type=str, default=None, help='Path to the cookie file')
    args = parser.parse_args()
    
    id_file_path = args.id_file_path
    video_ids = []
    # each line is a json object
    with open(id_file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
      json_data = json.loads(line)
      video_ids.append(json_data['id'])

    print("Number of videos to download: ", len(video_ids))

    download_video(video_ids, args.output_root, args.cookie_path)
