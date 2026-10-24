async(page)=>{
 const doc=await page.context().newPage();await doc.setViewportSize({width:1280,height:900});
 const errors=[];doc.on('pageerror',e=>errors.push(e.message));
 await doc.goto('file:///D:/工作/ChatGPT-Discussions/3D-Geometry/ah53-geometry-validation/AH53_三种几何表示验证_详细说明.html');
 await doc.waitForLoadState('load');
 const info={url:doc.url(),title:await doc.title(),headings:await doc.locator('h2').count(),images:await doc.locator('img').count(),broken:await doc.locator('img').evaluateAll(a=>a.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.src)),externalScripts:await doc.locator('script[src]').count()};
 await doc.screenshot({path:'output/playwright/report_offline_top.png'});
 await doc.getByRole('heading',{name:'7. 已经得到什么结果？如何合理使用这些结果？',exact:true}).scrollIntoViewIfNeeded();
 await doc.screenshot({path:'output/playwright/report_offline_results.png'});
 await doc.locator('img[src*="02_三种表示"]').scrollIntoViewIfNeeded();
 await doc.screenshot({path:'output/playwright/report_beginner_figure.png'});
 info.desktopOverflow=await doc.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 info.missingAnchors=await doc.locator('a[href^="#"]').evaluateAll(a=>a.filter(x=>!document.getElementById(decodeURIComponent(x.hash.slice(1)))).map(x=>x.hash));
 await doc.setViewportSize({width:390,height:844});await doc.evaluate(()=>scrollTo(0,0));
 await doc.screenshot({path:'output/playwright/report_beginner_mobile.png'});
 info.mobileOverflow=await doc.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 await doc.locator('.mobile-toc summary').click();
 info.mobileTocOpens=await doc.locator('.mobile-toc').getAttribute('open')!==null;
 info.errors=errors;
 await doc.close();return info;
}
