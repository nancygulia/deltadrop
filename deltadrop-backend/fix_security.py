with open('app/core/security.py', 'r') as f:
    content = f.read()

print("Current hash_password function:")
for i, line in enumerate(content.split('\n')):
    if 'hash_password' in line or 'verify_password' in line or 'pwd_context' in line:
        print(f"  Line {i}: {line}")

# Fix hash_password
content = content.replace(
    'def hash_password(plain: str) -> str:\n    return pwd_context.hash(plain)',
    'def hash_password(plain: str) -> str:\n    return pwd_context.hash(plain[:72])'
)

# Fix verify_password
content = content.replace(
    'def verify_password(plain: str, hashed: str) -> bool:\n    return pwd_context.verify(plain, hashed)',
    'def verify_password(plain: str, hashed: str) -> bool:\n    return pwd_context.verify(plain[:72], hashed)'
)

with open('app/core/security.py', 'w') as f:
    f.write(content)

print("Done - security.py updated")