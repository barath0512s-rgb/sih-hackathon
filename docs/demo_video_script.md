# Demo video script v2 (about 5 minutes)

v2 (27 Sep 2026): only what shipped by the uplift, in the order the team fixed.
Photo import (C2) is **not shown**: it is not built (blocked). v1.2 is in
`_archive/demo_video_script_v1.2.md`.

Every segment carries its **device label** on screen, exactly as written here.
Two set-ups appear, never mixed in one shot:

- **Laptop hub**: caption **"Laptop hub: everything runs on this laptop, offline"**.
- **Tablet app**: the caption names the device. Tablet shots are **recorded clips**:
  the Realme Pad Mini if its session passed (`docs/device_session.md`), otherwise
  the 2 GB Android 9 emulator. Speech into the app can only be filmed on the
  Realme (the emulator's microphone records silence); without the Realme session,
  segment 2 uses the emulator clip with typed input and the measured numbers as a
  caption, and says so.

**Do not say or show:** a speed other than the ones in the captions or on the
page's timer; "on a 2 GB tablet" for anything measured on the emulator or the
Realme (say "2 GB emulator" / "Realme Pad Mini, 4 GB"); free-form *spoken*
translation on the tablet (it is off); anything about photo import; any claim
that Santali output or voices are reviewed by a native speaker.

## Before recording

1. Laptop on mains power, other programs closed. `run_nijbhasha.bat`; then
   `python tools/demo_reset.py --forget-demo-correction` (must end with `Ready.`).
2. Wi-Fi off. Chrome at `http://127.0.0.1:5000`, zoom 125 %.
3. Tablet clips: install the release APK, import the newest **model pack** and
   **content pack** (both signed), switch airplane mode on.
4. A Santali speaker on the team writes the correction for segment 9 and, if
   possible, speaks the child's answer in segment 2. **Do not invent Santali.**

## Segments

| # | Time | Set-up | Shot | Caption (exact) |
|---|---|---|---|---|
| 1 | 0:00–0:20 | Tablet clip | Airplane mode on; open the app; lessons appear from the content pack | Realme: **"Realme Pad Mini, 4 GB RAM, Android 11, airplane mode"** / emulator: **"Android 9 emulator, 2 GB RAM, airplane mode"** |
| 2 | 0:20–1:05 | Tablet clip | **Lesson line by voice, on the tablet (A1):** the teacher says a lesson line (e.g. *"दो आम और तीन आम मिलाओ।"*); the Santali appears and plays. Then a child's Santali answer to a question; it turns green and the Hindi praise plays | Same device caption, plus: **"On-device speech for lesson lines. On a 2 GB RAM, Android 9 emulator: voice to voice p50 0.50 s, p90 0.82 s (to the reply audio); lines not in the lesson are refused, never guessed."** |
| 3 | 1:05–1:35 | Tablet clip, then hub | **New sentences (A5):** on the tablet, type a new Hindi sentence → Santali, translated on the tablet. Then on the hub, *speak* a free sentence → Santali voice | Tablet: **"Typed new sentences translated on the tablet (same output as the laptop on 1502 of 1503 test sentences)."** Hub: **"Laptop hub: everything runs on this laptop, offline"** |
| 4 | 1:35–1:55 | Hub | **Check with a native speaker (A3):** type a line the model gets wrong (pick one flagged in the pack); the ⚠️ मूल वक्ता से जाँचें badge shows, no auto-play, the nearest verified sentence is offered | **"A warning, not a quality score."** |
| 5 | 1:55–2:30 | Hub | **Worksheet v2 and flashcards (A2):** कार्यपत्रक → the PDF: pictures, count and write, circle the answer, trace the numerals, the answer key page; चित्र पत्ते → 🖨️ → the cut-out cards with the review-pending mark | **"Pictures: OpenMoji (CC BY-SA 4.0). Santali lines await native review."** |
| 6 | 2:30–3:05 | Hub | **Reading fluency (C1):** प्रगति → पढ़ने की गति जाँचें; tick the consent box; a team member reads *बगीचे की सैर*; words correct per minute and the NIPUN goal; tap one word to override | **"Checked on adult read speech; children not measured yet. The recording is not saved."** |
| 7 | 3:05–3:25 | Hub | **Class progress by NIPUN Lakshya (A8):** the table by Lakshya and week; CSV and PDF | **"Class level only: no child names, no voices."** |
| 8 | 3:25–3:55 | Tablet clip + hub | **Corrections between tablets (A4):** a correction on the tablet → निर्यात → the signed file merged on the hub → the next pack on another tablet shows it | Device caption; **"Packs and tablet files are signed (Ed25519); a changed pack is refused."** |
| 9 | 3:55–4:20 | Hub | **Mundari and Ho voices (A7):** सेटिंग → मुंडारी / हो आवाज़; a teacher's Devanagari line spoken | **"Preview: pronunciation not reviewed. No Mundari or Ho translation yet."** |
| 10 | 4:20–4:40 | Card | **Santali voice comparison (A6):** the table from `bench/results/voice_compare.md` | **"Kept the current voice by the rule fixed in advance; native listener ratings not collected yet."** |
| 11 | 4:40–4:55 | Card | Close: *"Offline on the laptop hub, and on the tablet for lesson lines, typed translation, worksheets and sync. Next: the 4 GB tablet, children's voices and native review."* | — |

## If something goes wrong

| Problem | Fix |
|---|---|
| No sound | Click once on the page, then 🔊. |
| A spoken line on the tablet says "not a lesson line" | That is the designed answer for lines not in the lesson; speak the lesson line exactly, or type it. |
| The tablet refuses a pack | It is unsigned or changed: rebuild it on the hub (`tools/build_content_pack.py`) and import again. |
| The reading check gives a low score for an adult | Recognition errors count as misreadings (5.9 % of words on adult speech); tap the word to correct it. |
