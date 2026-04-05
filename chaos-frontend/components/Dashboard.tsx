"use client";
import { useState } from 'react';
import TopologyMap from './TopologyMap';
import NodeDetails from './NodeDetails';
import SidebarLogs from './SidebarLogs';

export default function Dashboard({ gameState, setGameState }: { gameState: any, setGameState: any }) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  return (
    <div className="h-screen flex flex-col bg-chaos-bg text-white overflow-hidden font-mono">
      <header className="h-16 border-b border-gray-800 bg-[#0A0C10] flex items-center px-6 justify-between shrink-0">
        <div className="flex items-center space-x-8">
          <h1 className="font-bold text-xl tracking-widest flex items-center gap-2">
            <span className="text-chaos-cyan">⚙</span> CHAOS NETWORK
          </h1>
        </div>
        <div className="flex space-x-6 items-center bg-gray-900 px-4 py-2 rounded border border-gray-800">
           <span className="text-chaos-text text-sm">
             BUDGET: <span className="text-white font-bold">{gameState.steps_remaining} steps</span>
           </span>
           <span className={`text-sm font-bold flex items-center gap-2 ${gameState.system_health < 0.5 ? 'text-chaos-red animate-pulse' : 'text-green-400'}`}>
             INTEGRITY: {(gameState.system_health * 100).toFixed(0)}%
           </span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 relative p-8 overflow-auto bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#111318] to-[#0A0C10]">
          {selectedNode ? (
             <NodeDetails 
                nodeId={selectedNode} 
                nodeData={gameState.nodes[selectedNode]} 
                gameState={gameState}
                setGameState={setGameState}
                onBack={() => setSelectedNode(null)}
             />
          ) : (
             <TopologyMap 
                nodes={gameState.nodes} 
                onSelectNode={setSelectedNode} 
             />
          )}
        </main>
        <aside className="w-96 border-l border-gray-800 bg-chaos-panel flex flex-col">
          <SidebarLogs logs={gameState.intervention_log} alerts={gameState.active_alerts} />
        </aside>
      </div>
    </div>
  );
}