let frame=null,active=null,context=null,source=null;
let mouthOpen=false;

function host(){return document.querySelector?.('#companion')}
function setMouth(open){
 mouthOpen=Boolean(open);
 const el=host();
 el?.classList?.toggle('mouth-open',mouthOpen);
 el?.classList?.remove('mouth-half');
}
function releaseAudioGraph(){
 if(frame!==null)cancelAnimationFrame(frame);
 frame=null;
 try{source?.disconnect()}catch{}
 source=null;
 if(context){context.close?.().catch?.(()=>{});context=null}
}
export function stopMouth(){active=null;releaseAudioGraph();setMouth(false)}

function fallback(player){
 let last=0;
 const draw=now=>{
  if(active!==player||player.paused||player.ended){stopMouth();return}
  if(now-last>(mouthOpen?85:105)){setMouth(!mouthOpen);last=now}
  frame=requestAnimationFrame(draw);
 };
 frame=requestAnimationFrame(draw);
}

// Binary, syllable-like lip sync. The analyser finds speech-energy peaks, but
// the renderer only switches between the original closed and open frames.
export function followVoice(player){
 stopMouth();active=player;
 player.addEventListener?.('ended',stopMouth,{once:true});
 try{
  const AudioCtx=window.AudioContext||window.webkitAudioContext;
  if(!AudioCtx)throw new Error('Web Audio unavailable');
  context=new AudioCtx();source=context.createMediaElementSource(player);
  const analyser=context.createAnalyser();
  analyser.fftSize=256;analyser.smoothingTimeConstant=.48;
  source.connect(analyser);analyser.connect(context.destination);context.resume?.();
  const samples=new Uint8Array(analyser.fftSize);
  let envelope=0,previous=0,lastOpen=-999,lastClose=-999;
  const draw=now=>{
   if(active!==player||player.paused||player.ended){stopMouth();return}
   analyser.getByteTimeDomainData(samples);let sum=0;
   for(const sample of samples){const value=(sample-128)/128;sum+=value*value}
   const rms=Math.sqrt(sum/samples.length);
   envelope+=(rms > envelope ? 0.52 : 0.2)*(rms-envelope);
   const voiced=envelope>.024;
   const rising=envelope-previous>.006;
   // Open on a new energy rise. During a long connected phrase, permit a new
   // pulse after 175 ms so adjacent Chinese syllables do not merge into one.
   if(!mouthOpen&&voiced&&now-lastClose>48&&(rising||now-lastOpen>175)){
    setMouth(true);lastOpen=now;
   }
   // Each detected syllable is a clean open/closed pair using the two aligned
   // images. Quiet gaps close sooner; voiced syllables remain open up to 92 ms.
   if(mouthOpen&&((!voiced&&now-lastOpen>42)||now-lastOpen>92)){
    setMouth(false);lastClose=now;
   }
   previous=envelope;
   frame=requestAnimationFrame(draw);
  };
  draw();
 }catch(error){console.warn('Audio peak lip sync unavailable; using cadence fallback.',error);fallback(player)}
}
