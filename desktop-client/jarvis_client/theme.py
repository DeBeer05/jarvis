from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


def icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#61d7b6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 20, 20)
    painter.setPen(QColor("#0c1618"))
    painter.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "J")
    painter.end()
    return QIcon(pixmap)


def stylesheet(mode="dark"):
    bg, panel, raised, text, muted, border, accent = ("#10171d", "#151f27", "#1c2a33", "#e8eff3", "#91a5b3", "#2c3c46", "#71dbbd") if mode == "dark" else ("#f4f7f8", "#ffffff", "#e8eff1", "#17262e", "#536d7b", "#cbd9df", "#166b57")
    return f"""
    QWidget {{ background: {bg}; color: {text}; font-family: 'Segoe UI'; font-size: 14px; }}
    QMainWindow, QStackedWidget {{ background: {bg}; }}
    QFrame#sidebar, QFrame#card {{ background: {panel}; border: 1px solid {border}; border-radius: 14px; }}
    QLabel {{ background: transparent; }}
    QLabel#brand {{ color: {accent}; font-size: 23px; font-weight: 700; letter-spacing: 4px; }}
    QLabel#heading {{ font-size: 29px; font-weight: 600; }}
    QLabel#muted {{ color: {muted}; }}
    QLabel#eyebrow {{ color: {accent}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
    QLabel#notice {{ padding: 12px; background: {raised}; border-radius: 8px; color: {accent}; }}
    QPushButton {{ background: {raised}; border: 1px solid {border}; border-radius: 8px; padding: 10px 15px; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton:disabled {{ color: {muted}; }}
    QPushButton#primary {{ background: {accent}; color: {bg}; border: none; font-weight: 700; }}
    QPushButton#nav {{ text-align: left; border: none; padding: 13px 16px; background: transparent; }}
    QPushButton#nav:checked {{ background: {raised}; color: {accent}; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QComboBox {{ background: {panel}; border: 1px solid {border}; border-radius: 8px; padding: 10px; selection-background-color: {border}; }}
    QTextEdit {{ font-size: 16px; padding: 20px; }}
    QListWidget::item {{ padding: 12px; border-bottom: 1px solid {border}; }}
    QListWidget::item:selected {{ background: {raised}; color: {accent}; }}
    QComboBox::drop-down {{ width: 24px; border: none; }}
    QScrollArea {{ border: none; }}
    QCheckBox {{ spacing: 10px; padding: 5px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QToolTip {{ background: {panel}; color: {text}; border: 1px solid {border}; }}
    """
