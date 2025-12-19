import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import os
import sys
from pathlib import Path

class EditorWindow:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.root = None
        
    def show(self):
        self.root = tk.Tk()
        self.root.title(f"Edit {self.file_path.name} - Project Babel")
        self.root.geometry("600x500")
        
        # Center window
        self._center_window(self.root)
        
        # Label
        lbl_info = tk.Label(self.root, text=f"Editing: {self.file_path.name}\nPaste your JSON configuration below:", justify="left")
        lbl_info.pack(pady=5, padx=10, anchor="w")
        
        # Text Area
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=70, height=25)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Load Content
        content = self._load_file_content()
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
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def _load_file_content(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, indent=4)
            except Exception as e:
                return f"Error loading file: {e}\n\n{{\n    \"target_apps\": [],\n    \"mappings\": []\n}}"
        else:
            # Return default template
            return json.dumps({
                "profile_name": "Custom Profile",
                "target_apps": ["notepad"],
                "mappings": [
                    {
                        "input": "ctrl+shift+x",
                        "output": "alt+f4",
                        "description": "Example Mapping"
                    }
                ]
            }, indent=4)

    def _save(self):
        content = self.text_area.get("1.0", tk.END).strip()
        try:
            # Validate JSON
            data = json.loads(content)
            
            # Save to file
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            messagebox.showinfo("Success", "Configuration saved successfully!")
            self.root.destroy()
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"Syntax Error:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Default fallback (mainly for testing)
        target_file = "config_test.json"
        
    app = EditorWindow(target_file)
    app.show()
