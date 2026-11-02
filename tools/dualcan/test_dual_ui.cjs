/* Run with node and jsdom available through NODE_PATH. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync(path.join(__dirname,'../../components/web_ui_v2/web/monitor.js'),'utf8');
const fragment=source.split('/* DUAL_BUS_TEST_BEGIN')[1].split('/* DUAL_BUS_TEST_END */')[0];
const code='/* DUAL_BUS_TEST_BEGIN'+fragment+';window.makeDual=buildDualBusTest;';
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function scenario({reject='',autopid=false}={}){
 const dom=new JSDOM('<!doctype html><body></body>',{url:'http://wican/',runScripts:'outside-only'}),w=dom.window;
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.API='';
 w.api=async p=>p.includes('settings/autopid')?{enabled:autopid}:p.includes('obd_chip')?{ready:true}:p==='/api/autopid'?{stats:{running:false}}:{running:true,silent:true,baud_kbps:500};
 w.eval(`function h(tag,attrs,...kids){const e=document.createElement(tag);for(const [k,v]of Object.entries(attrs||{})){if(v==null||v===false)continue;if(k==='class')e.className=v;else if(k.startsWith('on'))e.addEventListener(k.slice(2),v);else e.setAttribute(k,v===true?'':v);}for(const c of kids.flat(9)){if(c!=null&&c!==false)e.append(c.nodeType?c:document.createTextNode(c));}return e;}`);
 const sockets=[];
 class WS{
  constructor(url){this.url=url;this.readyState=0;this.sent=[];sockets.push(this);setTimeout(()=>{this.readyState=1;this.onopen?.();},0);}
  send(data){const text=typeof data==='string'?data:new TextDecoder().decode(data);this.sent.push(text);if(this.url.endsWith('/ws/obd')&&text.endsWith('\r')&&text!=='ATMA\r')queueMicrotask(()=>this.onmessage?.({data:(text.trim()===reject?'?':'OK')+'\r>'}));}
  receive(text){this.onmessage?.({data:text});}
  close(){this.readyState=3;this.onclose?.();}
 }
 w.WebSocket=WS;w.eval(code);const ui=w.makeDual();w.document.body.append(ui.el);
 return{w,dom,ui,sockets,cards:[...ui.el.querySelectorAll('section')],dispose(){ui.dispose();dom.window.close();}};
}
(async()=>{
 let x=await scenario();
 assert.equal(x.sockets.length,0,'no implicit capture');
 const [native,chip]=x.cards;
 assert.equal(x.ui.parseNative('T18DAF1101FF').id,'18DAF110');
 assert.equal(x.ui.parseChip('321 03 04').data,'03 04');
 assert.equal(x.ui.parseNative('tFFF0'),null);assert.equal(x.ui.parseChip('BUFFER FULL'),null);
 native.querySelector('button').click();chip.querySelector('button').click();await pause(40);
 assert.equal(x.sockets.length,2);
 const ns=x.sockets.find(s=>s.url.endsWith('/ws/can')),cs=x.sockets.find(s=>s.url.endsWith('/ws/obd'));
 assert.deepEqual(cs.sent.slice(0,11),['ATE0','ATM0','VTP251','VT PBR 500000','ATCSM1','ATCFC0','ATH1','ATS1','ATL0','ATD0','ATCAF0'].map(c=>c+'\r'));
 assert.equal(cs.sent[11],'ATMA\r');assert.equal(ns.sent.length,0);
 ns.receive('t1232');ns.receive('0102\rt1232AABB\r');cs.receive('321 03');cs.receive(' 04\r321 AA BB\r');await pause(280);
 assert(native.textContent.includes('Frames: 2'));assert(chip.textContent.includes('Frames: 2'));
 assert(native.textContent.includes('AA BB'));assert(chip.textContent.includes('AA BB'));
 native.querySelectorAll('button')[1].click();assert.equal(ns.readyState,3);assert.equal(cs.readyState,1);
 cs.receive('321 CC DD\r');await pause(280);assert(chip.textContent.includes('Frames: 3'));
 native.querySelectorAll('button')[2].click();await pause(280);assert(native.textContent.includes('Frames: 0'));assert(chip.textContent.includes('Frames: 3'));
 x.dispose();assert.equal(cs.sent.at(-1),' ');assert.equal(cs.readyState,3);
 x=await scenario({reject:'ATCSM1'});x.cards[1].querySelector('button').click();await pause(40);
 assert(x.cards[1].textContent.includes('ATCSM1 rejected'));assert(!x.sockets[0].sent.includes('ATMA\r'));x.dispose();
 x=await scenario({autopid:true});x.cards[1].querySelector('button').click();await pause(20);
 assert.equal(x.sockets.length,0);assert(x.cards[1].textContent.includes('Disable AutoPID'));x.dispose();
 x=await scenario();x.cards[0].querySelector('button').click();x.ui.dispose();await pause(20);assert.equal(x.sockets.length,0);x.dom.window.close();
 console.log('PASS: independent sockets/counts, fragmented frames, setup sequence, stop/clear isolation, cleanup, command refusal, AutoPID gate, cancelled start');
})().catch(e=>{console.error(e);process.exit(1);});
