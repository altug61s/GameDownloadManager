#developed by altug61

import os
import json
import time
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw
import pystray
import winsound
from pypresence import Presence

STEAM_MANIFEST_PATH = os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamapps")
STEAM_DOWNLOAD_PATH = os.path.join(STEAM_MANIFEST_PATH, "downloading")
CHECK_INTERVAL = 5
CONFIG_FILE = "config.json"
DISCORD_CLIENT_ID = "1391515807984390264"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"epic_paths": []}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

config = load_config()

def get_folder_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            try:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
            except:
                continue
    return total

def get_steam_game_info():
    if not os.path.exists(STEAM_DOWNLOAD_PATH):
        return None
    for folder in os.listdir(STEAM_DOWNLOAD_PATH):
        downloading_path = os.path.join(STEAM_DOWNLOAD_PATH, folder)
        if not os.path.isdir(downloading_path):
            continue
        manifest_path = os.path.join(STEAM_MANIFEST_PATH, f"appmanifest_{folder}.acf")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, encoding='utf-8') as f:
                    name = None
                    for line in f:
                        if '"name"' in line:
                            name = line.split('"')[3]
                            break
                    if name:
                        if os.listdir(downloading_path):
                            return ("Steam", name, downloading_path)
            except Exception as e:
                print(f"Manifest okunamadı: {e}")
    return None


def check_epic_active_download(path):
    size_before = get_folder_size(path)
    time.sleep(CHECK_INTERVAL)
    size_after = get_folder_size(path)
    return size_after > size_before

def get_epic_game_info():
    for path in config["epic_paths"]:
        if os.path.exists(path):
            for folder in os.listdir(path):
                folder_path = os.path.join(path, folder)
                if os.path.isdir(folder_path) and any(os.scandir(folder_path)):
                    if check_epic_active_download(folder_path):
                        return ("Epic (Manuel)", folder, folder_path)
    return None

class DownloadApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.geometry("600x370")
        self.root.resizable(False, False)
        self.root.title("Game Download Manager")

        self.label = ctk.CTkLabel(self.root, text="İndirme Bilgisi", font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        self.info_label = ctk.CTkLabel(self.root, text="Bekleniyor...", font=("Arial", 16))
        self.info_label.pack(pady=5)

        self.timer_label = ctk.CTkLabel(self.root, text="", font=("Arial", 14))
        self.timer_label.pack(pady=5)

        self.cancel_button = ctk.CTkButton(self.root, text="Kapatmayı İptal Et", command=self.cancel_shutdown)
        self.cancel_button.pack(pady=5)
        self.cancel_button.configure(state="disabled")

        self.settings_button = ctk.CTkButton(self.root, text="Ayarlar", command=self.show_settings)
        self.settings_button.pack(pady=5)

        self.settings_frame = ctk.CTkFrame(self.root, width=560, height=280)
        self.settings_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.settings_frame.place_forget()  

        settings_title = ctk.CTkLabel(self.settings_frame, text="Epic Games Klasör Ayarları", font=("Arial", 16, "bold"))
        settings_title.pack(pady=10)

        self.epic_paths_var = tk.StringVar(value=config["epic_paths"])
        self.epic_listbox = tk.Listbox(self.settings_frame, listvariable=self.epic_paths_var, height=6)
        self.epic_listbox.pack(pady=5, fill="x", padx=20)

        btn_frame = ctk.CTkFrame(self.settings_frame)
        btn_frame.pack(pady=10)

        self.folder_button = ctk.CTkButton(btn_frame, text="Klasör Ekle", command=self.add_epic_folder)
        self.folder_button.grid(row=0, column=0, padx=10)

        self.delete_folder_button = ctk.CTkButton(btn_frame, text="Seçili Klasörü Sil", command=self.delete_epic_folder)
        self.delete_folder_button.grid(row=0, column=1, padx=10)

        self.close_settings_button = ctk.CTkButton(self.settings_frame, text="Ayarları Kapat", command=self.hide_settings)
        self.close_settings_button.pack(pady=10)

        self.shutdown_cancelled = False

        self.create_tray_icon()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.discord_rpc = None
        threading.Thread(target=self.discord_connect, daemon=True).start()

        self.no_download_count = 0
        self.shutdown_started = False
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def update_info(self, platform, name):
        self.info_label.configure(text=f"Oyun: {name}\nPlatform: {platform}")
        self.timer_label.configure(text="")
        self.cancel_button.configure(state="disabled")
        self.shutdown_cancelled = False
        self.update_discord_rpc(name)

    def monitor_loop(self):
        while True:
            info = get_steam_game_info() or get_epic_game_info()
            if info:
                platform, name, path = info
                self.update_info(platform, name)
                self.no_download_count = 0
                self.shutdown_started = False
            else:
                self.no_download_count += 1
                if self.no_download_count >= 3 and not self.shutdown_started:
                    self.shutdown_started = True
                    self.on_download_complete()
            time.sleep(CHECK_INTERVAL)

    def on_download_complete(self):
        def countdown():
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            self.cancel_button.configure(state="normal")
            for i in range(60, 0, -1):
                if self.shutdown_cancelled:
                    self.timer_label.configure(text="Kapatma iptal edildi.")
                    return
                self.timer_label.configure(text=f"Sistem {i} saniye içinde kapanacak...")
                time.sleep(1)
            os.system("shutdown /s /t 0")

        def popup():
            messagebox.showinfo("İndirme Tamamlandı", "İndirme tamamlandı. 60 saniye içinde sistem kapanacak.")
            threading.Thread(target=countdown, daemon=True).start()

        self.root.after(100, popup)
        self.update_discord_rpc(None)

    def cancel_shutdown(self):
        self.shutdown_cancelled = True
        self.cancel_button.configure(state="disabled")

    def add_epic_folder(self):
        folder = filedialog.askdirectory()
        if folder and folder not in config["epic_paths"]:
            config["epic_paths"].append(folder)
            save_config(config)
            self.refresh_epic_list()
            messagebox.showinfo("Klasör Eklendi", f"{folder}\nArtık takip edilecek.")

    def delete_epic_folder(self):
        try:
            selection = self.epic_listbox.curselection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen silmek için bir klasör seçin.")
                return
            index = selection[0]
            folder_to_remove = config["epic_paths"][index]
            confirm = messagebox.askyesno("Onay", f"{folder_to_remove} klasörünü silmek istediğinize emin misiniz?")
            if confirm:
                config["epic_paths"].pop(index)
                save_config(config)
                self.refresh_epic_list()
                messagebox.showinfo("Başarılı", "Klasör kaldırıldı ve takip durduruldu.")
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör silinirken hata oluştu:\n{e}")

    def refresh_epic_list(self):
        self.epic_paths_var.set(config["epic_paths"])

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill='green')

        menu = (
            pystray.MenuItem("Göster", self.show_window),
            pystray.MenuItem("Çıkış", self.quit_app)
        )
        self.icon = pystray.Icon("indirme_takipcisi", image, "İndirme Takipçisi", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon=None, item=None):
        if icon:
            icon.stop()
        self.root.quit()

    def discord_connect(self):
        try:
            self.discord_rpc = Presence(DISCORD_CLIENT_ID)
            self.discord_rpc.connect()
            while True:
                time.sleep(15)
        except Exception:
            pass

    def update_discord_rpc(self, game_name):
        if not self.discord_rpc:
            return
        try:
            if game_name:
                self.discord_rpc.update(state="İndiriyor", details=game_name)
            else:
                self.discord_rpc.clear()
        except:
            pass

    def show_settings(self):
        self.settings_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.settings_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

    def hide_settings(self):
        self.settings_frame.place_forget()
        self.settings_button.configure(state="normal")
        self.cancel_button.configure(state="normal")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DownloadApp()
    app.run()
