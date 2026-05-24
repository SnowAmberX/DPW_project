<template>
  <div class="app-shell">
    <header class="top-nav-wrap">
      <div class="brand">Vaccine Impact Lab</div>
      <nav class="top-nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link">
          {{ item.label }}
        </RouterLink>
      </nav>
    </header>

    <main class="page-container">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
const navItems = [
  { label: "Home", to: "/" },
  { label: "Vaccination Status Overview", to: "/overview" },
  { label: "Vaccination vs New Cases", to: "/cases-vaccination" },
  { label: "Vaccination vs Mortality", to: "/mortality-vaccination" },
  { label: "Prediction", to: "/prediction" }
];
</script>
