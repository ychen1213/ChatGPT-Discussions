async (page) => {
  const steps=[];
  const pause=async()=>{
    await page.waitForFunction(()=>window.AH53 && window.AH53.state.busy===0 && window.AH53.state.mesh && document.querySelector('#error').hidden,{timeout:60000});
    await page.waitForTimeout(350);
  };
  const record=async(name,start)=>steps.push({name,elapsed_ms:Date.now()-start,...await page.evaluate(()=>({model:document.querySelector('#model').value,scope:document.querySelector('#scope').value,status:document.querySelector('#status').textContent,mesh_id:window.AH53.state.mesh.model_id,section_z:window.AH53.state.sections?.z,section_y:window.AH53.state.sections?.y}))});
  await pause();await record('startup_full',Date.now());
  for(const scope of ['period','stripe']){const start=Date.now();await page.locator('#scope').selectOption(scope);await pause();await record(scope,start);}
  await page.locator('#scene').selectOption('local');await pause();
  for(const id of ['local_P_fine','local_T_direct_fine']){const start=Date.now();await page.locator('#model').selectOption(id);await pause();await record('A_'+id,start);}
  await page.locator('#scope').selectOption('shoulder');await pause();
  await page.locator('#model').selectOption('local_V_direct_fine');await pause();await record('A_voxel_raw',Date.now());
  await page.locator('#experiment').selectOption('B1');await pause();
  await page.locator('#model').selectOption('local_T_from_P');await pause();await record('B1_triangle',Date.now());
  await page.locator('#projection').selectOption('orthographic');await page.locator('#xy').click();
  await page.locator('#znumber').fill('413');await page.locator('#znumber').press('Tab');
  await page.waitForFunction(()=>window.AH53.state.sections?.z===410,{timeout:30000});
  await pause();await record('Z_slice',Date.now());
  await page.locator('#ynumber').fill('270');await page.locator('#ynumber').press('Tab');
  await page.waitForFunction(()=>window.AH53.state.sections?.y===270,{timeout:30000});
  await pause();await record('Y_slice',Date.now());
  await page.locator('#wireframe').check();await page.locator('#flat').check();await page.locator('#substrate').uncheck();
  await page.locator('#gain').selectOption('5');await page.locator('#gain').selectOption('1');
  await page.locator('#reset').click();
  await page.screenshot({path:'output/playwright/shoulder950.png'});
  await page.locator('#save').click();await page.waitForFunction(()=>!document.querySelector('#save').disabled,{timeout:30000});await record('screenshot_saved',Date.now());
  console.log(JSON.stringify({steps,viewport:page.viewportSize(),horizontalOverflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)}));
}
