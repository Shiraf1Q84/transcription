

import streamlit as st
import os
import openai
import moviepy.editor as mp
from pydub import AudioSegment
from dotenv import load_dotenv
import tempfile

# Initialize the OpenAI API
def get_api():
    user_api_key = st.sidebar.text_input(
        label="OpenAI API key",
        placeholder="Paste your openAI API key here",
        type="password"
    )
    return user_api_key

# Function to convert MP4 to MP3
def convert_mp4_to_mp3(mp4_file_path):
    mp3_file_path = os.path.splitext(mp4_file_path)[0] + '.mp3'
    audio = mp.AudioFileClip(mp4_file_path)
    audio.write_audiofile(mp3_file_path)
    return mp3_file_path


def transcribe_audio(mp3_file_path, api_key):
    try:
        openai.api_key = api_key  # Set the API key

        with open(mp3_file_path, 'rb') as audio_file:
            transcript = openai.Audio.transcribe("whisper-1",audio_file 
            # You can uncomment this line if needed
            )

        return transcript['text']
    except Exception as e:
        # Handle exceptions, e.g., print an error message
        print(f"Error in transcribe_audio: {str(e)}")
        return None  # Return None or an appropriate error message


# Function to split an MP3 file into chunks
def split_audio(mp3_file_path, interval_ms, output_folder):
    audio = AudioSegment.from_file(mp3_file_path)
    file_name, ext = os.path.splitext(os.path.basename(mp3_file_path))
    mp3_file_path_list = []
    n_splits = len(audio) // interval_ms
    for i in range(n_splits + 1):
        start = i * interval_ms
        end = (i + 1) * interval_ms
        split = audio[start:end]
        output_file_name = os.path.join(output_folder, f"{file_name}_{i}.mp3")
        split.export(output_file_name, format="mp3")
        mp3_file_path_list.append(output_file_name)
    return mp3_file_path_list

# Function to summarize transcription by chunk using ChatGPT
def summarize_transcription(transcription_list, mp3_file_path):
    pre_summary = ""
    for transcription_part in transcription_list:
        if transcription_part is not None:
            prompt = """
            あなたは、プロの要約作成者です。
            以下の制約条件、内容を元に要点をまとめてください.

            # 制約条件
            ・要点をまとめ、簡潔に書いて下さい.
            ・誤字・脱字があるため、話の内容を予測して置き換えてください.

            # 内容
            """ + transcription_part

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.0,
            )

            pre_summary += response['choices'][0]['message']['content']

    output_file_path = os.path.splitext(mp3_file_path)[0] + '_transcription.txt'

    return pre_summary, output_file_path
# Function to create minutes using ChatGPT
def create_minutes(transcription_list):
    prompt = """
    あなたは、プロの議事録作成者です。
    以下の制約条件、内容を元に要点をまとめ、議事録を作成してください.

    # 制約条件
    ・要点をまとめ、簡潔に書いて下さい.
    ・誤字・脱字があるため、話の内容を予測して置き換えてください.
    ・見やすいフォーマットにしてください.

    # 内容
    """ + "\n".join(transcription_list)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.0,
    )

    minutes = response['choices'][0]['message']['content']
    return minutes

# Streamlit App
def main():
    st.title("Video to Minutes Converter")

    # Set API Key
    user_api_key = get_api()

    # Upload a video file
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4"])

    if uploaded_file:
        st.sidebar.info("Processing... Please wait.")

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = temp_dir
            mp4_file_path = os.path.join(temp_dir_path, "uploaded.mp4")
            uploaded_file.seek(0)
            with open(mp4_file_path, "wb") as f:
                f.write(uploaded_file.read())

            # Convert MP4 to MP3
            st.sidebar.text("Converting video to audio...")
            mp3_file_path = convert_mp4_to_mp3(mp4_file_path)

            # Split audio into chunks
            st.sidebar.text("Splitting audio into chunks...")
            interval_ms = 480_000  # 60秒 = 60,000ミリ秒
            mp3_file_path_list = split_audio(mp3_file_path, interval_ms, temp_dir_path)

            # Transcribe and summarize
            st.sidebar.text("Transcribing and summarizing...")
            transcription_list = [transcribe_audio(mp3_file,user_api_key) for mp3_file in mp3_file_path_list]
            minutes, _ = summarize_transcription(transcription_list, mp3_file_path)

            st.sidebar.text("Processing complete!")

            # Display minutes
            st.subheader("Generated Minutes")
            st.write(minutes)

            # Copy the script button
            st.button("Copy the Script")

            # Download minutes button
            st.download_button(
                "Download Minutes",
                minutes.encode("utf-8"),
                file_name="minutes.txt",
                key="download-button",
            )

if __name__ == "__main__":
    main()