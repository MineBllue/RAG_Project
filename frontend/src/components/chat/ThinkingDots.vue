<template>
  <div class="thinking">
    <div class="t-dot"></div>
    <div class="t-dot"></div>
    <div class="t-dot"></div>
  </div>
</template>

<style scoped>
.thinking { display: flex; align-items: center; gap: 8px; padding: 4px 0 }
.t-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  animation: dotBounce 1.4s ease-in-out infinite
}
.t-dot:nth-child(2) { animation-delay: .2s }
.t-dot:nth-child(3) { animation-delay: .4s }
@keyframes dotBounce {
  0%, 80%, 100% { opacity: .2; transform: translateY(0) }
  40% { opacity: 1; transform: translateY(-6px) }
}
</style>
