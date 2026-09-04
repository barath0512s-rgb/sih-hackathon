import re

with open('VaaniSetu_WINNER_Build_Guide.md', 'r', encoding='utf-8') as f:
    text = f.read()

# We look for something like: Create `app.py`: ... ```python\nCODE\n```
# Let's split by "Create `"
parts = text.split("Create `")
for part in parts[1:]:
    fname = part.split("`")[0]
    if fname.endswith(".py"):
        # find the next ```python or ```
        code_start = part.find("```python")
        if code_start != -1:
            code_start += 9 # length of ```python
        else:
            code_start = part.find("```") + 3
        
        # find the end ```
        code_end = part.find("```", code_start)
        if code_end != -1:
            code = part[code_start:code_end].strip()
            with open(fname, 'w', encoding='utf-8') as out:
                out.write(code + '\n')
            print(f"Created {fname}")
