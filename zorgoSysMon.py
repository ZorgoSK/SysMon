#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio
import psutil
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.widgets import Cursor
import pystray
from pystray import Icon as icon, Menu as menu, MenuItem as item
from PIL import Image
import os

class CPUPlotWindow(Gtk.Window):
    def __init__(self, tray_icon=None, refresh_interval=2, duration=30, maxarraysize=10000):
        super(CPUPlotWindow, self).__init__(title="zorgoSysMon")
        self.set_default_size(1300, 500)
        self.set_position(Gtk.WindowPosition.CENTER)  # Set window position to center

        self.refresh_interval = refresh_interval
        self.duration = duration
        self.maxarraysize = maxarraysize

        self.time_values = []
        self.temperature_values = []
        self.cpu_load_values = []
        self.cpu_process_load_values = []
        self.batt_level_values = []
        self.batt_charging_values = []

        self.init_ui()

        self.connect("delete-event", self.on_delete_event)
        self.connect("destroy", self.on_destroy)

    def init_ui(self):
        plt.style.use({
            'axes.facecolor': '#1a1a1a',
            'axes.edgecolor': 'gray',
            'axes.labelcolor': 'white',
            'text.color': 'white',
            'xtick.color': 'tab:blue',
            'ytick.color': 'tab:blue',
            'grid.color': 'gray',
            'figure.facecolor': '#1a1a1a',
            'figure.edgecolor': '#1a1a1a',
            'savefig.facecolor': '#1a1a1a',
            'savefig.edgecolor': '#1a1a1a',
        })

        self.fig, ax = plt.subplots(figsize=(8, 6))

        self.line_temp, = ax.plot([], [], linewidth=1, color='tab:red', label='Temperature (°C)')
        self.line_load, = ax.plot([], [], linewidth=1, color='tab:blue', label='CPU Load (%)')
        self.line_battery, = ax.plot([], [], linewidth=1, color='tab:green', label='Battery (%)')

        ax.set_ylim(0, 101)
        ax.yaxis.set_major_locator(plt.MaxNLocator(12))

        ax.set_yticklabels([f"{i}" for i in range(0, 101, 10)])

        plt.rcParams["font.family"] = "monospace"
        plt.grid(axis='y', linewidth=0.5, alpha=0.4)

        vbox = Gtk.VBox(spacing=6)
        self.add(vbox)
        vbox.pack_end(self.get_canvas(), True, True, 0)

        self.timeout = GLib.timeout_add_seconds(int(self.refresh_interval), self.update_plot)

        self.show_all()
        self.hide()


    def on_destroy(self, widget):
        self.hide()
        return True

    def on_delete_event(self, widget, event):
        self.hide()
        return True

    def set_tray_icon(self, tray_icon):
        self.tray_icon = tray_icon

    def get_canvas(self):
        canvas = FigureCanvas(self.fig)
        self.ly = self.fig.axes[0].axvline(color='red', alpha=0.4)
        canvas.mpl_connect('motion_notify_event', self.on_cursor_hover)
        return canvas

    def on_cursor_hover(self, event):
        if event.inaxes:
            if len(self.time_values) > 2:
                base_date = datetime(1970, 1, 1)
                formatted_date = base_date + timedelta(days=event.xdata)

                x_index = min(range(len(self.time_values)), key=lambda i: abs(self.time_values[i] - formatted_date))

                time_at_cursor = self.time_values[x_index].strftime('%Y-%m-%d %H:%M:%S')
                temperature_at_cursor = self.temperature_values[x_index]
                cpu_load_at_cursor = self.cpu_load_values[x_index]
                batt_level_at_cursor = self.batt_level_values[x_index]
                top_process_at_cursor = self.cpu_process_load_values[x_index]
                charging_at_cursor = self.batt_charging_values[x_index]

                if charging_at_cursor:
                    charging_at_cursor_label = 'charging'
                else:
                    charging_at_cursor_label = 'discharging'

                for annotation in self.fig.axes[0].texts:
                    annotation.remove()

                self.ly.set_xdata(event.xdata)

                self.fig.axes[0].annotate(f'{time_at_cursor}\n[{x_index}]\nCPUTemp: {temperature_at_cursor}°C\nCPULoad: {cpu_load_at_cursor}% ({top_process_at_cursor})\nBattery: {batt_level_at_cursor}% {charging_at_cursor_label}',
                                          (event.xdata, 60), textcoords="offset points", xytext=(0, 0), ha='left', fontsize='10')
                self.fig.canvas.draw()
        else:
            for annotation in self.fig.axes[0].texts:
                annotation.remove()
            self.ly.set_xdata(-1)

    def update_plot(self):
        current_time = datetime.now()
        try:
            temperature = psutil.sensors_temperatures()['coretemp'][0].current
            cpu_load = psutil.cpu_percent()
            processes = sorted(psutil.process_iter(), key=lambda p: p.cpu_percent(), reverse=True)
            process_load = processes[0].name()
            bat_level = int(psutil.sensors_battery().percent)
            bat_charger = psutil.sensors_battery().power_plugged

            if bat_charger:
                bat_charger_status = 'charging'
            else:
                bat_charger_status = 'discharging'

            if self.maxarraysize != 0:
                if len(self.time_values) > self.maxarraysize:
                    self.time_values.pop(1)
                    self.temperature_values.pop(1)
                    self.cpu_load_values.pop(1)
                    self.cpu_process_load_values.pop(1)
                    self.batt_level_values.pop(1)
                    self.batt_charging_values.pop(1)

            if temperature is not None:
                self.time_values.append(current_time)
                self.temperature_values.append(temperature)
                self.cpu_load_values.append(cpu_load)
                self.cpu_process_load_values.append(process_load)
                self.batt_level_values.append(bat_level)
                self.batt_charging_values.append(bat_charger)

                selected_duration = float(self.duration)
                if selected_duration > 1:
                    xlim_start = max(current_time - timedelta(minutes=selected_duration), self.time_values[0])
                else:
                    xlim_start = max(current_time - timedelta(seconds=(selected_duration * 60)), self.time_values[0])

                self.fig.axes[0].set_xlim(xlim_start, current_time)

                self.line_temp.set_data(self.time_values, self.temperature_values)
                self.line_load.set_data(self.time_values, self.cpu_load_values)
                self.line_battery.set_data(self.time_values, self.batt_level_values)

                self.fig.axes[0].legend([self.line_temp, self.line_load, self.line_battery],
                                        ['CPUTemp: ' + str(temperature) + '°C',
                                         'CPULoad: ' + str(cpu_load) + '% (' + process_load + ')',
                                         'Battery: ' + str(bat_level) + '% ' + bat_charger_status],
                                        loc='lower left', fontsize='10')

                self.fig.canvas.draw()
        except Exception as e:
            print(f"Error: {e}")
            return "Error fetching process info"

        return True

class TrayIcon:
    def __init__(self, window):
        self.window = window
        self.window_position = None  # Store the window position

        self.tray_icon = Gtk.StatusIcon()
        self.tray_icon.set_from_file(os.path.dirname(os.path.abspath(__file__)) + '/icon.png') 
        self.tray_icon.connect("activate", self.on_tray_icon_activate)
        self.tray_icon.set_tooltip_markup("zorgoSysMon")
        self.tray_icon.connect("popup-menu", self.on_right_click)

        self.menu = Gtk.Menu()

        # Duration submenu
        duration_submenu = Gtk.Menu()
        duration_menu = Gtk.MenuItem(label="Show duration")
        duration_menu.set_submenu(duration_submenu)
        self.menu.append(duration_menu)

        durations = [0.5, 1, 5, 10, 30, 60, 300, 600, 1440, 525600]
        for duration in durations:
            if duration <= 1:
                duration_item = Gtk.CheckMenuItem(label=f"{duration} minute")
            elif duration > 1 and duration < 60:
                duration_item = Gtk.CheckMenuItem(label=f"{duration} minutes")
            elif duration >= 60 and duration <= 1440:
                duration_item = Gtk.CheckMenuItem(label=f"{int(duration/60)} hour")
            else:
                duration_item = Gtk.CheckMenuItem(label=f"{int(duration/(60*24*365))} year")

            duration_item.set_name(str(duration))
            if duration == self.window.duration:
                duration_item.set_active(1)
            duration_item.connect("toggled", self.on_duration_toggled, duration)
            duration_submenu.append(duration_item)

        # Refresh rate submenu
        refresh_submenu = Gtk.Menu()
        refresh_menu = Gtk.MenuItem(label="Set refresh rate")
        refresh_menu.set_submenu(refresh_submenu)
        self.menu.append(refresh_menu)

        refresh_intervals = [0.1, 0.5, 1, 2, 3, 4, 5, 10, 60]
        for refresh_interval in refresh_intervals:
            if refresh_interval < 1:
                refresh_item = Gtk.CheckMenuItem(label=f"{refresh_interval} seconds")
            else:
                refresh_item = Gtk.CheckMenuItem(label=f"{refresh_interval} second")

            refresh_item.set_name(str(refresh_interval))
            if refresh_interval == self.window.refresh_interval:
                refresh_item.set_active(1)
            refresh_item.connect("toggled", self.on_refresh_toggled, refresh_interval)
            refresh_submenu.append(refresh_item)

        # Max array size submenu
        maxarraysize_submenu = Gtk.Menu()
        maxarraysize_menu = Gtk.MenuItem(label="Max Array size")
        maxarraysize_menu.set_submenu(maxarraysize_submenu)
        self.menu.append(maxarraysize_menu)

        maxarraysize_sizes = [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 0]
        for maxarraysize_size in maxarraysize_sizes:
            if maxarraysize_size == 0:
                maxarraysize_item = Gtk.CheckMenuItem(label="Unlimited")
            else:
                maxarraysize_item = Gtk.CheckMenuItem(label=f"{maxarraysize_size*1000} logs")

            maxarraysize_item.set_name(str(maxarraysize_size*1000))
            if (maxarraysize_size * 1000) == self.window.maxarraysize:
                maxarraysize_item.set_active(1)
            maxarraysize_item.connect("toggled", self.on_maxarraysize_toggled, maxarraysize_size * 1000)
            maxarraysize_submenu.append(maxarraysize_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        array_reset = Gtk.MenuItem(label="Reset array")
        array_reset.connect("activate", self.on_array_reset)
        self.menu.append(array_reset)

        self.menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)

    def on_array_reset(self, widget):
        self.window.time_values = []
        self.window.temperature_values = []
        self.window.cpu_load_values = []
        self.window.cpu_process_load_values = []
        self.window.batt_level_values = []
        self.window.batt_charging_values = []

    def on_maxarraysize_toggled(self, widget, maxarraysize):
        if widget.get_active():
            self.window.maxarraysize = maxarraysize
            self.uncheck_other_items(widget.get_parent(), maxarraysize)            

    def on_duration_toggled(self, widget, duration):
        if widget.get_active():
            self.window.duration = duration
            self.uncheck_other_items(widget.get_parent(), duration)            

    def on_refresh_toggled(self, widget, refresh_interval):
        if widget.get_active():
            self.window.refresh_interval = refresh_interval
            self.uncheck_other_items(widget.get_parent(), refresh_interval)
            GLib.source_remove(self.window.timeout)
            self.window.timeout = GLib.timeout_add(refresh_interval * 1000, self.window.update_plot)

    def uncheck_other_items(self, parent_menu, current_value):
        for child in parent_menu.get_children():
            if child.get_name() != str(current_value):
                child.set_active(False)

    def on_right_click(self, icon, button, time):
        self.menu.popup(None, None, None, None, button, time)
        self.menu.show_all()

    def on_tray_icon_activate(self, _):
        if self.window.get_property("visible"):
            self.window_position = self.window.get_position()  # Store the window position
            self.window.hide()
        else:
            if self.window_position:
                self.window.move(*self.window_position)  # Set the window position
            self.window.show()

if __name__ == "__main__":
    window = CPUPlotWindow()

    tray_icon = TrayIcon(window)
    window.set_tray_icon(tray_icon)

    Gtk.main()
