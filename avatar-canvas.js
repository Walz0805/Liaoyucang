const sessions=new WeakMap();

// No-blink renderer.
// Runtime atlas is deliberately 1x2 and contains no closed-eye artwork:
//   top    = idle / eyes open / mouth closed
//   bottom = speaking / eyes open / mouth open
export function mountAvatar(canvas,guide){
 if(!canvas||!guide?.atlas||!guide?.mouth)return;
 const token=(sessions.get(canvas)?.token||0)+1;
 sessions.set(canvas,{token});
 const image=new Image();
 image.decoding='async';
 image.onload=()=>{
  if(sessions.get(canvas)?.token!==token)return;
  const w=guide.width,h=guide.height;
  canvas.width=w;canvas.height=h;
  const ctx=canvas.getContext('2d',{alpha:true});
  const frame=document.createElement('canvas');frame.width=w;frame.height=h;
  const f=frame.getContext('2d',{alpha:true});
  let last=0;

  function compose(speaking){
   f.clearRect(0,0,w,h);
   // The idle frame is the permanent base. Nothing else on the character moves.
   f.drawImage(image,0,0,w,h,0,0,w,h);
   if(!speaking)return;
   const [x,y,bw,bh]=guide.mouth;
   f.save();
   f.beginPath();
   f.ellipse(x+bw/2,y+bh/2,bw/2,bh/2,0,0,Math.PI*2);
   f.clip();
   // Switch to the strictly aligned open-mouth frame without scaling it.
   f.drawImage(image,x,h+y,bw,bh,x,y,bw,bh);
   f.restore();
  }

  const draw=now=>{
   if(sessions.get(canvas)?.token!==token)return;
   if(now-last<32){requestAnimationFrame(draw);return}
   last=now;
   const host=canvas.closest('#companion');
   const speaking=Boolean(host?.classList.contains('mouth-open'));

   compose(speaking);
   ctx.clearRect(0,0,w,h);
   const t=now/1000;
   const dx=Math.sin(t*.55)*.35;
   const dy=Math.sin(t*.92)*.65;
   ctx.drawImage(frame,dx,dy,w,h);
   canvas.classList.add('ready');
   requestAnimationFrame(draw);
  };
  requestAnimationFrame(draw);
 };
 image.src=guide.atlas;
}
