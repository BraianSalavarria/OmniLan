import customtkinter as ctk
import os

class VoiceCallEngine:
    """Motor y ventana independiente para llamadas de voz (Solo Audio)"""
    def __init__(self):
        self.window = None
        self.call_seconds = 0
        self.timer_job = None
        self.is_muted = False
        self.on_hangup = None
        self.on_toggle_mute = None

    def start_call(self, parent, remote_name, remote_ip, on_hangup_callback=None, on_toggle_mute_callback=None):
        self.stop_call()
        self.on_hangup = on_hangup_callback
        self.on_toggle_mute = on_toggle_mute_callback
        self.call_seconds = 0
        self.is_muted = False

        self.window = ctk.CTkToplevel(parent)
        self.window.title(f"Llamada de Voz - {remote_name}")
        self.geometry = self.window.geometry("380x280")
        self.window.resizable(False, False)
        self.window.configure(fg_color="#0B121C")

        ico_path = os.path.join("assets", "ico", "omnilan.ico")
        if os.path.exists(ico_path):
            try:
                self.window.iconbitmap(ico_path)
            except Exception:
                pass

        self.window.transient(parent)

        avatar_frame = ctk.CTkFrame(self.window, width=70, height=70, corner_radius=35, fg_color="#202B36")
        avatar_frame.pack(pady=(25, 10))
        avatar_frame.pack_propagate(False)

        avatar_label = ctk.CTkLabel(avatar_frame, text="📞", font=ctk.CTkFont(size=30))
        avatar_label.pack(expand=True)

        self.name_label = ctk.CTkLabel(
            self.window,
            text=remote_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#D3DDE5"
        )
        self.name_label.pack(pady=2)

        self.status_label = ctk.CTkLabel(
            self.window,
            text="Iniciando llamada...",
            font=ctk.CTkFont(size=12),
            text_color="#7CEAF5"
        )
        self.status_label.pack(pady=2)

        ctrl_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        ctrl_frame.pack(pady=20)

        self.mute_btn = ctk.CTkButton(
            ctrl_frame,
            text="🎙️ Mute",
            width=100,
            fg_color="#202B36",
            hover_color="#3A4A58",
            text_color="#D3DDE5",
            command=self._toggle_mute
        )
        self.mute_btn.pack(side="left", padx=10)

        self.hangup_btn = ctk.CTkButton(
            ctrl_frame,
            text="Colgar 📞",
            width=110,
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="white",
            font=ctk.CTkFont(weight="bold"),
            command=self._hangup
        )
        self.hangup_btn.pack(side="left", padx=10)

        self.window.protocol("WM_DELETE_WINDOW", self._hangup)

    def set_status(self, status_text):
        if self.window and self.window.winfo_exists() and hasattr(self, 'status_label') and self.status_label.winfo_exists():
            try:
                self.status_label.configure(text=status_text)
                if status_text == "Conectado":
                    self.status_label.configure(text_color="#72EAB6")
                    self._start_timer()
            except Exception:
                pass

    def _start_timer(self):
        if not self.timer_job and self.window and self.window.winfo_exists():
            self._update_timer()

    def _update_timer(self):
        if self.window and self.window.winfo_exists():
            mins = self.call_seconds // 60
            secs = self.call_seconds % 60
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                try:
                    self.status_label.configure(text=f"En llamada: {mins:02d}:{secs:02d}")
                except Exception:
                    pass
            self.call_seconds += 1
            self.timer_job = self.window.after(1000, self._update_timer)

    def _toggle_mute(self):
        if self.on_toggle_mute:
            self.is_muted = self.on_toggle_mute()
            if self.window and self.window.winfo_exists() and hasattr(self, 'mute_btn') and self.mute_btn.winfo_exists():
                if self.is_muted:
                    self.mute_btn.configure(fg_color="#EF4444", hover_color="#DC2626", text="🔇 Muted")
                else:
                    self.mute_btn.configure(fg_color="#202B36", hover_color="#3A4A58", text="🎙 Mute")

    def _hangup(self):
        if self.on_hangup:
            cb = self.on_hangup
            self.on_hangup = None
            cb()

    def stop_call(self):
        if self.timer_job and self.window:
            try:
                self.window.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

        if self.window:
            try:
                if self.window.winfo_exists():
                    self.window.destroy()
            except Exception:
                pass
            self.window = None