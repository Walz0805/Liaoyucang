# 星璇律动 · 网页 Demo

运行 `node server.cjs`，打开 http://127.0.0.1:5173 。无需安装依赖。

首次演示采用原生 JavaScript、CSS 与 SVG，便于直接启动。后续可迁移 Vue。

流程：首页 → 同意 → 模拟前测 → 摘要/目标 → 推荐或自选 → 沉浸 → 后测 → 反馈 → 报告 → 完成。

- `assessment.js`：Adapter、安全判断、规则推荐与覆盖接口。
- `mock/before.json`、`mock/after.json`：演示数据。可在采集页导入相同结构的 JSON。
- `app.js` 中 `media`：视频、音乐和语音独立资源槽位。
- 沉浸演示 120 秒，C/D/E/F/G 分别在 0/35/65/90/110 秒开始；可提前结束。
- 目前接入 MDN 花朵 MP4 在线占位视频（三个场景共用，静音循环）；无独立音乐、真实设备或 AI；数字人为 AI 补绘的小尺寸透明全身立绘，完整展示头部至双脚。
- 运行 `node verify.mjs` 检查 Adapter、安全拦截、推荐覆盖及 DOM 桩环境下的页面主流程（需先启动服务器）。不等同于完整浏览器视觉验收。

占位视频来源：https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/video ，视频地址：https://developer.mozilla.org/shared-assets/videos/flower.mp4 。加载失败会保留 CSS 动态场景。

视觉第二版：首页使用生成的月夜海面背景；检测/报告人体直接使用用户提供的截图，以 CSS 混合与柔化边缘融入背景。参考截图分辨率有限，未伪称为 3D 模型。

视觉第三版：人体图仅在最终报告显示。前后测使用简洁导入界面；首页分为深蓝沉浸区和暖白需求选择区。内容层级参考 Headspace（https://www.headspace.com/）和 Endel（https://endel.io/）公开官网，未复用其素材或疗效声明。外站浏览器视觉加载超时，参考范围为可访问页面内容结构。

当前 Demo 无需导入 JSON，前后测继续按钮自动使用 assessment-service.js 内置数据，默认推荐晨雾海岸。服务器接入时使用 configureAssessmentSource({mode: "server", endpoint: "/api/assessments/latest"})，返回数据仍经过 Adapter 和安全检查；服务器故障不会回退成模拟数据。verify.mjs 现在无需启动服务器，并在禁用 fetch 情况下验证流程。

最新流程：S 舱外同意 → 0 前测 → A 准备 → A2 选择 → B2 决策 → C/D/E/F/G 单页沉浸 → H 后测 → J 报告。标准表合计 22 分钟（已移除 2 分 30 秒对话），其中沉浸 12 分 30 秒；Demo 可选 2 分钟快览，其余阶段手动推进。不提供文字或语音对话，后测直接进入报告。报告删除重复曲线与汇总条，保留一次生理/情绪、一次 EEG，并加入规则型数值差异摘要和建议。参考资料：上音 AWE2026 与 WAIC2025 官方介绍；没有取得其完整报告原稿，不声称复刻。
