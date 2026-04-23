import sys
import os
import json
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QComboBox, QStatusBar, QFrame, QSplitter,
    QHeaderView, QMenu, QAction, QProgressBar, QMessageBox,
    QSystemTrayIcon, QStyle
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSortFilterProxyModel
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette, QBrush

# ─── Renk paleti ─────────────────────────────────────────────────────────────
COLORS = {
    "bg":        "#1A1A1F",
    "surface":   "#22222A",
    "surface2":  "#2A2A35",
    "border":    "#35354A",
    "accent":    "#6C63FF",
    "accent2":   "#00D4AA",
    "text":      "#E8E8F0",
    "text2":     "#8888A0",
    "proj":      ("#1D4D3E", "#00D4AA"),   # bg, fg
    "tool":      ("#1A2E4A", "#5BA3FF"),
    "doc":       ("#3D1F3D", "#D47FD4"),
    "media":     ("#3D2E1A", "#D4A04A"),
    "zip":       ("#2A2A35", "#8888A0"),
    "trash":     ("#3D1A1A", "#D45050"),
    "unknown":   ("#252530", "#606075"),
}

TAG_LABELS = {
    "proje":    "Proje",
    "araç":     "Araç",
    "belge":    "Belge",
    "medya":    "Medya",
    "zip":      "Zip/Arşiv",
    "çöp":      "Çöp",
    "bilinmiyor": "?",
}

TAG_COLORS = {
    "proje":    COLORS["proj"],
    "araç":     COLORS["tool"],
    "belge":    COLORS["doc"],
    "medya":    COLORS["media"],
    "zip":      COLORS["zip"],
    "çöp":      COLORS["trash"],
    "bilinmiyor": COLORS["unknown"],
}

# ─── Proje tespiti ────────────────────────────────────────────────────────────
PROJECT_MARKERS = [
    "main.py", "app.py", "requirements.txt", "setup.py", "pyproject.toml",
    "package.json", "index.js", "index.html", "main.cpp", "CMakeLists.txt",
    ".git", "venv", "env", "node_modules", "Makefile", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle",
]
PROJECT_EXTS = {".ino", ".pde"}

TOOL_MARKERS = ["installer", "setup", "portable", ".exe", ".msi"]
ZIP_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".xz", ".bz2"}
DOC_EXTS = {".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".odt", ".txt", ".md"}
MEDIA_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav", ".flac", ".jpg",
              ".jpeg", ".png", ".gif", ".psd", ".ai", ".svg", ".webp"}

def detect_tag(path: Path) -> str:
    name_lower = path.name.lower()
    if path.is_file():
        ext = path.suffix.lower()
        if ext in ZIP_EXTS:       return "zip"
        if ext in DOC_EXTS:       return "belge"
        if ext in MEDIA_EXTS:     return "medya"
        if ext in PROJECT_EXTS:   return "proje"
        if ext == ".exe" or ext == ".msi": return "araç"
        return "bilinmiyor"
    # klasör
    try:
        children = [c.name for c in path.iterdir()]
    except PermissionError:
        return "bilinmiyor"
    for marker in PROJECT_MARKERS:
        if marker in children:
            return "proje"
    for child in children:
        if any(t in child.lower() for t in TOOL_MARKERS):
            return "araç"
    return "bilinmiyor"

# ─── Tarayıcı thread ──────────────────────────────────────────────────────────
class ScanWorker(QThread):
    item_found = pyqtSignal(str, str, str, bool)   # name, path, tag, is_dir
    finished   = pyqtSignal(int)
    progress   = pyqtSignal(str)

    def __init__(self, root: str, saved_tags: dict):
        super().__init__()
        self.root = root
        self.saved_tags = saved_tags
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        count = 0
        root = Path(self.root)
        try:
            entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            self.finished.emit(0)
            return

        for entry in entries:
            if self._stop:
                break
            if entry.name.startswith("."):
                continue
            tag = self.saved_tags.get(str(entry), detect_tag(entry))
            self.progress.emit(f"Tarıyor: {entry.name}")
            self.item_found.emit(entry.name, str(entry), tag, entry.is_dir())
            count += 1

        self.finished.emit(count)

# ─── Özel eleman ─────────────────────────────────────────────────────────────
class FolderItem(QTreeWidgetItem):
    def __init__(self, name, path, tag, is_dir):
        super().__init__()
        self.item_path = path
        self.item_tag  = tag
        self.is_dir    = is_dir
        self.setText(0, ("  📁 " if is_dir else "  📄 ") + name)
        self.setText(1, path)
        self.setText(2, TAG_LABELS.get(tag, "?"))
        self._apply_color(tag)

    def _apply_color(self, tag):
        bg_hex, fg_hex = TAG_COLORS.get(tag, COLORS["unknown"])
        for col in range(3):
            self.setForeground(col, QBrush(QColor(COLORS["text"])))
        self.setBackground(2, QBrush(QColor(bg_hex)))
        self.setForeground(2, QBrush(QColor(fg_hex)))

    def update_tag(self, new_tag):
        self.item_tag = new_tag
        self.setText(2, TAG_LABELS.get(new_tag, "?"))
        self._apply_color(new_tag)

# ─── Ana pencere ─────────────────────────────────────────────────────────────
class DiskIndexer(QMainWindow):
    INDEX_FILE = os.path.join(os.path.expanduser("~"), ".disk_index.json")

    def __init__(self):
        super().__init__()
        self.saved_tags = self._load_index()
        self.worker = None
        self.all_items: list[FolderItem] = []
        self._build_ui()
        self._apply_theme()

    # ── UI kurulumu ─────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Disk İndeksi")
        self.setMinimumSize(980, 640)
        self.resize(1200, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # üst toolbar
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(60)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        tb_layout.setSpacing(10)

        title = QLabel("Disk İndeksi")
        title.setObjectName("appTitle")
        tb_layout.addWidget(title)

        tb_layout.addSpacing(12)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Klasör yolu gir veya seç…")
        self.path_edit.setObjectName("pathEdit")
        self.path_edit.returnPressed.connect(self._start_scan)
        tb_layout.addWidget(self.path_edit, 1)

        btn_browse = QPushButton("Klasör Seç")
        btn_browse.setObjectName("btnSecondary")
        btn_browse.clicked.connect(self._browse)
        tb_layout.addWidget(btn_browse)

        self.btn_scan = QPushButton("  ▶  Tara")
        self.btn_scan.setObjectName("btnPrimary")
        self.btn_scan.clicked.connect(self._start_scan)
        tb_layout.addWidget(self.btn_scan)

        root_layout.addWidget(toolbar)

        # istatistik şerit
        self.stat_bar = QFrame()
        self.stat_bar.setObjectName("statBar")
        self.stat_bar.setFixedHeight(52)
        stat_layout = QHBoxLayout(self.stat_bar)
        stat_layout.setContentsMargins(16, 0, 16, 0)
        stat_layout.setSpacing(0)

        self.stat_labels = {}
        stat_defs = [
            ("toplam",  "Toplam",        COLORS["text2"]),
            ("proje",   "Proje",         COLORS["proj"][1]),
            ("araç",    "Araç",          COLORS["tool"][1]),
            ("belge",   "Belge",         COLORS["doc"][1]),
            ("medya",   "Medya",         COLORS["media"][1]),
            ("zip",     "Zip/Arşiv",     COLORS["zip"][1]),
            ("bilinmiyor","Bilinmiyor",  COLORS["unknown"][1]),
        ]
        for key, label, color in stat_defs:
            frame = QFrame()
            frame.setObjectName("statFrame")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(16, 4, 16, 4)
            fl.setSpacing(1)
            val = QLabel("0")
            val.setObjectName("statVal")
            val.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 600;")
            lbl = QLabel(label)
            lbl.setObjectName("statLbl")
            fl.addWidget(val)
            fl.addWidget(lbl)
            self.stat_labels[key] = val
            stat_layout.addWidget(frame)
            if key != "bilinmiyor":
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setObjectName("sep")
                stat_layout.addWidget(sep)

        stat_layout.addStretch()
        root_layout.addWidget(self.stat_bar)

        # filtre satırı
        filter_frame = QFrame()
        filter_frame.setObjectName("filterBar")
        filter_frame.setFixedHeight(44)
        ff_layout = QHBoxLayout(filter_frame)
        ff_layout.setContentsMargins(16, 0, 16, 0)
        ff_layout.setSpacing(8)

        ff_layout.addWidget(QLabel("Filtre:"))
        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("filterCombo")
        self.filter_combo.addItems(["Tümü", "Proje", "Araç", "Belge", "Medya", "Zip/Arşiv", "Bilinmiyor", "Çöp"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        ff_layout.addWidget(self.filter_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Ad ara…")
        self.search_edit.setObjectName("searchEdit")
        self.search_edit.textChanged.connect(self._apply_filter)
        ff_layout.addWidget(self.search_edit, 1)

        ff_layout.addStretch()

        save_btn = QPushButton("Kaydet")
        save_btn.setObjectName("btnSecondary")
        save_btn.clicked.connect(self._save_index)
        ff_layout.addWidget(save_btn)

        root_layout.addWidget(filter_frame)

        # ağaç
        self.tree = QTreeWidget()
        self.tree.setObjectName("mainTree")
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Ad", "Yol", "Etiket"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.header().resizeSection(2, 110)
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.tree.setSortingEnabled(True)
        root_layout.addWidget(self.tree)

        # progress + status
        self.progress = QProgressBar()
        self.progress.setObjectName("progressBar")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setRange(0, 0)
        self.progress.hide()
        root_layout.addWidget(self.progress)

        self.status = QStatusBar()
        self.status.setObjectName("statusBar")
        self.setStatusBar(self.status)
        self.status.showMessage("Bir klasör seçin ve Tara butonuna basın.")

    # ── Tema ────────────────────────────────────────────────────────────────
    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {COLORS["bg"]};
                color: {COLORS["text"]};
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }}
            #appTitle {{
                font-size: 16px;
                font-weight: 700;
                color: {COLORS["accent"]};
                letter-spacing: 1px;
            }}
            #toolbar {{
                background: {COLORS["surface"]};
                border-bottom: 1px solid {COLORS["border"]};
            }}
            #statBar {{
                background: {COLORS["surface"]};
                border-bottom: 1px solid {COLORS["border"]};
            }}
            #filterBar {{
                background: {COLORS["surface2"]};
                border-bottom: 1px solid {COLORS["border"]};
            }}
            #statFrame {{
                background: transparent;
            }}
            #statVal {{
                font-size: 18px;
                font-weight: 600;
            }}
            #statLbl {{
                font-size: 11px;
                color: {COLORS["text2"]};
            }}
            #sep {{
                color: {COLORS["border"]};
                max-height: 28px;
            }}
            #pathEdit, #searchEdit {{
                background: {COLORS["bg"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 6px 10px;
                color: {COLORS["text"]};
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 12px;
            }}
            #pathEdit:focus, #searchEdit:focus {{
                border-color: {COLORS["accent"]};
            }}
            #filterCombo {{
                background: {COLORS["bg"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 4px 8px;
                color: {COLORS["text"]};
                min-width: 120px;
            }}
            #filterCombo::drop-down {{ border: none; }}
            #btnPrimary {{
                background: {COLORS["accent"]};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            #btnPrimary:hover {{ background: #7D75FF; }}
            #btnPrimary:pressed {{ background: #5A52E0; }}
            #btnSecondary {{
                background: {COLORS["surface2"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 7px 14px;
            }}
            #btnSecondary:hover {{ background: {COLORS["border"]}; }}
            #mainTree {{
                background: {COLORS["bg"]};
                border: none;
                alternate-background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                outline: none;
            }}
            #mainTree::item {{
                padding: 5px 2px;
                border: none;
            }}
            #mainTree::item:selected {{
                background: {COLORS["accent"]};
                color: white;
            }}
            #mainTree::item:hover {{
                background: {COLORS["surface2"]};
            }}
            QHeaderView::section {{
                background: {COLORS["surface"]};
                color: {COLORS["text2"]};
                border: none;
                border-bottom: 1px solid {COLORS["border"]};
                padding: 6px 8px;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            QScrollBar:vertical {{
                background: {COLORS["surface"]};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS["border"]};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            #progressBar {{
                background: {COLORS["surface"]};
                border: none;
            }}
            #progressBar::chunk {{
                background: {COLORS["accent"]};
            }}
            #statusBar {{
                background: {COLORS["surface"]};
                color: {COLORS["text2"]};
                font-size: 12px;
                border-top: 1px solid {COLORS["border"]};
            }}
            QMenu {{
                background: {COLORS["surface2"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                color: {COLORS["text"]};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: {COLORS["accent"]};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS["border"]};
                margin: 4px 0;
            }}
        """)

    # ── Klasör seçimi ────────────────────────────────────────────────────────
    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", self.path_edit.text() or "C:\\")
        if folder:
            self.path_edit.setText(folder)

    # ── Tarama ──────────────────────────────────────────────────────────────
    def _start_scan(self):
        path = self.path_edit.text().strip()
        if not path or not os.path.exists(path):
            self.status.showMessage("Geçerli bir klasör yolu girin.")
            return
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.tree.clear()
        self.all_items.clear()
        self._reset_stats()
        self.progress.show()
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("  ⏳  Tarıyor…")

        self.worker = ScanWorker(path, self.saved_tags)
        self.worker.item_found.connect(self._on_item_found)
        self.worker.finished.connect(self._on_finished)
        self.worker.progress.connect(lambda msg: self.status.showMessage(msg))
        self.worker.start()

    def _on_item_found(self, name, path, tag, is_dir):
        item = FolderItem(name, path, tag, is_dir)
        self.tree.addTopLevelItem(item)
        self.all_items.append(item)
        self._update_stats()

    def _on_finished(self, count):
        self.progress.hide()
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("  ▶  Tara")
        self.status.showMessage(f"Tamamlandı — {count} öğe bulundu. Etiket eklemek için sağ tıklayın.")
        self._update_stats()

    # ── İstatistik ───────────────────────────────────────────────────────────
    def _reset_stats(self):
        for lbl in self.stat_labels.values():
            lbl.setText("0")

    def _update_stats(self):
        counts = {k: 0 for k in TAG_LABELS}
        counts["toplam"] = len(self.all_items)
        for item in self.all_items:
            if item.item_tag in counts:
                counts[item.item_tag] += 1
        self.stat_labels["toplam"].setText(str(counts["toplam"]))
        for key in TAG_LABELS:
            if key in self.stat_labels:
                self.stat_labels[key].setText(str(counts.get(key, 0)))

    # ── Filtre ───────────────────────────────────────────────────────────────
    def _apply_filter(self):
        selected = self.filter_combo.currentText()
        search   = self.search_edit.text().lower()
        tag_map  = {
            "Tümü": None, "Proje": "proje", "Araç": "araç",
            "Belge": "belge", "Medya": "medya", "Zip/Arşiv": "zip",
            "Bilinmiyor": "bilinmiyor", "Çöp": "çöp",
        }
        tag_filter = tag_map.get(selected)
        for item in self.all_items:
            name_match = search in item.item_path.lower()
            tag_match  = (tag_filter is None) or (item.item_tag == tag_filter)
            item.setHidden(not (name_match and tag_match))

    # ── Sağ tık menüsü ───────────────────────────────────────────────────────
    def _context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not isinstance(item, FolderItem):
            return
        menu = QMenu(self)

        open_action = QAction("📂  Explorer'da Aç", self)
        open_action.triggered.connect(lambda: self._open_item(item, 0))
        menu.addAction(open_action)
        menu.addSeparator()

        tag_menu = menu.addMenu("🏷  Etiket Değiştir")
        for key, label in TAG_LABELS.items():
            if key == "bilinmiyor":
                continue
            act = QAction(label, self)
            act.triggered.connect(lambda checked, k=key: self._set_tag(item, k))
            tag_menu.addAction(act)

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def _set_tag(self, item: FolderItem, new_tag: str):
        item.update_tag(new_tag)
        self.saved_tags[item.item_path] = new_tag
        self._update_stats()
        self.status.showMessage(f"'{item.item_path}' → {TAG_LABELS[new_tag]} olarak etiketlendi.")

    def _open_item(self, item, col=0):
        if not isinstance(item, FolderItem):
            return
        path = item.item_path
        if sys.platform == "win32":
            subprocess.Popen(["explorer", path] if os.path.isdir(path) else ["explorer", "/select,", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    # ── Kaydet / Yükle ───────────────────────────────────────────────────────
    def _save_index(self):
        for item in self.all_items:
            self.saved_tags[item.item_path] = item.item_tag
        try:
            with open(self.INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self.saved_tags, f, ensure_ascii=False, indent=2)
            self.status.showMessage(f"İndeks kaydedildi → {self.INDEX_FILE}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız:\n{e}")

    def _load_index(self) -> dict:
        if os.path.exists(self.INDEX_FILE):
            try:
                with open(self.INDEX_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def closeEvent(self, event):
        self._save_index()
        event.accept()


# ─── Başlat ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DiskIndexer()
    win.show()
    sys.exit(app.exec_())
