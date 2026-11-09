import {baseline, post, concepts, type Item, type Modality} from './content.ts';
export type Answers = Record<string, number>;
export type Exposure = {concept: string; modality: Modality; seconds: number; transcript: boolean; audioPlayed: boolean; version: string};
export type Session = {id: string; rotation: number; stage: 'welcome'|'game'|'baseline'|'learn'|'post-test'|'results'; letters: Record<string,string>; answers: Answers; question: number; lesson: number; exposures: Exposure[]; readAloud?: string[]; attempts: number; hints: number; startedAt: string};
export const key = (r:number,c:number) => `${r}-${c}`;
export function cells() {
 const result: Record<string,{letter:string; number?:number; words:string[]}> = {};
 for (const c of concepts) for (let i=0;i<c.word.length;i++) {
  const k=key(c.row+(c.direction==='down'?i:0),c.col+(c.direction==='across'?i:0));
  if (result[k] && result[k].letter!==c.word[i]) throw Error('Invalid crossing');
  result[k] ??= {letter:c.word[i],words:[]}; result[k].words.push(c.id); if(i===0)result[k].number=c.number;
 }
 return result;
}
export function assignment(rotation:number):Record<string,Modality> { const modes:Modality[]=['text','audio','visual']; return Object.fromEntries(concepts.map((c,i)=>[c.id,modes[(i+rotation)%3]])); }
export function score(items:Item[],answers:Answers) {const correct=items.filter(q=>answers[q.id]===q.answer).length;return {correct,total:items.length,pct:items.length?100*correct/items.length:0};}
export function summary(answers:Answers) {return concepts.map(c=>{const before=score(baseline.filter(q=>q.concept===c.id),answers),after=score(post.filter(q=>q.concept===c.id),answers);return {...c,before,after,gain:after.pct-before.pct};});}
export function isSolved(letters:Record<string,string>) { return Object.entries(cells()).every(([k,c])=>letters[k]===c.letter); }
export const fresh = (rotation=0):Session => ({id:crypto.randomUUID(),rotation,stage:'welcome',letters:{},answers:{},question:0,lesson:0,exposures:[],readAloud:[],attempts:0,hints:0,startedAt:new Date().toISOString()});
export function validSession(s:unknown):s is Session {
 if(!s || typeof s!=='object')return false; const x=s as Session;
 const shape=typeof x.id==='string' && ['welcome','game','baseline','learn','post-test','results'].includes(x.stage) && Number.isInteger(x.rotation) && x.rotation>=0 && x.rotation<6 && Number.isInteger(x.question) && x.question>=0 && x.question<6 && Number.isInteger(x.lesson) && x.lesson>=0 && x.lesson<3 && !!x.letters && typeof x.letters==='object' && Object.values(x.letters).every(v=>typeof v==='string'&&/^[A-Z]?$/.test(v)) && !!x.answers && typeof x.answers==='object' && [...baseline,...post].every(q=> x.answers[q.id]===undefined || (Number.isInteger(x.answers[q.id]) && x.answers[q.id]>=0 && x.answers[q.id]<q.options.length)) && Array.isArray(x.exposures) && x.exposures.every(e=>e&&concepts.some(c=>c.id===e.concept)&&['text','audio','visual'].includes(e.modality)&&Number.isFinite(e.seconds)&&e.seconds>=0&&typeof e.transcript==='boolean'&&typeof e.audioPlayed==='boolean') && Number.isInteger(x.attempts)&&x.attempts>=0&&Number.isInteger(x.hints)&&x.hints>=0&&typeof x.startedAt==='string';
 if(!shape)return false;
 if(x.readAloud!==undefined&&(!Array.isArray(x.readAloud)||!x.readAloud.every(id=>[...baseline,...post].some(q=>q.id===id))))return false;
 if(['learn','post-test','results'].includes(x.stage)&&!baseline.every(q=>x.answers[q.id]!==undefined))return false;
 if(['post-test','results'].includes(x.stage)&&(x.exposures.length!==3||new Set(x.exposures.map(e=>e.concept)).size!==3))return false;
 if(x.stage==='results'&&!post.every(q=>x.answers[q.id]!==undefined))return false;
 return true;
}
