"""Forward Explorer image launches while allowing deliberate independent windows."""
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path
from PyQt6.QtCore import QObject, QDir, QLockFile, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


def launch_arguments(arguments):
    force_new = '--new-instance' in arguments
    values = [value for value in arguments if value != '--new-instance']
    if not values:
        return None, force_new
    value = values[0]
    path = QUrl(value).toLocalFile() if value.startswith('file:') else value
    return str(Path(path).resolve()), force_new


class InstanceBroker(QObject):
    image_requested = pyqtSignal(str)

    def __init__(self, parent=None, name=None):
        super().__init__(parent)
        user = hashlib.sha256(getpass.getuser().encode()).hexdigest()[:16]
        self.name = name or f'TABaTABCash-{user}'
        self.lock = QLockFile(str(Path(QDir.tempPath()) / f'{self.name}.lock'))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self.connections = {}
        self.election = QTimer(self)
        self.election.setInterval(1000)
        self.election.timeout.connect(self.try_own)

    def try_own(self):
        if self.server.isListening():
            return True
        if not self.lock.tryLock(0):
            return False
        # Only the lock owner may clean a stale server endpoint.
        QLocalServer.removeServer(self.name)
        if self.server.listen(self.name):
            return True
        self.lock.unlock()
        return False

    def forward(self, path):
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if not socket.waitForConnected(1000):
            return False
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(0xffffffff)
        socket.write((json.dumps({'path': path}, ensure_ascii=False) + '\n').encode('utf-8'))
        socket.flush()
        response = bytearray()
        while b'\n' not in response:
            if not socket.waitForReadyRead(5000):
                socket.abort()
                return False
            response.extend(bytes(socket.readAll()))
        socket.disconnectFromServer()
        return bytes(response).strip() == b'OK'

    def start(self, path=None, force_new=False):
        if path and not force_new:
            for _ in range(3):
                if self.forward(path):
                    return False
                if self.try_own():
                    break
        else:
            self.try_own()
        self.election.start()
        return True

    def _accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self.connections[socket] = bytearray()
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(lambda s=socket: self._discard(s))
            QTimer.singleShot(10000, lambda s=socket: s.abort() if s in self.connections else None)
            self._read(socket)

    def _read(self, socket):
        data = self.connections.get(socket)
        if data is None:
            return
        data.extend(bytes(socket.readAll()))
        if len(data) > 65536:
            socket.abort()
            return
        if b'\n' not in data:
            return
        try:
            payload = json.loads(bytes(data).split(b'\n', 1)[0].decode('utf-8'))
            path = payload['path']
            if not isinstance(path, str) or not path:
                raise ValueError('Invalid path')
        except (ValueError, KeyError, TypeError):
            socket.abort()
            return
        socket.write(b'OK\n')
        socket.flush()
        self.connections.pop(socket, None)
        # Acknowledge before showing a possible save-rotation dialog.
        QTimer.singleShot(0, lambda: self.image_requested.emit(path))
        socket.disconnectFromServer()

    def _discard(self, socket):
        self.connections.pop(socket, None)
        socket.deleteLater()

    def close(self):
        self.election.stop()
        self.server.close()
        if self.lock.isLocked():
            self.lock.unlock()
