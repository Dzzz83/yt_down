import os
import warnings
import csv
import time

# Set environment variables to suppress TensorFlow logs and disable GPU
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable GPU

# Now import logging and configure TensorFlow's logger
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# Suppress Python warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import yt_dlp
from spleeter.separator import Separator
from pydub import AudioSegment
import shutil
import glob

# ----------------------- Helper Functions -----------------------

def format_time(ms):
    """
    Format milliseconds to a string in HH:MM:SS format.

    :param ms: Time in milliseconds.
    :return: Formatted time string.
    """
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    seconds = seconds % 60
    minutes = minutes % 60
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

# Function to download audio
def download_audio(youtube_url, output_dir):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Define yt-dlp options for downloading the best audio
    ydl_opts = {
        'format': 'bestaudio/best',  # Download the best audio
        'outtmpl': os.path.join(output_dir, 'downloaded_audio.%(ext)s'), 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extract audio using ffmpeg
            'preferredcodec': 'mp3',      # Convert to mp3
            'preferredquality': '192',    # Set bitrate to 192 kbps
        }],
        'quiet': True,       # Suppress yt-dlp output
        'no_warnings': True, # Suppress yt-dlp warnings
    }

    # Initialize yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Download YouTube video using youtube_url
        ydl.download([youtube_url])

    # Construct the path to the downloaded mp3 file
    downloaded_mp3 = os.path.join(output_dir, 'downloaded_audio.mp3')

    # Check if the downloaded mp3 exists, raise error if not found
    if not os.path.exists(downloaded_mp3):
        raise FileNotFoundError(f"{downloaded_mp3} not found after download.")

    # Return the path to the downloaded mp3
    return downloaded_mp3

# Function to extract vocals from the audio using Spleeter
def extract_vocals(input_audio, output_dir):
    # Initialize Spleeter's separator with a 2-stem model (vocals and accompaniment)
    separator = Separator('spleeter:2stems')  # Splits into 2 stems: vocals and music

    # Perform the separation and store in the output directory
    separator.separate_to_file(input_audio, output_dir)

    # Wait until the vocals file is created or timeout
    vocals_wav_path = construct_vocals_path(input_audio, output_dir)
    wait_for_file(vocals_wav_path, timeout=30)

    # Check if the vocals wav file exists, raise error if not found
    if not os.path.exists(vocals_wav_path):
        raise FileNotFoundError(f"Vocals WAV file not found at {vocals_wav_path}.")

    # Return the path to the extracted vocals wav file
    return vocals_wav_path

# Helper function to construct the vocals wav path
def construct_vocals_path(input_audio, output_dir):
    base_filename = os.path.splitext(os.path.basename(input_audio))[0]
    vocals_wav_path = os.path.join(output_dir, base_filename, 'vocals.wav')
    return vocals_wav_path

# Function to wait for a file to exist
def wait_for_file(filepath, timeout=30):
    """Wait until a file exists or timeout is reached."""
    start_time = time.time()
    while not os.path.exists(filepath):
        if time.time() - start_time > timeout:
            raise TimeoutError(f"File {filepath} not found within {timeout} seconds.")
        time.sleep(0.5)

# Function to determine the next vocal file number based on existing files
def get_next_vocal_number(output_dir='split_vocals'):
    """
    Determines the next vocal file number based on existing files in the output directory.

    :param output_dir: Directory where split vocal files are saved.
    :return: The next available vocal number as an integer.
    """
    # Check if the output directory exists, create it if not
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        return 1  # Start from 1 if directory does not exist

    # Find all files in the output directory that match the pattern 'vocal*.wav'
    existing_files = glob.glob(os.path.join(output_dir, 'vocal*.wav'))
    
    # Initialize the maximum number found to 0
    max_number = 0
    
    # Iterate over each existing file to find the highest vocal number
    for file in existing_files:
        # Get the base name of the file (e.g., 'vocal12.wav')
        basename = os.path.basename(file)
        
        # Split the base name into name and extension (e.g., ('vocal12', '.wav'))
        name, _ = os.path.splitext(basename)
        
        # Extract the numeric part from the name (e.g., '12' from 'vocal12')
        number_part = ''.join(filter(str.isdigit, name))
        
        # Check if the extracted part is a digit
        if number_part.isdigit():
            # Convert the numeric string to an integer
            number = int(number_part)
            
            # Update max_number if the current number is greater
            if number > max_number:
                max_number = number
                
    # Return the next available number by adding 1 to the max found
    return max_number + 1

# Function to split a wav file into multiple chunks of specified length
def split_wav_file(input_wav, output_dir='split_vocals', chunk_length_sec=5, start_number=1):
    """
    Splits a wav file into multiple chunks of specified length with sequential naming.
    Also records the time range of each chunk in a separate CSV file.

    :param input_wav: Path to the input wav file.
    :param output_dir: Directory where split files will be saved.
    :param chunk_length_sec: Length of each chunk in seconds.
    :param start_number: The starting number for naming the split files.
    :return: The next available vocal number after splitting.
    """
    # Load the wav file using pydub
    audio = AudioSegment.from_wav(input_wav)
    
    # Calculate the total length of the audio in milliseconds
    total_length_ms = len(audio)  # pydub works in milliseconds
    
    # Determine the number of chunks needed, add one if there's a remainder
    num_chunks = int(total_length_ms // (chunk_length_sec * 1000)) + (1 if total_length_ms % (chunk_length_sec * 1000) > 0 else 0)

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # Wait for 5 seconds to ensure directory is ready
    time.sleep(5)
    # Initialize the current number for naming
    current_number = start_number

    # Define the CSV file path
    csv_file_path = os.path.join(output_dir, 'time_ranges.csv')
    
    # Check if the CSV file exists to determine if headers are needed
    file_exists = os.path.isfile(csv_file_path)
    
    with open(csv_file_path, 'a', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        
        # Write headers if the file does not exist
        if not file_exists:
            csv_writer.writerow(['Filename', 'Start Time', 'End Time'])
        
        # Iterate over the number of chunks to create each segment
        for i in range(num_chunks):
            # Calculate the start time in milliseconds
            start_ms = i * chunk_length_sec * 1000
            # Calculate the end time in milliseconds
            end_ms = start_ms + chunk_length_sec * 1000
            # Ensure the end time does not exceed the total length
            end_ms = min(end_ms, total_length_ms)
            # Extract the audio segment from start to end
            chunk = audio[start_ms:end_ms]

            # Format the start and end times
            start_time_str = format_time(start_ms)
            end_time_str = format_time(end_ms)

            # Define the output filename with sequential numbering
            output_filename = f'vocal{current_number}.wav'
            # Create the full path for the output file
            output_path = os.path.join(output_dir, output_filename)

            # Export the chunk as a wav file
            chunk.export(output_path, format='wav')
            # Print a message indicating successful export
            print(f"Exported {output_filename} (from {start_time_str} to {end_time_str})")

            # Write the row to the CSV file
            csv_writer.writerow([output_filename, start_time_str, end_time_str])

            # Increment the vocal number for the next chunk
            current_number += 1

    # Return the next available vocal number after splitting
    return current_number

# Function to clean up temporary files
def clean_up(temp_dir):
    """
    Removes the temporary directory used for processing each video.

    :param temp_dir: Directory to be removed.
    """
    # Check if the temporary directory exists
    if os.path.exists(temp_dir):
        try:
            # Remove the temporary directory and all its contents
            shutil.rmtree(temp_dir)
            # Print a message indicating successful cleanup
            print(f"Cleaned up temporary files in '{temp_dir}'.")
        except Exception as e:
            # Print an error message if cleanup fails
            print(f"Failed to clean up temporary files: {e}")

# Function to process a single YouTube video
def process_youtube_video(youtube_url, split_output_dir, current_number):
    """
    Processes a single YouTube video: downloads audio, extracts vocals, splits into chunks.

    :param youtube_url: The YouTube video URL.
    :param split_output_dir: Directory to save all split vocal files.
    :param current_number: The current vocal number to start naming from.
    :return: The updated current vocal number after processing.
    """
    # Define the temporary directory for processing
    temp_dir = 'temp_processing'
    try:
        # Create the temporary directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        # Print a message indicating which URL is being processed
        print(f"\nProcessing URL: {youtube_url}")

        # Step 1: Download audio
        print("  Downloading audio from YouTube...")
        # Download the audio and get the path to the downloaded mp3
        downloaded_mp3 = download_audio(youtube_url, os.path.join(temp_dir, 'audio'))
        # Print a message indicating successful download
        print("  Audio downloaded successfully.")
        # Wait for 5 seconds
        time.sleep(5)
        
        # Step 2: Extract vocals using Spleeter
        print("  Extracting vocals...")
        # Extract the vocals and get the path to the vocals wav
        vocals_wav_path = extract_vocals(downloaded_mp3, os.path.join(temp_dir, 'vocals'))
        # Print a message indicating where vocals are saved
        print(f"  Vocals extracted and saved to '{vocals_wav_path}'.")
        # Wait for 5 seconds
        time.sleep(5)
        
        # Step 3: Split the wav file into 5-second segments with sequential naming
        print("  Splitting the WAV file into 5-second segments...")
        # Split the wav file and update the current_number
        current_number = split_wav_file(vocals_wav_path, output_dir=split_output_dir, chunk_length_sec=5, start_number=current_number)
        # Print a message indicating successful splitting
        print("  Splitting completed successfully.")

    except Exception as e:
        # Get the error message
        error_message = str(e)
        # Print an error message indicating what went wrong
        print(f"  An error occurred while processing {youtube_url}: {error_message}")
    finally:
        # Clean up temporary files regardless of success or failure
        clean_up(temp_dir)

    # Return the updated current number for the next vocal file
    return current_number

# Main function to orchestrate the processing
def main():
    # Define the directory to save split vocal files
    split_output_dir = 'split_vocals1'
    # Define the error log file (optional, since logging is configured)
    error_log = 'error_log.txt'

    # Prompt the user to enter a YouTube URL
    print("Enter a YouTube video URL:")
    youtube_url = input("URL: ").strip()

    # If no URL was entered, print a message and exit
    if not youtube_url:
        print("No URL was entered. Exiting the program.")
        return

    # Get the next available vocal number based on existing split vocal files   
    current_number = get_next_vocal_number(split_output_dir)
    # Print a message indicating where numbering starts
    print(f"Starting vocal numbering from {current_number}.")

    # Process the YouTube video and update the current_number
    current_number = process_youtube_video(youtube_url, split_output_dir, current_number)

    # After processing, print a summary message
    print("\nThe video has been processed.")
    print(f"All split vocal files are saved in the '{split_output_dir}' directory.")
    print(f"Time ranges for each file are recorded in '{os.path.join(split_output_dir, 'time_ranges.csv')}'.")
    print("CSV file includes the following columns: Filename, Start Time, End Time.")

# Entry point of the script
if __name__ == "__main__":
    main()
