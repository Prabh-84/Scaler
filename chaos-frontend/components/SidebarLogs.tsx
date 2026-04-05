"use client";
import { Terminal, ShieldAlert } from 'lucide-react';

export default function SidebarLogs({ logs, alerts }: { logs: any[], alerts: any[] }) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-gray-800 bg-[#0A0C10]">
        <h3 className="text-xs text-chaos-text font-bold tracking-widest mb-3 flex items-center gap-2">
          <ShieldAlert size={14}/> ACTIVE ALERTS
        </h3>
        <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
          {alerts.length === 0 ? (
            <p className="text-xs text-green-400">No critical alerts detected.</p>
          ) : (
            alerts.map((alert, idx) => (
              <div key={idx} className="bg-red-950/30 border-l-2 border-chaos-red p-2 text-xs rounded-r">
                <span className="font-bold text-chaos-red">{alert.node}</span>: {alert.type}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="p-4 flex-1 overflow-hidden flex flex-col">
        <h3 className="text-xs text-chaos-text font-bold tracking-widest mb-3 flex items-center gap-2">
          <Terminal size={14}/> AGENT PATH HISTORY
        </h3>
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
          {logs.length === 0 ? (
            <p className="text-xs text-gray-600 font-mono">Awaiting commands...</p>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className="relative pl-4 border-l border-gray-700 pb-2">
                <div className="text-[10px] text-gray-500 mb-1">STEP {idx + 1}</div>
                <div className="text-sm text-gray-200 font-bold uppercase tracking-wider mb-1">
                  {log.action}
                </div>
                <div className="text-xs text-chaos-text">
                  Target: <span className="text-white">{log.target}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}