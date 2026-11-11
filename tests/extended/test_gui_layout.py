"""Native Tk regression checks for laptop-sized windows and preview fitting."""
from pathlib import Path
from types import SimpleNamespace
import os
import time
import pytest

tk=pytest.importorskip('tkinter')
if os.name!='nt' and not os.environ.get('DISPLAY'):
    pytest.skip('Native GUI layout needs a display; scientific worker tests remain headless',allow_module_level=True)

from jetbridge_ml.gui.app import App

ROOT=Path(__file__).resolve().parents[2]


def settle(window):
    """Process geometry and debounced preview events on this test window."""
    until=time.monotonic()+.25
    while time.monotonic()<until:
        window.update()
        time.sleep(.005)


@pytest.fixture(params=[1.0,1.5,2.0])
def gui(request,tmp_path):
    window=tk.Tk()
    window.tk.call('tk','scaling',request.param)
    app=App(window,ROOT)
    source=tk.PhotoImage(master=window,width=1600,height=900)
    file=tmp_path/'preview.png';source.write(file,format='png')
    app.figure_paths=[file];app.figures.insert('end','preview.png');app.figures.selection_set(0)
    app.tabs.select(1)
    yield window,app
    app.residual_plot.stop(SimpleNamespace(widget=app.residual_plot))
    for event in window.tk.call('after','info'):
        window.after_cancel(event)
    window.destroy()


@pytest.mark.parametrize('size',[(640,420),(800,500),(1024,600),(1280,720)])
def test_actions_and_preview_fit_the_available_window(gui,size):
    window,app=gui
    window.geometry(f'{size[0]}x{size[1]}');settle(window)
    for widget in (app.run_button,app.cancel_button,app.preview_host):
        assert widget.winfo_ismapped()
        x=widget.winfo_rootx()-window.winfo_rootx()
        y=widget.winfo_rooty()-window.winfo_rooty()
        assert x>=0 and y>=0
        assert x+widget.winfo_width()<=window.winfo_width()+2
        assert y+widget.winfo_height()<=window.winfo_height()+2
    assert app.image is not None
    assert app.image.width()<=app.preview_host.winfo_width()
    assert app.image.height()<=app.preview_host.winfo_height()
    app.control_canvas.yview_moveto(1);settle(window)
    assert app.control_canvas.yview()[1]>.99
    app.control_canvas.yview_moveto(0)
    app.reveal_focused_control(SimpleNamespace(widget=app.check));settle(window)
    # Keyboard access to a lower settings button scrolls it into the viewport.
    top=app.control_canvas.winfo_rooty()
    assert app.check.winfo_rooty()>=top-2
    assert app.check.winfo_rooty()+app.check.winfo_height()<=top+app.control_canvas.winfo_height()+3


def test_preview_tracks_shrink_and_growth_without_pillow(gui,monkeypatch):
    import builtins
    original=builtins.__import__
    def without_pillow(name,*args,**kwargs):
        if name=='PIL' or name.startswith('PIL.'):
            raise ImportError('Test the dependency-free preview path')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',without_pillow)
    window,app=gui
    for width,height in [(1200,720),(800,500),(1100,650)]:
        window.geometry(f'{width}x{height}');settle(window);app.preview()
        assert app.image.width()<=app.preview_host.winfo_width()
        assert app.image.height()<=app.preview_host.winfo_height()
