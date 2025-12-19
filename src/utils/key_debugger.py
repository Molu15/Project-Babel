import keyboard
print("Press 'ä' and '#' to see their names. Press Esc to exit.")
def print_key(e):
    print(f"Key: {e.name} Scan: {e.scan_code}")

keyboard.hook(print_key)
keyboard.wait('esc')
