from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
import sys, psutil, joblib, pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

model = joblib.load("/Users/adityaverma/Desktop/RansomwareMonitorApp/ransomware_rf_model1.joblib")

# Global counters
file_creations = 0
file_deletions = 0
file_modifications = 0
file_renames = 0

class RansomwareBehaviorHandler(FileSystemEventHandler):
    def on_created(self, event): global file_creations; file_creations += 1
    def on_deleted(self, event): global file_deletions; file_deletions += 1
    def on_modified(self, event): global file_modifications; file_modifications += 1
    def on_moved(self, event): global file_renames; file_renames += 1

class MonitorThread(QThread):
    update_signal = pyqtSignal(dict)

    def __init__(self, path_to_watch):
        super().__init__()
        self.path_to_watch = path_to_watch
        self.running = True

    def run(self):
        global file_creations, file_deletions, file_modifications, file_renames
        handler = RansomwareBehaviorHandler()
        observer = Observer()
        observer.schedule(handler, path=self.path_to_watch, recursive=True)
        observer.start()

        while self.running:
            cpu = psutil.cpu_percent(interval=1)
            X = pd.DataFrame([{
                'file_modifications': file_modifications,
                'file_creations': file_creations,
                'file_deletions': file_deletions,
                'file_entropy': 0.5,
                'file_renames': file_renames,
                'cpu_usage': cpu
            }])

            pred = model.predict(X)[0]
            result = {
                "cpu": cpu,
                "creations": file_creations,
                "deletions": file_deletions,
                "modifications": file_modifications,
                "renames": file_renames,
                "status": "RANSOMWARE DETECTED" if pred == 1 else "System Safe",
                "danger": pred == 1
            }

            file_creations = file_deletions = file_modifications = file_renames = 0
            self.update_signal.emit(result)
            time.sleep(5)

        observer.stop()
        observer.join()

    def stop(self):
        self.running = False

class RansomwareUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🛡️ Ransomware Monitor")
        self.setGeometry(200, 200, 600, 400)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #0f2027, stop:1 #203a43);
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 15px;
            }
            QLabel#statusLabel {
                font-size: 28px;
                font-weight: 900;
                color: #00ff99;
                text-shadow: 0 0 10px #00ff99;
            }
            QLabel#statusLabel.danger {
                color: #ff5555;
                text-shadow: 0 0 20px #ff0000;
                animation: blink 1s infinite;
            }
            QLabel {
                padding: 6px;
            }
            QPushButton {
                background-color: #1b2735;
                border: 2px solid #00ff99;
                border-radius: 12px;
                padding: 12px 25px;
                color: #00ff99;
                font-weight: bold;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #00ff99;
                color: #0a0a0a;
                font-size: 18px;
            }
            QProgressBar {
                border: 2px solid #00ff99;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                color: #00ff99;
                background: #1b2735;
            }
            QProgressBar::chunk {
                background-color: #00ff99;
                border-radius: 10px;
            }
            QFrame#separator {
                background-color: #00ff99;
                max-height: 2px;
                margin: 15px 0;
            }
            @keyframes blink {
                0% { opacity: 1; }
                50% { opacity: 0.3; }
                100% { opacity: 1; }
            }
        """)

        layout = QVBoxLayout()

        self.status_label = QLabel("System Status: Unknown")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.cpu_label = QLabel("CPU Usage: 0%")
        self.file_stats = QLabel(
            "Files Created: 0\n"
            "Files Deleted: 0\n"
            "Files Modified: 0\n"
            "Files Renamed: 0"
        )
        self.file_stats.setAlignment(Qt.AlignLeft)  # Left align text for better readability


        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        self.button_start = QPushButton("Start Monitoring")
        self.button_stop = QPushButton("Stop Monitoring")
        self.button_stop.setEnabled(False)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.button_start)
        hlayout.addWidget(self.button_stop)

        layout.addWidget(self.status_label)
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_progress)
        layout.addWidget(self.file_stats)
        layout.addWidget(separator)
        layout.addLayout(hlayout)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None

        self.button_start.clicked.connect(self.start_monitoring)
        self.button_stop.clicked.connect(self.stop_monitoring)

    def start_monitoring(self):
        self.thread = MonitorThread(path_to_watch="/Users/adityaverma")
        self.thread.update_signal.connect(self.update_ui)
        self.thread.start()
        self.button_start.setEnabled(False)
        self.button_stop.setEnabled(True)
        self.status_label.setText("🔄 Monitoring...")

    def stop_monitoring(self):
        if self.thread:
            self.thread.stop()
            self.thread.quit()
            self.thread.wait()
            self.button_start.setEnabled(True)
            self.button_stop.setEnabled(False)
            self.status_label.setText("⏹️ Monitoring Stopped")
            self.status_label.setStyleSheet("color: #e0e0e0; text-shadow: none; font-size: 28px; font-weight: 900;")

    def update_ui(self, data):
        if data["danger"]:
            self.status_label.setText(f"⚠️ {data['status']}")
            self.status_label.setProperty("class", "danger")
            self.status_label.setStyleSheet(self.status_label.styleSheet())  # Trigger stylesheet update for animation
        else:
            self.status_label.setText(f"🛡️ {data['status']}")
            self.status_label.setProperty("class", "")
            self.status_label.setStyleSheet("font-size: 28px; font-weight: 900; color: #00ff99; text-shadow: 0 0 10px #00ff99;")

        self.cpu_label.setText(f"CPU Usage: {data['cpu']}%")
        self.cpu_progress.setValue(int(data["cpu"]))
        self.file_stats.setText(
            f"Files Created: {data['creations']}\n"
            f"Files Deleted: {data['deletions']}\n"
            f"Files Modified: {data['modifications']}\n"
            f"Files Renamed: {data['renames']}"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RansomwareUI()
    window.show()
    sys.exit(app.exec_())
