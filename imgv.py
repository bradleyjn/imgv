import os
import glob
from random import shuffle
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets


STATUS_TIME = 3000
DISPLAY_TIME = 2500

NEXT_KEYS = [QtCore.Qt.Key_Right, QtCore.Qt.Key_L]
PREVIOUS_KEYS = [QtCore.Qt.Key_Left, QtCore.Qt.Key_K]

# TODO: Why do some pictures rotate?
class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtCore.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(QtCore.QPoint(event.pos()))
        super(PhotoViewer, self).mousePressEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('imgv')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # menu bar
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 26))
        self.menu_settings = QtWidgets.QMenu('Settings')
        self.setMenuBar(self.menubar)
        self.action_interval = QtWidgets.QAction(self)
        self.action_interval.setText('Interval')
        self.menu_settings.addAction(self.action_interval)
        self.action_show_hide_buttons = QtWidgets.QAction(self)
        self.action_show_hide_buttons.setText('Show/Hide Buttons')
        self.menu_settings.addAction(self.action_show_hide_buttons)
        self.action_reshuffle = QtWidgets.QAction(self)
        self.action_reshuffle.setText('Reshuffle')
        self.menu_settings.addAction(self.action_reshuffle)
        self.action_reload = QtWidgets.QAction(self)
        self.action_reload.setText('Reload')
        self.menu_settings.addAction(self.action_reload)
        self.menubar.addAction(self.menu_settings.menuAction())

        # status bar
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # central widget
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QtWidgets.QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # dock
        self.dock_sources = QtWidgets.QDockWidget("Sources", self)
        self.dock_sources.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dock_widget_contents = QtWidgets.QWidget()
        self.dock_layout = QtWidgets.QVBoxLayout(self.dock_widget_contents)
        self.sources_list = QtWidgets.QListWidget()
        # self.sources_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.dock_btn_layout = QtWidgets.QHBoxLayout(self.dock_widget_contents)
        self.btn_add = QtWidgets.QPushButton('Add')
        self.btn_add.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_remove = QtWidgets.QPushButton('Remove')
        self.btn_remove.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dock_btn_layout.addWidget(self.btn_add)
        self.dock_btn_layout.addWidget(self.btn_remove)
        self.dock_layout.addWidget(self.sources_list)
        self.dock_layout.addLayout(self.dock_btn_layout)
        self.dock_sources.setWidget(self.dock_widget_contents)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock_sources)

        # photo viewer
        self.photo_space = PhotoViewer(self)
        self.photo_space.setFocusPolicy(QtCore.Qt.NoFocus)
        self.layout.addWidget(self.photo_space)

        # buttons
        self.btn_container = QtWidgets.QGroupBox()
        self.btn_container.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_layout = QtWidgets.QHBoxLayout()
        self.left_spacer_item = QtWidgets.QSpacerItem(40, 20,
                                           QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Minimum)
        self.right_spacer_item = QtWidgets.QSpacerItem(40, 20,
                                           QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Minimum)
        self.btn_back = QtWidgets.QPushButton('<-')
        self.btn_back.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_pause = QtWidgets.QPushButton('Pause')
        self.btn_pause.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_forward = QtWidgets.QPushButton('->')
        self.btn_forward.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_layout.addItem(self.left_spacer_item)
        self.btn_layout.addWidget(self.btn_back)
        self.btn_layout.addWidget(self.btn_pause)
        self.btn_layout.addWidget(self.btn_forward)
        self.btn_layout.addItem(self.right_spacer_item)
        self.btn_container.setLayout(self.btn_layout)
        self.layout.addWidget(self.btn_container)

        # actions
        self.btn_add.pressed.connect(self.add_source)
        self.btn_remove.pressed.connect(self.remove_source)
        self.btn_forward.pressed.connect(self.next)
        self.btn_back.pressed.connect(partial(self.next, -1))
        self.btn_pause.pressed.connect(self.play_pause)
        self.action_interval.triggered.connect(self.set_interval)
        self.action_reshuffle.triggered.connect(self.reshuffle)
        self.action_reload.triggered.connect(self.update_files)
        self.action_show_hide_buttons.triggered.connect(self.show_hide_buttons)

        # variables
        self.interval = DISPLAY_TIME
        self.sources = list()
        self.files = list()
        self.index = None
        self.timer = None

    def add_source(self):
        # print('adding source')
        source = str(QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Source'))
        if source == '':
            return
        if source not in self.sources:
            self.sources.append(source)
            # self.sources_list.addItem(source.split('/')[-1])
            self.sources_list.addItem(source)
            # print('Added {}'.format(source))
        else:
            self.statusbar.showMessage('Source already added', STATUS_TIME)
        self.update_files()

    def remove_source(self):
        # print('removing source')
        selected = self.sources_list.selectedIndexes()
        for source in selected:
            self.sources_list.takeItem(source.row())
            self.sources.pop(source.row())
        # print(self.sources)
        self.update_files()

    def update_files(self):
        # print('Updating Files')
        self.files.clear()
        for source in self.sources:
            for file in glob.iglob('{}/**'.format(source), recursive=True):
                # print(file)
                self.files.append(file)
        # print(self.files)
        shuffle(self.files)
        if len(self.files):
            self.start()

    def start(self):
        # print('Starting')
        self.index = 0
        self.set_photo(self.index)
        self.start_timer()

    def next(self, inc=1):
        # print('next')
        if self.timer:
            self.timer.stop()
        if not len(self.files):
            return
        self.index += inc
        if self.index < 0:
            self.index = len(self.files)-1
        if self.index > len(self.files)-1:
            self.index = 0
        # print('{} / {}'.format(self.index, len(self.files)))
        self.set_photo(self.index, inc)
        if self.btn_pause.text().lower() == 'pause':
            self.start_timer()

    def play_pause(self):
        if self.btn_pause.text().lower() == 'pause':
            self.btn_pause.setText('Play')
            if self.timer:
                self.timer.stop()
        else:
            self.btn_pause.setText('Pause')
            self.start_timer()

    def set_photo(self, index, inc=1):
        if index is None or index > len(self.files):
            return
        try:
            self.photo_space.setPhoto(QtGui.QPixmap(self.files[index]))
            # self.statusbar.showMessage(os.path.basename(self.files[index]))
            self.statusbar.showMessage(self.files[index])
        except AttributeError:
            self.statusbar.showMessage('Couldn''t load photo {}'.format(self.files[index]), STATUS_TIME)
            self.next(inc)

    def start_timer(self):
        if self.timer:
            self.timer.stop()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next)
        self.timer.start(self.interval)

    def set_interval(self):
        num, ok = QtWidgets.QInputDialog.getInt(self, 'Set Interval', 'Interval', value=self.interval)
        if ok:
            self.interval = num

    def reshuffle(self):
        shuffle(self.files)

    def show_hide_buttons(self):
        if self.btn_container.isVisible():
            self.btn_container.setVisible(False)
        else:
            self.btn_container.setVisible(True)

    # def eventFilter(self, source, event):
    #     if event.type() == QtCore.QEvent.KeyPress:
    #         print(event.key())
    #     return super(MyApp, self).eventFilter(source, event)

    def keyPressEvent(self, event):
        # print('keyPressEvent')
        # if type(event) == QtGui.QKeyEvent:
        key = event.key()
        # print(key)
        if key in NEXT_KEYS:
            self.next()
        elif key in PREVIOUS_KEYS:
            self.next(-1)
        elif key == QtCore.Qt.Key_S:
            if self.dock_sources.isVisible():
                self.dock_sources.setVisible(False)
            else:
                self.dock_sources.setVisible(True)
        elif key == QtCore.Qt.Key_B:
            self.show_hide_buttons()

    def resizeEvent(self, event):
        self.set_photo(self.index)
        event.accept()


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
