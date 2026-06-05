# แผนพาระบบ Smart Supervision ไป Production

## Phase 1: ทำให้ข้อมูลไม่หายและ sync ได้

เป้าหมาย: หน้า HTML เดิมยังใช้ได้ แต่ข้อมูลสำคัญถูกส่งเข้า backend

- รัน backend FastAPI
- เพิ่ม `smart-supervision-api-client.js` ใน HTML
- sync `SCHOOLS` หลัง `saveData()`
- sync `Coaching Log` หลัง `saveLogs()`
- เก็บ SQLite ชั่วคราวก่อน แล้วค่อยย้ายเป็น PostgreSQL/Firestore

ผลลัพธ์ที่ต้องเห็น:

- เปิด `/health` แล้ว status เป็น `ok`
- กดบันทึก Coaching Log แล้ว backend มี record ใหม่
- ปิด/ล้าง browser cache แล้วข้อมูลยังดึงกลับจาก backend ได้

## Phase 2: Login และสิทธิ์

เป้าหมาย: แยกผู้ใช้จริง 3 กลุ่ม

- Admin: import, KPI, ทีม ศน., dashboard เขต
- Supervisor: บันทึก log และแก้ข้อมูลโรงเรียนที่รับผิดชอบ
- Viewer: ดูเฉพาะโรงเรียนตัวเองและ next step

จุดที่ต้องเปลี่ยน:

- แทน `current_user()` ใน backend ด้วย Google Workspace OAuth/JWT
- map email หรือ Google Group เป็น role
- frontend ซ่อนเมนูตาม role ที่ backend ส่งมา ไม่ใช้การสลับสิทธิ์แบบ JS อย่างเดียว

## Phase 3: Excel Import ที่ทนต่อไฟล์จริง

เป้าหมาย: ไม่พังเมื่อโรงเรียนสลับคอลัมน์

- ใช้ `robust-xlsx-parser.js`
- ตรวจหัวตารางด้วย keyword เช่น `ชื่อโรงเรียน`, `เข้าสอบ`, `กลุ่มแดง`
- reject ไฟล์ทันทีถ้า `เขียว + เหลือง + แดง != ผู้เข้าสอบ`
- แสดง row/sheet/school ที่ผิดให้ผู้ใช้แก้ได้

## Phase 4: AI จริงผ่าน backend

เป้าหมาย: ให้ AI วิเคราะห์จาก JSON จริง ไม่ใช่ hard-coded text

- frontend ส่ง Priority List, district stats, recent logs ไป `/ai/strategic-insight`
- backend เรียก Gemini API โดยเก็บ API key ใน `.env`
- ถ้าไม่มี key ให้ใช้ fallback local insight เพื่อไม่ให้ระบบล่ม
- ให้ผู้ใช้ตรวจ/แก้ข้อความก่อนเผยแพร่

## Phase 5: Notification และ Nudge

เป้าหมาย: Next Step ไปถึงคนที่ต้องทำงานต่อ

- เมื่อบันทึก Coaching Log ให้ส่ง LINE ไปยังผู้รับผิดชอบ
- เพิ่ม scheduled job ตรวจโรงเรียนสีแดงที่ไม่มี log หรือข้อมูลใหม่เกิน 14 วัน
- ส่ง nudge ให้ ศน. เจ้าภาพ
- เก็บ audit ในตาราง `notifications`

## สิ่งที่ยังไม่ควรรีบทำ

- อย่าเริ่มจาก AI เต็มรูปแบบก่อนข้อมูลนิ่ง
- อย่าใช้ frontend เรียก Gemini/LINE โดยตรง เพราะ key จะรั่ว
- อย่า import ไฟล์ที่ validation ไม่ผ่าน แม้จะเป็น warning เล็ก ๆ ในเดโมเดิม
