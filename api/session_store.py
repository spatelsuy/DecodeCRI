import time
import threading
import uuid

class SessionStore:
    def __init__(self, default_ttl=3600, cleanup_interval=60):
        self._store = {}
        self._ttl = default_ttl
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval

        cleaner = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleaner.start()

    def create_session(self, sessionID):
        session_id = sessionID #str(uuid.uuid4())
        with self._lock:
            self._store[session_id] = {
                "data": None,
                "expires": time.time() + self._ttl
            }
        return session_id

    def set(self, session_id, data):
        with self._lock:
            if session_id not in self._store:
                raise KeyError("Session expired or not found")
            self._store[session_id]["data"] = data
            self._store[session_id]["expires"] = time.time() + self._ttl

    def get(self, session_id):
        with self._lock:
            entry = self._store.get(session_id)
            if not entry:
                return None
            if time.time() > entry["expires"]:
                del self._store[session_id]
                return None
            return entry["data"]

    def _cleanup_loop(self):
        while True:
            time.sleep(self._cleanup_interval)
            now = time.time()
            with self._lock:
                expired = [k for k, v in self._store.items() if now > v["expires"]]
                for k in expired:
                    del self._store[k]


SESSION_STORE = SessionStore(default_ttl=3600)