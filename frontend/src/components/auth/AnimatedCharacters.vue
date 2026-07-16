<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps<{
  isTyping: boolean
  showPassword: boolean
  passwordLength: number
}>()

const mouseX = ref(0)
const mouseY = ref(0)
const purpleBlinking = ref(false)
const blackBlinking = ref(false)
const lookingAtEachOther = ref(false)
const purplePeeking = ref(false)

const purpleRef = ref<HTMLElement | null>(null)
const blackRef = ref<HTMLElement | null>(null)
const orangeRef = ref<HTMLElement | null>(null)
const yellowRef = ref<HTMLElement | null>(null)

let blinkTimers: ReturnType<typeof setTimeout>[] = []
let peekTimer: ReturnType<typeof setTimeout> | null = null

function onMouseMove(e: MouseEvent) {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}

function calcPos(el: HTMLElement | null) {
  if (!el) return { faceX: 0, faceY: 0, bodySkew: 0 }
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 3
  const dx = mouseX.value - cx
  const dy = mouseY.value - cy
  return {
    faceX: Math.max(-15, Math.min(15, dx / 20)),
    faceY: Math.max(-10, Math.min(10, dy / 30)),
    bodySkew: Math.max(-6, Math.min(6, -dx / 120)),
  }
}

function calcPupil(eyeEl: HTMLElement | null, maxDist = 5) {
  if (!eyeEl) return { x: 0, y: 0 }
  const rect = eyeEl.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = mouseX.value - cx
  const dy = mouseY.value - cy
  const dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxDist)
  const angle = Math.atan2(dy, dx)
  return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
}

function startBlink(setter: (v: boolean) => void) {
  const schedule = () => {
    const t = setTimeout(() => {
      setter(true)
      setTimeout(() => { setter(false); schedule() }, 150)
    }, Math.random() * 4000 + 3000)
    blinkTimers.push(t)
  }
  schedule()
}

// typing → characters look at each other
import { watch } from 'vue'
let lookTimer: ReturnType<typeof setTimeout> | null = null
watch(() => props.isTyping, (v) => {
  if (v) {
    lookingAtEachOther.value = true
    if (lookTimer) clearTimeout(lookTimer)
    lookTimer = setTimeout(() => { lookingAtEachOther.value = false }, 800)
  }
})

// password visible + has content → purple peeks
watch([() => props.showPassword, () => props.passwordLength], ([show, len]) => {
  if (show && len > 0) {
    const schedule = () => {
      peekTimer = setTimeout(() => {
        purplePeeking.value = true
        setTimeout(() => { purplePeeking.value = false; if (peekTimer) schedule() }, 800)
      }, Math.random() * 3000 + 2000)
    }
    schedule()
  } else {
    purplePeeking.value = false
    if (peekTimer) clearTimeout(peekTimer)
  }
})

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  startBlink((v) => purpleBlinking.value = v)
  startBlink((v) => blackBlinking.value = v)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  blinkTimers.forEach(clearTimeout)
  if (lookTimer) clearTimeout(lookTimer)
  if (peekTimer) clearTimeout(peekTimer)
})

const typing = computed(() => props.isTyping || (props.passwordLength > 0 && !props.showPassword))
const visiblePwd = computed(() => props.passwordLength > 0 && props.showPassword)

const purplePos = computed(() => calcPos(purpleRef.value))
const blackPos = computed(() => calcPos(blackRef.value))
const orangePos = computed(() => calcPos(orangeRef.value))
const yellowPos = computed(() => calcPos(yellowRef.value))
</script>

<template>
  <div class="characters-scene">
    <!-- Purple - tall, back -->
    <div
      ref="purpleRef"
      class="char-body char-purple"
      :style="{
        height: visiblePwd ? '440px' : typing ? '440px' : '400px',
        transform: visiblePwd
          ? 'skewX(0deg)'
          : typing
            ? `skewX(${purplePos.bodySkew - 12}deg) translateX(40px)`
            : `skewX(${purplePos.bodySkew}deg)`,
      }"
    >
      <div class="eyes-row" :style="{ left: visiblePwd ? '12px' : lookingAtEachOther ? '50px' : `${40 + purplePos.faceX}px`, top: visiblePwd ? '28px' : lookingAtEachOther ? '58px' : `${38 + purplePos.faceY}px` }">
        <div class="eye-white" :class="{ blinking: purpleBlinking }">
          <div class="pupil-dark" :style="{ transform: `translate(${calcPupil($el, 4).x}px, ${calcPupil($el, 4).y}px)` }" ref="el" />
        </div>
        <div class="eye-white" :class="{ blinking: purpleBlinking }">
          <div class="pupil-dark" :style="{ transform: `translate(${calcPupil($el, 4).x}px, ${calcPupil($el, 4).y}px)` }" />
        </div>
      </div>
    </div>

    <!-- Black - medium, middle -->
    <div
      ref="blackRef"
      class="char-body char-black"
      :style="{
        transform: visiblePwd
          ? 'skewX(0deg)'
          : lookingAtEachOther
            ? `skewX(${blackPos.bodySkew * 1.5 + 10}deg) translateX(20px)`
            : typing
              ? `skewX(${blackPos.bodySkew * 1.5}deg)`
              : `skewX(${blackPos.bodySkew}deg)`,
      }"
    >
      <div class="eyes-row" :style="{ left: visiblePwd ? '8px' : lookingAtEachOther ? '28px' : `${22 + blackPos.faceX}px`, top: visiblePwd ? '24px' : lookingAtEachOther ? '10px' : `${28 + blackPos.faceY}px` }">
        <div class="eye-white eye-sm" :class="{ blinking: blackBlinking }">
          <div class="pupil-dark pupil-sm" :style="{ transform: `translate(${calcPupil($el, 3).x}px, ${calcPupil($el, 3).y}px)` }" />
        </div>
        <div class="eye-white eye-sm" :class="{ blinking: blackBlinking }">
          <div class="pupil-dark pupil-sm" :style="{ transform: `translate(${calcPupil($el, 3).x}px, ${calcPupil($el, 3).y}px)` }" />
        </div>
      </div>
    </div>

    <!-- Orange - semicircle, front-left -->
    <div
      ref="orangeRef"
      class="char-body char-orange"
      :style="{ transform: visiblePwd ? 'skewX(0deg)' : `skewX(${orangePos.bodySkew}deg)` }"
    >
      <div class="eyes-row" :style="{ left: visiblePwd ? '48px' : `${80 + orangePos.faceX}px`, top: `85px` }">
        <div class="pupil-dark pupil-lg" :style="{ transform: `translate(${calcPupil($el, 4).x}px, ${calcPupil($el, 4).y}px)` }" />
        <div class="pupil-dark pupil-lg" :style="{ transform: `translate(${calcPupil($el, 4).x}px, ${calcPupil($el, 4).y}px)` }" />
      </div>
    </div>

    <!-- Yellow - rounded, front-right -->
    <div
      ref="yellowRef"
      class="char-body char-yellow"
      :style="{ transform: visiblePwd ? 'skewX(0deg)' : `skewX(${yellowPos.bodySkew}deg)` }"
    >
      <div class="eyes-row" :style="{ left: visiblePwd ? '20px' : `${50 + yellowPos.faceX}px`, top: visiblePwd ? '32px' : `${38 + yellowPos.faceY}px` }">
        <div class="pupil-dark pupil-lg" :style="{ transform: `translate(${calcPupil($el, 4).x}px, ${calcPupil($el, 4).y}px)` }" />
        <div class="pupil-dark pupil-lg" :style="{ transform: `translate(${calcPupil($el, 4).x}px, ${calcPupil($el, 4).y}px)` }" />
      </div>
      <div class="char-mouth" :style="{ left: visiblePwd ? '10px' : `${38 + yellowPos.faceX}px`, top: '85px' }" />
    </div>
  </div>
</template>

<style scoped>
.characters-scene {
  position: relative;
  width: 550px;
  height: 420px;
}

.char-body {
  position: absolute;
  bottom: 0;
  transition: transform .7s ease-in-out, height .7s ease-in-out;
  transform-origin: bottom center;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px)
}

.char-purple { left: 70px; width: 180px; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.28); border-radius: 10px 10px 0 0; z-index: 1 }
.char-black { left: 240px; width: 120px; height: 310px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.22); border-radius: 8px 8px 0 0; z-index: 2 }
.char-orange { left: 0; width: 240px; height: 200px; background: rgba(255,255,255,0.20); border: 1px solid rgba(255,255,255,0.30); border-radius: 120px 120px 0 0; z-index: 3 }
.char-yellow { left: 310px; width: 140px; height: 230px; background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.32); border-radius: 70px 70px 0 0; z-index: 4 }

.eyes-row {
  position: absolute;
  display: flex;
  gap: 20px;
  transition: left .7s ease-in-out, top .7s ease-in-out;
}
.char-black .eyes-row { gap: 16px }

.eye-white {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: rgba(255,255,255,0.6);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  transition: height .15s;
}
.eye-white.eye-sm { width: 16px; height: 16px }
.eye-white.blinking { height: 2px }

.pupil-dark {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #2D2D2D;
  transition: transform .1s ease-out;
}
.pupil-dark.pupil-sm { width: 6px; height: 6px }
.pupil-dark.pupil-lg { width: 12px; height: 12px }

.char-mouth {
  position: absolute;
  width: 80px; height: 4px;
  background: rgba(0,0,0,0.35);
  border-radius: 2px;
  transition: left .2s ease-out;
}
</style>
