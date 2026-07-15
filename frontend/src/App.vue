<script setup lang="ts">
import { toastVisible, toastMsg } from './stores/toast'
</script>

<template>
  <Transition name="toast">
    <div v-if="toastVisible" class="toast-bar">{{ toastMsg }}</div>
  </Transition>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>
