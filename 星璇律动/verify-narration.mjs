import assert from 'node:assert/strict';
const made=[];let button;
globalThis.document={createElement(){button={hidden:true,addEventListener(k,f){this[k]=f}};return button},body:{appendChild(){}}};
globalThis.Audio=class{constructor(src){this.src=src;this.paused=true;this.events={};made.push(this)} addEventListener(k,f){this.events[k]=f} pause(){this.paused=true} play(){this.paused=false;return Promise.resolve()}};
const n=await import('./narration.js');
for(const key of Object.keys(n.narrationFiles)){const previous=made.at(-1);n.playNarration(key);await Promise.resolve();if(previous)assert(previous.paused);assert(made.at(-1).src.endsWith(n.narrationFiles[key]+'.wav'));}
n.pauseNarration(true);assert(made.at(-1).paused);n.pauseNarration(false);assert(!made.at(-1).paused);n.setNarrationVolume(.2);assert.equal(made.at(-1).volume,.2);n.stopNarration();assert(button.hidden);assert(made.at(-1).paused);
Audio.prototype.play=function(){return Promise.reject(Object.assign(new Error(),{name:'NotAllowedError'}))};n.playNarration('report');await new Promise(r=>setTimeout(r,0));assert(button.textContent.includes('点击播放'));n.stopNarration();
console.log('PASS: 8 stage mappings, stop on switch, pause/resume, volume, autoplay fallback');
