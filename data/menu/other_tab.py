import threading
import time
import keyboard
import psutil
import dearpygui.dearpygui as dpg
from config import Config

class OtherTab:
    def __init__(self, main_app):
        self.main_app = main_app
        self.trans = self.main_app.translations.get(self.main_app.current_language, {}).get("other_tab", {})
        self.config = Config.from_json()

        # Settings from configuration
        self.PROCESS_NAME = self.config.other_tab.get("process_name", "ONCE_HUMAN.exe")
        self.THROTTLE_INTERVAL = self.config.other_tab.get("throttle_interval", 0.5)
        self.rus_to_eng = str.maketrans(
            "йцукенгшщзхъфывапролджэячсмитьбю",
            "qwertyuiop[]asdfghjkl;'zxcvbnm,."
        )

        self.selected_key = None
        self.bind_mode = False
        self.running = False

        self.drag_click_thread = None
        self.stop_drag_click = threading.Event()

        self.throttle_thread = None
        self.average_read_speed = 0

        with dpg.group():
            with dpg.group(horizontal=True):
                self.drag_click_var = dpg.add_checkbox(label=self.trans.get("drag_click", "Drag click"),
                                                        default_value=self.config.other_tab.get('drag_click', False),
                                                        callback=self.toggle_drag_click)
                self.bind_button = dpg.add_button(label=self.trans.get("bind_key", "Bind key"), callback=self.bind_key)

            self.no_prop_var = dpg.add_checkbox(label=self.trans.get("no_prop", "No Prop"),
                                                default_value=self.config.other_tab.get('no_prop', False),
                                                callback=self.toggle_no_prop)

            self.disk_limit_scale = dpg.add_slider_int(label=self.trans.get("disk_read_limit", "Disk Read Limit (%)"),
                                                        min_value=10, max_value=100,
                                                        default_value=self.config.other_tab.get("disk_read_limit", 100),
                                                        callback=self.adjust_read_speed)

    def press_key(self, key):
        key = key.lower()
        keyboard.press(key)
        print(f"Key pressed: {key}")

    def release_key(self, key):
        key = key.lower()
        keyboard.release(key)
        print(f"Key released: {key}")

    def bind_key(self):
        if not self.bind_mode:
            print(self.trans.get("bind_mode_enter", "Entering bind mode..."))
            dpg.configure_item(self.bind_button, label="[...]")
            self.bind_mode = True
            threading.Thread(target=self.wait_for_key).start()
        else:
            print(self.trans.get("bind_mode_exit", "Exiting bind mode..."))
            self.bind_mode = False
            dpg.configure_item(self.bind_button, label=self.trans.get("bind_key", "Bind key"))

    def wait_for_key(self):
        key_name = keyboard.read_key()
        if self.bind_mode:
            self.set_key(key_name)

    def set_key(self, key_name):
        print(f"Key pressed: {key_name}")
        self.selected_key = key_name.lower().translate(self.rus_to_eng)
        dpg.configure_item(self.bind_button, label=f"{self.selected_key}")
        self.bind_mode = False

        if self.selected_key:
            self.start_drag_click()

    def start_drag_click(self):
        if not self.running:
            print(self.trans.get("drag_click_thread_start", "Starting drag click thread..."))
            self.stop_drag_click.clear()
            self.drag_click_thread = threading.Thread(target=self.drag_click_loop, daemon=True)
            self.drag_click_thread.start()
            self.running = True

    def drag_click_loop(self):
        while not self.stop_drag_click.is_set():
            if dpg.get_value(self.drag_click_var) and self.selected_key:
                if keyboard.is_pressed(self.selected_key):
                    print(self.trans.get("drag_click_perform", "{key} pressed, performing drag click...").format(
                        key=self.selected_key))
                    self.press_key('f')
                    time.sleep(self.THROTTLE_INTERVAL)
                    self.release_key('f')
                elif keyboard.is_pressed('f'):
                    print(self.trans.get("drag_click_f_key", "Key 'f' pressed, simulating repeated press..."))
                    self.release_key('f')
                    time.sleep(self.THROTTLE_INTERVAL)
                    self.press_key('f')
                    time.sleep(self.THROTTLE_INTERVAL)
            else:
                time.sleep(0.1)

    def toggle_drag_click(self, sender, app_data):
        self.config.other_tab['drag_click'] = app_data
        self.config.save_to_json()
        if app_data and self.selected_key:
            self.start_drag_click()
        elif not app_data:
            self.stop_drag_click.set()
            if self.drag_click_thread and self.drag_click_thread.is_alive():
                self.drag_click_thread.join()
            self.running = False

    def toggle_no_prop(self, sender, app_data):
        self.config.other_tab['no_prop'] = app_data
        self.config.save_to_json()
        if app_data:
            self.average_read_speed = self.measure_average_read_speed()
            dpg.set_value(self.disk_limit_scale, 100)
            if not self.throttle_thread or not self.throttle_thread.is_alive():
                print(self.trans.get("throttle_thread_start", "Starting throttle thread..."))
                self.throttle_thread = threading.Thread(target=self.throttle_process, daemon=True)
                self.throttle_thread.start()
        else:
            self.reset_disk_usage()

    def measure_average_read_speed(self):
        total_read = 0
        measurements = 5

        for i in range(measurements):
            for proc in psutil.process_iter(['name', 'io_counters']):
                if proc.info['name'] == self.PROCESS_NAME:
                    try:
                        io_counters = proc.io_counters()
                        total_read += io_counters.read_bytes
                        break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            time.sleep(1)

        average_read_speed = (total_read / measurements) / (1024 * 1024)
        print(f"Average read speed: {average_read_speed:.2f} MB/s")
        return average_read_speed

    def adjust_read_speed(self, sender, app_data):
        limit_percent = app_data
        new_speed_limit = (self.average_read_speed * limit_percent) / 100
        print(self.trans.get("new_read_limit", "New disk read limit: {value} MB/s").format(value=new_speed_limit))
        self.speed_limit = new_speed_limit
        self.config.other_tab['disk_read_limit'] = limit_percent
        self.config.save_to_json()

    def throttle_process(self):
        speed_limit = (self.average_read_speed * dpg.get_value(self.disk_limit_scale)) / 100
        self.speed_limit = speed_limit
        process = None

        while dpg.get_value(self.no_prop_var):
            try:
                process = next(proc for proc in psutil.process_iter(['name']) if proc.info['name'] == self.PROCESS_NAME)
            except StopIteration:
                print(f"Process {self.PROCESS_NAME} not found.")
                break
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"Error accessing process {self.PROCESS_NAME}: {str(e)}")
                break

            try:
                current_speed = self.measure_current_speed(process)
                print(f"Current read speed: {current_speed:.2f} MB/s")
                if current_speed > self.speed_limit:
                    print(f"Read speed exceeds limit ({self.speed_limit:.2f} MB/s). Suspending process.")
                    process.suspend()
                    time.sleep(self.THROTTLE_INTERVAL)
                    process.resume()
            except psutil.NoSuchProcess:
                print(f"Process {self.PROCESS_NAME} terminated.")
                break
            except Exception as e:
                print(f"Error managing process {self.PROCESS_NAME}: {str(e)}")

            time.sleep(self.THROTTLE_INTERVAL)

    def measure_current_speed(self, proc):
        try:
            initial_io = proc.io_counters().read_bytes
            time.sleep(1)
            final_io = proc.io_counters().read_bytes
            current_speed = (final_io - initial_io) / (1024 * 1024)
            return current_speed
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0

    def reset_disk_usage(self):
        if self.throttle_thread and self.throttle_thread.is_alive():
            print(self.trans.get("throttle_thread_stop", "Stopping throttle thread..."))
            dpg.set_value(self.no_prop_var, False)
            self.throttle_thread.join()
        print("Resetting disk usage limits.")

    def stop(self):
        if self.running:
            print(self.trans.get("drag_click_thread_stop", "Stopping drag click thread..."))
            self.stop_drag_click.set()
            if self.drag_click_thread and self.drag_click_thread.is_alive():
                self.drag_click_thread.join()
            self.running = False

        if self.throttle_thread and self.throttle_thread.is_alive():
            print(self.trans.get("throttle_thread_stop", "Stopping throttle thread..."))
            dpg.set_value(self.no_prop_var, False)
            self.throttle_thread.join()
        print("All threads stopped.")

    def save_states(self):
        pass  # Implement saving logic

    def restore_states(self):
        pass  # Implement restoring logic

    def update_ui(self):
        # Update UI elements with new translations
        dpg.configure_item(self.drag_click_var, label=self.trans.get("drag_click", "Drag click"))
        dpg.configure_item(self.no_prop_var, label=self.trans.get("no_prop", "No Prop"))
        dpg.configure_item(self.disk_limit_scale, label=self.trans.get("disk_read_limit", "Disk Read Limit (%)"))
        dpg.configure_item(self.bind_button, label=self.trans.get("bind_key", "Bind key"))
