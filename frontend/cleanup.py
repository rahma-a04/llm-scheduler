import subprocess
import sys
import os
import shutil

def cleanup_project():
    """Complete cleanup of project dependencies and cache"""
    
    print("=" * 50)
    print("AI Task Planner - Complete Cleanup")
    print("=" * 50)
    print()
    
    items_to_remove = []
    
    # Check for virtual environment
    if os.path.exists('venv'):
        items_to_remove.append(('Virtual environment', 'venv'))
    
    # Check for __pycache__
    pycache_dirs = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_dirs.append(os.path.join(root, '__pycache__'))
    
    if pycache_dirs:
        items_to_remove.append((f'Python cache directories ({len(pycache_dirs)})', pycache_dirs))
    
    # Check for .pyc files
    pyc_files = []
    for root, dirs, files in os.walk('.'):
        pyc_files.extend([os.path.join(root, f) for f in files if f.endswith('.pyc')])
    
    if pyc_files:
        items_to_remove.append((f'Compiled Python files ({len(pyc_files)})', pyc_files))
    
    if not items_to_remove:
        print("✅ Project is already clean!")
        return
    
    print("The following will be removed:")
    for name, path in items_to_remove:
        print(f"  - {name}")
    print()
    
    response = input("Proceed with cleanup? (yes/no): ").lower()
    
    if response not in ['yes', 'y']:
        print("❌ Cleanup cancelled.")
        return
    
    print()
    print("Cleaning up...")
    print("-" * 50)
    
    # Uninstall packages first
    if os.path.exists('requirements.txt'):
        print("Uninstalling packages...")
        subprocess.run([sys.executable, "uninstall.py"])
    
    # Remove directories and files
    for name, paths in items_to_remove:
        if isinstance(paths, str):
            paths = [paths]
        
        for path in paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                print(f"✅ Removed: {path}")
            except Exception as e:
                print(f"⚠️  Could not remove {path}: {e}")
    
    print()
    print("=" * 50)
    print("✅ Cleanup complete!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        cleanup_project()
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)