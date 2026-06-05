# Smart Supervision Production Starter

ชุดนี้คือฐานเริ่มต้นสำหรับยกระดับไฟล์ `smart_supervision_app (6).html` จาก single-page/localStorage demo ไปเป็นระบบ client-server แบบค่อยเป็นค่อยไป

## 1. Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

ทดสอบ:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

## 2. Attach frontend adapter

เพิ่ม script 2 ตัวนี้ท้ายไฟล์ HTML เดิม หลัง script หลักของแอป:

```html
<script src="./frontend-adapter/smart-supervision-api-client.js"></script>
<script src="./frontend-adapter/robust-xlsx-parser.js"></script>
```

ถ้าเปิด HTML จากโฟลเดอร์อื่น ให้ปรับ path ตามตำแหน่งจริง หรือคัดลอกไฟล์ adapter ไปไว้ข้าง HTML เดิม

## 3. Migration points ใน HTML เดิม

### Coaching Log

ใน `saveTk1()` และ `saveTk4()` หลัง `LOGS.unshift(log); saveLogs();` เพิ่ม:

```js
if (window.SmartAPI) {
  SmartAPI.createCoachingLog(log).catch(function(err) {
    console.warn('Backend coaching sync failed', err);
    showNotification('warning', 'บันทึก local แล้ว แต่ sync backend ไม่สำเร็จ');
  });
}
```

### Sync schools

หลัง `saveData();` ในจุดที่อัปเดต dashboard เช่น `updateSchoolFromToolkit()` และ `confirmImport()` เพิ่ม:

```js
if (window.SmartAPI) {
  SmartAPI.syncSchools(SCHOOLS).catch(function(err) {
    console.warn('Backend school sync failed', err);
  });
}
```

### Real AI

ใน `generateAIInsight()` เปลี่ยนจากเรียก `buildLocalStrategicInsight()` อย่างเดียว เป็น:

```js
var aiPromise = window.SmartAPI
  ? SmartAPI.strategicInsight().then(function(res) { return res.text; })
  : Promise.resolve(buildLocalStrategicInsight());

aiPromise.then(renderAIResult).catch(function(err) {
  console.warn('AI backend failed', err);
  renderAIResult(buildLocalStrategicInsight());
});
```

### Robust Excel Import

ใน parser เดิม จุดที่ใช้ตำแหน่ง column ตายตัว เช่น `row[1]`, `row[5]`, `row[6]` ให้เปลี่ยน sheet ที่เป็นโครงสร้างสีมาตรฐานไปใช้:

```js
var rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
var parsed = RobustXLSXParser.parseRowsWithHeaderMapping(rows, matchSchoolName, 'กลุ่ม 1');
result.errors = result.errors.concat(parsed.errors);
result.warnings = result.warnings.concat(parsed.warnings);
return parsed.records;
```

ก่อน `importSetStep(2)` ให้บล็อกไฟล์ที่ผิด:

```js
if (result.errors.length > 0) {
  renderImportPreview(result);
  showNotification('error', 'พบข้อผิดพลาดในไฟล์ ต้องแก้ก่อนนำเข้า');
  importSetStep(2);
  return;
}
```

และใน `confirmImport()` ให้กันซ้ำ:

```js
if (importParsedData.errors && importParsedData.errors.length) {
  showNotification('error', 'นำเข้าไม่ได้: ยังมีข้อผิดพลาดในไฟล์');
  return;
}
```

## 4. RBAC production path

ตอนนี้ backend ใช้ `X-Demo-Role` เพื่อทดสอบ role:

- `admin`: import, จัดการโรงเรียน, AI, coaching
- `supervisor`: coaching และ sync โรงเรียนในความรับผิดชอบ
- `viewer`: อ่านข้อมูล

ขั้น production ให้แทน `current_user()` ด้วย Google Workspace OAuth/JWT verification แล้ว map email/domain/group เป็น role

## 5. Notification path

เมื่อ `POST /coaching-logs` สำเร็จ backend จะเรียก `send_line_message()`

ตอนนี้รองรับ LINE Messaging API ผ่าน env:

```env
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_DEFAULT_TO=...
```

ถ้าเขตยังใช้ LINE Notify แบบ legacy ให้แก้เฉพาะฟังก์ชัน `send_line_message()` โดยไม่กระทบ frontend

## 6. ลำดับทำงานที่แนะนำ

1. รัน backend ให้ผ่าน `/health`
2. เพิ่ม adapter เข้า HTML เดิม
3. sync `SCHOOLS` ไป backend
4. ต่อ `saveTk4()` เข้ากับ `/coaching-logs`
5. เปลี่ยน AI ให้เรียก `/ai/strategic-insight`
6. ค่อยปรับ Excel parser เป็น header mapping และ validation
