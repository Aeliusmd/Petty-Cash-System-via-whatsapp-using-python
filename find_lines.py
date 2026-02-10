
filename = r"d:\MedCube\Projects\4th Month\Petty Cash System via whatsapp - python\backend\app\reply_engine.py"
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "Welcome" in line:
            print(f"{i+1}: {line.strip()}")
