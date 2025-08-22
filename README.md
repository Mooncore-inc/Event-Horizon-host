# Event Horizon Chat 🚀

**End-to-End Encrypted Messenger Backend** - высокопроизводительный бэкенд для e2ee мессенджера с фокусом на безопасность, масштабируемость и простоту использования.

## 🌟 Особенности

- **🔐 End-to-End Шифрование** - все сообщения шифруются на клиентах
- **⚡ Real-time Messaging** - WebSocket для мгновенной доставки сообщений
- **🆔 DID-based Identity** - децентрализованная идентификация пользователей
- **📱 Масштабируемая архитектура** - легко расширяемая модульная структура
- **🔄 Public Key Exchange** - безопасный обмен публичными ключами
- **📊 Мониторинг и логирование** - встроенная система наблюдения
- **🚀 FastAPI** - современный, быстрый веб-фреймворк

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.8+
- pip (менеджер пакетов Python)

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/Mooncore-inc/Event-Horizon-host.git
cd Event-Horizon-host
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Запустите приложение:**
```bash
python -m app.main
```

Приложение будет доступно по адресу: `http://localhost:8000`

### Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# База данных
DATABASE_URL=sqlite+aiosqlite:///./database.db

# Сервер
HOST=0.0.0.0
PORT=8000

# Логирование
LOG_LEVEL=INFO
DEBUG=false

# JWT настройки
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate limiting
RATE_LIMIT_PER_MINUTE=100

# Ротация ключей (автоматическая)
KEY_ROTATION_INTERVAL_HOURS=24
MAX_PREVIOUS_KEYS=3
```

**🔒 ВАЖНО ПО БЕЗОПАСНОСТИ:**
- **SECRET_KEY генерируется автоматически** при каждом запуске
- **Не может быть изменен** через переменные окружения
- **Ротация ключей происходит автоматически** каждые 24 часа
- **Нет API endpoints** для принудительной смены ключей

## 📚 API Документация

### 🔑 Управление ключами

#### Обмен публичным ключом
```http
POST /api/v1/keys/exchange
Content-Type: application/json

{
  "did": "did:example:user123",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
}
```

**Ответ:**
```json
{
  "status": "success",
  "message": "Public key saved successfully",
  "did": "did:example:user123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Получение публичного ключа
```http
GET /api/v1/keys/{did}
```

**Ответ:**
```json
{
  "did": "did:example:user123",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
  "last_updated": "2024-01-01T12:00:00Z"
}
```

#### Получение JWT токена для WebSocket
```http
POST /api/v1/keys/{did}/token
```

**Ответ:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "did": "did:example:user123"
}
```

#### Генерация HMAC подписи для WebSocket
```http
POST /api/v1/keys/{did}/signature
```

**Ответ:**
```json
{
  "signature": "a1b2c3d4e5f6...",
  "timestamp": "2024-01-01T12:00:00Z",
  "did": "did:example:user123",
  "expires_in": 300
}
```

#### Отзыв публичного ключа
```http
DELETE /api/v1/keys/{did}
```

**Ответ:**
```json
{
  "status": "success",
  "message": "Public key revoked successfully",
  "did": "did:example:user123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Отзыв JWT токена
```http
POST /api/v1/keys/{did}/revoke-token
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Blacklist JWT токена
```http
POST /api/v1/keys/{did}/blacklist-token
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Информация о токене
```http
POST /api/v1/keys/{did}/token-info
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ответ:**
```json
{
  "did": "did:example:user123",
  "issued_at": "2024-01-01T12:00:00Z",
  "expires_at": "2024-01-01T12:30:00Z",
  "time_until_exp": 1800,
  "is_expired": false,
  "is_revoked": false,
  "is_blacklisted": false,
  "token_type": "access",
  "jti": "token_a1b2c3d4e5f6..."
}
```

#### Информация о ротации ключей
```http
GET /api/v1/keys/key-rotation/info
```

**Ответ:**
```json
{
  "status": "success",
  "key_rotation": {
    "current_key_hash": "a1b2c3d4e5f6...",
    "last_rotation": "2024-01-01T12:00:00Z",
    "next_rotation": "2024-01-02T12:00:00Z",
    "rotation_interval_hours": 24,
    "previous_keys_count": 2,
    "total_keys_managed": 3
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**🔒 БЕЗОПАСНОСТЬ: Принудительная ротация ключей отключена**
- **Нет API endpoints** для принудительной смены ключей
- **Ротация происходит только автоматически** каждые 24 часа
- **Это предотвращает атаки** злоумышленников на принудительную смену ключей

### 💬 Сообщения

#### Отправка приватного сообщения
```http
POST /api/v1/messages/send
Content-Type: application/json

{
  "sender_did": "did:example:sender123",
  "recipient_did": "did:example:recipient456",
  "encrypted_key": "base64_encoded_encrypted_symmetric_key",
  "iv": "base64_encoded_initialization_vector",
  "ciphertext": "base64_encoded_encrypted_message"
}
```

**Ответ:**
```json
{
  "id": "uuid-message-id",
  "sender_did": "did:example:sender123",
  "recipient_did": "did:example:recipient456",
  "encrypted_key": "base64_encoded_encrypted_symmetric_key",
  "iv": "base64_encoded_initialization_vector",
  "ciphertext": "base64_encoded_encrypted_message",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Получение сообщений пользователя
```http
GET /api/v1/messages/{did}?limit=50&offset=0
```

**Ответ:**
```json
{
  "messages": [
    {
      "id": "uuid-message-id",
      "sender_did": "did:example:sender123",
      "recipient_did": "did:example:recipient456",
      "encrypted_key": "...",
      "iv": "...",
      "ciphertext": "...",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### 🌐 WebSocket

#### Подключение к WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/did:example:user123');

ws.onopen = function() {
    console.log('Connected to Event Horizon Chat');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};
```

#### Типы WebSocket сообщений

**Приветственное сообщение:**
```json
{
  "type": "welcome",
  "data": {
    "message": "Welcome to Event Horizon Chat!",
    "did": "did:example:user123",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

**Heartbeat:**
```json
{
  "type": "heartbeat",
  "data": {
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

**Приватное сообщение:**
```json
{
  "type": "private_message",
  "sender_did": "did:example:sender123",
  "recipient_did": "did:example:recipient456",
  "encrypted_key": "...",
  "iv": "...",
  "ciphertext": "...",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 🏥 Система

#### Проверка здоровья
```http
GET /api/v1/system/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "database": "connected"
}
```

#### Информация о приложении
```http
GET /api/v1/system/info
```

### 📊 Статистика

#### Обзор системы
```http
GET /api/v1/stats/overview
```

**Ответ:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "users": {
    "total": 150,
    "connected": 45,
    "online_percentage": 30.0
  },
  "messages": {
    "total": 1250,
    "last_24h": 89,
    "rate_per_hour": 3.71
  },
  "system": {
    "status": "healthy",
    "uptime": "running"
  }
}
```

#### Активность пользователей
```http
GET /api/v1/stats/users/activity
```

#### Тренды сообщений
```http
GET /api/v1/stats/messages/trends
```

## 🔐 Безопасность

### Шифрование

- **End-to-End шифрование** - все сообщения шифруются на клиентах
- **Гибридное шифрование** - комбинация асимметричного и симметричного шифрования
- **DID-based аутентификация** - децентрализованная идентификация
- **Public Key Infrastructure** - безопасный обмен ключами

### Рекомендации по безопасности

1. **Используйте HTTPS в продакшене**
2. **Настройте CORS для ваших доменов**
3. **SECRET_KEY генерируется автоматически** - не требует ручной настройки
4. **Ограничьте доступ к API по IP адресам**
5. **Регулярно обновляйте зависимости**
6. **Ротация ключей происходит автоматически** - не требует вмешательства

### 🔐 Аутентификация WebSocket

Приложение поддерживает несколько методов аутентификации для WebSocket соединений:

#### 🔒 Безопасность JWT токенов

**Многоуровневая защита:**
- **Подпись токена** - каждый токен подписан секретным ключом
- **Время жизни** - токены автоматически истекают
- **Уникальный ID** - каждый токен имеет уникальный идентификатор (JTI)
- **Blacklist** - скомпрометированные токены можно заблокировать навсегда
- **Revoke** - токены можно отозвать до истечения срока
- **Автоочистка** - истекшие токены автоматически удаляются из памяти

**Защита от подмены:**
- Даже если токен украден из БД, его нельзя подделать без знания `SECRET_KEY`
- При изменении `SECRET_KEY` все существующие токены становятся недействительными
- Каждый токен проверяется на сервере при каждом запросе

#### 🔄 Автоматическая ротация SECRET_KEY

**Безопасность:**
- **Автоматическая смена** каждые 24 часа (настраивается)
- **Обратная совместимость** - поддерживаются последние N ключей (настраивается)
- **Автоматическая генерация** - ключ генерируется при каждом запуске
- **Безопасная генерация** - используются криптографически стойкие ключи
- **Автоочистка** - старые ключи автоматически удаляются
- **Нет внешнего доступа** - ротация происходит только автоматически

**Что происходит при ротации:**
- Все активные токены становятся недействительными
- Пользователи должны получить новые токены
- **Сообщения остаются в базе данных**
- WebSocket соединения разрываются (требуется переподключение)

#### JWT токен
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/did:example:user123?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...');
```

#### HMAC подпись
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/did:example:user123?signature=a1b2c3d4e5f6...&timestamp=2024-01-01T12:00:00Z');
```

#### Разработка (только в DEBUG режиме)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/did:example:user123');
```

## 📊 Мониторинг

### Логирование

Приложение автоматически логирует:
- Все API запросы
- WebSocket соединения
- Ошибки и исключения
- Операции с базой данных

### Метрики

- Количество активных WebSocket соединений
- Статистика сообщений
- Время отклика API
- Статус базы данных
- Активность пользователей
- Тренды сообщений по времени
- Процент пользователей онлайн
- Скорость обработки запросов

## 🧪 Тестирование

### Запуск тестов
```bash
pytest
```

### Тестирование с coverage
```bash
pytest --cov=app
```

### Простое тестирование API
```bash
python test_api.py
```

Этот скрипт проверит все основные endpoints и выведет результаты тестирования.

### Демонстрация безопасности JWT
```bash
python security_demo.py
```

Этот скрипт демонстрирует различные аспекты безопасности JWT токенов, включая защиту от подмены.

### Демонстрация ротации ключей
```bash
python key_rotation_demo.py
```

Этот скрипт демонстрирует автоматическую ротацию SECRET_KEY каждые 24 часа и обратную совместимость.

## 📄 Лицензия

Этот проект лицензирован под GNU GPLv3 — см. файл [LICENSE](LICENSE) для подробностей.

---

**Event Horizon Chat** - где безопасность встречается с простотой! 🚀🔐