import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {selectRecommendation} from '../recommendation-service.js';

const catalog=JSON.parse(await readFile(new URL('../assets/data/recommendation-catalog-v2.json',import.meta.url),'utf8'));
assert.equal(catalog.videos.length,12);
assert.equal(catalog.samples.length,10);
assert.equal(catalog.samples.find(x=>x.sampleId==='U001').sourceType,'real_extracted');
assert.equal(catalog.samples.find(x=>x.sampleId==='U002').sourceType,'simulated');

for(const sample of catalog.samples){
  const plan=selectRecommendation(catalog,{sampleId:sample.sampleId});
  assert.ok(plan.videoId);
  assert.ok(plan.videoUrl.endsWith(`${plan.videoId}.mp4`));
  await access(new URL(`../${plan.videoUrl}`,import.meta.url));
  assert.ok(Number.isFinite(plan.recommendationScore));
}

const defaultPlan=selectRecommendation(catalog);
assert.equal(defaultPlan.sampleId,'U002');
assert.equal(defaultPlan.sourceType,'simulated');
console.log(`recommendation_v2 OK: ${catalog.samples.length} samples -> ${catalog.videos.length} tagged videos`);
