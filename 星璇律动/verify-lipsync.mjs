import assert from 'node:assert/strict';
let open=false,frame;
globalThis.document={querySelector:()=>({classList:{toggle:(c,v)=>open=v,remove:()=>open=false}})};
globalThis.requestAnimationFrame=fn=>(frame=fn,1);globalThis.cancelAnimationFrame=()=>{};
globalThis.fetch=async()=>({json:async()=>({'test.wav':[.1,0,.1,.1]})});
const {followVoice,stopMouth}=await import('./lipsync.js');
const p={src:'test.wav',currentTime:0,paused:false,ended:false};followVoice(p);await new Promise(r=>setTimeout(r,0));frame();assert(open);p.currentTime=.06;frame();assert(!open);p.currentTime=.1;frame();assert(open);p.paused=true;frame();assert(!open);stopMouth();assert(!open);console.log('PASS: voice opens mouth, silence/pause/stop close mouth');
