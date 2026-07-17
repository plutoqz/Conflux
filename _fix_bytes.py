path = r"src/conflux/workbench/server.py"
with open(path, "rb") as f:
    data = f.read()

# We need to change the JS strings inside the APP_JS Python triple-quoted string.
# The pattern is: '=== X ===\n' + ... + '\n\n';
# In the Python source, \n is the escape for newline. We need \\n (double) so
# Python produces literal \n in the JS output.
#
# Strategy: find specific byte sequences and replace

# Old bytes for the query output lines (within the triple-quoted Python string):
# Line 1: '=== 最终答案 ===\n' + data.final_answer + '\n\n';
old_line1 = "=== \u6700\u7ec8\u7b54\u6848 ===\\n' + data.final_answer + '\\n\\n';".encode()
new_line1 = "=== \u6700\u7ec8\u7b54\u6848 ===\\\\n' + data.final_answer + '\\\\n\\\\n';".encode()
# Line 2: '=== 运行日志 ===\n' + data.stdout;
old_line2 = "=== \u8fd0\u884c\u65e5\u5fd7 ===\\n' + data.stdout;".encode()
new_line2 = "=== \u8fd0\u884c\u65e5\u5fd7 ===\\\\n' + data.stdout;".encode()

count = 0
if old_line1 in data:
    data = data.replace(old_line1, new_line1)
    count += 1
    print("Replaced line 1")
else:
    print("old_line1 not found")
if old_line2 in data:
    data = data.replace(old_line2, new_line2)
    count += 1
    print("Replaced line 2")
else:
    print("old_line2 not found")

if count:
    with open(path, "wb") as f:
        f.write(data)
    print(f"Written {count} replacements")

# Verify
with open(path, "rb") as f:
    data2 = f.read()
idx = data2.find("最终答案".encode())
print("Verify hex:", data2[idx:idx+30].hex(' '))
