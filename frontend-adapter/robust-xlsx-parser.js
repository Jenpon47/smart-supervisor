/*
  Header Mapping + Data Validation helper for SheetJS rows.
  Use this before confirmImport. It rejects rows where green+yellow+red != total.
*/
(function () {
  const HEADER_KEYS = {
    schoolName: ['ชื่อโรงเรียน', 'โรงเรียน', 'สถานศึกษา'],
    total: ['นร.เข้าสอบ', 'เข้าสอบ', 'ผู้เข้าสอบ', 'จำนวนนักเรียน', 'นร. ทั้งหมด'],
    green: ['กลุ่มเขียว', 'เขียว', 'green', '🟢'],
    yellow: ['กลุ่มเหลือง', 'เหลือง', 'yellow', '🟡'],
    red: ['กลุ่มแดง', 'แดง', 'red', '🔴']
  };

  function normalize(value) {
    return String(value || '').toLowerCase().replace(/\s+/g, '').replace(/[()（）:：._-]/g, '');
  }

  function findHeaderRow(rows) {
    let best = { index: -1, score: 0, map: {} };
    rows.forEach((row, index) => {
      const map = {};
      Object.entries(HEADER_KEYS).forEach(([field, keywords]) => {
        const col = row.findIndex(cell => keywords.some(k => normalize(cell).includes(normalize(k))));
        if (col >= 0) map[field] = col;
      });
      const score = Object.keys(map).length;
      if (score > best.score) best = { index, score, map };
    });
    return best.score >= 4 ? best : null;
  }

  function toInt(value) {
    const n = parseFloat(value);
    return Number.isFinite(n) ? Math.max(0, Math.round(n)) : 0;
  }

  function parseRowsWithHeaderMapping(rows, matchSchoolName, label) {
    const header = findHeaderRow(rows);
    const errors = [];
    const warnings = [];
    const records = {};

    if (!header) {
      return {
        records,
        errors: [{ row: 0, sheet: label, message: 'ไม่พบหัวตารางที่มี ชื่อโรงเรียน/เข้าสอบ/เขียว/เหลือง/แดง ครบถ้วน' }],
        warnings
      };
    }

    for (let r = header.index + 1; r < rows.length; r++) {
      const row = rows[r];
      const rawName = String(row[header.map.schoolName] || '').trim();
      if (!rawName) continue;
      const school = matchSchoolName(rawName);
      if (!school) {
        warnings.push({ row: r + 1, sheet: label, message: `ไม่พบโรงเรียนในระบบ: ${rawName}` });
        continue;
      }

      const total = toInt(row[header.map.total]);
      const green = toInt(row[header.map.green]);
      const yellow = toInt(row[header.map.yellow]);
      const red = toInt(row[header.map.red]);
      const checksum = green + yellow + red;

      if (total <= 0) {
        errors.push({ row: r + 1, schoolId: school.id, schoolName: school.name, sheet: label, message: 'จำนวนผู้เข้าสอบต้องมากกว่า 0' });
        continue;
      }
      if (checksum !== total) {
        errors.push({
          row: r + 1,
          schoolId: school.id,
          schoolName: school.name,
          sheet: label,
          message: `ผลรวมกลุ่มสี ${checksum} ไม่ตรงกับผู้เข้าสอบ ${total}`
        });
        continue;
      }

      records[school.id] = { schoolId: school.id, name: school.name, total, green, yellow, red };
    }

    return { records, errors, warnings, headerRow: header.index + 1, headerMap: header.map };
  }

  window.RobustXLSXParser = {
    parseRowsWithHeaderMapping,
    findHeaderRow
  };
})();
