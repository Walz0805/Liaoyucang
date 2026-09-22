import {followVoice,stopMouth} from './lipsync.js?v=20260916-4';
export const narrationFiles={consent:'consent',scan:'liangbiao',prepare:'prepare',select:'select','select-goal':'select',after:'liangbiao',report:'report',C01:'guide',F01:'wake'};
let audio=null,button=null,generation=0,volume=0.8;
function control(){
 if(button)return button;
 button=document.createElement('button');button.className='narration-control';button.type='button';button.hidden=true;
 button.addEventListener('click',()=>{if(!audio)return;if(!audio.paused){audio.pause();stopMouth();button.textContent='▶ 继续讲解';}else{if(audio.ended)audio.currentTime=0;attempt(audio,generation);}});
 (document.querySelector?.('#narration-slot')||document.body).appendChild(button);return button;
}
function attempt(player,id){player.play().then(()=>{if(id===generation){button.textContent='Ⅱ 暂停讲解';followVoice(player);}}).catch(error=>{if(id!==generation)return;button.textContent=error.name==='NotAllowedError'?'▶ 点击播放本段讲解':'▶ 讲解加载失败，点击重试';});}
export function stopNarration(){stopMouth();generation++;if(audio){audio.pause();audio.remove?.();audio=null;}if(button)button.hidden=true;}
export function playNarration(key,companion='xiaoxuan'){
 const file=narrationFiles[key];if(!file||typeof Audio==='undefined')return false;
 const visibleGuide=document.querySelector?.('#companion')?.dataset?.guide;
 const activeCompanion=companion||visibleGuide||'xiaoxuan';
 const voiceFile=activeCompanion==='xiaoxing'?`${file}-xiaoxing`:file;
 stopNarration();const id=generation;audio=new Audio(`assets/voice/${voiceFile}.wav`);audio.volume=volume;const player=audio;player.id="stage-narration";player.hidden=true;document.body.appendChild(player);
 control().hidden=false;button.textContent='正在载入讲解…';player.addEventListener('ended',()=>{if(id===generation){button.textContent='↻ 重听讲解';document.dispatchEvent(new CustomEvent('narration-ended',{detail:{key}}));}});attempt(player,id);document.dispatchEvent(new CustomEvent('narration-started',{detail:{key}}));return true;
}
export function pauseNarration(paused){if(!audio||audio.ended)return;if(paused){audio.pause();stopMouth();button.textContent='▶ 继续讲解';}else attempt(audio,generation);}
export function setNarrationVolume(value){volume=value;if(audio)audio.volume=value;}
