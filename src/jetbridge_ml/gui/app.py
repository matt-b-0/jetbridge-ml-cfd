"""Tk desktop GUI with a separate Python/WSL scientific worker."""
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from .config import KINDS, METHODS, MESHES, RunSpec, available_runs, cell_count, validate_output, windows_to_wsl, worker_arguments
from .guidance import guide_text, validation_message
from .progress import ResidualPlot


class App:
    """Keep GUI events responsive while an isolated worker owns all calculations."""

    def __init__(self, window, root):
        self.window, self.root = window, Path(root).resolve()
        self.events = queue.Queue(); self.process = None; self.output = None
        self.last_output = None; self.runtime_check = False; self.image = None
        window.title('Jet Bridge CFD and Reconstruction Lab')
        # Let Tk/Windows retain the user's DPI scaling. Fit the starting window
        # to the display rather than imposing a desktop-sized minimum.
        width=max(320,min(1370,window.winfo_screenwidth()-64))
        height=max(300,min(880,window.winfo_screenheight()-96))
        window.geometry(f'{width}x{height}')
        window.minsize(min(640,width),min(420,height))
        self._preview_after=None;self._preview_key=None;self._preview_original=None
        self._sash_initialised=False;self._left_width=0;self._last_manifest=None
        style=ttk.Style();style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10))
        style.configure('TFrame',background='#F5F7FA')
        style.configure('TLabel',background='#F5F7FA',foreground='#173345')
        style.configure('Heading.TLabel',font=('Segoe UI',20,'bold'))
        style.configure('Section.TLabel',font=('Segoe UI',11,'bold'))
        style.configure('Run.TButton',font=('Segoe UI',11,'bold'),padding=7)
        outer=ttk.Frame(window,padding=12);outer.pack(fill='both',expand=True)
        self.heading=ttk.Label(outer,text='Jet Bridge CFD and Reconstruction Lab',style='Heading.TLabel')
        self.heading.pack(fill='x',anchor='w')
        self.subtitle=ttk.Label(outer,text='Choose a setup, run an analysis, and inspect its numerical evidence.')
        self.subtitle.pack(fill='x',anchor='w',pady=(3,10))
        self.panes=ttk.Panedwindow(outer,orient='horizontal');self.panes.pack(fill='both',expand=True)
        left_pane=ttk.Frame(self.panes,width=330);self.right=right=ttk.Frame(self.panes)
        self.panes.add(left_pane,weight=0);self.panes.add(right,weight=1)
        left_pane.columnconfigure(0,weight=1);left_pane.rowconfigure(0,weight=1)
        self.control_canvas=tk.Canvas(left_pane,width=1,height=1,highlightthickness=0,
                                      borderwidth=0,background='#F5F7FA')
        self.control_canvas.grid(row=0,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(left_pane,orient='vertical',command=self.control_canvas.yview)
        scrollbar.grid(row=0,column=1,sticky='ns');self.control_canvas.configure(yscrollcommand=scrollbar.set)
        self.left=left=ttk.Frame(self.control_canvas,padding=(0,0,8,8))
        self.control_window=self.control_canvas.create_window((0,0),window=left,anchor='nw')
        left.bind('<Configure>',self.update_scroll_region)
        self.control_canvas.bind('<Configure>',self.resize_controls)
        window.bind('<MouseWheel>',self.scroll_controls,add='+')
        window.bind('<Button-4>',self.scroll_controls,add='+')
        window.bind('<Button-5>',self.scroll_controls,add='+')
        window.bind('<FocusIn>',self.reveal_focused_control,add='+')
        self.panes.bind('<Configure>',self.resize_layout)
        right.bind('<Configure>',self.resize_results)
        self.kind=tk.StringVar(value=KINDS['lab']);self.run=tk.StringVar()
        self.method=tk.StringVar(value=METHODS['rbf']);self.mesh=tk.StringVar(value='Standard — 141,312 cells')
        self.folder=tk.StringVar(value=str(self.root/'gui_runs'))
        self.python=tk.StringVar(value=os.environ.get('JETBRIDGE_WORKER_PYTHON',
                       '/home/mattb/projects/jetbridge-python-env/bin/python' if os.name=='nt' else sys.executable))
        self.distro=tk.StringVar(value='Ubuntu-24.04')
        self.status=tk.StringVar(value='Ready. No solver has run in this session.')
        self.detail=tk.StringVar();self.summary=tk.StringVar(value='Results will appear after a job finishes.')
        self.widgets=[]
        self.kind_box=self.combo(left,'Run type',self.kind,list(KINDS.values()))
        self.run_box=self.combo(left,'Experimental setup',self.run,[])
        self.method_box=self.combo(left,'Interpolation / regression',self.method,list(METHODS.values()))
        self.processes=tk.StringVar(value='1')
        self.processes_box=self.combo(left,'Solver processes (1 = serial; >1 = MPI)',self.processes,['1','2','4','8'])
        self.mesh_box=self.combo(left,'Mesh resolution',self.mesh,[self.mesh_label(k) for k in MESHES])
        self.kind_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_options())
        self.mesh_box.bind('<<ComboboxSelected>>',lambda e:self.describe())
        self.processes_box.bind('<<ComboboxSelected>>',lambda e:self.describe())
        self.run_box.bind('<<ComboboxSelected>>',lambda e:self.describe())
        ttk.Label(left,textvariable=self.detail,wraplength=300,justify='left').pack(fill='x',pady=(10,12))
        ttk.Label(left,text='Worker runtime',style='Section.TLabel').pack(anchor='w',pady=(6,4))
        if os.name=='nt':
            ttk.Label(left,text='WSL distribution').pack(fill='x',anchor='w')
            self.entry(left,self.distro)
        ttk.Label(left,text='Scientific Python executable (Linux path in WSL)').pack(fill='x',anchor='w')
        self.entry(left,self.python)
        ttk.Label(left,text='Output parent folder').pack(fill='x',anchor='w',pady=(8,0))
        self.entry(left,self.folder)
        self.browse=ttk.Button(left,text='Choose folder…',command=self.choose_folder)
        self.browse.pack(fill='x',pady=4);self.widgets.append(self.browse)
        self.check=ttk.Button(left,text='Check runtime',command=self.check_runtime)
        self.check.pack(fill='x',pady=(8,4));self.widgets.append(self.check)
        ttk.Label(left,text='Resolution describes cell counts, not physical accuracy. Archived thermal fields are diagnostic only.',
                  wraplength=300,foreground='#6B4B26').pack(fill='x',pady=(12,4))
        # Keep the job actions accessible even when the settings need scrolling.
        actions=ttk.Frame(left_pane,padding=(0,8,8,0));actions.grid(row=1,column=0,columnspan=2,sticky='ew')
        self.run_button=ttk.Button(actions,text='Run selected setup',style='Run.TButton',command=self.start)
        self.run_button.pack(fill='x',pady=(0,4))
        self.cancel_button=ttk.Button(actions,text='Cancel this job',command=self.cancel,state='disabled')
        self.cancel_button.pack(fill='x')
        self.progress=ttk.Progressbar(right,mode='indeterminate');self.progress.pack(fill='x')
        self.status_label=ttk.Label(right,textvariable=self.status,style='Section.TLabel',wraplength=500)
        self.status_label.pack(fill='x',anchor='w',pady=7)
        self.tabs=ttk.Notebook(right);self.tabs.pack(fill='both',expand=True)
        logs=ttk.Frame(self.tabs);results=ttk.Frame(self.tabs);self.tabs.add(logs,text='Log');self.tabs.add(results,text='Results')
        self.log=tk.Text(logs,width=1,height=1,wrap='word',font=('Consolas',10),background='#102C3C',foreground='#E3F0F4',state='disabled')
        scroll=ttk.Scrollbar(logs,orient='vertical',command=self.log.yview);self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.log.pack(fill='both',expand=True)
        results.columnconfigure(0,weight=1);results.rowconfigure(3,weight=1)
        self.summary_frame=summary_frame=ttk.Frame(results);summary_frame.grid(row=0,column=0,sticky='ew',pady=5)
        self.summary_text=tk.Text(summary_frame,width=1,height=4,wrap='word',font=('Segoe UI',10),
                                  background='#F5F7FA',foreground='#173345',relief='flat',state='disabled')
        summary_scroll=ttk.Scrollbar(summary_frame,orient='vertical',command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        summary_scroll.pack(side='right',fill='y');self.summary_text.pack(fill='x',expand=True)
        self.summary.trace_add('write',self.update_summary);self.update_summary()
        self.toolbar=ttk.Frame(results);self.toolbar.grid(row=1,column=0,sticky='ew')
        self.result_buttons=[ttk.Button(self.toolbar,text=text,command=command) for text,command in
                             [('Open result gallery',self.open_gallery),('Open output folder',self.open_folder),
                              ('Open full-size figure',self.open_figure)]]
        self.results_menu=ttk.Menubutton(self.toolbar,text='Open results…')
        menu=tk.Menu(self.results_menu,tearoff=False)
        for label,command in [('Result gallery',self.open_gallery),('Output folder',self.open_folder),('Full-size figure',self.open_figure)]:
            menu.add_command(label=label,command=command)
        menu.add_separator();menu.add_command(label='Run summary',command=self.show_summary)
        self.results_menu.configure(menu=menu)
        self.figures=tk.Listbox(results,width=1,height=3,font=('Segoe UI',10),exportselection=False)
        self.figures.grid(row=2,column=0,sticky='ew',pady=6);self.figures.bind('<<ListboxSelect>>',self.preview)
        self.preview_host=ttk.Frame(results,width=1,height=1)
        self.preview_host.grid(row=3,column=0,sticky='nsew')
        self.preview_host.pack_propagate(False);self.preview_host.grid_propagate(False)
        self.preview_label=ttk.Label(self.preview_host,anchor='center')
        self.preview_label.pack(fill='both',expand=True,padx=4,pady=4)
        self.preview_host.bind('<Configure>',self.schedule_preview)
        self.residual_plot=ResidualPlot(self.tabs);self.tabs.add(self.residual_plot,text='Residuals')
        self.guide_tab=ttk.Frame(self.tabs);self.tabs.add(self.guide_tab,text='Help')
        self.guide_view=tk.Text(self.guide_tab,width=1,height=1,wrap='word',font=('Segoe UI',10),
                                background='#F5F7FA',foreground='#173345',relief='flat',padx=12,pady=10)
        guide_scroll=ttk.Scrollbar(self.guide_tab,orient='vertical',command=self.guide_view.yview)
        self.guide_view.configure(yscrollcommand=guide_scroll.set)
        guide_scroll.pack(side='right',fill='y');self.guide_view.pack(fill='both',expand=True)
        self.method_box.bind('<<ComboboxSelected>>',lambda e:self.update_guide())
        self.figure_paths=[]
        self.refresh_options();self.tabs.select(self.guide_tab);window.after(150,self.poll);window.protocol('WM_DELETE_WINDOW',self.close)

    def update_scroll_region(self,event=None):
        """Keep every control reachable after font, DPI or wrap changes."""
        self.control_canvas.configure(scrollregion=self.control_canvas.bbox('all'))

    def resize_controls(self,event):
        width=max(1,event.width)
        self.control_canvas.itemconfigure(self.control_window,width=width)
        if width!=self._left_width:
            self._left_width=width
            for widget in self.left.winfo_children():
                if isinstance(widget,ttk.Label):widget.configure(wraplength=max(80,width-12))

    def resize_layout(self,event):
        if event.widget is not self.panes:return
        width=event.width
        if width<100:return
        current=self.panes.sashpos(0)
        target=min(350,max(240,int(width*.32))) if not self._sash_initialised else current
        target=max(min(220,width//2),min(target,max(220,width-250)))
        if current!=target:self.panes.sashpos(0,target)
        self._sash_initialised=True
        self.heading.configure(wraplength=max(160,width-8))
        self.subtitle.configure(wraplength=max(160,width-8))

    def resize_results(self,event):
        if event.widget is not self.right:return
        self.status_label.configure(wraplength=max(100,event.width-12))
        if not hasattr(self,'result_buttons'):return
        needed=max(button.winfo_reqwidth() for button in self.result_buttons)+8
        columns=max(1,min(3,event.width//max(1,needed)))
        for button in self.result_buttons:button.grid_forget()
        self.results_menu.grid_forget()
        compact=event.width<needed*2 or event.height<450
        if event.height<340:self.summary_frame.grid_remove()
        else:self.summary_frame.grid()
        self.summary_text.configure(height=2 if event.height<500 else 4)
        self.figures.configure(height=1 if event.height<340 else (2 if event.height<500 else 3))
        if compact:
            self.results_menu.grid(row=0,column=0,sticky='ew',padx=3,pady=2)
            for column in range(3):self.toolbar.columnconfigure(column,weight=1 if column==0 else 0)
            return
        for index,button in enumerate(self.result_buttons):
            button.grid(row=index//columns,column=index%columns,sticky='ew',padx=3,pady=2)
        for column in range(3):self.toolbar.columnconfigure(column,weight=1 if column<columns else 0)

    def scroll_controls(self,event):
        widget=self.window.winfo_containing(event.x_root,event.y_root)
        while widget is not None and widget is not self.left:widget=widget.master
        if widget is None:return
        bounds=self.control_canvas.bbox('all')
        if not bounds or bounds[3]<=self.control_canvas.winfo_height():return
        delta=getattr(event,'delta',0)
        units=(-max(1,abs(delta)//120) if delta>0 else max(1,abs(delta)//120)) if delta else (-1 if event.num==4 else 1)
        self.control_canvas.yview_scroll(units,'units');return 'break'

    def reveal_focused_control(self,event):
        widget=event.widget;parent=widget
        while parent is not None and parent is not self.left:parent=parent.master
        if parent is None:return
        bounds=self.control_canvas.bbox('all')
        if not bounds:return
        total=max(1,bounds[3]);top=self.control_canvas.canvasy(0);height=self.control_canvas.winfo_height()
        y=widget.winfo_rooty()-self.left.winfo_rooty()
        if y<top:self.control_canvas.yview_moveto(max(0,y/total))
        elif y+widget.winfo_height()>top+height:
            self.control_canvas.yview_moveto(max(0,(y+widget.winfo_height()-height)/total))

    def show_summary(self):
        """Keep the complete result text available when compact mode hides it."""
        window=tk.Toplevel(self.window);window.title('Jet Bridge run summary')
        window.geometry(f'{min(700,max(300,window.winfo_screenwidth()-80))}x{min(400,max(200,window.winfo_screenheight()-120))}')
        frame=ttk.Frame(window,padding=12);frame.pack(fill='both',expand=True)
        text=tk.Text(frame,wrap='word',width=1,height=1,font=('Segoe UI',10))
        scroll=ttk.Scrollbar(frame,orient='vertical',command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True)
        text.insert('1.0',self.summary.get());text.configure(state='disabled')

    def update_summary(self,*args):
        self.summary_text.configure(state='normal');self.summary_text.delete('1.0','end')
        self.summary_text.insert('1.0',self.summary.get());self.summary_text.configure(state='disabled')

    def schedule_preview(self,event=None):
        if self._preview_after is not None:self.window.after_cancel(self._preview_after)
        self._preview_after=self.window.after(100,self.preview)

    @staticmethod
    def mesh_label(key):
        """Render a qualitative mesh label together with its exact cell count."""
        return f'{key.title()} — {cell_count(key):,} cells'

    def combo(self,parent,label,variable,values):
        ttk.Label(parent,text=label,style='Section.TLabel').pack(anchor='w',pady=(10,4))
        box=ttk.Combobox(parent,textvariable=variable,values=values,state='readonly',width=1)
        box.pack(fill='x');self.widgets.append(box);return box

    def entry(self,parent,variable):
        entry=ttk.Entry(parent,textvariable=variable,width=1);entry.pack(fill='x',pady=4);self.widgets.append(entry)

    def key(self,options,label):
        if options is METHODS and label=='All four methods (comparison)':return 'rbf'
        return next(k for k,v in options.items() if v==label)

    def refresh_options(self):
        kind=self.key(KINDS,self.kind.get());runs=available_runs(self.root,kind)
        self.run_box.configure(values=runs)
        if self.run.get() not in runs:self.run.set(runs[0] if runs else '')
        self.mesh_box.configure(state='readonly' if kind=='fresh' else 'disabled')
        self.processes_box.configure(state='readonly' if kind=='fresh' else 'disabled')
        if kind!='fresh':
            self.mesh.set(self.mesh_label('standard'));self.processes.set('1')
        self.method_box.configure(state='disabled' if kind in ('thermal','lab','lab_cfd') else 'readonly')
        if kind in ('lab','lab_cfd'):self.method.set('All four methods (comparison)')
        elif kind=='thermal' or self.method.get() not in METHODS.values():self.method.set(METHODS['rbf'])
        self.describe()

    def describe(self):
        kind=self.key(KINDS,self.kind.get())
        text={'lab':'Compare all four methods with matching field maps, held-out errors, sensor-count learning, noise sensitivity and accuracy versus time. No CFD run.',
              'lab_cfd':'Virtual sensor study using the archived converged 16 ft CFD plane. Disjoint training/test coordinates; numerical reconstruction only. No CFD run.',
              'fresh':'Fresh blockMesh, checkMesh and simpleFoam. Selected entire-set HVAC mean supplies Q. CFD comparison requires mesh, residual and flux screens.',
              'experimental':'No CFD execution. Refit the selected experimental plane and test predictions at withheld locations. 58 ft A/B layouts remain sequential.',
              'archive':'No CFD execution. Replot the recorded iteration-237 baseline at its matched 10 ft sensors. Mesh controls are unavailable.',
              'thermal':'No CFD execution or model fitting. View the archived cold-supply case and its failed convergence diagnostics.'}[kind]
        self.detail.set(text)
        if hasattr(self,'guide_view'):self.update_guide()

    def update_guide(self):
        """Explain the selection and distinguish numeric checks from physical evidence."""
        kind=self.key(KINDS,self.kind.get())
        manifest=self._last_manifest
        if manifest and (manifest['request']['kind']!=kind or manifest['request']['run_id']!=self.run.get()
                         or manifest['request']['method']!=self.key(METHODS,self.method.get())
                         or self.mesh.get()!=self.mesh_label(manifest['request']['mesh'])
                         or int(self.processes.get())!=manifest['request'].get('processes',1)):
            manifest=None
        text=guide_text(kind,self.run.get(),self.method.get(),self.mesh.get(),manifest)
        if kind=='fresh':
            text += '\n\nSOLVER EXECUTION\nSelected processes: '+self.processes.get()+'. One runs serially; larger counts use MPI domain decomposition and reconstruct the converged fields before sampling. MPI can be slower on small meshes. Process count does not establish physical accuracy.'
        self.guide_view.configure(state='normal');self.guide_view.delete('1.0','end')
        self.guide_view.insert('1.0',text)
        self.guide_view.tag_configure('heading',font=('Segoe UI',11,'bold'),foreground='#007F85')
        for index,line in enumerate(text.splitlines(),1):
            if line.isupper() and len(line)<90:
                self.guide_view.tag_add('heading',f'{index}.0',f'{index}.end')
        self.guide_view.configure(state='disabled')

    def choose_folder(self):
        path=filedialog.askdirectory(initialdir=self.folder.get(),title='Choose parent for new run folders')
        if path:self.folder.set(path)

    def command(self,args):
        python=self.python.get().strip()
        if not python:raise ValueError('Enter the scientific Python executable')
        if os.name=='nt':
            root=windows_to_wsl(self.root)
            converted=[]
            for arg in args:
                value=str(arg)
                if len(value)>2 and value[1]==':':value=windows_to_wsl(value)
                converted.append(value)
            return ['wsl.exe','-d',self.distro.get().strip(),'--exec','env',
                    'PYTHONPATH='+root+'/src','PYTHONUNBUFFERED=1',python,
                    '-u','-m','jetbridge_ml.gui.workflow',*converted]
        return [python,'-u','-m','jetbridge_ml.gui.workflow',*map(str,args)]

    def write_log(self,line):
        self.log.configure(state='normal');self.log.insert('end',line);self.log.see('end');self.log.configure(state='disabled')

    def launch(self,args,checking=False):
        command=self.command(args);self.runtime_check=checking
        env=dict(os.environ,PYTHONPATH=str(self.root/'src'),PYTHONUNBUFFERED='1')
        self.process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                      text=True,encoding='utf-8',errors='replace',cwd=self.root,env=env,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.write_log('\n'+' '.join(command)+'\n\n')
        self.run_button.configure(state='disabled')
        for widget in self.widgets:widget.configure(state='disabled')
        self.cancel_button.configure(state='disabled' if checking else 'normal')
        self.progress.start(12);self.tabs.select(0)
        def reader():
            for line in self.process.stdout:self.events.put(('line',line))
            self.events.put(('done',self.process.wait()))
        threading.Thread(target=reader,daemon=True).start()

    def check_runtime(self):
        try:
            self.status.set('Checking Python dependencies and the OpenFOAM runtime…')
            self.launch(['--root',str(self.root),'--check'],True)
        except Exception as error:self.error(error)

    def start(self):
        try:
            kind=self.key(KINDS,self.kind.get())
            mesh=next(k for k in MESHES if self.mesh.get()==self.mesh_label(k))
            spec=RunSpec(kind,self.run.get(),self.key(METHODS,self.method.get()),mesh,int(self.processes.get())).validate(self.root)
            parent=Path(self.folder.get()).expanduser().resolve()
            stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            self.output=validate_output(self.root,parent/f'{stamp}_{kind}_{spec.run_id}',fresh_cfd=kind=='fresh')
            self.figures.delete(0,'end');self.figure_paths=[];self.image=None
            self.preview_label.configure(image='',text='')
            self.summary.set('Job running. Results will appear after completion.')
            self.last_output=None;self._last_manifest=None;self.update_guide()
            descriptions={'fresh':'Live fresh isothermal CFD','archive':'Archived isothermal CFD',
                          'thermal':'Archived unconverged thermal CFD','experimental':'Reconstruction-only mode: no CFD residual history',
                          'lab':'Reconstruction Lab: no CFD solver run', 'lab_cfd':'Archived CFD virtual sensors: no new solver run'}
            self.residual_plot.watch(self.output/'residual_history.csv' if kind not in ('experimental','lab','lab_cfd') else None,descriptions[kind])
            self.status.set('Starting isolated '+KINDS[kind].lower()+'…')
            self.launch(worker_arguments(self.root,self.output,spec))
        except Exception as error:self.error(error)

    def error(self,error):
        self.status.set('Unable to start. See error message.');self.write_log(str(error)+'\n');messagebox.showerror('Jet Bridge GUI',str(error))

    def cancel(self):
        if self.process is not None and self.process.poll() is None and not self.runtime_check:
            self.output.parent.mkdir(parents=True,exist_ok=True)
            self.output.with_name(self.output.name+'.cancel').write_text('Cancel requested by desktop GUI\n')
            self.status.set('Cancellation requested. Waiting for the worker to stop safely…')
            self.cancel_button.configure(state='disabled')

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='line':
                    self.write_log(value)
                    if value.startswith('STAGE:'):self.status.set(value.strip())
                else:self.finished(value)
        except queue.Empty:pass
        self.window.after(150,self.poll)

    def finished(self,code):
        self.progress.stop();self.process=None;self.run_button.configure(state='normal')
        for widget in self.widgets:
            widget.configure(state='readonly' if isinstance(widget,ttk.Combobox) else 'normal')
        self.cancel_button.configure(state='disabled');self.refresh_options()
        if self.runtime_check:
            self.status.set('Runtime check passed. See log for OpenFOAM availability.' if code==0 else 'Runtime check failed. See log and docs/GUI.md.')
            self.runtime_check=False;return
        self.last_output=self.output
        try:
            manifest=json.loads((self.output/'manifest.json').read_text())
            self._last_manifest=manifest;self.update_guide()
            history=self.output/'residual_history.csv' if manifest['request']['kind'] not in ('experimental','lab','lab_cfd') else None
            description=manifest['status'].upper()+': '+manifest['request']['kind']+' history' if history else 'Reconstruction-only mode: no CFD residual history'
            self.residual_plot.watch(history,description)
            status=manifest['status'];lines=[status.upper()+' — '+manifest['request']['run_id'],
                   validation_message(manifest['request']['kind'],manifest)]
            if 'case_setup' in manifest:
                lines.append(f"Mesh: {manifest['case_setup']['cells']:,} cells. "
                             f"Supply: {manifest['boundary']['flow_m3s']:.6f} m³/s. "
                             f"Converged: {manifest.get('solver_converged',False)}. "
                             f"Saved iteration: {manifest.get('saved_iteration','none')}.")
            for key,label in [('experimental_reconstruction','Held-location prediction'),
                              ('cfd_sensor_metrics','CFD versus measured means')]:
                if key in manifest:
                    values=manifest[key]
                    rmse=values.get('rmse');bias=values.get('bias')
                    lines.append(label+': RMSE '+(f'{rmse:.5f}' if rmse is not None else 'unavailable')
                                 +' m/s, bias '+(f'{bias:+.5f}' if bias is not None else 'unavailable')+' m/s.')
            fit=manifest.get('experimental_reconstruction',{})
            if fit.get('negative_full_grid_predictions',0):
                lines.append(f"Reconstruction has {fit['negative_full_grid_predictions']} negative grid predictions; inspect extrapolation.")
            if 'reconstruction_lab' in manifest:
                lines.append('All-method comparison complete. Open result gallery for the interactive lab; PNG/PDF/CSV exports are saved alongside it.')
            if 'error' in manifest:lines.append('Error: '+manifest['error'])
            self.summary.set('\n'.join(lines));self.status.set(status.upper()+'. Results saved.')
            self.figure_paths=[self.output/p for p in manifest.get('figures',[])]
            self.figures.delete(0,'end')
            for path in self.figure_paths:self.figures.insert('end',path.name)
            if self.figure_paths:self.figures.selection_set(0);self.preview()
            self.tabs.select(1)
        except Exception as error:
            self.status.set(f'Worker exited ({code}). Inspect Log.');self.write_log(str(error)+'\n')

    def preview(self,event=None):
        """Fit a cached image to the actual viewport whenever the window changes."""
        self._preview_after=None
        selected=self.figures.curselection()
        if not selected:return
        width=self.preview_host.winfo_width()-12;height=self.preview_host.winfo_height()-12
        if width<12 or height<12:return
        try:
            path=self.figure_paths[selected[0]]
            try:
                from PIL import Image,ImageTk
            except ImportError:
                Image=None
            key=(path,Image is not None)
            if key!=self._preview_key:
                if Image is not None:
                    with Image.open(path) as source:self._preview_original=source.copy()
                else:self._preview_original=tk.PhotoImage(file=str(path))
                self._preview_key=key
            if Image is not None:
                original=self._preview_original
                scale=min(width/original.width,height/original.height,1)
                size=(max(1,int(original.width*scale)),max(1,int(original.height*scale)))
                self.image=ImageTk.PhotoImage(original.resize(size,Image.Resampling.LANCZOS),master=self.window)
            else:
                original=self._preview_original
                factor=max(1,math.ceil(original.width()/width),math.ceil(original.height()/height))
                self.image=original.subsample(factor,factor)
            self.preview_label.configure(image=self.image,text='')
        except (tk.TclError,OSError) as error:
            self.preview_label.configure(image='',text='Open the full-size figure: '+str(error),wraplength=max(100,width))

    def open_gallery(self):
        if self.last_output and (self.last_output/'index.html').is_file():
            target = self.last_output/('reconstruction_lab.html' if (self.last_output/'reconstruction_lab.html').is_file() else 'index.html')
            webbrowser.open(target.as_uri())

    def open_folder(self):
        if self.last_output:
            if os.name=='nt':os.startfile(str(self.last_output))
            else:subprocess.Popen(['xdg-open',str(self.last_output)])

    def open_figure(self):
        selected=self.figures.curselection()
        if selected:webbrowser.open(self.figure_paths[selected[0]].as_uri())

    def close(self):
        if self.process is not None and self.process.poll() is None:
            if self.runtime_check:
                self.status.set('Wait for the runtime check to finish before closing.');return
            self.cancel();self.status.set('Stopping this job. Close the window after cancellation completes.');return
        self.window.destroy()


def main(root=None):
    """Launch the dependency-light frontend with scientific work in another process."""
    root=Path(root) if root else Path(__file__).resolve().parents[3]
    window=tk.Tk();App(window,root);window.mainloop()


if __name__=='__main__':
    main()
