"use client";
import { api } from '../lib/api';
import { Activity, ArrowLeft, RefreshCw, RotateCcw, TrendingUp, Eye, CheckCircle } from 'lucide-react';

export default function NodeDetails({ nodeId, nodeData, gameState, setGameState, onBack }: any) {
  
  const handleAction = async (action: string) => {
    try {
      const result = await api.step(action, nodeId);
      setGameState(result.observation || result);
      
      if (result.done) {
        const scoreData = await fetch('http://localhost:7860/grader').then(res => res.json());
        alert(`EPISODE COMPLETE!\nFinal Score: ${(scoreData.total * 100).toFixed(1)}%`);
      }
    } catch (e) {
      console.error("Action failed:", e);
    }
  };

  const isHidden = nodeData.health === "hidden";

  return (
    <div className="flex flex-col h-full space-y-8">
      <div className="flex items-center space-x-6 border-b border-gray-800 pb-6">
        <button onClick={onBack} className="p-3 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded transition-colors text-gray-300">
          <ArrowLeft size={24}/>
        </button>
        <div>
          <h2 className="text-sm text-chaos-cyan font-bold tracking-widest uppercase">Target Node</h2>
          <h1 className="text-4xl font-bold uppercase tracking-wide">{nodeId.replace('_', ' ')}</h1>
        </div>
      </div>

      {isHidden ? (
         <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-gray-700 rounded-xl bg-[#0A0C10] max-h-[400px]">
            <Eye size={64} className="text-gray-600 mb-6" />
            <h3 className="text-2xl font-bold mb-2">Telemetry Data Hidden</h3>
            <p className="text-chaos-text mb-8 max-w-md text-center">Execute an observation action to reveal real-time metrics.</p>
            <button onClick={() => handleAction('observe')} className="bg-chaos-cyan text-black px-8 py-3 font-bold rounded shadow-[0_0_15px_rgba(0,229,255,0.3)] hover:shadow-[0_0_20px_rgba(0,229,255,0.5)] transition-all">
              EXECUTE OBSERVATION
            </button>
         </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1">
          <div className="bg-chaos-panel p-8 rounded border border-gray-800 flex flex-col">
             <h3 className="text-sm text-chaos-cyan font-bold tracking-widest mb-6 border-b border-gray-800 pb-2">
               <Activity size={18} className="inline mr-2"/> REMEDIATION PROTOCOLS
             </h3>
             <div className="grid grid-cols-1 gap-4 flex-1">
                <ActionCard title="Restart Service" desc="Clears transient memory leaks." icon={<RefreshCw size={20}/>} onClick={() => handleAction('restart')} />
                <ActionCard title="Rollback Deployment" desc="Reverts service image to previous stable build." icon={<RotateCcw size={20}/>} onClick={() => handleAction('rollback')} />
                <ActionCard title="Scale Up Pods" desc="Increase replica count." icon={<TrendingUp size={20}/>} onClick={() => handleAction('scale_replica')} />
             </div>
             <div className="mt-8 pt-6 border-t border-gray-800">
               <button onClick={() => handleAction('declare_root_cause')} className="w-full py-4 border border-chaos-cyan text-chaos-cyan font-bold hover:bg-chaos-cyan hover:text-black transition-colors rounded tracking-widest uppercase">
                  Declare Root Cause
               </button>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActionCard({ title, desc, icon, onClick }: any) {
  return (
    <div onClick={onClick} className="border border-gray-700 bg-gray-900/50 p-5 rounded hover:border-chaos-cyan hover:bg-chaos-cyan/5 cursor-pointer transition-all group">
      <div className="flex items-center space-x-4 mb-2 text-gray-200 group-hover:text-chaos-cyan">
        {icon}
        <h4 className="font-bold text-lg">{title}</h4>
      </div>
      <p className="text-sm text-gray-400 pl-9">{desc}</p>
    </div>
  )
}