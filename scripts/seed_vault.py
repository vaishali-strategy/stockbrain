"""Seed an example Obsidian vault with realistic Indian-market notes.

Creates ./example-vault/ (override with VAULT_PATH or argv[1]) containing the standard
folder structure plus three educational example notes so the RAG chat has something to
retrieve out of the box. Content is realistic but clearly illustrative — not advice.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_VAULT = Path(__file__).resolve().parent.parent / "example-vault"
_FOLDERS = ["Companies", "Sectors", "Earnings", "Thesis", "News", "Concepts", "Watchlist", "Journal"]

RELIANCE = """---
ticker: RELIANCE
company: Reliance Industries Ltd.
sector: Energy
type: company
market_cap: large
exchange: NSE
tags: [oil-to-chemicals, retail, jio, conglomerate]
sentiment: bullish
position: long
confidence: medium
last_updated: 2025-01-15
---

## Business summary
Reliance Industries is India's largest company by market cap — a conglomerate spanning
oil-to-chemicals (O2C), Jio (telecom/digital), and Reliance Retail. The investment story
has shifted from a pure energy play to a consumer + digital growth story, with Jio and
Retail now driving the re-rating.

## Why I'm watching this
The Jio Platforms and Reliance Retail IPOs are the big potential catalysts. A listing
could unlock significant value that's currently buried inside the holdco structure.

## Key metrics
- Revenue growth YoY: ~8% (O2C cyclical, Jio + Retail compounding double digits)
- Gross margin: ~35%
- Net margin: ~8%
- P/E ratio: ~22x
- Debt/equity: moderate; net debt watched closely after capex peak
- Free cash flow: improving as Jio capex intensity falls

## Moat analysis
Jio's nationwide 5G network and scale give a durable telecom moat. Retail has the largest
store footprint in India. O2C is world-scale but cyclical and commoditised.

## Bull case
Jio/Retail value unlock via IPO; ARPU hikes in telecom; new energy (solar/hydrogen) optionality.

## Bear case
O2C margin cycles, heavy capex, regulatory/telecom price wars, holdco discount persists.

## Key risks
Crude/refining spreads, FII flows, INR depreciation on imported crude, execution on new energy.

## Linked notes
- [[TCS_Q3_2025]]

## My observations
Position sized as a core long-term holding. Adding on O2C-driven dips below 22x.
"""

TCS_EARNINGS = """---
ticker: TCS
quarter: Q3
year: 2025
type: earnings
beat_miss: in-line
tags: [it-services, deal-wins, margins]
date: 2025-01-09
---

## Headline numbers
- Revenue: ₹63,973 cr vs estimate ~₹64,000 cr (broadly in line)
- EPS: ~₹34 vs estimate ~₹33.5
- Guidance next quarter: cautious near-term on discretionary spend; FY momentum intact

## Management commentary (key quotes)
"Demand for cost-optimisation and AI-led transformation remains strong." Management
flagged a healthy deal pipeline and a record TCV of new deal wins, with BFSI stabilising.

## What surprised me
Margins held up better than feared despite wage hikes and a weak discretionary environment.
Attrition continued to cool, which supports margin durability into next year.

## How this changes my thesis
Reinforces TCS as the steady compounder of Indian IT. Not a high-growth story right now,
but cash generation and buybacks remain shareholder-friendly. I stay neutral-to-positive.

## Linked company note
- [[RELIANCE]]
"""

HDFCBANK_THESIS = """---
ticker: HDFCBANK
direction: bull
type: thesis
conviction: high
time_horizon: long
entry_target: 1450
exit_target: 2100
stop_loss: 1320
tags: [private-banks, credit-growth, merger]
created: 2025-01-12
---

## Core thesis (one paragraph)
HDFC Bank is the highest-quality private lender in India. Post the HDFC Ltd merger, the
near-term overhang has been elevated cost of funds and a depressed NIM, plus the LDR (loan-
to-deposit ratio) being stretched. As deposits catch up and the merged book normalises,
NIMs should recover and the bank can re-rate back toward its historical premium multiple.

## Catalysts I'm watching
1. Deposit growth outpacing loan growth (LDR normalising back toward ~90%)
2. NIM recovery as high-cost HDFC Ltd borrowings roll off
3. FII re-entry once index weight / MSCI adjustments play out

## What would invalidate this thesis
A structural inability to grow deposits at system-beating rates, or asset-quality slippage
in the unsecured book. A sustained NIM below ~3.4% would break the re-rating case.

## Position sizing rationale
High conviction, so a top-3 position. Accumulating in tranches near ₹1,450 with a mental
stop around ₹1,320. RBI rate-cut cycle would be a tailwind for treasury and NIM.

## Linked notes
- [[RELIANCE]]
"""


def _vault_dir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    env = os.getenv("VAULT_PATH", "").strip()
    return Path(env).expanduser().resolve() if env else _DEFAULT_VAULT


def main() -> int:
    vault = _vault_dir()
    for folder in _FOLDERS:
        (vault / folder).mkdir(parents=True, exist_ok=True)

    notes = {
        "Companies/RELIANCE.md": RELIANCE,
        "Earnings/TCS_Q3_2025.md": TCS_EARNINGS,
        "Thesis/Bull_HDFCBANK.md": HDFCBANK_THESIS,
    }
    for rel, content in notes.items():
        (vault / rel).write_text(content, encoding="utf-8")
        print(f"  wrote {rel}")

    print(f"Seeded example vault at {vault}")
    print("Point StockBrain at this folder (Settings → vault path) to try RAG chat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
