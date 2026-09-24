# Demo video script (3–4 minutes)

Every shot shows something that works today. The whole demo runs in
**laptop hub mode**: speech recognition, translation and speech all run on
the laptop, offline. Put the caption **"Laptop hub mode: everything runs on
this laptop, offline"** on screen at the start, and again on any shot of a
tablet or phone.

**Do not say or show:**
- the app running *on* a tablet;
- any accuracy number;
- any speed number other than the one the timer shows during the take;
- "0.15 s", "<4 s", or "all MIT-licensed".

## Before recording

1. Laptop on mains power. Close other programs.
2. Start `run_vaanisetu.bat` and wait for `Running on http://127.0.0.1:5000`.
3. In a second window, run `python tools/demo_reset.py --forget-demo-correction`.
   It must end with `Ready.` It backs up the database, clears old sessions,
   checks that all lessons loaded, and warms the models.
4. **Turn Wi-Fi off** (or unplug the network). The rest of the demo is offline.
5. Open `http://127.0.0.1:5000` in Chrome and reload once. Zoom 125%, or
   switch on large type in सेटिंग.
6. Test the microphone once: speak any Hindi line, then refresh the page.
7. Have the correction for the 1:55 shot ready on paper. **A Santali speaker on the
   team must write it. Do not invent one.**

## Shots

| Time | Shot | What to do and say |
|---|---|---|
| 0:00–0:15 | Title card | Product name, SIH26042. One line: *"In the surveyed Jharkhand districts, Hindi is the medium of instruction in about 98% of schools (JEPC Language Mapping Survey)."* |
| 0:15–0:35 | Offline proof | Show Wi-Fi off. Open `http://127.0.0.1:5000/health/models` and point at `"online_dependencies": []`. Caption: **Laptop hub mode, offline**. |
| 0:35–1:10 | Teacher speaks Hindi | Classroom (कक्षा), lesson **जोड़ना** (Grade 2). Press **🎤 हिंदी बोलिए** and say *"दो आम और तीन आम मिलाओ। कुल कितने हुए? उंगलियों पर गिनो।"* Santali appears in Ol Chiki and is spoken. Point at the source badge (सत्यापित शब्दकोश) and at the timer card, which shows the real wait from the end of speech to the start of the voice. |
| 1:10–1:35 | Child answers | Go to the question *"तीन और चार कितने होते हैं?"* In the answer box (बच्चे ने क्या कहा), a Santali speaker says the answer into 🎤. Without one, type **᱗**. It turns green (बिलकुल सही). Point at the ⏳ badge: the accepted answers await native review. |
| 1:35–1:55 | Santali to Hindi | Press the swap button (🔄) and type *"ᱯᱮ ᱟᱨ ᱯᱩᱱ ᱡᱚᱛᱚ ᱦᱩᱭᱩᱜᱼᱟ?"*, then अनुवाद. A Santali speaker can use **🎙️ ᱥᱟᱱᱛᱟᱲᱤ** instead. The Hindi appears and is spoken. |
| 1:55–2:25 | A correction is reused | Press 🔄 again to go back to Hindi → Santali. Type *"गांव के बच्चे खेत में खेल रहे हैं।"* The badge says 🤖 मशीन अनुवाद. Under अनुवाद ठीक था, press **✏️ सुधारें**, enter the correction from the Santali speaker, and save it. Translate the same line again: the badge now says 🧑‍🏫 शिक्षक द्वारा सुधारा and the corrected Santali is used. |
| 2:25–2:45 | Worksheet | Press कार्यपत्रक. Show the PDF: Hindi and Santali headings, the lesson's lines, and the NIPUN Lakshya tag with the Ministry's wording. |
| 2:45–3:00 | Flashcards | चित्र पत्ते → deck **जोड़ना**. Flip two cards and press 🔊 on one. Point at the badges: word list, review pending. |
| 3:00–3:35 | Teacher adds a lesson | पाठ → ➕ नया पाठ जोड़िए. Choose कक्षा 1. Paste three prepared lines, e.g. *"आज हम पाँच तक गिनेंगे। चार आम गिनो। यहाँ कितने आम हैं?"* Press ✂️ पंक्तियाँ बनाइए. Tap one label to show it changes. Show the suggested NIPUN goal, tick the confirm box, and press 📘 पाठ बनाइए. Open it in the classroom (कक्षा में खोलिए). |
| 3:35–3:50 | Optional: a tablet as a screen | **Only if the tablet's microphone was tested over `run_vaanisetu.bat https` before recording.** Show the tablet's browser using the laptop. Caption: **Laptop hub mode: the tablet is a screen and microphone; everything runs on the laptop.** Otherwise skip this shot. |
| 3:50–4:00 | Close | *"Built so far: offline on the laptop hub, 17 NIPUN-tagged lessons that teachers can extend. Next: the Android app that runs on a 2 GB RAM, Android 9+ tablet."* |

The step 3:00 lesson is added to the database. After the recording, you can
remove it by restoring the backup `demo_reset.py` made (in `data/backups/`),
or keep it.

## If something goes wrong

| Problem | Fix |
|---|---|
| No sound | Click once on the page (the browser blocks autoplay), then press 🔊. |
| The mic does nothing | Chrome allows the microphone only on `http://127.0.0.1` or `https://`. Use the laptop's own browser for the take. |
| A slow first translation | Run `tools/demo_reset.py` again with the server already running. |
| Green does not appear for a spoken Santali answer | Type ᱗ instead. Speech recognition of Santali has not been measured on real voices yet. |
