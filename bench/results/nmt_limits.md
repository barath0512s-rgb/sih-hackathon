# NMT decode limit

60 reference lines; greedy; fixed limit 128 vs sized limit min(128, 3 x input tokens + 10).

| Language in | Fixed median ms | Sized median ms | Longest output (tokens) |
|---|---|---|---|
| hi | 454 | 460 | 19 |
| sat | 437 | 429 | 21 |

Outputs that reached the fixed limit (runaway generation): 0 of 60.
Outputs changed by the sized limit: 0 of 60.
