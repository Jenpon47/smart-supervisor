# Frontend Adapter

`smart-supervision-api-client.js` สร้าง `window.SmartAPI` เพื่อให้ `index.html` เรียก backend:

- `SmartAPI.syncSchools(SCHOOLS)`
- `SmartAPI.createCoachingLog(log)`
- `SmartAPI.strategicInsight()`
- `SmartAPI.setApiBase(url)`

ค่า API base อ่านจาก `localStorage.SMART_API_BASE`, `window.SMART_SUPERVISION_CONFIG.API_BASE`, หรือ fallback เป็น `http://127.0.0.1:8000`
