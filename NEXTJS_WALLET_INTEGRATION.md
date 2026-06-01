# Next.js Phantom + OKX Wallet Integration

This template targets Next.js App Router. It uses:

- Solana Wallet Adapter for Phantom and OKX through WalletConnect.
- Wagmi for Base wallets, including injected Phantom and OKX through WalletConnect.
- Supabase SSR for the existing authenticated user session.
- Server-side signature verification before binding a wallet.
- Server-side transaction verification before upgrading a subscription.

Do not place a service-role key, private key, or seed phrase in a `NEXT_PUBLIC_*` variable.

## 1. Install

Remove the broad wallet bundle when possible. It pulls many adapters that the app does not use.

```bash
npm uninstall @solana/wallet-adapter-wallets
npm install \
  @solana/web3.js \
  @solana/spl-token \
  @solana/wallet-adapter-base \
  @solana/wallet-adapter-react \
  @solana/wallet-adapter-react-ui \
  @solana/wallet-adapter-phantom \
  @solana/wallet-adapter-walletconnect \
  @supabase/ssr \
  @supabase/supabase-js \
  @tanstack/react-query \
  bs58 \
  tweetnacl \
  viem \
  wagmi
```

## 2. File Structure

```text
app/
  api/
    auth/wallet-login/route.ts
    payments/confirm/route.ts
  layout.tsx
components/
  connect-wallet-button.tsx
  premium-payment-button.tsx
lib/
  constants.ts
  supabase/
    admin.ts
    server.ts
providers/
  wallet-provider.tsx
supabase/
  migrations/
    001_wallets_and_payments.sql
.env.local
```

## 3. Environment Variables

Create `.env.local`. Replace both recipient placeholders with addresses that you control. Test with Base Sepolia and Solana devnet before changing the production variables.

```dotenv
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=replace_me
NEXT_PUBLIC_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
NEXT_PUBLIC_BASE_RPC_URL=https://mainnet.base.org

NEXT_PUBLIC_SOLANA_USDC_RECIPIENT=replace_with_solana_wallet
NEXT_PUBLIC_BASE_USDC_RECIPIENT=0xreplace_with_base_wallet

NEXT_PUBLIC_SUPABASE_URL=https://replace_me.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=replace_me
SUPABASE_SERVICE_ROLE_KEY=replace_me_server_only
```

## 4. Database Migration

Create `supabase/migrations/001_wallets_and_payments.sql`.

```sql
create table if not exists public.wallets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  chain text not null check (chain in ('solana', 'base')),
  address text not null,
  created_at timestamptz not null default now(),
  unique (chain, address),
  unique (user_id, chain, address)
);

create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  chain text not null check (chain in ('solana', 'base')),
  tx_hash text not null,
  wallet_address text not null,
  amount_units numeric not null,
  status text not null check (status in ('confirmed')),
  created_at timestamptz not null default now(),
  unique (chain, tx_hash)
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  subscription_status text not null default 'free'
    check (subscription_status in ('free', 'premium')),
  updated_at timestamptz not null default now()
);

alter table public.wallets enable row level security;
alter table public.payments enable row level security;
alter table public.profiles enable row level security;

create policy "read own wallets" on public.wallets
  for select to authenticated using (auth.uid() = user_id);

create policy "read own payments" on public.payments
  for select to authenticated using (auth.uid() = user_id);

create policy "read own profile" on public.profiles
  for select to authenticated using (auth.uid() = id);
```

Writes happen through server-only API routes using the service role client.

## 5. Shared Constants

Create `lib/constants.ts`.

```ts
import { base } from "viem/chains";

export const PREMIUM_PRICE_USDC = 19_900_000n;
export const USDC_DECIMALS = 6;

export const BASE_CHAIN_ID = base.id;
export const BASE_USDC_ADDRESS =
  "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" as const;
export const SOLANA_USDC_MINT =
  "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";

export const BASE_USDC_RECIPIENT =
  process.env.NEXT_PUBLIC_BASE_USDC_RECIPIENT as `0x${string}`;
export const SOLANA_USDC_RECIPIENT =
  process.env.NEXT_PUBLIC_SOLANA_USDC_RECIPIENT as string;

export const erc20TransferAbi = [
  {
    type: "function",
    name: "transfer",
    stateMutability: "nonpayable",
    inputs: [
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
  {
    type: "event",
    name: "Transfer",
    inputs: [
      { indexed: true, name: "from", type: "address" },
      { indexed: true, name: "to", type: "address" },
      { indexed: false, name: "value", type: "uint256" },
    ],
  },
] as const;
```

## 6. Supabase Server Clients

Create `lib/supabase/server.ts`.

```ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createSupabaseServerClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (items) => {
          try {
            items.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Server Components cannot always write cookies.
          }
        },
      },
    },
  );
}
```

Create `lib/supabase/admin.ts`.

```ts
import { createClient } from "@supabase/supabase-js";

export function createSupabaseAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    },
  );
}
```

## 7. Wallet Provider

Create `providers/wallet-provider.tsx`.

```tsx
"use client";

import { useMemo, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConnectionProvider, WalletProvider as SolanaWalletProvider } from "@solana/wallet-adapter-react";
import { WalletModalProvider } from "@solana/wallet-adapter-react-ui";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";
import { WalletConnectWalletAdapter } from "@solana/wallet-adapter-walletconnect";
import { WalletAdapterNetwork } from "@solana/wallet-adapter-base";
import { WagmiProvider, createConfig, http } from "wagmi";
import { base } from "wagmi/chains";
import { injected, walletConnect } from "wagmi/connectors";

import "@solana/wallet-adapter-react-ui/styles.css";

const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID!;

const wagmiConfig = createConfig({
  chains: [base],
  connectors: [
    injected({ shimDisconnect: true }),
    walletConnect({
      projectId,
      metadata: {
        name: "FIFA 2026",
        description: "FIFA 2026 premium subscription",
        url: typeof window === "undefined" ? "https://example.com" : window.location.origin,
        icons: [],
      },
      showQrModal: true,
    }),
  ],
  transports: {
    [base.id]: http(process.env.NEXT_PUBLIC_BASE_RPC_URL),
  },
});

export function WalletProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const solanaEndpoint = process.env.NEXT_PUBLIC_SOLANA_RPC_URL!;

  const solanaWallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      new WalletConnectWalletAdapter({
        network: WalletAdapterNetwork.Mainnet,
        options: {
          projectId,
          metadata: {
            name: "FIFA 2026",
            description: "FIFA 2026 premium subscription",
            url: typeof window === "undefined" ? "https://example.com" : window.location.origin,
            icons: [],
          },
        },
      }),
    ],
    [],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <WagmiProvider config={wagmiConfig}>
        <ConnectionProvider endpoint={solanaEndpoint}>
          <SolanaWalletProvider wallets={solanaWallets} autoConnect>
            <WalletModalProvider>{children}</WalletModalProvider>
          </SolanaWalletProvider>
        </ConnectionProvider>
      </WagmiProvider>
    </QueryClientProvider>
  );
}
```

WalletConnect displays compatible wallets such as OKX. The injected connector also supports installed EVM wallets, including Phantom and OKX extensions.

## 8. Root Layout

Update `app/layout.tsx`.

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { WalletProvider } from "@/providers/wallet-provider";

export const metadata: Metadata = {
  title: "FIFA 2026",
  description: "World Cup odds and premium insights",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <WalletProvider>{children}</WalletProvider>
      </body>
    </html>
  );
}
```

## 9. Wallet Login API

Create `app/api/auth/wallet-login/route.ts`.

```ts
import { randomBytes } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import bs58 from "bs58";
import nacl from "tweetnacl";
import { verifyMessage } from "viem";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

const COOKIE_NAME = "wallet-login-nonce";

function loginMessage(nonce: string) {
  return `FIFA 2026 wallet login\nNonce: ${nonce}`;
}

export async function GET() {
  const nonce = randomBytes(24).toString("hex");
  const response = NextResponse.json({ message: loginMessage(nonce) });
  response.cookies.set(COOKIE_NAME, nonce, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 300,
    path: "/",
  });
  return response;
}

export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Sign in to Supabase first" }, { status: 401 });
  }

  const nonce = request.cookies.get(COOKIE_NAME)?.value;
  const body = (await request.json()) as {
    chain: "solana" | "base";
    address: string;
    signature: string;
  };

  if (!nonce || !body.address || !body.signature) {
    return NextResponse.json({ error: "Invalid login request" }, { status: 400 });
  }

  const message = loginMessage(nonce);
  let verified = false;

  if (body.chain === "solana") {
    verified = nacl.sign.detached.verify(
      new TextEncoder().encode(message),
      bs58.decode(body.signature),
      bs58.decode(body.address),
    );
  }

  if (body.chain === "base") {
    verified = await verifyMessage({
      address: body.address as `0x${string}`,
      message,
      signature: body.signature as `0x${string}`,
    });
  }

  if (!verified) {
    return NextResponse.json({ error: "Invalid wallet signature" }, { status: 401 });
  }

  const admin = createSupabaseAdminClient();
  const { data: existing } = await admin
    .from("wallets")
    .select("user_id")
    .eq("chain", body.chain)
    .ilike("address", body.address)
    .maybeSingle();

  if (existing && existing.user_id !== user.id) {
    return NextResponse.json({ error: "Wallet is already linked" }, { status: 409 });
  }

  if (!existing) {
    const { error } = await admin.from("wallets").insert({
      user_id: user.id,
      chain: body.chain,
      address: body.address,
    });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 409 });
    }
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.delete(COOKIE_NAME);
  return response;
}
```

This route binds a wallet to an existing Supabase-authenticated account. For wallet-only authentication, add a dedicated SIWS/SIWE auth flow and issue an application session after verification.

## 10. Connect Wallet Button

Create `components/connect-wallet-button.tsx`.

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import bs58 from "bs58";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import { useWallet } from "@solana/wallet-adapter-react";
import { useAccount, useConnect, useDisconnect, useSignMessage } from "wagmi";

function short(address?: string) {
  return address ? `${address.slice(0, 5)}...${address.slice(-4)}` : "";
}

async function bindWallet(chain: "solana" | "base", address: string, signature: string) {
  const response = await fetch("/api/auth/wallet-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chain, address, signature }),
  });
  if (!response.ok) throw new Error((await response.json()).error);
}

export function ConnectWalletButton() {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const solana = useWallet();
  const evm = useAccount();
  const { connectors, connect, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const { signMessageAsync } = useSignMessage();

  const getChallenge = useCallback(async () => {
    const response = await fetch("/api/auth/wallet-login");
    return (await response.json()).message as string;
  }, []);

  const bindSolana = useCallback(async () => {
    if (!solana.publicKey || !solana.signMessage) return;
    setBusy(true);
    try {
      const challenge = await getChallenge();
      const signature = await solana.signMessage(new TextEncoder().encode(challenge));
      await bindWallet("solana", solana.publicKey.toBase58(), bs58.encode(signature));
      setMessage("Solana wallet linked");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Wallet link failed");
    } finally {
      setBusy(false);
    }
  }, [getChallenge, solana.publicKey, solana.signMessage]);

  const bindBase = useCallback(async () => {
    if (!evm.address) return;
    setBusy(true);
    try {
      const challenge = await getChallenge();
      const signature = await signMessageAsync({ message: challenge });
      await bindWallet("base", evm.address, signature);
      setMessage("Base wallet linked");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Wallet link failed");
    } finally {
      setBusy(false);
    }
  }, [evm.address, getChallenge, signMessageAsync]);

  useEffect(() => {
    if (solana.connected && solana.publicKey) void bindSolana();
  }, [bindSolana, solana.connected, solana.publicKey]);

  useEffect(() => {
    if (evm.isConnected && evm.address) void bindBase();
  }, [bindBase, evm.address, evm.isConnected]);

  const injected = connectors.find((item) => item.id === "injected");
  const wc = connectors.find((item) => item.id === "walletConnect");

  return (
    <div className="flex flex-wrap items-center gap-3">
      <WalletMultiButton className="!h-10 !rounded-md !bg-emerald-700 !px-4 hover:!bg-emerald-800" />

      {!evm.isConnected ? (
        <>
          <button
            className="h-10 rounded-md bg-neutral-900 px-4 text-sm font-semibold text-white"
            disabled={!injected || isPending}
            onClick={() => injected && connect({ connector: injected })}
          >
            Connect Base wallet
          </button>
          <button
            className="h-10 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold"
            disabled={!wc || isPending}
            onClick={() => wc && connect({ connector: wc })}
          >
            Connect OKX with WalletConnect
          </button>
        </>
      ) : (
        <button
          className="h-10 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold"
          onClick={() => disconnect()}
        >
          Base: {short(evm.address)} · Disconnect
        </button>
      )}

      {(busy || message) && (
        <span className="text-sm text-neutral-600">{busy ? "Verifying wallet..." : message}</span>
      )}
    </div>
  );
}
```

## 11. Premium Payment Button

Create `components/premium-payment-button.tsx`.

```tsx
"use client";

import { useState } from "react";
import { useWallet, useConnection } from "@solana/wallet-adapter-react";
import {
  createAssociatedTokenAccountInstruction,
  createTransferCheckedInstruction,
  getAssociatedTokenAddress,
} from "@solana/spl-token";
import { PublicKey, Transaction } from "@solana/web3.js";
import { useAccount, useChainId, usePublicClient, useSwitchChain, useWriteContract } from "wagmi";
import { base } from "wagmi/chains";
import {
  BASE_USDC_ADDRESS,
  BASE_USDC_RECIPIENT,
  PREMIUM_PRICE_USDC,
  SOLANA_USDC_MINT,
  SOLANA_USDC_RECIPIENT,
  USDC_DECIMALS,
  erc20TransferAbi,
} from "@/lib/constants";

async function confirmPayment(chain: "solana" | "base", txHash: string) {
  const response = await fetch("/api/payments/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chain, txHash }),
  });
  if (!response.ok) throw new Error((await response.json()).error);
}

export function PremiumPaymentButton() {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const solana = useWallet();
  const { connection } = useConnection();
  const evm = useAccount();
  const chainId = useChainId();
  const baseClient = usePublicClient({ chainId: base.id });
  const { switchChainAsync } = useSwitchChain();
  const { writeContractAsync } = useWriteContract();

  async function paySolana() {
    if (!solana.publicKey || !solana.sendTransaction) throw new Error("Connect Solana wallet first");
    const mint = new PublicKey(SOLANA_USDC_MINT);
    const recipient = new PublicKey(SOLANA_USDC_RECIPIENT);
    const senderAta = await getAssociatedTokenAddress(mint, solana.publicKey);
    const recipientAta = await getAssociatedTokenAddress(mint, recipient);
    const transaction = new Transaction();

    if (!(await connection.getAccountInfo(recipientAta))) {
      transaction.add(
        createAssociatedTokenAccountInstruction(
          solana.publicKey,
          recipientAta,
          recipient,
          mint,
        ),
      );
    }

    transaction.add(
      createTransferCheckedInstruction(
        senderAta,
        mint,
        recipientAta,
        solana.publicKey,
        PREMIUM_PRICE_USDC,
        USDC_DECIMALS,
      ),
    );

    const signature = await solana.sendTransaction(transaction, connection);
    await connection.confirmTransaction(signature, "confirmed");
    await confirmPayment("solana", signature);
  }

  async function payBase() {
    if (!evm.address) throw new Error("Connect Base wallet first");
    if (chainId !== base.id) await switchChainAsync({ chainId: base.id });

    const hash = await writeContractAsync({
      address: BASE_USDC_ADDRESS,
      abi: erc20TransferAbi,
      functionName: "transfer",
      args: [BASE_USDC_RECIPIENT, PREMIUM_PRICE_USDC],
      chainId: base.id,
    });

    if (!baseClient) throw new Error("Base RPC is unavailable");
    await baseClient.waitForTransactionReceipt({ hash });
    await confirmPayment("base", hash);
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      setMessage("Payment confirmed. Premium is active.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Payment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <p className="text-sm font-semibold text-emerald-700">Premium</p>
        <h3 className="text-xl font-bold">Unlock for 19.9 USDC</h3>
      </div>
      <div className="flex flex-wrap gap-3">
        <button
          className="h-10 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white disabled:opacity-50"
          disabled={busy}
          onClick={() => void run(paySolana)}
        >
          Pay on Solana
        </button>
        <button
          className="h-10 rounded-md bg-blue-700 px-4 text-sm font-semibold text-white disabled:opacity-50"
          disabled={busy}
          onClick={() => void run(payBase)}
        >
          Pay on Base
        </button>
      </div>
      {message && <p className="mt-3 text-sm text-neutral-600">{message}</p>}
    </div>
  );
}
```

## 12. Payment Confirmation API

Create `app/api/payments/confirm/route.ts`.

```ts
import { NextRequest, NextResponse } from "next/server";
import { Connection, PublicKey } from "@solana/web3.js";
import { createPublicClient, decodeEventLog, http, isAddressEqual } from "viem";
import { base } from "viem/chains";
import {
  BASE_USDC_ADDRESS,
  BASE_USDC_RECIPIENT,
  PREMIUM_PRICE_USDC,
  SOLANA_USDC_MINT,
  SOLANA_USDC_RECIPIENT,
  erc20TransferAbi,
} from "@/lib/constants";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

async function verifySolana(txHash: string) {
  const connection = new Connection(process.env.NEXT_PUBLIC_SOLANA_RPC_URL!, "confirmed");
  const transaction = await connection.getParsedTransaction(txHash, {
    commitment: "confirmed",
    maxSupportedTransactionVersion: 0,
  });
  if (!transaction || transaction.meta?.err) throw new Error("Solana transaction is not confirmed");

  const recipient = new PublicKey(SOLANA_USDC_RECIPIENT).toBase58();
  const deltas = (transaction.meta?.postTokenBalances ?? []).map((post) => {
    const pre = transaction.meta?.preTokenBalances?.find((item) => item.accountIndex === post.accountIndex);
    return {
      mint: post.mint,
      owner: post.owner,
      delta: BigInt(post.uiTokenAmount.amount) - BigInt(pre?.uiTokenAmount.amount ?? "0"),
    };
  });

  const payment = deltas.find(
    (item) =>
      item.mint === SOLANA_USDC_MINT &&
      item.owner === recipient &&
      item.delta >= PREMIUM_PRICE_USDC,
  );
  if (!payment) throw new Error("Expected Solana USDC transfer was not found");

  const signer = transaction.transaction.message.accountKeys.find((item) => item.signer)?.pubkey.toBase58();
  if (!signer) throw new Error("Solana signer was not found");
  return signer;
}

async function verifyBase(txHash: `0x${string}`) {
  const client = createPublicClient({
    chain: base,
    transport: http(process.env.NEXT_PUBLIC_BASE_RPC_URL),
  });
  const receipt = await client.getTransactionReceipt({ hash: txHash });
  if (receipt.status !== "success") throw new Error("Base transaction failed");

  for (const log of receipt.logs) {
    if (!isAddressEqual(log.address, BASE_USDC_ADDRESS)) continue;
    try {
      const decoded = decodeEventLog({ abi: erc20TransferAbi, data: log.data, topics: log.topics });
      if (
        decoded.eventName === "Transfer" &&
        isAddressEqual(decoded.args.to, BASE_USDC_RECIPIENT) &&
        decoded.args.value >= PREMIUM_PRICE_USDC
      ) {
        return decoded.args.from;
      }
    } catch {
      // Ignore unrelated USDC logs.
    }
  }
  throw new Error("Expected Base USDC transfer was not found");
}

export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json()) as {
    chain: "solana" | "base";
    txHash: string;
  };
  if (!body.txHash || !["solana", "base"].includes(body.chain)) {
    return NextResponse.json({ error: "Invalid payment request" }, { status: 400 });
  }

  try {
    const walletAddress =
      body.chain === "solana"
        ? await verifySolana(body.txHash)
        : await verifyBase(body.txHash as `0x${string}`);

    const admin = createSupabaseAdminClient();
    const { data: linkedWallet } = await admin
      .from("wallets")
      .select("id")
      .eq("user_id", user.id)
      .eq("chain", body.chain)
      .ilike("address", walletAddress)
      .maybeSingle();

    if (!linkedWallet) throw new Error("Payment wallet is not linked to this account");

    const { error: paymentError } = await admin.from("payments").insert({
      user_id: user.id,
      chain: body.chain,
      tx_hash: body.txHash,
      wallet_address: walletAddress,
      amount_units: PREMIUM_PRICE_USDC.toString(),
      status: "confirmed",
    });
    if (paymentError?.code !== "23505" && paymentError) throw paymentError;

    const { error: profileError } = await admin.from("profiles").upsert({
      id: user.id,
      subscription_status: "premium",
      updated_at: new Date().toISOString(),
    });
    if (profileError) throw profileError;

    return NextResponse.json({ ok: true, subscriptionStatus: "premium" });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Payment verification failed" },
      { status: 400 },
    );
  }
}
```

## 13. Add Components To A Page

```tsx
import { ConnectWalletButton } from "@/components/connect-wallet-button";
import { PremiumPaymentButton } from "@/components/premium-payment-button";

export default function AccountPage() {
  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <ConnectWalletButton />
      <PremiumPaymentButton />
    </main>
  );
}
```

## 14. Production Checklist

1. Replace recipient environment variables with wallets that you control.
2. Start on Base Sepolia and Solana devnet with test tokens.
3. Add the production origin to the WalletConnect allowlist.
4. Confirm that the user is already authenticated with Supabase before wallet binding.
5. Keep `SUPABASE_SERVICE_ROLE_KEY` server-only.
6. Add rate limiting to both API routes.
7. Add CSRF protection if the app accepts cross-origin requests.
8. Add a payment expiry or invoice table if each payment should unlock only one purchase.
9. Review indirect dependency audit findings before deploying.

## 15. Official References

- Phantom React SDK: https://docs.phantom.com/sdks/react-sdk
- WalletConnect App SDK: https://docs.walletconnect.network/app-sdk/overview
- WalletConnect allowlist: https://docs.walletconnect.network/app-sdk/javascript/installation
- OKX wallet integration overview: https://web3.okx.com/onchain-os/dev-docs/sdks/app-connect-preparation
- OKX supported networks: https://web3.okx.com/pt/onchain-os/dev-docs/sdks/okx-wallet-integration-supported-networks
- Circle USDC addresses: https://developers.circle.com/stablecoins/usdc-contract-addresses
- Supabase SSR client setup: https://supabase.com/docs/guides/auth/server-side/creating-a-client?framework=nextjs
- Supabase service role isolation: https://supabase.com/docs/guides/troubleshooting/why-is-my-service-role-key-client-getting-rls-errors-or-not-returning-data-7_1K9z

## 15.1 Solana-only Confirmation Route

Use this smaller route when the deployed app only accepts the Solana USDC payment exposed by the static dashboard. It deliberately ignores client-provided user IDs, amounts, and plan names.

Create `app/api/payments/confirm-solana/route.ts`.

```ts
import { NextRequest, NextResponse } from "next/server";
import { Connection, PublicKey } from "@solana/web3.js";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

const connection = new Connection(
  process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com",
  "confirmed",
);

const RECIPIENT = new PublicKey(process.env.MY_SOLANA_WALLET!).toBase58();
const USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const PREMIUM_PRICE_UNITS = 19_900_000n;

export async function POST(req: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { signature, walletAddress } = (await req.json()) as {
      signature?: string;
      walletAddress?: string;
    };

    if (!signature || !walletAddress) {
      return NextResponse.json({ error: "Missing payment details" }, { status: 400 });
    }

    const tx = await connection.getParsedTransaction(signature, {
      maxSupportedTransactionVersion: 0,
      commitment: "finalized",
    });

    if (!tx || tx.meta?.err) {
      return NextResponse.json({ error: "Transaction is not finalized" }, { status: 400 });
    }

    const received = (tx.meta.postTokenBalances ?? []).some((post) => {
      const pre = tx.meta?.preTokenBalances?.find(
        (item) => item.accountIndex === post.accountIndex,
      );

      const delta =
        BigInt(post.uiTokenAmount.amount) -
        BigInt(pre?.uiTokenAmount.amount ?? "0");

      return (
        post.mint === USDC_MINT &&
        post.owner === RECIPIENT &&
        delta >= PREMIUM_PRICE_UNITS
      );
    });

    if (!received) {
      return NextResponse.json({ error: "Expected 19.9 USDC payment was not found" }, { status: 400 });
    }

    const payer = tx.transaction.message.accountKeys
      .find((account) => account.signer)
      ?.pubkey.toBase58();

    if (!payer || payer !== walletAddress) {
      return NextResponse.json({ error: "Payment signer does not match connected wallet" }, { status: 403 });
    }

    const admin = createSupabaseAdminClient();
    const { data: linkedWallet } = await admin
      .from("wallets")
      .select("id")
      .eq("user_id", user.id)
      .eq("chain", "solana")
      .eq("address", payer)
      .maybeSingle();

    if (!linkedWallet) {
      return NextResponse.json({ error: "Wallet is not linked to this account" }, { status: 403 });
    }

    const { error: paymentError } = await admin.from("payments").insert({
      user_id: user.id,
      chain: "solana",
      tx_hash: signature,
      wallet_address: payer,
      amount_units: PREMIUM_PRICE_UNITS.toString(),
      status: "confirmed",
    });

    if (paymentError?.code === "23505") {
      return NextResponse.json({ error: "Transaction was already processed" }, { status: 409 });
    }

    if (paymentError) throw paymentError;

    const { error: profileError } = await admin.from("profiles").upsert({
      id: user.id,
      subscription_status: "premium",
      updated_at: new Date().toISOString(),
    });

    if (profileError) throw profileError;

    return NextResponse.json({
      success: true,
      amount: "19.9",
      message: "Payment verified. Permanent premium access is active.",
    });
  } catch (error) {
    console.error("Solana payment verification failed:", error);
    return NextResponse.json({ error: "Payment verification failed" }, { status: 500 });
  }
}
```

Add these server-only variables to `.env.local`:

```dotenv
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
MY_SOLANA_WALLET=EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq
```

## 16. One Connect Button For Phantom And OKX

The earlier example exposes separate Solana and Base controls. Use the component below when the product should have one polished `Connect Wallet` entry point. It opens a compact chooser with:

- Phantom extension on Solana.
- Phantom or another installed EVM wallet on Base.
- OKX Wallet through WalletConnect QR / mobile deep link.
- Solana Wallet Adapter's modal as a fallback for WalletConnect-compatible Solana wallets.

Replace `components/connect-wallet-button.tsx` with:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useWalletModal } from "@solana/wallet-adapter-react-ui";
import { useAccount, useConnect, useDisconnect } from "wagmi";

function short(address?: string) {
  return address ? `${address.slice(0, 5)}...${address.slice(-4)}` : "";
}

export function ConnectWalletButton() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const solana = useWallet();
  const { setVisible: setSolanaModalVisible } = useWalletModal();
  const evm = useAccount();
  const { connectors, connect, isPending } = useConnect();
  const { disconnect } = useDisconnect();

  const injected = connectors.find((item) => item.id === "injected");
  const walletConnect = connectors.find((item) => item.id === "walletConnect");
  const activeAddress = solana.publicKey?.toBase58() ?? evm.address;

  useEffect(() => {
    function closeOnOutsideClick(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, []);

  function openSolanaChooser() {
    setOpen(false);
    setSolanaModalVisible(true);
  }

  function openEvmInjected() {
    if (!injected) return;
    setOpen(false);
    connect({ connector: injected });
  }

  function openOkxWalletConnect() {
    if (!walletConnect) return;
    setOpen(false);
    connect({ connector: walletConnect });
  }

  async function disconnectAll() {
    if (solana.connected) await solana.disconnect();
    if (evm.isConnected) disconnect();
    setOpen(false);
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        className="inline-flex h-10 items-center gap-2 rounded-md bg-neutral-950 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-neutral-800"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        {activeAddress ? short(activeAddress) : "Connect Wallet"}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-neutral-200 bg-white p-2 shadow-xl">
          {activeAddress ? (
            <button
              type="button"
              className="w-full rounded-md px-3 py-3 text-left text-sm font-semibold text-red-700 hover:bg-red-50"
              onClick={() => void disconnectAll()}
            >
              Disconnect {short(activeAddress)}
            </button>
          ) : (
            <div className="space-y-1">
              <button
                type="button"
                className="w-full rounded-md px-3 py-3 text-left hover:bg-neutral-100"
                onClick={openSolanaChooser}
              >
                <span className="block text-sm font-semibold">Phantom / Solana wallet</span>
                <span className="block text-xs text-neutral-500">Extension or Solana WalletConnect</span>
              </button>

              <button
                type="button"
                className="w-full rounded-md px-3 py-3 text-left hover:bg-neutral-100 disabled:opacity-50"
                disabled={!injected || isPending}
                onClick={openEvmInjected}
              >
                <span className="block text-sm font-semibold">Phantom / browser wallet on Base</span>
                <span className="block text-xs text-neutral-500">Installed EVM extension</span>
              </button>

              <button
                type="button"
                className="w-full rounded-md px-3 py-3 text-left hover:bg-neutral-100 disabled:opacity-50"
                disabled={!walletConnect || isPending}
                onClick={openOkxWalletConnect}
              >
                <span className="block text-sm font-semibold">OKX Wallet</span>
                <span className="block text-xs text-neutral-500">WalletConnect QR code or mobile deep link</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

The Solana fallback modal already receives:

```ts
new PhantomWalletAdapter()
new WalletConnectWalletAdapter({ ... })
```

The Base chooser already receives:

```ts
injected({ shimDisconnect: true })
walletConnect({ projectId, showQrModal: true })
```

This provides one visible Connect button while keeping Phantom and OKX selectable inside the same menu.

### Optional OKX-native Mobile SDK

If OKX mobile App Wallet deep links need OKX-specific UI, add:

```bash
npm install @okxconnect/ui @okxconnect/universal-provider
```

OKX documents `OKXUniversalConnectUI.init(...)` and `openModal(...)` for this flow. Keep it behind the same `OKX Wallet` option rather than adding a second top-level button. WalletConnect remains the simpler default when Phantom and OKX need to coexist with Base and Solana in one chooser.
