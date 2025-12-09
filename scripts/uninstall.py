import subprocess
import sys
import os

def uninstall_requirements():
    """Uninstall all packages from requirements.txt"""
    
    print("=" * 50)
    print("AI Task Planner - Uninstall Script")
    print("=" * 50)
    print()
    
    # Check if requirements.txt exists
    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt not found!")
        print("Nothing to uninstall.")
        sys.exit(1)
    
    # Read requirements.txt
    with open('requirements.txt', 'r') as f:
        packages = [line.strip().split('==')[0].split('>=')[0] 
                   for line in f if line.strip() and not line.startswith('#')]
    
    if not packages:
        print("❌ No packages found in requirements.txt")
        sys.exit(1)
    
    print(f"Found {len(packages)} package(s) to uninstall:")
    for pkg in packages:
        print(f"  - {pkg}")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed with uninstallation? (yes/no): ").lower()
    
    if response not in ['yes', 'y']:
        print("❌ Uninstallation cancelled.")
        sys.exit(0)
    
    print()
    print("Uninstalling packages...")
    print("-" * 50)
    
    failed_packages = []
    
    for package in packages:
        try:
            print(f"Uninstalling {package}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "uninstall", package, "-y"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✅ {package} uninstalled successfully")
        except subprocess.CalledProcessError:
            print(f"⚠️  {package} not found or already uninstalled")
            failed_packages.append(package)
    
    print()
    print("=" * 50)
    
    if failed_packages:
        print(f"⚠️  Some packages could not be uninstalled:")
        for pkg in failed_packages:
            print(f"  - {pkg}")
        print()
    
    print("✅ Uninstallation process complete!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        uninstall_requirements()
    except KeyboardInterrupt:
        print("\n\n❌ Uninstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)