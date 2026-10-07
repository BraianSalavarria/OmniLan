import socket
import threading
import json
import time
import os

BROADCAST_PORT = 30001
TCP_CHAT_PORT = 30002
CALL_SIGNAL_PORT = 30005
TCP_FILE_PORT = 30006
CHUNK_SIZE = 1024 * 1024  # 1 MB para máxima velocidad en LAN

class NetworkEngine:
    def __init__(self, get_user_info_callback, on_user_list_changed, on_message_received, on_typing_status_changed, on_call_event, on_file_offer=None, on_file_progress=None, on_file_canceled=None):
        self.get_user_info_callback = get_user_info_callback
        self.on_user_list_changed = on_user_list_changed
        self.on_message_received = on_message_received
        self.on_typing_status_changed = on_typing_status_changed
        self.on_call_event = on_call_event
        self.on_file_offer = on_file_offer
        self.on_file_progress = on_file_progress
        self.on_file_canceled = on_file_canceled

        self.active_transfers = {}
        self.active_users = {}
        self.running = True

        self.my_ip = self._get_local_ip()

        self._start_udp_broadcast_listener()
        self._start_udp_broadcast_sender()
        self._start_tcp_chat_server()
        self._start_tcp_file_server()
        self._start_call_signal_listener()
        self._start_user_cleanup_thread()

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _start_call_signal_listener(self):
        def listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('', CALL_SIGNAL_PORT))
            except Exception as e:
                print(f"[NetworkEngine] No se pudo vincular puerto de señal de llamada {CALL_SIGNAL_PORT}: {e}")
                return

            sock.settimeout(1.0)

            while self.running:
                try:
                    data, addr = sock.recvfrom(2048)
                    msg = json.loads(data.decode('utf-8'))
                    if self.on_call_event:
                        self.on_call_event(addr[0], msg)
                except socket.timeout:
                    continue
                except Exception:
                    pass
            sock.close()

        threading.Thread(target=listen, daemon=True).start()

    def send_call_request(self, target_ip, is_video=True):
        my_info = self.get_user_info_callback()
        payload = {
            "type": "CALL_REQUEST",
            "caller_name": my_info["full_name"],
            "is_video": is_video
        }
        self._send_udp_json(target_ip, CALL_SIGNAL_PORT, payload)

    def send_call_response(self, target_ip, accepted, is_video=True):
        payload = {
            "type": "CALL_RESPONSE",
            "accepted": accepted,
            "is_video": is_video
        }
        self._send_udp_json(target_ip, CALL_SIGNAL_PORT, payload)

    def send_call_end(self, target_ip):
        payload = {"type": "CALL_END"}
        self._send_udp_json(target_ip, CALL_SIGNAL_PORT, payload)

    def _send_udp_json(self, ip, port, data_dict):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            msg = json.dumps(data_dict).encode('utf-8')
            sock.sendto(msg, (ip, port))
            sock.close()
        except Exception as e:
            print(f"[NetworkEngine] Error enviando UDP señal: {e}")

    def _start_udp_broadcast_listener(self):
        def listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            try:
                sock.bind(('', BROADCAST_PORT))
            except Exception as e:
                print(f"[NetworkEngine] Error vinculando puerto Broadcast {BROADCAST_PORT}: {e}")
                return

            sock.settimeout(1.0)

            while self.running:
                try:
                    data, addr = sock.recvfrom(1024)
                    ip = addr[0]
                    if ip == self.my_ip:
                        continue

                    msg = json.loads(data.decode('utf-8'))
                    if msg.get("type") == "PRESENCE":
                        self.active_users[ip] = {
                            "name": msg.get("name"),
                            "initials": msg.get("initials"),
                            "avatar": msg.get("avatar", ""),
                            "last_seen": time.time()
                        }
                        self.on_user_list_changed(self.active_users)
                except socket.timeout:
                    continue
                except Exception:
                    pass
            sock.close()

        threading.Thread(target=listen, daemon=True).start()

    def _start_udp_broadcast_sender(self):
        def send_presence():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            while self.running:
                try:
                    info = self.get_user_info_callback()
                    payload = {
                        "type": "PRESENCE",
                        "name": info["full_name"],
                        "initials": info["initials"],
                        "avatar": info.get("avatar", "")
                    }
                    msg = json.dumps(payload).encode('utf-8')
                    sock.sendto(msg, ('<broadcast>', BROADCAST_PORT))
                except Exception:
                    pass
                time.sleep(3)
            sock.close()

        threading.Thread(target=send_presence, daemon=True).start()

    def _start_tcp_chat_server(self):
        def server_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('', TCP_CHAT_PORT))
            except Exception as e:
                print(f"[NetworkEngine] Error vinculando puerto TCP {TCP_CHAT_PORT}: {e}")
                return

            sock.listen(5)
            sock.settimeout(1.0)

            while self.running:
                try:
                    conn, addr = sock.accept()
                    threading.Thread(target=self._handle_tcp_client, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception:
                    pass
            sock.close()

        threading.Thread(target=server_loop, daemon=True).start()

    def _handle_tcp_client(self, conn, addr):
        try:
            raw_len = conn.recv(4)
            if not raw_len:
                return
            msg_len = int.from_bytes(raw_len, 'big')

            chunks = []
            bytes_recvd = 0
            while bytes_recvd < msg_len:
                chunk = conn.recv(min(msg_len - bytes_recvd, 4096))
                if not chunk:
                    break
                chunks.append(chunk)
                bytes_recvd += len(chunk)

            data = b''.join(chunks)
            payload = json.loads(data.decode('utf-8'))

            msg_type = payload.get("type")
            avatar = payload.get("avatar", "")

            if msg_type == "TEXT":
                self.on_message_received(addr[0], payload["initials"], payload["content"], "text", avatar=avatar)
            elif msg_type == "TYPING":
                self.on_typing_status_changed(addr[0], payload["is_typing"])
            elif msg_type == "AUDIO":
                audio_bytes = bytes.fromhex(payload["audio_hex"])
                filename = f"recv_voice_{int(time.time())}.wav"
                filepath = os.path.join("recordings", filename)
                if not os.path.exists("recordings"):
                    os.makedirs("recordings")
                with open(filepath, "wb") as f:
                    f.write(audio_bytes)
                self.on_message_received(addr[0], payload["initials"], filepath, "audio", avatar=avatar)
            elif msg_type == "FILE_OFFER":
                if self.on_file_offer:
                    self.on_file_offer(
                        sender_ip=addr[0],
                        initials=payload.get("initials", ""),
                        file_id=payload["file_id"],
                        file_name=payload["file_name"],
                        file_size=payload["file_size"],
                        file_path=payload["file_path"],
                        avatar=avatar
                    )
            elif msg_type == "CANCEL_FILE":
                file_id = payload.get("file_id")
                if file_id in self.active_transfers:
                    self.active_transfers[file_id] = False
                if self.on_file_canceled:
                    self.on_file_canceled(file_id)

        except Exception as e:
            print(f"[NetworkEngine] Error recibiendo paquete TCP: {e}")
        finally:
            conn.close()

    def _start_tcp_file_server(self):
        def file_server_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('', TCP_FILE_PORT))
            except Exception as e:
                print(f"[NetworkEngine] Error vinculando puerto TCP Archivos {TCP_FILE_PORT}: {e}")
                return

            sock.listen(10)
            sock.settimeout(1.0)

            while self.running:
                try:
                    conn, addr = sock.accept()
                    threading.Thread(target=self._handle_file_download_request, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception:
                    pass
            sock.close()

        threading.Thread(target=file_server_loop, daemon=True).start()

    def _handle_file_download_request(self, conn, addr):
        try:
            raw_len = conn.recv(4)
            if not raw_len:
                return
            meta_len = int.from_bytes(raw_len, 'big')

            chunks = []
            recvd = 0
            while recvd < meta_len:
                c = conn.recv(min(meta_len - recvd, 4096))
                if not c:
                    break
                chunks.append(c)
                recvd += len(c)

            data = b''.join(chunks)
            req = json.loads(data.decode('utf-8'))

            file_path = req.get("file_path")
            file_id = req.get("file_id")
            self.active_transfers[file_id] = True

            if file_path and os.path.exists(file_path):
                total_size = os.path.getsize(file_path)
                bytes_sent = 0

                with open(file_path, "rb") as f:
                    while self.running and self.active_transfers.get(file_id, True):
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                        bytes_sent += len(chunk)
                        if self.on_file_progress:
                            self.on_file_progress(file_id, bytes_sent, total_size, "sending")

        except Exception as e:
            print(f"[NetworkEngine] Error sirviendo archivo TCP: {e}")
        finally:
            conn.close()

    def send_file_offer(self, target_ip, file_id, file_path):
        if not os.path.exists(file_path):
            return

        info = self.get_user_info_callback()
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        payload = {
            "type": "FILE_OFFER",
            "initials": info["initials"],
            "avatar": info.get("avatar", ""),
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "file_path": file_path
        }
        self._send_tcp_json(target_ip, payload)

    def cancel_file_transfer(self, target_ip, file_id):
        self.active_transfers[file_id] = False
        payload = {
            "type": "CANCEL_FILE",
            "file_id": file_id
        }
        self._send_tcp_json(target_ip, payload)

    def download_file_from_peer(self, target_ip, file_id, remote_file_path, save_dest_path, total_size):
        def download_thread():
            self.active_transfers[file_id] = True
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                sock.connect((target_ip, TCP_FILE_PORT))

                req = {
                    "file_id": file_id,
                    "file_path": remote_file_path
                }
                data = json.dumps(req).encode('utf-8')
                sock.sendall(len(data).to_bytes(4, 'big') + data)

                os.makedirs(os.path.dirname(save_dest_path), exist_ok=True)
                received_bytes = 0

                with open(save_dest_path, "wb") as f:
                    while received_bytes < total_size and self.running and self.active_transfers.get(file_id, True):
                        chunk = sock.recv(min(CHUNK_SIZE, total_size - received_bytes))
                        if not chunk:
                            break
                        f.write(chunk)
                        f.flush()
                        received_bytes += len(chunk)
                        if self.on_file_progress:
                            self.on_file_progress(file_id, received_bytes, total_size, "receiving")

                sock.close()
                if not self.active_transfers.get(file_id, True) and os.path.exists(save_dest_path):
                    try:
                        os.remove(save_dest_path)
                    except Exception:
                        pass

            except Exception as e:
                print(f"[NetworkEngine] Error descargando archivo de {target_ip}: {e}")

        threading.Thread(target=download_thread, daemon=True).start()

    def send_message(self, target_ip, content):
        info = self.get_user_info_callback()
        payload = {
            "type": "TEXT",
            "initials": info["initials"],
            "avatar": info.get("avatar", ""),
            "content": content
        }
        self._send_tcp_json(target_ip, payload)

    def send_typing_status(self, target_ip, is_typing):
        payload = {
            "type": "TYPING",
            "is_typing": is_typing
        }
        self._send_tcp_json(target_ip, payload)

    def send_audio(self, target_ip, audio_filepath):
        if not os.path.exists(audio_filepath):
            return
        try:
            with open(audio_filepath, "rb") as f:
                audio_bytes = f.read()

            info = self.get_user_info_callback()
            payload = {
                "type": "AUDIO",
                "initials": info["initials"],
                "avatar": info.get("avatar", ""),
                "audio_hex": audio_bytes.hex()
            }
            self._send_tcp_json(target_ip, payload)
        except Exception as e:
            print(f"[NetworkEngine] Error enviando audio TCP: {e}")

    def _send_tcp_json(self, target_ip, payload):
        def send_thread():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((target_ip, TCP_CHAT_PORT))

                data = json.dumps(payload).encode('utf-8')
                msg_len = len(data)
                sock.sendall(msg_len.to_bytes(4, 'big') + data)
                sock.close()
            except Exception as e:
                print(f"[NetworkEngine] Error enviando mensaje a {target_ip}: {e}")

        threading.Thread(target=send_thread, daemon=True).start()

    def _start_user_cleanup_thread(self):
        def cleanup():
            while self.running:
                now = time.time()
                to_remove = []
                for ip, data in list(self.active_users.items()):
                    if now - data["last_seen"] > 20:
                        to_remove.append(ip)

                if to_remove:
                    for ip in to_remove:
                        del self.active_users[ip]
                    self.on_user_list_changed(self.active_users)

                time.sleep(3)

        threading.Thread(target=cleanup, daemon=True).start()

    def stop(self):
        self.running = False