"""Report exports and an offline, responsive reconstruction dashboard."""
import html
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from jetbridge_ml.validation.reconstruction_lab import METHODS, LABELS, COLORS


def export_views(output, payload, held, studies, metrics):
    """Save scientific figures and a self-contained interactive HTML dashboard.

    Parameters
    ----------
    output : pathlib.Path
        Existing isolated destination.
    payload : dict
        Coordinates, full-array predictions and evidence metadata.
    held, studies, metrics : pandas.DataFrame
        Held-location predictions, sensitivity trials and common-hull metrics.
    """
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'bold', 'axes.labelcolor': '#334155',
                         'text.color': '#0f172a', 'axes.edgecolor': '#cbd5e1',
                         'figure.facecolor': '#f8fafc', 'axes.facecolor': '#ffffff'})
    def save(fig, name):
        for ext in ('png', 'pdf'):
            fig.savefig(output/f'{name}.{ext}', dpi=180, bbox_inches='tight')
        plt.close(fig)
    q=np.asarray(payload['query']); sensors=np.asarray(payload['sensors'])
    nx,ny=payload['nx'],payload['ny']; floor=payload['floor']
    data=[np.asarray(payload['fields'][m],float) for m in METHODS]
    lo=min(np.nanmin(v) for v in data); hi=max(np.nanmax(v) for v in data)
    norm=Normalize(lo,hi); hull=np.asarray(payload['inside'])
    fig,axes=plt.subplots(1,4,figsize=(13,6),layout='constrained',sharex=True,sharey=True)
    for ax,method,values in zip(axes,METHODS,data):
        image=ax.pcolormesh(q[:,0].reshape(ny,nx),(q[:,1]-floor).reshape(ny,nx),
                            values.reshape(ny,nx),cmap='viridis',norm=norm,shading='nearest')
        ax.contourf(q[:,0].reshape(ny,nx),(q[:,1]-floor).reshape(ny,nx),
                    (~hull).reshape(ny,nx),levels=[.5,1.5],colors='none',hatches=['////'])
        ax.scatter(sensors[:,0],sensors[:,1]-floor,s=20,c='white',edgecolors='#0f172a',lw=.7)
        ax.set(title=LABELS[method],xlabel='x (m)',xlim=(0,payload['width']),ylim=(0,payload['height']))
        ax.set_aspect('equal')
    axes[0].set_ylabel('Height above local floor (m)')
    fig.colorbar(image,ax=axes,label='Scalar speed (m/s)',shrink=.7)
    fig.suptitle(payload['title']+'\nSame sensors and colour scale | full-array refits; hatching = outside sensor hull')
    save(fig,'01_method_comparison')
    if 'reference' in payload:
        reference=np.asarray(payload['reference'])
        fig,axes=plt.subplots(1,5,figsize=(15,5.5),layout='constrained',sharey=True)
        ref=axes[0].pcolormesh(q[:,0].reshape(ny,nx),(q[:,1]-floor).reshape(ny,nx),
                               reference.reshape(ny,nx),cmap='viridis',shading='nearest')
        axes[0].set_title('Archived CFD reference')
        fig.colorbar(ref,ax=axes[0],label='Speed (m/s)',shrink=.65)
        bound=max(np.nanmax(np.abs(v-reference)) for v in data)
        for ax,m,v in zip(axes[1:],METHODS,data):
            image=ax.pcolormesh(q[:,0].reshape(ny,nx),(q[:,1]-floor).reshape(ny,nx),
                                (v-reference).reshape(ny,nx),cmap='RdBu_r',vmin=-bound,vmax=bound,shading='nearest')
            ax.set_title(LABELS[m]+' − CFD')
        fig.colorbar(image,ax=list(axes[1:]),label='Signed difference (m/s)',shrink=.65)
        for ax in axes:ax.set_aspect('equal');ax.set_xlabel('x (m)')
        axes[0].set_ylabel('Height above floor (m)')
        fig.suptitle('Where does sparse reconstruction lose the numerical field?\nFull display includes extrapolation; common-support scores use disjoint test points only')
        save(fig,'01b_virtual_field_errors')
    common=held[held.inside_hull & held.method.isin(METHODS)]
    fig,axes=plt.subplots(1,4,figsize=(13,4),layout='constrained')
    limit=[min(common.speed_mps.min(),common.prediction_mps.min()),
           max(common.speed_mps.max(),common.prediction_mps.max())]
    margin=max(.005,(limit[1]-limit[0])*.1);limit=[limit[0]-margin,limit[1]+margin]
    for ax,m in zip(axes,METHODS):
        part=common[common.method==m]
        ax.plot(limit,limit,'--',color='#94a3b8',lw=1)
        ax.scatter(part.speed_mps,part.prediction_mps,c=COLORS[m],s=35,alpha=.8)
        metric=metrics[metrics.method==m].iloc[0]
        ax.set(xlim=limit,ylim=limit,xlabel='Held-out reference (m/s)',
               title=f'{LABELS[m]}\nRMSE {metric.rmse:.4f} m/s')
        ax.set_aspect('equal');ax.grid(alpha=.15)
    axes[0].set_ylabel('Prediction (m/s)')
    fig.suptitle('Predict locations the model did not see\nCommon supported locations; separate from the full-array maps')
    save(fig,'02_heldout_predictions')
    fig,ax=plt.subplots(figsize=(11,4.5),layout='constrained')
    for i,m in enumerate(METHODS):
        part=held[held.method==m].sort_values('source_row')
        ax.scatter(part.source_row+(i-1.5)*.12,part.prediction_mps-part.speed_mps,
                   c=COLORS[m],label=LABELS[m],s=32,
                   marker=['o','s','^','D'][i])
    ax.axhline(0,c='#94a3b8',lw=1);ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,1.2))
    ax.set(xlabel='Source sensor row / virtual test index (zero based)',ylabel='Prediction − reference (m/s)',
           title='Local error reveals where the reconstruction misses')
    save(fig,'02b_local_errors')
    clean=studies[studies.noise_fraction==0]
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for m in METHODS:
        g=clean[clean.method==m].groupby('sensor_count').rmse
        mean=g.mean();low=g.min();high=g.max()
        ax.plot(mean.index,mean.values,'o-',color=COLORS[m],label=LABELS[m],lw=2)
        ax.fill_between(mean.index,low.values,high.values,color=COLORS[m],alpha=.12)
    ax.set(xlabel='Retained training sensors',ylabel='Common-support held-out RMSE (m/s)',
           title='How much information do more sensors add?\nThree nested layouts; fixed hull anchors and fixed held-out targets')
    ax.legend(ncol=2);ax.grid(alpha=.15);save(fig,'03_sensor_learning')
    noisy=studies[studies.sensor_count==studies.sensor_count.max()]
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for m in METHODS:
        g=noisy[noisy.method==m].groupby('noise_fraction').rmse
        a=g.mean();ax.plot(a.index*100,a.values,'o-',color=COLORS[m],label=LABELS[m],lw=2)
        ax.fill_between(a.index*100,g.min().values,g.max().values,color=COLORS[m],alpha=.12)
    ax.set(xlabel='Gaussian noise σ / retained-speed RMS (%)',ylabel='Common-support held-out RMSE (m/s)',
           title='How robust is the fit to noisy inputs?\nTraining targets perturbed; held-out references unchanged; bands = trial range')
    ax.legend(ncol=2);ax.grid(alpha=.15);save(fig,'04_noise_sensitivity')
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    timing=payload['timing']
    for m in METHODS:
        point=metrics[metrics.method==m].iloc[0]
        seconds=np.median([row['seconds'] for row in timing if row['method']==m])
        ax.scatter(seconds*1000,point.rmse,c=COLORS[m],s=130,edgecolors='white',lw=1.5)
        ax.annotate(LABELS[m],(seconds*1000,point.rmse),xytext=(9,6),textcoords='offset points',color=COLORS[m])
    ax.set(xscale='log',xlabel=f'Median full fit + {len(q):,} grid predictions (ms; log scale)',
           ylabel='Common-support held-location RMSE (m/s)',
           title='Is the extra fitting cost worthwhile?\nSVR includes training-only search; accuracy comes from separate held-out fits')
    ax.margins(x=.3,y=.25);ax.grid(alpha=.15);save(fig,'05_accuracy_cost')
    payload['metrics']=metrics.replace({np.nan:None}).to_dict('records')
    payload['studies']=studies.to_dict('records')
    (output/'dashboard_data.json').write_text(json.dumps(payload,allow_nan=False))
    template=HTML.replace('__TITLE__',html.escape(payload['title']))
    # Escape script delimiters even though IDs and values are controlled inputs.
    encoded=json.dumps(payload,allow_nan=False).replace('<','\\u003c')
    (output/'reconstruction_lab.html').write_text(template.replace('__PAYLOAD__',encoded),encoding='utf-8')


HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reconstruction Lab · __TITLE__</title><style>
:root{--ink:#12263a;--muted:#526577;--line:#dae4ea;--teal:#0d9488}*{box-sizing:border-box}body{margin:0;background:#eef3f7;color:var(--ink);font:15px/1.55 system-ui,Segoe UI,sans-serif}header{background:#102b3c;color:white;padding:34px max(24px,calc((100vw - 1280px)/2));border-bottom:5px solid #30c4ad}header small{letter-spacing:.15em;color:#69dbc9;font-weight:700}h1{font-size:clamp(28px,4vw,44px);line-height:1.1;margin:12px 0}header p{color:#c4d4de;max-width:800px;margin-bottom:4px}main{max-width:1328px;margin:auto;padding:24px}button,select{font:inherit}button{cursor:pointer}nav{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}nav button{border:1px solid var(--line);border-radius:30px;padding:10px 17px;background:white;color:var(--muted);font-weight:600}nav button[aria-selected=true]{background:var(--ink);color:white;border-color:var(--ink)}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card,.panel{background:white;border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 4px 20px #18354d06}.card strong{display:block;font-size:25px;line-height:1.4}.card small{color:var(--muted)}.card .name{font-size:12px;font-weight:750;text-transform:uppercase;letter-spacing:.05em}.panel{margin:15px 0}.panel h2{font-size:23px;margin:0 0 6px}.panel p{color:var(--muted);margin:5px 0 16px}.pill{font-size:12px;border-radius:8px;padding:5px 10px;display:inline-block;background:#e1f6f0;color:#126653;font-weight:700}.tools{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:15px 0}.tools label{display:flex;align-items:center;gap:6px}.maps{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}.map{min-width:0;border:1px solid var(--line);border-radius:12px;overflow:hidden}.map h3{font-size:15px;margin:12px 14px 2px}.map small{display:block;margin:0 14px 8px;color:var(--muted)}canvas{width:100%;display:block;aspect-ratio:1/1.65}.legend{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--muted);margin-top:12px}.ramp{height:12px;width:170px;border-radius:5px;background:linear-gradient(90deg,#440154,#3b528b,#21918c,#5ec962,#fde725)}.readout{background:#edf6f5;padding:10px 14px;border-radius:9px;min-height:43px;font-variant-numeric:tabular-nums}.note{border-left:3px solid #d8972a;background:#fff9ed;padding:13px 17px;color:#6d522a;border-radius:0 8px 8px 0;margin-top:18px}.figure{width:100%;height:auto;display:block;border-radius:8px}.downloads{display:flex;gap:14px;flex-wrap:wrap;margin-top:12px}a{color:#0a766c;text-underline-offset:3px}.chartview[hidden]{display:none}.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}.explain{display:grid;grid-template-columns:1fr 1fr;gap:18px}.explain h3{margin-bottom:5px}.explain p{font-size:14px}footer{font-size:13px;color:var(--muted);padding:20px 0 35px}.status{margin-top:15px;display:flex;gap:8px;flex-wrap:wrap}.muted{color:var(--muted)}@media(max-width:900px){.maps{grid-template-columns:repeat(2,1fr)}.cards{grid-template-columns:repeat(2,1fr)}}@media(max-width:550px){main{padding:14px}.panel{padding:15px}.maps,.explain{grid-template-columns:1fr}.cards{gap:8px}.card{padding:13px}.card strong{font-size:21px}header{padding:26px 20px}nav button{font-size:13px;padding:9px 12px}}@media print{header{color:#102b3c;background:white}nav,.tools{display:none}.chartview[hidden]{display:block}.panel{break-inside:avoid}.maps{grid-template-columns:repeat(4,1fr)}}
</style></head><body><header><small>MMA3001 / INTERPOLATION + MACHINE LEARNING</small><h1>From sparse sensors<br>to an airflow picture.</h1><p>Compare what the methods reconstruct, what they predict at unseen locations, and what happens when measurements become fewer or noisier.</p><div class="status"><span class="pill" id="source"></span><span class="pill">SI units · scalar air speed</span><span class="pill">Offline · reproducible</span></div></header><main>
<div class="cards" id="cards"></div><nav role="tablist" aria-label="Study views">
<button role="tab" aria-selected="true" data-view="maps">01 · Compare fields</button><button role="tab" aria-selected="false" data-view="held">02 · Unseen sensors</button><button role="tab" aria-selected="false" data-view="density">03 · Sensor count</button><button role="tab" aria-selected="false" data-view="noise">04 · Input noise</button><button role="tab" aria-selected="false" data-view="cost">05 · Accuracy & cost</button></nav>
<section class="chartview" id="maps"><div class="panel"><h2>Same observations. Four different answers.</h2><p>The maps use identical inputs, coordinates and a shared colour scale. Toggle overlays and hover to inspect a fitted value. These full-array maps are illustrations, not held-out prediction tests.</p>
<div class="tools"><label><input id="sensors" type="checkbox" checked>Sensor locations</label><label><input id="support" type="checkbox" checked>Mark extrapolation</label><label>Focus <select id="focus"><option value="all">All four methods</option><option value="nearest">Nearest</option><option value="linear">Linear</option><option value="rbf">Thin-plate RBF</option><option value="svr">SVR</option></select></label></div>
<div class="maps" id="mapgrid"></div><div class="legend"><span id="low"></span><span class="ramp"></span><span id="high"></span><span>m/s · grey = no linear prediction · diagonal marks = outside hull</span></div><p class="muted">Horizontal axis: x (m) · Vertical axis: height above the local sloped floor (m)</p><div class="readout" id="readout" aria-live="polite">Hover over a map to inspect a grid value.</div><div class="downloads"><a href="01_method_comparison.png">Report PNG</a><a href="01_method_comparison.pdf">Vector PDF</a><a href="lab_fields.csv">Field values CSV</a></div><div class="note">A smooth map does not establish physical accuracy. Negative predictions are retained and counted; unsupported extrapolation is shown explicitly.</div></div></section>
<section class="chartview" id="held" hidden><div class="panel"><h2>Can the method predict a location it never saw?</h2><p id="heldtext"></p><img class="figure" src="02_heldout_predictions.png" alt="Four parity plots of held-out prediction against reference speed"><div class="downloads"><a href="02_heldout_predictions.pdf">Parity PDF</a><a href="lab_heldout_predictions.csv">Predictions CSV</a><a href="lab_metrics.csv">Metrics CSV</a></div><div class="tablewrap"><table><thead><tr><th>Method</th><th>RMSE (m/s)</th><th>MAE (m/s)</th><th>Common targets</th><th>Full-map negatives</th></tr></thead><tbody id="metrics"></tbody></table></div><img class="figure" src="02b_local_errors.png" alt="Signed errors by held-out sensor row"><div class="note">These metrics use common supported locations. Outside-hull performance and coverage are separate in the CSVs. No displayed uncertainty interval is claimed for the instrument.</div></div></section>
<section class="chartview" id="density" hidden><div class="panel"><h2>When do extra sensors stop helping?</h2><p>Each curve uses the same fixed held-out targets and nested training subsets. Hull vertices are deliberately retained so the supported region stays fixed. Shading spans three deterministic layouts; it is not a confidence interval.</p><img class="figure" src="03_sensor_learning.png" alt="Held-out RMSE versus retained sensor count"><div class="downloads"><a href="03_sensor_learning.pdf">Vector PDF</a><a href="lab_sensitivity.csv">All trials CSV</a><a href="lab_split_audit.json">Exact designs</a></div><div class="note">This is a controlled, coverage-preserving design experiment, not a universal minimum-sensor recommendation. With few experimental sensors, the attainable counts and independent test set are small.</div></div></section>
<section class="chartview" id="noise" hidden><div class="panel"><h2>Does the fit chase measurement noise?</h2><p>Independent zero-mean Gaussian noise is added only to retained training speeds, with σ equal to 0, 2, 5 or 10% of their RMS. Held-out references stay unchanged. Each method receives the same perturbation; SVR is reselected using noisy training data only.</p><img class="figure" src="04_noise_sensitivity.png" alt="Held-out error versus synthetic training noise"><div class="downloads"><a href="04_noise_sensitivity.pdf">Vector PDF</a><a href="lab_sensitivity.csv">Trial values CSV</a></div><div class="note">A synthetic noise scenario is not the measured SWEMA uncertainty. Bands show trial range, not experimental uncertainty or statistical confidence.</div></div></section>
<section class="chartview" id="cost" hidden><div class="panel"><h2>More complexity should earn its place.</h2><p>Lower is more accurate; farther left is faster. Timings are the median of three full-data fit + display-grid prediction calls. SVR includes its training-only hyperparameter search. Error comes from separate held-out fits, so the timing and accuracy measurements have different purposes.</p><img class="figure" src="05_accuracy_cost.png" alt="Held-out RMSE against fitting and grid-prediction runtime on a logarithmic time axis"><div class="downloads"><a href="05_accuracy_cost.pdf">Vector PDF</a><a href="lab_timing.csv">Raw timings CSV</a></div><div class="note">Timing is machine-specific and excludes plotting, CFD and data loading. SVR uses optimisation iterations, not neural-network epochs.</div></div></section>
<div class="panel explain"><div><h3>What makes this a fair comparison?</h3><p>Methods share input locations, target units and evaluation locations. Coordinates are standardised using training data only. SVR selection stays inside each training split. Replicates are never pooled into a simultaneous field.</p></div><div><h3>Where does CFD fit?</h3><p>CFD supplies a controlled numerical reference for virtual sensors. Experimental tests assess withheld measured means. Agreement with a CFD field cannot certify the physical ventilation model.</p></div></div><footer id="foot"></footer></main>
<script>const D=__PAYLOAD__;
const methods=['nearest','linear','rbf','svr'],names={nearest:'Nearest',linear:'Linear',rbf:'Thin-plate RBF',svr:'SVR'},colors={nearest:'#64748b',linear:'#0284c7',rbf:'#0d9488',svr:'#8b5cf6'};
document.querySelector('#source').textContent=D.lineage;document.querySelector('#heldtext').textContent=D.evaluation;
document.querySelector('#foot').textContent=D.title+' · '+D.protocol+' · Physical validation remains unestablished. Download manifest.json and lab_search_audit.json for provenance and selection records.';
const best=[...D.metrics].filter(m=>m.rmse!==null).sort((a,b)=>a.rmse-b.rmse)[0];
const info=[['INPUTS',D.sensors.length+' sensors',D.reference?'One numerical reference plane':'One replicate / planar layout'],['SUPPORTED TEST',D.metrics[0].n_requested+' locations','Shared across methods'],['LOWEST HELD-OUT RMSE',best.rmse.toFixed(4)+' m/s',names[best.method]+' · descriptive comparison'],['STUDY DESIGN','3 repeats','Fixed held-out targets; nested counts']];
document.querySelector('#cards').innerHTML=info.map(c=>`<div class="card"><div class="name">${c[0]}</div><strong>${c[1]}</strong><small>${c[2]}</small></div>`).join('');
document.querySelector('#metrics').innerHTML=D.metrics.map(m=>`<tr><td style="color:${colors[m.method]};font-weight:700">${names[m.method]}</td><td>${m.rmse===null?'—':m.rmse.toFixed(5)}</td><td>${m.mae===null?'—':m.mae.toFixed(5)}</td><td>${m.n_predicted} / ${m.n_requested}</td><td>${D.fields[m.method].filter(v=>v!==null&&v<0).length}</td></tr>`).join('');
const vals=methods.flatMap(m=>D.fields[m].filter(v=>v!==null));const lo=Math.min(...vals),hi=Math.max(...vals);
document.querySelector('#low').textContent=lo.toFixed(3);document.querySelector('#high').textContent=hi.toFixed(3);
const stops=[[68,1,84],[59,82,139],[33,145,140],[94,201,98],[253,231,37]];
function color(v){if(v===null)return '#e2e8f0';const t=Math.max(0,Math.min(1,(v-lo)/(hi-lo||1)))*4,i=Math.min(3,Math.floor(t)),a=t-i;return `rgb(${stops[i].map((c,j)=>Math.round(c+(stops[i+1][j]-c)*a)).join(',')})`;}
const grid=document.querySelector('#mapgrid');
if(D.reference){const p=document.createElement('div');p.className='panel';p.innerHTML='<h2>Inspect the numerical reconstruction error</h2><p>Archived CFD reference and signed method-minus-CFD maps. Display includes extrapolation; this is not experimental validation.</p><img class="figure" src="01b_virtual_field_errors.png" alt="Archived CFD reference and four signed reconstruction error maps"><div class="downloads"><a href="01b_virtual_field_errors.pdf">Vector PDF</a></div>';document.querySelector('#maps').appendChild(p);}
methods.forEach(m=>{const card=document.createElement('div');card.className='map';card.dataset.method=m;card.innerHTML=`<h3 style="color:${colors[m]}">${names[m]}</h3><small>Full-array refit · scalar speed</small><canvas tabindex="0" aria-label="${names[m]} reconstructed field"></canvas>`;grid.appendChild(card);const c=card.querySelector('canvas');c.width=380;c.height=Math.round(380*D.height/D.width);c.style.aspectRatio=D.width+'/'+D.height;
c.addEventListener('mousemove',e=>{const r=c.getBoundingClientRect(),col=Math.floor((e.clientX-r.left)/r.width*D.nx),row=D.ny-1-Math.floor((e.clientY-r.top)/r.height*D.ny);if(col<0||col>=D.nx||row<0||row>=D.ny)return;const i=row*D.nx+col,v=D.fields[m][i];document.querySelector('#readout').textContent=`${names[m]} · x ${D.query[i][0].toFixed(3)} m · height ${(D.query[i][1]-D.floor).toFixed(3)} m · ${v===null?'No supported prediction':v.toFixed(5)+' m/s'} · ${D.inside[i]?'Inside sensor hull':'EXTRAPOLATION region'}`;});});
function draw(){const one=document.querySelector('#focus').value!=='all';grid.style.gridTemplateColumns=one?'minmax(240px,420px)':'';grid.style.justifyContent=one?'center':'';document.querySelectorAll('.map').forEach(card=>{const m=card.dataset.method,c=card.querySelector('canvas'),ctx=c.getContext('2d'),w=c.width,h=c.height;card.hidden=document.querySelector('#focus').value!=='all'&&document.querySelector('#focus').value!==m;
for(let row=0;row<D.ny;row++)for(let col=0;col<D.nx;col++){const i=row*D.nx+col,x=col*w/D.nx,y=(D.ny-1-row)*h/D.ny,cw=w/D.nx,ch=h/D.ny;ctx.fillStyle=color(D.fields[m][i]);ctx.fillRect(x,y,cw+1,ch+1);if(!D.inside[i]&&document.querySelector('#support').checked){ctx.strokeStyle='#1e293b77';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,y+ch);ctx.lineTo(x+cw,y);ctx.stroke();}}
if(document.querySelector('#sensors').checked)D.sensors.forEach(s=>{ctx.beginPath();ctx.arc(s[0]/D.width*w,h-(s[1]-D.floor)/D.height*h,4.7,0,Math.PI*2);ctx.fillStyle='white';ctx.fill();ctx.strokeStyle='#102b3c';ctx.lineWidth=1.4;ctx.stroke();});});}
['sensors','support','focus'].forEach(id=>document.getElementById(id).addEventListener('change',draw));draw();
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('nav button').forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('.chartview').forEach(s=>s.hidden=s.id!==b.dataset.view);}));
</script></body></html>'''
