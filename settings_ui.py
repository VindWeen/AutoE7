"""Preferences and opt-in updates. All Tk calls stay on the UI thread."""
from dataclasses import replace
from queue import Queue, Empty
from threading import Thread, Event, Lock
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from app_settings import save_settings
from desktop_ui import apply_language, BG, CARD, TEXT, MUTED
from i18n import translate
from updates import UpdateResult, check_for_updates, load_release_config
from installation import is_installed
from installed_updates import DownloadCancelled, download_installer, launch_installer, discard_installer


class PreferencesController:
    def __init__(self, app, root_path):
        self.app = app
        self.root_path = root_path
        self.installed = is_installed(root_path)
        self.config = load_release_config(root_path)
        self.results = Queue()
        self.busy = False
        self.closed = False
        self.dialog = None
        self.release_dialog = None
        self.latest = None
        self.poll_id = None
        self.start_id = None
        self.manual = False
        self.startup_started = False
        self.startup_checked = False
        self.install_events = Queue()
        self.install_queue_lock = Lock()
        self.download_cancel = Event()
        self.download_busy = False
        self.downloaded = None
        self.download_release = None

    def tr(self, text):
        return translate(text, self.app.language)

    def start(self):
        if self.closed or self.startup_started:
            return
        self.startup_started = True
        self.poll_id = self.app.root.after(150, self.poll)
        if self.app.settings.check_updates and self.config.repository:
            self.header('checking')
            self.start_id = self.app.root.after(1200, self.startup_check)
        else:
            self.header('disabled' if not self.config.repository else 'off')

    def header(self, status, result=None):
        """One persistent header state; only a newer release is actionable."""
        messages = {
            'checking': 'Đang kiểm tra cập nhật…',
            'up_to_date': 'Bạn đang dùng phiên bản mới nhất.',
            'error': 'Chưa kiểm tra được cập nhật · Vẫn có thể sử dụng.',
            'no_release': 'Chưa có bản phát hành công khai.',
            'disabled': 'Chưa cấu hình cập nhật.',
            'off': 'Tự kiểm tra cập nhật đang tắt.',
        }
        if status == 'available' and result is not None:
            self.app.update_status.pack_forget()
            suffix = ' · Cập nhật' if self.installed and result.installer else ' · Xem cập nhật'
            self.app.update_button.configure(text='Có bản mới: ' + result.latest_version + suffix)
            self.app.update_button.pack(anchor='w')
        else:
            self.app.update_button.pack_forget()
            self.app.update_status.configure(text=messages.get(status, messages['error']),
                                             foreground='#abc8a6' if status == 'up_to_date' else MUTED)
            self.app.update_status.pack(anchor='w')
        self.retranslate()

    def startup_check(self):
        self.start_id = None
        if self.closed or self.startup_checked:
            return
        if self.app.settings.check_updates:
            self.startup_checked = True
            self.check()
        else:
            self.header('off')

    def close(self):
        with self.install_queue_lock:
            self.closed = True
            self.download_cancel.set()
            while True:
                try:
                    event, value = self.install_events.get_nowait()
                except Empty:
                    break
                if event == 'ready':
                    self.discard_download(value)
        for callback in (self.poll_id, self.start_id):
            if callback is not None:
                self.app.root.after_cancel(callback)

    def window(self, title, geometry):
        window = tk.Toplevel(self.app.root)
        # Positioning flushes idle tasks: keep the empty window hidden until
        # its controls and translated labels are ready.
        window.withdraw()
        window.title(self.tr(title))
        window.configure(bg=BG)
        width, height = map(int, geometry.split('x'))
        width = min(width, self.app.root.winfo_screenwidth() - 80)
        height = min(height, self.app.root.winfo_screenheight() - 100)
        self.app.root.update_idletasks()
        x = max(60, min(self.app.root.winfo_rootx() + (self.app.root.winfo_width() - width) // 2,
                        self.app.root.winfo_screenwidth() - width - 20))
        y = max(40, min(self.app.root.winfo_rooty() + (self.app.root.winfo_height() - height) // 2,
                        self.app.root.winfo_screenheight() - height - 60))
        window.geometry(f'{width}x{height}+{x}+{y}')
        window.transient(self.app.root)
        window.minsize(width, height)
        window.bind('<Escape>', lambda event: window.destroy())
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill='both', expand=True)
        return window, frame

    @staticmethod
    def present(window):
        window.update_idletasks()
        window.deiconify()
        window.lift()

    def open(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        self.dialog, frame = self.window('Cài đặt', '560x450')
        ttk.Label(frame, text='Cài đặt', style='Title.TLabel').pack(anchor='w', pady=(0, 18))
        ttk.Label(frame, text='Ngôn ngữ / Language').pack(anchor='w')
        language = ttk.Combobox(frame, state='readonly', values=['Tiếng Việt', 'English'])
        language.current(0 if self.app.language == 'vi' else 1)
        language.pack(fill='x', pady=(6, 16))
        auto = tk.BooleanVar(frame, value=self.app.settings.check_updates)
        ttk.Checkbutton(frame, text='Kiểm tra cập nhật khi mở tool', variable=auto,
                        command=lambda: self.save(auto=auto.get())).pack(anchor='w')
        language.bind('<<ComboboxSelected>>', lambda event: self.save(
            language='vi' if language.current() == 0 else 'en'))
        ttk.Label(frame, text='Phiên bản hiện tại: ' + self.config.version,
                  wraplength=490).pack(anchor='w', pady=(20, 4))
        self.feedback = ttk.Label(frame, text='', wraplength=490)
        self.feedback.pack(anchor='w', pady=(4, 12))
        ttk.Button(frame, text='Kiểm tra cập nhật', command=lambda: self.check(manual=True)).pack(anchor='w')
        ttk.Label(frame, text=('Bản cài đặt hỗ trợ tải và cài cập nhật ngay trong app.' if self.installed else
                              'Tải bản mới từ GitHub Releases, giải nén vào thư mục mới rồi mở AutoE7.exe.'),
                  wraplength=490).pack(anchor='w', pady=(16, 12))
        ttk.Button(frame, text='Đóng', command=self.dialog.destroy).pack(anchor='e', side='bottom')
        self.feedback.configure(text='Đang kiểm tra cập nhật…' if self.busy else
            'Chưa cấu hình repo GitHub.' if not self.config.repository else 'Sẵn sàng')
        self.retranslate()
        self.present(self.dialog)

    def save(self, language=None, auto=None):
        settings = replace(self.app.settings,
                           language=language or self.app.settings.language,
                           check_updates=self.app.settings.check_updates if auto is None else auto)
        if not save_settings(settings):
            messagebox.showerror(self.tr('Cài đặt'), self.tr('Không lưu được cài đặt. Vui lòng kiểm tra quyền ghi.'),
                                 parent=self.dialog)
            # Restore persisted choices so the form never claims success.
            if self.dialog is not None and self.dialog.winfo_exists():
                self.dialog.destroy()
                self.open()
            return
        self.app.settings = settings
        self.app.language = settings.language
        self.retranslate()

    def retranslate(self):
        apply_language(self.app)
        for dialog, title in ((self.dialog, 'Cài đặt'), (self.release_dialog, 'Có bản cập nhật mới')):
            if dialog is not None and dialog.winfo_exists():
                dialog.title(self.tr(title))

    def feedback_text(self, text):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.feedback.configure(text=text)
            self.retranslate()

    def check(self, manual=False):
        if self.closed:
            return
        if self.download_busy:
            self.feedback_text('Đang tải bản cập nhật…')
            return
        if self.start_id is not None:
            self.app.root.after_cancel(self.start_id)
        self.start_id = None
        if self.busy:
            self.manual = self.manual or manual
            self.feedback_text('Đang kiểm tra cập nhật…')
            return
        self.busy = True
        self.manual = manual
        self.header('checking')
        self.feedback_text('Đang kiểm tra cập nhật…')
        def work():
            try:
                result = check_for_updates(self.config)
            except Exception:
                # A failed worker must not leave the Check button stuck forever.
                result = UpdateResult('error', self.config.version)
            self.results.put(result)
        Thread(target=work, name='AutoE7-update-check', daemon=True).start()

    def poll(self):
        if self.closed:
            return
        try:
            result = self.results.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            messages = {
                'disabled': 'Chưa cấu hình repo GitHub.',
                'up_to_date': 'Bạn đang dùng phiên bản mới nhất.',
                'no_release': 'Chưa có bản phát hành công khai trên repo này.',
                'error': 'Không kiểm tra được cập nhật. Bạn vẫn có thể dùng tool và thử lại sau.',
                'available': 'Có bản cập nhật mới: ' + result.latest_version,
            }
            text = messages.get(result.status, messages['error'])
            self.feedback_text(text)
            self.header(result.status, result)
            if result.status == 'available':
                self.latest = result
                # Startup reports inline; details open only on explicit action.
                if self.manual:
                    self.show_release()
            else:
                self.latest = None
                if self.manual and not (self.dialog is not None and self.dialog.winfo_exists()):
                    messagebox.showinfo(self.tr('Kiểm tra cập nhật'), self.tr(text), parent=self.app.root)
        self.poll_install_events()
        if not self.closed:
            self.poll_id = self.app.root.after(150, self.poll)

    def show_release(self):
        if self.latest is None:
            return
        if self.release_dialog is not None and self.release_dialog.winfo_exists():
            self.release_dialog.lift()
            return
        result = self.latest
        self.release_dialog, frame = self.window('Có bản cập nhật mới', '620x530')
        ttk.Label(frame, text='Có bản cập nhật mới: ' + result.latest_version,
                  style='Title.TLabel', wraplength=560).pack(anchor='w')
        ttk.Label(frame, text='Phiên bản hiện tại: ' + self.config.version).pack(anchor='w', pady=(6, 14))
        ttk.Label(frame, text='Nội dung cập nhật').pack(anchor='w', pady=(0, 6))
        notes_frame = ttk.Frame(frame)
        notes_frame.pack(fill='both', expand=True)
        notes = tk.Text(notes_frame, height=8, wrap='word', bg=CARD, fg=TEXT, relief='flat', padx=12, pady=12)
        scroll = ttk.Scrollbar(notes_frame, command=notes.yview)
        notes.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        notes.pack(side='left', fill='both', expand=True)
        notes.insert('1.0', result.release_notes or self.tr('Xem chi tiết trên GitHub Releases.'))
        notes.configure(state='disabled')
        can_install = self.installed and result.installer is not None
        ttk.Label(frame, text=('Bấm Cập nhật để tải bản mới. Tải xong, app sẽ dừng tác vụ, cài đặt và mở lại; cấu hình được giữ nguyên.' if can_install else
                              'Bản phát hành này chưa có bộ cài cập nhật. Bạn vẫn có thể mở trang tải.' if self.installed else
                              'Dừng tool trước khi đổi bản. Tải ZIP portable trong Assets, giải nén toàn bộ vào thư mục mới rồi mở AutoE7.exe.'),
                  wraplength=560).pack(anchor='w', pady=14)
        if can_install:
            self.install_feedback = ttk.Label(frame, text='Sẵn sàng cập nhật.', wraplength=560)
            self.install_feedback.pack(anchor='w', pady=(0, 6))
            self.install_progress = ttk.Progressbar(frame, maximum=100, mode='determinate')
            self.install_progress.pack(fill='x', pady=(0, 10))
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        if can_install:
            self.install_button = ttk.Button(actions, text='Cập nhật', style='Primary.TButton',
                                              command=self.start_download)
            self.install_button.pack(side='left')
            self.cancel_download_button = ttk.Button(actions, text='Hủy tải', command=self.cancel_download,
                                                      state='disabled')
            self.cancel_download_button.pack(side='left', padx=(10, 0))
        else:
            ttk.Button(actions, text='Mở trang tải', style='Primary.TButton',
                       command=self.open_download).pack(side='left')
        ttk.Button(actions, text='Để sau', command=self.dismiss_release).pack(side='right')
        self.release_dialog.protocol('WM_DELETE_WINDOW', self.dismiss_release)
        self.release_dialog.bind('<Escape>', lambda event: self.dismiss_release())
        self.retranslate()
        self.present(self.release_dialog)

    def dismiss_release(self):
        if self.download_busy:
            self.cancel_download()
        if self.release_dialog is not None and self.release_dialog.winfo_exists():
            self.release_dialog.destroy()

    def cancel_download(self):
        self.download_cancel.set()

    @staticmethod
    def discard_download(path):
        try:
            discard_installer(path)
        except (OSError, ValueError):
            # Cache cleanup must not prevent cancellation or closing the app.
            pass

    def install_status(self, text, percent=None):
        self.app.update_button.pack_forget()
        self.app.update_status.configure(text=text, foreground=MUTED)
        self.app.update_status.pack(anchor='w')
        if self.release_dialog is not None and self.release_dialog.winfo_exists():
            self.install_feedback.configure(text=text)
            if percent is not None:
                self.install_progress.configure(value=percent)
        self.retranslate()

    def start_download(self):
        if self.closed or self.busy or self.download_busy or not self.installed:
            return
        result = self.latest
        if result is None or result.installer is None:
            return
        self.download_release = result
        self.downloaded = None
        self.download_cancel = Event()
        self.download_busy = True
        self.install_button.configure(state='disabled')
        self.cancel_download_button.configure(state='normal')
        self.install_status('Đang tải bản cập nhật…', 0)
        def work():
            previous = -1
            def progress(done, total):
                nonlocal previous
                percent = min(100, int(done * 100 / total))
                if percent != previous:
                    previous = percent
                    self.install_events.put(('progress', percent))
            try:
                path = download_installer(result.installer, self.config.repository,
                                          progress=progress, cancel=self.download_cancel)
                with self.install_queue_lock:
                    if self.closed or self.download_cancel.is_set():
                        self.discard_download(path)
                        self.install_events.put(('cancelled', None))
                    else:
                        self.install_events.put(('ready', path))
            except DownloadCancelled:
                self.install_events.put(('cancelled', None))
            except Exception:
                self.install_events.put(('failed', None))
        Thread(target=work, name='AutoE7-installer-download', daemon=True).start()

    def poll_install_events(self):
        while not self.closed:
            try:
                event, value = self.install_events.get_nowait()
            except Empty:
                return
            if event == 'progress':
                self.install_status(f'Đang tải cập nhật: {value}%', value)
                continue
            self.download_busy = False
            if self.release_dialog is not None and self.release_dialog.winfo_exists():
                self.install_button.configure(state='normal', command=self.start_download)
                self.cancel_download_button.configure(state='disabled')
            if event == 'ready' and not self.download_cancel.is_set():
                self.downloaded = value
                self.finish_install()
            else:
                if event == 'ready':
                    self.discard_download(value)
                self.install_status('Đã hủy cập nhật. Bạn có thể tiếp tục sử dụng.' if event == 'cancelled' or
                                    self.download_cancel.is_set() else
                                    'Không tải được cập nhật. Bản hiện tại vẫn dùng bình thường.')

    def finish_install(self):
        if self.closed or self.downloaded is None or self.download_release is None:
            return
        try:
            if not self.app.mode_preferences.flush():
                raise OSError('Preferences could not be saved')
            if self.app.running:
                self.app.stop('Dừng tác vụ để cập nhật.')
            launch_installer(self.downloaded, self.root_path, asset=self.download_release.installer,
                             repository=self.config.repository)
        except Exception:
            self.install_status('Chưa cài được cập nhật. Bản hiện tại vẫn dùng bình thường.')
            if self.release_dialog is not None and self.release_dialog.winfo_exists():
                self.install_button.configure(text='Thử cài lại', state='normal', command=self.finish_install)
            return
        self.app.close()

    def open_download(self):
        try:
            opened = webbrowser.open(self.latest.release_url)
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            messagebox.showinfo(self.tr('Mở trang tải'), self.tr('Mở địa chỉ này trong trình duyệt:') + '\n' +
                                self.latest.release_url, parent=self.release_dialog)
