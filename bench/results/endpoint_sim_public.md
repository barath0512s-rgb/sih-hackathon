# Endpointing replayed on 80 clips (manifest.json)

Rule as in frontend.html: 20 ms frames, 300 ms calibration, speech = RMS > max(3 x floor, 0.01).
Public dataset, adult read speech (FLEURS) unless the manifest says otherwise. Laptop, offline.

| Endpoint silence | Clips cut early (a pause ended the recording) | Speech lost when cut, median | Wait after speech ends |
|---|---|---|---|
| 500 ms | 27 of 78 | 4.4 s | median 500 ms |
| 700 ms | 17 of 78 | 4.1 s | median 700 ms |
| 1000 ms | 11 of 78 | 4.2 s | median 1000 ms |
| adaptive: 500 ms, 1000 ms after 2.5 s of speech | 16 of 78 | 5.4 s | median 720 ms |
