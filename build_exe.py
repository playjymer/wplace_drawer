#!/usr/bin/env python3
"""
Build script for creating Wplace Drawer 2.0 executable
"""
import os
import subprocess
import sys
import shutil

def build_exe():
    """Build executable with PyInstaller"""
    print("🔨 Building Wplace Drawer 2.0 executable...")
    
    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable
        "--windowed",                   # No console window
        "--name=WplaceDrawer2",         # Output name
        "--icon=icon.ico",              # Icon (if exists)
        "--add-data=README.md;.",       # Include README
        "--hidden-import=PIL",          # Ensure PIL is included
        "--hidden-import=tkinter",      # Ensure tkinter is included
        "--hidden-import=pyautogui",    # Ensure pyautogui is included
        "wplace_drawer2.py"
    ]
    
    # Remove icon parameter if icon file doesn't exist
    if not os.path.exists("icon.ico"):
        cmd.remove("--icon=icon.ico")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful!")
        print(f"📦 Executable created: dist/WplaceDrawer2.exe")
        
        # Show file size
        exe_path = "dist/WplaceDrawer2.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"📏 File size: {size_mb:.1f} MB")
        
    except subprocess.CalledProcessError as e:
        print("❌ Build failed!")
        print(f"Error: {e.stderr}")
        return False
    
    return True

def create_release_folder():
    """Create release folder with executable and docs"""
    print("📁 Creating release folder...")
    
    release_dir = "WplaceDrawer2_Release"
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    
    os.makedirs(release_dir)
    
    # Copy executable
    if os.path.exists("dist/WplaceDrawer2.exe"):
        shutil.copy("dist/WplaceDrawer2.exe", release_dir)
    
    # Copy documentation
    if os.path.exists("README.md"):
        shutil.copy("README.md", release_dir)
    
    if os.path.exists("requirements.txt"):
        shutil.copy("requirements.txt", release_dir)
    
    print(f"✅ Release folder created: {release_dir}/")
    print("Contents:")
    for item in os.listdir(release_dir):
        size = os.path.getsize(os.path.join(release_dir, item)) / (1024 * 1024)
        print(f"  - {item} ({size:.1f} MB)")

if __name__ == "__main__":
    print("🚀 Wplace Drawer 2.0 Build Script")
    print("="*40)
    
    if build_exe():
        create_release_folder()
        print("\n🎉 Build complete! Ready for distribution.")
    else:
        print("\n💥 Build failed. Check the errors above.")
        sys.exit(1)
