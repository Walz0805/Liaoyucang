const CONFIG={
 stateWeights:{stai:0.30,mood:0.25,physiology:0.35,hrv:0.10},
 physiologyWeights:{heartRate:0.35,respiration:0.35,eda:0.30},
 relaxationWeights:{hrv:0.35,eda:0.25,respiration:0.20,alpha:0.20},
 attentionWeights:{eyeStability:0.35,motionStability:0.25,betaTheta:0.40},
 emotionWeights:{expression:0.50,eda:0.25,heartRate:0.25},
 comprehensiveWeights:{relaxation:0.45,attention:0.25,emotionPeace:0.30}
};

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value))?Number(value):null;
const clamp=value=>Math.max(0,Math.min(100,value));
const round=value=>value==null?null:Number(value.toFixed(1));
const mean=values=>{const valid=(values||[]).map(finite).filter(value=>value!=null);return valid.length?valid.reduce((sum,value)=>sum+value,0)/valid.length:null};

function weighted(values,weights,keys=Object.keys(weights)){
 const used=keys.filter(key=>finite(values[key])!=null&&weights[key]>0);
 const total=used.reduce((sum,key)=>sum+weights[key],0);
 const score=total?used.reduce((sum,key)=>sum+finite(values[key])*weights[key],0)/total:null;
 return {score:round(score),components:Object.fromEntries(Object.keys(weights).map(key=>[key,round(finite(values[key]))])),weights:Object.fromEntries(used.map(key=>[key,round(weights[key]/total)])),usedMetrics:used,missingMetrics:Object.keys(weights).filter(key=>!used.includes(key))};
}

function intervalScore(value,[low,high],[lowerMargin,upperMargin]){
 value=finite(value);if(value==null)return null;if(value>=low&&value<=high)return 100;
 const distance=value<low?low-value:value-high,margin=value<low?lowerMargin:upperMargin;
 return clamp(100*(1-distance/margin));
}

function seriesQuality(values,{min=0,max=Infinity,minSamples=30}={}){
 const raw=(values||[]).map(finite).filter(value=>value!=null),valid=raw.filter(value=>value>=min&&value<=max);
 const validRatio=raw.length?valid.length/raw.length:0;
 const repeats=valid.length>1?valid.slice(1).filter((value,index)=>value===valid[index]).length/(valid.length-1):0;
 const flags=[];
 if(!raw.length)flags.push('missing');
 if(raw.length&&validRatio<0.8)flags.push('low_valid_ratio');
 if(raw.length<minSamples)flags.push('insufficient_samples');
 if(repeats>=0.9)flags.push('flat_or_repeated');
 return {mean:mean(valid),rawCount:raw.length,validCount:valid.length,validRatio:round(validRatio),flags};
}

function expressionScore(emotion={}){
 const code={happy:2,surprise:1,neutral:0,sadness:-1,disgust:-2,fear:-3,anger:-4};
 const pairs=Object.entries(code).map(([key,value])=>[finite(emotion[key])||0,value]);
 const total=pairs.reduce((sum,[ratio])=>sum+ratio,0);
 if(!total)return {score:null,used:false,reason:'missing_expression'};
 const average=pairs.reduce((sum,[ratio,value])=>sum+ratio*value,0)/total;
 const quality=emotion.quality||{};
 const usable=quality.valid!==false&&(quality.validRatio==null||quality.validRatio>=0.8)&&(quality.sampleCount==null||quality.sampleCount>=10);
 return {score:usable?round(clamp((average+4)/6*100)):null,used:usable,meanDeviceValue:round(average),reason:usable?null:'expression_quality_failed'};
}

function eyeScore(device={}){
 const points=device.eyeSeries||[];
 if(points.length<2)return null;
 const mx=mean(points.map(point=>point.x)),my=mean(points.map(point=>point.y));
 const dispersion=Math.sqrt(points.reduce((sum,point)=>sum+(point.x-mx)**2+(point.y-my)**2,0)/points.length);
 return {score:round(clamp((1-dispersion)*100)),dispersion:round(dispersion)};
}

function motionScore(device={}){
 const values=device.motionMagnitudes||[];
 const motionMean=mean(values);
 return motionMean==null?null:{score:round(clamp((5-motionMean)/5*100)),mean:round(motionMean)};
}

function hrvScore(assessment={}){
 const intervals=(assessment.hrv?.ibi||assessment.series?.ibi||[]).map(finite).filter(value=>value!=null&&value>=300&&value<=2000);
 if(intervals.length<30)return {score:null,rmssd:null,lnRmssd:null,available:false};
 const rmssd=Math.sqrt(intervals.slice(1).reduce((sum,value,index)=>sum+(value-intervals[index])**2,0)/(intervals.length-1));
 const lnRmssd=rmssd>0?Math.log(rmssd):null;
 return {score:lnRmssd==null?null:round(clamp((lnRmssd-2.5)/2*100)),rmssd:round(rmssd),lnRmssd:round(lnRmssd),available:lnRmssd!=null};
}

export function scoreAssessment(assessment){
 const heart=seriesQuality(assessment.series?.heartRate||[assessment.basic?.heartRate],{min:30,max:220});
 const respiration=seriesQuality(assessment.series?.respiration||[assessment.basic?.respiration],{min:4,max:60});
 const eda=seriesQuality(assessment.series?.eda||[assessment.basic?.eda],{min:0,max:100});
 const hrv=hrvScore(assessment),expression=expressionScore(assessment.emotion);
 const physiology=weighted({heartRate:heart.validRatio>=0.8?intervalScore(heart.mean,[60,80],[10,20]):null,respiration:respiration.validRatio>=0.8?intervalScore(respiration.mean,[10,18],[4,8]):null,eda:eda.validRatio>=0.8?intervalScore(eda.mean,[1,10],[1,15]):null},CONFIG.physiologyWeights);
 const relaxation=weighted({hrv:hrv.score,eda:eda.validRatio>=0.8?clamp(100-eda.mean):null,respiration:respiration.validRatio>=0.8?intervalScore(respiration.mean,[10,18],[4,8]):null,alpha:clamp(finite(assessment.eeg?.alpha))},CONFIG.relaxationWeights);
 const eye=eyeScore(assessment.device),motion=motionScore(assessment.device),theta=finite(assessment.eeg?.theta),beta=finite(assessment.eeg?.beta),ratio=theta>0?beta/theta:null;
 const attention=weighted({eyeStability:eye?.score,motionStability:motion?.score,betaTheta:ratio==null?null:clamp((ratio-.25)/2.75*100)},CONFIG.attentionWeights);
 const emotionPeace=weighted({expression:expression.score,eda:eda.validRatio>=0.8?clamp(100-eda.mean):null,heartRate:intervalScore(heart.mean,[60,80],[10,20])},CONFIG.emotionWeights);
 const comprehensive=weighted({relaxation:relaxation.score,attention:attention.score,emotionPeace:emotionPeace.score},CONFIG.comprehensiveWeights);
 const stai=finite(assessment.questionnaire?.score),staiState=stai>=20&&stai<=80?(80-stai)/60*100:null;
 const moodSubjective=mean([assessment.mood?.vas==null?null:finite(assessment.mood.vas)*10,assessment.mood?.samValence==null?null:(finite(assessment.mood.samValence)-1)/8*100]);
 const mood=moodSubjective!=null&&expression.score!=null?moodSubjective*.7+expression.score*.3:moodSubjective??expression.score;
 const state=weighted({stai:staiState,mood,physiology:physiology.score,hrv:hrv.score},CONFIG.stateWeights);
 const qualityFlags=[...heart.flags.map(x=>`heart_rate_${x}`),...respiration.flags.map(x=>`respiration_${x}`),...eda.flags.map(x=>`eda_${x}`)];
 return {version:'score_v2_web_2026_09',state,physiology,hrv,expression,relaxation,attention,emotionPeace,comprehensive,raw:{eyeDispersion:eye?.dispersion,motionMean:motion?.mean,betaThetaRatio:round(ratio)},quality:{flags:qualityFlags,dataQuality:qualityFlags.some(flag=>flag.includes('low_valid_ratio'))?'fair':'good'}};
}

function effectLabel(change){return change>=15?'明显改善':change>=5?'轻度改善':change<=-15?'明显下降':change<=-5?'轻度下降':'基本稳定'}
function compareMetric(before,after,weights){
 const common=Object.keys(weights).filter(key=>before.components[key]!=null&&after.components[key]!=null);
 const b=weighted(before.components,weights,common).score,a=weighted(after.components,weights,common).score;
 const change=b==null||a==null?null:round(a-b);
 return {before:b,after:a,change,changePercent:b?round(change/Math.abs(b)*100):null,commonMetrics:common,label:change==null?'数据不足':effectLabel(change),comparable:change!=null};
}

export function compareAssessments(beforeAssessment,afterAssessment){
 const before=scoreAssessment(beforeAssessment),after=scoreAssessment(afterAssessment);
 return {before,after,effect:{relaxation:compareMetric(before.relaxation,after.relaxation,CONFIG.relaxationWeights),attention:compareMetric(before.attention,after.attention,CONFIG.attentionWeights),emotionPeace:compareMetric(before.emotionPeace,after.emotionPeace,CONFIG.emotionWeights),comprehensive:compareMetric(before.comprehensive,after.comprehensive,CONFIG.comprehensiveWeights)}};
}

export {CONFIG};
