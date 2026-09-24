# ASR decoding and silence trimming (synthetic)

60 clips; ASR only (audio already decoded to WAV); times in ms.

> Synthetic clips. CER compares the variants on identical audio; it is not
> ASR accuracy on real speech.

| Language | Decoding | Trim silence | ASR median ms | ASR p90 ms | CER median | CER mean |
|---|---|---|---|---|---|---|
| hi | rnnt | no | 1521 | 1766 | 0.031 | 0.039 |
| hi | rnnt | yes | 1304 | 1800 | 0.029 | 0.032 |
| hi | ctc | no | 693 | 781 | 0.031 | 0.043 |
| hi | ctc | yes | 578 | 683 | 0.029 | 0.033 |
| sat | rnnt | no | 1562 | 1829 | 0.217 | 0.226 |
| sat | rnnt | yes | 1379 | 1778 | 0.202 | 0.239 |
| sat | ctc | no | 733 | 783 | 0.195 | 0.216 |
| sat | ctc | yes | 577 | 712 | 0.218 | 0.235 |
