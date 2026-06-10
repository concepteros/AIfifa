# CheckFIFA Vercel 部署说明

本项目是静态页面加轻量 Node API 的结构，适合直接部署到 Vercel。

## 结构

- 根目录 HTML/CSS/JS：由 Vercel 作为静态资源直接托管。
- `api/[...path].js`：把 `/api/*` 请求交给 `server.js` 处理。
- `server.js`：提供实时比分、体育新闻、预测投票和本地开发静态服务。
- `data.js`、`squad-data.js`：前端静态数据源。

## Vercel 环境变量

可选：

```env
API_FOOTBALL_KEY=你的 API-Football Key
```

未配置时，实时比分接口会返回“等待开赛”的空状态，页面仍可正常访问。

## 本地运行

```bash
npm start
```

默认访问：

```text
http://localhost:4173/
```

## 上线前检查

```bash
npm test
```

也可以直接检查核心脚本：

```bash
node --check server.js
node --check app.js
node --check portal.js
node --check team.js
```
