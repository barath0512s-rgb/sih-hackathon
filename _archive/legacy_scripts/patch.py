import re

with open('frontend.html', 'r', encoding='utf-8') as f:
    frontend_html = f.read()

with open('frontend_v3.html', 'r', encoding='utf-8') as f:
    v3_html = f.read()

# Extract the script contents from frontend.html
script_match = re.search(r'<script>(.*?)</script>', frontend_html, flags=re.DOTALL)
if script_match:
    script_content = script_match.group(1)
    
    # Replace the script contents in frontend_v3.html
    v3_html_patched = re.sub(r'<script>.*?</script>', f'<script>{script_content}</script>', v3_html, flags=re.DOTALL)
    
    with open('frontend.html', 'w', encoding='utf-8') as f:
        f.write(v3_html_patched)
    print("Patched successfully!")
else:
    print("Could not find script block.")
