import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import os
import sys
from pathlib import Path

class EditorWindow:
    def __init__(self, file_path, profile_name="custom.json"):
        self.file_path = Path(file_path)
        self.profile_name = profile_name
        self.root = None
        self.full_config_data = {} # Store full config to preserve other parts
        
    def show(self):
        self.root = tk.Tk()
        self.root.title(f"Edit Profile: {self.profile_name} - Project Babel")
        self.root.geometry("600x600")
        
        # Center window
        self._center_window(self.root)
        
        # Header
        header_frame = tk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        lbl_title = tk.Label(header_frame, text=f"Profile: {self.profile_name}", font=("Segoe UI", 12, "bold"))
        lbl_title.pack(anchor="w")
        
        lbl_info = tk.Label(header_frame, text="Edit your shortcuts expectations below.\nValues: 'figma', 'photoshop', or 'custom: <key>'", justify="left")
        lbl_info.pack(anchor="w", pady=(5,0))
        
        # Text Area
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=70, height=25, font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Load Content
        content = self._load_profile_content()
        self.text_area.insert(tk.INSERT, content)
        
        # Buttons Frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        btn_save = tk.Button(btn_frame, text="Save & Apply", command=self._save, bg="#4CAF50", fg="white", width=20)
        btn_save.pack(side=tk.RIGHT, padx=5)
        
        btn_cancel = tk.Button(btn_frame, text="Cancel", command=self.root.destroy, width=10)
        btn_cancel.pack(side=tk.RIGHT, padx=5)
        
        # Focus window
        self.root.lift()
        self.root.attributes('-topmost',True)
        self.root.after_idle(self.root.attributes,'-topmost',False)
        
        self.root.mainloop()

    def _center_window(self, win):
        """Centers the window on the screen."""
        win.update_idletasks()
        try:
            width = win.winfo_width()
            height = win.winfo_height()
            x = (win.winfo_screenwidth() // 2) - (width // 2)
            y = (win.winfo_screenheight() // 2) - (height // 2)
            win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        except:
            pass

    def _load_profile_content(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.full_config_data = json.load(f)
                    
                profiles = self.full_config_data.get("profiles", {})
                target_profile = profiles.get(self.profile_name, {})
                settings = target_profile.get("settings", {})
                
                if not settings:
                     return f"// Profile '{self.profile_name}' not found or empty.\n{{\n}}"

                return json.dumps(settings, indent=4)
            except Exception as e:
                return f"// Error loading file: {e}\n{{\n}}"
        else:
            return "// Config file not found.\n{}"

    def _save(self):
        content = self.text_area.get("1.0", tk.END).strip()
        
        # Remove comments if any (simple hack: remove lines starting with //)
        clean_lines = [line for line in content.splitlines() if not line.strip().startswith("//")]
        clean_content = "\n".join(clean_lines)

        try:
            # Validate JSON
            new_settings = json.loads(clean_content)
            
            # Update full config
            if "profiles" not in self.full_config_data:
                self.full_config_data["profiles"] = {}
                
            if self.profile_name not in self.full_config_data["profiles"]:
                 self.full_config_data["profiles"][self.profile_name] = {"settings": {}}
                 
            self.full_config_data["profiles"][self.profile_name]["settings"] = new_settings
            
            # Save to file
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.full_config_data, f, indent=4)
            
            messagebox.showinfo("Success", f"Profile '{self.profile_name}' saved successfully!")
            self.root.destroy()
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"Syntax Error:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        profile = sys.argv[2] if len(sys.argv) > 2 else "custom.json"
    else:
        # Default fallback (mainly for testing)
        target_file = "semantic_config.json"
        profile = "custom.json"
        
    app = EditorWindow(target_file, profile)
    app.show()
