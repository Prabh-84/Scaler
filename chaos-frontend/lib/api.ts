const API_URL = 'http://localhost:7860'; // Change this to your laptop's IP later!

export const api = {
  getTasks: async () => {
    const res = await fetch(`${API_URL}/tasks`);
    return res.json();
  },
  resetEnv: async (scenarioId: string = 'easy_e1') => {
    const res = await fetch(`${API_URL}/reset?scenario_id=${scenarioId}`, { method: 'POST' });
    return res.json();
  },
  step: async (action: string, target: string, failureType?: string) => {
    const body = { action, target, failure_type: failureType || null };
    const res = await fetch(`${API_URL}/step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return res.json();
  }
};