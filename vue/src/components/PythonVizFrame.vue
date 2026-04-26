<template>
  <div>
    <iframe
      v-if="src"
      :src="src"
      title="python-viz-iframe"
      style="width: 100%; height: 360px; border: none; border-radius: 10px"
    />
    <p v-else class="hint">
      No `src` is set yet. You can use a Flask/FastAPI URL or a path to an exported static HTML chart.
    </p>
  </div>
</template>

<script setup>
defineProps({
  src: { type: String, default: "" }
});
</script>
