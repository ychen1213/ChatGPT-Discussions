async(page)=>{
  await page.waitForFunction(()=>window.AH53 && !window.AH53.state.busy,null,{timeout:60000});
  await page.locator('#scene').selectOption('local');await page.locator('#scope').selectOption('shoulder');
  const results=[];
  for(const [route,id] of [['B1','local_T_from_P'],['B2','local_V_from_P'],['B3','local_V_from_T'],['B4','local_V_from_Tdirect']]){
    await page.locator('#experiment').selectOption(route);
    await page.waitForFunction(id=>document.querySelector('#model').value===id && !window.AH53.state.busy && document.querySelector('#error').hidden,id,{timeout:60000});
    const options=await page.locator('#model option').evaluateAll(els=>els.map(e=>e.value));
    if(options.some(x=>x.includes('coarse')))throw Error('Coarse model leaked into '+route);
    results.push({route,selected:id,options});
  }
  const externalResources=await page.evaluate(()=>performance.getEntriesByType('resource').map(x=>x.name).filter(u=>!u.startsWith(location.origin)));
  return {passed:true,results,externalResources};
}
