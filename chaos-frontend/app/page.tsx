"use client";

import { useState } from 'react';
import LandingPage from '../components/LandingPage';
import Dashboard from '../components/Dashboard';

export default function Home() {
  const [gameState, setGameState] = useState<any>(null);

  if (!gameState) {
    return <LandingPage onStart={(state) => setGameState(state)} />;
  }

  return <Dashboard gameState={gameState} setGameState={setGameState} />;
}