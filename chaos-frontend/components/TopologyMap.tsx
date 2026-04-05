"use client";
import { EyeOff, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function TopologyMap({ nodes, onSelectNode }: { nodes: any, onSelectNode: (id: string) => void }) {
  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-wider mb-2">SYSTEM TOPOLOGY</h2>
        <p className="text-chaos-text text-sm">Select a node to view detailed telemetry and execute remediation protocols.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-max">
        {Object.entries(nodes).map(([id, node]: [string, any]) => {
          const isHidden = node.health === "hidden";
          const isCritical = node.status === "critical";
          
          return (
            <div 
              key={id}
              onClick={() => onSelectNode(id)}
              className={`p-6 rounded border cursor-pointer transition-all duration-200 group
                ${isHidden ? 'bg-gray-900 border-gray-800 hover:border-gray-600' : 
                  isCritical ? 'bg-red-950/20 border-chaos-red/50 hover:border-chaos-red hover:shadow-[0_0_15px_rgba(255,77,77,0.2)]' : 
                  'bg-chaos-panel border-gray-700 hover:border-chaos-cyan hover:shadow-[0_0_15px_rgba(0,229,255,0.1)]'}
              `}
            >
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-lg uppercase group-hover:text-chaos-cyan transition-colors">{id.replace('_', ' ')}</h3>
                {isHidden ? <EyeOff size={20} className="text-gray-600" /> : 
                 isCritical ? <AlertTriangle size={20} className="text-chaos-red animate-pulse" /> : 
                 <CheckCircle2 size={20} className="text-green-500" />}
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-chaos-text">Status</span>
                  <span className={isHidden ? 'text-gray-600' : isCritical ? 'text-chaos-red font-bold' : 'text-green-400'}>
                    {isHidden ? 'UNKNOWN' : node.status.toUpperCase()}
                  </span>
                </div>
                {!isHidden && (
                  <div className="flex justify-between">
                    <span className="text-chaos-text">Health</span>
                    <span>{(node.health * 100).toFixed(1)}%</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}