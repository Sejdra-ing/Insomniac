"""
End-to-end check of Insomniac's device layer on a connected Android device or emulator (no Instagram needed).

It drives the system Settings app through the same code Insomniac uses to drive Instagram: adb connection check,
ADB Keyboard install, uiautomator2 connection, finding/clicking/scrolling views, typing, back presses and screenshots.

Usage: python -m insomniac.tests.emulator_smoke [expected_width expected_height]
"""
import os
import subprocess
import sys
import time
import traceback

from insomniac.device import DeviceWrapper
from insomniac.device_facade import DeviceFacade
from insomniac.views import DialogView

SETTINGS_APP_ID = "com.android.settings"
ARTIFACTS_PATH = "emulator-artifacts"

results = []


def step(name, required=True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                value = func(*args, **kwargs)
                results.append((name, True, required, ""))
                print(f"PASS  {name}")
                return value
            except Exception as e:
                results.append((name, False, required, f"{type(e).__name__}: {e}"))
                print(f"FAIL  {name}: {type(e).__name__}: {e}")
                traceback.print_exc()
                return None
        return wrapper
    return decorator


def adb(*args):
    return subprocess.run(["adb", *args], capture_output=True, text=True, timeout=60).stdout.strip()


def dismiss_system_dialogs(device):
    # A freshly booted emulator often shows "Pixel Launcher isn't responding": wait for it instead of closing it
    for _ in range(5):
        wait_button = device.find(resourceId="android:id/aerr_wait")
        if not wait_button.exists(quick=True):
            break
        print("      dismissing \"isn't responding\" dialog")
        wait_button.click()
        time.sleep(2)


def launch_settings(device, action=None):
    dismiss_system_dialogs(device)
    if action is None:
        adb("shell", "am", "start", "-W", "-n", f"{SETTINGS_APP_ID}/.Settings")
    else:
        # Settings search can live in another package (e.g. Settings Intelligence), so don't wait for a package
        adb("shell", "am", "start", "-W", "-a", action)
        time.sleep(2)
        dismiss_system_dialogs(device)
        return
    deadline = time.time() + 30
    while time.time() < deadline:
        dismiss_system_dialogs(device)
        if device.get_info().get("currentPackageName") == SETTINGS_APP_ID:
            return
        time.sleep(1)
    raise AssertionError(f"Settings did not come to foreground, current app: "
                         f"{device.get_info().get('currentPackageName')}")


@step("connect through DeviceWrapper (adb check, ADB Keyboard, uiautomator2)")
def connect():
    wrapper = DeviceWrapper(device_id=None, old_uiautomator=False, wait_for_device=False, app_id=SETTINGS_APP_ID,
                            app_name=None, dont_set_typewriter=False)
    device = wrapper.get()
    assert device is not None, "DeviceWrapper returned no device"
    return device


@step("wake up uiautomator server and check it is alive")
def wake_up(device):
    device.wake_up()
    assert device.is_alive(), "uiautomator2 server is not alive"


@step("read device info and screen size")
def screen_size(device, expected):
    info = device.get_info()
    print(f"      device info: {info}")
    size = device._get_screen_size()
    print(f"      screen size: {size}")
    return size


@step("screen size matches the emulated phone", required=False)
def check_screen_size(size, expected):
    # displayHeight can exclude the navigation bar, so only the width has to match exactly
    assert size is not None and size[0] == expected[0] and size[1] <= expected[1], f"expected {expected}, got {size}"


@step("ADB Keyboard is set as input method", required=False)
def adb_keyboard(device):
    assert device.typewriter.is_adb_keyboard_set, "fallback to copy-paste typing"


@step("close an \"isn't responding\" dialog with Insomniac's DialogView", required=False)
def insomniac_dialog_view(device):
    DialogView(device).close_not_responding_dialog_if_visible()


@step("open Settings and find a view by class")
def open_settings(device):
    launch_settings(device)
    view = device.find(className="android.widget.TextView")
    assert view.exists(), "no TextView on Settings screen"
    print(f"      first text: {view.get_text()!r}")


@step("dump UI hierarchy")
def dump(device):
    xml = device.dump_hierarchy(os.path.join(ARTIFACTS_PATH, "settings.xml"))
    assert SETTINGS_APP_ID in xml, "Settings is not in the hierarchy"


@step("missing view: exists() is False and click(ignore_if_missing) is a no-op")
def missing_view(device):
    view = device.find(text="This view does not exist 1234")
    assert not view.exists(quick=True)
    view.click(ignore_if_missing=True)


@step("scroll and fling a scrollable list")
def scroll(device):
    launch_settings(device)
    view = device.find(scrollable=True)
    assert view.exists(), "no scrollable view"
    view.scroll(DeviceFacade.Direction.BOTTOM)
    view.swipe(DeviceFacade.Direction.TOP)
    device.swipe(DeviceFacade.Direction.TOP, 0.5)


@step("click a Settings entry and go back")
def click_and_back(device):
    launch_settings(device)
    entry = device.find(resourceId="android:id/title")
    assert entry.exists(), "no Settings entry with android:id/title"
    print(f"      clicking {entry.get_text()!r}")
    entry.click()
    assert device.back(), "back press did not change the screen"


@step("type text in Settings search", required=False)
def typing(device):
    launch_settings(device, "android.search.action.SEARCH_SETTINGS")
    field = device.find(className="android.widget.EditText")
    assert field.exists(), "no search field"
    if device.typewriter.write(field, "wifi"):
        print("      typed with ADB Keyboard")
    else:
        field.set_text("wifi")
        print("      typed with set_text fallback")
    assert "wifi" in (field.get_text() or "").lower(), f"field contains {field.get_text()!r}"
    device.close_keyboard()


@step("take a screenshot")
def screenshot(device):
    path = os.path.join(ARTIFACTS_PATH, "settings.png")
    device.screenshot(path)
    assert os.path.getsize(path) > 0


def main():
    expected = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else None
    os.makedirs(ARTIFACTS_PATH, exist_ok=True)

    device = connect()
    if device is not None:
        wake_up(device)
        size = screen_size(device, expected)
        if expected is not None:
            check_screen_size(size, expected)
        adb_keyboard(device)
        insomniac_dialog_view(device)
        open_settings(device)
        dump(device)
        missing_view(device)
        scroll(device)
        click_and_back(device)
        typing(device)
        screenshot(device)

    print("\nSummary:")
    for name, ok, required, error in results:
        print(f"  {'PASS' if ok else ('FAIL' if required else 'WARN')}  {name}{'' if ok else '  -> ' + error}")
    failed = [r for r in results if not r[1] and r[2]]
    sys.exit(1 if failed or device is None else 0)


if __name__ == '__main__':
    main()
