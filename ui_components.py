import customtkinter as ctk
from tkinter import filedialog, colorchooser, messagebox
import tkinter as tk
import os
import pygame
import wave
import subprocess
import sys
import time
from PIL import Image, ImageTk, ImageOps


class FileCardWidget(ctk.CTkFrame):
    """Widget de tarjeta de archivo compacto con ancho fijo, previsualización para ambos pares y colores seguros."""
    def __init__(self, parent, file_id, file_name, file_size, file_path, is_mine, config_mgr, on_accept_download=None, on_cancel_download=None, bg_color=None):
        super().__init__(parent, fg_color=bg_color, corner_radius=10, width=320)
        self.file_id = file_id
        self.file_name = file_name
        self.file_size = file_size
        self.file_path = file_path
        self.is_mine = is_mine
        self.config_mgr = config_mgr
        self.on_accept_download = on_accept_download
        self.on_cancel_download = on_cancel_download
        self.is_canceled = False

        self.last_bytes = 0
        self.last_speed_time = time.time()
        self.current_speed_str = ""
        self.preview_btn = None

        self.formatted_size = self._format_size(file_size)
        self._build_ui()

    def _format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def _format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"

    def _build_ui(self):
        txt_color = "#0B121C" if self.is_mine else "#D3DDE5"
        sub_color = "#151E29" if self.is_mine else "#8796A5"

        self.top_frame = ctk.CTkFrame(self, fg_color="transparent", width=300)
        self.top_frame.pack(fill="x", padx=10, pady=(8, 2))

        ext = os.path.splitext(self.file_name)[1].lower()
        is_image = ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]

        self._try_render_preview()

        icon_text = "🖼️" if is_image else ("📦" if ext in [".zip", ".rar", ".7z", ".tar", ".gz"] else "📄")
        
        info_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent", width=290)
        info_frame.pack(fill="x", expand=True)

        ctk.CTkLabel(
            info_frame,
            text=f"{icon_text} {self.file_name}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=txt_color,
            anchor="w",
            wraplength=280
        ).pack(anchor="w", fill="x")

        self.status_label = ctk.CTkLabel(
            info_frame,
            text=f"{self.formatted_size}",
            font=ctk.CTkFont(size=10),
            text_color=sub_color,
            anchor="w",
            wraplength=280
        )
        self.status_label.pack(anchor="w", fill="x")

        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=6,
            progress_color="#0B121C" if self.is_mine else "#72EAB6"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=10, pady=4)

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        has_actions = False

        if not self.is_mine and self.on_accept_download:
            has_actions = True
            self.accept_btn = ctk.CTkButton(
                self.actions_frame,
                text="Aceptar Descarga",
                height=22,
                fg_color="#72EAB6",
                hover_color="#55D9F2",
                text_color="#0B121C",
                font=ctk.CTkFont(size=10, weight="bold"),
                command=self._accept
            )
            self.accept_btn.pack(side="left", padx=(0, 4))

        if self.is_mine and self.on_cancel_download:
            has_actions = True
            self.cancel_btn = ctk.CTkButton(
                self.actions_frame,
                text="Cancelar",
                height=22,
                fg_color="#EF4444",
                hover_color="#DC2626",
                text_color="white",
                font=ctk.CTkFont(size=10, weight="bold"),
                command=self._cancel
            )
            self.cancel_btn.pack(side="left")

        if has_actions:
            self.actions_frame.pack(fill="x", padx=10, pady=(2, 6))

    def _try_render_preview(self):
        """Intenta cargar y renderizar la vista previa si el archivo existe."""
        if self.preview_btn is not None:
            return

        ext = os.path.splitext(self.file_name)[1].lower()
        is_image = ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]

        if is_image and self.file_path and os.path.exists(self.file_path):
            try:
                with Image.open(self.file_path) as img:
                    img_copy = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (160, 90), Image.Resampling.LANCZOS)
                    preview = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=(160, 90))
                    # CORREGIDO: hover_color="transparent" evita el error TclError unknown color name ""
                    self.preview_btn = ctk.CTkButton(
                        self.top_frame,
                        text="",
                        image=preview,
                        fg_color="transparent",
                        hover_color="transparent",
                        command=self.open_file
                    )
                    self.preview_btn.pack(anchor="w", pady=2)
            except Exception:
                pass

    def _accept(self):
        if self.on_accept_download:
            if self.actions_frame.winfo_manager():
                self.actions_frame.pack_forget()
            self.on_accept_download()

    def _cancel(self):
        if self.on_cancel_download:
            self.on_cancel_download()
        self.mark_canceled()

    def mark_canceled(self):
        self.is_canceled = True
        self.status_label.configure(text=f"{self.formatted_size} - Cancelado")
        self.progress_bar.set(0.0)
        if self.actions_frame.winfo_manager():
            self.actions_frame.pack_forget()

    def update_progress(self, current_bytes, total_bytes):
        if self.is_canceled:
            return

        now = time.time()
        dt = now - self.last_speed_time

        if dt >= 1.0 or current_bytes >= total_bytes:
            db = current_bytes - self.last_bytes
            speed = db / dt if dt > 0 else 0
            self.last_bytes = current_bytes
            self.last_speed_time = now

            if self.config_mgr.config.get("show_transfer_speed", True) and speed > 0:
                self.current_speed_str = f" - {self._format_speed(speed)}"
            else:
                self.current_speed_str = ""

        ratio = min(max(current_bytes / max(total_bytes, 1), 0.0), 1.0)
        self.progress_bar.set(ratio)
        pct = int(ratio * 100)
        
        state_str = "Enviando" if self.is_mine else "Descargando"
        self.status_label.configure(
            text=f"{state_str} {pct}% ({self._format_size(current_bytes)} / {self.formatted_size}){self.current_speed_str}"
        )

        if current_bytes >= total_bytes and total_bytes > 0:
            btn_bg = "#0B121C" if self.is_mine else "#202B36"
            btn_txt = "#72EAB6" if self.is_mine else "#7CEAF5"
            self.status_label.configure(text=f"{self.formatted_size} - Completado")
            self.progress_bar.pack_forget()
            self._try_render_preview()
            self._show_completed_actions(btn_bg, btn_txt)

    def set_file_path(self, path):
        self.file_path = path
        self._try_render_preview()

    def _show_completed_actions(self, btn_bg, btn_txt):
        for w in self.actions_frame.winfo_children():
            w.destroy()

        ctk.CTkButton(
            self.actions_frame,
            text="Abrir Archivo",
            height=22,
            fg_color=btn_bg,
            hover_color="#3A4A58",
            text_color=btn_txt,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self.open_file
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.actions_frame,
            text="Mostrar en carpeta",
            height=22,
            fg_color=btn_bg,
            hover_color="#3A4A58",
            text_color=btn_txt,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self.show_in_folder
        ).pack(side="left")

        if not self.actions_frame.winfo_manager():
            self.actions_frame.pack(fill="x", padx=10, pady=(2, 6))

    def open_file(self):
        target = self.file_path
        if target and os.path.exists(target):
            try:
                if sys.platform == "win32":
                    os.startfile(target)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", target])
                else:
                    subprocess.Popen(["xdg-open", target])
            except Exception as e:
                print(f"Error al abrir archivo: {e}")
        else:
            messagebox.showwarning("Archivo no encontrado", "No se encuentra el archivo en el sistema.", parent=self)

    def show_in_folder(self):
        target = self.file_path
        if target and os.path.exists(target):
            try:
                if sys.platform == "win32":
                    subprocess.Popen(f'explorer /select,"{os.path.normpath(target)}"')
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", target])
                else:
                    subprocess.Popen(["xdg-open", os.path.dirname(target)])
            except Exception as e:
                print(f"Error al mostrar carpeta: {e}")
        else:
            messagebox.showwarning("Archivo no encontrado", "No se encuentra la carpeta o el archivo especificado.", parent=self)


class ChatDisplay(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._rows = []
        self._layout_job = None
        self._scroll_to_end = False
        self._background = None
        self._background_photo = None
        self._background_size = None
        self.file_cards = {}
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._parent_canvas = tk.Canvas(self, bg="#202B36", highlightthickness=0, bd=0)
        self._parent_canvas.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self._scrollbar = ctk.CTkScrollbar(self, command=self._parent_canvas.yview)
        self._scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=6)
        self._background_item = self._parent_canvas.create_image(0, 0, anchor="nw")
        self._parent_canvas.configure(yscrollcommand=self._on_scroll)
        self._parent_canvas.bind("<Configure>", self._schedule_layout)
        self._wheel_bindings = []
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            binding = self.winfo_toplevel().bind(event, self._on_mousewheel, add="+")
            self._wheel_bindings.append((event, binding))

    def set_background(self, filepath):
        self._background = None
        if filepath:
            try:
                with Image.open(filepath) as image:
                    self._background = ImageOps.exif_transpose(image).convert("RGB")
            except Exception as exc:
                print(f"No se pudo cargar el fondo del chat: {exc}")
        self._background_size = None
        self._draw_background()

    def _draw_background(self):
        canvas = self._parent_canvas
        if self._background is None:
            canvas.itemconfigure(self._background_item, image="")
            self._background_photo = None
            return
        size = (max(1, canvas.winfo_width()), max(1, canvas.winfo_height()))
        if size != self._background_size:
            resized = self._background.resize(size, Image.Resampling.LANCZOS)
            self._background_photo = ImageTk.PhotoImage(resized, master=canvas)
            self._background_size = size
            canvas.itemconfigure(self._background_item, image=self._background_photo)
        canvas.coords(self._background_item, canvas.canvasx(0), canvas.canvasy(0))
        canvas.tag_lower(self._background_item)

    def _on_scroll(self, first, last):
        self._scrollbar.set(first, last)
        self._draw_background()

    def _on_mousewheel(self, event):
        widget = event.widget
        while widget is not None and widget is not self:
            widget = getattr(widget, "master", None)
        if widget is None:
            return
        if getattr(event, "num", None) in (4, 5):
            units = -1 if event.num == 4 else 1
        else:
            delta = getattr(event, "delta", 0)
            units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        self._parent_canvas.yview_scroll(units, "units")
        return "break"

    def add_message(self, *, is_mine, initials, avatar, content, msg_type,
                    font, bubble_color, text_color, name_color, config_mgr,
                    file_id=None, file_name="", file_size=0, on_accept_download=None, on_cancel_download=None):
        canvas = self._parent_canvas
        scale = self._get_widget_scaling()
        tag = f"message_{len(self._rows)}"
        name_font = ctk.CTkFont(size=12, weight="bold")
        photo = None

        if avatar is not None:
            avatar = avatar.resize((round(36 * scale), round(36 * scale)), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(avatar, master=canvas)
            canvas.create_image(0, 0, image=photo, anchor="nw", tags=tag)
        else:
            canvas.create_oval(0, 0, 36 * scale, 36 * scale, fill=name_color, outline="", tags=tag)
            canvas.create_text(18 * scale, 18 * scale, text=initials,
                               font=name_font.create_scaled_tuple(scale), fill="#0B121C", tags=tag)

        name = canvas.create_text(44 * scale, 18 * scale, text=initials,
                                  anchor="w", fill=name_color,
                                  font=name_font.create_scaled_tuple(scale), tags=tag)
        header_width = max(36 * scale, canvas.bbox(name)[2])
        top = 40 * scale
        player = None
        file_card = None
        window = None
        text = None

        if msg_type == "text":
            text = canvas.create_text(0, 0, text=content, anchor="nw",
                                      font=font.create_scaled_tuple(scale),
                                      fill=text_color, width=380 * scale,
                                      justify="left", tags=tag)
            bounds = canvas.bbox(text)
            bubble_width = bounds[2] - bounds[0] + 24 * scale
            bubble_height = max(28 * scale, bounds[3] - bounds[1]) + 16 * scale

        elif msg_type == "audio":
            player = AudioPlayerWidget(canvas, audio_path=content, config_mgr=config_mgr, is_mine=is_mine, bg_color=bubble_color)
            player.update_idletasks()
            bubble_width = player.winfo_reqwidth() + 4 * scale
            bubble_height = player.winfo_reqheight() + 4 * scale

        elif msg_type == "file":
            file_card = FileCardWidget(
                canvas,
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                file_path=content,
                is_mine=is_mine,
                config_mgr=config_mgr,
                on_accept_download=on_accept_download,
                on_cancel_download=on_cancel_download,
                bg_color=bubble_color
            )
            file_card.update_idletasks()
            bubble_width = file_card.winfo_reqwidth() + 4 * scale
            bubble_height = file_card.winfo_reqheight() + 4 * scale
            if file_id:
                self.file_cards[file_id] = file_card

        else:
            bubble_width = bubble_height = 0

        width = max(header_width, bubble_width)
        left = width - bubble_width if is_mine else 0

        if text is not None:
            right, bottom = left + bubble_width, top + bubble_height
            radius = min(12 * scale, bubble_width / 2, bubble_height / 2)
            canvas.create_polygon(
                left + radius, top, right - radius, top, right, top,
                right, top + radius, right, bottom - radius, right, bottom,
                right - radius, bottom, left + radius, bottom, left, bottom,
                left, bottom - radius, left, top + radius, left, top,
                smooth=True, splinesteps=24, fill=bubble_color, outline="", tags=tag)
            canvas.coords(text, left + 12 * scale, top + (bubble_height - (bounds[3] - bounds[1])) / 2)
            canvas.tag_raise(text)

        elif player is not None:
            window = canvas.create_window(left + 2 * scale, top + 2 * scale, window=player, anchor="nw", tags=tag)

        elif file_card is not None:
            window = canvas.create_window(left + 2 * scale, top + 2 * scale, window=file_card, anchor="nw", tags=tag)

        row_data = dict(tag=tag, width=width, height=top + bubble_height,
                        is_mine=is_mine, x=0, y=0, photo=photo,
                        player=player, window=window, file_card=file_card, font=font,
                        name_font=name_font)
        self._rows.append(row_data)
        self._scroll_to_end = True
        self._schedule_layout()

    def update_file_progress(self, file_id, current_bytes, total_bytes, save_path=None):
        card = self.file_cards.get(file_id)
        if card:
            if save_path:
                card.set_file_path(save_path)
            card.update_progress(current_bytes, total_bytes)
            self._schedule_layout()

    def mark_file_canceled(self, file_id):
        card = self.file_cards.get(file_id)
        if card:
            card.mark_canceled()
            self._schedule_layout()

    def _schedule_layout(self, event=None):
        if self._layout_job is None:
            self._layout_job = self.after_idle(self._layout_messages)

    def _layout_messages(self):
        self._layout_job = None
        canvas = self._parent_canvas
        width = max(1, canvas.winfo_width())
        scale = self._get_widget_scaling()
        top_offset = 40 * scale
        y = 6

        for row in self._rows:
            if row.get("file_card") is not None:
                card = row["file_card"]
                card.update_idletasks()
                bubble_width = card.winfo_reqwidth() + 4 * scale
                bubble_height = card.winfo_reqheight() + 4 * scale
                row["width"] = bubble_width
                row["height"] = top_offset + bubble_height

            x = width - 5 - row["width"] if row["is_mine"] else 5
            canvas.move(row["tag"], x - row["x"], y - row["y"])
            row["x"], row["y"] = x, y
            y += row["height"] + 12

        canvas.configure(scrollregion=(0, 0, width, max(y, canvas.winfo_height())))
        if self._scroll_to_end:
            canvas.yview_moveto(1.0)
            self._scroll_to_end = False
        self._draw_background()

    def clear_messages(self):
        for row in self._rows:
            self._parent_canvas.delete(row["tag"])
            if row["player"] is not None:
                row["player"].destroy()
            if row.get("file_card") is not None:
                row["file_card"].destroy()
        self._rows.clear()
        self.file_cards.clear()
        self._schedule_layout()

    def destroy(self):
        if self._layout_job is not None:
            self.after_cancel(self._layout_job)
        for event, binding in self._wheel_bindings:
            self.winfo_toplevel().unbind(event, binding)
        super().destroy()


class AudioPlayerWidget(ctk.CTkFrame):
    _current_playing_widget = None

    def __init__(self, parent, audio_path, config_mgr, is_mine=True, bg_color=None):
        super().__init__(parent, fg_color=bg_color, corner_radius=10)
        self.audio_path = audio_path
        self.config_mgr = config_mgr
        self.is_mine = is_mine
        self.is_playing = False
        self.duration = self._get_audio_duration(audio_path)
        self.current_pos = 0.0
        self.timer_job = None

        self._build_ui()

    def _get_audio_duration(self, filepath):
        try:
            with wave.open(filepath, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        except Exception:
            return 0.0

    def _format_time(self, seconds):
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins}:{secs:02d}"

    def _build_ui(self):
        if self.is_mine:
            btn_fg = "#0B121C"
            btn_hover = "#151E29"
            btn_txt = "#72EAB6"
            slider_prog = "#0B121C"
            slider_btn = "#151E29"
            slider_btn_hover = "#3A4A58"
            time_txt = "#0B121C"
        else:
            btn_fg = "#7CEAF5"
            btn_hover = "#55D9F2"
            btn_txt = "#0B121C"
            slider_prog = "#7CEAF5"
            slider_btn = "#B6FFFF"
            slider_btn_hover = "#55D9F2"
            time_txt = "#8796A5"

        self.play_btn = ctk.CTkButton(
            self,
            text="▶",
            width=32,
            height=32,
            corner_radius=16,
            fg_color=btn_fg,
            hover_color=btn_hover,
            text_color=btn_txt,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_play
        )
        self.play_btn.pack(side="left", padx=(8, 4), pady=6)

        mid_frame = ctk.CTkFrame(self, fg_color="transparent")
        mid_frame.pack(side="left", fill="x", expand=True, padx=6, pady=4)

        self.slider = ctk.CTkSlider(
            mid_frame,
            from_=0,
            to=max(self.duration, 0.1),
            number_of_steps=100,
            height=12,
            progress_color=slider_prog,
            button_color=slider_btn,
            button_hover_color=slider_btn_hover,
            command=self._on_slider_seek
        )
        self.slider.set(0)
        self.slider.pack(fill="x", expand=True)

        dur_str = self._format_time(self.duration)
        self.time_label = ctk.CTkLabel(
            mid_frame,
            text=f"0:00 / {dur_str}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=time_txt
        )
        self.time_label.pack(anchor="w", pady=(2, 0))

    def _get_effective_volume(self):
        master_vol = float(self.config_mgr.config.get("master_volume", 1.0))
        return min(max(master_vol, 0.0), 1.0)

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if AudioPlayerWidget._current_playing_widget and AudioPlayerWidget._current_playing_widget != self:
            AudioPlayerWidget._current_playing_widget.stop()

        AudioPlayerWidget._current_playing_widget = self

        if os.path.exists(self.audio_path):
            try:
                vol = self._get_effective_volume()
                if not pygame.mixer.music.get_busy() or self.current_pos == 0:
                    pygame.mixer.music.load(self.audio_path)
                    pygame.mixer.music.set_volume(vol)
                    pygame.mixer.music.play(start=self.current_pos)
                else:
                    pygame.mixer.music.set_volume(vol)
                    pygame.mixer.music.unpause()

                self.is_playing = True
                self.play_btn.configure(text="⏸")
                self._update_progress_loop()
            except Exception as e:
                print(f"Error al reproducir nota de voz: {e}")

    def pause(self):
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass
        self.is_playing = False
        self.play_btn.configure(text="▶")
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None

    def stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.is_playing = False
        self.current_pos = 0.0
        self.slider.set(0)
        self.time_label.configure(text=f"0:00 / {self._format_time(self.duration)}")
        self.play_btn.configure(text="▶")
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        if AudioPlayerWidget._current_playing_widget == self:
            AudioPlayerWidget._current_playing_widget = None

    def _on_slider_seek(self, value):
        self.current_pos = float(value)
        if self.is_playing:
            try:
                vol = self._get_effective_volume()
                pygame.mixer.music.load(self.audio_path)
                pygame.mixer.music.set_volume(vol)
                pygame.mixer.music.play(start=self.current_pos)
            except Exception:
                pass
        dur_str = self._format_time(self.duration)
        pos_str = self._format_time(self.current_pos)
        self.time_label.configure(text=f"{pos_str} / {dur_str}")

    def _update_progress_loop(self):
        if not self.is_playing:
            return

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self._get_effective_volume())
            self.current_pos += 0.1
            if self.current_pos > self.duration:
                self.current_pos = self.duration

            self.slider.set(self.current_pos)
            pos_str = self._format_time(self.current_pos)
            dur_str = self._format_time(self.duration)
            self.time_label.configure(text=f"{pos_str} / {dur_str}")

            self.timer_job = self.after(100, self._update_progress_loop)
        else:
            self.stop()


class SetupDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_fn="", current_ln="", on_save=None):
        super().__init__(parent)
        self.title("OmniLan - Registro Inicial")
        self.geometry("380x280")
        self.resizable(False, False)
        self.configure(fg_color="#0B121C")
        self.on_save = on_save

        ico_path = os.path.join("assets", "ico", "omnilan.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Bienvenido a OmniLan", font=ctk.CTkFont(size=18, weight="bold"), text_color="#7CEAF5").pack(pady=15)

        self.fn_entry = ctk.CTkEntry(self, placeholder_text="Nombre", width=280, fg_color="#202B36", text_color="#D3DDE5", border_color="#3A4A58")
        self.fn_entry.insert(0, current_fn)
        self.fn_entry.pack(pady=8)

        self.ln_entry = ctk.CTkEntry(self, placeholder_text="Apellido", width=280, fg_color="#202B36", text_color="#D3DDE5", border_color="#3A4A58")
        self.ln_entry.insert(0, current_ln)
        self.ln_entry.pack(pady=8)

        ctk.CTkButton(self, text="Guardar y Continuar", fg_color="#7CEAF5", hover_color="#55D9F2", text_color="#0B121C", font=ctk.CTkFont(weight="bold"), command=self.save).pack(pady=20)

    def save(self):
        fn = self.fn_entry.get().strip()
        ln = self.ln_entry.get().strip()
        if fn and ln:
            if self.on_save:
                self.on_save(fn, ln)
            self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config_mgr, on_update):
        super().__init__(parent)
        self.title("OmniLan - Configuración")
        self.geometry("560x760")
        self.resizable(False, False)
        self.configure(fg_color="#0B121C")
        self.config_mgr = config_mgr
        self.on_update = on_update
        self.selected_avatar = self.config_mgr.config.get("avatar_filename", "")
        self.avatar_buttons = {}
        self.pending_chat_background = None

        ico_path = os.path.join("assets", "ico", "omnilan.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self.transient(parent)
        self.grab_set()

        self.tabview = ctk.CTkTabview(
            self,
            width=520,
            height=670,
            fg_color="#151E29",
            segmented_button_fg_color="#202B36",
            segmented_button_selected_color="#7CEAF5",
            segmented_button_selected_hover_color="#55D9F2",
            segmented_button_unselected_color="#202B36",
            segmented_button_unselected_hover_color="#3A4A58",
            text_color="#0B121C"
        )
        self.tabview.pack(padx=20, pady=10)

        self.tab_profile = self.tabview.add("Perfil")
        self.tab_audio = self.tabview.add("Audio")
        self.tab_design = self.tabview.add("Apariencia")
        self.tab_downloads = self.tabview.add("Descargas")
        self.tab_network = self.tabview.add("Red")

        self._build_profile_tab()
        self._build_audio_tab()
        self._build_design_tab()
        self._build_downloads_tab()
        self._build_network_tab()

        ctk.CTkButton(self, text="Aplicar y Guardar", fg_color="#72EAB6", hover_color="#55D9F2", text_color="#0B121C", font=ctk.CTkFont(weight="bold"), command=self.save).pack(pady=10)

    def _build_profile_tab(self):
        ctk.CTkLabel(self.tab_profile, text="Datos del Usuario", font=ctk.CTkFont(size=13, weight="bold"), text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(10, 5))

        self.fn_entry = ctk.CTkEntry(self.tab_profile, placeholder_text="Nombre", width=280, fg_color="#202B36", text_color="#D3DDE5", border_color="#3A4A58")
        self.fn_entry.insert(0, self.config_mgr.config.get("first_name", ""))
        self.fn_entry.pack(anchor="w", padx=15, pady=2)

        self.ln_entry = ctk.CTkEntry(self.tab_profile, placeholder_text="Apellido", width=280, fg_color="#202B36", text_color="#D3DDE5", border_color="#3A4A58")
        self.ln_entry.insert(0, self.config_mgr.config.get("last_name", ""))
        self.ln_entry.pack(anchor="w", padx=15, pady=2)

        ctk.CTkFrame(self.tab_profile, height=1, fg_color="#3A4A58").pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.tab_profile, text="Selecciona tu Avatar", font=ctk.CTkFont(size=13, weight="bold"), text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(2, 5))

        avatars_scroll = ctk.CTkScrollableFrame(self.tab_profile, width=460, height=220, fg_color="#202B36")
        avatars_scroll.pack(fill="x", padx=15, pady=2)

        avatars_dir = os.path.join("assets", "avatars")
        avatar_files = [f for f in os.listdir(avatars_dir) if f.lower().endswith('.png')] if os.path.exists(avatars_dir) else []

        if not avatar_files:
            ctk.CTkLabel(avatars_scroll, text="No se encontraron archivos .png en\nassets/avatars", font=ctk.CTkFont(size=11), text_color="#8796A5").pack(pady=40)
        else:
            cols = 4
            for idx, filename in enumerate(avatar_files):
                row = idx // cols
                col = idx % cols
                filepath = os.path.join(avatars_dir, filename)

                try:
                    pil_img = Image.open(filepath)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 60))
                except Exception:
                    continue

                is_selected = (self.selected_avatar == filename)
                border_col = "#7CEAF5" if is_selected else "#3A4A58"

                btn = ctk.CTkButton(
                    avatars_scroll,
                    text="",
                    image=ctk_img,
                    width=70,
                    height=70,
                    fg_color="#151E29",
                    hover_color="#3A4A58",
                    border_width=3 if is_selected else 1,
                    border_color=border_col,
                    command=lambda f=filename: self._select_avatar(f)
                )
                btn.grid(row=row, column=col, padx=10, pady=10)
                self.avatar_buttons[filename] = btn

    def _select_avatar(self, filename):
        self.selected_avatar = filename
        for f, btn in self.avatar_buttons.items():
            if f == filename:
                btn.configure(border_color="#7CEAF5", border_width=3)
            else:
                btn.configure(border_color="#3A4A58", border_width=1)

    def _build_audio_tab(self):
        ctk.CTkLabel(self.tab_audio, text="🔊 Controles de Nivel de Audio", font=ctk.CTkFont(size=13, weight="bold"), text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(10, 5))

        vol_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        vol_frame.pack(fill="x", padx=15, pady=2)
        current_master_vol = self.config_mgr.config.get("master_volume", 1.0)
        ctk.CTkLabel(vol_frame, text="Volumen General (Altavoces):", font=ctk.CTkFont(size=11), text_color="#D3DDE5").pack(side="left")
        self.master_vol_label = ctk.CTkLabel(vol_frame, text=f"{int(current_master_vol * 100)}%", width=45, text_color="#8796A5")
        self.master_vol_label.pack(side="right")
        self.master_vol_slider = ctk.CTkSlider(
            vol_frame, from_=0.0, to=1.0, number_of_steps=20, progress_color="#7CEAF5", button_color="#B6FFFF",
            command=lambda v: self.master_vol_label.configure(text=f"{int(v * 100)}%")
        )
        self.master_vol_slider.set(current_master_vol)
        self.master_vol_slider.pack(side="right", fill="x", expand=True, padx=10)

        notif_vol_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        notif_vol_frame.pack(fill="x", padx=15, pady=2)
        current_notif_vol = self.config_mgr.config.get("notification_volume", 1.0)
        ctk.CTkLabel(notif_vol_frame, text="Volumen Notificaciones:", font=ctk.CTkFont(size=11), text_color="#D3DDE5").pack(side="left")
        self.notif_vol_label = ctk.CTkLabel(notif_vol_frame, text=f"{int(current_notif_vol * 100)}%", width=45, text_color="#8796A5")
        self.notif_vol_label.pack(side="right")
        self.notif_vol_slider = ctk.CTkSlider(
            notif_vol_frame, from_=0.0, to=1.0, number_of_steps=20, progress_color="#7CEAF5", button_color="#B6FFFF",
            command=lambda v: self.notif_vol_label.configure(text=f"{int(v * 100)}%")
        )
        self.notif_vol_slider.set(current_notif_vol)
        self.notif_vol_slider.pack(side="right", fill="x", expand=True, padx=10)

        mic_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        mic_frame.pack(fill="x", padx=15, pady=2)
        current_gain = self.config_mgr.config.get("mic_gain", 1.0)
        ctk.CTkLabel(mic_frame, text="Volumen/Ganancia Micrófono:", font=ctk.CTkFont(size=11), text_color="#D3DDE5").pack(side="left")
        self.mic_gain_label = ctk.CTkLabel(mic_frame, text=f"{int(current_gain * 100)}%", width=45, text_color="#8796A5")
        self.mic_gain_label.pack(side="right")
        self.mic_slider = ctk.CTkSlider(
            mic_frame, from_=0.0, to=1.0, number_of_steps=20, progress_color="#72EAB6", button_color="#B6FFFF",
            command=lambda v: self.mic_gain_label.configure(text=f"{int(v * 100)}%")
        )
        self.mic_slider.set(current_gain)
        self.mic_slider.pack(side="right", fill="x", expand=True, padx=10)

        ctk.CTkFrame(self.tab_audio, height=1, fg_color="#3A4A58").pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.tab_audio, text="🔔 Tonos y Sonidos de Notificación", font=ctk.CTkFont(size=13, weight="bold"), text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(2, 5))

        self.sound_var = ctk.BooleanVar(value=self.config_mgr.config.get("sound_enabled", True))
        ctk.CTkCheckBox(self.tab_audio, text="Notificación de Mensaje (Chat Inactivo)", variable=self.sound_var, text_color="#D3DDE5", fg_color="#7CEAF5").pack(anchor="w", padx=15, pady=2)

        msg_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        msg_frame.pack(fill="x", padx=15, pady=1)
        current_msg_sound = self.config_mgr.config.get("sound_path", "")
        self.msg_sound_label = ctk.CTkLabel(msg_frame, text=f"Tono: {os.path.basename(current_msg_sound) if current_msg_sound else 'Predeterminado'}", font=ctk.CTkFont(size=11), text_color="#8796A5")
        self.msg_sound_label.pack(side="left")
        ctk.CTkButton(msg_frame, text="Cambiar", width=65, fg_color="#202B36", hover_color="#3A4A58", text_color="#D3DDE5", command=self._browse_msg_sound).pack(side="right")

        self.active_chat_sound_var = ctk.BooleanVar(value=self.config_mgr.config.get("active_chat_sound_enabled", True))
        ctk.CTkCheckBox(self.tab_audio, text="Notificación de Mensaje (Chat Activo)", variable=self.active_chat_sound_var, text_color="#D3DDE5", fg_color="#7CEAF5").pack(anchor="w", padx=15, pady=(5, 2))

        active_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        active_frame.pack(fill="x", padx=15, pady=1)
        current_active_sound = self.config_mgr.config.get("active_chat_sound_path", "")
        self.active_sound_label = ctk.CTkLabel(active_frame, text=f"Tono: {os.path.basename(current_active_sound) if current_active_sound else 'Predeterminado'}", font=ctk.CTkFont(size=11), text_color="#8796A5")
        self.active_sound_label.pack(side="left")
        ctk.CTkButton(active_frame, text="Cambiar", width=65, fg_color="#202B36", hover_color="#3A4A58", text_color="#D3DDE5", command=self._browse_active_chat_sound).pack(side="right")

        self.call_sound_var = ctk.BooleanVar(value=self.config_mgr.config.get("call_sound_enabled", True))
        ctk.CTkCheckBox(self.tab_audio, text="Tono de Videollamada Entrante", variable=self.call_sound_var, text_color="#D3DDE5", fg_color="#7CEAF5").pack(anchor="w", padx=15, pady=(5, 2))

        call_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        call_frame.pack(fill="x", padx=15, pady=1)
        current_call_sound = self.config_mgr.config.get("call_sound_path", "")
        self.call_sound_label = ctk.CTkLabel(call_frame, text=f"Tono: {os.path.basename(current_call_sound) if current_call_sound else 'Predeterminado'}", font=ctk.CTkFont(size=11), text_color="#8796A5")
        self.call_sound_label.pack(side="left")
        ctk.CTkButton(call_frame, text="Cambiar", width=65, fg_color="#202B36", hover_color="#3A4A58", text_color="#D3DDE5", command=self._browse_call_sound).pack(side="right")

        self.outgoing_call_sound_var = ctk.BooleanVar(value=self.config_mgr.config.get("outgoing_call_sound_enabled", True))
        ctk.CTkCheckBox(self.tab_audio, text="Tono de Videollamada Saliente", variable=self.outgoing_call_sound_var, text_color="#D3DDE5", fg_color="#7CEAF5").pack(anchor="w", padx=15, pady=(5, 2))

        out_call_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        out_call_frame.pack(fill="x", padx=15, pady=1)
        current_out_call_sound = self.config_mgr.config.get("outgoing_call_sound_path", "")
        self.out_call_sound_label = ctk.CTkLabel(out_call_frame, text=f"Tono: {os.path.basename(current_out_call_sound) if current_out_call_sound else 'Predeterminado'}", font=ctk.CTkFont(size=11), text_color="#8796A5")
        self.out_call_sound_label.pack(side="left")
        ctk.CTkButton(out_call_frame, text="Cambiar", width=65, fg_color="#202B36", hover_color="#3A4A58", text_color="#D3DDE5", command=self._browse_outgoing_call_sound).pack(side="right")

        self.presence_sound_var = ctk.BooleanVar(value=self.config_mgr.config.get("presence_sound_enabled", True))
        ctk.CTkCheckBox(self.tab_audio, text="Sonidos de Conexión y Desconexión", variable=self.presence_sound_var, text_color="#D3DDE5", fg_color="#7CEAF5").pack(anchor="w", padx=15, pady=(5, 2))

        conn_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        conn_frame.pack(fill="x", padx=15, pady=1)
        current_conn_sound = self.config_mgr.config.get("presence_connect_sound_path", "")
        self.conn_sound_label = ctk.CTkLabel(conn_frame, text=f"Conexión: {os.path.basename(current_conn_sound) if current_conn_sound else 'Predeterminado'}", font=ctk.CTkFont(size=11), text_color="#8796A5")
        self.conn_sound_label.pack(side="left")
        ctk.CTkButton(conn_frame, text="Cambiar", width=65, fg_color="#202B36", hover_color="#3A4A58", text_color="#D3DDE5", command=self._browse_connect_sound).pack(side="right")

        disconn_frame = ctk.CTkFrame(self.tab_audio, fg_color="transparent")
        disconn_frame.pack(fill="x", padx=15, pady=1)
        current_disconn_sound = self.config_mgr.config.get("presence_disconnect_sound_path", "")
        self.disconn_sound_label = ctk.CTkLabel(disconn_frame, text=f"Desconexión: {os.path.basename(current_disconn_sound) if current_disconn_sound else 'Predeterminado'}", font=ctk.CTkFont(size=11), text_color="#8796A5")
        self.disconn_sound_label.pack(side="left")
        ctk.CTkButton(disconn_frame, text="Cambiar", width=65, fg_color="#202B36", hover_color="#3A4A58", text_color="#D3DDE5", command=self._browse_disconnect_sound).pack(side="right")

    def _browse_msg_sound(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Tono de Notificación", filetypes=[("Archivos de Audio", "*.wav *.mp3")])
        if filepath and self.config_mgr.set_custom_sound(filepath, "sound_path"):
            self.msg_sound_label.configure(text=f"Tono: {os.path.basename(filepath)}")

    def _browse_active_chat_sound(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Tono de Chat Activo", filetypes=[("Archivos de Audio", "*.wav *.mp3")])
        if filepath and self.config_mgr.set_custom_sound(filepath, "active_chat_sound_path"):
            self.active_sound_label.configure(text=f"Tono: {os.path.basename(filepath)}")

    def _browse_call_sound(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Tono de Videollamada Entrante", filetypes=[("Archivos de Audio", "*.wav *.mp3")])
        if filepath and self.config_mgr.set_custom_sound(filepath, "call_sound_path"):
            self.call_sound_label.configure(text=f"Tono: {os.path.basename(filepath)}")

    def _browse_outgoing_call_sound(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Tono de Videollamada Saliente", filetypes=[("Archivos de Audio", "*.wav *.mp3")])
        if filepath and self.config_mgr.set_custom_sound(filepath, "outgoing_call_sound_path"):
            self.out_call_sound_label.configure(text=f"Tono: {os.path.basename(filepath)}")

    def _browse_connect_sound(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Tono de Conexión", filetypes=[("Archivos de Audio", "*.wav *.mp3")])
        if filepath and self.config_mgr.set_custom_sound(filepath, "presence_connect_sound_path"):
            self.conn_sound_label.configure(text=f"Conexión: {os.path.basename(filepath)}")

    def _browse_disconnect_sound(self):
        filepath = filedialog.askopenfilename(title="Seleccionar Tono de Desconexión", filetypes=[("Archivos de Audio", "*.wav *.mp3")])
        if filepath and self.config_mgr.set_custom_sound(filepath, "presence_disconnect_sound_path"):
            self.disconn_sound_label.configure(text=f"Desconexión: {os.path.basename(filepath)}")

    def _build_design_tab(self):
        ctk.CTkLabel(self.tab_design, text="Tipografía del Chat",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(10, 5))

        font_frame = ctk.CTkFrame(self.tab_design, fg_color="transparent")
        font_frame.pack(fill="x", padx=15, pady=2)
        font_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(font_frame, font=ctk.CTkFont(size=11), text="Tipo de Fuente:", text_color="#D3DDE5").grid(row=0, column=0, sticky="w", pady=2)
        self.font_family_option = ctk.CTkOptionMenu(
            font_frame,
            values=["Segoe UI", "Arial", "Roboto", "Consolas", "Courier New", "Verdana", "Trebuchet MS"],
            fg_color="#202B36", button_color="#3A4A58", text_color="#D3DDE5"
        )
        self.font_family_option.set(self.config_mgr.config.get("font_family", "Segoe UI"))
        self.font_family_option.grid(row=0, column=1, sticky="e", pady=2)

        ctk.CTkLabel(font_frame, font=ctk.CTkFont(size=11), text="Tamaño de Fuente:", text_color="#D3DDE5").grid(row=1, column=0, sticky="w", pady=2)
        self.font_size_option = ctk.CTkOptionMenu(
            font_frame,
            values=["11", "12", "13", "14", "15", "16", "18"],
            fg_color="#202B36", button_color="#3A4A58", text_color="#D3DDE5"
        )
        self.font_size_option.set(str(self.config_mgr.config.get("font_size", 13)))
        self.font_size_option.grid(row=1, column=1, sticky="e", pady=2)

        ctk.CTkFrame(self.tab_design, height=1, fg_color="#3A4A58").pack(
            fill="x", padx=10, pady=10)
        ctk.CTkLabel(self.tab_design, text="Colores del Chat",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(2, 5))

        color_frame = ctk.CTkFrame(self.tab_design, fg_color="transparent")
        color_frame.pack(fill="x", padx=15, pady=2)
        color_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(color_frame, font=ctk.CTkFont(size=11), text="Color Burbuja Recibida:", text_color="#D3DDE5").grid(row=0, column=0, sticky="w", pady=2)
        self.received_color_btn = ctk.CTkButton(
            color_frame,
            text="Elegir Color",
            width=140,
            fg_color=self.config_mgr.config.get("received_bubble_color", "#202B36"),
            text_color="#D3DDE5",
            command=self._pick_received_color
        )
        self.received_color_btn.grid(row=0, column=1, sticky="e", pady=2)

        ctk.CTkLabel(color_frame, font=ctk.CTkFont(size=11), text="Color Usuario Seleccionado:", text_color="#D3DDE5").grid(row=1, column=0, sticky="w", pady=2)
        self.selection_color_btn = ctk.CTkButton(
            color_frame,
            text="Elegir Color",
            width=140,
            fg_color=self.config_mgr.config.get("selection_color", "#7CEAF5"),
            text_color="#0B121C",
            command=self._pick_selection_color
        )
        self.selection_color_btn.grid(row=1, column=1, sticky="e", pady=2)

        ctk.CTkFrame(self.tab_design, height=1, fg_color="#3A4A58").pack(
            fill="x", padx=10, pady=10)
        ctk.CTkLabel(self.tab_design, text="Selecciona tu Fondo",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#7CEAF5").pack(anchor="w", padx=10, pady=(2, 5))

        self.backgrounds_scroll = ctk.CTkScrollableFrame(
            self.tab_design, width=460, height=180, fg_color="#202B36")
        self.backgrounds_scroll.pack(fill="x", padx=15, pady=2)
        self.background_buttons = {}
        self.selected_background = self.config_mgr.config.get("chat_background_path", "")

        background_actions = ctk.CTkFrame(self.tab_design, fg_color="transparent")
        background_actions.pack(fill="x", padx=15, pady=2)
        ctk.CTkButton(background_actions, text="Agregar imagen", width=110, fg_color="#202B36",
                      hover_color="#3A4A58", text_color="#D3DDE5",
                      command=self._browse_chat_background).pack(side="right", padx=(10, 0))
        self.chat_background_label = ctk.CTkLabel(
            background_actions, text=os.path.basename(self.selected_background) or "Sin imagen seleccionada",
            font=ctk.CTkFont(size=11), text_color="#8796A5",
            wraplength=300, anchor="w", justify="left")
        self.chat_background_label.pack(side="left", fill="x", expand=True)
        self._refresh_background_gallery()

    def _refresh_background_gallery(self):
        for widget in self.backgrounds_scroll.winfo_children():
            widget.destroy()
        self.background_buttons.clear()
        backgrounds_dir = os.path.join("assets", "img")
        extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        paths = [os.path.join(backgrounds_dir, name)
                 for name in sorted(os.listdir(backgrounds_dir), key=str.casefold)
                 if name.lower().endswith(extensions)] if os.path.isdir(backgrounds_dir) else []

        for path in (self.config_mgr.config.get("chat_background_path", ""),
                     self.selected_background):
            if path:
                paths.append(path)
        seen = set()
        selected = os.path.normcase(os.path.abspath(self.selected_background)) if self.selected_background else None
        for filepath in paths:
            key = os.path.normcase(os.path.abspath(filepath))
            if key in seen:
                continue
            seen.add(key)
            try:
                with Image.open(filepath) as image:
                    thumbnail = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"),
                                             (180, 108), Image.Resampling.LANCZOS)
                preview = ctk.CTkImage(light_image=thumbnail, dark_image=thumbnail, size=(90, 54))
            except Exception:
                continue
            index = len(self.background_buttons)
            button = ctk.CTkButton(
                self.backgrounds_scroll, text="", image=preview, width=100, height=70,
                fg_color="#151E29", hover_color="#3A4A58",
                border_width=3 if key == selected else 1,
                border_color="#7CEAF5" if key == selected else "#3A4A58",
                command=lambda path=filepath: self._select_chat_background(path))
            button.grid(row=index // 4, column=index % 4, padx=6, pady=10)
            self.background_buttons[key] = button
        if not self.background_buttons:
            ctk.CTkLabel(self.backgrounds_scroll,
                         text="No hay fondos disponibles.\nAgregá una imagen para comenzar.",
                         font=ctk.CTkFont(size=11), text_color="#8796A5").pack(pady=40)

    def _select_chat_background(self, filepath):
        self.selected_background = filepath
        self.pending_chat_background = filepath
        selected = os.path.normcase(os.path.abspath(filepath))
        for path, button in self.background_buttons.items():
            button.configure(border_color="#7CEAF5" if path == selected else "#3A4A58",
                             border_width=3 if path == selected else 1)
        self.chat_background_label.configure(text=os.path.basename(filepath))

    def _browse_chat_background(self):
        filepath = filedialog.askopenfilename(
            parent=self, title="Seleccionar fondo del chat",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if not filepath:
            return
        try:
            with Image.open(filepath) as image:
                image.load()
        except Exception as exc:
            messagebox.showerror("Fondo del chat", f"No se pudo abrir la imagen: {exc}", parent=self)
            return
        self._select_chat_background(filepath)
        self._refresh_background_gallery()

    def _pick_received_color(self):
        color = colorchooser.askcolor(title="Seleccionar Color de Mensajes Recibidos")[1]
        if color:
            self.config_mgr.config["received_bubble_color"] = color
            self.received_color_btn.configure(fg_color=color)

    def _pick_selection_color(self):
        color = colorchooser.askcolor(title="Seleccionar Color de Usuario Seleccionado")[1]
        if color:
            self.config_mgr.config["selection_color"] = color
            self.selection_color_btn.configure(fg_color=color)

    def _build_downloads_tab(self):
        ctk.CTkLabel(
            self.tab_downloads,
            text="📁 Directorio de Guardado",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7CEAF5"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        dir_frame = ctk.CTkFrame(self.tab_downloads, fg_color="transparent")
        dir_frame.pack(fill="x", padx=15, pady=5)

        self.downloads_path_label = ctk.CTkLabel(
            dir_frame,
            text=self.config_mgr.config.get("downloads_dir", ""),
            font=ctk.CTkFont(size=11),
            text_color="#8796A5",
            wraplength=340,
            anchor="w",
            justify="left"
        )
        self.downloads_path_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            dir_frame,
            text="Examinar...",
            width=90,
            fg_color="#202B36",
            hover_color="#3A4A58",
            text_color="#D3DDE5",
            command=self._browse_downloads_dir
        ).pack(side="right")

        ctk.CTkFrame(self.tab_downloads, height=1, fg_color="#3A4A58").pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            self.tab_downloads,
            text="⚙️ Opciones de Transferencia",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7CEAF5"
        ).pack(anchor="w", padx=10, pady=(2, 5))

        self.ask_download_var = ctk.BooleanVar(value=self.config_mgr.config.get("ask_before_download", False))
        ctk.CTkCheckBox(
            self.tab_downloads,
            text="Preguntar siempre dónde guardar antes de descargar",
            variable=self.ask_download_var,
            text_color="#D3DDE5",
            fg_color="#7CEAF5"
        ).pack(anchor="w", padx=15, pady=5)

    def _browse_downloads_dir(self):
        chosen_dir = filedialog.askdirectory(
            parent=self,
            title="Seleccionar carpeta de descargas",
            initialdir=self.config_mgr.config.get("downloads_dir", "")
        )
        if chosen_dir:
            self.downloads_path_label.configure(text=chosen_dir)

    def _build_network_tab(self):
        ctk.CTkLabel(
            self.tab_network,
            text="🌐 Monitor de Red y Transferencias",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7CEAF5"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.show_speed_var = ctk.BooleanVar(value=self.config_mgr.config.get("show_transfer_speed", True))
        ctk.CTkCheckBox(
            self.tab_network,
            text="Mostrar velocidad de envío y recepción de archivos en el chat",
            variable=self.show_speed_var,
            text_color="#D3DDE5",
            fg_color="#7CEAF5"
        ).pack(anchor="w", padx=15, pady=10)

    def save(self):
        fn = self.fn_entry.get().strip()
        ln = self.ln_entry.get().strip()
        if fn and ln:
            if self.pending_chat_background:
                try:
                    with Image.open(self.pending_chat_background) as image:
                        image.load()
                    self.config_mgr.set_chat_background(self.pending_chat_background)
                except Exception as exc:
                    messagebox.showerror("Fondo del chat", f"No se pudo guardar la imagen: {exc}", parent=self)
                    return
            self.config_mgr.config["first_name"] = fn
            self.config_mgr.config["last_name"] = ln
            self.config_mgr.config["avatar_filename"] = self.selected_avatar
            self.config_mgr.config["master_volume"] = float(self.master_vol_slider.get())
            self.config_mgr.config["notification_volume"] = float(self.notif_vol_slider.get())
            self.config_mgr.config["mic_gain"] = float(self.mic_slider.get())
            self.config_mgr.config["sound_enabled"] = self.sound_var.get()
            self.config_mgr.config["active_chat_sound_enabled"] = self.active_chat_sound_var.get()
            self.config_mgr.config["call_sound_enabled"] = self.call_sound_var.get()
            self.config_mgr.config["outgoing_call_sound_enabled"] = self.outgoing_call_sound_var.get()
            self.config_mgr.config["presence_sound_enabled"] = self.presence_sound_var.get()
            self.config_mgr.config["font_family"] = self.font_family_option.get()
            self.config_mgr.config["font_size"] = int(self.font_size_option.get())
            self.config_mgr.config["downloads_dir"] = self.downloads_path_label.cget("text")
            self.config_mgr.config["ask_before_download"] = self.ask_download_var.get()
            self.config_mgr.config["show_transfer_speed"] = self.show_speed_var.get()
            self.config_mgr.save_config()
            self.on_update()
            self.destroy()


class IncomingCallDialog(ctk.CTkToplevel):
    def __init__(self, parent, caller_name, is_video=True, on_accept=None, on_reject=None):
        super().__init__(parent)
        title_type = "📹 Videollamada Entrante" if is_video else "📞 Llamada de Voz Entrante"
        self.title(f"OmniLan - {title_type}")
        self.geometry("350x200")
        self.resizable(False, False)
        self.configure(fg_color="#0B121C")
        self.on_accept_cb = on_accept
        self.on_reject_cb = on_reject

        ico_path = os.path.join("assets", "ico", "omnilan.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=title_type,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#7CEAF5"
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            self,
            text=f"{caller_name}\nte está llamando...",
            font=ctk.CTkFont(size=14),
            text_color="#D3DDE5"
        ).pack(pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame,
            text="Aceptar",
            fg_color="#72EAB6",
            hover_color="#55D9F2",
            text_color="#0B121C",
            font=ctk.CTkFont(weight="bold"),
            width=110,
            command=self._accept
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Rechazar",
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="white",
            font=ctk.CTkFont(weight="bold"),
            width=110,
            command=self._reject
        ).pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", self._reject)

    def _safe_close(self):
        try:
            self.withdraw()
            self.after(100, self.destroy)
        except Exception:
            pass

    def _accept(self):
        cb = self.on_accept_cb
        self._safe_close()
        if cb:
            cb()

    def _reject(self):
        cb = self.on_reject_cb
        self._safe_close()
        if cb:
            cb()