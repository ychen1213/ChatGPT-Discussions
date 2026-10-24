async (page) => {
  const steps=[],errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const ready=async()=>{
    await page.waitForFunction(()=>window.AH53 && window.AH53.state.busy===0 && window.AH53.state.mesh && document.querySelector('#error').hidden,null,{timeout:60000});
    await page.waitForFunction(()=>window.AH53.state.sections?.models?.includes(document.querySelector('#model').value),null,{timeout:60000});
  };
  const action=async(name,fn)=>{const start=Date.now();await fn();await ready();steps.push({name,ms:Date.now()-start,...await page.evaluate(()=>({model:document.querySelector('#model').value,scope:document.querySelector('#scope').value,z:window.AH53.state.sections.z,y:window.AH53.state.sections.y,status:document.querySelector('#status').textContent}))});};
  await ready();
  const before=await page.evaluate(()=>window.AH53.camera.position.toArray());
  const box=await page.locator('#webgl').boundingBox();
  await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);await page.mouse.down();await page.mouse.move(box.x+box.width*.57,box.y+box.height*.6,{steps:8});await page.mouse.up();await page.waitForTimeout(300);
  const rotated=await page.evaluate(()=>window.AH53.camera.position.toArray());
  if(JSON.stringify(before)===JSON.stringify(rotated))throw Error('Camera did not rotate');
  await page.mouse.wheel(0,-90);await page.mouse.down({button:'right'});await page.mouse.move(box.x+box.width*.60,box.y+box.height*.61,{steps:4});await page.mouse.up({button:'right'});await page.waitForTimeout(250);
  await page.locator('#reset').click();
  await page.screenshot({path:'output/playwright/full_final950.png'});
  const frameIntervals=await page.evaluate(()=>new Promise(resolve=>{let last=performance.now(),times=[];function next(t){times.push(t-last);last=t;if(times.length>=40)resolve(times.slice(1).sort((a,b)=>a-b));else requestAnimationFrame(next);}requestAnimationFrame(next);}));
  await action('whole_to_period',()=>page.locator('#scope').selectOption('period'));
  await action('period_to_stripe',()=>page.locator('#scope').selectOption('stripe'));
  await action('local_scene',()=>page.locator('#scene').selectOption('local'));
  for(const id of ['local_P_fine','local_T_direct_fine','local_V_direct_fine'])await action('A_'+id,()=>page.locator('#model').selectOption(id));
  await action('shoulder',()=>page.locator('#scope').selectOption('shoulder'));
  await action('route_B1',()=>page.locator('#experiment').selectOption('B1'));
  await action('T_from_P',()=>page.locator('#model').selectOption('local_T_from_P'));
  const cameraBefore=await page.evaluate(()=>window.AH53.camera.position.toArray());
  await action('same_view_P',()=>page.locator('#model').selectOption('local_P_fine'));
  const cameraAfter=await page.evaluate(()=>window.AH53.camera.position.toArray());
  const cameraPreserved=Math.max(...cameraBefore.map((v,i)=>Math.abs(v-cameraAfter[i])))<.001;
  if(!cameraPreserved)throw Error('Model switch changed camera');
  await page.locator('#projection').selectOption('orthographic');await page.locator('#xy').click();
  await page.locator('#znumber').fill('410');await page.locator('#znumber').press('Tab');
  await page.waitForFunction(()=>window.AH53.state.sections.z===410,null,{timeout:30000});await ready();
  await page.locator('#ynumber').fill('270');await page.locator('#ynumber').press('Tab');
  await page.waitForFunction(()=>window.AH53.state.sections.y===270,null,{timeout:30000});
  for(const [route,id] of [['B2','local_V_from_P'],['B3','local_V_from_T'],['B4','local_V_from_Tdirect']]){
    await action(route+'_route',()=>page.locator('#experiment').selectOption(route));
    await action(route+'_output',()=>page.locator('#model').selectOption(id));
  }
  await page.locator('#substrate').uncheck();await page.locator('#wireframe').check();await page.locator('#flat').check();
  await page.locator('#gain').selectOption('5');await page.locator('#gain').selectOption('1');await page.locator('#reset').click();
  await page.screenshot({path:'output/playwright/voxel_final950.png'});
  await page.locator('#save').click();await page.waitForFunction(()=>!document.querySelector('#save').disabled,null,{timeout:30000});
  const saved=await page.locator('#status').textContent();if(!saved.includes('已保存'))throw Error('Save screenshot failed');
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  const [doc]=await Promise.all([page.waitForEvent('popup'),page.getByRole('link',{name:'阅读详细说明 ↗'}).click()]);
  await doc.waitForLoadState();const docTitle=await doc.title();const broken=await doc.locator('img').evaluateAll(imgs=>imgs.filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src));await doc.close();
  const result={passed:!errors.length&&!overflow&&!broken.length,viewport:page.viewportSize(),steps,camera_rotated:true,camera_preserved_on_model_switch:cameraPreserved,section_z_nm:410,section_y_nm:270,screenshot_message:saved,doc_title:docTitle,broken_images:broken,horizontal_overflow:overflow,errors,full_preview_frame_intervals_ms:{samples:frameIntervals.length,median:frameIntervals[Math.floor(frameIntervals.length*.5)],p95:frameIntervals[Math.floor(frameIntervals.length*.95)],max:Math.max(...frameIntervals)}};
  await page.evaluate(r=>window.QA_RESULT=r,result);
  return result;
}
