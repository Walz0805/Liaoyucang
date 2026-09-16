# 数字人 DEMO 适配说明（v3）

本版只替换两位数字人的人物状态素材与动画驱动；原有 WAV 语音、页面流程和疗愈内容保持不变。

## 运行时方式

每位角色使用一个 2×2 **完整人物帧**图集：

- 左上：正常 / 闭嘴
- 右上：眨眼 / 闭嘴
- 左下：睁眼 / 说话
- 右下：眨眼 / 说话

`avatar-canvas.js` 每次直接从图集中绘制一整张完整人物帧。运行时不再粘贴 mouth patch、face patch，也不做局部蒙版覆盖。

- 眨眼：约 3.2–5.9 秒随机触发一次，闭眼约 155 ms。
- 说话：沿用项目原 WAV 音频；播放期间按原 DEMO 风格在 idle / speaking 完整帧间切换。
- 暂停、停止、播放结束：立即回到 idle 完整帧。

## 网页实际加载素材

- `assets/avatar/xiaoxuan-demo-exact-states-v3.png`
- `assets/avatar/xiaoxing-demo-exact-states-v3.png`

以上两个文件由确认过的四个状态图严格合成，`app.js` 直接引用它们。

## 主要修改代码

- `avatar-canvas.js`
- `lipsync.js`
- `app.js`
- `index.html`

另见 `AVATAR-RUNTIME-ASSETS.txt`。
