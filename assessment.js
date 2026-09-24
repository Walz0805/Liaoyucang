const number=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const finite=a=>(a||[]).map(number).filter(v=>v!==null);
const sample=(a,limit=72)=>{a=finite(a);if(a.length<=limit)return a;const step=Math.ceil(a.length/limit);return a.filter((_,i)=>i%step===0).slice(0,limit)};
const average=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;

// Adapter for the exported platform structure supplied in 评估报告数据.zip.
export function platformAssessmentAdapter(raw,stage='before'){
 const rows=Array.isArray(raw?.data)?raw.data:[];
 const row=label=>rows.find(x=>x.label===label)||{};
 const values=(label,key='value')=>sample((row(label).dateValues||[]).map(x=>x[key]));
 const value=label=>number(row(label).preValue)??average(values(label));
 const alphaLow=values('Alpha','x'),alphaHigh=values('Alpha','z');
 const betaLow=values('Beta','x'),betaHigh=values('Beta','z');
 const gammaLow=values('Gamma','x'),gammaHigh=values('Gamma','y');
 const expressions=(row('表情数据').dateValues||[]).flatMap(x=>[x.x,x.y]).filter(Boolean);
 const emotionNames={happy:['愉悦','开心','高兴'],neutral:['中性'],sadness:['悲伤','低落'],fear:['恐惧'],surprise:['惊讶'],disgust:['厌恶'],anger:['愤怒','生气']};
 const emotion=Object.fromEntries(Object.entries(emotionNames).map(([k,names])=>[k,expressions.length?expressions.filter(x=>names.includes(x)).length/expressions.length:null]));
 emotion.polarity=(emotion.happy??0)-(emotion.sadness??0)-(emotion.fear??0);
 return {stage,basic:{heartRate:value('心率'),respiration:value('呼吸'),temperature:value('体温'),eda:value('皮电'),spo2:value('血氧')},eeg:{delta:value('Delta'),theta:value('Theta'),lowAlpha:average(alphaLow),highAlpha:average(alphaHigh),alpha:average([...alphaLow,...alphaHigh]),beta:average([...betaLow,...betaHigh]),gamma:average([...gammaLow,...gammaHigh])},emotion,stateVector:{},questionnaire:{name:'STAI-S',score:stage==='before'?52:37,totalItems:20},flags:{highRisk:false,fatigue:false},series:{heartRate:values('心率'),respiration:values('呼吸'),temperature:values('体温'),eda:values('皮电'),spo2:values('血氧'),delta:values('Delta'),theta:values('Theta'),lowAlpha:alphaLow,highAlpha:alphaHigh,alpha:sample([...alphaLow,...alphaHigh]),beta:sample([...betaLow,...betaHigh]),gamma:sample([...gammaLow,...gammaHigh])},source:'platform-export'};
}

export function assessmentAdapter(raw,stage){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('检测文件格式不正确');
 if(Array.isArray(raw.data))return platformAssessmentAdapter(raw,stage);
 const group=o=>Object.fromEntries(Object.entries(o||{}).map(([k,v])=>[k,number(v)]));
 if(typeof raw.flags?.highRisk!=='boolean')throw Error('缺少有效的 highRisk 安全字段，请由工作人员确认');
 return {stage,basic:group(raw.basic),eeg:group(raw.eeg),emotion:{...group(raw.emotion),quality:{...(raw.emotion?.quality||{})}},device:structuredClone(raw.device||{}),hrv:structuredClone(raw.hrv||{}),mood:structuredClone(raw.mood||{}),stateVector:group(raw.stateVector),questionnaire:{name:'STAI-S',score:number(raw.questionnaire?.score)??(stage==='before'?52:37),totalItems:20,responses:Array.isArray(raw.questionnaire?.responses)?raw.questionnaire.responses.map(number):[],band:raw.questionnaire?.band||null,completedAt:raw.questionnaire?.completedAt||null,scoringVersion:raw.questionnaire?.scoringVersion||'stai-s-v1'},flags:{...raw.flags},series:Object.fromEntries(Object.entries(raw.series||{}).map(([k,v])=>[k,Array.isArray(v)?finite(v):[]]))};
}
export function safetyCheck(a){return a?.flags.highRisk===false}
export function buildRecommendationPrompt({goal,physiologySummary,scene,tone}){return `目标=${goal}，生理摘要=${physiologySummary}，命中场景=${scene}，五音=${tone}。输出一句不超过25字的推荐理由，口语、非医疗、不报数字。`}
export function recommendationEngine(a,goal,preference={}){if(!safetyCheck(a))throw Error('请先完成安全确认');const scene=preference.scene||(goal==='focus'?'forest':goal==='energy'?'aurora':'ocean');const instrument=preference.instrument||'chinese';const tone=preference.tone||'jue';const titles={ocean:'晨雾海岸',forest:'林间微光',aurora:'极光来信'};return {goal,scene,instrument,tone,music:instrument==='chinese'?'five-tone':'piano',title:titles[scene],reason:goal==='sleep'?'让柔和声景陪你慢慢安静下来':'从熟悉的自然节律开始放松吧',prompt:buildRecommendationPrompt({goal,physiologySummary:'HRV偏低、表情偏紧张',scene:titles[scene],tone})}}
export function overrideRecommendation(plan,changes){return {...plan,...changes}}
