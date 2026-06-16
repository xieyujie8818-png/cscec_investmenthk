import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="ignore").read()

nums = sorted(
    set(int(x) for x in re.findall(r"\b(\d{4,5})\b", text) if 3000 <= int(x) <= 20000)
)
print("NUMS:", nums)

# dollar amounts with context
for m in re.finditer(r".{0,40}(?:HK\$|HKD\s*)?[\d,]{3,5}.{0,40}", text):
    s = m.group(0)
    if any(c.isdigit() for c in s):
        print("CTX:", repr(s[:120]))

# chinese fragments
texts = re.findall(r"[\u4e00-\u9fff]{2,50}", text)
uniq = []
for t in texts:
    if any(k in t for k in ["租", "房", "月", "單", "雙", "人", "價", "元", "港", "太子", "尖沙咀"]):
        if t not in uniq:
            uniq.append(t)
print("---CN---")
for t in uniq[:100]:
    print(t)

# english fragments
for m in re.finditer(r"[A-Za-z][A-Za-z0-9 ,.'\-]{8,80}", text):
    s = m.group(0)
    if any(k in s.lower() for k in ["rent", "room", "single", "month", "price", "hk"]):
        if s not in uniq:
            print("EN:", s)
