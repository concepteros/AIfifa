# CheckFIFA 微信小程序

这是从当前 Web 版本打包出的微信小程序基础版，可直接用微信开发者工具导入 `miniprogram` 目录。

## 页面

- `pages/index/index`：首页、夺冠胜率榜、球队列表
- `pages/groups/groups`：小组赛赛程、十二个小组
- `pages/team/team`：球队详情、球员姓名/年龄/caps/goals/club
- `pages/predictions/predictions`：本地用户预测投票
- `pages/mvp/mvp`：历届 MVP / 金球奖得主

## 数据

- `utils/worldcup-data.js`：由 Web 版 `data.js` 和 `squad-data.js` 生成
- `utils/helpers.js`：球队标签、胜率格式化、小组赛程生成

## 导入方式

1. 打开微信开发者工具。
2. 选择“导入项目”。
3. 项目目录选择本目录：`miniprogram`。
4. AppID 可先使用测试号或在 `project.config.json` 中替换。

## 后续接入实时 API

小程序正式上线前，需要在微信公众平台配置合法 request 域名。实时比分、新闻、后端投票等接口可在对应页面 JS 中用 `wx.request` 接入。
