import customtkinter as ctk
import os
import pygame
import time
import sys
from PIL import Image, ImageDraw

if sys.platform == "win32":
    try:
        import ctypes
        myappid = "omnilan.p2p.chat.v1.0.3"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"[OmniLan] No se pudo establecer AppUserModelID: {e}")

from config_manager import ConfigManager
from network_engine import NetworkEngine
from ui_components import SetupDialog, SettingsDialog, IncomingCallDialog, AudioPlayerWidget, ChatDisplay
from notification_manager import SystemTrayManager
from audio_recorder import AudioRecorder
from video_engine import VideoEngine
from voice_call_engine import VoiceCallEngine
from audio_engine import AudioEngine

ctk.set_appearance_mode("Dark")


def crop_to_circle(pil_img, size=(38, 38)):
    """Recorta una imagen PIL dentro de un círculo perfecto transparente."""
    pil_img = pil_img.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)

    transparent_bg = Image.new('RGBA', size, (0, 0, 0, 0))
    circle_img = Image.composite(pil_img, transparent_bg, mask)
    return circle_img


class LANChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OmniLan - Red Local P2P")
        self.geometry("850x550")
        self.minsize(700, 450)
        self.configure(fg_color="#0B121C")

        ico_path = os.path.join("assets", "ico", "omnilan.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception as e:
                print(f"[OmniLan] No se pudo cargar el icono .ico: {e}")

        try:
            pygame.mixer.init()
        except Exception:
            pass

        self.config_mgr = ConfigManager()
        self.recorder = AudioRecorder()
        self.video_engine = VideoEngine()
        self.voice_engine = VoiceCallEngine()
        self.audio_engine = AudioEngine()

        self.selected_user_ip = None
        self.user_widgets = {}
        self.chat_histories = {}
        self.unread_counts = {}
        self.previous_users_count = None

        self.last_typing_time = 0
        self.is_currently_typing = False
        self.is_recording_audio = False

        self.current_call_ip = None
        self.is_current_call_video = False
        self.incoming_call_dialog = None
        self.call_sound_channel = None

        self._build_ui()

        self.tray_mgr = SystemTrayManager(
            on_show_window=self._restore_from_tray,
            on_quit=self._force_quit
        )
        self.tray_mgr.start()

        if not self.config_mgr.is_configured():
            self.withdraw()
            SetupDialog(self, on_save=self._on_first_setup_complete)
        else:
            self._start_network()

    def _on_first_setup_complete(self, fn, ln):
        self.config_mgr.config["first_name"] = fn
        self.config_mgr.config["last_name"] = ln
        self.config_mgr.save_config()
        self.deiconify()
        self._start_network()

    def _start_network(self):
        self.network = NetworkEngine(
            get_user_info_callback=self._get_my_info,
            on_user_list_changed=self._update_user_list_ui,
            on_message_received=self._on_message_received,
            on_typing_status_changed=self._on_typing_status_changed,
            on_call_event=self._on_call_event
        )

    def _get_my_info(self):
        fn = self.config_mgr.config.get("first_name", "")
        ln = self.config_mgr.config.get("last_name", "")
        return {
            "full_name": f"{fn} {ln}".strip(),
            "initials": self.config_mgr.get_initials(),
            "avatar": self.config_mgr.config.get("avatar_filename", "")
        }

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1, minsize=230)
        self.grid_columnconfigure(1, weight=3, minsize=450)
        self.grid_rowconfigure(0, weight=1)

        self.left_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#151E29",
            border_color="#3A4A58",
            border_width=1
        )
        self.left_frame.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="nsew"
        )

        top_left = ctk.CTkFrame(
            self.left_frame,
            fg_color="transparent"
        )
        top_left.pack(
            fill="x",
            padx=10,
            pady=10
        )

        ctk.CTkLabel(
            top_left,
            text="Usuarios Conectados",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#7CEAF5"
        ).pack(side="left")

        ctk.CTkButton(
            top_left,
            text="⚙",
            width=32,
            height=32,
            fg_color="#202B36",
            hover_color="#3A4A58",
            text_color="#D3DDE5",
            command=self._open_settings
        ).pack(side="right")

        self.users_scroll = ctk.CTkScrollableFrame(
            self.left_frame,
            fg_color="transparent"
        )
        self.users_scroll.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        self.right_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#151E29",
            border_color="#3A4A58",
            border_width=1
        )
        self.right_frame.grid(
            row=0,
            column=1,
            padx=(0, 10),
            pady=10,
            sticky="nsew"
        )

        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.chat_header = ctk.CTkFrame(
            self.right_frame,
            fg_color="transparent"
        )
        self.chat_header.grid(
            row=0,
            column=0,
            columnspan=3,
            padx=12,
            pady=(8, 0),
            sticky="ew"
        )

        header_text_frame = ctk.CTkFrame(
            self.chat_header,
            fg_color="transparent"
        )
        header_text_frame.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.header_title = ctk.CTkLabel(
            header_text_frame,
            text="Selecciona un usuario para chatear",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#D3DDE5",
            anchor="w"
        )
        self.header_title.pack(anchor="w")

        self.typing_indicator = ctk.CTkLabel(
            header_text_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#72EAB6",
            anchor="w"
        )
        self.typing_indicator.pack(anchor="w")

        self.video_call_btn = ctk.CTkButton(
            self.chat_header,
            text="📹",
            width=36,
            height=32,
            fg_color="#7CEAF5",
            hover_color="#55D9F2",
            text_color="#0B121C",
            command=self._start_video_call,
            state="disabled"
        )
        self.video_call_btn.pack(
            side="right",
            padx=(2, 5)
        )

        self.voice_call_btn = ctk.CTkButton(
            self.chat_header,
            text="📞",
            width=36,
            height=32,
            fg_color="#72EAB6",
            hover_color="#55D9F2",
            text_color="#0B121C",
            command=self._start_voice_call,
            state="disabled"
        )
        self.voice_call_btn.pack(
            side="right",
            padx=(5, 2)
        )

        self.chat_display = ChatDisplay(
            self.right_frame,
            fg_color="#202B36",
            corner_radius=8
        )
        self.chat_display.grid(
            row=1,
            column=0,
            columnspan=3,
            padx=10,
            pady=5,
            sticky="nsew"
        )

        self.chat_display.set_background(self.config_mgr.config.get("chat_background_path", ""))

        self.msg_entry = ctk.CTkEntry(
            self.right_frame,
            placeholder_text="Escribe un mensaje...",
            fg_color="#202B36",
            text_color="#D3DDE5",
            placeholder_text_color="#8796A5",
            border_color="#3A4A58"
        )
        self.msg_entry.grid(
            row=2,
            column=0,
            padx=(10, 5),
            pady=10,
            sticky="ew"
        )
        self.msg_entry.bind(
            "<KeyRelease>",
            self._on_key_release
        )
        self.msg_entry.bind(
            "<Return>",
            lambda e: self._send_message()
        )

        self.mic_btn = ctk.CTkButton(
            self.right_frame,
            text="🎙",
            width=40,
            fg_color="#202B36",
            hover_color="#3A4A58",
            text_color="#7CEAF5",
            command=self._toggle_recording,
            state="disabled"
        )
        self.mic_btn.grid(
            row=2,
            column=1,
            padx=2,
            pady=10
        )

        self.send_btn = ctk.CTkButton(
            self.right_frame,
            text="Enviar",
            width=70,
            fg_color="#7CEAF5",
            hover_color="#55D9F2",
            text_color="#0B121C",
            font=ctk.CTkFont(weight="bold"),
            command=self._send_message,
            state="disabled"
        )
        self.send_btn.grid(
            row=2,
            column=2,
            padx=(2, 10),
            pady=10
        )

    def _start_incoming_call_ringtone(self):
        if not self.config_mgr.config.get("call_sound_enabled", True):
            return

        sound_path = self.config_mgr.config.get(
            "call_sound_path",
            ""
        )
        notif_vol = float(
            self.config_mgr.config.get(
                "notification_volume",
                1.0
            )
        )

        if sound_path and os.path.exists(sound_path):
            try:
                sound = pygame.mixer.Sound(sound_path)
                sound.set_volume(notif_vol)
                self.call_sound_channel = sound.play(loops=-1)
                return
            except Exception:
                pass

        try:
            self.bell()
        except Exception:
            pass

    def _start_outgoing_call_ringtone(self):
        if not self.config_mgr.config.get(
            "outgoing_call_sound_enabled",
            True
        ):
            return

        sound_path = self.config_mgr.config.get(
            "outgoing_call_sound_path",
            ""
        )
        notif_vol = float(
            self.config_mgr.config.get(
                "notification_volume",
                1.0
            )
        )

        if sound_path and os.path.exists(sound_path):
            try:
                sound = pygame.mixer.Sound(sound_path)
                sound.set_volume(notif_vol)
                self.call_sound_channel = sound.play(loops=-1)
                return
            except Exception:
                pass

        try:
            self.bell()
        except Exception:
            pass

    def _stop_call_ringtone(self):
        if self.call_sound_channel:
            try:
                self.call_sound_channel.stop()
            except Exception:
                pass

            self.call_sound_channel = None

        try:
            pygame.mixer.stop()
        except Exception:
            pass

    def _start_video_call(self):
        if not self.selected_user_ip or self.current_call_ip:
            return

        self.is_current_call_video = True
        self.current_call_ip = self.selected_user_ip

        user_info = self.network.active_users.get(
            self.selected_user_ip,
            {}
        )
        remote_name = user_info.get(
            "name",
            self.selected_user_ip
        )

        self.network.send_call_request(
            self.selected_user_ip,
            is_video=True
        )
        self._start_outgoing_call_ringtone()

        self.video_engine.start_call(
            self,
            remote_name,
            self.selected_user_ip,
            on_hangup_callback=self._end_call,
            on_toggle_mute_callback=self.audio_engine.toggle_mute
        )

        self.video_engine.set_status(
            f"Llamando a {remote_name}..."
        )

    def _start_voice_call(self):
        if not self.selected_user_ip or self.current_call_ip:
            return

        self.is_current_call_video = False
        self.current_call_ip = self.selected_user_ip

        user_info = self.network.active_users.get(
            self.selected_user_ip,
            {}
        )
        remote_name = user_info.get(
            "name",
            self.selected_user_ip
        )

        self.network.send_call_request(
            self.selected_user_ip,
            is_video=False
        )
        self._start_outgoing_call_ringtone()

        self.voice_engine.start_call(
            self,
            remote_name,
            self.selected_user_ip,
            on_hangup_callback=self._end_call,
            on_toggle_mute_callback=self.audio_engine.toggle_mute
        )

        self.voice_engine.set_status(
            f"Llamando a {remote_name}..."
        )

    def _end_call(self):
        self._stop_call_ringtone()
        self.audio_engine.stop_audio_call()

        if self.current_call_ip:
            self.network.send_call_end(
                self.current_call_ip
            )
            self.current_call_ip = None

        if self.is_current_call_video:
            self.after(
                0,
                self.video_engine.stop_call
            )
        else:
            self.after(
                0,
                self.voice_engine.stop_call
            )

    def _on_call_event(self, sender_ip, msg):
        self.after(
            0,
            lambda: self._handle_call_event_ui(
                sender_ip,
                msg
            )
        )

    def _handle_call_event_ui(self, sender_ip, msg):
        event_type = msg.get("type")

        if event_type == "CALL_REQUEST":
            if self.current_call_ip:
                self.network.send_call_response(
                    sender_ip,
                    accepted=False
                )
                return

            is_video = msg.get(
                "is_video",
                True
            )
            self.is_current_call_video = is_video
            self._start_incoming_call_ringtone()

            caller_name = msg.get(
                "caller_name",
                sender_ip
            )

            self.incoming_call_dialog = IncomingCallDialog(
                self,
                caller_name,
                is_video=is_video,
                on_accept=lambda: self._accept_incoming_call(
                    sender_ip,
                    caller_name,
                    is_video
                ),
                on_reject=lambda: self._reject_incoming_call(
                    sender_ip
                )
            )

        elif event_type == "CALL_RESPONSE":
            self._stop_call_ringtone()

            accepted = msg.get(
                "accepted",
                False
            )

            if accepted:
                mic_gain = float(
                    self.config_mgr.config.get(
                        "mic_gain",
                        1.0
                    )
                )
                master_vol = float(
                    self.config_mgr.config.get(
                        "master_volume",
                        1.0
                    )
                )

                if self.is_current_call_video:
                    self.video_engine.set_status(
                        "Conectado"
                    )
                else:
                    self.voice_engine.set_status(
                        "Conectado"
                    )

                self.audio_engine.start_audio_call(
                    self.current_call_ip,
                    mic_gain=mic_gain,
                    master_volume=master_vol
                )
            else:
                if self.is_current_call_video:
                    self.video_engine.set_status(
                        "Llamada rechazada"
                    )
                else:
                    self.voice_engine.set_status(
                        "Llamada rechazada"
                    )

                self.after(
                    1500,
                    self._end_call
                )

        elif event_type == "CALL_END":
            self._stop_call_ringtone()
            self.audio_engine.stop_audio_call()

            if self.incoming_call_dialog:
                try:
                    self.incoming_call_dialog.destroy()
                except Exception:
                    pass

                self.incoming_call_dialog = None

            self._end_call()

    def _accept_incoming_call(
        self,
        sender_ip,
        caller_name,
        is_video
    ):
        self._stop_call_ringtone()

        self.current_call_ip = sender_ip
        self.is_current_call_video = is_video

        self.network.send_call_response(
            sender_ip,
            accepted=True,
            is_video=is_video
        )

        mic_gain = float(
            self.config_mgr.config.get(
                "mic_gain",
                1.0
            )
        )
        master_vol = float(
            self.config_mgr.config.get(
                "master_volume",
                1.0
            )
        )

        if is_video:
            self.video_engine.start_call(
                self,
                caller_name,
                sender_ip,
                on_hangup_callback=self._end_call,
                on_toggle_mute_callback=self.audio_engine.toggle_mute
            )
            self.video_engine.set_status(
                "Conectado"
            )
        else:
            self.voice_engine.start_call(
                self,
                caller_name,
                sender_ip,
                on_hangup_callback=self._end_call,
                on_toggle_mute_callback=self.audio_engine.toggle_mute
            )
            self.voice_engine.set_status(
                "Conectado"
            )

        self.audio_engine.start_audio_call(
            sender_ip,
            mic_gain=mic_gain,
            master_volume=master_vol
        )

    def _reject_incoming_call(self, sender_ip):
        self._stop_call_ringtone()

        self.network.send_call_response(
            sender_ip,
            accepted=False
        )

        self.current_call_ip = None

    def _toggle_recording(self):
        if not self.selected_user_ip:
            return

        if not self.is_recording_audio:
            self.is_recording_audio = True

            self.mic_btn.configure(
                text="🔴",
                fg_color="#EF4444",
                hover_color="#DC2626",
                text_color="white"
            )

            self.msg_entry.configure(
                placeholder_text="Grabando audio... Haz clic en 🔴 para enviar"
            )

            self.recorder.start_recording()

        else:
            self.is_recording_audio = False

            self.mic_btn.configure(
                text="🎙",
                fg_color="#202B36",
                hover_color="#3A4A58",
                text_color="#7CEAF5"
            )

            self.msg_entry.configure(
                placeholder_text="Escribe un mensaje..."
            )

            audio_path = self.recorder.stop_recording()

            if audio_path and os.path.exists(audio_path):
                my_info = self._get_my_info()

                self.network.send_audio(
                    self.selected_user_ip,
                    audio_path
                )

                msg_obj = {
                    "initials": my_info["initials"],
                    "sender_name": my_info["full_name"],
                    "avatar": my_info["avatar"],
                    "content": audio_path,
                    "msg_type": "audio",
                    "is_mine": True
                }

                if self.selected_user_ip not in self.chat_histories:
                    self.chat_histories[
                        self.selected_user_ip
                    ] = []

                self.chat_histories[
                    self.selected_user_ip
                ].append(msg_obj)

                self._append_single_message(
                    msg_obj
                )

    def _on_key_release(self, event):
        if event.keysym == "Return":
            return

        text = self.msg_entry.get().strip()

        if text and self.selected_user_ip:
            self.last_typing_time = time.time()

            if not self.is_currently_typing:
                self.is_currently_typing = True

                self.network.send_typing_status(
                    self.selected_user_ip,
                    True
                )

            self.after(
                2500,
                self._check_stop_typing
            )

    def _check_stop_typing(self):
        if (
            self.is_currently_typing
            and (time.time() - self.last_typing_time >= 2.0)
        ):
            self.is_currently_typing = False

            if self.selected_user_ip:
                self.network.send_typing_status(
                    self.selected_user_ip,
                    False
                )

    def _on_typing_status_changed(
        self,
        sender_ip,
        is_typing
    ):
        self.after(
            0,
            lambda: self._update_typing_ui(
                sender_ip,
                is_typing
            )
        )

    def _update_typing_ui(
        self,
        sender_ip,
        is_typing
    ):
        if self.selected_user_ip == sender_ip:
            if is_typing:
                self.typing_indicator.configure(
                    text="escribiendo..."
                )
            else:
                self.typing_indicator.configure(
                    text=""
                )

    def _on_message_received(
        self,
        sender_ip,
        initials,
        content,
        msg_type="text",
        sender_name="",
        avatar=""
    ):
        if sender_ip not in self.chat_histories:
            self.chat_histories[sender_ip] = []

        user_info = self.network.active_users.get(
            sender_ip,
            {}
        )
        if not sender_name:
            sender_name = user_info.get(
                "name",
                sender_ip
            )

        if not avatar:
            avatar = user_info.get("avatar", "")

        msg_obj = {
            "initials": initials,
            "sender_name": sender_name,
            "avatar": avatar,
            "content": content,
            "msg_type": msg_type,
            "is_mine": False
        }

        self.chat_histories[
            sender_ip
        ].append(msg_obj)

        def update_gui():
            if self.selected_user_ip == sender_ip:
                self.typing_indicator.configure(
                    text=""
                )

                self._append_single_message(
                    msg_obj
                )

                if self.config_mgr.config.get(
                    "active_chat_sound_enabled",
                    True
                ):
                    self._play_active_chat_sound()

            else:
                self.unread_counts[
                    sender_ip
                ] = self.unread_counts.get(
                    sender_ip,
                    0
                ) + 1

                if self.config_mgr.config.get(
                    "sound_enabled",
                    True
                ):
                    self._play_notification_sound()

                self._update_badges_and_tray()

        self.after(
            0,
            update_gui
        )

    def _update_user_list_ui(
        self,
        active_users
    ):
        current_count = len(active_users)

        if (
            self.previous_users_count is not None
            and current_count != self.previous_users_count
        ):
            if self.config_mgr.config.get(
                "presence_sound_enabled",
                True
            ):
                if current_count > self.previous_users_count:
                    self._play_presence_sound(
                        "connect"
                    )
                else:
                    self._play_presence_sound(
                        "disconnect"
                    )

        self.previous_users_count = current_count

        self.after(
            0,
            lambda: self._refresh_users_gui(
                active_users
            )
        )

    def _refresh_users_gui(
        self,
        active_users
    ):
        selection_color = self.config_mgr.config.get(
            "selection_color",
            "#7CEAF5"
        )

        for ip in list(self.user_widgets.keys()):
            if ip not in active_users:
                try:
                    self.user_widgets[ip][
                        "frame"
                    ].destroy()
                except Exception:
                    pass

                del self.user_widgets[ip]

                if self.selected_user_ip == ip:
                    self.selected_user_ip = None

                    self.send_btn.configure(
                        state="disabled"
                    )
                    self.mic_btn.configure(
                        state="disabled"
                    )
                    self.video_call_btn.configure(
                        state="disabled"
                    )
                    self.voice_call_btn.configure(
                        state="disabled"
                    )
                    self.header_title.configure(
                        text="Selecciona un usuario para chatear"
                    )
                    self.typing_indicator.configure(
                        text=""
                    )

        for ip, info in active_users.items():
            btn_text = f"{info['name']} ({info['initials']})"

            is_selected = (
                self.selected_user_ip == ip
            )

            bg_col = (
                selection_color
                if is_selected
                else "transparent"
            )

            txt_col = (
                "#0B121C"
                if is_selected
                else "#D3DDE5"
            )

            if ip not in self.user_widgets:
                frame = ctk.CTkFrame(
                    self.users_scroll,
                    fg_color="transparent"
                )
                frame.pack(
                    fill="x",
                    pady=2
                )

                btn = ctk.CTkButton(
                    frame,
                    text=btn_text,
                    anchor="w",
                    fg_color=bg_col,
                    text_color=txt_col,
                    hover_color="#202B36",
                    font=ctk.CTkFont(
                        weight="bold"
                        if is_selected
                        else "normal"
                    ),
                    command=lambda target_ip=ip:
                        self._select_user(target_ip)
                )
                btn.pack(
                    side="left",
                    fill="x",
                    expand=True
                )

                badge = ctk.CTkLabel(
                    frame,
                    text="",
                    width=22,
                    height=22,
                    corner_radius=11,
                    fg_color="#EF4444",
                    text_color="white",
                    font=ctk.CTkFont(
                        size=11,
                        weight="bold"
                    )
                )

                self.user_widgets[ip] = {
                    "frame": frame,
                    "button": btn,
                    "badge": badge
                }

            else:
                self.user_widgets[ip][
                    "button"
                ].configure(
                    text=btn_text,
                    fg_color=bg_col,
                    text_color=txt_col
                )

        if self.selected_user_ip in active_users:
            new_avatar = active_users[self.selected_user_ip].get("avatar", "")
            history = self.chat_histories.get(self.selected_user_ip, [])
            updated = False
            for msg in history:
                if not msg.get("is_mine") and msg.get("avatar") != new_avatar:
                    msg["avatar"] = new_avatar
                    updated = True
            if updated:
                self._render_chat_history()

    def _select_user(self, ip):
        self.selected_user_ip = ip

        user_info = self.network.active_users.get(
            ip,
            {}
        )
        name = user_info.get(
            "name",
            ip
        )

        self.unread_counts[ip] = 0
        self._update_badges_and_tray()

        selection_color = self.config_mgr.config.get(
            "selection_color",
            "#7CEAF5"
        )

        for u_ip, w in self.user_widgets.items():
            if u_ip == ip:
                w["button"].configure(
                    fg_color=selection_color,
                    text_color="#0B121C"
                )
            else:
                w["button"].configure(
                    fg_color="transparent",
                    text_color="#D3DDE5"
                )

        self.send_btn.configure(
            state="normal"
        )
        self.mic_btn.configure(
            state="normal"
        )
        self.video_call_btn.configure(
            state="normal"
        )
        self.voice_call_btn.configure(
            state="normal"
        )

        self.header_title.configure(
            text=f"Chat con {name}"
        )
        self.typing_indicator.configure(
            text=""
        )

        self._render_chat_history()

    def _send_message(self):
        text = self.msg_entry.get().strip()

        if not text or not self.selected_user_ip:
            return

        if self.is_currently_typing:
            self.is_currently_typing = False

            self.network.send_typing_status(
                self.selected_user_ip,
                False
            )

        my_info = self._get_my_info()

        self.network.send_message(
            self.selected_user_ip,
            text
        )

        msg_obj = {
            "initials": my_info["initials"],
            "sender_name": my_info["full_name"],
            "avatar": my_info["avatar"],
            "content": text,
            "msg_type": "text",
            "is_mine": True
        }

        if self.selected_user_ip not in self.chat_histories:
            self.chat_histories[
                self.selected_user_ip
            ] = []

        self.chat_histories[
            self.selected_user_ip
        ].append(msg_obj)

        self.msg_entry.delete(
            0,
            "end"
        )

        self._append_single_message(
            msg_obj
        )

    def _append_single_message(
        self,
        msg_obj
    ):
        is_mine = msg_obj.get(
            "is_mine",
            False
        )
        msg_type = msg_obj.get(
            "msg_type",
            "text"
        )
        content = msg_obj.get(
            "content",
            ""
        )

        if is_mine:
            avatar_filename = self.config_mgr.config.get(
                "avatar_filename",
                ""
            )
            display_initials = (
                self.config_mgr.get_initials()
                or "Tú"
            )
        else:
            avatar_filename = msg_obj.get(
                "avatar",
                ""
            )
            display_initials = msg_obj.get(
                "initials",
                "Contacto"
            )

        font_family = self.config_mgr.config.get(
            "font_family",
            "Segoe UI"
        )
        font_size = self.config_mgr.config.get(
            "font_size",
            13
        )
        received_color = self.config_mgr.config.get(
            "received_bubble_color",
            "#202B36"
        )

        custom_font = ctk.CTkFont(
            family=font_family,
            size=font_size
        )

        avatar = None
        avatar_path = os.path.join("assets", "avatars", avatar_filename) if avatar_filename else ""
        if avatar_path and os.path.exists(avatar_path):
            try:
                with Image.open(avatar_path) as image:
                    avatar = crop_to_circle(image, size=(36, 36))
            except Exception:
                pass

        self.chat_display.add_message(
            is_mine=is_mine,
            initials=display_initials,
            avatar=avatar,
            content=content,
            msg_type=msg_type,
            font=custom_font,
            bubble_color="#72EAB6" if is_mine else received_color,
            text_color="#0B121C" if is_mine else "#D3DDE5",
            name_color="#72EAB6" if is_mine else "#7CEAF5",
            config_mgr=self.config_mgr,
        )

    def _render_chat_history(self):
        self.chat_display.clear_messages()

        if not self.selected_user_ip:
            return

        messages = self.chat_histories.get(
            self.selected_user_ip,
            []
        )

        for msg in messages:
            self._append_single_message(
                msg
            )

    def _update_badges_and_tray(self):
        total_unread = sum(
            self.unread_counts.values()
        )

        for ip, count in self.unread_counts.items():
            if ip in self.user_widgets:
                badge = self.user_widgets[ip][
                    "badge"
                ]

                if count > 0:
                    badge.configure(
                        text=str(count)
                    )
                    badge.pack(
                        side="right",
                        padx=5
                    )
                else:
                    badge.pack_forget()

        self.tray_mgr.update_badge(
            total_unread
        )

    def _play_notification_sound(self):
        sound_path = self.config_mgr.config.get(
            "sound_path",
            ""
        )
        notif_vol = float(
            self.config_mgr.config.get(
                "notification_volume",
                1.0
            )
        )

        if sound_path and os.path.exists(
            sound_path
        ):
            try:
                sound = pygame.mixer.Sound(
                    sound_path
                )
                sound.set_volume(
                    notif_vol
                )
                sound.play()
                return
            except Exception:
                pass

        try:
            self.bell()
        except Exception:
            pass

    def _play_active_chat_sound(self):
        sound_path = self.config_mgr.config.get(
            "active_chat_sound_path",
            ""
        )
        notif_vol = float(
            self.config_mgr.config.get(
                "notification_volume",
                1.0
            )
        )

        if sound_path and os.path.exists(
            sound_path
        ):
            try:
                sound = pygame.mixer.Sound(
                    sound_path
                )
                sound.set_volume(
                    notif_vol
                )
                sound.play()
                return
            except Exception:
                pass

        try:
            self.bell()
        except Exception:
            pass

    def _play_presence_sound(
        self,
        event_type="connect"
    ):
        key = (
            "presence_connect_sound_path"
            if event_type == "connect"
            else "presence_disconnect_sound_path"
        )

        sound_path = self.config_mgr.config.get(
            key,
            ""
        )

        notif_vol = float(
            self.config_mgr.config.get(
                "notification_volume",
                1.0
            )
        )

        if sound_path and os.path.exists(
            sound_path
        ):
            try:
                sound = pygame.mixer.Sound(
                    sound_path
                )
                sound.set_volume(
                    notif_vol
                )
                sound.play()
                return
            except Exception:
                pass

        try:
            self.bell()
        except Exception:
            pass

    def _open_settings(self):
        SettingsDialog(
            self,
            self.config_mgr,
            on_update=self._on_settings_applied
        )

    def _on_settings_applied(self):
        self.chat_display.set_background(self.config_mgr.config.get("chat_background_path", ""))
        if (
            self.audio_engine
            and self.audio_engine.is_streaming
        ):
            mic_gain = float(
                self.config_mgr.config.get(
                    "mic_gain",
                    1.0
                )
            )

            master_vol = float(
                self.config_mgr.config.get(
                    "master_volume",
                    1.0
                )
            )

            self.audio_engine.update_volumes(
                mic_gain,
                master_vol
            )

        if self.network:
            self._refresh_users_gui(
                self.network.active_users
            )

        if self.selected_user_ip:
            self._render_chat_history()

    def _minimize_to_tray(self):
        self.withdraw()

    def _restore_from_tray(self):
        self.after(
            0,
            self._do_restore
        )

    def _do_restore(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _force_quit(self):
        self._stop_call_ringtone()

        if hasattr(self, "network"):
            self.network.stop()

        self.video_engine.stop_call()
        self.voice_engine.stop_call()
        self.audio_engine.stop_audio_call()
        self.tray_mgr.stop()

        self.after(
            0,
            self.destroy
        )


if __name__ == "__main__":
    app = LANChatApp()
    app.protocol(
        "WM_DELETE_WINDOW",
        app._minimize_to_tray
    )
    app.mainloop()