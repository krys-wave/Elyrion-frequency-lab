const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
 try {
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{if(new URL(route.request().url()).hostname!=='127.0.0.1'){external.push(route.request().url());return route.abort()}return route.continue()});
 await page.goto('http://127.0.0.1:8765');
 await page.getByRole('button',{name:'New Baseline Run',exact:true}).click();
 await page.waitForTimeout(9500);
 let a=await page.request.get('http://127.0.0.1:8765/api/status').then(r=>r.json());
 if(a.fm.status!=='ready'||!a.connected)throw Error('Live acquisition failed: '+JSON.stringify({fm:a.fm.status,error:a.error}));
 await page.getByRole('button',{name:'Mark event',exact:true}).click();
 await page.getByRole('button',{name:'Stop & save',exact:true}).click();
 await page.waitForFunction(()=>!document.querySelector('.toolbar select').disabled);
 await page.locator('.toolbar select').nth(0).selectOption('Room B');
 await page.getByRole('button',{name:'Start',exact:true}).click();
 // Use five-second windows so scheduler jitter at the 80-frame minimum
 // does not make this browser transport test depend on an exact boundary.
 for(const label of ['duration s','pre s','post s'])await page.getByLabel(label,{exact:true}).fill('5');
 await page.waitForTimeout(6500);
 await page.getByRole('button',{name:'Start Acoustic Perturbation',exact:true}).click();
 await page.waitForTimeout(12500);
 let b=await page.request.get('http://127.0.0.1:8765/api/status').then(r=>r.json());
 if(b.response?.status!=='ready')throw Error('Response not ready: '+JSON.stringify({response:b.response?.status,error:b.error,pre:b.response?.pre_state?.samples,mid:b.response?.during_state?.samples,post:b.response?.post_state?.samples}));
 await page.screenshot({path:require('path').join(process.cwd(),'docs/dashboard.png'),fullPage:true});
 await page.getByRole('button',{name:'Stop & save',exact:true}).click();
 await page.waitForTimeout(1000);
 await page.getByRole('button',{name:'Room A ↔ Room B',exact:true}).click();
 await page.getByRole('article',{name:'Room A summary',exact:true}).waitFor();
 let comparison=await page.request.get('http://127.0.0.1:8765/api/compare').then(r=>r.json());
 if(comparison.status!=='ready'||comparison.similarity>=.8)throw Error('Comparison failed');
 await page.screenshot({path:require('path').join(process.cwd(),'docs/comparison.png'),fullPage:true});
 await page.getByRole('button',{name:'Run archive',exact:true}).click();
 await page.locator('.runlist button').first().waitFor();
 await page.locator('.runlist button').first().click();
 await page.getByText('Events, response functions, metadata, raw measurements',{exact:true}).waitFor({state:'visible'});
 if(errors.length||external.length)throw Error(JSON.stringify({errors,external}));
 console.log(JSON.stringify({liveFramesA:a.fm.samples,liveFramesB:b.fm.samples,response:b.response.status,similarity:comparison.similarity,browserErrors:errors,externalRequests:external,archive:'opened'}));
 } finally {
 await browser.close();
 }
})().catch(e=>{console.error(e);process.exit(1)});
