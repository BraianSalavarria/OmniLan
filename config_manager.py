import json
import os
import shutil

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SOUNDS_DIR = "sounds"
AVATARS_DIR = os.path.join("assets", "avatars")
CHAT_IMAGES_DIR = os.path.join("assets", "img")

DEFAULT_CONFIG = {
    "first_name": "",
    "last_name": "",
    "avatar_filename": "",
    "master_volume": 1.0,
    "notification_volume": 1.0,
    "mic_gain": 1.0,
    "sound_enabled": True,
    "sound_path": "",
    "active_chat_sound_enabled": True,
    "active_chat_sound_path": "",
    "presence_sound_enabled": True,
    "presence_connect_sound_path": "",
    "presence_disconnect_sound_path": "",
    "call_sound_enabled": True,
    "call_sound_path": "",
    "outgoing_call_sound_enabled": True,
    "outgoing_call_sound_path": "",
    "chat_background_path": "",
    "font_family": "Segoe UI",
    "font_size": 13,
    "received_bubble_color": "#202B36",
    "selection_color": "#7CEAF5"
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self._ensure_directories()
        self.load_config()

    def _ensure_directories(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        if not os.path.exists(SOUNDS_DIR):
            os.makedirs(SOUNDS_DIR)
        if not os.path.exists(AVATARS_DIR):
            os.makedirs(AVATARS_DIR)
        os.makedirs(CHAT_IMAGES_DIR, exist_ok=True)

    def set_chat_background(self, source_filepath):
        """Copia el fondo y prepara su ruta relativa para guardar la configuración."""
        self._ensure_directories()
        filename = os.path.basename(source_filepath)
        destination = os.path.join(CHAT_IMAGES_DIR, filename)
        if os.path.abspath(source_filepath) != os.path.abspath(destination):
            shutil.copy2(source_filepath, destination)
        self.config["chat_background_path"] = destination.replace(os.sep, "/")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
            except Exception as e:
                print(f"Error cargando {CONFIG_FILE}: {e}")

    def save_config(self):
        self._ensure_directories()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando {CONFIG_FILE}: {e}")

    def is_configured(self):
        return bool(self.config.get("first_name") and self.config.get("last_name"))

    def get_initials(self):
        fn = self.config.get("first_name", "").strip()
        ln = self.config.get("last_name", "").strip()
        f_init = fn[0].upper() if fn else ""
        l_init = ln[0].upper() if ln else ""
        return f"{f_init}{l_init}"

    def set_custom_sound(self, source_filepath, key_path="sound_path"):
        if not os.path.exists(source_filepath):
            return False

        self._ensure_directories()
        filename = os.path.basename(source_filepath)
        dest_filepath = os.path.join(SOUNDS_DIR, filename)

        try:
            if os.path.abspath(source_filepath) != os.path.abspath(dest_filepath):
                shutil.copy2(source_filepath, dest_filepath)

            self.config[key_path] = dest_filepath
            self.save_config()
            return True
        except Exception as e:
            print(f"Error al copiar el sonido a {SOUNDS_DIR}: {e}")
            return False