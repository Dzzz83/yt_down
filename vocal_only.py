import os
import logging
import warnings

# set environment variables to suppress tensorflow logs and disable gpu
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# configure tensorflow's logger to error level
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# suppress python warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import yt_dlp
from spleeter.separator import Separator
from pydub import AudioSegment
import shutil
import glob
import time

# function for downloading audio
def download_audio(youtube_url, output_dir):
    # create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # define yt-dlp options for downloading the best audio
    ydl_opts = {
        'format': 'bestaudio/best', # download the best audio

        # defines the output filename and directory for the downloaded file
        'outtmpl': os.path.join(output_dir, 'downloaded_audio.%(ext)s'), 

        'postprocessors': [{
            'key': 'FFmpegExtractAudio', # extract audio using ffmpeg
            'preferredcodec': 'mp3', # convert to mp3 to ensure the best audio quality
            'preferredquality': '192', # sets the target bitrate for the audio in kbps. 192 is good
        }],
        'quiet': True, # set quiet so yt-dlp's output isn't printed out in the terminal for simplicity
        'no_warnings': True, # to stop yt-dlp's warnings
    }

    # initialize yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # download yt video using youtube_url
        ydl.download([youtube_url])

    # construct the path to the downloaded mp3 file
    downloaded_mp3 = os.path.join(output_dir, 'downloaded_audio.mp3')

    # check if the downloaded mp3 exists, raise error if not found
    if not os.path.exists(downloaded_mp3):
        raise FileNotFoundError(f"{downloaded_mp3} not found after download.")

    # return the path to the downloaded mp3
    return downloaded_mp3

# function to extract vocals from the audio using spleeter
def extract_vocals(input_audio, output_dir):
    # initialize spleeter's separator with a 2-stem model (vocals and accompaniment)
    separator = Separator('spleeter:2stems')  # splits into 2 stems : vocal and music

    # perform the separation and store in the output directory
    separator.separate_to_file(input_audio, output_dir)

    # wait for 5 seconds to ensure files are written
    time.sleep(5)

    # extract the file name from the path. for example, 
    # os.path.basename('C:/Users/ExampleUser/Music/track1.mp3') -> 'track1.mp3'
    # os.path.splitext('track1.mp3') -> ('track1', '.mp3')
    # base_filename -> 'track1'
    base_filename = os.path.splitext(os.path.basename(input_audio))[0]

    # construct the path to the extracted vocals wav file
    vocals_wav_path = os.path.join(output_dir, base_filename, 'vocals.wav')
    # 'C:/Users/ExampleUser/ProcessedAudio/track1/vocals.wav'

    # check if the vocals wav file exists, raise error if not found
    if not os.path.exists(vocals_wav_path):
        raise FileNotFoundError(f"Vocals WAV file not found at {vocals_wav_path}.")

    # return the path to the extracted vocals wav file
    return vocals_wav_path

# function to determine the next vocal file number based on existing files
def get_next_vocal_number(output_dir='split_vocals'):
    """
    determines the next vocal file number based on existing files in the output directory.

    :param output_dir: directory where split vocal files are saved.
    :return: the next available vocal number as an integer.
    """
    # check if the output directory exists, create it if not
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        return 1  # start from 1 if directory does not exist

    # find all files in the output directory that match the pattern 'vocal*.wav'
    existing_files = glob.glob(os.path.join(output_dir, 'vocal*.wav'))
    
    # initialize the maximum number found to 0
    max_number = 0
    
    # wait for 5 seconds to ensure all files are accessible
    time.sleep(5)
    
    # iterate over each existing file to find the highest vocal number
    for file in existing_files:
        # get the base name of the file (e.g., 'vocal12.wav')
        basename = os.path.basename(file)
        
        # split the base name into name and extension (e.g., ('vocal12', '.wav'))
        name, _ = os.path.splitext(basename)
        
        # extract the numeric part from the name (e.g., '12' from 'vocal12')
        number_part = ''.join(filter(str.isdigit, name))
        
        # check if the extracted part is a digit
        if number_part.isdigit():
            # convert the numeric string to an integer
            number = int(number_part)
            
            # update max_number if the current number is greater
            if number > max_number:
                max_number = number
                
    # return the next available number by adding 1 to the max found
    return max_number + 1

# function to split a wav file into multiple chunks of specified length
def split_wav_file(input_wav, output_dir='split_vocals', chunk_length_sec=30, start_number=1):
    """
    splits a wav file into multiple chunks of specified length with sequential naming.

    :param input_wav: path to the input wav file.
    :param output_dir: directory where split files will be saved.
    :param chunk_length_sec: length of each chunk in seconds.
    :param start_number: the starting number for naming the split files.
    :return: the next available vocal number after splitting.
    """
    # load the wav file using pydub
    audio = AudioSegment.from_wav(input_wav)
    
    # calculate the total length of the audio in seconds
    total_length_sec = len(audio) / 1000  # pydub works in milliseconds
    
    # determine the number of chunks needed, add one if there's a remainder
    num_chunks = int(total_length_sec // chunk_length_sec) + (1 if total_length_sec % chunk_length_sec > 0 else 0)

    # ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # wait for 5 seconds to ensure directory is ready
    time.sleep(5)
    # initialize the current number for naming
    current_number = start_number

    # iterate over the number of chunks to create each segment
    for i in range(num_chunks):
        # calculate the start time in milliseconds
        start_ms = i * chunk_length_sec * 1000
        # calculate the end time in milliseconds
        end_ms = start_ms + chunk_length_sec * 1000
        # extract the audio segment from start to end
        chunk = audio[start_ms:end_ms]

        # define the output filename with sequential numbering
        output_filename = f'vocal{current_number}.wav'
        # create the full path for the output file
        output_path = os.path.join(output_dir, output_filename)

        # export the chunk as a wav file
        chunk.export(output_path, format='wav')
        # print a message indicating successful export
        print(f"Exported {output_filename}")

        # increment the vocal number for the next chunk
        current_number += 1

    # return the next available vocal number after splitting
    return current_number

# function to clean up temporary files
def clean_up(temp_dir):
    """
    removes the temporary directory used for processing each video.

    :param temp_dir: directory to be removed.
    """
    # check if the temporary directory exists
    if os.path.exists(temp_dir):
        try:
            # remove the temporary directory and all its contents
            shutil.rmtree(temp_dir)
            # print a message indicating successful cleanup
            print(f"Cleaned up temporary files in '{temp_dir}'.")
        except Exception as e:
            # print an error message if cleanup fails
            print(f"Failed to clean up temporary files: {e}")

# function to process a single youtube video
def process_youtube_video(youtube_url, split_output_dir, current_number):
    """
    processes a single youtube video: downloads audio, extracts vocals, splits into chunks.

    :param youtube_url: the youtube video url.
    :param split_output_dir: directory to save all split vocal files.
    :param current_number: the current vocal number to start naming from.
    :return: the updated current vocal number after processing.
    """
    # define the temporary directory for processing
    temp_dir = 'temp_processing'
    try:
        # create the temporary directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        # print a message indicating which url is being processed
        print(f"\nProcessing URL: {youtube_url}")

        # step 1: download audio
        print("  Downloading audio from YouTube...")
        # download the audio and get the path to the downloaded mp3
        downloaded_mp3 = download_audio(youtube_url, os.path.join(temp_dir, 'audio'))
        # print a message indicating successful download
        print("  Audio downloaded successfully.")
        # wait for 5 seconds
        time.sleep(5)
        
        # step 2: extract vocals using spleeter
        print("  Extracting vocals...")
        # extract the vocals and get the path to the vocals wav
        vocals_wav_path = extract_vocals(downloaded_mp3, os.path.join(temp_dir, 'vocals'))
        # print a message indicating where vocals are saved
        print(f"  Vocals extracted and saved to '{vocals_wav_path}'.")
        # wait for 5 seconds
        time.sleep(5)
        
        # step 3: split the wav file into 30-second segments with sequential naming
        print("  Splitting the WAV file into 30-second segments...")
        # split the wav file and update the current_number
        current_number = split_wav_file(vocals_wav_path, output_dir=split_output_dir, chunk_length_sec=30, start_number=current_number)
        # print a message indicating successful splitting
        print("  Splitting completed successfully.")

    except Exception as e:
        # get the error message
        error_message = str(e)
        # print an error message indicating what went wrong
        print(f"  An error occurred while processing {youtube_url}: {error_message}")
    finally:
        # clean up temporary files regardless of success or failure
        clean_up(temp_dir)

    # return the updated current number for the next vocal file
    return current_number

# main function to orchestrate the processing
def main():
    # define the directory to save split vocal files
    split_output_dir = 'split_vocals'
    # define the error log file
    error_log = 'error_log.txt'

    # prompt the user to enter a youtube url
    print("Enter a YouTube video URL:")
    youtube_url = input("URL: ").strip()

    # if no url was entered, print a message and exit
    if not youtube_url:
        print("No URL was entered. Exiting the program.")
        return

    # get the next available vocal number based on existing split vocal files
    current_number = get_next_vocal_number(split_output_dir)
    # print a message indicating where numbering starts
    print(f"Starting vocal numbering from {current_number}.")

    # process the youtube video and update the current_number
    current_number = process_youtube_video(youtube_url, split_output_dir, current_number)

    # after processing, print a summary message
    print("\nThe video has been processed.")
    print(f"All split vocal files are saved in the '{split_output_dir}' directory.")

# entry point of the script
if __name__ == "__main__":
    main()
