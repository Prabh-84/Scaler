// "use client";
// import { useState } from 'react';
// import { api } from '../lib/api';

// export default function LandingPage({ onStart }: { onStart: (state: any) => void }) {
//   const [loading, setLoading] = useState(false);

//   const handleStart = async () => {
//     setLoading(true);
//     try {
//       const state = await api.resetEnv('easy_e1');
//       onStart(state);
//     } catch (e) {
//       alert("Backend not reachable! Ensure Python server is running.");
//       console.error(e);
//     }
//     setLoading(false);
//   };

//   return (
//     <div className="min-h-screen bg-chaos-bg flex flex-col items-center justify-center p-8">
//       <div className="max-w-4xl w-full space-y-8 text-center">
//         <h4 className="text-chaos-cyan uppercase tracking-widest text-sm font-bold">Meta AI Hackathon Entry</h4>
//         <h1 className="text-6xl font-extrabold text-white leading-tight">
//           Mastering Chaos: <br/>
//           <span className="text-chaos-cyan">AI-Powered Root Cause Analysis in Distributed Systems</span>
//         </h1>
//         <p className="text-chaos-text text-lg max-w-2xl mx-auto">
//           Introducing The Agent's Dilemma. A simulated microservice ecosystem designed to fail in complex, non-obvious ways. Can you identify the root cause, or will you fall for the traps?
//         </p>
//         <div className="pt-8">
//           <button 
//             onClick={handleStart}
//             disabled={loading}
//             className="bg-chaos-cyan text-black px-10 py-4 font-bold rounded shadow-[0_0_15px_rgba(0,229,255,0.4)] hover:shadow-[0_0_25px_rgba(0,229,255,0.6)] transition-all disabled:opacity-50 tracking-wider">
//             {loading ? 'INITIALIZING...' : 'START SIMULATION'}
//           </button>
//         </div>
//       </div>
//     </div>
//   );
// }
"use client";
import { useState } from 'react';
import { api } from '../lib/api';

export default function LandingPage({ onStart }: { onStart: (state: any) => void }) {
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    setLoading(true);
    try {
      const state = await api.resetEnv('easy_e1');
      onStart(state);
    } catch (e) {
      alert("Backend not reachable! Ensure Python server is running.");
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-chaos-bg flex flex-col items-center justify-center p-8">
      <div className="max-w-4xl w-full space-y-8 text-center">
        <h3 className="text-chaos-cyan uppercase tracking-widest text-sm font-bold">
          TEAM SAGE
        </h3>

        <h1 className="text-6xl font-extrabold text-white leading-tight">
          Mastering Chaos: <br/>
          <span className="text-chaos-cyan text-3xl">
            AI-Powered Root Cause Analysis in Distributed Systems
          </span>
        </h1>

        <p className="text-chaos-text text-lg max-w-2xl mx-auto">
         A microservice environment where failures are designed to mislead.
The obvious fix is often wrong , the real cause lies deeper.
Identify the root cause before your steps run out.
        </p>

        <div className="pt-8">
          <button 
            onClick={handleStart}
            disabled={loading}
            className="bg-chaos-cyan text-black px-10 py-4 font-bold rounded shadow-[0_0_15px_rgba(0,229,255,0.4)] hover:shadow-[0_0_25px_rgba(0,229,255,0.6)] transition-all disabled:opacity-50 tracking-wider">
            {loading ? 'INITIALIZING...' : 'START SIMULATION'}
          </button>
        </div>
      </div>
    </div>
  );
}