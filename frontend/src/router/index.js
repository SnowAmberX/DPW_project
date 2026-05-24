import { createRouter, createWebHistory } from "vue-router";
import HomePage from "../pages/home/index.vue";
import OverviewPage from "../pages/overview/index.vue";
import CasesVaccinationPage from "../pages/cases-vaccination/index.vue";
import MortalityVaccinationPage from "../pages/mortality-vaccination/index.vue";
import PredictionPage from "../pages/prediction/index.vue";

const routes = [
  { path: "/", name: "home", component: HomePage, meta: { title: "Home | Vaccine Impact Lab" } },
  {
    path: "/overview",
    name: "overview",
    component: OverviewPage,
    meta: { title: "Vaccination Status Overview | Vaccine Impact Lab" }
  },
  {
    path: "/overview-python",
    redirect: { name: "overview" }
  },
  {
    path: "/cases-vaccination",
    name: "casesVaccination",
    component: CasesVaccinationPage,
    meta: { title: "Vaccination Status and New Cases" }
  },
  {
    path: "/mortality-vaccination",
    name: "mortalityVaccination",
    component: MortalityVaccinationPage,
    meta: { title: "Vaccination Status and Mortality Rate" }
  },
  {
    path: "/vaccination-rollout",
    redirect: { name: "overview" }
  },
  {
    path: "/prediction",
    name: "prediction",
    component: PredictionPage,
    meta: { title: "Future Outbreak Prediction" }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
