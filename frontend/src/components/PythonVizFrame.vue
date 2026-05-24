<template>
  <div class="python-viz-frame-root">
    <iframe
      v-if="src"
      :src="src"
      title="python-viz-iframe"
      scrolling="no"
      :style="iframeStyle"
    />
    <p v-else class="hint">
      No `src` is set yet. You can use a Flask/FastAPI URL or a path to an exported static HTML chart.
    </p>
  </div>
</template>

<style scoped>
.python-viz-frame-root {
  overscroll-behavior: contain;
  isolation: isolate;
  border-radius: 10px;
  display: block;
  line-height: 0;
  overflow: hidden;
}
</style>

<script setup>
import { computed, onMounted } from "vue";

const PV_WHEEL_MSG = "python-viz-parent-wheel";

function handleEmbedWheelMessage(ev) {
  const d = ev.data;
  if (!d || d.type !== PV_WHEEL_MSG) return;
  if (typeof d.dy !== "number" || !Number.isFinite(d.dy)) return;
  if (typeof window === "undefined") return;
  if (ev.origin !== window.location.origin && ev.origin !== "null") return;

  window.scrollBy(0, d.dy);
}

let wheelMsgListenerInstalled = false;

function ensureWheelMessageListener() {
  if (wheelMsgListenerInstalled) return;
  wheelMsgListenerInstalled = true;
  window.addEventListener("message", handleEmbedWheelMessage);
}

onMounted(() => {
  ensureWheelMessageListener();
});

const props = defineProps({
  src: { type: String, default: "" },
  height: { type: Number, default: 420 },
  /**
   * Reserved for pages that inject `overflow:hidden` on the embedded HTML document.
   * Iframe chrome always hides scrollbars; ensure exported chart height matches `height`.
   */
  noScroll: { type: Boolean, default: false }
});

const iframeStyle = computed(() => ({
  width: "100%",
  height: `${props.height}px`,
  border: "none",
  borderRadius: "10px",
  background: "#fffaf2",
  overflow: "hidden",
  display: "block"
}));
</script>
