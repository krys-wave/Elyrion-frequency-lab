// Run against an idle local server with an isolated LAB_DATA_DIR.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH,headless:true,args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const api = async (path,body) => {
      const response = await page.request.fetch('http://127.0.0.1:8765/api/'+path,body===undefined?{}:{method:'POST',data:body});
      assert.ok(response.ok(),await response.text());
      return response.json();
    };
    await page.goto('http://127.0.0.1:8765');
    assert.equal((await api('status')).run,null,'Use an idle test server');
    await page.getByRole('button',{name:'New Baseline Run',exact:true}).click();
    await page.waitForTimeout(9100);
    await page.getByRole('button',{name:'Stop & save',exact:true}).click();
    await page.getByRole('status').filter({hasText:'Run saved locally'}).waitFor();
    await page.waitForFunction(()=>!document.querySelector('.toolbar select').disabled);
    await page.locator('.toolbar select').first().selectOption('Room B');
    await page.getByRole('button',{name:'New Baseline Run',exact:true}).click();
    await page.waitForTimeout(9100);
    const roomB = (await api('status')).run.id;
    await page.getByRole('button',{name:'Run archive',exact:true}).click();
    const runButton = page.locator('.runlist button').filter({hasText:roomB.slice(0,8)});
    await runButton.filter({hasText:'recording'}).waitFor();
    await runButton.click();
    const selectedRaw = page.locator('details').filter({has:page.getByText('Events, response functions, metadata, raw measurements',{exact:true})}).locator('pre');
    await selectedRaw.waitFor({state:'attached'});

    // Hold an archive read taken BEFORE saving, then deliver it AFTER success.
    let release, captured;
    const held = new Promise(resolve => { release=resolve; });
    const responseCaptured = new Promise(resolve => { captured=resolve; });
    let holdNext=true;
    await page.route('**/api/runs',async route => {
      if(route.request().method()==='GET' && holdNext){
        holdNext=false;
        const response=await route.fetch();
        const snapshot=await response.json();
        assert.equal(snapshot.find(r=>r.id===roomB).status,'recording');
        captured();
        await held;
        try{await route.fulfill({response})}catch(error){
          if(!/abort|closed|handled|cancel|intercept/i.test(String(error)))throw error;
        }
      }else await route.continue();
    });
    let captureTimeout;
    try{
      await Promise.race([responseCaptured,new Promise((_,reject)=>{captureTimeout=setTimeout(()=>reject(new Error('Archive polling did not issue the expected read')),10000)})]);
    }finally{clearTimeout(captureTimeout)}
    await page.getByRole('button',{name:'Stop & save',exact:true}).click();
    await page.getByRole('status').filter({hasText:'Run saved locally'}).waitFor();
    await runButton.filter({hasText:'complete'}).waitFor();
    release();
    await page.waitForTimeout(1500);
    assert.match(await runButton.textContent(),/complete/);
    await page.waitForFunction(() => {
      const summary=[...document.querySelectorAll('summary')].find(s=>s.textContent==='Events, response functions, metadata, raw measurements');
      const text=summary?.parentElement.querySelector('pre')?.textContent;
      return text && JSON.parse(text).run.status==='complete';
    });
    await page.unroute('**/api/runs');

    // A save from another client also refreshes the already-open archive.
    const external = await api('runs',{room:'Room B',source:'simulation',baseline:false});
    const externalButton=page.locator('.runlist button').filter({hasText:external.id.slice(0,8)});
    await externalButton.filter({hasText:'recording'}).waitFor();
    await api('stop',{});
    await externalButton.filter({hasText:'complete'}).waitFor();

    await page.getByRole('button',{name:'Room A ↔ Room B',exact:true}).click();
    await page.getByRole('article',{name:'Room A summary',exact:true}).waitFor();
    const comparison=await api('compare');
    for(const room of ['Room A','Room B']){
      const card=page.getByRole('article',{name:room+' summary',exact:true});
      assert.deepEqual(await card.locator('dt').allTextContents(),['Run ID','PA ID','Dominant frequency (M_X)','PI status','Qualifying baseline count']);
      const values=await card.locator('dd').allTextContents();
      assert.equal(values[0],comparison.runs[room]);
      assert.equal(values[1],comparison.pa[room].identifier);
      assert.notEqual(values[0],values[1]);
      assert.equal(values[2],comparison.fm[room].components.M_X.frequency_hz.toFixed(3)+' Hz');
      assert.equal(values[3],comparison.pi[room].status==='ready'?'Ready':comparison.pi[room].status);
      assert.equal(values[4],String(comparison.pi[room].qualifying_runs));
    }
    const raw=page.locator('details').filter({has:page.getByText('Raw Analysis / Machine Representation',{exact:true})});
    const machine=JSON.parse(await raw.locator('pre').textContent());
    for(const key of ['runs','fm','pi','pa','responses','normalized_difference'])assert.ok(key in machine);
    const legend=page.locator('.lab-key');
    assert.equal(await legend.getAttribute('open'),null);
    await page.getByText('Key / Legend',{exact:true}).click();
    assert.deepEqual(await legend.locator('dt').allTextContents(),['Sensor State','FAP','Relationship Map','FM','PI','D','PA','RFN','ΔFM']);
    await legend.locator('dd').last().waitFor({state:'visible'});
    await page.getByText('Key / Legend',{exact:true}).click();
    await page.screenshot({path:'docs/comparison.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({roomSummaries:'passed',rawAnalysis:'preserved',legend:'passed',archiveSave:'complete',delayedRecordingResponse:'ignored',externalSave:'refreshed',browserErrors:errors}));
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exit(1)});
