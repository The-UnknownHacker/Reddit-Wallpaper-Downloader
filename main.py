from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                           QScrollArea, QGridLayout, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage
import sys
import requests
import os
import platform
from PIL import Image
import ctypes
from io import BytesIO
import subprocess
import uuid

class WallpaperDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_images = []
        self.os_name = platform.system()
        self.after_id = None
        self.current_page = 0
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Reddit Wallpaper Downloader")
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
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.subreddit_entry = QLineEdit()
        self.subreddit_entry.setPlaceholderText("Enter subreddit name...")
        self.subreddit_entry.setText("wallpapers")
        self.subreddit_entry.setMinimumHeight(40)
        
        search_button = QPushButton("Search")
        search_button.setMinimumHeight(40)
        search_button.clicked.connect(lambda: self.fetch_wallpapers(reset=True))
        
        search_layout.addWidget(self.subreddit_entry, stretch=4)
        search_layout.addWidget(search_button, stretch=1)
        
        main_layout.addLayout(search_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.image_grid_widget = QWidget()
        self.image_grid = QGridLayout(self.image_grid_widget)
        self.image_grid.setSpacing(20)
        
        scroll_area.setWidget(self.image_grid_widget)
        main_layout.addWidget(scroll_area)
        
        self.load_more_button = QPushButton("Load More Images")
        self.load_more_button.clicked.connect(lambda: self.fetch_wallpapers(reset=False))
        self.load_more_button.hide()
        main_layout.addWidget(self.load_more_button)
        
        self.resize(1200, 800)
        
    def create_image_card(self, image_url, title, row, col):
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #363636;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton {
                padding: 5px 10px;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))
        image.thumbnail((300, 300))

        buffer = BytesIO()
        image.save(buffer, format='PNG')
        qimg = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        
        image_label = QLabel()
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
        
        self.image_grid.addWidget(card, row, col)

    def fetch_wallpapers(self, reset=False):
        if reset:
            self.current_page = 0
            self.current_images.clear()
            while self.image_grid.count():
                item = self.image_grid.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        subreddit_name = self.subreddit_entry.text()
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            limit = 50
            after_param = f"&after={self.after_id}" if self.after_id else ""
            url = f'https://www.reddit.com/r/{subreddit_name}/hot.json?limit={limit}{after_param}'
            
            response = requests.get(url, headers=headers)
            data = response.json()
            
            self.after_id = data['data'].get('after')
            
            start_pos = len(self.current_images)
            row = start_pos // 3
            col = start_pos % 3
            
            images_found = 0
            
            for post in data['data']['children']:
                if images_found >= 18:
                    break
                    
                post_data = post['data']
                image_url = post_data.get('url', '')
                
                if image_url.endswith(('.jpg', '.png', '.jpeg')):
                    try:
                        self.create_image_card(image_url, post_data['title'], row, col)
                        self.current_images.append({
                            'url': image_url,
                            'title': post_data['title']
                        })
                        
                        col += 1
                        if col > 2:
                            col = 0
                            row += 1
                        
                        images_found += 1
                    except Exception as e:
                        continue
            
            self.load_more_button.setVisible(bool(self.after_id))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error fetching wallpapers: {str(e)}")
            self.load_more_button.hide()

    def set_wallpaper(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers)
            
            if self.os_name == "Windows":
                downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            else:
                downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            
            filename = f'wallpaper_{uuid.uuid4().hex[:8]}.jpg'
            wallpaper_path = os.path.join(downloads_path, filename)
            
            with open(wallpaper_path, 'wb') as f:
                f.write(response.content)
            
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
            initial_file = f"{clean_title}.jpg"
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Wallpaper",
                initial_file,
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WallpaperDownloader()
    window.show()
    sys.exit(app.exec()) 
