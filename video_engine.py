import cv2
import numpy as np
import threading
import socket
import time
import customtkinter as ctk
from PIL import Image

VIDEO_PORT = 50002
BUFFER_SIZE = 65536


class VideoCallWindow(ctk.CTkToplevel):
    """Ventana de videollamada con vista previa doble garantizada (Remota + Local) y controles de audio"""
    def __init__(self, parent, remote_name, on_hangup, on_toggle_mute=None):
        super().__init__(parent)
        self.title(f"Videollamada con {remote_name}")
        self.geometry("720x600")
        self.minsize(580, 450)
        self.on_hangup = on_hangup
        self.on_toggle_mute = on_toggle_mute

        self.transient(parent)

        # 1. Panel Inferior (SIEMPRE VISIBLE ABAJO): Mi Cámara + Botones Control
        controls = ctk.CTkFrame(self, fg_color="#111827", height=130)
        controls.pack(side="bottom", fill="x", padx=10, pady=10)

        # Miniatura de Mi Cámara (Local)
        self.local_video_label = ctk.CTkLabel(
            controls,
            text="Mi camara",
            width=160,
            height=110,
            fg_color="#1F2937",
            corner_radius=8
        )
        self.local_video_label.pack(side="left", padx=10, pady=10)

        # Botón Mute / Unmute Micrófono
        self.mute_btn = ctk.CTkButton(
            controls,
            text="🎙️ Mic On",
            fg_color="#3B82F6",
            hover_color="#2563EB",
            width=110,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._toggle_mute
        )
        self.mute_btn.pack(side="right", padx=(5, 15), pady=10)

        # Botón Cortar
        ctk.CTkButton(
            controls,
            text="🔴 Cortar Llamada",
            fg_color="#EF4444",
            hover_color="#DC2626",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._hangup
        ).pack(side="right", padx=5, pady=10)

        # 2. Frame de Video Principal (Remoto)
        self.main_container = ctk.CTkFrame(self, fg_color="black")
        self.main_container.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))

        self.remote_video_label = ctk.CTkLabel(
            self.main_container,
            text="Conectando camara...",
            fg_color="black"
        )
        self.remote_video_label.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._hangup)

    def _toggle_mute(self):
        if self.on_toggle_mute:
            is_muted = self.on_toggle_mute()
            if is_muted:
                self.mute_btn.configure(text="🔇 Mute", fg_color="#6B7280", hover_color="#4B5563")
            else:
                self.mute_btn.configure(text="🎙️ Mic On", fg_color="#3B82F6", hover_color="#2563EB")

    def update_remote_frame(self, pil_img):
        try:
            if self.winfo_exists():
                w = max(self.remote_video_label.winfo_width(), 400)
                h = max(self.remote_video_label.winfo_height(), 300)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(w, h))
                self.remote_video_label.configure(image=ctk_img, text="")
        except Exception:
            pass

    def update_local_frame(self, pil_img):
        try:
            if self.winfo_exists():
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 110))
                self.local_video_label.configure(image=ctk_img, text="")
        except Exception:
            pass

    def set_status(self, text):
        try:
            if self.winfo_exists():
                self.remote_video_label.configure(image="", text=text)
        except Exception:
            pass

    def _hangup(self):
        cb = self.on_hangup
        try:
            self.withdraw()
            self.after(100, self.destroy)
        except Exception:
            pass
        if cb:
            cb()


class VideoEngine:
    """Motor para captura, envío y recepción bidireccional de video"""
    def __init__(self):
        self.is_streaming = False
        self.target_ip = None
        self.window = None

    def _get_working_camera(self):
        for idx in [0, 1, 2, -1]:
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        return cap
                    cap.release()
            except Exception:
                pass
        return None

    def start_call(self, parent_widget, remote_name, target_ip, on_hangup_callback, on_toggle_mute_callback=None):
        self.target_ip = target_ip
        self.is_streaming = True

        self.window = VideoCallWindow(
            parent_widget,
            remote_name,
            on_hangup=on_hangup_callback,
            on_toggle_mute=on_toggle_mute_callback
        )

        threading.Thread(target=self._sender_thread, daemon=True).start()
        threading.Thread(target=self._receiver_thread, daemon=True).start()

    def set_status(self, status_text):
        if self.window:
            self.window.set_status(status_text)

    def stop_call(self):
        self.is_streaming = False
        self.target_ip = None
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None

    def _sender_thread(self):
        cap = self._get_working_camera()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while self.is_streaming:
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    rgb_local = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_local = Image.fromarray(rgb_local)
                    if self.window:
                        self.window.after(0, lambda img=pil_local: self.window.update_local_frame(img) if self.window else None)

                    if self.target_ip:
                        frame_resized = cv2.resize(frame, (480, 360))
                        _, buffer = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 45])
                        data = buffer.tobytes()

                        if len(data) < 60000:
                            try:
                                sock.sendto(data, (self.target_ip, VIDEO_PORT))
                            except Exception:
                                pass
            else:
                blank = np.zeros((360, 480, 3), dtype=np.uint8)
                cv2.putText(blank, "Sin Camara Detectada", (80, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                pil_blank = Image.fromarray(blank)
                if self.window:
                    self.window.after(0, lambda img=pil_blank: self.window.update_local_frame(img) if self.window else None)

            time.sleep(0.033)

        if cap:
            cap.release()
        sock.close()

    def _receiver_thread(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('', VIDEO_PORT))
        except Exception:
            return

        while self.is_streaming:
            try:
                sock.settimeout(1.0)
                data, _ = sock.recvfrom(BUFFER_SIZE)
                if data and self.window:
                    np_arr = np.frombuffer(data, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb_frame)
                        self.window.after(0, lambda img=pil_img: self.window.update_remote_frame(img) if self.window else None)
            except Exception:
                pass

        sock.close()