<script setup lang="ts">
import { ref, onMounted } from 'vue';
import flatpickr from 'flatpickr';

const props = defineProps<{
  defaultStartTime?: string;
}>();

const emit = defineEmits(['add']);

const startDateEl = ref<HTMLInputElement | null>(null);
const startTimeEl = ref<HTMLInputElement | null>(null);
const endTimeEl = ref<HTMLInputElement | null>(null);
const periodicity = ref(7);
const repetitions = ref(12);

let fpDate: flatpickr.Instance;
let fpStart: flatpickr.Instance;
let fpEnd: flatpickr.Instance;

onMounted(() => {
  const now = new Date();
  const currentTime = now.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
  const dateStr = now.toISOString().split('T')[0];
  const startTime = props.defaultStartTime || currentTime;

  if (startDateEl.value) {
    fpDate = flatpickr(startDateEl.value, {
      altInput: true,
      altFormat: 'd. m. Y',
      dateFormat: 'Y-m-d',
      defaultDate: dateStr
    });
  }
  if (startTimeEl.value) {
    fpStart = flatpickr(startTimeEl.value, {
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
      time_24hr: true,
      defaultDate: startTime
    });
  }
  if (endTimeEl.value) {
    fpEnd = flatpickr(endTimeEl.value, {
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
      time_24hr: true,
      defaultDate: startTime
    });
    // Set default end time to +90 minutes
    setEndTime(90);
  }
});

function add() {
  const dateVal = fpDate?.input.value;
  const startVal = fpStart?.input.value;
  const endVal = fpEnd?.input.value;

  if (!dateVal || !startVal || !endVal) return;

  const baseDate = new Date(dateVal);
  const newSessions = [];

  for (let i = 0; i < repetitions.value; i++) {
    const currentDt = new Date(baseDate);
    currentDt.setDate(currentDt.getDate() + i * periodicity.value);
    const dateStr = currentDt.toISOString().split('T')[0];

    newSessions.push({
      start: `${dateStr}T${startVal}`,
      end: `${dateStr}T${endVal}`,
      _isNew: true
    });
  }

  emit('add', newSessions);
}

function setEndTime(mins: number) {
  const startTime = fpStart?.input.value;
  if (!startTime) return;
  const [h, m] = startTime.split(':').map(Number);
  const dt = new Date();
  dt.setHours(h, m + mins);
  fpEnd.setDate(dt.toTimeString().split(' ')[0].substring(0, 5));
}
</script>

<template>
  <div class="card mb-3">
    <div class="card-header">Bulk add sessions</div>
    <div class="card-body">
      <div class="row g-2 align-items-end">
        <div class="col-md-2">
          <label class="form-label small" for="firstDate">First date</label>
          <input id="firstDate" ref="startDateEl" class="form-control form-control-sm" />
        </div>
        <div class="col-md-2">
          <label class="form-label small" for="periodicity">Period (days)</label>
          <input
            id="periodicity"
            v-model.number="periodicity"
            type="number"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-md-2">
          <label class="form-label small" for="repetitions">Repetitions</label>
          <input
            id="repetitions"
            v-model.number="repetitions"
            type="number"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-md-2">
          <label class="form-label small" for="startTime">Start time</label>
          <input id="startTime" ref="startTimeEl" class="form-control form-control-sm" />
        </div>
        <div class="col-md-2">
          <label class="form-label small" for="endTime">End time</label>
          <div class="input-group input-group-sm">
            <input id="endTime" ref="endTimeEl" class="form-control form-control-sm" />
            <button
              class="btn btn-outline-secondary dropdown-toggle"
              type="button"
              data-bs-toggle="dropdown"
            ></button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item" @click="setEndTime(45)">+ 45 min</a></li>
              <li><a class="dropdown-item" @click="setEndTime(90)">+ 90 min</a></li>
              <li><a class="dropdown-item" @click="setEndTime(135)">+ 135 min</a></li>
            </ul>
          </div>
        </div>
        <div class="col-md-2">
          <button class="btn btn-sm btn-primary w-100" @click="add">Add sessions</button>
        </div>
      </div>
    </div>
  </div>
</template>
