const API_URL = ""; // HF te same domain use hovega

export const api = {
  getTasks: async () => {
    const res = await fetch(`/tasks`);
    if (!res.ok) throw new Error("Failed to fetch tasks");
    return res.json();
  },

  resetEnv: async (scenarioId: string = "easy_e1") => {
    const res = await fetch(`/reset?scenario_id=${scenarioId}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to reset environment");
    return res.json();
  },

  step: async (action: string, target: string, failureType?: string) => {
    const body = { action, target, failure_type: failureType || null };

    const res = await fetch(`/step`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error("Step execution failed");
    return res.json();
  },
};