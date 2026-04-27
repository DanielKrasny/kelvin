<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { Bar, Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  PointElement,
  LineElement,
  CategoryScale,
  LinearScale,
  ChartData,
  ChartOptions
} from 'chart.js';
import { getDataWithCSRF } from '../../utilities/api';
import type { ClassSession } from '../ClassSessions/dto';
import type { StudentPresence, SessionTimespan } from './dto';

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  PointElement,
  LineElement,
  CategoryScale,
  LinearScale
);

const props = defineProps<{
  classId: number | string;
  sessions: ClassSession[];
  currentSessionId: number | null;
}>();

const emit = defineEmits<{
  (e: 'select-session', sessionId: number): void;
}>();

const classPresenceData = ref<Record<number, StudentPresence[]>>({});
const sessionTimespans = ref<SessionTimespan[]>([]);
const includeManual = ref(false);

const classChartData = computed<ChartData<'bar'>>(() => {
  const labels = props.sessions.map((s) => {
    const date = new Date(s.start);
    return (
      date.toLocaleDateString() +
      ' ' +
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    );
  });
  const data = props.sessions.map((s) => {
    const presence = classPresenceData.value[s.id] || [];
    return presence.filter((p) => p.is_present).length;
  });

  return {
    labels,
    datasets: [
      {
        label: 'Present Students',
        backgroundColor: '#0d6efd',
        data
      }
    ]
  };
});

const sessionChartData = computed<ChartData<'line'>>(() => {
  return {
    labels: sessionTimespans.value.map((t) => t.time),
    datasets: [
      {
        label: 'Students Present',
        borderColor: '#198754',
        backgroundColor: '#19875488',
        fill: true,
        tension: 0.4,
        data: sessionTimespans.value.map((t) => t.count)
      }
    ]
  };
});

const chartOptions: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  onClick: (_event, elements) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      const sessionId = props.sessions[index].id;
      emit('select-session', sessionId);
    }
  }
};

const sessionChartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        stepSize: 1
      }
    }
  }
};

async function fetchClassPresence() {
  try {
    const data = await getDataWithCSRF<Record<number, StudentPresence[]>>(
      `/api/v2/attendance/class-session/class/${props.classId}/presence`
    );
    classPresenceData.value = data;
  } catch (e) {
    console.error(e);
  }
}

async function fetchSessionTimespans() {
  if (!props.currentSessionId) return;
  try {
    const data = await getDataWithCSRF<SessionTimespan[]>(
      `/api/v2/attendance/class-session/${props.currentSessionId}/timespans?include_manual=${includeManual.value}`
    );
    sessionTimespans.value = data;
  } catch (e) {
    console.error(e);
  }
}

onMounted(() => {
  fetchClassPresence();
  fetchSessionTimespans();
});

defineExpose({
  fetchClassPresence,
  fetchSessionTimespans
});

watch(() => props.currentSessionId, fetchSessionTimespans);
watch(includeManual, fetchSessionTimespans);
</script>

<template>
  <div class="row mb-4">
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-body">
          <h5 class="card-title">Attendance history</h5>
          <div style="height: 300px">
            <Bar :data="classChartData" :options="chartOptions" />
          </div>
        </div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card h-100">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h5 class="card-title mb-0">Session retention</h5>
            <div class="form-check form-switch">
              <input
                id="includeManualSwitch"
                v-model="includeManual"
                class="form-check-input"
                type="checkbox"
              />
              <label class="form-check-label" for="includeManualSwitch">Include manual</label>
            </div>
          </div>
          <div style="height: 300px">
            <Line v-if="currentSessionId" :data="sessionChartData" :options="sessionChartOptions" />
            <div v-else class="d-flex h-100 align-items-center justify-content-center text-muted">
              Select a session to see retention
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
