/*
  Drop this script after the existing app script, then call SmartAPI methods
  from saveTk1/saveTk4/confirmImport/generateAIInsight as you migrate features.
*/
(function () {
  const runtimeConfig = window.SMART_SUPERVISION_CONFIG || {};
  const API_BASE = localStorage.getItem('SMART_API_BASE') || runtimeConfig.API_BASE || 'http://127.0.0.1:8000';

  function hasMetric(value) {
    return value !== null && value !== undefined && value !== '' && !Number.isNaN(Number(value));
  }

  function nullableNumber(value) {
    return hasMetric(value) ? Number(value) : null;
  }

  async function request(path, options) {
    const res = await fetch(API_BASE + path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Demo-Role': localStorage.getItem('SMART_DEMO_ROLE') || 'admin',
        ...((options && options.headers) || {})
      }
    });
    if (!res.ok) {
      let detail = await res.text();
      try { detail = JSON.stringify(JSON.parse(detail), null, 2); } catch (_) {}
      throw new Error(detail);
    }
    return res.json();
  }

  function schoolToApi(s) {
    return {
      id: s.id,
      name: s.name,
      district: s.district || s.cluster || '',
      flag: s.flag || 'gray',
      red: Number(s.red || 0),
      prev: Number(s.prev || 0),
      min15: nullableNumber(s.min15),
      adjust: nullableNumber(s.adjust),
      sim: s.sim || null,
      supervisor_id: s.supervisorId || null,
      payload: s
    };
  }

  function buildInsightPayload() {
    const schools = (window.SCHOOLS || []).slice();
    const priority = schools
      .sort((a, b) => (window.calcPriorityScore ? window.calcPriorityScore(b) - window.calcPriorityScore(a) : (b.red || 0) - (a.red || 0)))
      .slice(0, 10)
      .map(s => ({
        id: s.id,
        name: s.name,
        red: s.red,
        min15: s.min15,
        adjust: s.adjust,
        sim: s.sim,
        flag: s.flag,
        priorityScore: window.calcPriorityScore ? window.calcPriorityScore(s) : s.red
      }));

    const stats = window.calcDistrictStats ? window.calcDistrictStats() : {
      total: schools.length,
      avgRed: Math.round(schools.reduce((sum, s) => sum + Number(s.red || 0), 0) / Math.max(schools.length, 1))
    };

    return {
      district_name: 'Smart Supervision District',
      priority_schools: priority,
      district_stats: stats,
      recent_logs: (window.LOGS || []).slice(0, 30)
    };
  }

  window.SmartAPI = {
    API_BASE,
    setApiBase: value => {
      if (value) localStorage.setItem('SMART_API_BASE', value);
      else localStorage.removeItem('SMART_API_BASE');
    },
    health: () => request('/health'),
    me: () => request('/me'),
    listSchools: () => request('/schools'),
    syncSchools: schools => request('/schools/bulk', {
      method: 'POST',
      body: JSON.stringify((schools || window.SCHOOLS || []).map(schoolToApi))
    }),
    createCoachingLog: log => request('/coaching-logs', {
      method: 'POST',
      body: JSON.stringify({
        school_id: log.schoolId,
        teacher: log.teacher,
        log_type: log.type || 'coaching',
        next_step: log.nextStep || '',
        followup: log.followup || null,
        payload: log,
        notify: true
      })
    }),
    createScreeningImport: parsed => request('/screening/imports', {
      method: 'POST',
      body: JSON.stringify(parsed)
    }),
    strategicInsight: () => request('/ai/strategic-insight', {
      method: 'POST',
      body: JSON.stringify(buildInsightPayload())
    })
  };
})();
