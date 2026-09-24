import assert from 'node:assert/strict';
import {compareAssessments,scoreAssessment} from '../scoring-engine.js';

const sample=(stage)=>({
 basic:{heartRate:stage==='before'?88:70,respiration:stage==='before'?21:14,eda:stage==='before'?18:5},
 eeg:{alpha:stage==='before'?25:45,beta:stage==='before'?24:18,theta:24},
 emotion:{neutral:stage==='before'?.3:.65,happy:.2,sadness:stage==='before'?.35:.05,quality:{valid:true,sampleCount:30,validRatio:1}},
 questionnaire:{score:stage==='before'?55:38},
 series:{heartRate:Array(40).fill(stage==='before'?88:70),respiration:Array(40).fill(stage==='before'?21:14),eda:Array(40).fill(stage==='before'?18:5)},
 device:{eyeSeries:Array.from({length:30},(_,i)=>({x:.5+(stage==='before'?.2:.03)*Math.sin(i),y:.5+(stage==='before'?.2:.03)*Math.cos(i)})),motionMagnitudes:Array(30).fill(stage==='before'?3.5:.5)}
});

const result=compareAssessments(sample('before'),sample('after'));
assert.equal(result.after.hrv.available,false,'不得从普通心率序列推导 HRV');
assert.ok(result.effect.relaxation.change>0);
assert.ok(result.effect.attention.change>0);
assert.ok(result.effect.emotionPeace.change>0);
assert.ok(result.effect.comprehensive.change>0);
assert.ok(!result.after.relaxation.usedMetrics.includes('hrv'));
assert.equal(Math.round(Object.values(result.after.relaxation.weights).reduce((a,b)=>a+b,0)),1,'缺失项权重应重新归一化');
const missing=scoreAssessment({...sample('after'),device:{}});
assert.deepEqual(missing.attention.usedMetrics,['betaTheta']);
console.log('scoring-engine tests passed');
