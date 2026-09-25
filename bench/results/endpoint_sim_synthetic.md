# Endpointing replayed on 30 clips (manifest.json)

n = 30 clips, n_distinct = 30 sentences. Endpointing depends on each recording's pauses, so every clip counts (different readers of one sentence pause differently). A clip whose speech starts inside the 300 ms calibration cannot be evaluated; each row gives the clips evaluated.

Rule as in frontend.html: 20 ms frames, 300 ms calibration, speech = RMS > max(3 x floor, 0.01).
Public dataset, adult read speech (FLEURS) unless the manifest says otherwise. Laptop, offline.

| Endpoint silence | Clips cut early (a pause ended the recording) | n evaluated / n_distinct | Speech lost when cut, median | Wait after speech ends |
|---|---|---|---|---|
| 500 ms | 0 of 30 | 30 / 30 | 0.0 s | median 500 ms |
| 700 ms | 0 of 30 | 30 / 30 | 0.0 s | median 700 ms |
| 1000 ms | 0 of 30 | 30 / 30 | 0.0 s | median 1000 ms |
| adaptive: 500 ms, 1000 ms after 2.5 s of speech | 0 of 30 | 30 / 30 | 0.0 s | median 500 ms |
