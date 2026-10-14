# Data quality report

Source: CMS Transparency in Coverage PUF, Individual Marketplace medical plans (Ind QHP sheet). Self-reported by insurers to CMS.

| Check | Result | Detail |
|---|---|---|
| [2023] One row per plan | Pass | 4,541 rows, 4,541 unique plan IDs |
| [2023] Insurer totals identical on every plan row | Pass | max distinct values of an insurer field within one insurer: 1 |
| [2023] Each insurer ID belongs to one state | Pass | max states per insurer ID: 1 |
| [2023] Insurer totals counted once, not once per plan | Pass | summing every plan row would report 38,057,731,335 claims; deduplicated it's 471,049,416 (81x overcount avoided) |
| [2023] No insurer denies more claims than it received | Pass | 0 insurers fail |
| [2023] Insurers with claims data | Pass | 177 of 206 insurers report claims; 29 have none (mostly new to the exchange) and are left out of rates, not counted as zero |
| [2023] Plans with plan-level claims data | Pass | 2,468 of 4,541 plans (54%); denial reasons only exist for these |
| [2023] Denial reasons vs plan denial totals | Pass | reasons sum to 82,851,909 vs 63,642,808 plan denials (1.30x). Some claims are denied for more than one reason, so reasons are reported as shares only |
| [2023] Reported appeal overturn % matches recomputed | Pass | 154 of 154 insurers within 1 point; recomputed values used downstream |
| [2024] One row per plan | Pass | 4,159 rows, 4,159 unique plan IDs |
| [2024] Insurer totals identical on every plan row | Pass | max distinct values of an insurer field within one insurer: 1 |
| [2024] Each insurer ID belongs to one state | Pass | max states per insurer ID: 1 |
| [2024] Insurer totals counted once, not once per plan | Pass | summing every plan row would report 48,621,672,358 claims; deduplicated it's 495,646,850 (98x overcount avoided) |
| [2024] No insurer denies more claims than it received | Pass | 0 insurers fail |
| [2024] Insurers with claims data | Pass | 159 of 185 insurers report claims; 26 have none (mostly new to the exchange) and are left out of rates, not counted as zero |
| [2024] Plans with plan-level claims data | Pass | 2,554 of 4,159 plans (61%); denial reasons only exist for these |
| [2024] Denial reasons vs plan denial totals | Pass | reasons sum to 87,173,324 vs 75,856,033 plan denials (1.15x). Some claims are denied for more than one reason, so reasons are reported as shares only |
| [2024] Reported appeal overturn % matches recomputed | Pass | 129 of 129 insurers within 1 point; recomputed values used downstream |

## CMS special codes, treated as missing (never as zero)

| Code | Meaning | Rows across all columns |
|---|---|---|
| `*` | not available | 5,941 |
| `**` | suppressed (small numbers) | 14,962 |
| `***` | not required for plan type | 516 |
