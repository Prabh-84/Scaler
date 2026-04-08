
// "use client";

// import { api } from "../lib/api";
// import {
//   Activity,
//   ArrowLeft,
//   RefreshCw,
//   RotateCcw,
//   TrendingUp,
//   Eye,
// } from "lucide-react";

// export default function NodeDetails({
//   nodeId,
//   nodeData,
//   gameState,
//   setGameState,
//   onBack,
// }: any) {
//   const handleAction = async (action: string) => {
//     try {
//       let failureType: string | undefined = undefined;

//       if (action === "declare_root_cause") {
//         const userInput = prompt(
//           "Enter failure type (optional).\nExamples:\nprocess_crash\ntls_certificate_expired\nmemory_leak\nconnection_pool_exhaustion"
//         );
//         failureType = userInput?.trim() ? userInput.trim() : undefined;
//       }

//       const result = await api.step(action, nodeId, failureType);
//       setGameState(result.observation || result);

//       if (result.done) {
//         const scoreData = await api.getGrader();

//         const declared =
//           scoreData?.breakdown?.correct_root_cause ||
//           scoreData?.declared_root_cause ||
//           null;

//         const groundTruth =
//           scoreData?.breakdown?.ground_truth_root_cause ||
//           scoreData?.ground_truth_root_cause ||
//           "N/A";

//         const declaredText =
//           declared && typeof declared === "object"
//             ? `${declared.node ?? "N/A"}${
//                 declared.failure_type ? ` (${declared.failure_type})` : ""
//               }`
//             : declared || nodeId;

//         alert(
//           `EPISODE COMPLETE!\n\n` +
//             `Final Score: ${(Number(scoreData.total || 0) * 100).toFixed(1)}%\n` +
//             `Scenario: ${scoreData.scenario_id ?? "N/A"}\n\n` +
//             `Declared Root Cause: ${declaredText}\n` +
//             `Ground Truth Root Cause: ${groundTruth}`
//         );
//       }
//     } catch (e) {
//       console.error("Action failed:", e);
//       alert("Action failed. Please try again.");
//     }
//   };

//   const isHidden = nodeData.health === "hidden";

//   return (
//     <div className="flex flex-col h-full space-y-8">
//       <div className="flex items-center space-x-6 border-b border-gray-800 pb-6">
//         <button
//           onClick={onBack}
//           className="p-3 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded transition-colors text-gray-300"
//         >
//           <ArrowLeft size={24} />
//         </button>
//         <div>
//           <h2 className="text-sm text-chaos-cyan font-bold tracking-widest uppercase">
//             Target Node
//           </h2>
//           <h1 className="text-4xl font-bold uppercase tracking-wide">
//             {nodeId.replace("_", " ")}
//           </h1>
//         </div>
//       </div>

//       {isHidden ? (
//         <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-gray-700 rounded-xl bg-[#0A0C10] max-h-[400px]">
//           <Eye size={64} className="text-gray-600 mb-6" />
//           <h3 className="text-2xl font-bold mb-2">Telemetry Data Hidden</h3>
//           <p className="text-chaos-text mb-8 max-w-md text-center">
//             Execute an observation action to reveal real-time metrics.
//           </p>
//           <button
//             onClick={() => handleAction("observe")}
//             className="bg-chaos-cyan text-black px-8 py-3 font-bold rounded shadow-[0_0_15px_rgba(0,229,255,0.3)] hover:shadow-[0_0_20px_rgba(0,229,255,0.5)] transition-all"
//           >
//             EXECUTE OBSERVATION
//           </button>
//         </div>
//       ) : (
//         <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1">
//           <div className="bg-chaos-panel p-8 rounded border border-gray-800 flex flex-col">
//             <h3 className="text-sm text-chaos-cyan font-bold tracking-widest mb-6 border-b border-gray-800 pb-2">
//               <Activity size={18} className="inline mr-2" /> REMEDIATION
//               PROTOCOLS
//             </h3>

//             <div className="grid grid-cols-1 gap-4 flex-1">
//               <ActionCard
//                 title="Restart Service"
//                 desc="Clears transient memory leaks."
//                 icon={<RefreshCw size={20} />}
//                 onClick={() => handleAction("restart")}
//               />
//               <ActionCard
//                 title="Rollback Deployment"
//                 desc="Reverts service image to previous stable build."
//                 icon={<RotateCcw size={20} />}
//                 onClick={() => handleAction("rollback")}
//               />
//               <ActionCard
//                 title="Scale Up Pods"
//                 desc="Increase replica count."
//                 icon={<TrendingUp size={20} />}
//                 onClick={() => handleAction("scale_replica")}
//               />
//             </div>

//             <div className="mt-8 pt-6 border-t border-gray-800">
//               <button
//                 onClick={() => handleAction("declare_root_cause")}
//                 className="w-full py-4 border border-chaos-cyan text-chaos-cyan font-bold hover:bg-chaos-cyan hover:text-black transition-colors rounded tracking-widest uppercase"
//               >
//                 Declare Root Cause
//               </button>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// function ActionCard({ title, desc, icon, onClick }: any) {
//   return (
//     <div
//       onClick={onClick}
//       className="border border-gray-700 bg-gray-900/50 p-5 rounded hover:border-chaos-cyan hover:bg-chaos-cyan/5 cursor-pointer transition-all group"
//     >
//       <div className="flex items-center space-x-4 mb-2 text-gray-200 group-hover:text-chaos-cyan">
//         {icon}
//         <h4 className="font-bold text-lg">{title}</h4>
//       </div>
//       <p className="text-sm text-gray-400 pl-9">{desc}</p>
//     </div>
//   );
// }
"use client";

import { useState } from "react";
import { api } from "../lib/api";
import {
  Activity,
  ArrowLeft,
  RefreshCw,
  RotateCcw,
  TrendingUp,
  Eye,
  CheckCircle2,
  XCircle,
} from "lucide-react";

export default function NodeDetails({
  nodeId,
  nodeData,
  gameState,
  setGameState,
  onBack,
}: any) {
  const [resultModal, setResultModal] = useState<null | {
    score: string;
    scenario: string;
    declared: string;
    groundTruth: string;
    isCorrect: boolean;
  }>(null);

  const handleAction = async (action: string) => {
    try {
      const result = await api.step(action, nodeId);
      setGameState(result.observation || result);

      if (result.done) {
        const scoreData = await api.getGrader();

        const declared =
          scoreData?.breakdown?.correct_root_cause ||
          scoreData?.declared_root_cause ||
          null;

        const groundTruth =
          scoreData?.breakdown?.ground_truth_root_cause ||
          scoreData?.ground_truth_root_cause ||
          "N/A";

        const declaredText =
          declared && typeof declared === "object"
            ? `${declared.node ?? "N/A"}${
                declared.failure_type ? ` (${declared.failure_type})` : ""
              }`
            : declared || nodeId;

        const normalizedDeclared =
          typeof declared === "object" ? declared?.node ?? "" : declaredText;

        const normalizedGroundTruth =
          typeof groundTruth === "object"
            ? groundTruth?.node ?? ""
            : String(groundTruth);

        setResultModal({
          score: `${(Number(scoreData.total || 0) * 100).toFixed(1)}%`,
          scenario: scoreData.scenario_id ?? "N/A",
          declared: declaredText,
          groundTruth: normalizedGroundTruth,
          isCorrect:
            normalizedDeclared.toLowerCase() ===
            normalizedGroundTruth.toLowerCase(),
        });
      }
    } catch (e) {
      console.error("Action failed:", e);
      setResultModal({
        score: "N/A",
        scenario: "N/A",
        declared: "Action failed",
        groundTruth: "N/A",
        isCorrect: false,
      });
    }
  };

  const isHidden = nodeData.health === "hidden";

  return (
    <>
      <div className="flex flex-col h-full space-y-8">
        <div className="flex items-center space-x-6 border-b border-gray-800 pb-6">
          <button
            onClick={onBack}
            className="p-3 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded transition-colors text-gray-300"
          >
            <ArrowLeft size={24} />
          </button>
          <div>
            <h2 className="text-sm text-chaos-cyan font-bold tracking-widest uppercase">
              Target Node
            </h2>
            <h1 className="text-4xl font-bold uppercase tracking-wide">
              {nodeId.replaceAll("_", " ")}
            </h1>
          </div>
        </div>

        {isHidden ? (
          <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-gray-700 rounded-xl bg-[#0A0C10] max-h-[400px]">
            <Eye size={64} className="text-gray-600 mb-6" />
            <h3 className="text-2xl font-bold mb-2">Telemetry Data Hidden</h3>
            <p className="text-chaos-text mb-8 max-w-md text-center">
              Execute an observation action to reveal real-time metrics.
            </p>
            <button
              onClick={() => handleAction("observe")}
              className="bg-chaos-cyan text-black px-8 py-3 font-bold rounded shadow-[0_0_15px_rgba(0,229,255,0.3)] hover:shadow-[0_0_20px_rgba(0,229,255,0.5)] transition-all"
            >
              EXECUTE OBSERVATION
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1">
            <div className="bg-chaos-panel p-8 rounded border border-gray-800 flex flex-col">
              <h3 className="text-sm text-chaos-cyan font-bold tracking-widest mb-6 border-b border-gray-800 pb-2">
                <Activity size={18} className="inline mr-2" />
                REMEDIATION PROTOCOLS
              </h3>

              <div className="grid grid-cols-1 gap-4 flex-1">
                <ActionCard
                  title="Restart Service"
                  desc="Clears transient memory leaks."
                  icon={<RefreshCw size={20} />}
                  onClick={() => handleAction("restart")}
                />
                <ActionCard
                  title="Rollback Deployment"
                  desc="Reverts service image to previous stable build."
                  icon={<RotateCcw size={20} />}
                  onClick={() => handleAction("rollback")}
                />
                <ActionCard
                  title="Scale Up Pods"
                  desc="Increase replica count."
                  icon={<TrendingUp size={20} />}
                  onClick={() => handleAction("scale_replica")}
                />
              </div>

              <div className="mt-8 pt-6 border-t border-gray-800">
                <button
                  onClick={() => handleAction("declare_root_cause")}
                  className="w-full py-4 border border-chaos-cyan text-chaos-cyan font-bold hover:bg-chaos-cyan hover:text-black transition-colors rounded tracking-widest uppercase"
                >
                  Declare Root Cause
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {resultModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center px-4">
          <div className="w-full max-w-xl bg-[#0A0C10] border border-cyan-500/40 rounded-2xl shadow-[0_0_30px_rgba(0,229,255,0.12)] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <p className="text-chaos-cyan text-xs tracking-[0.3em] uppercase font-bold">
                  Episode Complete
                </p>
                <h2 className="text-2xl font-bold mt-1">Simulation Result</h2>
              </div>

              <div
                className={`flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-semibold ${
                  resultModal.isCorrect
                    ? "border-green-500/40 text-green-400 bg-green-500/10"
                    : "border-red-500/40 text-red-400 bg-red-500/10"
                }`}
              >
                {resultModal.isCorrect ? (
                  <CheckCircle2 size={16} />
                ) : (
                  <XCircle size={16} />
                )}
                {resultModal.isCorrect ? "Correct" : "Incorrect"}
              </div>
            </div>

            <div className="p-6 space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <StatCard label="Final Score" value={resultModal.score} />
                <StatCard label="Scenario" value={resultModal.scenario} />
              </div>

              <div className="border border-gray-800 rounded-xl bg-gray-900/40 p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-gray-400 mb-2">
                  Declared Root Cause
                </p>
                <p className="text-lg font-semibold text-white break-words">
                  {resultModal.declared}
                </p>
              </div>

              <div className="border border-gray-800 rounded-xl bg-gray-900/40 p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-gray-400 mb-2">
                  Ground Truth Root Cause
                </p>
                <p className="text-lg font-semibold text-white break-words">
                  {resultModal.groundTruth}
                </p>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-800 flex justify-end">
              <button
                onClick={() => setResultModal(null)}
                className="px-5 py-2 rounded-lg border border-chaos-cyan text-chaos-cyan font-bold hover:bg-chaos-cyan hover:text-black transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ActionCard({ title, desc, icon, onClick }: any) {
  return (
    <div
      onClick={onClick}
      className="border border-gray-700 bg-gray-900/50 p-5 rounded hover:border-chaos-cyan hover:bg-chaos-cyan/5 cursor-pointer transition-all group"
    >
      <div className="flex items-center space-x-4 mb-2 text-gray-200 group-hover:text-chaos-cyan">
        {icon}
        <h4 className="font-bold text-lg">{title}</h4>
      </div>
      <p className="text-sm text-gray-400 pl-9">{desc}</p>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-gray-800 rounded-xl bg-gray-900/40 p-4">
      <p className="text-xs uppercase tracking-[0.25em] text-gray-400 mb-2">
        {label}
      </p>
      <p className="text-2xl font-bold text-chaos-cyan">{value}</p>
    </div>
  );
}