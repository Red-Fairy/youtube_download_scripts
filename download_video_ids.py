import os
from turtle import down
import yt_dlp
import pandas as pd
import argparse
import json
import glob
import smtplib
from email.mime.text import MIMEText
import time

# NEW: Import wandb for progress tracking
os.environ["WANDB_API_KEY"] = "51014f57401295d9587e4a5b2e8507492e718b73"
import wandb

MAX_DOWNLOAD_RETRIES = 5
DELAY_FOR_RATE_LIMIT = 60
DELAY_FOR_SUCCESS_DOWNLOAD = 10

class Logger:
    def __init__(self, log_path):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_file = open(log_path, 'w')
    
    def log(self, message):
        print(message)
        self.log_file.write(message + '\n') 
        self.log_file.flush()

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

    downloaded_video_paths = glob.glob(os.path.join(output_root, '*.mp4'))
    downloaded_video_ids = [os.path.basename(path).split('.')[0] for path in downloaded_video_paths]
    video_ids = [x for x in video_ids if x not in downloaded_video_ids]
    logger.log(f"Start downloading {len(video_ids)} videos")

    total_videos = len(video_ids)

    giveup_count = 0

    with yt_dlp.YoutubeDL(ytdlp_options) as ydl:
        for i, video_id in enumerate(video_ids):
            logger.log(f"--- Processing video {i+1}/{total_videos}: {video_id} ---")
            wandb.log({"message": f"Processing video {i+1}/{total_videos}: {video_id}"})

            output_path = os.path.join(output_root, video_id + '.mp4')

            if not os.path.exists(output_path):
                retries = 0
                download_successful = False
                while retries < MAX_DOWNLOAD_RETRIES:
                    try:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        ydl.download([video_url])
                        logger.log(f"Successfully downloaded video with ID {video_id}")
                        wandb.log({"progress": (i+1)/total_videos, "last_video_status": "Success"})
                        wandb.log({"message": f"Successfully downloaded video with ID {video_id}"})
                        download_successful = True
                        break 

                    except Exception as e:
                        message = str(e)
                        # Check for "Broken pipe" or other common transient network errors
                        if "Broken pipe" in message or "content isn't available" in message:
                            message_short = "Broken pipe" if "Broken pipe" in message else "Content not available"
                            retries += 1
                            if retries >= MAX_DOWNLOAD_RETRIES:
                                logger.log(f"ERROR: Download failed for {video_id} after {MAX_DOWNLOAD_RETRIES} retries. Final error: {message}")
                                wandb.log({"message": f"Download failed for {video_id} after {MAX_DOWNLOAD_RETRIES} retries. Final error: {message}"})
                                wandb.log({"last_video_status": "Failed, Reason: " + message_short})
                                giveup_count += 1
                                break # Give up

                            if giveup_count >= 10:
                                message = f"Give up after {giveup_count} videos due to Broken pipe or Content not available.\nTerminating the script."
                                logger.log(message)
                                wandb.log({"message": message})
                                return False # This is a fatal error, so we exit the function

                            backoff_time = DELAY_FOR_RATE_LIMIT
                            logger.log(f"WARNING: Encountered a '{message_short}' for {video_id}. Retrying in {backoff_time} seconds... (Attempt {retries}/{MAX_DOWNLOAD_RETRIES})")
                            time.sleep(backoff_time)
                        
                        elif "not a bot" in message:
                            message = "IP is blocked.\nTerminating the script."
                            logger.log(message)
                            wandb.log({"message": message})
                            # send_termination_notification(message, email_args)
                            return False # This is a fatal error, so we exit the function
                        
                        else: # Handle other, non-retriable errors
                            if 'confirm your age' in message:
                                message = "Need to confirm age for video " + video_id + ". Skipping this video."
                            else:
                                message = f"Encountered unexpected error: {e} when downloading video {video_id}"
                            logger.log(f"ERROR: An unrecoverable error occurred for video {video_id}: {message}")
                            wandb.log({"message": message})
                            wandb.log({"last_video_status": "Failed (Other)"})
                            break # Exit retry loop for other errors

                # --- NEW: Polite delay between each video download ---
                if download_successful:
                    logger.log(f"Waiting {DELAY_FOR_SUCCESS_DOWNLOAD}s before next video...")
                    time.sleep(DELAY_FOR_SUCCESS_DOWNLOAD)

            else:
                message = f"Video already exists."
                logger.log(message)
                wandb.log({"log_message": message})

    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download videos from YouTube')
    parser.add_argument('--start', type=int, default=0, help='Start index')
    parser.add_argument('--end', type=int, default=-1, help='End index')
    parser.add_argument('--output_root', type=str, required=True, help='Root directory to save the downloaded videos')
    parser.add_argument('--id_file_path', type=str, required=True, help='Path to the file containing video IDs')
    parser.add_argument('--cookie_path', type=str, default=None, help='Path to the cookie file')
    parser.add_argument('--log_path', type=str, default=None, help='Path to the log file')
    parser.add_argument('--unwanted_categories', type=str, nargs='+', default=["Music"], help='List of unwanted categories')
    
    parser.add_argument('--wandb_project', type=str, default='youtube-video-downloader', help='Weights & Biases project name')
    # parser.add_argument('--wandb_api_key', type=str, required=True, help='Weights & Biases API key')
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
                    category = video['categoryName'] if 'categoryName' in video else None
                    if category is None or category not in args.unwanted_categories:
                        video_ids.append(video['videoId'])
        except json.JSONDecodeError:
            logger.log(f"Skipping line, not a valid JSON object: {line.strip()}")

    if not video_ids:
        logger.log(f"No video IDs found in the file {id_file_path}")
        exit(1)

    video_ids = video_ids[args.start: args.end if args.end != -1 else len(video_ids)]
    success = download_video(video_ids, args.output_root, args.cookie_path, logger, email_args)

    # write the success to a file
    if success:
        logger.log(f"Finished successfully.")

    del logger
    wandb.finish()