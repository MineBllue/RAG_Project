<script setup lang="ts">
const temperature = defineModel<number>('temperature', { default: 0.3 })
const topP = defineModel<number>('topP', { default: 0.85 })
const maxTokens = defineModel<number>('maxTokens', { default: 2048 })
const historyRounds = defineModel<number>('historyRounds', { default: 5 })
const show = defineModel<boolean>('show', { default: false })
</script>

<template>
  <aside v-if="show" class="panel-r">
    <div class="pr-title">推理参数</div>
    <div class="pr-group">
      <div class="pr-row"><span>Temperature</span><span class="pr-val">{{ temperature }}</span></div>
      <input type="range" class="pr-slider" min="0" max="1" step="0.01" v-model.number="temperature" />
    </div>
    <div class="pr-group">
      <div class="pr-row"><span>Top P</span><span class="pr-val">{{ topP }}</span></div>
      <input type="range" class="pr-slider" min="0" max="1" step="0.01" v-model.number="topP" />
    </div>
    <div class="pr-group">
      <div class="pr-row"><span>Max Tokens</span><span class="pr-val">{{ maxTokens }}</span></div>
      <input type="range" class="pr-slider" min="256" max="8192" step="256" v-model.number="maxTokens" />
    </div>
    <div class="pr-group">
      <div class="pr-row"><span>历史轮数</span><span class="pr-val">{{ historyRounds }}</span></div>
      <input type="range" class="pr-slider" min="0" max="20" step="1" v-model.number="historyRounds" />
    </div>
  </aside>
</template>

<style scoped>
.panel-r {
  width: 240px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-subtle);
  padding: 14px;
  overflow-y: auto;
  animation: sIn .3s cubic-bezier(.4, 0, .2, 1)
}
@keyframes sIn { from { transform: translateX(20px); opacity: 0 } to { transform: translateX(0); opacity: 1 } }
.pr-title { font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: var(--text-tertiary); font-weight: 600; margin-bottom: 12px }
.pr-group { margin-bottom: 14px }
.pr-row { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px }
.pr-val { color: var(--text-primary); font-weight: 500; font-family: monospace; font-size: 10px }
.pr-slider { -webkit-appearance: none; width: 100%; height: 4px; border-radius: 2px; background: var(--border-card); outline: none }
.pr-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: var(--accent); cursor: pointer; border: 2px solid var(--bg-surface); transition: transform .15s }
.pr-slider::-webkit-slider-thumb:hover { transform: scale(1.2) }
</style>
