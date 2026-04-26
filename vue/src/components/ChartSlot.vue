<template>
  <section class="panel-card">
    <h3 class="chart-slot-title">{{ title }}</h3>
    <div class="chart-slot-body">
      <slot>
        <p class="hint">Default slot: this area is reserved for chart components.</p>
      </slot>
    </div>
    <p class="hint">{{ description }}</p>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "Replace this with your teammates' Python visualization output." }
});
</script>
