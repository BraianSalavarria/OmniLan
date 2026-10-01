import socket
import threading
import numpy as np

SEND_AUDIO_PORT = 50003
RECV_AUDIO_PORT = 50004
CHUNK = 1024
RATE = 16000
CHANNELS = 1

class AudioEngine:
    """Motor de audio con amplificación de salida potente y respuesta dinámica"""
    def __init__(self):
        self.is_streaming = False
        self.is_muted = False
        self.target_ip = None
        self.mic_gain = 1.0
        self.master_volume = 1.0
        self.p = None
        self.input_stream = None
        self.output_stream = None
        self.send_sock = None
        self.recv_sock = None

    def update_volumes(self, mic_gain, master_volume):
        """Permite actualizar volúmenes en caliente durante la llamada"""
        self.mic_gain = float(mic_gain)
        self.master_volume = float(master_volume)

    def start_audio_call(self, target_ip, mic_gain=1.0, master_volume=1.0):
        self.stop_audio_call()
        self.target_ip = target_ip
        self.mic_gain = float(mic_gain)
        self.master_volume = float(master_volume)
        self.is_streaming = True
        self.is_muted = False

        threading.Thread(target=self._init_audio_streams, daemon=True).start()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        return self.is_muted

    def _init_audio_streams(self):
        try:
            import pyaudio
        except ImportError:
            return

        try:
            self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.recv_sock.bind(('', RECV_AUDIO_PORT))
            self.recv_sock.settimeout(0.5)

            self.p = pyaudio.PyAudio()

            # Entrada Micrófono
            def in_callback(in_data, frame_count, time_info, status):
                if self.is_streaming and not self.is_muted and self.target_ip and self.send_sock:
                    try:
                        if in_data:
                            audio_data = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
                            scale = self.mic_gain * 3.0
                            amplified = np.clip(audio_data * scale, -32768, 32767).astype(np.int16)
                            out_bytes = amplified.tobytes()
                        else:
                            out_bytes = in_data

                        self.send_sock.sendto(out_bytes, (self.target_ip, RECV_AUDIO_PORT))
                    except Exception:
                        pass
                return (None, pyaudio.paContinue)

            try:
                self.input_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=in_callback
                )
                self.input_stream.start_stream()
            except Exception as e:
                print(f"[AudioEngine] No se pudo abrir micrófono: {e}")

            # Salida Altavoces (Master Volume Amplificado hasta 5x)
            def out_callback(in_data, frame_count, time_info, status):
                data = b'\x00' * (frame_count * 2)
                if self.is_streaming and self.recv_sock:
                    try:
                        raw_data, _ = self.recv_sock.recvfrom(frame_count * 2)
                        if raw_data:
                            audio_data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
                            scale = self.master_volume * 5.0
                            adjusted = np.clip(audio_data * scale, -32768, 32767).astype(np.int16)
                            data = adjusted.tobytes()
                    except Exception:
                        pass
                return (data, pyaudio.paContinue)

            try:
                self.output_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=out_callback
                )
                self.output_stream.start_stream()
            except Exception as e:
                print(f"[AudioEngine] No se pudo abrir altavoces: {e}")

        except Exception as e:
            print(f"[AudioEngine] Error al iniciar streams: {e}")

    def stop_audio_call(self):
        self.is_streaming = False
        self.target_ip = None

        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception:
                pass
            self.input_stream = None

        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception:
                pass
            self.output_stream = None

        if self.p:
            try:
                self.p.terminate()
            except Exception:
                pass
            self.p = None

        if self.send_sock:
            try:
                self.send_sock.close()
            except Exception:
                pass
            self.send_sock = None

        if self.recv_sock:
            try:
                self.recv_sock.close()
            except Exception:
                pass
            self.recv_sock = None