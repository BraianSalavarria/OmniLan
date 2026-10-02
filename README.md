# OmniLan P2P 🚀

**OmniLan** es una aplicación de escritorio modular para comunicación en red local (LAN) de punto a punto (P2P) desarrollada en **Python**[cite: 20]. Permite a usuarios dentro de la misma red comunicarse mediante **chat de texto**, **notas de voz**, **llamadas de audio** y **videollamadas**, sin depender de servidores centralizados ni conexión a Internet.

---

## 🌟 Características Principales

* **Descubrimiento Automático de Usuarios**: Utiliza un sistema de *broadcast UDP* para detectar automáticamente otros miembros conectados en la red local[cite: 20].
* **Chat de Texto en Tiempo Real**: Transferencia directa mediante *sockets TCP* con actualización continua de estado de escritura ("escribiendo...") e historial por sesión.
* **Notas de Voz**: Grabación de notas de audio mediante PyAudio con normalización automática de picos para evitar distorsiones y reproductor multimedia integrado.
* **Llamadas y Videollamadas P2P**:
  * Transmisión de voz de baja latencia con control de ganancia de micrófono e intensidad de salida[cite: 26, 35].
  * Transmisión de video con OpenCV mediante UDP, vista previa dual (remota y local) y controles de silenciamiento[cite: 34].
* **Interfaz Personalizable (CustomTkinter)**:
  * Avatares en forma circular con sincronización de perfiles.
  * Galería de fondos de chat personalizables.
  * Ajuste de fuentes, tamaños y colores de las burbujas de chat.
  * Configuración independiente de tonos de notificación, llamadas e ingresos a la red.
* **Integración con el Sistema**:
  * Bandeja de sistema (*System Tray*) para minimizar la aplicación y recibir notificaciones sin interrumpir el flujo de trabajo.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje**: Python 3.x
* **GUI**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
* **Multimedia & Procesamiento de Imágenes**: Pillow (PIL), OpenCV, Pygame.
* **Audio & Grabación**: PyAudio, NumPy, Wave, SoundDevice, SoundFile.
* **Redes & P2P**: Sockets UDP (Broadcast y Señalización) y Sockets TCP (Chat de Texto y Transferencia).
* **Integración OS**: PyStray (System Tray Manager).

---

## 📋 Requisitos Previos

Asegúrate de tener instalado Python en tu sistema.

Dependencias necesarias (incluidas en `requirements.txt`):
```bash
cffi==2.1.1
customtkinter==6.0.0
darkdetect==0.8.0
numpy==2.5.3
opencv-python==5.0.0.93
packaging==26.3
pillow==12.3.0
pycparser==3.0
pygame==2.6.1
pystray==0.19.5
six==1.17.0
sounddevice==0.5.6
soundfile==0.14.0
typing_extensions==4.16.0
```
## 📂 Estructura del Proyecto
Plaintext
omnilan/
│
├── assets/                  # Recursos gráficos
│   ├── avatars/             # Avatares predefinidos de usuario
│   ├── ico/                 # Iconos de la aplicación (.ico)
│   └── img/                 # Fondos e imágenes auxiliares
│
├── config/                  # Archivos de configuración persistente
│   └── config.json
│
├── recordings/              # Almacenamiento temporal de notas de voz
├── sounds/                  # Tonos y efectos de sonido de notificación
│
├── audio_engine.py          # Motor de llamadas de audio P2P (PyAudio)
├── audio_recorder.py        # Grabador y normalizador de notas de voz
├── config_manager.py        # Gestor de lectura/escritura de parámetros
├── main.py                  # Ventana principal e integración del sistema
├── network_engine.py        # Motor de red (Sockets UDP/TCP y presencia)
├── notification_manager.py # Controlador de bandeja de sistema (System Tray)
├── ui_components.py         # Componentes personalizados de interfaz gráfica
├── video_engine.py          # Motor de transmisión y renderizado de video
├── voice_call_engine.py     # Ventana e interfaz de llamadas de solo voz
└── requirements.txt         # Lista de dependencias del proyecto
