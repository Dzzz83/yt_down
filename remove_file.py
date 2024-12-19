import os
import wave
import contextlib
import sys
import shutil

def get_wav_duration(filepath):
    """
    Returns the duration of a WAV file in seconds.
    """
    try:
        with contextlib.closing(wave.open(filepath, 'r')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return duration
    except wave.Error as e:
        print(f"Error reading {filepath}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error with {filepath}: {e}")
        return None

def process_wav_files(source_directory, min_duration=30, final_folder_path=r"C:\Users\phatt\OneDrive\Desktop\code\yt_down\final"):
    """
    Processes WAV files in the source directory:
    - Deletes files shorter than min_duration seconds.
    - Moves and renames files equal to or longer than min_duration seconds to the final folder.
    
    Parameters:
    - source_directory (str): The path to the directory to scan.
    - min_duration (float): The threshold duration in seconds.
    - final_folder_path (str): The fixed path to the folder where qualifying WAV files will be moved.
    """
    if not os.path.isdir(source_directory):
        print(f"The specified path '{source_directory}' is not a directory or does not exist.")
        sys.exit(1)
    
    # Create the final folder if it doesn't exist
    os.makedirs(final_folder_path, exist_ok=True)
    
    # Initialize a counter for renaming
    vocal_counter = 1
    
    # Iterate over files in the source directory
    for root, dirs, files in os.walk(source_directory):
        # Avoid processing files in the final folder
        if os.path.abspath(root) == os.path.abspath(final_folder_path):
            continue
        
        for file in files:
            if file.lower().endswith('.wav'):
                filepath = os.path.join(root, file)
                duration = get_wav_duration(filepath)
                
                if duration is None:
                    print(f"Skipping file due to read error: {filepath}")
                    continue
                
                if duration < min_duration or duration > min_duration:
                    # Delete the file
                    try:
                        os.remove(filepath)
                        print(f"Deleted: {filepath} (Duration: {duration:.2f} seconds)")
                    except Exception as e:
                        print(f"Failed to delete {filepath}: {e}")
                else:
                    # Define the new filename
                    new_filename = f"vocal{vocal_counter}.wav"
                    new_filepath = os.path.join(final_folder_path, new_filename)
                    
                    # Ensure the new filename does not already exist
                    while os.path.exists(new_filepath):
                        vocal_counter += 1
                        new_filename = f"vocal{vocal_counter}.wav"
                        new_filepath = os.path.join(final_folder_path, new_filename)
                    
                    try:
                        shutil.move(filepath, new_filepath)
                        print(f"Moved and renamed: {filepath} --> {new_filepath} (Duration: {duration:.2f} seconds)")
                        vocal_counter += 1
                    except Exception as e:
                        print(f"Failed to move {filepath}: {e}")
    
    print("\nOperation Completed.")
    print(f"All WAV files shorter than or longer than {min_duration} seconds have been deleted.")
    print(f"All WAV files equal to {min_duration} seconds have been moved to '{final_folder_path}' and renamed accordingly.")

def main():
    # Prompt the user for the source directory path
    source_directory = input("Enter the path to the directory to scan: ").strip()
    
    if not source_directory:
        print("No directory path provided. Exiting.")
        sys.exit(1)
    
    # Prompt the user for the minimum duration
    min_duration = 30.0
    
    # Define the fixed final folder path
    final_folder_path = r"C:\Users\phatt\OneDrive\Desktop\code\yt_down\final1"
    
    # Call the function with the fixed final folder path
    process_wav_files(source_directory, min_duration, final_folder_path)

if __name__ == "__main__":
    main()
