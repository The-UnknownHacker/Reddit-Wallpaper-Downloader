from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                           QScrollArea, QGridLayout, QFileDialog, QMessageBox, QMenu, QMenuBar, QTabWidget, QDialog, QGroupBox, QRadioButton)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, QRect, QSettings
from PyQt6.QtGui import QPixmap, QImage, QPainter, QTransform, QFont
import sys
import requests
import os
import platform
from PIL import Image
import ctypes
from io import BytesIO
import subprocess
import uuid
from threading import Thread
from queue import Queue

COMMON_RESOLUTIONS = [
    "All Resolutions",
    "1920x1080 (FHD)",
    "2560x1440 (2K)",
    "3840x2160 (4K)",
    "1366x768",
    "1280x720 (HD)",
    "3440x1440 (UW)",
]

DEFAULT_WALLPAPER_DIR = os.path.join(os.path.expanduser('~'), 'Pictures', 'Wallpapers')

class LoadingSpinner(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
                padding: 20px;
                font-size: 24px;
                color: white;
            }
        """)
        self.setText("⟳")  # Using a unicode character as spinner
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def rotate(self):
        self.angle = (self.angle + 36) % 360
        # Use Qt's native transformation
        transform = QTransform().rotate(self.angle)
        # Create a new pixmap with the rotated text
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setFont(QFont("Arial", 24))
        painter.setPen(Qt.GlobalColor.white)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.translate(pixmap.width() / 2, pixmap.height() / 2)
        painter.rotate(self.angle)
        painter.drawText(QRect(-20, -20, 40, 40), Qt.AlignmentFlag.AlignCenter, "⟳")
        painter.end()
        self.setPixmap(pixmap)

    def start(self):
        self.show()
        self.timer.start(50)  # Update every 50ms for smoother rotation

    def stop(self):
        self.timer.stop()
        self.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update the pixmap when the widget is resized
        self.rotate()

class WallpaperDownloader(QMainWindow):
    image_loaded = pyqtSignal(dict)
    loading_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings('RedditWallpaperDownloader', 'WallpaperDownloader')
        self.image_queue = Queue()
        self.current_images = []
        self.os_name = platform.system()
        self.after_id = None
        self.current_page = 0
        self.load_settings()
        self.setup_ui()
        
        # Connect signals
        self.image_loaded.connect(self.add_image_to_grid)
        self.loading_finished.connect(self.on_loading_finished)
        
    def setup_ui(self):
        self.setWindowTitle("Reddit Wallpaper Downloader")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #363636;
                color: white;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0d6efd;
            }
            QTabBar::tab:hover:!selected {
                background-color: #404040;
            }
        """)
        
        # Create tabs
        self.browse_tab = QWidget()
        self.my_wallpapers_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.browse_tab, "Browse")
        self.tab_widget.addTab(self.my_wallpapers_tab, "My Wallpapers")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        # Setup each tab
        self.setup_browse_tab()
        self.setup_my_wallpapers_tab()
        self.setup_settings_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: #363636;
                color: white;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #0d6efd;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QScrollArea {
                border: none;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)
        
        self.resize(1200, 800)
        
    def setup_browse_tab(self):
        layout = QVBoxLayout(self.browse_tab)
        layout.setSpacing(20)
        
        # Move existing search and filter controls here
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.subreddit_entry = QLineEdit()
        self.subreddit_entry.setPlaceholderText("Enter subreddit names (comma-separated)...")
        self.subreddit_entry.setText("wallpapers, wallpaper, widescreenwallpaper")
        self.subreddit_entry.setMinimumHeight(40)
        
        search_button = QPushButton("Search")
        search_button.setMinimumHeight(40)
        search_button.clicked.connect(lambda: self.fetch_wallpapers(reset=True))
        
        search_layout.addWidget(self.subreddit_entry, stretch=4)
        search_layout.addWidget(search_button, stretch=1)
        
        layout.addLayout(search_layout)
        
        # Add resolution layout
        resolution_layout = QHBoxLayout()
        resolution_layout.setSpacing(10)
        
        resolution_label = QLabel("Resolution:")
        
        # Add resolution dropdown
        self.resolution_dropdown = QLineEdit()
        self.resolution_dropdown.setPlaceholderText("Select or type resolution...")
        self.resolution_dropdown.setMinimumHeight(40)
        self.resolution_dropdown.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: #363636;
                color: white;
                font-size: 14px;
            }
        """)
        
        # Create resolution menu
        self.resolution_menu = QMenu()
        self.resolution_menu.setStyleSheet("""
            QMenu {
                background-color: #363636;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 15px;
                color: white;
            }
            QMenu::item:selected {
                background-color: #0d6efd;
            }
        """)
        
        for resolution in COMMON_RESOLUTIONS:
            action = self.resolution_menu.addAction(resolution)
            action.triggered.connect(lambda checked, res=resolution: self.set_resolution(res))
        
        # Add dropdown button
        dropdown_button = QPushButton("▼")
        dropdown_button.setMaximumWidth(40)
        dropdown_button.setMinimumHeight(40)
        dropdown_button.clicked.connect(self.show_resolution_menu)
        
        resolution_layout.addWidget(resolution_label)
        resolution_layout.addWidget(self.resolution_dropdown, stretch=1)
        resolution_layout.addWidget(dropdown_button)
        
        layout.addLayout(resolution_layout)
        
        # Add directory selection layout
        directory_layout = QHBoxLayout()
        directory_layout.setSpacing(10)
        
        directory_label = QLabel("Wallpaper Directory:")
        self.directory_entry = QLineEdit()
        self.directory_entry.setReadOnly(True)
        self.directory_entry.setMinimumHeight(40)
        self.directory_entry.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: #363636;
                color: white;
                font-size: 14px;
            }
        """)
        
        browse_button = QPushButton("Browse")
        browse_button.setMinimumHeight(40)
        browse_button.clicked.connect(self.select_wallpaper_directory)
        
        directory_layout.addWidget(directory_label)
        directory_layout.addWidget(self.directory_entry, stretch=1)
        directory_layout.addWidget(browse_button)
        
        layout.addLayout(directory_layout)
        
        # Add scroll area with grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.image_grid_widget = QWidget()
        self.image_grid = QGridLayout(self.image_grid_widget)
        self.image_grid.setSpacing(20)
        
        scroll_area.setWidget(self.image_grid_widget)
        layout.addWidget(scroll_area)
        
        # Add load more button
        self.load_more_button = QPushButton("Load More Images")
        self.load_more_button.clicked.connect(lambda: self.fetch_wallpapers(reset=False))
        self.load_more_button.hide()
        layout.addWidget(self.load_more_button)
        
        # Add loading spinner
        self.loading_spinner = LoadingSpinner(self)
        self.loading_spinner.setFixedSize(100, 100)
        
        # Center the spinner in the window
        def center_spinner():
            geometry = self.geometry()
            self.loading_spinner.move(
                geometry.width()//2 - self.loading_spinner.width()//2,
                geometry.height()//2 - self.loading_spinner.height()//2
            )
        
        self.resizeEvent = lambda e: center_spinner()
        
    def setup_my_wallpapers_tab(self):
        layout = QVBoxLayout(self.my_wallpapers_tab)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.local_grid_widget = QWidget()
        self.local_grid = QGridLayout(self.local_grid_widget)
        self.local_grid.setSpacing(20)
        
        scroll_area.setWidget(self.local_grid_widget)
        layout.addWidget(scroll_area)

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title_label = QLabel("Settings")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title_label)
        
        # Theme selection
        theme_group = QGroupBox("Theme")
        theme_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 15px;
                margin-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 5px;
            }
            QRadioButton {
                font-size: 14px;
                padding: 5px;
                spacing: 10px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        theme_layout = QVBoxLayout()
        theme_layout.setSpacing(10)
        theme_layout.setContentsMargins(20, 20, 20, 20)
        
        self.dark_theme = QRadioButton("Dark Theme")
        self.light_theme = QRadioButton("Light Theme")
        current_theme = self.settings.value('theme', 'dark')
        if current_theme == 'dark':
            self.dark_theme.setChecked(True)
        else:
            self.light_theme.setChecked(True)
        
        theme_layout.addWidget(self.dark_theme)
        theme_layout.addWidget(self.light_theme)
        theme_group.setLayout(theme_layout)
        
        # Default subreddits
        subreddits_group = QGroupBox("Default Subreddits")
        subreddits_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 15px;
                margin-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 5px;
            }
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                background-color: #363636;
            }
        """)
        
        subreddits_layout = QVBoxLayout()
        subreddits_layout.setSpacing(10)
        subreddits_layout.setContentsMargins(20, 20, 20, 20)
        
        subreddits_label = QLabel("Enter comma-separated subreddit names:")
        subreddits_label.setStyleSheet("font-size: 14px;")
        
        self.default_subreddits = QLineEdit()
        self.default_subreddits.setText(self.settings.value('default_subreddits', 
            'wallpapers, wallpaper, widescreenwallpaper'))
        self.default_subreddits.setMinimumHeight(40)
        
        subreddits_layout.addWidget(subreddits_label)
        subreddits_layout.addWidget(self.default_subreddits)
        subreddits_group.setLayout(subreddits_layout)
        
        # Save button with better styling
        save_button = QPushButton("Save Changes")
        save_button.setMinimumHeight(50)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        save_button.clicked.connect(self.save_settings)
        
        # Add everything to main layout
        layout.addWidget(theme_group)
        layout.addWidget(subreddits_group)
        layout.addSpacing(20)
        layout.addWidget(save_button)
        layout.addStretch()
        
        # Add a reset button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                border-radius: 6px;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        reset_button.clicked.connect(self.reset_settings)
        layout.addWidget(reset_button)

    def process_image(self, image_url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            width, height = image.size
            
            # Create thumbnail
            image.thumbnail((300, 300))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            
            return {
                'image_data': buffer.getvalue(),
                'width': width,
                'height': height
            }
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

    def create_image_card(self, image_url, title, row, col, processed_data=None, subreddit=None, is_local=False, grid=None):
        if grid is None:
            grid = self.image_grid
        
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #363636;
                border-radius: 8px;
                padding: 10px;
            }
            QWidget:hover {
                background-color: #404040;
            }
            QPushButton {
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        
        image_label = QLabel()
        if processed_data:
            qimg = QImage.fromData(processed_data['image_data'])
            pixmap = QPixmap.fromImage(qimg)
            image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(image_label)
        
        button_layout = QHBoxLayout()
        
        set_wallpaper_btn = QPushButton("Set as Wallpaper")
        set_wallpaper_btn.clicked.connect(lambda: self.set_wallpaper(image_url))
        
        download_btn = QPushButton("Download")
        download_btn.clicked.connect(lambda: self.download_wallpaper(image_url, title))
        
        button_layout.addWidget(set_wallpaper_btn)
        button_layout.addWidget(download_btn)
        card_layout.addLayout(button_layout)
        
        # Create info label with processed dimensions
        info_label = QLabel()
        info_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        
        if processed_data:
            info_text = f"{subreddit}\n" if subreddit else ""
            info_text += f"Resolution: {processed_data['width']}x{processed_data['height']}\n{title}"
            info_label.setText(info_text)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setVisible(False)
        card_layout.addWidget(info_label)
        
        # Create fade animations
        fade_in = QPropertyAnimation(info_label, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        fade_out = QPropertyAnimation(info_label, b"windowOpacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        fade_out.finished.connect(lambda: info_label.setVisible(False))
        
        def enterEvent(event):
            fade_out.stop()
            info_label.setVisible(True)
            fade_in.start()
        
        def leaveEvent(event):
            fade_in.stop()
            fade_out.start()
        
        card.enterEvent = enterEvent
        card.leaveEvent = leaveEvent
        
        grid.addWidget(card, row, col)

    def fetch_wallpapers(self, reset=False):
        if reset:
            self.current_page = 0
            self.current_images.clear()
            while self.image_grid.count():
                item = self.image_grid.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        self.loading_spinner.start()
        Thread(target=self._fetch_wallpapers_thread, args=(reset,)).start()

    def _fetch_wallpapers_thread(self, reset):
        try:
            # Split and clean subreddit names
            subreddit_names = [s.strip() for s in self.subreddit_entry.text().split(',')]
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            limit = max(50 // len(subreddit_names), 10)  # Distribute limit across subreddits
            
            all_posts = []
            for subreddit_name in subreddit_names:
                try:
                    after_param = f"&after={self.after_id}" if self.after_id else ""
                    url = f'https://www.reddit.com/r/{subreddit_name}/hot.json?limit={limit}{after_param}'
                    
                    response = requests.get(url, headers=headers)
                    data = response.json()
                    
                    # Store the last after_id
                    if subreddit_name == subreddit_names[-1]:
                        self.after_id = data['data'].get('after')
                    
                    # Add subreddit name to each post for display
                    for post in data['data']['children']:
                        post['data']['subreddit_display'] = f"r/{subreddit_name}"
                        all_posts.append(post)
                        
                except Exception as e:
                    print(f"Error fetching from r/{subreddit_name}: {str(e)}")
                    continue
            
            # Shuffle posts to mix content from different subreddits
            import random
            random.shuffle(all_posts)
            
            images_found = 0
            resolution = self.resolution_dropdown.text().strip()
            desired_width = None
            desired_height = None
            tolerance = 100  # pixels tolerance for resolution matching

            if resolution and resolution != "All Resolutions":
                try:
                    # Handle resolution with or without label (e.g., "1920x1080" or "1920x1080 (FHD)")
                    resolution = resolution.split(" ")[0]  # Get just the resolution part
                    width, height = map(int, resolution.lower().split('x'))
                    desired_width = width
                    desired_height = height
                except ValueError:
                    self.loading_finished.emit()
                    return

            for post in all_posts:
                if images_found >= 18:
                    break
                    
                post_data = post['data']
                image_url = post_data.get('url', '')
                
                if image_url.endswith(('.jpg', '.png', '.jpeg')):
                    try:
                        # Process image in background
                        processed_data = self.process_image(image_url)
                        if processed_data:
                            width = processed_data['width']
                            height = processed_data['height']
                            
                            # Check resolution if filtering is active
                            if desired_width and desired_height:
                                width_matches = abs(width - desired_width) <= tolerance
                                height_matches = abs(height - desired_height) <= tolerance
                                # Also check rotated orientation
                                rotated_width_matches = abs(width - desired_height) <= tolerance
                                rotated_height_matches = abs(height - desired_width) <= tolerance
                                
                                if not ((width_matches and height_matches) or 
                                       (rotated_width_matches and rotated_height_matches)):
                                    continue
                            
                            self.image_loaded.emit({
                                'url': image_url,
                                'title': post_data['title'],
                                'subreddit': post_data['subreddit_display'],
                                'position': images_found,
                                'processed_data': processed_data
                            })
                            images_found += 1
                    
                    except Exception as e:
                        continue
            
            self.loading_finished.emit()
                
        except Exception as e:
            print(f"Error in fetch thread: {e}")
            self.loading_finished.emit()

    def add_image_to_grid(self, image_data):
        position = image_data['position']
        row = position // 3
        col = position % 3
        self.create_image_card(
            image_data['url'], 
            image_data['title'], 
            row, 
            col, 
            image_data['processed_data'],
            image_data['subreddit']
        )
        self.current_images.append({
            'url': image_data['url'],
            'title': image_data['title'],
            'subreddit': image_data['subreddit']
        })

    def on_loading_finished(self):
        self.loading_spinner.stop()
        self.load_more_button.setVisible(bool(self.after_id))

    def set_wallpaper(self, url_or_path):
        try:
            # Check if this is a local file or URL
            if url_or_path.startswith(('http://', 'https://')):
                # Handle remote URL
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url_or_path, headers=headers)
                
                # Save to wallpaper directory
                filename = f'wallpaper_{uuid.uuid4().hex[:8]}.jpg'
                wallpaper_path = os.path.join(self.wallpaper_directory, filename)
                
                with open(wallpaper_path, 'wb') as f:
                    f.write(response.content)
            else:
                # Handle local file
                wallpaper_path = url_or_path
                if not os.path.exists(wallpaper_path):
                    raise Exception(f"File not found: {wallpaper_path}")
            
            abs_path = os.path.abspath(wallpaper_path)
            
            if self.os_name == "Darwin":
                abs_path = abs_path.replace('\\', '/')
                
                script = f'''
                    tell application "System Events"
                        tell every desktop
                            set picture to "{abs_path}"
                        end tell
                    end tell
                    '''
                
                try:
                    os.chmod(abs_path, 0o644)
                    
                    result = subprocess.run(
                        ['osascript', '-e', script],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        alternative_script = f'''
                            tell application "Finder"
                                set desktop picture to POSIX file "{abs_path}"
                            end tell
                            '''
                        result = subprocess.run(
                            ['osascript', '-e', alternative_script],
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode != 0:
                            final_script = f'''
                                tell application "System Events"
                                    set picture of current desktop to "{abs_path}"
                                end tell
                                '''
                            subprocess.run(
                                ['osascript', '-e', final_script],
                                check=True,
                                capture_output=True,
                                text=True
                            )
                    
                except subprocess.CalledProcessError as e:
                    raise Exception(f"AppleScript error: {e.stderr}\nCommand output: {e.stdout}")
                
            elif self.os_name == "Windows":
                SPI_SETDESKWALLPAPER = 0x0014
                SPIF_UPDATEINIFILE = 0x01
                SPIF_SENDCHANGE = 0x02
                if not ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETDESKWALLPAPER, 
                    0, 
                    abs_path, 
                    SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
                ):
                    raise Exception(f"SystemParametersInfoW failed: {ctypes.get_last_error()}")
            
            elif self.os_name == "Linux":
                desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
                if 'gnome' in desktop or 'unity' in desktop:
                    subprocess.run([
                        'gsettings', 
                        'set', 
                        'org.gnome.desktop.background', 
                        'picture-uri-dark' if 'dark' in desktop else 'picture-uri',
                        f'file://{abs_path}'
                    ], check=True)
                elif 'kde' in desktop:
                    subprocess.run(['plasma-apply-wallpaperimage', abs_path], check=True)
                elif 'xfce' in desktop:
                    subprocess.run([
                        'xfconf-query', 
                        '-c', 'xfce4-desktop', 
                        '-p', '/backdrop/screen0/monitor0/workspace0/last-image', 
                        '-s', abs_path
                    ], check=True)
                elif 'mate' in desktop:
                    subprocess.run([
                        'gsettings', 
                        'set', 
                        'org.mate.background', 
                        'picture-filename', 
                        abs_path
                    ], check=True)
                else:
                    QMessageBox.warning(
                        self,
                        "Warning", 
                        f"Unsupported Linux desktop environment: {desktop}\n"
                        "The image has been saved to: " + abs_path
                    )
                    return
            
            QMessageBox.information(self, "Success", f"Wallpaper set successfully!")
        
        except Exception as e:
            error_msg = str(e)
            if self.os_name == "Windows":
                error_code = ctypes.get_last_error()
                error_msg += f"\nWindows Error Code: {error_code}"
            
            QMessageBox.critical(
                self,
                "Error", 
                f"Error setting wallpaper: {error_msg}\n"
                f"OS: {self.os_name}\n"
                f"File path: {abs_path if 'abs_path' in locals() else 'Not created'}"
            )

    def download_wallpaper(self, url, title):
        try:
            clean_title = "".join(x for x in title if x.isalnum() or x in (' ', '-', '_'))
            clean_title = clean_title[:50]
            
            file_types = 'JPEG Files (*.jpg);;PNG Files (*.png);;All Files (*)'
            initial_path = os.path.join(self.wallpaper_directory, f"{clean_title}.jpg")
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Wallpaper",
                initial_path,
                file_types
            )
            
            if save_path:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers)
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                QMessageBox.information(self, "Success", "Image downloaded successfully!")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error downloading image: {str(e)}")

    def show_resolution_menu(self):
        # Position the menu under the dropdown
        pos = self.resolution_dropdown.mapToGlobal(self.resolution_dropdown.rect().bottomLeft())
        self.resolution_menu.popup(pos)

    def set_resolution(self, resolution):
        if resolution == "All Resolutions":
            self.resolution_dropdown.clear()
        else:
            # Extract just the resolution part before the parentheses
            res = resolution.split(" ")[0]
            self.resolution_dropdown.setText(res)
        
        # Clear the current grid and fetch new wallpapers
        self.clear_grid()
        self.current_images.clear()
        self.after_id = None
        self.fetch_wallpapers(reset=True)

    def load_settings(self):
        self.wallpaper_directory = self.settings.value(
            'wallpaper_directory',
            DEFAULT_WALLPAPER_DIR
        )
        # Create directory if it doesn't exist
        os.makedirs(self.wallpaper_directory, exist_ok=True)

    def select_wallpaper_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Wallpaper Directory",
            self.wallpaper_directory,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.wallpaper_directory = directory
            self.settings.setValue('wallpaper_directory', directory)
            self.directory_entry.setText(directory)
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)

    def show_my_wallpapers(self):
        self.clear_grid()
        self.load_local_wallpapers()

    def load_local_wallpapers(self):
        try:
            # Clear the grid first
            while self.local_grid.count():
                item = self.local_grid.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                
            files = os.listdir(self.wallpaper_directory)
            images = [f for f in files if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
            
            for i, image_file in enumerate(images):
                file_path = os.path.join(self.wallpaper_directory, image_file)
                row = i // 3
                col = i % 3
                self.create_local_image_card(file_path, row, col, grid=self.local_grid)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading wallpapers: {str(e)}")

    def create_local_image_card(self, file_path, row, col, grid=None):
        try:
            image = Image.open(file_path)
            width, height = image.size
            
            # Create thumbnail
            image.thumbnail((300, 300))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            
            processed_data = {
                'image_data': buffer.getvalue(),
                'width': width,
                'height': height
            }
            
            filename = os.path.basename(file_path)
            
            self.create_image_card(
                file_path,
                filename,
                row,
                col,
                processed_data,
                is_local=True,
                grid=grid
            )
            
        except Exception as e:
            print(f"Error loading image {file_path}: {e}")

    def apply_theme(self, theme):
        if theme == 'dark':
            self.setStyleSheet(self.get_dark_theme())
        else:
            self.setStyleSheet(self.get_light_theme())

    def get_dark_theme(self):
        return """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: #363636;
                color: white;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #0d6efd;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QScrollArea {
                border: none;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """

    def get_light_theme(self):
        return """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QWidget {
                background-color: #f0f0f0;
                color: #000000;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #d0d0d0;
                border-radius: 4px;
                background-color: #ffffff;
                color: #000000;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #0d6efd;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QScrollArea {
                border: none;
            }
            QLabel {
                color: #000000;
                font-size: 14px;
            }
        """

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()
        # After dialog closes, update the subreddit entry with default subreddits
        default_subreddits = self.settings.value('default_subreddits', 
            'wallpapers, wallpaper, widescreenwallpaper')
        self.subreddit_entry.setText(default_subreddits)

    def clear_grid(self):
        # Clear the grid layout
        while self.image_grid.count():
            item = self.image_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # Reset current images
        self.current_images.clear()
        # Hide load more button
        self.load_more_button.hide()

    def on_tab_changed(self, index):
        if index == 1:  # My Wallpapers tab
            self.load_local_wallpapers()

    def save_settings(self):
        # Save theme
        theme = 'dark' if self.dark_theme.isChecked() else 'light'
        self.settings.setValue('theme', theme)
        
        # Save default subreddits
        self.settings.setValue('default_subreddits', self.default_subreddits.text())
        
        # Apply theme
        self.apply_theme(theme)
        
        # Update subreddit entry with new defaults
        self.subreddit_entry.setText(self.default_subreddits.text())
        
        # Show success message
        QMessageBox.information(self, "Success", "Settings saved successfully!")

    def reset_settings(self):
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset theme
            self.dark_theme.setChecked(True)
            self.settings.setValue('theme', 'dark')
            
            # Reset subreddits
            default_subreddits = 'wallpapers, wallpaper, widescreenwallpaper'
            self.default_subreddits.setText(default_subreddits)
            self.settings.setValue('default_subreddits', default_subreddits)
            
            # Apply changes
            self.apply_theme('dark')
            self.subreddit_entry.setText(default_subreddits)
            
            QMessageBox.information(self, "Success", "Settings have been reset to defaults!")

# Add new class for Settings dialog
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.settings = parent.settings
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Theme selection
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout()
        self.dark_theme = QRadioButton("Dark")
        self.light_theme = QRadioButton("Light")
        current_theme = self.settings.value('theme', 'dark')
        if current_theme == 'dark':
            self.dark_theme.setChecked(True)
        else:
            self.light_theme.setChecked(True)
        theme_layout.addWidget(self.dark_theme)
        theme_layout.addWidget(self.light_theme)
        theme_group.setLayout(theme_layout)
        
        # Default subreddits
        subreddits_group = QGroupBox("Default Subreddits")
        subreddits_layout = QVBoxLayout()
        self.default_subreddits = QLineEdit()
        self.default_subreddits.setText(self.settings.value('default_subreddits', 
            'wallpapers, wallpaper, widescreenwallpaper'))
        subreddits_layout.addWidget(self.default_subreddits)
        subreddits_group.setLayout(subreddits_layout)
        
        # Save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        
        layout.addWidget(theme_group)
        layout.addWidget(subreddits_group)
        layout.addWidget(save_button)
        layout.addStretch()
        
    def save_settings(self):
        # Save theme
        theme = 'dark' if self.dark_theme.isChecked() else 'light'
        self.settings.setValue('theme', theme)
        
        # Save default subreddits
        self.settings.setValue('default_subreddits', self.default_subreddits.text())
        
        # Apply theme
        self.parent.apply_theme(theme)
        self.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WallpaperDownloader()
    window.show()
    sys.exit(app.exec()) 
