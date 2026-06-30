"""
Predict.fun on-chain trading module.
Full flow: swap USDC→USDT → approve USDT → build + sign order → submit on-chain.

Uses predict-sdk for order building/signing and web3 for chain interaction.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Literal

from dotenv import load_dotenv
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from predict_sdk import (
    OrderBuilder,
    BuildOrderInput,
    OrderBuilderOptions,
    Side,
    ChainId,
    SignatureType,
)

# ── Constants ──────────────────────────────────────────────────────
BSC_RPC = "https://bsc-dataseed.binance.org"

# BSC token addresses
USDC_ADDRESS = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"  # 18 decimals
USDT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"  # 18 decimals
# PancakeSwap V2 Router
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

# Minimal ERC20 ABI
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]

# PancakeSwap Router minimal ABI
ROUTER_ABI = [
    {"inputs": [
        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
        {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
        {"internalType": "address[]", "name": "path", "type": "address[]"},
        {"internalType": "address", "name": "to", "type": "address"},
        {"internalType": "uint256", "name": "deadline", "type": "uint256"},
    ], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "type": "function"},
    {"inputs": [
        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
        {"internalType": "address[]", "name": "path", "type": "address[]"},
    ], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
]


@dataclass
class TradeConfig:
    """Configuration for a Predict.fun trade."""
    private_key: str
    wallet_address: str
    market_id: int | str
    token_id: str           # onChainId of the outcome to buy
    side: str               # "buy" or "sell"
    amount_usdt: float      # how much USDT to spend
    price_limit: float      # max price willing to pay (0.0-1.0)
    fee_rate_bps: int = 0
    slippage_bps: int = 100  # 1% default slippage
    dry_run: bool = True


@dataclass
class TradeResult:
    success: bool
    tx_hash: str = ""
    order_hash: str = ""
    error: str = ""
    details: str = ""


class PredictFunTrader:
    """Handles the full on-chain trading lifecycle for Predict.fun."""

    def __init__(self, config: TradeConfig):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(BSC_RPC))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Derive account
        self.account: LocalAccount = Account.from_key(config.private_key)
        self.address = self.w3.to_checksum_address(config.wallet_address)

        # SDK OrderBuilder
        self.builder = OrderBuilder.make(
            chain_id=ChainId.BNB_MAINNET,
            signer=self.account,
        )

    @property
    def usdc(self):
        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI,
        )

    @property
    def usdt(self):
        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(USDT_ADDRESS),
            abi=ERC20_ABI,
        )

    @property
    def router(self):
        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(PANCAKE_ROUTER),
            abi=ROUTER_ABI,
        )

    # ── Balance & Allowances ───────────────────────────────────────

    def get_balances(self) -> dict:
        """Return BNB, USDC, USDT balances."""
        bnb = self.w3.eth.get_balance(self.address)
        usdc_bal = self.usdc.functions.balanceOf(self.address).call()
        usdt_bal = self.usdt.functions.balanceOf(self.address).call()
        return {
            "bnb": float(self.w3.from_wei(bnb, "ether")),
            "usdc": usdc_bal / 1e18,
            "usdt": usdt_bal / 1e18,
        }

    def get_usdt_allowance(self) -> float:
        """USDT allowance for CTF Exchange."""
        exchange = self.w3.to_checksum_address(
            "0x8BC070BEdAB741406F4B1Eb65A72bee27894B689"
        )
        return self.usdt.functions.allowance(self.address, exchange).call() / 1e18

    def get_usdc_allowance_for_router(self) -> float:
        """USDC allowance for PancakeSwap Router."""
        router_addr = self.w3.to_checksum_address(PANCAKE_ROUTER)
        return self.usdc.functions.allowance(self.address, router_addr).call() / 1e18

    # ── Swap USDC → USDT ──────────────────────────────────────────

    def swap_usdc_to_usdt(self, amount_usdc: float) -> TradeResult:
        """
        Swap USDC for USDT via PancakeSwap V2.
        Returns TradeResult with tx_hash on success.
        """
        if self.config.dry_run:
            return TradeResult(
                success=True,
                details=f"[DRY RUN] Would swap {amount_usdc} USDC → USDT",
            )

        amount_wei = int(Decimal(str(amount_usdc)) * Decimal(10**18))

        # Check balance with 0.1% buffer for rounding
        bal = self.usdc.functions.balanceOf(self.address).call()
        if bal < amount_wei:
            # Try with exact balance minus safety margin
            safe_wei = int(bal * 0.999)
            if safe_wei <= 0:
                return TradeResult(
                    success=False,
                    error=f"Insufficient USDC: have {bal/1e18:.6f}, need ~{amount_usdc:.6f}"
                )
            amount_wei = safe_wei

        # Approve router if needed
        router_addr = self.w3.to_checksum_address(PANCAKE_ROUTER)
        allowance = self.usdc.functions.allowance(self.address, router_addr).call()
        if allowance < amount_wei:
            print(f"  Approving PancakeSwap Router for {amount_usdc} USDC...")
            tx = self.usdc.functions.approve(router_addr, amount_wei).build_transaction({
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"  USDC approved: {tx_hash.hex()}")

        # Get expected output
        path = [self.w3.to_checksum_address(USDC_ADDRESS), self.w3.to_checksum_address(USDT_ADDRESS)]
        amounts_out = self.router.functions.getAmountsOut(amount_wei, path).call()
        min_out = int(amounts_out[1] * 0.99)  # 1% slippage

        # Execute swap
        deadline = int(time.time()) + 300  # 5 min
        tx = self.router.functions.swapExactTokensForTokens(
            amount_wei,
            min_out,
            path,
            self.address,
            deadline,
        ).build_transaction({
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "gas": 250000,
            "gasPrice": self.w3.eth.gas_price,
        })

        if self.config.dry_run:
            return TradeResult(
                success=True,
                details=f"[DRY RUN] Would swap {amount_usdc} USDC → ~{amounts_out[1]/1e18:.6f} USDT",
            )

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return TradeResult(
            success=receipt["status"] == 1,
            tx_hash=tx_hash.hex(),
            details=f"Swapped {amount_usdc} USDC → ~{amounts_out[1]/1e18:.6f} USDT | tx: {tx_hash.hex()[:16]}...",
        )

    # ── Approve USDT for Exchange ──────────────────────────────────

    def approve_usdt_for_exchange(self, amount: float | None = None) -> TradeResult:
        """
        Approve USDT spending for CTF Exchange.
        If amount is None, approve MAX_UINT256.
        """
        exchange = self.w3.to_checksum_address(
            "0x8BC070BEdAB741406F4B1Eb65A72bee27894B689"
        )

        if amount is None:
            amount_wei = 2**256 - 1  # max approval
        else:
            amount_wei = int(Decimal(str(amount)) * Decimal(10**18))

        current = self.usdt.functions.allowance(self.address, exchange).call()
        if current >= amount_wei and amount_wei != 2**256 - 1:
            return TradeResult(success=True, details=f"Already approved: {current/1e18:.2f} USDT")

        if self.config.dry_run:
            return TradeResult(
                success=True,
                details=f"[DRY RUN] Would approve {amount_wei/1e18 if amount else 'MAX'} USDT for Exchange",
            )

        tx = self.usdt.functions.approve(exchange, amount_wei).build_transaction({
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "gas": 100000,
            "gasPrice": self.w3.eth.gas_price,
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return TradeResult(
            success=receipt["status"] == 1,
            tx_hash=tx_hash.hex(),
            details=f"Approved Exchange for USDT | tx: {tx_hash.hex()[:16]}...",
        )

    # ── Build & Sign Order ────────────────────────────────────────

    def build_order(self) -> tuple:
        """
        Build and sign an EIP-712 order using predict-sdk.
        Returns (Order, SignedOrder, EIP712TypedData).
        """
        # Calculate amounts
        price = Decimal(str(self.config.price_limit))
        spend = Decimal(str(self.config.amount_usdt))
        shares = spend / price  # shares = USDT / price

        maker_amount = str(int(spend * Decimal(10**18)))  # USDT in wei (18 dec)
        taker_amount = str(int(shares * Decimal(10**18)))  # shares in wei (18 dec)

        # For LIMIT order: maker_amount = USDT, taker_amount = shares
        # Side.BUY = we pay USDT (maker_amount) to receive shares (taker_amount)
        order_input = BuildOrderInput(
            side=Side.BUY,
            token_id=self.config.token_id,
            maker_amount=maker_amount,
            taker_amount=taker_amount,
            fee_rate_bps=str(self.config.fee_rate_bps),
            signature_type=SignatureType.EOA,
        )

        order = self.builder.build_order("LIMIT", order_input)
        typed_data = self.builder.build_typed_data(
            order, is_neg_risk=False, is_yield_bearing=False
        )
        signed = self.builder.sign_typed_data_order(typed_data)

        return order, signed, typed_data

    # ── Submit Order On-Chain ─────────────────────────────────────

    def submit_order(self, order, signed) -> TradeResult:
        """
        Submit signed order to the CTF Exchange via fillOrder().
        The order is self-filled (taker fills own maker order).
        """
        from predict_sdk.constants import ADDRESSES_BY_CHAIN_ID, ChainId as SDKChain
        from predict_sdk.abis import CTF_EXCHANGE_ABI

        exchange_addr = ADDRESSES_BY_CHAIN_ID[SDKChain.BNB_MAINNET].CTF_EXCHANGE
        exchange = self.w3.eth.contract(
            address=self.w3.to_checksum_address(exchange_addr),
            abi=CTF_EXCHANGE_ABI,
        )

        # Build order struct for contract call (must be list for web3.py struct encoding)
        # Order struct: (salt, maker, signer, taker, tokenId, makerAmount, takerAmount, expiration, nonce, feeRateBps, side, signatureType, signature)
        order_struct = [
            int(order.salt),
            order.maker,
            order.signer,
            order.taker,
            int(order.token_id),
            int(order.maker_amount),
            int(order.taker_amount),
            int(order.expiration),
            int(order.nonce),
            int(order.fee_rate_bps),
            int(order.side),
            int(order.signature_type),
            bytes.fromhex(signed.signature[2:] if signed.signature.startswith("0x") else signed.signature),
        ]

        fill_amount = int(order.maker_amount)  # fill entire order

        if self.config.dry_run:
            # Compute order hash for verification — struct must be passed as single tuple arg
            order_hash = exchange.functions.hashOrder(order_struct).call()
            return TradeResult(
                success=True,
                order_hash=order_hash.hex(),
                details=(
                    f"[DRY RUN] Order built & signed\n"
                    f"  Market: {self.config.market_id}\n"
                    f"  Side: BUY Over 2.5\n"
                    f"  Price: {self.config.price_limit}\n"
                    f"  Spend: {self.config.amount_usdt} USDT\n"
                    f"  Shares: ~{float(order.taker_amount)/1e18:.4f}\n"
                    f"  Fee: {self.config.fee_rate_bps} bps\n"
                    f"  Order hash: {order_hash.hex()[:20]}..."
                ),
            )

        tx = exchange.functions.fillOrder(order_struct, fill_amount).build_transaction({
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "gas": 500000,
            "gasPrice": self.w3.eth.gas_price,
        })
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return TradeResult(
            success=receipt["status"] == 1,
            tx_hash=tx_hash.hex(),
            details=f"Order filled | tx: {tx_hash.hex()[:20]}...",
        )

    # ── Full Flow ─────────────────────────────────────────────────

    def execute(self) -> TradeResult:
        """Execute the full trading flow."""
        print("═══ Predict.fun Trade ═══")
        print(f"Market: {self.config.market_id}")
        print(f"Action: BUY Over 2.5 @ ≤{self.config.price_limit}")
        print(f"Amount: {self.config.amount_usdt} USDT")
        print(f"Mode: {'DRY RUN' if self.config.dry_run else 'LIVE'}")
        print()

        # 1. Check balances
        balances = self.get_balances()
        print(f"Balances: BNB={balances['bnb']:.4f}, USDC={balances['usdc']:.4f}, USDT={balances['usdt']:.4f}")

        # 2. Swap USDC → USDT if needed
        need = self.config.amount_usdt * 1.01  # 1% buffer
        if balances["usdt"] < need:
            # Use all available USDC up to what's needed, minus 0.1% safety margin
            max_swap = min(balances["usdc"] * 0.999, need - balances["usdt"])
            if max_swap <= 0.0001:
                return TradeResult(success=False, error=f"Need {need:.4f} USDT, have {balances['usdt']:.4f} USDT and {balances['usdc']:.4f} USDC")
            print(f"\n→ Step 1: Swap {max_swap:.4f} USDC → USDT")
            result = self.swap_usdc_to_usdt(max_swap)
            if not result.success:
                return result
            print(f"  {result.details}")
        else:
            print(f"\n→ Step 1: USDT balance sufficient ({balances['usdt']:.4f})")

        # 3. Approve USDT for Exchange
        print(f"\n→ Step 2: Check USDT approval for Exchange")
        allowance = self.get_usdt_allowance()
        if allowance < self.config.amount_usdt:
            print(f"  Current allowance: {allowance:.4f}, approving...")
            result = self.approve_usdt_for_exchange()
            if not result.success:
                return result
            print(f"  {result.details}")
        else:
            print(f"  Already approved: {allowance:.4f} USDT")

        # 4. Build & sign order
        print(f"\n→ Step 3: Build & sign order")
        order, signed, typed_data = self.build_order()
        print(f"  Order salt: {order.salt}")
        print(f"  Maker: {order.maker[:16]}...")
        print(f"  makerAmount: {int(order.maker_amount)/1e18:.6f} USDT")
        print(f"  takerAmount: {int(order.taker_amount)/1e18:.6f} shares")
        print(f"  Expiration: {order.expiration}")
        print(f"  Signed: {signed.signature[:20]}...")

        # 5. Submit
        print(f"\n→ Step 4: Submit order on-chain")
        result = self.submit_order(order, signed)
        print(f"  {result.details}")

        return result


# ── CLI ────────────────────────────────────────────────────────────

def main():
    load_dotenv()

    private_key = os.getenv("PREDICTFUN_WALLET_PRIVATE_KEY")
    wallet = os.getenv("PREDICTFUN_WALLET_ADDRESS")

    if not private_key or not wallet:
        print("ERROR: Set PREDICTFUN_WALLET_PRIVATE_KEY and PREDICTFUN_WALLET_ADDRESS in .env")
        return

    # Over 2.5 market (Spain vs Saudi Arabia)
    config = TradeConfig(
        private_key=private_key,
        wallet_address=wallet,
        market_id=376983,
        token_id="49516906126729542533748342594721723546560009285100531762101622758288875127029",  # Over
        side="buy",
        amount_usdt=1.0,       # $1 test
        price_limit=0.75,      # current ask
        fee_rate_bps=200,      # from API
        dry_run=True,           # dry run first!
    )

    trader = PredictFunTrader(config)
    result = trader.execute()

    print(f"\n═══ Result: {'✅ SUCCESS' if result.success else '❌ FAILED'} ═══")
    if result.tx_hash:
        print(f"TX: {result.tx_hash}")
    if result.order_hash:
        print(f"Order hash: {result.order_hash}")


if __name__ == "__main__":
    main()
