export function assessmentAdapter(raw,stage){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('检测文件格式不正确');
 const number=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
 const group=o=>Object.fromEntries(Object.entries(o||{}).map(([k,v])=>[k,number(v)]));
 if(typeof raw.flags?.highRisk!=='boolean')throw Error('缺少有效的 highRisk 安全字段，请由工作人员确认');
 return {stage,basic:group(raw.basic),eeg:group(raw.eeg),emotion:group(raw.emotion),stateVector:group(raw.stateVector),flags:{...raw.flags},series:Object.fromEntries(Object.entries(raw.series||{}).map(([k,v])=>[k,Array.isArray(v)?v.map(number).filter(x=>x!==null):[]]))};
}
export function safetyCheck(a){return a?.flags.highRisk===false}
export function recommendationEngine(a,goal){if(!safetyCheck(a))throw Error('请先完成安全确认');return {goal,scene:goal==='focus'?'forest':goal==='energy'?'aurora':'ocean',music:goal==='sleep'?'piano':'five-tone',title:goal==='focus'?'林间微光':goal==='energy'?'极光来信':'晨雾海岸',reason:a.flags.fatigue?'此刻可以先给自己一点休息的空间。这段低刺激、慢节奏的自然体验，陪你慢慢安静下来。':'根据你的体验目标，为你准备了一段柔和的自然声景。'}}
export function overrideRecommendation(plan,changes){return {...plan,...changes}}
