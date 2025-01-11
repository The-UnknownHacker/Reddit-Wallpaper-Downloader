# Reddit Wallpaper Downloader

A desktop application that allows you to browse and download wallpapers from any subreddit. You can preview images, set them as your desktop wallpaper, or download them to your computer.

## Features

- Browse wallpapers from any subreddit
- - Now Includes searching Multiple Sub Reddits
- Preview images before downloading
-  - Also Preview There resolution now
- Set images as desktop wallpaper directly
- Download images to your computer
- - Also Use this program as a wallpaper manager
- Dark mode interface
- - Now Supports Light Mode As well
- Support for Windows, macOS, and Linux
- Resolution Filtering - Always find the right resolution for you

## Installation

### Option 1: Run from Source
1. Make sure you have Python 3.6+ installed
2. Install the required packages:
```
pip install PyQt6 Pillow requests
```
3. Run the application:
```
python main.py  # If running from source
# OR
# Double-click the executable if using the compiled version - coming soon
```
### Option 2: Run from Executable - coming soon
1. Download the executable for your platform from the [Releases](https://github.com/yourusername/reddit-wallpaper-downloader/releases) page - coming soon
2. Double-click the executable to run the application

## Usage
1. Enter a subreddit name (default is "wallpapers", a good one is also "wallpaper") - You can now add multiple if you prefer
2. Click "Search" to browse wallpapers
3. Use "Set as Wallpaper" to set an image as your desktop background
4. Use "Download" to save an image to your computer
5. Click "Load More Images" to view additional wallpapers

## Note for macOS Users

You may need to grant permissions for the application to:
- Access the Downloads folder
- Control System Events
- Control Finder

These permissions can be granted in System Preferences > Security & Privacy > Privacy > Automation.

## Building from Source - coming soon

### Windows
```
python build.py
```
The executable will be created in `dist/RedditWallpaperDownloader.exe`

### macOS
```
python build.py
```
The application bundle will be created in `dist/RedditWallpaperDownloader.app`

## License

MIT License 
