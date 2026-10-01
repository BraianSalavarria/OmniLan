import threading
import pystray
from PIL import Image, ImageDraw
import os

class SystemTrayManager:
    def __init__(self, on_show_window=None, on_quit=None):
        self.on_show_window = on_show_window
        self.on_quit = on_quit
        self.icon = None
        self.thread = None
        self.badge_count = 0

    def _create_default_image(self):
        # Intenta cargar el icono oficial de OmniLan primero
        ico_path = os.path.join("assets", "ico", "omnilan.ico")
        img_path = os.path.join("assets", "img", "omnilan.png")
        
        if os.path.exists(ico_path):
            try:
                return Image.open(ico_path)
            except Exception:
                pass
        elif os.path.exists(img_path):
            try:
                return Image.open(img_path)
            except Exception:
                pass

        # Imagen genérica de respaldo en caso de que no existan los assets
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (11, 18, 28, 255))
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill=(124, 234, 245, 255))
        return image

    def start(self):
        def run_tray():
            image = self._create_default_image()
            menu = pystray.Menu(
                # default=True le indica a pystray que ejecute esta acción al hacer doble clic sobre el icono
                pystray.MenuItem("Abrir OmniLan", self._on_show, default=True),
                pystray.MenuItem("Salir", self._on_exit)
            )
            self.icon = pystray.Icon("OmniLan", image, "OmniLan P2P", menu)
            self.icon.run()

        self.thread = threading.Thread(target=run_tray, daemon=True)
        self.thread.start()

    def update_badge(self, unread_count):
        self.badge_count = unread_count
        if self.icon:
            if unread_count > 0:
                self.icon.title = f"OmniLan P2P ({unread_count} mensajes)"
            else:
                self.icon.title = "OmniLan P2P"

    def _on_show(self, icon=None, item=None):
        if self.on_show_window:
            self.on_show_window()

    def _on_exit(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass