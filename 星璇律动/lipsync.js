let timer=null,active=null,envelopes=null,load=null;
export function stopMouth(){if(timer!==null)cancelAnimationFrame(timer);timer=null;active=null;document.querySelector?.('#companion')?.classList?.remove('mouth-open');}
export function followVoice(player){
 if(typeof requestAnimationFrame==='undefined')return;
 stopMouth();active=player;
 load??=fetch('assets/voice/envelopes.json').then(r=>r.json()).then(data=>envelopes=data).catch(()=>null);
 const file=player.src.split('/').pop();
 function frame(){
  if(active!==player)return;
  const samples=envelopes?.[file];const level=samples?.[Math.floor(player.currentTime/0.05)]??0;
  const open=!player.paused&&!player.ended&&level>0.025&&Math.floor(player.currentTime/0.11)%3!==2;
  document.querySelector('#companion')?.classList.toggle('mouth-open',open);
  if(player.paused||player.ended){stopMouth();return;}timer=requestAnimationFrame(frame);
 }
 frame();
}
