import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QColorDialog, QSlider, QLabel,
                             QFileDialog, QShortcut)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QImage, QKeySequence

# ========== 可自定义参数 ==========
BG_COLOR = QColor("#1E3A32")       # C30 同款深墨绿
ERASER_SIZE = 40                   # 板擦默认大小
# =================================

class Whiteboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(900, 700)
        self.move(100, 100)
        self.setMouseTracking(True)

        # 页码 & 批注层
        self.current_page = 1
        self.pages = {}

        self.img = QImage(self.size(), QImage.Format_ARGB32)
        self.img.fill(BG_COLOR)
        self.last_point = None
        self.pen_color = Qt.white
        self.pen_width = 3
        self.eraser_mode = False
        self.eraser_size = ERASER_SIZE
        self.history = []
        self.transparent_mode = False
        self._push_history()

        self._init_toolbar()
        self._init_shortcuts()

    # ---------- 工具栏 ----------
    def _init_toolbar(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        bar = QHBoxLayout()
        for text, slot in [
            ("画笔", lambda: self.set_eraser(False)),
            ("板擦", lambda: self.set_eraser(True)),
            ("撤销", self.undo),
            ("清空", self.clear),
            ("颜色", self.choose_color),
            ("保存", self.save_image),
            ("透明批注", self.toggle_transparent),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        layout.addLayout(bar)

        page_bar = QHBoxLayout()
        prev_btn = QPushButton("◀ 上一页")
        prev_btn.clicked.connect(self.prev_page)
        next_btn = QPushButton("下一页 ▶")
        next_btn.clicked.connect(self.next_page)
        self.page_label = QLabel("第 1 页")
        page_bar.addWidget(prev_btn)
        page_bar.addWidget(self.page_label)
        page_bar.addWidget(next_btn)
        layout.addLayout(page_bar)

        s1 = QHBoxLayout()
        s1.addWidget(QLabel("笔粗"))
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 30)
        self.width_slider.setValue(self.pen_width)
        self.width_slider.valueChanged.connect(self.set_width)
        s1.addWidget(self.width_slider)
        layout.addLayout(s1)

        s2 = QHBoxLayout()
        s2.addWidget(QLabel("板擦"))
        self.eraser_slider = QSlider(Qt.Horizontal)
        self.eraser_slider.setRange(10, 100)
        self.eraser_slider.setValue(self.eraser_size)
        self.eraser_slider.valueChanged.connect(self.set_eraser_size)
        s2.addWidget(self.eraser_slider)
        layout.addLayout(s2)

        layout.addStretch()

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Escape"), self, self.exit_transparent)

    # ---------- 翻页 ----------
    def save_current_page(self):
        self.pages[self.current_page] = self.img.copy()

    def load_page(self, page_num):
        self.current_page = page_num
        self.page_label.setText(f"第 {page_num} 页")
        if page_num in self.pages:
            self.img = self.pages[page_num].copy()
        else:
            self.img = QImage(self.size(), QImage.Format_ARGB32)
            self.img.fill(Qt.transparent if self.transparent_mode else BG_COLOR)
        self.history = [self.img.copy()]
        self.update()

    def next_page(self):
        self.save_current_page()
        self.load_page(self.current_page + 1)

    def prev_page(self):
        if self.current_page > 1:
            self.save_current_page()
            self.load_page(self.current_page - 1)

    # ---------- 透明批注 ----------
    def toggle_transparent(self):
        if not self.transparent_mode:
            self.transparent_mode = True
            screen = QApplication.primaryScreen().geometry()
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setStyleSheet("background: transparent;")
            self.setGeometry(screen)
            self.showFullScreen()
            for k in list(self.pages.keys()):
                self.pages[k] = QImage(self.size(), QImage.Format_ARGB32)
                self.pages[k].fill(Qt.transparent)
            self.img = QImage(self.size(), QImage.Format_ARGB32)
            self.img.fill(Qt.transparent)
        else:
            self.exit_transparent()

    def exit_transparent(self):
        if self.transparent_mode:
            self.transparent_mode = False
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setStyleSheet("")
            self.resize(900, 700)
            self.move(100, 100)
            self.pages.clear()
            self.img = QImage(self.size(), QImage.Format_ARGB32)
            self.img.fill(BG_COLOR)
            self.showNormal()
            self._push_history()
            self.update()

    # ---------- 工具 ----------
    def set_eraser(self, val):
        self.eraser_mode = val

    def set_width(self, val):
        self.pen_width = val

    def set_eraser_size(self, val):
        self.eraser_size = val

    def choose_color(self):
        c = QColorDialog.getColor(self.pen_color, self, "选择颜色")
        if c.isValid():
            self.pen_color = c

    def _push_history(self):
        self.history.append(self.img.copy())
        if len(self.history) > 50:
            self.history.pop(0)

    def undo(self):
        if len(self.history) > 1:
            self.history.pop()
            self.img = self.history[-1].copy()
            self.update()

    def clear(self):
        if self.transparent_mode:
            self.img.fill(Qt.transparent)
        else:
            self.img.fill(BG_COLOR)
        self.history = [self.img.copy()]
        self.update()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存板书", "板书.png", "PNG (*.png)")
        if path:
            self.img.save(path)

    # ---------- 绘制 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._push_history()
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_point and event.buttons() & Qt.LeftButton:
            painter = QPainter(self.img)
            if self.eraser_mode:
                if self.transparent_mode:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    pen = QPen(Qt.transparent, self.eraser_size)
                else:
                    pen = QPen(BG_COLOR, self.eraser_size)
            else:
                pen = QPen(self.pen_color, self.pen_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            painter.end()
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.last_point = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.img)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Whiteboard()
    w.show()
    sys.exit(app.exec_())
