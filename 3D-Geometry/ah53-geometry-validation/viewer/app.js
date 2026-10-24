import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = id => document.getElementById(id);
const state = { catalog: [], model: null, mesh: null, sections: null, meshTicket: 0, sectionTicket: 0, direction: 'oblique', initial: true, busy: 0 };
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(0x0a1422);
$('webgl').appendChild(renderer.domElement);
const world = new THREE.Scene(), modelGroup = new THREE.Group(), overlayGroup = new THREE.Group();
world.add(modelGroup, overlayGroup);
world.add(new THREE.HemisphereLight(0xe7faff, 0x2c3b4d, 2.2));
const sun = new THREE.DirectionalLight(0xf3f9ff, 2.5); sun.position.set(5000, 10000, 6000); world.add(sun);
const fill = new THREE.DirectionalLight(0x4b9fa2, 1.4); fill.position.set(-10000, 6000, -3000); world.add(fill);
let camera = new THREE.PerspectiveCamera(40, 1, .01, 1000000);
let controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
let substrate, axes, grid;
const tick = () => { requestAnimationFrame(tick); controls.update();const distance=camera.position.distanceTo(controls.target);camera.near=Math.max(.01,distance/100);camera.far=Math.max(10000,distance*20);camera.updateProjectionMatrix();renderer.render(world, camera); }; tick();
const status = (msg, error=false) => { $('status').textContent=msg; $('status').className=error?'failure':state.busy?'busy':''; };
function fail(error) { console.error(error); $('error').hidden=false; $('error').textContent=error.message; status(`加载失败：${error.message}`, true); }
async function api(path, options) { const response=await fetch(path,options); if(!response.ok){let text=await response.text();throw new Error(text.slice(0,600));} return response.json(); }
function query() { return new URLSearchParams({model:$('model').value, scope:$('scope').value,z:$('zcut').value,y:$('ycut').value,overlay:$('overlay').checked?'1':'0'}); }
function dispose(group) { for(const o of [...group.children]){group.remove(o);o.traverse(x=>{x.geometry?.dispose();if(x.material)Array.isArray(x.material)?x.material.forEach(m=>m.dispose()):x.material.dispose();});} }
function resize(){const r=$('webgl').getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;if(camera.isOrthographicCamera){const h=camera.top-camera.bottom;camera.left=-h*camera.aspect/2;camera.right=h*camera.aspect/2;}camera.updateProjectionMatrix();drawSections();}
new ResizeObserver(resize).observe($('webgl'));
new ResizeObserver(drawSections).observe($('xyplot'));
function fitCamera(direction=state.direction) {
 if(!state.mesh)return;state.direction=direction;
 const b=state.mesh.view_bounds,g=Number($('gain').value), center=new THREE.Vector3((b[0]+b[1])/2,(b[2]+b[3])*g/2,(b[4]+b[5])/2),sx=b[1]-b[0],sy=(b[3]-b[2])*g,sz=b[5]-b[4];
 const extent=direction==='xy'?Math.max(sx,sy*camera.aspect):direction==='top'?Math.max(sx,sz*camera.aspect):direction==='side'?Math.max(sz,sy*camera.aspect):Math.max(sx,sz,sy);
 const dist=Math.max(extent,20)*1.65;
 const vector={oblique:[.6,.9,1.1],xy:[0,0,1],top:[0,1,0],side:[1,0,0]}[direction];
 camera.up.set(0,1,0);if(direction==='top')camera.up.set(0,0,-1);
 camera.position.copy(center).add(new THREE.Vector3(...vector).normalize().multiplyScalar(dist));controls.target.copy(center);
 if(camera.isOrthographicCamera){const h=Math.max(direction==='top'?sz:sy,extent/camera.aspect,30)*1.3;camera.top=h/2;camera.bottom=-h/2;camera.left=-h*camera.aspect/2;camera.right=h*camera.aspect/2;camera.zoom=1;}
 camera.near=.01;camera.far=Math.max(1000000,dist*15);camera.updateProjectionMatrix();controls.update();
}
function switchProjection(){const previous=camera,pos=previous.position.clone(),target=controls.target.clone(),aspect=previous.aspect;
 camera=$('projection').value==='orthographic'?new THREE.OrthographicCamera(-1000*aspect,1000*aspect,1000,-1000,.01,1000000):new THREE.PerspectiveCamera(40,aspect,.01,1000000);
 camera.position.copy(pos);camera.up.copy(previous.up);
 if(camera.isOrthographicCamera){const h=2*pos.distanceTo(target)*Math.tan(20*Math.PI/180);camera.top=h/2;camera.bottom=-h/2;camera.left=-h*aspect/2;camera.right=h*aspect/2;camera.aspect=aspect;}
 else if(previous.isOrthographicCamera){const h=(previous.top-previous.bottom)/previous.zoom;camera.position.copy(target).add(pos.clone().sub(target).normalize().multiplyScalar(h/(2*Math.tan(20*Math.PI/180))));}
 controls.dispose();controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.target.copy(target);camera.updateProjectionMatrix();controls.update();
}
function makeMesh(data){dispose(modelGroup);const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(data.vertices,3));geometry.setIndex(data.faces);geometry.computeVertexNormals();
 const color=new THREE.Color(), colors=[];for(let i=1;i<data.vertices.length;i+=3){const t=THREE.MathUtils.clamp(data.vertices[i]/340,0,1);color.setHSL(.50-t*.09,.48,.30+t*.25);colors.push(color.r,color.g,color.b);}geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
 const material=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.78,metalness:.12,side:THREE.DoubleSide,flatShading:$('flat').checked,wireframe:$('wireframe').checked});modelGroup.add(new THREE.Mesh(geometry,material));
 const b=data.view_bounds,thick=Math.max(20,Math.min(80,(b[1]-b[0])/100));const sg=new THREE.BoxGeometry(b[1]-b[0],thick,b[5]-b[4]);substrate=new THREE.Mesh(sg,new THREE.MeshStandardMaterial({color:0x465769,roughness:.9,transparent:true,opacity:.7,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));substrate.position.set((b[0]+b[1])/2,-thick/2,(b[4]+b[5])/2);substrate.visible=$('substrate').checked;modelGroup.add(substrate);
 modelGroup.scale.y=Number($('gain').value);
 dispose(overlayGroup);const size=Math.max(b[1]-b[0],b[5]-b[4]);axes=new THREE.AxesHelper(size*.15);axes.position.set(b[0],0,b[4]);overlayGroup.add(axes);
 const n=data.faces.length/3; $('mesh-label').textContent=`${data.display_label} · ${n.toLocaleString()} 个显示面片`;
 $('source-label').textContent=`${data.metadata.model_id} · ${data.metadata.source_model||'独立参考输入'}`;
 $('metadata').textContent=JSON.stringify({...data.metadata,display:data.display},null,2);
 $('error').hidden=true;
}
async function loadMesh(reset=false){const ticket=++state.meshTicket;state.busy++;status('正在读取已保存模型并生成显示数据…');const start=performance.now();
 try{const data=await api(`/api/mesh?${query()}`);if(ticket!==state.meshTicket)return;state.mesh=data;makeMesh(data);if(reset||state.initial){fitCamera();state.initial=false;}status(`${data.display_label}；加载 ${(performance.now()-start).toFixed(0)} ms。${data.display.note}`);}
 catch(e){if(ticket===state.meshTicket)fail(e);}finally{state.busy--;if(!state.busy)$('status').classList.remove('busy');}
}
async function loadSections(){if(!$('model').value)return;const ticket=++state.sectionTicket;
 try{const data=await api(`/api/sections?${query()}`);if(ticket!==state.sectionTicket)return;state.sections=data;drawSections();$('xy-title').textContent=`Z = ${(data.z/1000).toFixed(3)} µm`;$('xz-title').textContent=`Y = ${data.y.toFixed(1)} nm`;$('section-note').textContent=data.note;}
 catch(e){if(ticket===state.sectionTicket)fail(e);}
}
let debounce;
function cutsChanged(source){const z=source==='znumber'?Number($('znumber').value):Number($('zcut').value),y=source==='ynumber'?Number($('ynumber').value):Number($('ycut').value);$('zcut').value=z;$('znumber').value=$('zcut').value;$('ycut').value=y;$('ynumber').value=$('ycut').value;$('zvalue').textContent=`${(Number($('zcut').value)/1000).toFixed(3)} µm`;$('yvalue').textContent=`${Number($('ycut').value).toFixed(1)} nm`;clearTimeout(debounce);debounce=setTimeout(()=>{loadSections();if($('scope').value==='shoulder')loadMesh(false);},180);}
function drawPlot(canvas, series, bounds, xlabel, ylabel, filled=false){if(!canvas||!bounds)return;const rect=canvas.getBoundingClientRect();if(rect.width<2||rect.height<2)return;const dpi=Math.min(devicePixelRatio,2);canvas.width=rect.width*dpi;canvas.height=rect.height*dpi;const ctx=canvas.getContext('2d');ctx.scale(dpi,dpi);const w=rect.width,h=rect.height,L=45,R=12,T=9,B=28,pw=w-L-R,ph=h-T-B;ctx.clearRect(0,0,w,h);ctx.font='9px Segoe UI,Microsoft YaHei';
 const project=p=>[L+(p[0]-bounds[0])/(bounds[1]-bounds[0])*pw,T+ph-(p[1]-bounds[2])/(bounds[3]-bounds[2])*ph];
 ctx.lineWidth=1;ctx.strokeStyle='#243c50';ctx.fillStyle='#809db6';ctx.textAlign='center';
 for(let i=0;i<=4;i++){const x=L+i*pw/4,val=bounds[0]+i*(bounds[1]-bounds[0])/4;ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,T+ph);ctx.stroke();ctx.fillText(Math.abs(val)>=1000?(val/1000).toFixed(2)+'k':val.toFixed(0),x,T+ph+13);const y=T+ph-i*ph/4,v=bounds[2]+i*(bounds[3]-bounds[2])/4;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(L+pw,y);ctx.stroke();ctx.textAlign='right';ctx.fillText(Math.abs(v)>=1000?(v/1000).toFixed(2)+'k':v.toFixed(0),L-5,y+3);ctx.textAlign='center';}
 ctx.fillStyle='#9db5ca';ctx.fillText(xlabel,L+pw/2,h-2);ctx.save();ctx.translate(10,T+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText(ylabel,0,0);ctx.restore();ctx.save();ctx.beginPath();ctx.rect(L,T,pw,ph);ctx.clip();if(canvas.id==='xyplot'&&bounds[2]<0&&$('substrate').checked){const y0=project([bounds[0],0])[1];ctx.fillStyle='#52677966';ctx.fillRect(L,y0,pw,T+ph-y0);}
 const styles={current:['#58e4cc',[]],reference:['#f4c36a',[5,3]],direct:['#87b9ff',[2,3]],derived:['#db92ea',[7,2,1,2]]};
 for(const s of series||[]){const [color,dash]=styles[s.role]||styles.current;ctx.strokeStyle=color;ctx.lineWidth=s.role==='current'?1.8:1.2;ctx.setLineDash(dash);for(const line of s.lines||[]){ctx.beginPath();let started=false;for(const p of line){if(p===null||p[0]===null||p[1]===null){started=false;continue;}const [x,y]=project(p);if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);}if(filled&&s.role==='current'){ctx.fillStyle='#36baa52a';ctx.fill();}ctx.stroke();}}
 ctx.restore();ctx.setLineDash([]);
}
function drawSections(){if(!state.sections)return;const d=state.sections;drawPlot($('xyplot'),d.xy,d.xy_bounds,'X / nm','Y / nm',true);drawPlot($('xzplot'),d.xz,d.xz_bounds,'X / nm','Z / nm',true);}
function filteredModels(){const scene=$('scene').value,experiment=$('experiment').value,isConversion=/^B[1-4]$/.test(experiment);return state.catalog.filter(m=>m.scene===scene&&(!isConversion||m.density!=='coarse')&&(experiment==='all'||m.routes.includes(experiment)||m.kind==='reference'));}
function populateModels(preferred){let items=filteredModels();if(!items.length){$('experiment').value='all';items=filteredModels();}const old=state.catalog.find(m=>m.id===(preferred||$('model').value));$('model').replaceChildren(...items.map(m=>new Option(m.label,m.id)));const match=items.find(m=>m.id===preferred)||items.find(m=>old&&m.family===old.family&&m.density===old.density)||items.find(m=>m.kind==='parametric')||items.find(m=>m.kind!=='reference')||items[0];if(match)$('model').value=match.id;updateLimits();}
function updateLimits(){state.model=state.catalog.find(m=>m.id===$('model').value);if(!state.model)return;const b=state.model.bounds;$('zcut').min=b[4];$('zcut').max=b[5];$('znumber').min=b[4];$('znumber').max=b[5];$('ycut').max=b[3];$('ynumber').max=b[3];cutsChanged();}
async function saveImage(){if(!state.mesh)return;$('save').disabled=true;try{renderer.render(world,camera);const w=1280,h=940,c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d');ctx.fillStyle='#0d1926';ctx.fillRect(0,0,w,h);ctx.fillStyle='#d5e7ee';ctx.font='22px Microsoft YaHei, sans-serif';ctx.fillText('AH53 · 基于名义版图的合成工艺形貌',24,37);ctx.font='14px Microsoft YaHei, sans-serif';ctx.fillText(`${$('model').selectedOptions[0].text} | ${$('scope').selectedOptions[0].text} | Y ×${$('gain').value} | ${$('projection').selectedOptions[0].text}`,24,66);const gl=renderer.domElement;const imageScale=Math.min((w-40)/gl.width,550/gl.height),imageWidth=gl.width*imageScale,imageHeight=gl.height*imageScale;ctx.drawImage(gl,20+((w-40)-imageWidth)/2,82+(550-imageHeight)/2,imageWidth,imageHeight);ctx.drawImage($('xyplot'),20,645,610,215);ctx.drawImage($('xzplot'),650,645,610,215);ctx.fillStyle='#b2c9db';ctx.fillText(`XY: Z=${$('zcut').value} nm；XZ: Y=${$('ycut').value} nm。${state.mesh.display_label}`,24,885);ctx.font='11px Microsoft YaHei, sans-serif';ctx.fillText(state.model.id+' | '+new Date().toISOString(),24,912);const metadata={model:state.model.id,range:$('scope').value,height_gain:Number($('gain').value),projection:$('projection').value,z_nm:Number($('zcut').value),y_nm:Number($('ycut').value),camera:{position:camera.position.toArray(),target:controls.target.toArray()},display:state.mesh.display,source:state.mesh.metadata};const result=await api('/api/screenshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({png:c.toDataURL('image/png'),metadata})});status(`截图与来源信息已保存：${result.file}`);const a=document.createElement('a');a.href=c.toDataURL('image/png');a.download=result.name;a.click();}catch(e){fail(e);}finally{$('save').disabled=false;}}
for(const id of ['oblique','top','xy','side'])$(id).onclick=()=>fitCamera(id);
$('reset').onclick=()=>fitCamera();$('projection').onchange=switchProjection;$('save').onclick=saveImage;
$('gain').onchange=()=>{modelGroup.scale.y=Number($('gain').value);$('scale-label').textContent=`Y ×${$('gain').value} · ${$('gain').value==='1'?'真实比例':'高度放大，非真实比例'}`;fitCamera();};
$('wireframe').onchange=()=>modelGroup.children[0]&&(modelGroup.children[0].material.wireframe=$('wireframe').checked);
$('flat').onchange=()=>{if(modelGroup.children[0]){modelGroup.children[0].material.flatShading=$('flat').checked;modelGroup.children[0].material.needsUpdate=true;}};
$('substrate').onchange=()=>{if(substrate)substrate.visible=$('substrate').checked;drawSections();};
$('overlay').onchange=loadSections;
for(const id of ['zcut','ycut','znumber','ynumber'])$(id).oninput=()=>cutsChanged(id);
$('model').onchange=()=>{updateLimits();loadMesh(false);loadSections();};
$('experiment').onchange=()=>{const target={B1:'T_from_P',B2:'V_from_P',B3:'V_from_T_from_P',B4:'V_from_T_direct'}[$('experiment').value];if(target&&!state.catalog.some(m=>m.scene===$('scene').value&&m.family===target)&&state.catalog.some(m=>m.scene==='local'&&m.family===target))$('scene').value='local';const output=filteredModels().find(m=>m.family===target);populateModels(output?.id);loadMesh(false);loadSections();};
$('scene').onchange=()=>{populateModels();loadMesh(true);loadSections();};
$('scope').onchange=()=>{if($('scope').value==='full'&&$('scene').value!=='full'){$('scene').value='full';populateModels();}if($('scope').value==='shoulder'){$('zcut').value=Math.max(-1600,Math.min(1600,Number($('zcut').value)));cutsChanged();}$('wireframe').checked=false;loadMesh(true);loadSections();};
try{const data=await api('/api/catalog');state.catalog=data.models;if(!state.catalog.length)throw new Error('没有找到已保存模型，请先运行 run_validation.py。');if(!state.catalog.some(m=>m.scene==='full'))$('scene').value='local';populateModels();await Promise.all([loadMesh(true),loadSections()]);resize();window.AH53={state,get controls(){return controls;},get camera(){return camera;},renderer};}catch(e){fail(e);}
