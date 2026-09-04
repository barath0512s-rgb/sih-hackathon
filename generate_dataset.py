import pandas as pd
import os

# Create the training dataset directory
os.makedirs("training_data", exist_ok=True)

# FLN (Foundational Literacy & Numeracy) Parallel Corpus
# Hindi -> Santali (Ol Chiki) direct translations for Grade 1-3 math & language
data = [
    # ── Greetings & Classroom Management ──
    {"hindi": "सुप्रभात बच्चों।", "santali": "ᱥᱮᱛᱟᱜ ᱡᱚᱦᱟᱨ ᱜᱤᱫᱽᱨᱟᱹᱠᱚ᱾"},
    {"hindi": "आज हम एक नया पाठ पढ़ेंगे।", "santali": "ᱛᱮᱦᱮᱧ ᱟᱵᱚ ᱢᱤᱫᱴᱟᱹᱝ ᱱᱟᱶᱟ ᱯᱟᱴᱷ ᱵᱚᱱ ᱯᱟᱲᱦᱟᱣᱟ᱾"},
    {"hindi": "कृपया अपनी जगह पर बैठ जाएं।", "santali": "ᱫᱟᱭᱟ ᱠᱟᱛᱮ ᱟᱯᱮᱭᱟᱜ ᱡᱟᱭᱜᱟ ᱨᱮ ᱫᱩᱲᱩᱵ ᱯᱮ᱾"},
    {"hindi": "क्या सब लोग तैयार हैं?", "santali": "ᱪᱮᱫ ᱡᱚᱛᱚ ᱦᱚᱲ ᱯᱮ ᱥᱟᱯᱲᱟᱣ ᱟᱠᱟᱱᱟ?"},
    {"hindi": "मेरी बात ध्यान से सुनो।", "santali": "ᱤᱧᱟᱜ ᱠᱟᱛᱷᱟ ᱢᱚᱱᱮ ᱞᱟᱜᱟᱣ ᱠᱟᱛᱮ ᱟᱸᱡᱚᱢ ᱯᱮ᱾"},
    {"hindi": "शोर मत करो।", "santali": "ᱟᱞᱚ ᱯᱮ ᱜᱚᱞᱢᱟᱞᱟ᱾"},
    {"hindi": "अपना हाथ उठाएं।", "santali": "ᱟᱯᱮᱭᱟᱜ ᱛᱤ ᱛᱩᱞ ᱯᱮ᱾"},
    {"hindi": "बहुत अच्छा!", "santali": "ᱟᱹᱰᱤ ᱱᱟᱯᱟᱭ!"},
    {"hindi": "शाबाश!", "santali": "ᱥᱟᱵᱟᱥ!"},

    # ── Numeracy: Numbers & Counting ──
    {"hindi": "एक, दो, तीन, चार, पांच।", "santali": "ᱢᱤᱫ, ᱵᱟᱨ, ᱯᱮ, ᱯᱩᱱ, ᱢᱚᱬᱮ᱾"},
    {"hindi": "मेरे साथ गिनो।", "santali": "ᱤᱧ ᱥᱟᱶᱛᱮ ᱞᱮᱠᱷᱟᱭ ᱯᱮ᱾"},
    {"hindi": "तुम्हारे पास कितनी किताबें हैं?", "santali": "ᱟᱢ ᱴᱷᱮᱱ ᱛᱤᱱᱟᱹᱜ ᱯᱚᱛᱚᱵ ᱢᱮᱱᱟᱜᱼᱟ?"},
    {"hindi": "यह संख्या क्या है?", "santali": "ᱱᱚᱶᱟ ᱮᱞ ᱫᱚ ᱪᱮᱫ ᱠᱟᱱᱟ?"},
    {"hindi": "पांच के बाद क्या आता है?", "santali": "ᱢᱚᱬᱮ ᱛᱟᱭᱚᱢ ᱪᱮᱫ ᱦᱤᱡᱩᱜᱼᱟ?"},
    {"hindi": "अपनी उंगलियों पर गिनो।", "santali": "ᱟᱢᱟᱜ ᱠᱟᱹᱴᱩᱵ ᱨᱮ ᱞᱮᱠᱷᱟᱭ ᱢᱮ᱾"},

    # ── Numeracy: Addition (NIPUN Grade 2) ──
    {"hindi": "आज हम जोड़ना सीखेंगे।", "santali": "ᱛᱮᱦᱮᱧ ᱟᱵᱚ ᱥᱮᱞᱮᱫ ᱵᱚᱱ ᱪᱮᱫᱚᱜᱼᱟ᱾"},
    {"hindi": "दो और तीन को जोड़ने पर क्या मिलता है?", "santali": "ᱵᱟᱨ ᱟᱨ ᱯᱮ ᱥᱮᱞᱮᱫ ᱞᱮᱠᱷᱟᱱ ᱪᱮᱫ ᱧᱟᱢᱚᱜᱼᱟ?"},
    {"hindi": "अगर मेरे पास दो आम हैं, और तुम मुझे तीन आम और दो, तो मेरे पास कितने आम होंगे?", "santali": "ᱡᱩᱫᱤ ᱤᱧ ᱴᱷᱮᱱ ᱵᱟᱨᱭᱟ ᱩᱞ ᱢᱮᱱᱟᱜᱼᱟ, ᱟᱨ ᱟᱢ ᱤᱧ ᱯᱮᱭᱟ ᱩᱞ ᱮᱢᱟᱹᱧᱟ, ᱮᱱᱠᱷᱟᱱ ᱤᱧ ᱴᱷᱮᱱ ᱛᱤᱱᱟᱹᱜ ᱩᱞ ᱦᱩᱭᱩᱜᱼᱟ?"},
    {"hindi": "सही जवाब है पांच।", "santali": "ᱥᱚᱦᱤ ᱛᱮᱞᱟ ᱫᱚ ᱢᱚᱬᱮ ᱠᱟᱱᱟ᱾"},
    {"hindi": "इन दोनों संख्याओं को जोड़ो।", "santali": "ᱱᱚᱶᱟ ᱵᱟᱱᱟᱨ ᱮᱞ ᱥᱮᱞᱮᱫ ᱢᱮ᱾"},
    {"hindi": "कुल मिलाकर कितने हुए?", "santali": "ᱡᱚᱛᱚ ᱢᱮᱥᱟ ᱠᱟᱛᱮ ᱛᱤᱱᱟᱹᱜ ᱦᱩᱭᱮᱱᱟ?"},
    {"hindi": "यह जोड़ का चिन्ह है।", "santali": "ᱱᱚᱶᱟ ᱫᱚ ᱥᱮᱞᱮᱫ ᱪᱤᱱᱦᱟᱹ ᱠᱟᱱᱟ᱾"},

    # ── Numeracy: Subtraction (NIPUN Grade 2) ──
    {"hindi": "आज हम घटाना सीखेंगे।", "santali": "ᱛᱮᱦᱮᱧ ᱟᱵᱚ ᱵᱷᱮᱜᱟᱨ ᱵᱚᱱ ᱪᱮᱫᱚᱜᱼᱟ᱾"},
    {"hindi": "पांच में से दो घटाने पर क्या बचेगा?", "santali": "ᱢᱚᱬᱮ ᱠᱷᱚᱱ ᱵᱟᱨ ᱵᱷᱮᱜᱟᱨ ᱞᱮᱠᱷᱟᱱ ᱪᱮᱫ ᱥᱟᱨᱮᱡᱚᱜᱼᱟ?"},
    {"hindi": "तुम्हारे पास चार पेन हैं। एक पेन मुझे दे दो।", "santali": "ᱟᱢ ᱴᱷᱮᱱ ᱯᱩᱱᱭᱟ ᱠᱚᱞᱚᱢ ᱢᱮᱱᱟᱜᱼᱟ᱾ ᱢᱤᱫᱴᱟᱹᱝ ᱠᱚᱞᱚᱢ ᱤᱧ ᱮᱢᱟᱹᱧ ᱢᱮ᱾"},
    {"hindi": "अब तुम्हारे पास कितने पेन बचे?", "santali": "ᱱᱤᱛᱚᱜ ᱟᱢ ᱴᱷᱮᱱ ᱛᱤᱱᱟᱹᱜ ᱠᱚᱞᱚᱢ ᱥᱟᱨᱮᱡ ᱮᱱᱟ?"},
    {"hindi": "यह घटाने का चिन्ह है।", "santali": "ᱱᱚᱶᱟ ᱫᱚ ᱵᱷᱮᱜᱟᱨ ᱪᱤᱱᱦᱟᱹ ᱠᱟᱱᱟ᱾"},

    # ── Assessment & Feedback ──
    {"hindi": "इसका जवाब कौन देगा?", "santali": "ᱱᱚᱶᱟ ᱨᱮᱭᱟᱜ ᱛᱮᱞᱟ ᱚᱠᱚᱭ ᱮᱢᱟᱭ?"},
    {"hindi": "बोर्ड पर आकर लिखो।", "santali": "ᱵᱳᱨᱰ ᱨᱮ ᱦᱮᱡ ᱠᱟᱛᱮ ᱚᱞ ᱢᱮ᱾"},
    {"hindi": "तुम्हारा जवाब बिल्कुल सही है।", "santali": "ᱟᱢᱟᱜ ᱛᱮᱞᱟ ᱫᱚ ᱮᱠᱟᱞ ᱥᱚᱦᱤ ᱜᱮᱭᱟ᱾"},
    {"hindi": "यह गलत है, फिर से कोशिश करो।", "santali": "ᱱᱚᱶᱟ ᱫᱚ ᱵᱷᱩᱞ ᱜᱮᱭᱟ, ᱟᱨᱦᱚᱸ ᱪᱮᱥᱴᱟᱭ ᱢᱮ᱾"},
    {"hindi": "क्या तुम इसे समझा सकते हो?", "santali": "ᱪᱮᱫ ᱟᱢ ᱱᱚᱶᱟᱢ ᱵᱩᱡᱷᱟᱹᱣ ᱫᱟᱲᱮᱭᱟᱜᱼᱟ?"},
    {"hindi": "इस वर्कशीट को पूरा करो।", "santali": "ᱱᱚᱶᱟ ᱣᱟᱨᱠᱥᱤᱴ ᱯᱩᱨᱟᱹᱣ ᱢᱮ᱾"}
]

# Convert to Pandas DataFrame
df = pd.DataFrame(data)

# Save as CSV for fine-tuning
csv_path = "training_data/nipun_hindi_santali.csv"
df.to_csv(csv_path, index=False, encoding="utf-8")

print(f"✅ Generated dataset: {csv_path} ({len(df)} rows)")
print("This parallel corpus maps Grade 1-3 classroom Hindi directly to Santali (Ol Chiki).")
print("We completely bypass English to preserve gender, respect levels, and mathematical context.")
