# downloader.py - Steam & Epic indirme takibi

import os
import time
import re

STEAM_MANIFEST_PATH = os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamapps")
STEAM_DOWNLOAD_PATH = os.path.join(STEAM_MANIFEST_PATH, "downloading")
CHECK_INTERVAL = 1

def get_folder_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            try:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
            except Exception:
                continue
    return total

def is_steam_downloading(appid):
    path = os.path.join(STEAM_DOWNLOAD_PATH, appid)
    if not os.path.exists(path):
        return False
    size_before = get_folder_size(path)
    time.sleep(CHECK_INTERVAL)
    size_after = get_folder_size(path)
    return size_after > size_before

def extract_name_from_acf(content):
    match = re.search(r'"name"\s+"([^"]+)"', content)
    if match:
        return match.group(1)
    return None

def get_steam_game_info():
    if not os.path.exists(STEAM_DOWNLOAD_PATH):
        return None

    for file in os.listdir(STEAM_MANIFEST_PATH):
        if file.startswith("appmanifest_") and file.endswith(".acf"):
            manifest_path = os.path.join(STEAM_MANIFEST_PATH, file)
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    content = f.read()
                    if '"StateFlags"' not in content:
                        continue

                    name = extract_name_from_acf(content)
                    appid = file.split('_')[1].split('.')[0]

                    if is_steam_downloading(appid):
                        return ("Steam", name, os.path.join(STEAM_DOWNLOAD_PATH, appid))

            except Exception:
                continue
    return None



def check_epic_active_download(path):
    size_before = get_folder_size(path)
    time.sleep(CHECK_INTERVAL)
    size_after = get_folder_size(path)
    return size_after > size_before

def get_epic_game_info(config):
    for path in config.get("epic_paths", []):
        if os.path.exists(path):
            for folder in os.listdir(path):
                folder_path = os.path.join(path, folder)
                if os.path.isdir(folder_path) and os.listdir(folder_path):
                    if check_epic_active_download(folder_path):
                        return ("Epic", folder, folder_path)
    return None
