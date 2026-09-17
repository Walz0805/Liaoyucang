const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=value=>Number.isFinite(value)?Number(value.toFixed(2)):'—';
const stats=values=>values?.length?[Math.max(...values),values.at(-1),Math.min(...values)]:[null,null,null];
function trend(before=[],after=[],unit='字段值'){
 const all=[...before,...after];if(!all.length)return '<div class="no-signal">暂无序列数据</div>';
 const min=Math.min(...all),max=Math.max(...all),pad=(max-min)*.12||1,lo=min-pad,hi=max+pad;
 const poly=(arr,color)=>arr.length?`<polyline fill="none" stroke="${color}" stroke-width="1.5" points="${arr.map((v,i)=>`${38+i/(arr.length-1||1)*300},${110-(v-lo)/(hi-lo)*95}`).join(' ')}"/>`:'';
 const ticks=[0,.5,1].map((v,i)=>`<span class="chart-y chart-y-${i}">${num(hi-(hi-lo)*v)}</span>`).join('');
 return `<div class="signal-chart-wrap" role="img" aria-label="前后测${escape(unit)}序列比较"><svg class="signal-chart" preserveAspectRatio="none" viewBox="0 0 350 140" aria-hidden="true">${[0,.5,1].map(v=>`<path d="M38 ${15+95*v}H338" stroke="#95b7d31b"/>`).join('')}${poly(before,'#6a83b8')}${poly(after,'#a0dfd6')}</svg>${ticks}<span class="chart-x chart-x-start">开始</span><span class="chart-x chart-x-end">归一化采样进程</span></div>`;
}
function signal(b,a,key,label,unit){const bv=b.basic[key]??b.eeg[key],av=a.basic[key]??a.eeg[key];return `<article class="panel signal-panel"><h3>${label}<small>${unit}</small></h3><div class="signal-values"><span>${num(bv)}</span><i>→</i><strong>${num(av)}</strong></div>${trend(b.series[key],a.series[key],unit)}<details class="signal-detail"><summary>采样统计</summary><div class="signal-stats"><span></span><span>最大值</span><span>末次值</span><span>最小值</span>${[[b,'前测'],[a,'后测']].map(([d,l])=>`<span>${l}</span>${stats(d.series[key]).map(v=>`<b>${num(v)}</b>`).join('')}`).join('')}</div></details></article>`}
export function reportInsight(b,a){
 const changes=[['heartRate','心率','次/分钟'],['respiration','呼吸','次/分钟'],['temperature','体温','°C']].flatMap(([k,n,u])=>{
 const x=b.basic[k],y=a.basic[k];if(!Number.isFinite(x)||!Number.isFinite(y))return [];
 const d=Number((y-x).toFixed(2));return [`${n}${d===0?'保持一致':`${d>0?'上升':'下降'} ${Math.abs(d)} ${u}`}`];
 });
 return {analysis:changes.length?changes.join('，')+'。':'当前可比较的数据不足。',suggestion:a.flags.fatigue?'仍有疲劳标记。下次可继续选择低刺激、慢节奏声景。':'保留喜欢的场景；如有不适，优先调整音乐或缩短时长。'};
}
export function reportPanels(b,a){
 const bands=[['delta','Delta'],['theta','Theta'],['lowAlpha','Low Alpha'],['highAlpha','High Alpha'],['alpha','Alpha'],['beta','Beta'],['gamma','Gamma']];
 const bs=b.questionnaire?.score,as=a.questionnaire?.score;
 return `<div class="report-section-title"><h3>01 · 生理信号与情绪迁移</h3><span class="legend">● 前测 <span>● 后测</span> · DEMO 模拟数据</span></div><div class="signal-grid">${signal(b,a,'heartRate','心率','次/分钟')}${signal(b,a,'respiration','呼吸','次/分钟')}${signal(b,a,'temperature','体温','°C')}<article class="panel emotion-panel"><h3>情绪迁移 <small>前测 → 后测</small></h3><p>情绪极性 <strong>${num(b.emotion.polarity)} → ${num(a.emotion.polarity)}</strong></p>${[['happy','愉悦'],['neutral','中性'],['sadness','低落'],['fear','恐惧'],['surprise','惊讶'],['disgust','厌恶']].map(([k,l])=>`<div class="emotion-row"><span>${l}</span><div>${[b,a].map(d=>`<i style="width:${Math.max(0,Math.min(1,d.emotion[k]||0))*100}%"></i>`).join('')}</div><small>${num(b.emotion[k])} → ${num(a.emotion[k])}</small></div>`).join('')}<p class="signal-note">缺失项显示 —，不推断情绪诊断。</p></article></div><div class="report-section-title"><h3>02 · EEG 分频段趋势</h3><span>各频段独立展示</span></div><div class="eeg-grid">${bands.map(([k,l])=>signal(b,a,k,l,'设备字段值')).join('')}</div>`;
}
