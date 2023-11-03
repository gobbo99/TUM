import subprocess

package_managers = ["apt", "dnf", "yum", "zypper", "pacman", "apk", "emerge"]


def is_terminal_installed(terminal_name):
    try:
        subprocess.check_output([terminal_name, "--version"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_terminal(terminal_name, package_manager):
    try:
        subprocess.check_call(["sudo", package_manager, "update"])
        subprocess.check_call(["sudo", package_manager, "install", terminal_name])
        print(f"{terminal_name} has been successfully installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {terminal_name}: {e}")


def install_gnome_terminal():
    for package_manager in package_managers:
        try:
            subprocess.check_output([package_manager, "--version"])
            if is_terminal_installed("gnome-terminal"):
                return

            print(f"gnome-terminal is not installed. Installing using {package_manager}...")
            install_terminal("gnome-terminal", package_manager)
            return
        except FileNotFoundError:
            continue

    print("Unsupported distribution. Unable to install gnome-terminal.")


def install_xfce4_terminal():
    for package_manager in package_managers:
        try:
            subprocess.check_output([package_manager, "--version"])
            if is_terminal_installed("xfce4-terminal"):
                return

            install_terminal("xfce4-terminal", package_manager)
            return
        except FileNotFoundError:
            continue
