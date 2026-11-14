"""Preferences and read-only update notices. All Tk calls stay on the UI thread."""
from dataclasses import replace
from queue import Queue, Empty
from threading import Thread
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from app_settings import save_settings
from desktop_ui import apply_language, BG, CARD, TEXT
from i18n import translate
from updates import UpdateResult, check_for_updates, load_release_config


class PreferencesController:
    def __init__(self, app, root_path):
        self.app = app
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

    def tr(self, text):
        return translate(text, self.app.language)

    def start(self):
        self.poll_id = self.app.root.after(150, self.poll)
        if self.app.settings.check_updates and self.config.repository:
            self.start_id = self.app.root.after(1200, self.startup_check)

    def startup_check(self):
        self.start_id = None
        if not self.closed and self.app.settings.check_updates:
            self.check()

    def close(self):
        self.closed = True
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
        ttk.Label(frame, text='Tải bản mới từ GitHub Releases, giải nén vào thư mục mới rồi mở AutoE7.exe.',
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
        if self.start_id is not None:
            self.app.root.after_cancel(self.start_id)
        self.start_id = None
        if self.busy:
            self.manual = self.manual or manual
            self.feedback_text('Đang kiểm tra cập nhật…')
            return
        self.busy = True
        self.manual = manual
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
            if result.status == 'available':
                self.latest = result
                self.app.update_button.configure(text=text)
                self.app.update_button.pack(side='right', padx=(0, 10), anchor='n')
                self.retranslate()
                # Do not interrupt a game session when a late network result arrives.
                if self.manual or not self.app.running:
                    self.show_release()
            elif self.manual and not (self.dialog is not None and self.dialog.winfo_exists()):
                messagebox.showinfo(self.tr('Kiểm tra cập nhật'), self.tr(text), parent=self.app.root)
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
        ttk.Label(frame, text='Dừng tool trước khi đổi bản. Tải ZIP portable trong Assets, giải nén toàn bộ vào thư mục mới rồi mở AutoE7.exe.',
                  wraplength=560).pack(anchor='w', pady=14)
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        ttk.Button(actions, text='Mở trang tải', style='Primary.TButton',
                   command=self.open_download).pack(side='left')
        ttk.Button(actions, text='Để sau', command=self.release_dialog.destroy).pack(side='right')
        self.retranslate()
        self.present(self.release_dialog)

    def open_download(self):
        try:
            opened = webbrowser.open(self.latest.release_url)
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            messagebox.showinfo(self.tr('Mở trang tải'), self.tr('Mở địa chỉ này trong trình duyệt:') + '\n' +
                                self.latest.release_url, parent=self.release_dialog)
