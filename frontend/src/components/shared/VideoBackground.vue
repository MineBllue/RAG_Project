<script setup lang="ts">
defineProps<{ src: string }>()
</script>

<template>
  <div class="video-bg">
    <video autoplay muted loop playsinline preload="auto">
      <source :src="src" type="video/mp4" />
    </video>
    <div class="video-overlay"></div>
  </div>
</template>

<style scoped>
.video-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden
}
.video-bg video {
  position: absolute;
  top: 50%; left: 50%;
  min-width: 100%; min-height: 100%;
  width: auto; height: auto;
  transform: translate(-50%, -50%);
  object-fit: cover
}
.video-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.25)
}
</style>
