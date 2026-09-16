import fs from 'node:fs';
import assert from 'node:assert/strict';
import {assessmentAdapter,safetyCheck,recommendationEngine,overrideRecommendation} from './assessment.js';
const b=assessmentAdapter(JSON.parse(fs.readFileSync('mock/before.json','utf8')),'before');
assert(safetyCheck(b));assert.equal(recommendationEngine(b,'focus').scene,'forest');
assert.equal(overrideRecommendation(recommendationEngine(b,'relax'),{scene:'aurora'}).scene,'aurora');
assert(!safetyCheck({...b,flags:{highRisk:true}}));assert.throws(()=>recommendationEngine({...b,flags:{highRisk:true}},'relax'));
assert.throws(()=>assessmentAdapter({flags:{}},'before'));
const elements=new Map();const el=()=>({style:{},className:'',classList:{add(){},remove(){}},value:'',innerHTML:'',disabled:false,prepend(){},addEventListener(){},play(){return Promise.resolve()},pause(){}});
globalThis.document={createElement:()=>el(),querySelector(s){if(!elements.has(s))elements.set(s,el());return elements.get(s)},body:{className:''},addEventListener(type,fn){globalThis.handler=fn}};
globalThis.window={scrollTo(){}};
globalThis.fetch=()=>{throw Error('Network deliberately unavailable')};
await import('./app.js');
const click=async dataset=>handler({target:{closest:()=>({dataset})}});
for(const action of ['consent','scan','load','select','confirm-plan','immersion','after','load','report','done']){
 await click({action});const html=elements.get('#app').innerHTML;assert(html.length>0);
 if(action==='scan'||action==='after'){assert(!html.includes('body-reference.png'));assert(!html.includes('type="file"'));}
 if(action==='confirm-plan')assert(html.includes('B2 · 决策确认'));
 if(action==='report'){assert(html.includes('body-reference.png'));assert.equal((html.match(/生理信号与情绪/g)||[]).length,1);assert(html.includes('下次建议'));assert(!html.includes('刚才，有轻松一点吗'));}
}
assert(elements.get('#app').innerHTML.includes('把这一点安稳'));
console.log('PASS: adapter, safety, recommendation override, complete demo flow');

const {getAssessment,configureAssessmentSource}=await import('./assessment-service.js');
const sample=await getAssessment('before');sample.flags.highRisk=true;assert.equal((await getAssessment('before')).flags.highRisk,false);
configureAssessmentSource({mode:'server'});await assert.rejects(()=>getAssessment('before'),/暂时无法读取/);configureAssessmentSource({mode:'demo'});console.log('PASS: demo flow works without fetch; server failure is explicit; samples isolated');

const {reportPanels}=await import('./report-panels.js');
const after=assessmentAdapter(JSON.parse(fs.readFileSync('mock/after.json','utf8')),'after');
const panels=reportPanels(b,after);
for(const label of ['STAI-S','心率','呼吸','体温','情绪迁移','Delta','Theta','Low Alpha','High Alpha','Beta','Gamma','最大值','末次值','最小值'])assert(panels.includes(label));
for(const label of ['红外','可见光','眼动','<video'])assert(!panels.includes(label));
console.log('PASS: requested report signals present; capture modules excluded');

const {standardFlow,getImmersionPhase}=await import('./experience.js');
assert.equal(standardFlow.reduce((n,p)=>n+p.seconds,0),1320);
assert.equal(getImmersionPhase(120,750).id,'D');assert.equal(getImmersionPhase(360,750).id,'E');assert.equal(getImmersionPhase(570,750).id,'F');assert.equal(getImmersionPhase(690,750).id,'G');
await click({action:'consent'});await click({action:'scan'});await click({action:'load'});assert(elements.get('#app').innerHTML.includes('接入准备'));
await click({action:'select-goal'});await click({action:'select-mode'});await click({instrument:'western'});await click({action:'select-preference'});await click({scene:'forest'});await click({action:'confirm-plan'});assert(elements.get('#app').innerHTML.includes('森林微光'));assert(elements.get('#app').innerHTML.includes('西洋乐器'));
await click({action:'after'});await click({action:'load'});assert(elements.get('#app').innerHTML.includes('J · 本次体验报告'));assert(!elements.get('#app').innerHTML.includes('dialogue-form'));assert(!standardFlow.some(p=>p.id==='I'));assert(!elements.get('#app').innerHTML.includes('跳过反馈'));
console.log('PASS: standard flow, phase boundaries, user preference preservation, direct post-assessment report and report deduplication');
