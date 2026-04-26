<script setup lang="ts">
import { computed } from 'vue';
import SessionRow from './SessionRow.vue';
import type { ClassSession } from './dto';

interface ClassSessionLocal extends Partial<ClassSession> {
  id?: number;
  start: string;
  end: string;
  _isNew?: boolean;
  _deleted?: boolean;
  _original?: { start: string; end: string };
}

const props = defineProps<{
  sessions: ClassSessionLocal[];
  selectedIndices: Set<number>;
}>();

const emit = defineEmits(['toggleSelectAll', 'toggleSelect', 'markForDeletion', 'update:sessions']);

const allSelected = computed(() => {
  return props.sessions.length > 0 && props.selectedIndices.size === props.sessions.length;
});

function handleUpdateSession(index: number, value: ClassSessionLocal) {
  const newSessions = [...props.sessions];
  newSessions[index] = value;
  emit('update:sessions', newSessions);
}
</script>

<template>
  <div class="table-responsive">
    <table class="table table-hover align-middle">
      <thead>
        <tr>
          <th style="width: 40px">
            <input
              type="checkbox"
              class="form-check-input"
              :checked="allSelected"
              @change="emit('toggleSelectAll', ($event.target as HTMLInputElement).checked)"
            />
          </th>
          <th>Date</th>
          <th>Start time</th>
          <th>End time</th>
          <th class="text-end">Actions</th>
        </tr>
      </thead>
      <tbody>
        <SessionRow
          v-for="(session, index) in sessions"
          :key="session.id || index"
          :model-value="session"
          :selected="selectedIndices.has(index)"
          @update:model-value="(val) => handleUpdateSession(index, val)"
          @delete="emit('markForDeletion', [index])"
          @select="(checked) => emit('toggleSelect', index, checked)"
        />
      </tbody>
    </table>
  </div>
  <p v-if="sessions.length === 0" class="text-center text-muted my-4">
    No sessions found for this class.
  </p>
</template>
