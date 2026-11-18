"""Einzelinstanz-Schutz (T1): QLocalServer mit festem Namen. Zweite Instanz schickt 'show' an die erste und beendet sich."""
from __future__ import annotations

import getpass

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

NAME = f"MXRouty-{getpass.getuser()}"


class SingleInstance(QObject):
    show_requested = Signal()  # andere Instanz wurde gestartet -> Fenster nach vorn

    def __init__(self):
        super().__init__()
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        """True = wir sind die erste Instanz. False = es läuft schon eine (wurde benachrichtigt)."""
        sock = QLocalSocket()
        sock.connectToServer(NAME)
        if sock.waitForConnected(300):
            sock.write(b"show"); sock.waitForBytesWritten(300); sock.disconnectFromServer()
            return False
        QLocalServer.removeServer(NAME)  # Leiche nach Absturz entfernen
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        return self._server.listen(NAME)

    def _on_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn:
            conn.waitForReadyRead(200); conn.readAll(); conn.close()
        self.show_requested.emit()
