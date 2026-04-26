<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import flatpickr from 'flatpickr';

const props = defineProps<{
  modelValue: {
    id?: number;
    start: string;
    end: string;
    _deleted?: boolean;
    _isNew?: boolean;
    _original?: { start: string; end: string };
  };
  selected?: boolean;
}>();

const emit = defineEmits(['update:modelValue', 'delete', 'select']);

const dateEl = ref<HTMLInputElement | null>(null);
const startEl = ref<HTMLInputElement | null>(null);
const endEl = ref<HTMLInputElement | null>(null);

let fpDate: flatpickr.Instance;
let fpStart: flatpickr.Instance;
let fpEnd: flatpickr.Instance;

const isDirty = computed(() => {
  if (props.modelValue._isNew || props.modelValue._deleted) return false;
  if (!props.modelValue._original) return false;
  return (
    props.modelValue.start !== props.modelValue._original.start ||
    props.modelValue.end !== props.modelValue._original.end
  );
});

function onCheckboxChange(event: HTMLInputElement) {
  emit('select', event.checked);
}

function update() {
  const date = fpDate?.input.value;
  const start = fpStart?.input.value;
  const end = fpEnd?.input.value;

  if (date && start && end) {
    emit('update:modelValue', {
      ...props.modelValue,
      start: `${date}T${start}`,
      end: `${date}T${end}`
    });
  }
}

onMounted(() => {
  const startDt = new Date(props.modelValue.start);
  const endDt = new Date(props.modelValue.end);

  const dateStr = startDt.toISOString().split('T')[0];
  const startStr = startDt.toTimeString().split(' ')[0].substring(0, 5);
  const endStr = endDt.toTimeString().split(' ')[0].substring(0, 5);

  if (dateEl.value) {
    fpDate = flatpickr(dateEl.value, {
      altInput: true,
      altFormat: 'd. m. Y',
      dateFormat: 'Y-m-d',
      defaultDate: dateStr,
      onChange: update
    });
  }
  if (startEl.value) {
    fpStart = flatpickr(startEl.value, {
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
      time_24hr: true,
      defaultDate: startStr,
      onChange: update
    });
  }
  if (endEl.value) {
    fpEnd = flatpickr(endEl.value, {
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
      time_24hr: true,
      defaultDate: endStr,
      onChange: update
    });
  }
});

watch(
  () => props.modelValue.start,
  (newVal) => {
    if (!newVal) return;
    const dt = new Date(newVal);
    const dateStr = dt.toISOString().split('T')[0];
    const timeStr = dt.toTimeString().split(' ')[0].substring(0, 5);
    if (fpDate && fpDate.input.value !== dateStr) fpDate.setDate(dateStr);
    if (fpStart && fpStart.input.value !== timeStr) fpStart.setDate(timeStr);
  }
);

watch(
  () => props.modelValue.end,
  (newVal) => {
    if (!newVal) return;
    const dt = new Date(newVal);
    const timeStr = dt.toTimeString().split(' ')[0].substring(0, 5);
    if (fpEnd && fpEnd.input.value !== timeStr) fpEnd.setDate(timeStr);
  }
);
</script>

<template>
  <tr
    :class="{
      'table-danger': modelValue._deleted,
      'table-info': modelValue._isNew,
      'table-warning': isDirty && !modelValue._deleted
    }"
  >
    <td>
      <input
        type="checkbox"
        class="form-check-input"
        :checked="selected"
        @change="onCheckboxChange($event.target as HTMLInputElement)"
      />
    </td>
    <td>
      <input ref="dateEl" class="form-control form-control-sm" />
    </td>
    <td>
      <input ref="startEl" class="form-control form-control-sm" />
    </td>
    <td>
      <input ref="endEl" class="form-control form-control-sm" />
    </td>
    <td class="text-end">
      <button
        class="btn btn-sm"
        :class="modelValue._deleted ? 'btn-outline-secondary' : 'btn-outline-danger'"
        @click="emit('delete')"
      >
        <span
          class="iconify"
          :data-icon="modelValue._deleted ? 'bx:bx-undo' : 'akar-icons:trash-can'"
        ></span>
      </button>
    </td>
  </tr>
</template>
