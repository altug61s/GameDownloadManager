import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"epic_paths": [], "discord_rpc_enabled": True, "theme_mode": "dark", "windows_notifications_enabled": True}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "discord_rpc_enabled" not in config:
                config["discord_rpc_enabled"] = True
            if "theme_mode" not in config:
                config["theme_mode"] = "dark"
            if "windows_notifications_enabled" not in config:
                config["windows_notifications_enabled"] = True
            return config
    except Exception:
        print("Config dosyası okunurken hata oluştu. Varsayılan ayarlar kullanılıyor.")
        return {"epic_paths": [], "discord_rpc_enabled": True, "theme_mode": "dark", "windows_notifications_enabled": True}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Config kaydedilirken hata: {e}")
