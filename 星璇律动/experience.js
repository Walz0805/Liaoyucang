export const standardFlow = [
 {id:'S',name:'知情同意 / 监护人同意',seconds:0,note:'首次约 3–5 分钟 · 舱外完成'},
 {id:'0',name:'前测评估',seconds:150,note:'量表与生理基线采集'},
 {id:'A',name:'接入准备 · 模式选择',seconds:120,note:'佩戴设备，选择目标、场景和音乐'},
 {id:'B2',name:'决策确认',seconds:60,note:'推荐供参考，选择由你决定'},
 {id:'C',name:'引导',seconds:120,note:'轻声引导，逐步入境'},
 {id:'D',name:'深化',seconds:240,note:'让视频与音乐接过舞台'},
 {id:'E',name:'巩固',seconds:210,note:'保持稳定，安静沉浸'},
 {id:'F',name:'唤醒',seconds:120,note:'温柔回到当下'},
 {id:'G',name:'余韵',seconds:60,note:'音乐渐退，画面稍作停留'},
 {id:'H',name:'后测评估',seconds:120,note:'再次采集，比较前后'},
 {id:'J',name:'分析报告',seconds:120,note:'查看变化和下次建议'}
];
export const immersionPhases=standardFlow.filter(p=>['C','D','E','F','G'].includes(p.id));
export function getImmersionPhase(seconds,duration){let offset=0;const total=immersionPhases.reduce((n,p)=>n+p.seconds,0);const standardSeconds=seconds/duration*total;for(const phase of immersionPhases){if(standardSeconds<offset+phase.seconds)return {...phase,progress:(standardSeconds-offset)/phase.seconds};offset+=phase.seconds;}return {...immersionPhases.at(-1),progress:1};}
