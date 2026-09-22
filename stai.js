export const STAI_ITEMS=[
 ['我感到心情平静',true],['我感到安全',true],['我是紧张的',false],['我感到紧张不安（局促）',false],['我感到安逸、舒适',true],
 ['我感到心烦意乱',false],['我现在正为可能发生的不幸而烦恼',false],['我感到满意',true],['我感到害怕',false],['我感到舒适自在',true],
 ['我有自信心',true],['我觉得神经过敏（神经质）',false],['我极度紧张不安',false],['我优柔寡断（拿不定主意）',false],['我是轻松的',true],
 ['我感到心满意足',true],['我是烦恼的',false],['我感到慌乱（不知所措）',false],['我感觉镇定、沉着',true],['我感到愉快',true]
];

export const STAI_OPTIONS=['完全没有','有些','中等程度','非常明显'];

export function scoreStai(responses=[]){
 if(responses.length!==STAI_ITEMS.length||responses.some(value=>![1,2,3,4].includes(Number(value))))return null;
 return responses.reduce((total,value,index)=>total+(STAI_ITEMS[index][1]?5-Number(value):Number(value)),0);
}

export function staiBand(score){
 if(!Number.isFinite(Number(score)))return '尚未完成';
 return Number(score)<=37?'低焦虑参考区间':Number(score)<=44?'中等焦虑参考区间':'高焦虑参考区间';
}

export function staiChangeText(before,after){
 const change=Number(before)-Number(after);
 if(!Number.isFinite(change))return '暂无可比较结果';
 if(change>=10)return `下降 ${change} 分 · 变化较明显`;
 if(change>0)return `下降 ${change} 分 · 有所改善`;
 if(change===0)return '前后评分保持一致';
 return `上升 ${Math.abs(change)} 分 · 建议持续关注`;
}
