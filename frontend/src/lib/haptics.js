export const triggerHaptic = (type) => {
  if (!('vibrate' in navigator)) return;
  if (type === 'approve') navigator.vibrate([50, 50, 50]); // Quick double tap
  if (type === 'reject') navigator.vibrate([200]); // Heavy pulse
  if (type === 'scan') navigator.vibrate([30]); // Light tick
};
