import secrets

# Генерация безопасного секретного ключа для Flask
secret_key = secrets.token_hex(32)  # 64 символа (32 байта в hex)
print(f"FLASK_SECRET_KEY={secret_key}")

# Альтернативный вариант с base64
import base64
secret_key_b64 = base64.b64encode(secrets.token_bytes(32)).decode()
print(f"FLASK_SECRET_KEY_B64={secret_key_b64}")
