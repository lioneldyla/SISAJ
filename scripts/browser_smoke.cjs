/* Full synthetic browser workflow. Starts and stops only its own local API. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'sisa-browser-'));
 const port=process.env.SISA_TEST_PORT||'8877';
 const python=process.env.SISA_TEST_PYTHON||'python';
 const base=`http://127.0.0.1:${port}`;
 const logs=fs.openSync(path.join(temp,'server.log'),'w');
 const server=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',port],{cwd:root,env:{...process.env,DATABASE_URL:'',SISA_DEPLOYMENT:'local',SISA_BOOTSTRAP_KEY:'',SISA_SECURE_COOKIE:'0',SISA_DB_PATH:path.join(temp,'synthetic.db'),SISA_BACKUP_DIR:path.join(temp,'backups')},stdio:['ignore',logs,logs]});
 let browser;
 try {
  let ready=false;
  for(let i=0;i<100;i++){try{const r=await fetch(base+'/ready');if(r.ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}
  assert(ready,'API did not become ready');
  browser=await chromium.launch({headless:true,...(process.env.SISA_CHROMIUM_PATH?{executablePath:process.env.SISA_CHROMIUM_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--disable-setuid-sandbox']}: {})});
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);
  await page.getByRole('heading',{name:'Initialiser votre plateforme'}).waitFor();
  await page.getByLabel('Identifiant nominatif',{exact:true}).fill('demo_admin');
  await page.getByLabel('Mot de passe',{exact:true}).fill('Synthetic-Browser-2026!');
  await page.getByRole('button',{name:'Créer mon compte administrateur'}).click();
  await page.getByRole('heading',{name:'Vue d’ensemble',exact:true}).waitFor();
  await page.getByRole('button',{name:'Nouveau dossier',exact:true}).click();
  await page.getByLabel('Numéro RP *',{exact:true}).fill('SYNTH-UI-001');
  await page.getByLabel('Date RP *',{exact:true}).fill('2026-02-10');
  await page.getByLabel('Année RP *',{exact:true}).fill('2026');
  await page.getByLabel('Unité de provenance *',{exact:true}).fill('Unité fictive');
  await page.getByLabel('Catégorie / qualification source *',{exact:true}).fill('Corruption fictive');
  await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
  await page.getByRole('button',{name:'SYNTH-UI-001',exact:true}).click();
  await page.getByRole('button',{name:'Soumettre à validation'}).click();
  await page.getByRole('button',{name:'Valider',exact:true}).click();
  await page.getByRole('dialog').getByText('Validé',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Fermer',exact:true}).click();
  await page.locator('nav').getByRole('link',{name:'Utilisateurs',exact:true}).click();
  await page.getByRole('button',{name:'Ajouter un utilisateur'}).click();
  await page.getByRole('dialog').getByLabel('Identifiant nominatif',{exact:true}).fill('demo_agent');
  await page.getByLabel('Mot de passe initial').fill('Synthetic-Agent-2026!');
  await page.getByRole('button',{name:'Créer le compte'}).click();
  await page.getByText('demo_agent',{exact:true}).waitFor();
  await page.locator('nav').getByRole('link',{name:'Imports',exact:true}).click();
  await page.getByLabel('Fichier CSV ou XLSX').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:Buffer.from('rp_number,rp_year,date_rp,provenance,category,transnational\nSYNTH-UI-IMP,2026,2026-03-01,OPJ fictif,Fraude fictive,Non\n')});
  await page.getByRole('button',{name:'Contrôler le fichier'}).click();
  await page.getByRole('button',{name:'Confirmer l’import de 1 ligne(s)'}).click();
  await page.getByRole('cell',{name:'synthetic.csv',exact:true}).waitFor();
  await page.locator('nav').getByRole('link',{name:'Statistiques & rapports',exact:true}).click();
  await page.locator('#stats-result .metric-value').first().waitFor();
  assert.equal(await page.locator('#stats-result .metric-value').first().innerText(),'1');
  for(const [type,signature] of [['PDF','%PDF-'],['XLSX','PK']]){
   const row=page.locator('.export-option').filter({has:page.locator('.export-type',{hasText:type})});
   const pending=page.waitForEvent('download');await row.getByRole('button').click();const file=await pending;
   const buffer=fs.readFileSync(await file.path());assert(buffer.subarray(0,signature.length).toString()===signature);
  }
  await page.locator('nav').getByRole('link',{name:'Journal d’audit',exact:true}).click();
  await page.getByRole('heading',{name:'Dernières opérations'}).waitFor();
  await page.locator('nav').getByRole('link',{name:'Vue d’ensemble',exact:true}).click();
  await page.getByRole('heading',{name:'Vue d’ensemble',exact:true}).waitFor();
  const out=process.env.SISA_SCREENSHOT_DIR;
  if(out){fs.mkdirSync(out,{recursive:true});await page.locator('#toast').waitFor({state:'hidden'});await page.screenshot({path:path.join(out,'sisa-dashboard-desktop.png'),fullPage:true,animations:'disabled'});}
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Horizontal overflow on mobile');
  await page.getByRole('button',{name:'Ouvrir le menu'}).click();
  await page.locator('nav').getByRole('link',{name:'Dossiers',exact:true}).click();
  await page.getByRole('heading',{name:'Dossiers',exact:true}).waitFor();
  if(out)await page.screenshot({path:path.join(out,'sisa-dossiers-mobile.png'),fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'Ouvrir le menu'}).click();
  await page.getByRole('button',{name:'Se déconnecter',exact:true}).click();
  await page.getByRole('heading',{name:'Heureux de vous retrouver.'}).waitFor();
  assert.deepEqual(errors,[]);
  console.log('Browser workflow passed: bootstrap, login, creation, submission, validation, users, import confirmation, statistics, PDF/XLSX downloads, responsive navigation, logout; 0 JavaScript errors.');
 } finally {
  if(browser)await browser.close();server.kill('SIGTERM');
  await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
  fs.closeSync(logs);fs.rmSync(temp,{recursive:true,force:true});
 }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
