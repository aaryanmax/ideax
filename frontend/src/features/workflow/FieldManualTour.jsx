import React from 'react';
import { Joyride } from 'react-joyride';

export default function FieldManualTour({ run, setRun }) {
  const steps = [
    {
      target: '.tour-search',
      content: "Enter natural language intelligence queries here (e.g., 'dense urban settlement').",
      disableBeacon: true,
    },
    {
      target: '.tour-gallery',
      content: "Ranked bitemporal candidates. Use Up/Down arrow keys to navigate.",
    },
    {
      target: '.tour-viewer',
      content: "Split-slider comparison. Drag to verify phenological drift between T1 and T2.",
    },
    {
      target: '.tour-spotrep',
      content: "Automated AI SPOTREP and DGIS target classification.",
    },
    {
      target: '.tour-audit',
      content: "Cryptographic ledger. Press Enter to Approve, Backspace to Reject.",
    }
  ];

  const [stepIndex, setStepIndex] = React.useState(0);

  React.useEffect(() => {
    if (run) {
      setStepIndex(0);
    }
  }, [run]);

  const handleJoyrideCallback = (data) => {
    const { status, type, index } = data;
    const finishedStatuses = ['finished', 'skipped'];
    if (finishedStatuses.includes(status)) {
      setRun(false);
      setStepIndex(0);
    } else if (type === 'step:after' || type === 'target:notFound') {
      setStepIndex(index + (data.action === 'prev' ? -1 : 1));
    }
  };

  return (
    <Joyride
      steps={steps}
      run={run}
      stepIndex={stepIndex}
      continuous
      scrollToFirstStep
      showProgress
      showSkipButton
      callback={handleJoyrideCallback}
      styles={{
        options: {
          arrowColor: '#18181b', // zinc-900
          backgroundColor: '#18181b', // zinc-900
          overlayColor: 'rgba(0, 0, 0, 0.5)',
          primaryColor: '#10b981', // emerald-500
          textColor: '#34d399', // emerald-400
          width: 280,
          zIndex: 1000,
        },
        tooltip: {
          border: '1px solid #047857', // emerald-700
          borderRadius: '4px',
          padding: '12px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)'
        },
        tooltipContent: {
          fontFamily: 'monospace',
          fontSize: '12px',
          lineHeight: '1.6',
          textAlign: 'left',
          wordWrap: 'break-word',
          padding: '10px 0',
        },
        buttonClose: {
          display: 'none',
        },
        buttonNext: {
          backgroundColor: '#064e3b', // emerald-900
          color: '#10b981', // emerald-500
          borderRadius: '2px',
          fontFamily: 'monospace',
          fontSize: '11px',
          border: '1px solid #047857', // emerald-700
          padding: '6px 10px',
        },
        buttonBack: {
          color: '#a1a1aa', // zinc-400
          fontFamily: 'monospace',
          fontSize: '11px',
          marginRight: '10px',
        },
        buttonSkip: {
          color: '#a1a1aa', // zinc-400
          fontFamily: 'monospace',
          fontSize: '11px',
        }
      }}
    />
  );
}
