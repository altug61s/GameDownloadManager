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
import subprocess
from pypresence import Presence
from downloader import get_steam_game_info, get_epic_game_info, check_epic_active_download, get_folder_size, CHECK_INTERVAL
from config import load_config, save_config

DISCORD_CLIENT_ID = "1391515807984390264"

THEMES = {
    "dark": {
        "bg": "#121212",
        "fg": "#1D9BF0",
        "text": "#FFFFFF",
        "hover": "#1482c2",
        "frame_bg": "#181818",
        "listbox_bg": "#2a2a2a",
        "listbox_fg": "white",
        "listbox_highlight": "#1D9BF0",
        "listbox_select": "#1D9BF0",
        "switch_slider_on": "#1D9BF0",
        "switch_slider_off": "#7A7A7A"
    },
    "light": {
        "bg": "#F0F0F0",
        "fg": "#007ACC",
        "text": "#333333",
        "hover": "#005F99",
        "frame_bg": "#E0E0E0",
        "listbox_bg": "#FFFFFF",
        "listbox_fg": "black",
        "listbox_highlight": "#007ACC",
        "listbox_select": "#007ACC",
        "switch_slider_on": "#007ACC",
        "switch_slider_off": "#A0A0A0"
    }
}

class AnimatedLabel(ctk.CTkLabel):
    def animate_text(self, text, delay=30):
        self.configure(text="")
        def animate():
            for i in range(len(text) + 1):
                self.after(0, lambda t=text[:i]: self.configure(text=t))
                time.sleep(delay / 1000)
        threading.Thread(target=animate, daemon=True).start()

class AnimatedFrame(ctk.CTkFrame):
    def fade_in(self, steps=10, duration=300):
        pass 

class AnimatedButton(ctk.CTkButton):
    def __init__(self, master, app_instance, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.app_instance = app_instance
        self.default_color = kwargs.get("fg_color", None)
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.update_button_colors()

    def update_button_colors(self):
        current_theme_colors = self.app_instance.get_current_theme_colors()
        self.configure(fg_color=current_theme_colors["fg"], hover_color=current_theme_colors["hover"])
        self.default_color = current_theme_colors["fg"]

    def on_hover(self, event=None):
        current_theme_colors = self.app_instance.get_current_theme_colors()
        self.configure(fg_color=current_theme_colors["hover"])

    def on_leave(self, event=None):
        current_theme_colors = self.app_instance.get_current_theme_colors()
        self.configure(fg_color=self.default_color if self.default_color else current_theme_colors["fg"])

    def on_click(self, event=None):
        current_theme_colors = self.app_instance.get_current_theme_colors()
        click_color = "#0f4c81" if self.app_instance.config["theme_mode"] == "dark" else "#003A66"
        self.configure(fg_color=click_color)
        self.after(150, lambda: self.configure(fg_color=self.default_color if self.default_color else current_theme_colors["fg"]))


class DownloadApp:
    def __init__(self):
        self.config = load_config()
        ctk.set_appearance_mode(self.config["theme_mode"])

        self.root = ctk.CTk()
        self.root.geometry("600x400")
        self.root.title("Game Download Manager")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind("<Escape>", lambda e: self.hide_settings())

        self.label = AnimatedLabel(self.root, font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        self.info_label = AnimatedLabel(self.root, text="Bekleniyor...", font=("Arial", 16))
        self.info_label.pack(pady=5)

        self.timer_label = AnimatedLabel(self.root, text="", font=("Arial", 14))
        self.timer_label.pack(pady=5)

        self.cancel_button = AnimatedButton(self.root, self, text="Kapatmayı İptal Et", command=self.cancel_shutdown)
        self.cancel_button.pack(pady=5)
        self.cancel_button.configure(state="disabled")

        self.settings_button = AnimatedButton(self.root, self, text="Ayarlar", command=self.show_settings)
        self.settings_button.pack(pady=5)

        self.settings_frame = AnimatedFrame(self.root, width=560, height=320) 
        self.settings_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.settings_frame.place_forget()

        settings_title = ctk.CTkLabel(self.settings_frame, text="Ayarlar", font=("Arial", 16, "bold"))
        settings_title.pack(pady=10)

        self.discord_rpc_var = tk.BooleanVar(value=self.config["discord_rpc_enabled"])
        self.discord_rpc_switch = ctk.CTkSwitch(self.settings_frame, text="Discord RPC Etkinleştir",
                                                command=self.toggle_discord_rpc,
                                                variable=self.discord_rpc_var, 
                                                onvalue=True, offvalue=False)
        self.discord_rpc_switch.pack(pady=5)

        self.theme_mode_var = tk.StringVar(value=self.config["theme_mode"])
        self.theme_switch = ctk.CTkSwitch(self.settings_frame, text="Açık Tema",
                                          command=self.toggle_theme,
                                          variable=self.theme_mode_var,
                                          onvalue="light", offvalue="dark")
        self.theme_switch.pack(pady=5)

        epic_settings_title = ctk.CTkLabel(self.settings_frame, text="Epic Games Klasör Ayarları", font=("Arial", 14, "bold"))
        epic_settings_title.pack(pady=(15, 5))

        self.epic_paths_var = tk.StringVar(value=self.config.get("epic_paths", []))
        self.epic_listbox = tk.Listbox(self.settings_frame, listvariable=self.epic_paths_var, height=6,
                                       bd=0, highlightthickness=0, selectmode=tk.SINGLE)
        self.epic_listbox.pack(pady=5, fill="x", padx=20)

        self.btn_frame = ctk.CTkFrame(self.settings_frame) 
        self.btn_frame.pack(pady=10)

        self.folder_button = AnimatedButton(self.btn_frame, self, text="Klasör Ekle", command=self.add_epic_folder)
        self.folder_button.grid(row=0, column=0, padx=10)

        self.delete_folder_button = AnimatedButton(self.btn_frame, self, text="Seçili Klasörü Sil", command=self.delete_epic_folder)
        self.delete_folder_button.grid(row=0, column=1, padx=10)

        self.close_settings_button = AnimatedButton(self.settings_frame, self, text="Ayarları Kapat", command=self.hide_settings)
        self.close_settings_button.pack(pady=10)


        self.apply_theme()
        self.label.animate_text("\u25CF Game Download Manager")

        self.shutdown_cancelled = False
        self.shutdown_started = False
        self.shutdown_blocked_until_restart = False

        self.discord_rpc = None
        if self.config["discord_rpc_enabled"]:
            threading.Thread(target=self.discord_connect, daemon=True).start()

        self.no_download_count = 0
        threading.Thread(target=self.monitor_loop, daemon=True).start()

        self.create_tray_icon()


    def get_current_theme_colors(self):
        return THEMES[self.config["theme_mode"]]

    def apply_theme(self):
        colors = self.get_current_theme_colors()
        ctk.set_appearance_mode(self.config["theme_mode"])
        
        self.update_ui_colors()

    def update_ui_colors(self):
        colors = self.get_current_theme_colors()

        self.settings_frame.configure(fg_color=colors["frame_bg"])

        for label_widget in [self.label, self.info_label, self.timer_label,
                             self.settings_frame.winfo_children()[0], 
                             self.settings_frame.winfo_children()[3]]:
            if isinstance(label_widget, (ctk.CTkLabel, AnimatedLabel)):
                label_widget.configure(text_color=colors["text"])
        
        for btn in [self.cancel_button, self.settings_button, self.folder_button,
                    self.delete_folder_button, self.close_settings_button]:
            if isinstance(btn, (ctk.CTkButton, AnimatedButton)):
                btn.update_button_colors()

        self.discord_rpc_switch.configure(text_color=colors["text"],
                                          button_color=colors["switch_slider_on"],
                                          button_hover_color=colors["fg"]) 
        self.theme_switch.configure(text_color=colors["text"],
                                    button_color=colors["switch_slider_on"],
                                    button_hover_color=colors["fg"]) 

        
        self.epic_listbox.configure(bg=colors["listbox_bg"], fg=colors["listbox_fg"],
                                    selectbackground=colors["listbox_select"],
                                    selectforeground=colors["listbox_fg"]) 

        
        self.btn_frame.configure(fg_color=colors["frame_bg"])

        
        self.create_tray_icon()


    def show_settings(self):
        self.settings_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.settings_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.update_ui_colors() 

    def hide_settings(self):
        self.settings_frame.place_forget()
        self.settings_button.configure(state="normal")
        if self.shutdown_started and not self.shutdown_cancelled:
             self.cancel_button.configure(state="normal")


    def toggle_discord_rpc(self):
        self.config["discord_rpc_enabled"] = self.discord_rpc_var.get() 
        save_config(self.config)
        if self.config["discord_rpc_enabled"]:
            if not self.discord_rpc: 
                threading.Thread(target=self.discord_connect, daemon=True).start()
        else:
            if self.discord_rpc:
                try:
                    self.discord_rpc.close()
                    self.discord_rpc = None
                    print("Discord RPC bağlantısı kesildi.")
                except Exception as e:
                    print(f"Discord RPC bağlantısı kesilirken hata: {e}")

    def toggle_theme(self):
        self.config["theme_mode"] = self.theme_mode_var.get() 
        save_config(self.config)
        self.apply_theme() 

    def cancel_shutdown(self):
        self.shutdown_cancelled = True
        self.cancel_button.configure(state="disabled")

    def add_epic_folder(self):
        folder = filedialog.askdirectory()
        if folder and folder not in self.config["epic_paths"]:
            self.config["epic_paths"].append(folder)
            save_config(self.config)
            self.refresh_epic_list()
            messagebox.showinfo("Klasör Eklendi", f"{folder}\nArtık takip edilecek.")

    def delete_epic_folder(self):
        selection = self.epic_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen silmek için bir klasör seçin.")
            return
        index = selection[0]
        folder_to_remove = self.config["epic_paths"][index]
        if messagebox.askyesno("Onay", f"{folder_to_remove} klasörünü silmek istiyor musunuz?"):
            self.config["epic_paths"].pop(index)
            save_config(self.config)
            self.refresh_epic_list()

    def refresh_epic_list(self):
        self.epic_paths_var.set(self.config["epic_paths"])
        colors = self.get_current_theme_colors()
        self.epic_listbox.configure(bg=colors["listbox_bg"], fg=colors["listbox_fg"],
                                    selectbackground=colors["listbox_select"],
                                    selectforeground=colors["listbox_fg"])


    def monitor_loop(self):
        while True:
            info = get_steam_game_info() or get_epic_game_info(self.config)
            if info:
                platform, name, path = info
                self.info_label.after(0, lambda: self.info_label.animate_text(f"Oyun: {name} | Platform: {platform}", 20))
                self.timer_label.after(0, lambda: self.timer_label.configure(text=""))
                self.cancel_button.after(0, lambda: self.cancel_button.configure(state="disabled"))
                self.shutdown_cancelled = False
                self.shutdown_blocked_until_restart = False
                self.no_download_count = 0
                if self.config["discord_rpc_enabled"]: 
                    self.update_discord_status(platform, name)
            else:
                self.no_download_count += 1
                if self.no_download_count >= 3 and not self.shutdown_started and not self.shutdown_blocked_until_restart:
                    self.shutdown_started = True
                    self.root.after(0, self.on_download_complete)
                
                if self.config["discord_rpc_enabled"] and self.discord_rpc:
                    try:
                        self.discord_rpc.update(
                            details="Oyun İndirme Takibi Açık",
                            state="Bekleniyor",
                            large_text="Game Download Manager"
                        )
                    except Exception as e:
                        print(f"[Discord] Bekleme durumu güncellenirken hata: {e}")
            time.sleep(CHECK_INTERVAL)

    def on_download_complete(self):
        def countdown():
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except:
                pass
            self.root.after(0, lambda: self.cancel_button.configure(state="normal"))
            for i in range(60, 0, -1):
                if self.shutdown_cancelled:
                    self.root.after(0, lambda: self.timer_label.animate_text("Kapatma iptal edildi.", 15))
                    self.shutdown_blocked_until_restart = True
                    self.shutdown_started = False
                    return
                self.root.after(0, lambda val=i: self.timer_label.animate_text(f"Sistem {val} saniye içinde kapanacak...", 15))
                time.sleep(1)
            subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)

        threading.Thread(target=countdown, daemon=True).start()

    def create_tray_icon(self):
        colors = self.get_current_theme_colors()
        image = Image.new('RGB', (32, 32), color=colors["bg"])
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 24, 24), fill=colors["fg"]) 

        if hasattr(self, 'icon') and self.icon:
            self.icon.stop()

        menu = (
            pystray.MenuItem("Göster", self.show_window),
            pystray.MenuItem("Gizle", self.hide_window),
            pystray.MenuItem("Çıkış", self.quit_app)
        )
        self.icon = pystray.Icon("indirme_takipcisi", image, "İndirme Takipçisi", menu)
        if not hasattr(self, '_icon_thread_started'):
            threading.Thread(target=self.icon.run, daemon=True).start()
            self._icon_thread_started = True


    def hide_window(self, icon=None, item=None):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon=None, item=None):
        if self.discord_rpc:
            try:
                self.discord_rpc.close()
            except Exception as e:
                print(f"Discord RPC kapatılırken hata: {e}")
        if hasattr(self, 'icon') and self.icon:
            self.icon.stop() 
        self.root.quit()

    def update_discord_status(self, platform, game_name):
        if self.discord_rpc and self.config["discord_rpc_enabled"]: 
            try:
                self.discord_rpc.update(
                    details=f"Oyunu indiriyor: {game_name}",
                    state=f"Platform: {platform}",
                    large_text="Game Download Manager"
                )
                print(f"[Discord] Status güncellendi: {game_name} - {platform}")
            except Exception as e:
                print(f"[Discord] Status güncellenirken hata: {e}")
        elif not self.config["discord_rpc_enabled"] and self.discord_rpc:
            try:
                self.discord_rpc.close()
                self.discord_rpc = None
                print("Discord RPC bağlantısı kapatıldığı için kesildi.")
            except Exception as e:
                print(f"Discord RPC kapatılırken hata: {e}")


    def discord_connect(self):
        if not self.config["discord_rpc_enabled"]:
            print("Discord RPC devre dışı bırakıldı, bağlanılmıyor.")
            return

        while True:
            try:
                self.discord_rpc = Presence(DISCORD_CLIENT_ID)
                self.discord_rpc.connect()
                print("Discord RPC bağlandı.")

                self.discord_rpc.update(
                    details="Oyun İndirme Takibi Açık",
                    state="Bekleniyor",
                    large_text="Game Download Manager"
                )
                break
            except Exception as e:
                print("Discord RPC bağlanamadı:", e)
                self.discord_rpc = None 
                time.sleep(60)

    def run(self):
        self.root.mainloop()
