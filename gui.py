import shutil
import sys
import os


from PySide6.QtCore import QSize, Qt, Signal, QObject, QUrl, QTimer
from PySide6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QPushButton, 
    QFileDialog, 
    QScrollArea, 
    QWidget, 
    QHBoxLayout, 
    QLabel, 
    QVBoxLayout, 
    QSizePolicy, 
    QMessageBox,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,

)
from PySide6.QtGui import (
    QPixmap, 
    QAction, 
    QDesktopServices, 
    QShortcut, 
    QKeySequence, 
    QCloseEvent,
    QWheelEvent,
    QKeyEvent,
)

class GalleryState(QObject):
    discarded = Signal(str)
    selected = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)

        self.changes_since_save: bool = False

        self.selected_id: int = 0
        self.photo_files: list[str] = []
        
        self.select_directory(parent)

        next_shortcut = QShortcut(QKeySequence("Right"), parent, context=Qt.ShortcutContext.WindowShortcut)
        next_shortcut.activated.connect(self.next_image)

        prev_shortcut = QShortcut(QKeySequence("Left"), parent, context=Qt.ShortcutContext.WindowShortcut)
        prev_shortcut.activated.connect(self.previous_image)

        enter_shortcut = QShortcut(QKeySequence("Enter"), parent, context=Qt.ShortcutContext.WindowShortcut)
        enter_shortcut.activated.connect(self.next_image)

        enter_shortcut = QShortcut(QKeySequence("Shift+Return"), parent, context=Qt.ShortcutContext.WindowShortcut)
        enter_shortcut.activated.connect(self.previous_image)

        return_shortcut = QShortcut(QKeySequence("Return"), parent, context=Qt.ShortcutContext.WindowShortcut)
        return_shortcut.activated.connect(self.next_image)

        delete_shortcut = QShortcut(QKeySequence("Delete"), parent, context=Qt.ShortcutContext.WindowShortcut)
        delete_shortcut.activated.connect(self.discard_image)
        
        backspace_shortcut = QShortcut(QKeySequence("Backspace"), parent, context=Qt.ShortcutContext.WindowShortcut)
        backspace_shortcut.activated.connect(self.discard_image)

    def try_again_modal(self, parent):
        button = QMessageBox.warning(
            parent,
            "No photos found or no directory selected",
            "",
            buttons=QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
            defaultButton=QMessageBox.StandardButton.Retry,
        )

        if button == QMessageBox.StandardButton.Retry:
            self.select_directory(parent)
        elif button == QMessageBox.StandardButton.Cancel:
            QTimer.singleShot(0, parent.close)

    def select_directory(self, parent):
        dir: str = QFileDialog.getExistingDirectory(parent, "Select Directory")
        
        if dir == "":
            self.try_again_modal(parent)
            return

        for file_name in os.listdir(dir):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.photo_files.append(os.path.join(dir, file_name))

        if len(self.photo_files) == 0:
            self.try_again_modal(parent)
            return
        
        self.photo_files.sort()

    def discard_image(self):
        path = self.photo_files.pop(self.selected_id)
        self.changes_since_save = True
        self.discarded.emit(path)
        self.selected_id = self.selected_id % len(self.photo_files)
        self.selected.emit(self.selected_id)

    def next_image(self):
        self.selected_id = (self.selected_id + 1) % len(self.photo_files)
        self.selected.emit(self.selected_id)

    def previous_image(self):
        self.selected_id = (self.selected_id - 1) % len(self.photo_files)
        self.selected.emit(self.selected_id)

    def select_image(self, id: int):
        if 0 <= id < len(self.photo_files):
            self.selected_id = id
            self.selected.emit(self.selected_id)
        

class ClickableGalleryItem(QLabel):
    # Define a custom signal for when the label is clicked
    clicked = Signal(str)

    def mousePressEvent(self, event):
        # Call the parent's event handler
        super().mousePressEvent(event)
        id = self.gallery.photo_files.index(self.image_path)
        self.gallery.select_image(id)
        # Emit the custom clicked signal
        self.clicked.emit(self.image_path)

    def __init__(self, image_path: str, gallery: GalleryState, parent=None):
        super().__init__(parent)

        self.gallery = gallery

        self.selected = False
        self.image_path = image_path
        self.setFixedSize(100, 100)
        
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            QSize(100,100),
            aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
            mode=Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def setSelected(self, selected: bool):
        if selected:
            self.setStyleSheet("background: gray;")
        else:
            self.setStyleSheet("background: none;")

class KeepOrDiscard(QWidget):
    def __init__(self, gallery: GalleryState, parent=None):
        super().__init__(parent)

        self.gallery = gallery

        layout = QHBoxLayout()
        self.keep_button = QPushButton("Keep")
        self.keep_button.clicked.connect(gallery.next_image)

        self.count_text = QLabel(str(len(self.gallery.photo_files)))
        self.gallery.discarded.connect(self.on_deleted)
        layout.addWidget(self.count_text)

        self.discard_button = QPushButton("Discard")
        self.discard_button.clicked.connect(gallery.discard_image)

        layout.addWidget(self.keep_button)
        layout.addWidget(self.discard_button)
        self.setLayout(layout)

    def on_deleted(self, path: str):
        self.count_text.setText(str(len(self.gallery.photo_files)))

class GalleryScroller(QScrollArea):
    def __init__(self, gallery: GalleryState, parent=None):
        super().__init__(parent)

        self.gallery = gallery

        self.container = QWidget()
        self.h_layout = QHBoxLayout(self.container)

        self.gallery_items: dict[str, ClickableGalleryItem] = {}

        for image_path in self.gallery.photo_files:
            item = ClickableGalleryItem(image_path, gallery, parent=self.container)
            self.h_layout.addWidget(item)
            self.gallery_items[image_path] = item

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setFixedHeight(130)

        QTimer.singleShot(0, lambda: self.select_preview(self.gallery.selected_id))

        self.gallery.selected.connect(self.select_preview)
        self.gallery.discarded.connect(self.delete_preview)

        # scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded) 
        # scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.h_layout.setContentsMargins(0, 0, 0, 0)
        # self.h_layout.setSpacing(0)
        # scroll_area.setWidgetResizable(True) 

    def select_preview(self, id: int):
        if not (0 <= id < len(self.gallery.photo_files)):
            return

        selected_path = self.gallery.photo_files[id]
        for item in self.gallery_items.values():
            item.setSelected(item.image_path == selected_path)

        self.ensureWidgetVisible(self.gallery_items[selected_path])

    def delete_preview(self, path: str):
        self.h_layout.removeWidget(self.gallery_items[path])
        self.gallery_items[path].deleteLater()
        del self.gallery_items[path]

class ImageViewer(QGraphicsView):
    def __init__(self, gallery: GalleryState, parent=None):
        super().__init__(parent)

        self.gallery = gallery

        self.g_scene = QGraphicsScene(self)
        self.setScene(self.g_scene)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse) # Zoom around mouse pointer
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Enable hand panning with left mouse button by default

        pixmap = QPixmap(500, 500)
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self.image_item)

        self.gallery.selected.connect(self.image_selected)

        QTimer.singleShot(0, lambda: self.image_selected(self.gallery.selected_id))

        # self.grabGesture(Qt.GestureType.PinchGesture)
        # self.grabGesture(Qt.GestureType.PanGesture)

    def load_image(self, filename):
        pixmap = QPixmap(filename)
        self.image_item.setPixmap(pixmap)
        self.setSceneRect(self.image_item.boundingRect())
        self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio) # Fit image in view initially

    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.05 # Factor to zoom by
        if event.angleDelta().y() > 0:
            # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            self.scale(1 / zoom_factor, 1 / zoom_factor)

        
        # Prevent scrollbar from interfering with zoom
        event.accept()

    def image_selected(self, id: int):
        if not (0 <= id < len(self.gallery.photo_files)):
            return
        image_path = self.gallery.photo_files[id]
        self.load_image(image_path)

    # def event(self, event: QEvent):
    #     if event.type() == QEvent.Type.Gesture and isinstance(event, QGestureEvent):
    #         return self.gestureEvent(event)
    #     return super().event(event)

    # def gestureEvent(self, event: QGestureEvent):
    #     for gesture in event.activeGestures():
    #         if isinstance(gesture, QPinchGesture):
    #             # Check if the scale factor has changed
    #             if gesture.changeFlags() & QPinchGesture.ChangeFlag.ScaleFactorChanged:
    #                 # Apply the scale factor to the view's transform
    #                 # Use scaleFactor() for incremental updates
    #                 self.scale(gesture.scaleFactor(), gesture.scaleFactor())
    #                 return True
    #         if isinstance(gesture, QPanGesture):
    #             delta = gesture.delta()
    #             self.horizontalScrollBar().setValue(round(self.horizontalScrollBar().value() - delta.x()))
    #             self.verticalScrollBar().setValue(round(self.verticalScrollBar().value() - delta.y()))
    #             return True
            

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        self.gallery_state = GalleryState(self)

        self.keep_or_discard = KeepOrDiscard(self.gallery_state, parent=self)
        
        self.image_viewer = ImageViewer(self.gallery_state, parent=self)
        self.image_viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_viewer.setMinimumSize(400, 400)

        self.gallery_scroller = GalleryScroller(self.gallery_state, parent=self)

        whole_container = QWidget()
        main_layout = QVBoxLayout(whole_container)
        main_layout.addWidget(self.keep_or_discard)
        main_layout.addWidget(self.image_viewer)
        main_layout.addWidget(self.gallery_scroller)

        self.setCentralWidget(whole_container)
            
        file_qmenu = self.menuBar().addMenu("&File")
        copy_to_folder_action = QAction("Copy images to folder", self)
        copy_to_folder_action.triggered.connect(self.copy_images_to_folder)
        file_qmenu.addAction(copy_to_folder_action)

    def copy_images_to_folder(self):
        dest_dir = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if dest_dir:
            for image_path in self.gallery_state.photo_files:
                base_name = os.path.basename(image_path)
                dest_path = os.path.join(dest_dir, base_name)
                shutil.copy(image_path, dest_path)
            self.gallery_state.changes_since_save = False
            url = QUrl.fromLocalFile(dest_dir)
            QDesktopServices.openUrl(url)
            
    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.gallery_state.changes_since_save:
            event.accept()
            return
        
        button = QMessageBox.warning(
            self,
            "Quit Confirmation",
            "You may have unsaved changes. Do you want to save and quit, quit without saving, or cancel?",
            buttons=QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard,
            defaultButton=QMessageBox.StandardButton.Discard,
        )

        if button == QMessageBox.StandardButton.Save:
            self.copy_images_to_folder()
        elif button == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return
        
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            event.accept()
            return

        return super().keyPressEvent(event)

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()