import argparse
import os
import numpy as np
import speech_recognition as sr
import whisper
import torch
import requests
import subprocess
import signal
import sys

from datetime import datetime, timedelta
from queue import Queue
from time import sleep
from sys import platform


OLLAMA_MODEL = "phi3:latest"
OLLAMA_SYSTEM = "You are a helpful ai assistant named Echo. Please always keep your answers as concise as possible unless explicitly asked by the user."
WHISPER_MODEL = "base.en"  # available models: tiny, base, medium, large


def send_to_ollama(prompt: str):
    url = "http://localhost:11434/api/generate"
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": OLLAMA_MODEL,
        "system": OLLAMA_SYSTEM,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # err handling
        result = response.json()
        print(f"[OLLAMA]: {result['response']}")
    except requests.exceptions.RequestException as e:
        print(f"[ECHO]: Error sending to Ollama: {e}")


def start_ollama():
    """Start the Ollama process in the background."""
    ollama_process = subprocess.Popen(
        ["ollama", "serve"], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    return ollama_process


def stop_ollama(ollama_process):
    """Stop the Ollama process."""
    if ollama_process:
        os.kill(ollama_process.pid, signal.SIGTERM)


def main():
    phrase_time = None
    data_queue = Queue()
    recorder = sr.Recognizer()
    recorder.energy_threshold = 100
    recorder.dynamic_energy_threshold = False

    # Start Ollama process
    ollama_process = start_ollama()
    print(f"[ECHO]: Successfully started ollama")

    if 'linux' in platform:
        mic_name = "pulse"
        if not mic_name or mic_name == 'list':
            print("[ECHO]: Available microphone devices are: ")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"[ECHO]: Microphone with name \"{name}\" found")
            return
        else:
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                if mic_name in name:
                    source = sr.Microphone(sample_rate=16000, device_index=index)
                    break
    else:
        source = sr.Microphone(sample_rate=16000)

    audio_model = whisper.load_model(WHISPER_MODEL)

    record_timeout = 5
    phrase_timeout = 10

    transcription = ['']

    with source:
        recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio: sr.AudioData) -> None:
        data = audio.get_raw_data()
        data_queue.put(data)

    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

    print(f"[ECHO]: voice model loaded (WHISPER-{WHISPER_MODEL})")
    print(f"[ECHO]: using language model {OLLAMA_MODEL}\n")
    try:
        while True:
            now = datetime.now()
            if not data_queue.empty():
                phrase_complete = False
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    phrase_complete = True
                phrase_time = now
                
                audio_data = b''.join(data_queue.queue)
                data_queue.queue.clear()
                
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
                text = result['text'].strip()

                if phrase_complete:
                    transcription.append(text)
                else:
                    transcription[-1] = text

                for line in transcription:
                    print(f"[PROMPT]: {line}")
                print('', end='', flush=True)
                # send current transcription to ollama
                send_to_ollama(text)
            else:
                sleep(0.15)
    except KeyboardInterrupt:
        pass
    finally:
        # stop ollama
        stop_ollama(ollama_process)
        print(f"\n[ECHO]: Stopped ollama")


if __name__ == "__main__":
    main()
