# Smart Supervision System

Frontend สำหรับระบบนิเทศอัจฉริยะ และ FastAPI backend starter สำหรับบันทึกข้อมูลจริง, Coaching Log, AI insight และ notification

## โครงสร้าง

- `index.html` แอป frontend แบบ static
- `frontend-adapter/` ตัวเชื่อม frontend กับ backend API
- `backend/` FastAPI backend starter
- `docs/` คู่มือ implementation และ roadmap

## Run frontend

```powershell
python -m http.server 3000 --bind 127.0.0.1
```

เปิด:

```
http://127.0.0.1:3000/index.html
```

## Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

ตรวจ:

```
http://127.0.0.1:8000/health
```

## Frontend API URL

ค่าเริ่มต้นชี้ไปที่:

```
http://127.0.0.1:8000
```

สำหรับ production ให้สร้าง `config.js` จาก `config.example.js` แล้วตั้ง:

```js
window.SMART_SUPERVISION_CONFIG = {
  API_BASE: 'https://your-backend.example.com'
};
```

หรือใน browser console:

```js
SmartAPI.setApiBase('https://your-backend.example.com')
```

## Security

- ห้ามใส่ Gemini API key, LINE token, database URL หรือ secret ใน `index.html`
- Secret ทั้งหมดอยู่ฝั่ง backend ใน `backend/.env`
- `.env` และ database runtime ถูก ignore ใน `.gitignore`

## GitHub Pages

GitHub Pages ใช้ host frontend ได้ แต่ backend ต้อง deploy แยก เช่น Render, Railway, Cloud Run, VPS หรือบริการอื่น
