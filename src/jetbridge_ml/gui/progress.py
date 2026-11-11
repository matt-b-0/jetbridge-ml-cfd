"""A lightweight, resizable live log-residual view for the desktop GUI."""
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog,ttk
from .residuals import read_history

COLORS={'p':'#006B78','Ux':'#797979','Uy':'#9073B5','Uz':'#D66B24','k':'#2D8B57','epsilon':'#B84D73','T':'#6F56A2','p_rgh':'#006B78'}


class ResidualPlot(ttk.Frame):
    """Watch a CSV without importing scientific packages into the frontend."""
    def __init__(self,parent):
        super().__init__(parent)
        self.path=None;self.records=[];self.description='No CFD history selected'
        self.signature=None;self.timer=None
        self.columnconfigure(0,weight=1);self.rowconfigure(3,weight=1)
        self.heading=ttk.Label(self,text='Initial residuals against SIMPLE iteration',style='Section.TLabel',wraplength=500)
        self.heading.grid(row=0,column=0,sticky='ew',pady=(8,4))
        controls=ttk.Frame(self);controls.grid(row=1,column=0,sticky='ew');controls.columnconfigure(0,weight=1)
        self.selection=tk.StringVar(value='All active fields')
        self.fields=ttk.Combobox(controls,textvariable=self.selection,values=['All active fields'],state='readonly',width=1)
        self.fields.grid(row=0,column=0,sticky='ew',padx=(0,6));self.fields.bind('<<ComboboxSelected>>',lambda e:self.draw())
        ttk.Button(controls,text='Load CSV…',command=self.load_saved).grid(row=0,column=1)
        self.message=tk.StringVar(value='Start fresh CFD or load a saved residual_history.csv.')
        self.label=ttk.Label(self,textvariable=self.message,wraplength=500)
        self.label.grid(row=2,column=0,sticky='ew',pady=5)
        self.canvas=tk.Canvas(self,width=1,height=1,background='white',highlightthickness=0)
        self.canvas.grid(row=3,column=0,sticky='nsew')
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.bind('<Configure>',self.wrap)
        self.bind('<Destroy>',self.stop,add='+')
        self.timer=self.after(700,self.tick)

    def wrap(self,event):
        if event.widget is self:
            for label in (self.heading,self.label):label.configure(wraplength=max(100,event.width-12))

    def watch(self,path,description):
        """Select live or archived evidence, clearing traces from the previous job."""
        self.path=Path(path) if path else None;self.description=description
        self.signature=None;self.records=[];self.read();self.draw()

    def load_saved(self):
        path=filedialog.askopenfilename(title='Load saved residual history',filetypes=[('Residual CSV','*.csv')])
        if path:self.watch(path,'Saved history: '+Path(path).name)

    def read(self):
        if self.path is None:
            self.message.set(self.description);return
        try:
            stat=self.path.stat();signature=(stat.st_mtime_ns,stat.st_size)
        except (FileNotFoundError,PermissionError):
            self.message.set(self.description+'. Waiting for solver residuals…');return
        if signature!=self.signature:
            self.signature=signature;self.records=read_history(self.path)
            names=sorted({r['field'] for r in self.records})
            self.fields.configure(values=['All active fields',*names])
            if self.selection.get() not in ['All active fields',*names]:self.selection.set('All active fields')
            if self.records:
                latest=max(r['iteration'] for r in self.records)
                self.message.set(f'{self.description}. Latest iteration {latest:g}. Log scale; initial residuals.')
            else:self.message.set(self.description+'. No finite residual samples yet.')
            self.draw()

    def tick(self):
        self.read();self.timer=self.after(700,self.tick)

    def stop(self,event):
        if event.widget is self and self.timer is not None:
            self.after_cancel(self.timer);self.timer=None

    def draw(self):
        canvas=self.canvas;canvas.delete('all')
        width,height=canvas.winfo_width(),canvas.winfo_height()
        if width<180 or height<150:
            canvas.create_text(max(1,width//2),max(1,height//2),text='Enlarge the panel to view residuals.',width=max(60,width-12),fill='#52636C');return
        choice=self.selection.get()
        groups={}
        for r in self.records:
            if choice!='All active fields' and r['field']!=choice:continue
            groups.setdefault(r['field'],[]).append(r)
        # All-zero component equations have no log ordinate. Keep zeros in CSV.
        omitted=[field for field,rows in groups.items() if not any(r['initial_residual']>0 for r in rows)]
        groups={field:rows for field,rows in groups.items() if field not in omitted}
        positives=[r['initial_residual'] for rows in groups.values() for r in rows if r['initial_residual']>0]
        if not positives:
            canvas.create_text(width/2,height/2,text='No positive residual samples to plot.\nExact zeros remain in the CSV.',width=width-30,fill='#52636C');return
        left,right,top,bottom=65,width-18,38,height-65
        xmin=min(r['iteration'] for rows in groups.values() for r in rows)
        xmax=max(r['iteration'] for rows in groups.values() for r in rows)
        if xmax<=xmin:xmax=xmin+1
        low=math.floor(math.log10(min(positives)));high=math.ceil(math.log10(max(positives)))
        if high<=low:high=low+1
        zero=any(r['initial_residual']==0 for rows in groups.values() for r in rows)
        if zero:low-=1
        def px(x):return left+(x-xmin)/(xmax-xmin)*(right-left)
        def py(value):
            log=math.log10(value) if value>0 else low
            return bottom-(log-low)/(high-low)*(bottom-top)
        step=max(1,math.ceil((high-low)/5))
        for exponent in range(low,high+1,step):
            y=bottom-(exponent-low)/(high-low)*(bottom-top)
            canvas.create_line(left,y,right,y,fill='#E1E7EB')
            canvas.create_text(left-8,y,text=f'1e{exponent}',anchor='e',fill='#52636C',font=('Segoe UI',9))
        for i in range(5):
            value=xmin+(xmax-xmin)*i/4;x=px(value)
            canvas.create_line(x,top,x,bottom,fill='#EEF2F5')
            canvas.create_text(x,bottom+15,text=f'{value:g}',fill='#52636C',font=('Segoe UI',9))
        canvas.create_line(left,top,left,bottom,right,bottom,fill='#52636C')
        canvas.create_text((left+right)/2,height-24,text='SIMPLE iteration (not physical seconds)',fill='#173345',font=('Segoe UI',9))
        legend_x=left
        for n,(field,rows) in enumerate(sorted(groups.items())):
            color=COLORS.get(field,['#006B78','#D66B24','#2D8B57','#B84D73'][n%4])
            rows=sorted(rows,key=lambda r:r['iteration'])
            points=[coordinate for r in rows for coordinate in (px(r['iteration']),py(r['initial_residual']))]
            if len(points)>2:canvas.create_line(*points,fill=color,width=2)
            else:canvas.create_oval(points[0]-2,points[1]-2,points[0]+2,points[1]+2,fill=color,outline=color)
            canvas.create_text(legend_x,16,text=field,anchor='w',fill=color,font=('Segoe UI',9,'bold'));legend_x+=max(44,len(field)*9+14)
        if omitted or zero:
            note=('All-zero series omitted. ' if omitted else '')+('Zero points use the lower edge.' if zero else '')
            canvas.create_text(width/2,height-5,text=note,fill='#52636C',font=('Segoe UI',8))
