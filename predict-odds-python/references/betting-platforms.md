# 下注平台对比

截至 2026-06-21，足球博彩 bot 可用的平台。

## 对比表

| 维度 | Polymarket | Predict.fun | The Odds API |
|------|-----------|-------------|--------------|
| 单场盘口 | ✅ Moneyline/Spread/Total | ✅ 世界杯单场 (slug直查) | N/A (数据源) |
| 程序化交易 | ❌ 需 EIP-712 钱包 | ✅ predict-sdk (链上) | N/A |
| 交易链 | Polygon | **BNB Chain** (chainId 56) | - |
| 当前可用 | 浏览器手动下注 | SDK链上下单 (需BNB链USDC) | 赔率数据 |
| 钱包 | 未配置 | 0x9E47a210...503eaD | - |
| 钱包链 | - | Polygon / BNB (同地址) | - |

## ⚠️ Predict.fun 重要变更 (2026-06-21)

- **REST API `POST /v1/orders` 已确认不可用** — 不是格式问题，REST API 纯读数据
- **下单必须走链上** — `predict-sdk` → BNB Chain CTF Exchange 合约
- **BNB 链独有** — SDK 只支持 ChainId.BNB_MAINNET (56) / BNB_TESTNET (97)
- **同私钥跨链可用** — Polygon 钱包 `0x9E47...` 在 BNB 链地址相同
- **需 BNB 链 USDC** — 当前 20 USDC 在 Polygon，需 bridge 到 BNB 链
- **需少量 BNB 做 gas** — ~0.001 BNB 每笔交易

## Predict.fun 下单流程 (SDK)

```bash
pip install predict-sdk
```

```python
from predict_sdk import OrderBuilder, BuildOrderInput, Side, ChainId

order = BuildOrderInput(
    side=Side.BUY,
    token_id="<from outcomes[].onChainId>",
    maker_amount="5",       # USDC
    taker_amount="595",     # shares
    fee_rate_bps=200,       # from market detail
)

builder = OrderBuilder.make(chain_id=ChainId.BNB_MAINNET, signer=pk)
signed = builder.build(order)
# → 提交到 CTF Exchange 合约
```

详见 `predict-fun` 技能 `references/predict-sdk-usage.md`。

## Polymarket CLOB 备选

- Gamma API 可用: `GET gamma-api.polymarket.com/events?slug=fifwc-...`
- 需 EIP-712 签名 + API key
- Token ID 已获取（Tunisia vs Japan 等）
