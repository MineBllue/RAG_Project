<script setup lang="ts">
defineProps<{ title: string; subtitle: string }>()
</script>

<template>
  <div class="welcome">
    <img class="welcome-img" src="@/icon/avatar_anime.jpg" alt="Logo" />
    <h2>{{ title }}</h2>
    <p>{{ subtitle }}</p>
  </div>
</template>
