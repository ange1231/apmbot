#!/usr/bin/env python3
"""
Простая проверка файла логотипа
"""

import os

def check_logo():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "logoSblack.png")
    
    print(f"Checking logo file:")
    print(f"Script directory: {script_dir}")
    print(f"Logo path: {logo_path}")
    
    if os.path.exists(logo_path):
        size = os.path.getsize(logo_path)
        print(f"Status: FOUND")
        print(f"Size: {size} bytes ({size/1024:.1f} KB)")
        return True
    else:
        print(f"Status: NOT FOUND")
        return False

if __name__ == "__main__":
    check_logo()
