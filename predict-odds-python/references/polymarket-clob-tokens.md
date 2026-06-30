# Polymarket CLOB — Tunisia vs Japan (2026-06-21)

## Event
- Slug: `fifwc-tun-jpn-2026-06-21`
- Event ID: `351750`
- Gamma API: `GET https://gamma-api.polymarket.com/events?slug=fifwc-tun-jpn-2026-06-21`

## CLOB Token IDs

| Market | Outcome | Token ID |
|--------|---------|----------|
| Japan win | Yes | `91234906493805354217250440222911012200186057450151286874925972448339630680686` |
| Japan win | No | `45846181464354825959264722709108649428761038520429535399562488658314436133090` |
| Tunisia win | Yes | `62516949205730668430138255140150438665483187962069999240136080804116109915287` |
| Tunisia win | No | `32305022863642881983854568910858512907521560231740993713994899203087286530811` |
| Draw | Yes | `50275383633644719253389412495747849486228904621414058936414415835809185820411` |
| Draw | No | `5693157367968176695938919502623564101036527678755862600029916323784435468280` |

## Live prices (in-play, Japan 1-0, 7')
- Japan: 84¢
- Draw: 13¢
- Tunisia: 3.9¢

## CLOB Order
```
POST https://clob.polymarket.com/order
Body: {tokenID, price, size, side: "BUY"/"SELL"}
Auth: EIP-712 signature + Polymarket API key
```

## Prerequisites
1. Polymarket API key from https://polymarket.com/account
2. USDC deposited to CLOB exchange contract
3. EIP-712 typed signature for each order
