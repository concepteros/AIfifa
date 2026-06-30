# 特征嵌套 Bug 诊断

## 症状

所有预测概率接近均匀分布（~33%/33%/33%），特征全部为 0。

## 根因

`build_match_features()` 返回双层嵌套结构：
```python
{
  "league": "...",
  "date": "...",
  "match": {...},
  "features": {           # ← 实际特征在这里
    "home_xg_for_avg": 1.04,
    ...
  }
}
```

但 `predict_match()` 内部做了第二次提取：
```python
features = feature_payload.get("features", {})  # 默认 {}
```

## 修复（两处）

### 1. bot_scanner.py — 传内层
```python
# 错误
prediction = predict_match(features, odds=...)

# 正确
prediction = predict_match(features["features"], odds=...)
```

### 2. prediction.py — 兼容双层
```python
# 旧
features = feature_payload.get("features", {})

# 新（兼容两层）
features = feature_payload.get("features", feature_payload)
```

这样无论调用方传外层还是内层，都能正确读取。

## 验证

```python
feat = result['features']['features']
assert feat.get('home_xg_for_avg', 0) > 0, "特征仍为 0！"
```
