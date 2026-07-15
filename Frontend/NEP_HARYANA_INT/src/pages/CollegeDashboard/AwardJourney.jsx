import { useState, useEffect, useRef } from "react";
import styles from "./AwardJourney.module.css";
import { fetchNominationConfig } from "../../api/nomination";

export default function AwardJourney({ score = 0, award = "No Award" }) {
  const [thresholds, setThresholds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [celebrationAward, setCelebrationAward] = useState(null);
  s
  // Track milestones that have been celebrated during the session
  const [celebratedMilestones, setCelebratedMilestones] = useState(() => {
    const initialCelebrated = ["Entry"];
    if (score >= 51) initialCelebrated.push("Silver");
    if (score >= 75) initialCelebrated.push("Gold");
    if (score >= 91) initialCelebrated.push("Platinum");
    return initialCelebrated;
  });
  const prevScoreRef = useRef(score);

  useEffect(() => {
    async function loadConfig() {
      try {
        const config = await fetchNominationConfig();
        if (config && config.award_thresholds) {
          setThresholds(config.award_thresholds);
        } else {
          // Fallbacks in case config fails
          setThresholds([
            { level: "Silver", min_score: 51, description: "Recognized for meeting key quality indicators across the nomination framework.", badge_color: "silver" },
            { level: "Gold", min_score: 75, description: "Exemplary implementation of institutional governance and core values.", badge_color: "gold" },
            { level: "Platinum", min_score: 91, description: "Outstanding leadership and state-level benchmarking in higher education.", badge_color: "platinum" }
          ]);
        }
      } catch (err) {
        console.error("Failed to load thresholds config:", err);
      } finally {
        setLoading(false);
      }
    }
    loadConfig();
  }, []);

  // Listen to score increases and trigger celebration overlay
  useEffect(() => {
    if (thresholds.length === 0) return;

    // Check if score went up and crossed any threshold
    if (score > prevScoreRef.current) {
      thresholds.forEach((t) => {
        if (score >= t.min_score && !celebratedMilestones.includes(t.level)) {
          // Newly unlocked! Trigger celebration
          setCelebrationAward(t);
          setCelebratedMilestones((prev) => [...prev, t.level]);
        }
      });
    }
    prevScoreRef.current = score;
  }, [score, thresholds, celebratedMilestones]);

  if (loading) {
    return (
      <div className={styles.journeyContainer} style={{ minHeight: "150px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "#64748b", fontSize: "0.9rem", fontWeight: "600" }}>Loading journey configuration...</div>
      </div>
    );
  }

  // Construct ladder nodes: starting with entry node (0 points)
  const steps = [
    { level: "Entry", min_score: 0, description: "Nomination started.", badge_color: "slate" },
    ...thresholds
  ];

  // Determine current active level
  let currentActiveStepIndex = 0;
  steps.forEach((step, idx) => {
    if (score >= step.min_score) {
      currentActiveStepIndex = idx;
    }
  });

  // Calculate percentage along the ladder bar line
  let overallPercentage = 0;
  if (steps.length > 1) {
    const totalThresholdRange = steps[steps.length - 1].min_score;
    overallPercentage = Math.min((score / totalThresholdRange) * 100, 100);
  }

  // Determine next milestone
  const nextStep = currentActiveStepIndex < steps.length - 1 ? steps[currentActiveStepIndex + 1] : null;
  const currentStep = steps[currentActiveStepIndex];
  
  // Calculate details for next benchmark
  const remainingPoints = nextStep ? nextStep.min_score - score : 0;
  const nextStepScoreRange = nextStep ? (nextStep.min_score - currentStep.min_score) : 1;
  const nextStepProgress = nextStep ? Math.min(((score - currentStep.min_score) / nextStepScoreRange) * 100, 100) : 100;

  // Icons mapper helper
  const getBadgeIcon = (level) => {
    switch (level) {
      case "Platinum":
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="8" r="7" />
            <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
          </svg>
        );
      case "Gold":
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
            <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
            <path d="M4 22h16" />
            <path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34" />
            <path d="M12 2a4 4 0 0 0-4 4v8h8V6a4 4 0 0 0-4-4z" />
          </svg>
        );
      case "Silver":
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        );
      default:
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        );
    }
  };

  return (
    <div className={styles.journeyContainer}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="8" r="6" />
            <path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11" />
          </svg>
          <span>Nomination Award Journey</span>
        </div>
        <div className={styles.scorePill}>
          Score: {score} / 100
        </div>
      </div>

      {/* Award Ladder */}
      <div className={styles.ladder}>
        <div className={styles.ladderLine}>
          <div 
            className={styles.ladderLineProgress} 
            style={{ width: `${overallPercentage}%` }} 
          />
        </div>

        {steps.map((step, idx) => {
          const isUnlocked = score >= step.min_score;
          const isActive = idx === currentActiveStepIndex;
          
          return (
            <div 
              key={step.level} 
              className={`${styles.ladderStep} ${isUnlocked ? styles.unlocked : ""} ${isActive ? styles.active : ""}`}
            >
              <div className={styles.badgeCircle}>
                {getBadgeIcon(step.level)}
                <div className={styles.lockOverlay}>
                  {isUnlocked ? (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  )}
                </div>
              </div>
              <span className={styles.stepLabel}>{step.level}</span>
              <span className={styles.stepScore}>{step.min_score}+ pts</span>
            </div>
          );
        })}
      </div>

      {/* Progress & Target Section */}
      <div className={styles.progressSection}>
        {nextStep ? (
          <>
            <div className={styles.progressStats}>
              <span>Current Status: <strong className={styles.targetHighlight}>{currentStep.level}</strong></span>
              <span>Next Goal: <strong>{nextStep.level}</strong> ({score}/{nextStep.min_score} pts)</span>
            </div>
            <div className={styles.progressBarContainer}>
              <div 
                className={styles.progressBarFill} 
                style={{ width: `${nextStepProgress}%` }} 
              />
            </div>
            <div className={styles.progressStats}>
              <span>Unlocked at {currentStep.min_score} pts</span>
              <span>Need {remainingPoints} more points</span>
            </div>
            
            <div className={styles.motivationMessage}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="m9 18 6-6-6-6" />
              </svg>
              <span>
                You are only <strong>{remainingPoints} points</strong> away from <strong>{nextStep.level}</strong>. 
                Focus on accreditation status, IDP implementation, student counseling support, and foreign collaborations to earn more marks.
              </span>
            </div>
          </>
        ) : (
          <div style={{ textAlign: "center", padding: "10px 0" }}>
            <span style={{ fontSize: "1.05rem", fontWeight: "800", color: "#16a34a" }}>
              🏆 Incredible! You have achieved the peak level of <strong>Platinum Award</strong>!
            </span>
            <p style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "4px" }}>
              Your nomination fulfills the highest benchmarks of the Haryana State Higher Education Council evaluation framework.
            </p>
          </div>
        )}
      </div>

      {/* Dynamic Celebration Overlay */}
      {celebrationAward && (
        <div className={styles.celebrationOverlay}>
          <div className={styles.celebrationCard}>
            {/* Confetti falling animations */}
            <div className={styles.confettiContainer}>
              {[...Array(12)].map((_, i) => (
                <div 
                  key={i} 
                  className={styles.particle} 
                  style={{
                    left: `${Math.random() * 90}%`,
                    backgroundColor: ["#f59e0b", "#10b981", "#3b82f6", "#ec4899", "#8b5cf6"][i % 5],
                    animationDelay: `${Math.random() * 2}s`,
                    animationDuration: `${2 + Math.random() * 2}s`
                  }}
                />
              ))}
            </div>

            <div className={styles.trophyAnim}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                <path d="M4 22h16" />
                <path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34" />
                <path d="M12 2a4 4 0 0 0-4 4v8h8V6a4 4 0 0 0-4-4z" />
              </svg>
            </div>

            <h2>🎉 {celebrationAward.level} Unlocked!</h2>
            <p>
              Congratulations! Your institution has achieved the <strong>{celebrationAward.level} Benchmark</strong> with {score} points.<br/><br/>
              <span style={{ fontSize: "0.95rem", color: "#64748b", fontStyle: "italic" }}>
                "{celebrationAward.description}"
              </span>
            </p>

            <button 
              className={styles.dismissBtn} 
              onClick={() => setCelebrationAward(null)}
            >
              Continue Nomination Journey
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
