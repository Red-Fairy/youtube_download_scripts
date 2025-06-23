import os
from turtle import down
import yt_dlp
import pandas as pd
import argparse
import json
import glob
import smtplib
from email.mime.text import MIMEText

# NEW: Import wandb for progress tracking
import wandb

class Logger:
    def __init__(self, log_path):
        self.log_path = log_path
        self.log_file = open(log_path, 'a')
    
    def log(self, message):
        print(message)
        self.log_file.write(message + '\n') 
        self.log_file.flush()
        # NEW: Log messages to wandb
        if wandb.run:
            wandb.log({"log_message": message})

    def log_silent(self, message):
        self.log_file.write(message + '\n') 
        self.log_file.flush()

    def __del__(self):
        self.log_file.close()

# NEW: Function to send an email notification
def send_termination_notification(error_message, email_args):
    if not all(email_args.values()):
        print("Email credentials not fully provided. Skipping email notification.")
        return

    msg = MIMEText(f"The script has been terminated due to an IP block.\n\nError message: {error_message}")
    msg['Subject'] = 'Video Download Script Terminated'
    msg['From'] = email_args['sender_email']
    msg['To'] = email_args['receiver_email']

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(email_args['sender_email'], email_args['sender_password'])
            smtp_server.sendmail(email_args['sender_email'], email_args['receiver_email'], msg.as_string())
        print("Termination notification email sent.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def download_video(video_ids, output_root, cookie_path, logger: Logger, email_args):

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
                logger.log(f"Downloaded video with ID {video_id}")
                # NEW: Log successful download to wandb
                wandb.log({"download_status": "success", "video_id": video_id})
            except Exception as e:
                message = str(e)
                if "not a bot" in message:
                    logger.log(f"IP is blocked. Terminating the script.")
                    # NEW: Send email notification and log to wandb before exiting
                    # send_termination_notification(message, email_args)
                    wandb.log({"status": "terminated", "reason": "IP blocked"})
                    break
                else:
                    logger.log(f"Error downloading video with ID {video_id}: {e}")
                    # NEW: Log error to wandb
                    wandb.log({"download_status": "error", "video_id": video_id, "error_message": message})
        else:
            logger.log(f"Video with ID {video_id} already exists in the specified output path.")
            # NEW: Log existing video to wandb
            wandb.log({"download_status": "already_exists", "video_id": video_id})
                

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download videos from YouTube')
    parser.add_argument('--start', type=int, default=0, help='Start index')
    parser.add_argument('--end', type=int, default=-1, help='End index')
    parser.add_argument('--output_root', type=str, required=True, help='Root directory to save the downloaded videos')
    parser.add_argument('--id_file_path', type=str, required=True, help='Path to the file containing video IDs')
    parser.add_argument('--cookie_path', type=str, default=None, help='Path to the cookie file')
    parser.add_argument('--log_path', type=str, default=None, help='Path to the log file')
    
    # NEW: Arguments for Weights & Biases and Email Notifications
    parser.add_argument('--wandb_project', type=str, default='youtube-video-downloader', help='Weights & Biases project name')
    parser.add_argument('--wandb_api_key', type=str, required=True, help='Weights & Biases API key')
    parser.add_argument('--sender_email', type=str, default=None, help='Sender email address for notifications')
    parser.add_argument('--sender_password', type=str, default=None, help='Sender email password for notifications')
    parser.add_argument('--receiver_email', type=str, default=None, help='Receiver email address for notifications')

    args = parser.parse_args()
    
    # NEW: Initialize Weights & Biases
    wandb.init(project=args.wandb_project, config=args)
    
    email_args = {
        'sender_email': args.sender_email,
        'sender_password': args.sender_password,
        'receiver_email': args.receiver_email
    }

    id_file_path = args.id_file_path
    log_path = args.log_path
    logger = Logger(log_path)

    video_ids = []
    with open(id_file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        try:
            json_data = json.loads(line)
            if 'id' in json_data:
                video_ids.append(json_data['id'])
            elif 'videos' in json_data:
                for video in json_data['videos']:
                    video_ids.append(video['videoId'])
        except json.JSONDecodeError:
            logger.log(f"Skipping line, not a valid JSON object: {line.strip()}")

    if not video_ids:
        logger.log(f"No video IDs found in the file {id_file_path}")
        exit(1)

    video_ids = video_ids[args.start: args.end if args.end != -1 else len(video_ids)]
    logger.log(f"Number of videos to download: {len(video_ids)}")
    download_video(video_ids, args.output_root, args.cookie_path, logger, email_args)

    # NEW: Finish the wandb run
    wandb.finish()