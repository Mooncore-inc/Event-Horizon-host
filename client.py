import aiohttp
import os
import sys
import threading
import asyncio
import json
import websockets
from queue import Queue
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend

BASE_URL = "http://localhost:8000"
KEYS_DIR = "keys"
realtime_queue = Queue()

def ensure_keys_dir():
    os.makedirs(KEYS_DIR, exist_ok=True)

def generate_keys():
    """Генерация пары ключей RSA"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Сериализация приватного ключа
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Сериализация публичного ключа
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem

def save_keys(private_pem, public_pem, username):
    """Сохранение ключей в файлы"""
    ensure_keys_dir()
    with open(f"{KEYS_DIR}/{username}_private.pem", "wb") as f:
        f.write(private_pem)
    with open(f"{KEYS_DIR}/{username}_public.pem", "wb") as f:
        f.write(public_pem)

def load_private_key(username):
    """Загрузка приватного ключа пользователя"""
    try:
        with open(f"{KEYS_DIR}/{username}_private.pem", "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None

def load_public_key(username):
    """Загрузка публичного ключа пользователя"""
    try:
        with open(f"{KEYS_DIR}/{username}_public.pem", "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None

def encrypt_message(message, public_key_pem):
    """Шифрование сообщения с использованием гибридного шифрования"""
    # Десериализация публичного ключа
    public_key = serialization.load_pem_public_key(
        public_key_pem,
        backend=default_backend()
    )
    
    # Генерация симметричного ключа и IV
    session_key = os.urandom(32)  # AES-256
    iv = os.urandom(16)           # AES block size
    
    # Шифрование сообщения AES
    padder = sym_padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode()) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # Шифрование сессионного ключа RSA
    encrypted_key = public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # Возвращаем данные в hex формате для удобства передачи
    return {
        "encrypted_key": encrypted_key.hex(),
        "ciphertext": ciphertext.hex(),
        "iv": iv.hex()
    }

def decrypt_message(private_key_pem, encrypted_key_hex, iv_hex, ciphertext_hex):
    """Дешифрование сообщения"""
    # Загрузка приватного ключа
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
        backend=default_backend()
    )
    
    # Конвертация из hex
    encrypted_key = bytes.fromhex(encrypted_key_hex)
    iv = bytes.fromhex(iv_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)
    
    # Дешифрование сессионного ключа
    session_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # Дешифрование сообщения
    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    # Удаление padding
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    
    return plaintext.decode()

async def exchange_keys(username: str):
    """Асинхронный обмен публичными ключами"""
    public_key = load_public_key(username)
    if not public_key:
        print("🔑 Публичный ключ не найден. Сгенерируйте ключи сначала.")
        return None
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/exchange_keys",
                json={"username": username, "public_key": public_key.decode()}
            ) as response:
                if response.status == 200:
                    print("✅ Публичный ключ успешно отправлен на сервер!")
                    return True
                else:
                    print(f"❌ Ошибка обмена ключами: {response.status}")
                    return False
        except Exception as e:
            print(f"🚫 Ошибка соединения: {e}")
            return False

async def get_remote_public_key(username: str):
    """Асинхронное получение публичного ключа"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/public_key/{username}") as response:
                if response.status == 200:
                    data = await response.json()
                    return data["public_key"].encode()
                else:
                    print(f"❌ Не удалось получить ключ: {await response.text()}")
                    return None
        except Exception as e:
            print(f"🚫 Ошибка соединения: {e}")
            return None

async def send_private_message(sender: str, recipient: str, message: str):
    """Асинхронная отправка приватного сообщения"""
    public_key_pem = await get_remote_public_key(recipient)
    if not public_key_pem:
        return None
    
    encrypted = encrypt_message(message, public_key_pem)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/send_private",
                json={
                    "sender": sender,
                    "recipient": recipient,
                    "encrypted_key": encrypted["encrypted_key"],
                    "iv": encrypted["iv"],
                    "ciphertext": encrypted["ciphertext"]
                }
            ) as response:
                if response.status == 200:
                    print("✉️ Приватное сообщение отправлено!")
                    return await response.json()
                else:
                    print(f"❌ Ошибка отправки: {response.status}")
                    return None
        except Exception as e:
            print(f"🚫 Ошибка соединения: {e}")
            return None

async def get_private_messages(username: str, limit: int = 100):
    """Асинхронное получение сообщений"""
    params = {"limit": limit}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{BASE_URL}/private_messages/{username}",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ Ошибка получения: {response.status}")
                    return None
        except Exception as e:
            print(f"🚫 Ошибка соединения: {e}")
            return None

def print_private_messages(messages, username):
    """Вывод сообщений с улучшенным форматированием"""
    if not messages:
        print("\n📭 Нет приватных сообщений")
        return
    
    print("\n" + "="*50)
    print("📬 ПРИВАТНЫЕ СООБЩЕНИЯ".center(50))
    print("="*50)
    
    for msg in messages:
        private_key = load_private_key(username)
        if not private_key:
            print("🔐 Приватный ключ не найден")
            continue
            
        try:
            decrypted = decrypt_message(
                private_key,
                msg["encrypted_key"],
                msg["iv"],
                msg["ciphertext"]
            )
            direction = "→" if msg["sender"] == username else "←"
            color = "\033[94m" if direction == "→" else "\033[92m"
            other_user = msg["recipient"] if direction == "→" else msg["sender"]
            
            print(f"\n{color}[{msg['timestamp']}] {direction} {other_user}\033[0m")
            print(f"   {decrypted}")
            print("-"*50)
        except Exception as e:
            print(f"🔓 Ошибка дешифрования: {e}")

async def websocket_listener(username: str):
    """Асинхронный WebSocket listener"""
    uri = f"ws://localhost:8000/ws/{username}"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                async for message in websocket:
                    data = json.loads(message)
                    await realtime_queue.put(data)
        except Exception as e:
            print(f"🔌 WebSocket error: {e}, reconnecting in 5 seconds...")
            await asyncio.sleep(5)

async def handle_realtime_messages(username):
    """Обработка сообщений в реальном времени"""
    while True:
        if not realtime_queue.empty():
            msg = await realtime_queue.get()
            if msg.get("type") == "private_message" and msg["recipient"] == username:
                try:
                    private_key = load_private_key(username)
                    decrypted = decrypt_message(
                        private_key,
                        msg["encrypted_key"],
                        msg["iv"],
                        msg["ciphertext"]
                    )
                    print("\n" + "="*50)
                    print(f"\033[93m✉️ НОВОЕ СООБЩЕНИЕ ОТ {msg['sender']}!\033[0m")
                    print(f"   {decrypted}")
                    print("="*50)
                    print("\n>>> Введите команду: ", end="", flush=True)
                except Exception as e:
                    print(f"🔓 Ошибка дешифрования: {e}")
        await asyncio.sleep(0.1)

def print_menu():
    """Визуально улучшенное меню"""
    print("\n" + "="*50)
    print("🔐 СИСТЕМА ЗАЩИЩЕННЫХ СООБЩЕНИЙ".center(50))
    print("="*50)
    print("1. 🔄 Обменять ключи")
    print("2. 🔑 Получить чужой публичный ключ")
    print("3. ✉️ Отправить приватное сообщение")
    print("4. 📬 Получить приватные сообщения")
    print("5. 🚪 Выход")
    print("="*50)

async def main():
    ensure_keys_dir()
    username = None
    
    print("\033[94m" + "="*50)
    print("🔐 СИСТЕМА ЗАЩИЩЕННЫХ СООБЩЕНИЙ С E2E ШИФРОВАНИЕМ".center(50))
    print("="*50 + "\033[0m")
    
    while not username:
        username = input("👤 Введите ваше имя пользователя: ")
        if not username:
            print("🚫 Имя пользователя не может быть пустым!")
    
    # Генерация/загрузка ключей
    private_key = load_private_key(username)
    public_key = load_public_key(username)
    
    if not private_key or not public_key:
        print("🔑 Генерация новых ключей...")
        private_pem, public_pem = generate_keys()
        save_keys(private_pem, public_pem, username)
        print(f"✅ Ключи сохранены в {KEYS_DIR}/")
    
    # Запуск фоновых задач
    asyncio.create_task(websocket_listener(username))
    asyncio.create_task(handle_realtime_messages(username))
    
    # Главный цикл
    while True:
        print_menu()
        choice = input("\n>>> Введите команду: ")
        
        if choice == "1":
            if await exchange_keys(username):
                print("✅ Ключи успешно обновлены на сервере")
            
        elif choice == "2":
            target = input("👥 Чей ключ получить? ")
            key = await get_remote_public_key(target)
            if key:
                print(f"🔑 Публичный ключ пользователя {target}:")
                print(key.decode())
            
        elif choice == "3":
            recipient = input("👤 Получатель: ")
            message = input("💬 Сообщение: ")
            await send_private_message(username, recipient, message)
            
        elif choice == "4":
            limit = input("📊 Лимит сообщений (по умолчанию 100): ")
            try:
                limit = int(limit) if limit.strip() else 100
            except ValueError:
                limit = 100
            messages = await get_private_messages(username, limit)
            print_private_messages(messages, username)
            
        elif choice == "5":
            print("🚪 Выход...")
            break
            
        else:
            print("🚫 Некорректный ввод")

if __name__ == "__main__":
    # Установка цветовой поддержки для Windows
    if sys.platform == "win32":
        import colorama
        colorama.init()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🚫 Приложение завершено")