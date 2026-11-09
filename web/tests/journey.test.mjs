// Runs the real UI event handlers with a tiny DOM adapter; not a browser/layout test.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import * as content from '../src/content.ts';
import * as engine from '../src/engine.ts';
async function demo(saved){
 const events={},store=new Map(saved?[['crosslearn-demo-v1',saved]]:[]),elements=new Map();
 const el=()=>({textContent:'',innerHTML:'',classList:{add(){},remove(){},toggle(){}},focus(){},select(){},setAttribute(){}});
 const root={innerHTML:'',className:'',addEventListener:(n,fn)=>events[n]=fn};
 const document={querySelector:sel=>sel==='#root'?root:elements.get(sel)||((elements.set(sel,el())),elements.get(sel)),querySelectorAll:()=>[],createElement:()=>({...el(),click(){}})};
 const window={addEventListener(){}};
 const context=vm.createContext({...content,...engine,document,window,crypto:globalThis.crypto,localStorage:{getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,v)},navigator:{onLine:true},console,Date,Set,Blob,URL,setTimeout});
 let source=await readFile(new URL('../src/app.js',import.meta.url),'utf8');source=source.replace(/^import .*;\r?\n/gm,'');vm.runInContext(source,context);
 const click=(dataset)=>events.click({target:{closest:()=>({dataset,matches:()=>false})}});
 const state=()=>JSON.parse(store.get('crosslearn-demo-v1'));
 return {root,events,click,state,store};
}
test('complete journey: wrong crossword, hint, baseline, three modalities, post-test, report, restart',async()=>{const d=await demo();assert.match(d.root.innerHTML,/Small discoveries/);d.click({action:'teacher'});assert.match(d.root.innerHTML,/No results have been invented/);d.click({action:'pupil'});d.click({action:'start'});d.click({action:'check'});assert.match(d.root.innerHTML,/another look/);d.click({action:'hint'});assert.equal(d.state().hints,1);
 for(const [k,c]of Object.entries(engine.cells()))d.events.input({target:{dataset:{cell:k},value:c.letter}});
 d.click({action:'check'});assert.equal(d.state().stage,'baseline');
 for(const q of content.baseline){assert.doesNotMatch(d.root.innerHTML,/Correct answer:/);assert.doesNotMatch(d.root.innerHTML,/Roots hold many plants/);d.click({answer:String((q.answer+1)%3)});d.click({action:'next'});}
 assert.equal(d.state().stage,'learn');assert.equal(engine.score(content.baseline,d.state().answers).correct,0);
 assert.match(d.root.innerHTML,/text explanation/);d.click({action:'next-lesson'});assert.match(d.root.innerHTML,/audio explanation/);assert.doesNotMatch(d.root.innerHTML,/Moss is a small plant without flowers/);d.click({action:'transcript'});assert.match(d.root.innerHTML,/Moss is a small plant without flowers/);d.click({action:'next-lesson'});assert.match(d.root.innerHTML,/Diagram explanation/);d.click({action:'next-lesson'});assert.equal(d.state().stage,'post-test');assert.equal(d.state().exposures.length,3);assert.equal(d.state().exposures[1].transcript,true);
 for(const q of content.post){d.click({answer:String(q.answer)});d.click({action:'next'});}assert.equal(d.state().stage,'results');assert.equal(engine.score(content.post,d.state().answers).correct,6);assert.ok(engine.validSession(d.state()));
 d.click({action:'teacher'});assert.match(d.root.innerHTML,/Insufficient evidence/);assert.match(d.root.innerHTML,/100 pp/);assert.match(d.root.innerHTML,/No AI calls/);d.click({action:'restart'});assert.equal(d.state().rotation,1);assert.equal(d.state().stage,'welcome');assert.equal(Object.keys(d.state().answers).length,0);
});
test('refresh restores progress; malformed data starts safely',async()=>{const d=await demo();d.click({action:'start'});d.click({action:'hint'});const resumed=await demo(d.store.get('crosslearn-demo-v1'));assert.equal(resumed.state().hints,1);assert.match(resumed.root.innerHTML,/Check crossword/);const invalid=await demo('{broken');assert.equal(invalid.state().stage,'welcome');});
