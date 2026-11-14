"""Desktop presentation for AutoE7. Automation remains in app.py."""
import tkinter as tk
from tkinter import ttk
from secret_shop import ITEMS
from i18n import translate
from updates import load_release_config

BG = '#17191e'
CARD = '#22252b'
FIELD = '#30343c'
TEXT = '#f4eee1'
MUTED = '#b6b1a8'
GOLD = '#e2b55f'
BUILD = load_release_config().version


class LocalizedCombobox(ttk.Combobox):
    """Display translated labels while keeping automation keys unchanged."""

    def __init__(self, master, *, language, values, **kwargs):
        self.source_values = list(values)
        self.language = language
        super().__init__(master, values=self.source_values, **kwargs)
        self.retranslate()

    def get(self):
        index = self.current()
        return self.source_values[index] if index >= 0 else super().get()

    def retranslate(self):
        index = self.current()
        self.configure(values=[translate(value, self.language()) for value in self.source_values])
        if index >= 0:
            self.current(index)


class LocalizedStringVar(tk.StringVar):
    def __init__(self, master, language, value=''):
        self.language = language
        self.source = value
        super().__init__(master, value=translate(value, language()))

    def set(self, value):
        self.source = str(value)
        super().set(translate(self.source, self.language()))

    def retranslate(self):
        super().set(translate(self.source, self.language()))


def apply_language(app):
    """Refresh labels in place, preserving form values and active automation."""
    language = getattr(app, 'language', 'vi')
    def visit(widget):
        if isinstance(widget, LocalizedCombobox):
            widget.retranslate()
        elif 'text' in widget.keys():
            current = str(widget.cget('text'))
            if current != getattr(widget, '_i18n_last', None):
                widget._i18n_source = current
            translated = translate(getattr(widget, '_i18n_source', current), language)
            widget.configure(text=translated)
            widget._i18n_last = translated
        for child in widget.winfo_children():
            visit(child)
    visit(app.root)
    if isinstance(app.status, LocalizedStringVar):
        app.status.retranslate()


def build_ui(app):
    root = app.root
    root.title('AutoE7 · ' + BUILD)
    width = min(1040, max(900, root.winfo_screenwidth() - 80))
    height = min(780, max(620, root.winfo_screenheight() - 100))
    root.geometry(f'{width}x{height}')
    root.minsize(900, 620)
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Segoe UI', 10), background=BG, foreground=TEXT)
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background=CARD)
    style.configure('Card.TLabel', background=CARD, foreground=TEXT)
    style.configure('Muted.TLabel', background=CARD, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Section.TLabel', background=CARD, foreground=GOLD, font=('Segoe UI', 10, 'bold'))
    style.configure('Title.TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 21, 'bold'))
    style.configure('Sub.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 10))
    style.configure('TCheckbutton', background=CARD, foreground=TEXT, padding=(0, 2))
    style.map('TCheckbutton', background=[('active', CARD), ('disabled', CARD)], foreground=[('disabled', '#777b80')])
    style.configure('TButton', background=FIELD, foreground=TEXT, borderwidth=0, padding=(12, 7))
    style.map('TButton', background=[('active', '#484c54'), ('disabled', '#292c31')], foreground=[('disabled', '#777b80')])
    style.configure('Primary.TButton', background=GOLD, foreground='#211b12', font=('Segoe UI', 10, 'bold'), padding=(20, 10))
    style.map('Primary.TButton', background=[('active', '#f0c87b'), ('disabled', '#554a35')], foreground=[('disabled', '#aaa092')])
    style.configure('Stop.TButton', background='#593639', foreground='#ffe4de', font=('Segoe UI', 10, 'bold'), padding=(18, 10))
    style.map('Stop.TButton', background=[('active', '#754649'), ('disabled', '#30292c')], foreground=[('disabled', '#766a6a')])
    style.configure('TEntry', fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, bordercolor=FIELD, padding=5)
    style.configure('TSpinbox', fieldbackground=FIELD, foreground=TEXT, arrowcolor=TEXT, bordercolor=FIELD, padding=5)
    style.configure('TCombobox', fieldbackground=FIELD, foreground=TEXT, arrowcolor=TEXT, bordercolor=FIELD, padding=5)
    for name in ('TEntry', 'TSpinbox', 'TCombobox'):
        style.configure(name, lightcolor=FIELD, darkcolor=FIELD)
        style.map(name, bordercolor=[('focus', GOLD), ('!focus', FIELD)],
                  lightcolor=[('focus', GOLD), ('!focus', FIELD)],
                  darkcolor=[('focus', GOLD), ('!focus', FIELD)])
    style.configure('Vertical.TScrollbar', background=FIELD, troughcolor=CARD,
                    bordercolor=CARD, lightcolor=FIELD, darkcolor=FIELD, arrowcolor=MUTED)
    style.map('Vertical.TScrollbar', background=[('active', '#555a63')])
    style.configure('TCheckbutton', indicatorbackground=FIELD, indicatorcolor=GOLD,
                    indicatormargin=3, indicatorrelief='flat')
    style.map('TCheckbutton', indicatorbackground=[('selected', GOLD), ('disabled', '#383a3d'), ('!selected', FIELD)],
              indicatorcolor=[('selected', '#211b12')])
    style.map('TCombobox', fieldbackground=[('readonly', FIELD), ('disabled', '#292c31')], foreground=[('readonly', TEXT), ('disabled', '#777b80')])
    root.option_add('*TCombobox*Listbox.background', FIELD)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground', '#806434')

    outer = ttk.Frame(root, padding=(24, 17, 24, 16))
    outer.pack(fill='both', expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(1, weight=1)
    header = ttk.Frame(outer)
    header.grid(row=0, column=0, sticky='ew', pady=(0, 14))
    app.settings_button = ttk.Button(header, text='⚙ Settings / Cài đặt', command=app.open_settings)
    app.settings_button.pack(side='right', anchor='n')
    app.update_button = ttk.Button(header, command=lambda: app.preferences.show_release())
    ttk.Label(header, text='AutoE7', style='Title.TLabel').pack(anchor='w')
    ttk.Label(header, text='Thiết lập và theo dõi phiên tự động', style='Sub.TLabel').pack(anchor='w')
    body = ttk.Frame(outer)
    body.grid(row=1, column=0, sticky='nsew')
    body.columnconfigure(0, weight=3, uniform='columns')
    body.columnconfigure(1, weight=2, uniform='columns')
    body.rowconfigure(0, weight=1)
    left_shell = ttk.Frame(body, style='Card.TFrame')
    left_shell.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
    canvas = tk.Canvas(left_shell, background=CARD, highlightthickness=0, borderwidth=0)
    left_scroll = ttk.Scrollbar(left_shell, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=left_scroll.set)
    canvas.pack(side='left', fill='both', expand=True)
    left = ttk.Frame(canvas, style='Card.TFrame', padding=18)
    canvas_window = canvas.create_window((0, 0), window=left, anchor='nw')

    def resize_content(event=None):
        canvas.configure(scrollregion=canvas.bbox('all'))
        needed = left.winfo_reqheight() > canvas.winfo_height()
        if needed and not left_scroll.winfo_ismapped():
            left_scroll.pack(side='right', fill='y')
        elif not needed and left_scroll.winfo_ismapped():
            left_scroll.pack_forget()
            canvas.yview_moveto(0)

    def resize_canvas(event):
        canvas.itemconfigure(canvas_window, width=event.width)
        resize_content()

    left.bind('<Configure>', resize_content)
    canvas.bind('<Configure>', resize_canvas)
    right = ttk.Frame(body, style='Card.TFrame', padding=18)
    right.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

    ttk.Label(left, text='THIẾT LẬP', style='Section.TLabel').pack(anchor='w', pady=(0, 9))
    ttk.Label(left, text='Cửa sổ game', style='Card.TLabel').pack(anchor='w')
    winrow = ttk.Frame(left, style='Card.TFrame')
    winrow.pack(fill='x', pady=(4, 10))
    app.window = ttk.Combobox(winrow, state='readonly')
    app.window.pack(side='left', fill='x', expand=True)
    app.refresh_button = ttk.Button(winrow, text='Làm mới', command=app.refresh)
    app.refresh_button.pack(side='left', padx=(8, 0))
    ttk.Label(left, text='Hoạt động', style='Card.TLabel').pack(anchor='w')
    app.scenario = LocalizedCombobox(left, language=lambda: getattr(app, 'language', 'vi'), state='readonly', values=list(app.config))
    app.scenario.current(0)
    app.scenario.pack(fill='x', pady=(4, 10))
    app.scenario.bind('<<ComboboxSelected>>', app.update_limit)

    app.scenario_help = ttk.Label(left, text='', style='Muted.TLabel', wraplength=500)
    app.scenario_help.pack(anchor='w', pady=(0, 6))
    app.mode_options = ttk.Frame(left, style='Card.TFrame')
    app.mode_options.pack(fill='x')
    app.count_options = ttk.Frame(app.mode_options, style='Card.TFrame')
    countrow = ttk.Frame(app.count_options, style='Card.TFrame')
    countrow.pack(fill='x')
    app.limit_label = ttk.Label(countrow, text='Số vòng', style='Card.TLabel')
    app.limit_label.pack(side='left')
    app.limit = ttk.Spinbox(countrow, from_=1, to=9999, width=8)
    app.limit.set('1')
    app.limit.pack(side='left', padx=(12, 0))
    app.forever = tk.BooleanVar(value=False)
    app.forever_check = ttk.Checkbutton(app.count_options, text='Chạy tới khi dừng', variable=app.forever, command=app.update_limit)
    app.shop_options = ttk.Frame(app.mode_options, style='Card.TFrame')
    ttk.Label(app.shop_options, text='Món muốn mua', style='Card.TLabel').pack(anchor='w')
    app.shop_selected = {}
    app.shop_checks = []
    for kind, label in ITEMS.items():
        var = tk.BooleanVar(value=kind in ('covenant', 'mystic'))
        app.shop_selected[kind] = var
        prices = {'friendship': '18,000', 'covenant': '184,000', 'mystic': '280,000'}
        check = ttk.Checkbutton(app.shop_options, text=f'{label}  ·  {prices[kind]} Gold', variable=var)
        check.pack(anchor='w')
        app.shop_checks.append(check)
    budgetrow = ttk.Frame(app.shop_options, style='Card.TFrame')
    budgetrow.pack(fill='x', pady=(5, 0))
    ttk.Label(budgetrow, text='Ngân sách Skystone', style='Card.TLabel').pack(side='left')
    app.shop_budget = ttk.Entry(budgetrow, width=12)
    app.shop_budget.pack(side='left', padx=(10, 0))
    ttk.Label(app.shop_options, text='Bội số của 3 · Để trống để chạy tới khi dừng', style='Muted.TLabel').pack(anchor='w', pady=(2, 0))

    app.arena_options = ttk.Frame(app.mode_options, style='Card.TFrame')
    app.arena_mode = LocalizedCombobox(app.arena_options, language=lambda: getattr(app, 'language', 'vi'), state='readonly', values=['Cố định vị trí ưu tiên', 'Tuần tự 1 → 2 → 3'])
    app.arena_mode.current(0)
    app.arena_mode.pack(fill='x', pady=(6, 4))
    prefrow = ttk.Frame(app.arena_options, style='Card.TFrame')
    prefrow.pack(fill='x')
    ttk.Label(prefrow, text='Vị trí ưu tiên', style='Card.TLabel').pack(side='left')
    app.arena_preferred = ttk.Combobox(prefrow, state='readonly', values=['1', '2', '3'], width=5)
    app.arena_preferred.current(0)
    app.arena_preferred.pack(side='left', padx=(12, 0))
    app.arena_mode.bind('<<ComboboxSelected>>', app.update_limit)
    app.arena_refill = tk.BooleanVar(value=False)
    app.arena_refill_check = ttk.Checkbutton(app.arena_options, text='Tự mua lượt khi hết · ưu tiên tim', variable=app.arena_refill)
    app.arena_refill_check.pack(anchor='w', pady=(5, 0))
    arena_budgetrow = ttk.Frame(app.arena_options, style='Card.TFrame')
    arena_budgetrow.pack(fill='x', pady=(4, 0))
    ttk.Label(arena_budgetrow, text='Ngân sách SkyStone / lần chạy', style='Card.TLabel').pack(side='left')
    app.arena_budget = ttk.Entry(arena_budgetrow, width=9)
    app.arena_budget.insert(0, '0')
    app.arena_budget.pack(side='left', padx=(10, 0))
    ttk.Label(app.arena_options, text='30 SkyStone / 5 lượt · 0: chỉ mua bằng tim', style='Muted.TLabel').pack(anchor='w', pady=(2, 0))

    ttk.Separator(left).pack(fill='x', pady=10)
    ttk.Label(left, text='CÁCH CHẠY', style='Section.TLabel').pack(anchor='w', pady=(0, 4))
    app.dry = tk.BooleanVar(value=True)
    app.dry_check = ttk.Checkbutton(left, text='Chỉ nhận diện · không click', variable=app.dry)
    app.dry_check.pack(anchor='w')
    app.no_mouse = tk.BooleanVar(value=False)
    app.mouse_check = ttk.Checkbutton(left, text='Không chiếm chuột', variable=app.no_mouse)
    app.mouse_check.pack(anchor='w')
    app.hidden_capture = tk.BooleanVar(value=False)
    app.capture_check = ttk.Checkbutton(left, text='Chụp cửa sổ khi bị che', variable=app.hidden_capture)
    app.capture_check.pack(anchor='w')
    ttk.Label(left, text='Không thu nhỏ game trong khi chạy.', style='Muted.TLabel').pack(anchor='w', pady=(2, 0))
    app.advanced_open = tk.BooleanVar(value=False)
    app.advanced_check = ttk.Checkbutton(left, text='Vùng game nâng cao', variable=app.advanced_open, command=lambda: _toggle_advanced(app))
    app.advanced_check.pack(anchor='w', pady=(4, 0))
    app.advanced = ttk.Frame(left, style='Card.TFrame')
    ttk.Label(app.advanced, text='Trái, trên, phải, dưới (tỷ lệ 0–1)', style='Muted.TLabel').pack(anchor='w')
    app.region = ttk.Entry(app.advanced)
    app.region.insert(0, '0,0,1,1')
    app.region.pack(fill='x', pady=(3, 0))

    ttk.Label(right, text='TRẠNG THÁI', style='Section.TLabel').pack(anchor='w', pady=(0, 8))
    app.status = LocalizedStringVar(root, lambda: getattr(app, 'language', 'vi'), value='Sẵn sàng')
    app.status_label = ttk.Label(right, textvariable=app.status, style='Card.TLabel', width=1, anchor='nw', wraplength=335, justify='left')
    app.status_label.pack(fill='x', anchor='w', pady=(0, 15))
    def resize_status(event):
        wrap = max(120, event.width)
        if int(float(app.status_label.cget('wraplength'))) != wrap:
            app.status_label.configure(wraplength=wrap)
    app.status_label.bind('<Configure>', resize_status)
    ttk.Separator(right).pack(fill='x', pady=(0, 12))
    ttk.Label(right, text='Nhật ký hoạt động', style='Card.TLabel', font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 7))
    logframe = ttk.Frame(right, style='Card.TFrame')
    logframe.pack(fill='both', expand=True)
    app.logbox = tk.Text(logframe, width=1, height=1, state='disabled', wrap='word', background='#191c21', foreground='#e7e0d4', insertbackground=TEXT, relief='flat', borderwidth=0, padx=10, pady=10, font=('Consolas', 10))
    scrollbar = ttk.Scrollbar(logframe, command=app.logbox.yview)
    app.logbox.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    app.logbox.pack(side='left', fill='both', expand=True)
    footer = ttk.Frame(outer)
    footer.grid(row=2, column=0, sticky='ew', pady=(14, 0))
    app.start_button = ttk.Button(footer, text='Bắt đầu', style='Primary.TButton', command=app.start)
    app.start_button.pack(side='left')
    app.stop_button = ttk.Button(footer, text='Dừng', style='Stop.TButton', command=lambda: app.stop('Đã dừng.'))
    app.stop_button.pack(side='left', padx=(8, 0))
    ttk.Label(footer, text='F8  ·  Dừng khẩn cấp', style='Sub.TLabel').pack(side='right')
    def bind_wheel(widget):
        if not isinstance(widget, (ttk.Combobox, ttk.Spinbox, ttk.Entry)):
            widget.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        for child in widget.winfo_children():
            bind_wheel(child)
    bind_wheel(left)
    canvas.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
    app.update_limit()
    set_running_ui(app, False)


def _toggle_advanced(app):
    if app.advanced_open.get():
        app.advanced.pack(fill='x', pady=(2, 0))
    else:
        app.advanced.pack_forget()


def update_scenario_ui(app):
    shop = app.scenario.get() == 'Reroll Secret Shop'
    abyss = app.scenario.get() == 'Abyss (Tháp)'
    arena = app.scenario.get() == 'Rookie Arena'
    app.limit_label.configure(text='Số trận' if arena else 'Số tầng' if abyss else 'Số vòng')
    app.scenario_help.configure(text=('Quét shop hiện tại và mua các món đã chọn.' if shop else
                                      'Mở sẵn danh sách Rookie Arena. Giữ nguyên đội hình đang chọn.' if arena else
                                      'Hoàn thành từng tầng cho đến giới hạn đã chọn.' if abyss else
                                      'Chọn số vòng hoặc tích Chạy tới khi dừng.' if app.scenario.get() == 'Đi Map' else
                                      'Chọn số vòng muốn chạy.'))
    if shop:
        app.count_options.pack_forget()
        app.shop_options.pack(fill='x')
    else:
        app.shop_options.pack_forget()
        app.count_options.pack(fill='x')
    if arena:
        app.arena_options.pack(fill='x')
    else:
        app.arena_options.pack_forget()
    app.arena_preferred.configure(state='readonly' if not app.running and app.arena_mode.get() == 'Cố định vị trí ưu tiên' else 'disabled')
    if abyss or arena or app.scenario.get() == 'Đi Map':
        app.forever_check.pack(anchor='w', pady=(3, 0))
    else:
        app.forever_check.pack_forget()
    app.limit.configure(state='disabled' if app.running or ((abyss or arena or app.scenario.get() == 'Đi Map') and app.forever.get()) else 'normal')
    apply_language(app)


def set_running_ui(app, running):
    state = 'disabled' if running else 'normal'
    for widget in (app.refresh_button, app.forever_check, app.shop_budget, app.dry_check,
                   app.mouse_check, app.capture_check, app.advanced_check, app.region, *app.shop_checks):
        widget.configure(state=state)
    app.arena_refill_check.configure(state=state)
    app.arena_budget.configure(state=state)
    app.arena_mode.configure(state='disabled' if running else 'readonly')
    app.arena_preferred.configure(state='readonly' if not running and app.arena_mode.get() == 'Cố định vị trí ưu tiên' else 'disabled')
    for widget in (app.window, app.scenario):
        widget.configure(state='disabled' if running else 'readonly')
    app.start_button.configure(state='disabled' if running else 'normal')
    app.stop_button.configure(state='normal' if running else 'disabled')
    app.limit.configure(state='disabled' if running or (app.scenario.get() in ('Đi Map', 'Abyss (Tháp)', 'Rookie Arena') and app.forever.get()) else 'normal')
