import os
from turtle import down

import yt_dlp
import pandas as pd
import argparse
import json
import glob

'''
Sample data:
{
    "kind": "youtube#video",
    "etag": "yxddzEqDHaxw4xgRzOfjepvfa_0",
    "id": "05-ceCK5e9U",
    "snippet": {
      "publishedAt": "2025-04-16T18:34:07Z",
      "channelId": "UCUK0HBIBWgM2c4vsPhkYY4w",
      "title": "Backwards Bullet Shockwaves between Glass at 375,000 FPS - The Slow Mo Guys",
      "description": "Gav and Dan discover an eruption of shockwaves and flashes while challenging a 30.06 round to 50 panes of glass.\nInstagram - https://www.instagram.com/theslowmoguys\nTik Tok - https://www.tiktok.com/@theslowmoguys\nFilmed at 120,000 - 375,000 FPS with the Phantom TMX 7510\nBackwards Bullet Shockwaves between Glass at 375,000 FPS - The Slow Mo Guys",
      "thumbnails": {
        "default": {
          "url": "https://i.ytimg.com/vi/05-ceCK5e9U/default.jpg",
          "width": 120,
          "height": 90
        },
        "medium": {
          "url": "https://i.ytimg.com/vi/05-ceCK5e9U/mqdefault.jpg",
          "width": 320,
          "height": 180
        },
        "high": {
          "url": "https://i.ytimg.com/vi/05-ceCK5e9U/hqdefault.jpg",
          "width": 480,
          "height": 360
        },
        "standard": {
          "url": "https://i.ytimg.com/vi/05-ceCK5e9U/sddefault.jpg",
          "width": 640,
          "height": 480
        },
        "maxres": {
          "url": "https://i.ytimg.com/vi/05-ceCK5e9U/maxresdefault.jpg",
          "width": 1280,
          "height": 720
        }
      },
      "channelTitle": "The Slow Mo Guys",
      "tags": [
        "slomo", "slow", "mo", "super", "motion", "Slow Motion", "1000", "1000fps", 
        "gav", "dan", "slowmoguys", "phantom", "guys", "HD", "flex", "gavin", "free", 
        "gavin free", "high speed camera", "the slow mo guys", "2000", "2000fps", 
        "5000", "5000fps", "bullet", "backwards", "shockwave", "375000", "30.06", "rifle"
      ],
      "categoryId": "24",
      "liveBroadcastContent": "none",
      "defaultLanguage": "en-GB",
      "localized": {
        "title": "Backwards Bullet Shockwaves between Glass at 375,000 FPS - The Slow Mo Guys",
        "description": "Gav and Dan discover an eruption of shockwaves and flashes while challenging a 30.06 round to 50 panes of glass.\nInstagram - https://www.instagram.com/theslowmoguys\nTik Tok - https://www.tiktok.com/@theslowmoguys\nFilmed at 120,000 - 375,000 FPS with the Phantom TMX 7510\nBackwards Bullet Shockwaves between Glass at 375,000 FPS - The Slow Mo Guys"
      },
      "defaultAudioLanguage": "en-GB"
    },
    "contentDetails": {
      "duration": "PT12M13S",
      "dimension": "2d",
      "definition": "hd",
      "caption": "false",
      "licensedContent": true,
      "contentRating": {},
      "projection": "rectangular"
    },
    "statistics": {
      "viewCount": "976564",
      "likeCount": "55434",
      "favoriteCount": "0",
      "commentCount": "2092"
    }
  }
'''

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
    parser.add_argument('--start', type=int, default=0, help='Index of the first video to download')
    parser.add_argument('--end', type=int, default=-1, help='Index of the last video to download')
    parser.add_argument('--output_root', type=str, default='/share/ma/datasets/slow_motion/youtube/8k_video_ultra_hd', help='Root directory to save the downloaded videos')
    parser.add_argument('--id_path', type=str, default='/home/rl897/data_downloading/google_api/data/videos_metadata.jsonl', 
                        help='Path to the JSONL file containing video IDs and titles')
    parser.add_argument('--keywords_title', type=str, nargs='+', default=None, help='Keywords to filter videos')
    parser.add_argument('--keywords_description', type=str, nargs='+', default=None, help='Keywords to filter videos')
    parser.add_argument('--cookie_path', type=str, default=None, help='Path to the cookie file')
    args = parser.parse_args()
    
    id_title_path = args.id_path
    video_ids = []
    # each line is a json object
    with open(id_title_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
      json_data = json.loads(line)

      if args.keywords_title is None and args.keywords_description is None:
        video_ids.append(json_data['id'])
        continue
      
      title = json_data['snippet']['title'].lower()
      if any(keyword in title for keyword in args.keywords_title):
        video_ids.append(json_data['id'])

      description = json_data['snippet']['description'].lower()
      if any(keyword in description for keyword in args.keywords_description):
        video_ids.append(json_data['id'])

    video_ids = video_ids[args.start: args.end if args.end != -1 else len(video_ids)]
    print("Number of videos to download: ", len(video_ids))

    download_video(video_ids, args.output_root, args.cookie_path)
