"""Remember editable options per activity without restoring any running session."""
from dataclasses import replace
import tkinter as tk

from app_settings import save_settings
from desktop_ui import _toggle_advanced


COMMON_DEFAULTS = {
    'limit': '1', 'forever': False, 'dry': True, 'no_mouse': False,
    'hidden_capture': False, 'advanced_open': False, 'region': '0,0,1,1',
}
SHOP_DEFAULTS = {'shop_budget': '', 'shop_selected': {
    'friendship': False, 'covenant': True, 'mystic': True,
}}
ARENA_DEFAULTS = {'arena_mode': 'fixed', 'arena_preferred': '1',
                  'arena_refill': False, 'arena_budget': '0'}


class ModePreferences:
    def __init__(self, app, path=None):
        self.app = app
        self.path = path
        self.pending = None
        self.restoring = False
        self.closed = False
        self.save_failed = False
        self.variables = []
        self.active = app.settings.last_mode if app.settings.last_mode in app.config else app.scenario.get()
        app.scenario.current(app.scenario.source_values.index(self.active))
        self.restore(self.active)
        for name in ('limit', 'region', 'shop_budget', 'arena_budget'):
            widget = getattr(app, name)
            variable = tk.StringVar(app.root, value=widget.get())
            widget.configure(textvariable=variable)
            variable.trace_add('write', self.changed)
            self.variables.append(variable)
        for name in ('forever', 'dry', 'no_mouse', 'hidden_capture', 'advanced_open', 'arena_refill'):
            getattr(app, name).trace_add('write', self.changed)
        for variable in app.shop_selected.values():
            variable.trace_add('write', self.changed)
        for widget in (app.arena_mode, app.arena_preferred):
            widget.bind('<<ComboboxSelected>>', self.changed, add='+')
        app.scenario.bind('<<ComboboxSelected>>', self.select_mode, add='+')

    def snapshot(self):
        app = self.app
        values = {name: getattr(app, name).get() for name in COMMON_DEFAULTS}
        if self.active == 'Reroll Secret Shop':
            values.update(shop_budget=app.shop_budget.get(),
                          shop_selected={item: var.get() for item, var in app.shop_selected.items()})
        elif self.active == 'Rookie Arena':
            values.update(arena_mode='fixed' if app.arena_mode.current() == 0 else 'sequential',
                          arena_preferred=app.arena_preferred.get(), arena_refill=app.arena_refill.get(),
                          arena_budget=app.arena_budget.get())
        profiles = dict(app.settings.mode_settings)
        profiles[self.active] = values
        app.settings = replace(app.settings, last_mode=self.active, mode_settings=profiles)

    def restore(self, mode):
        self.restoring = True
        try:
            app = self.app
            defaults = dict(COMMON_DEFAULTS)
            if mode == 'Reroll Secret Shop':
                defaults.update(SHOP_DEFAULTS)
            elif mode == 'Rookie Arena':
                defaults.update(ARENA_DEFAULTS)
            values = {**defaults, **app.settings.mode_settings.get(mode, {})}
            for name in COMMON_DEFAULTS:
                widget = getattr(app, name)
                if name == 'region':
                    self.set_entry(widget, values[name])
                else:
                    widget.set(values[name])
            if mode == 'Reroll Secret Shop':
                self.set_entry(app.shop_budget, values['shop_budget'])
                selected = {**SHOP_DEFAULTS['shop_selected'], **values['shop_selected']}
                for item, variable in app.shop_selected.items():
                    variable.set(selected[item])
            elif mode == 'Rookie Arena':
                app.arena_mode.current(0 if values['arena_mode'] == 'fixed' else 1)
                app.arena_preferred.set(values['arena_preferred'])
                app.arena_refill.set(values['arena_refill'])
                self.set_entry(app.arena_budget, values['arena_budget'])
            _toggle_advanced(app)
            app.update_limit()
        finally:
            self.restoring = False

    @staticmethod
    def set_entry(widget, value):
        widget.delete(0, 'end')
        widget.insert(0, value)

    def changed(self, *args):
        if self.restoring or self.closed:
            return
        self.snapshot()
        if self.pending is not None:
            self.app.root.after_cancel(self.pending)
        self.pending = self.app.root.after(400, self.flush)

    def select_mode(self, event=None):
        mode = self.app.scenario.get()
        if self.closed or mode == self.active:
            return
        self.snapshot()
        self.active = mode
        self.restore(mode)
        self.changed()

    def flush(self):
        if self.pending is not None:
            self.app.root.after_cancel(self.pending)
            self.pending = None
        self.snapshot()
        success = save_settings(self.app.settings, self.path)
        if not success and not self.save_failed:
            self.app.log('Không lưu được cấu hình hoạt động. Vui lòng kiểm tra quyền ghi.')
        self.save_failed = not success
        return success

    def close(self):
        success = self.flush()
        self.closed = True
        return success
