import wave
import os
import time
import threading
import numpy as np

RECORD_DIR = "recordings"

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames = []
        self.thread = None
        self.filepath = None
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(RECORD_DIR):
            os.makedirs(RECORD_DIR)

    def start_recording(self):
        try:
            import pyaudio
        except ImportError:
            print("[AudioRecorder] PyAudio no está instalado.")
            return

        self.is_recording = True
        self.frames = []
        filename = f"voice_note_{int(time.time())}.wav"
        self.filepath = os.path.join(RECORD_DIR, filename)

        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()

    def _record_loop(self):
        import pyaudio
        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )

            while self.is_recording:
                data = stream.read(1024, exception_on_overflow=False)
                self.frames.append(data)

            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"[AudioRecorder] Error durante grabación: {e}")
        finally:
            p.terminate()

    def stop_recording(self):
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=1.0)

        if self.frames and self.filepath:
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                
                raw_bytes = b''.join(self.frames)
                audio_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)

                # --- NORMALIZACIÓN DE PICOS LIMPIA SIN SATURACIÓN ---
                max_peak = np.max(np.abs(audio_data))
                
                if max_peak > 0:
                    # Target peak al 90% del límite de int16 (29490 de 32767)
                    target_peak = 29490.0
                    gain_factor = target_peak / max_peak
                    
                    # Limitar el factor máximo de ganancia a 4.0x para no amplificar demasiado el ruido blanco de fondo
                    gain_factor = min(gain_factor, 4.0)
                    
                    normalized_data = audio_data * gain_factor
                    int16_data = np.clip(normalized_data, -32768, 32767).astype(np.int16)
                else:
                    int16_data = audio_data.astype(np.int16)

                wf = wave.open(self.filepath, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(int16_data.tobytes())
                wf.close()
                return self.filepath
            except Exception as e:
                print(f"[AudioRecorder] Error al guardar archivo de audio: {e}")
                return None
        return None