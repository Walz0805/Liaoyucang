const catalogUrl='assets/data/recommendation-catalog-v2.json?v=20260916-1';
let catalogPromise;

export function loadRecommendationCatalog(){
  if(!catalogPromise)catalogPromise=fetch(catalogUrl,{cache:'no-store'}).then(response=>{
    if(!response.ok)throw new Error(`推荐目录加载失败 (${response.status})`);
    return response.json();
  });
  return catalogPromise;
}

const sceneKind=video=>{
  const text=[video?.title,video?.sceneCategory,...(video?.contentKeywords||[])].join(' ');
  if(/海|水|荷|湿地/.test(text))return 'ocean';
  if(/山|雪|云/.test(text))return 'aurora';
  return 'forest';
};

export function selectRecommendation(catalog,{sampleId='U002',goal='relax',instrument='chinese',tone='jue'}={}){
  const sample=catalog.samples.find(item=>item.sampleId===sampleId)||catalog.samples.find(item=>item.sourceType==='simulated')||catalog.samples[0];
  if(!sample)throw new Error('推荐目录中没有可用样本');
  const recommendation=sample.recommendation?.recommendations?.[0];
  if(!recommendation)throw new Error(`样本 ${sample.sampleId} 没有可用推荐`);
  const video=catalog.videos.find(item=>item.videoId===recommendation.video_id);
  if(!video)throw new Error(`素材库缺少视频 ${recommendation.video_id}`);
  const reasons=(recommendation.reasons||[]).filter(Boolean);
  return {
    goal,
    scene:sceneKind(video),
    instrument,
    tone,
    music:instrument==='chinese'?'five-tone':'piano',
    title:video.title,
    reason:reasons[0]||'画面节律与当前状态较为匹配。',
    reasons,
    videoId:video.videoId,
    videoUrl:video.url,
    functionTag:video.functionTag,
    sceneCategory:video.sceneCategory,
    recommendationScore:recommendation.score,
    algorithm:'recommendation_v2',
    sampleId:sample.sampleId,
    sourceType:sample.sourceType,
    riskLevel:sample.recommendation.risk_level,
    fallbackUsed:Boolean(sample.recommendation.fallback_used)
  };
}

export async function getDemoRecommendation(options={}){
  return selectRecommendation(await loadRecommendationCatalog(),options);
}

