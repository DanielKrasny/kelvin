<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { getDataWithCSRF } from '../../utilities/api';
import type { StudentPresence, AttendanceRecord } from './dto';
import { AttendanceRecordFormat } from '../../Attendance/dto';

const props = defineProps<{
  sessionId: number;
  students: StudentPresence[];
  unsavedChanges: Record<number, boolean>;
  showFullIdentity: boolean;
  pendingStudents: { login: string; is_present: boolean }[];
}>();

const emit = defineEmits<{
  (e: 'toggle-presence', studentId: number, isPresent: boolean): void;
  (e: 'add-pending-student'): void;
  (e: 'remove-pending-student', index: number): void;
  (e: 'update-pending-student', index: number, field: string, value: string | boolean): void;
}>();

const sortedStudents = computed(() => sortStudents(props.students));

const expandedRows = ref<Set<number>>(new Set());
const detailedRecords = ref<Record<number, AttendanceRecord[]>>({});
const loadingDetails = ref<Record<number, boolean>>({});

function sortStudents(students: StudentPresence[]): StudentPresence[] {
  return [...students].sort((a, b) => {
    const last = a.last_name.localeCompare(b.last_name);
    if (last !== 0) return last;
    const first = a.first_name.localeCompare(b.first_name);
    if (first !== 0) return first;
    return a.login.localeCompare(b.login);
  });
}

function formatStudentName(student: StudentPresence): string {
  return `${student.last_name} ${student.first_name} (${student.login})`;
}

async function toggleExpand(student: StudentPresence) {
  if (expandedRows.value.has(student.id)) {
    expandedRows.value.delete(student.id);
  } else {
    expandedRows.value.add(student.id);
    if (!detailedRecords.value[student.id]) {
      await fetchDetailedRecords(student.id);
    }
  }
}

async function fetchDetailedRecords(studentId: number) {
  loadingDetails.value[studentId] = true;
  try {
    const data = await getDataWithCSRF<AttendanceRecord[]>(
      `/api/v2/attendance/class-session/${props.sessionId}/presence/${studentId}`
    );
    detailedRecords.value[studentId] = data;
  } catch (e) {
    console.error(e);
  } finally {
    loadingDetails.value[studentId] = false;
  }
}

watch(
  () => props.sessionId,
  () => {
    expandedRows.value.clear();
    detailedRecords.value = {};
  }
);
</script>

<template>
  <div class="table-responsive">
    <table class="table table-hover">
      <thead>
        <tr>
          <th style="width: 40px"></th>
          <th>Student</th>
          <th>Status</th>
          <th>Method</th>
          <th style="width: 100px">Present</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="student in sortedStudents" :key="student.id">
          <tr :class="{ 'unsaved-row': unsavedChanges[student.id] }">
            <td>
              <button
                class="btn btn-sm btn-outline-secondary py-0 px-1"
                @click="toggleExpand(student)"
              >
                <span
                  class="iconify"
                  :data-icon="
                    expandedRows.has(student.id) ? 'mdi:chevron-down' : 'mdi:chevron-right'
                  "
                ></span>
              </button>
            </td>
            <td>
              {{ showFullIdentity ? formatStudentName(student) : student.login }}
            </td>
            <td>
              <span :class="['badge', student.is_present ? 'bg-success' : 'bg-danger']">
                {{ student.is_present ? 'Present' : 'Absent' }}
              </span>
              <small v-if="unsavedChanges[student.id]" class="ms-2 text-warning italic"
                >● unsaved</small
              >
            </td>
            <td>{{ student.record_format || '-' }}</td>
            <td class="text-center">
              <input
                class="form-check-input"
                type="checkbox"
                :checked="student.is_present"
                @change="
                  (e) => emit('toggle-presence', student.id, (e.target as HTMLInputElement).checked)
                "
              />
            </td>
          </tr>
          <tr
            v-if="expandedRows.has(student.id)"
            :key="'expanded-' + student.id"
            class="expanded-row"
          >
            <td colspan="5" class="p-0 border-0 shadow-inner">
              <div class="expanded-container py-2 px-3">
                <div v-if="loadingDetails[student.id]" class="text-center py-2">
                  <div class="spinner-border spinner-border-sm text-secondary" role="status"></div>
                </div>
                <div v-else-if="detailedRecords[student.id]?.length">
                  <table class="table table-sm table-borderless mb-0">
                    <thead class="border-bottom">
                      <tr class="text-muted small">
                        <th style="width: 40px"></th>
                        <th style="width: 25%">Time</th>
                        <th style="width: 20%">Format</th>
                        <th style="width: 15%">State</th>
                        <th style="width: 15%">By</th>
                        <th>Note</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="record in detailedRecords[student.id]"
                        :key="record.id"
                        class="small"
                      >
                        <td></td>
                        <td>{{ new Date(record.attendance_time).toLocaleString() }}</td>
                        <td>{{ record.record_format }}</td>
                        <td>
                          <span :class="record.is_present ? 'text-success' : 'text-danger'">
                            {{ record.is_present ? 'Present' : 'Absent' }}
                          </span>
                        </td>
                        <td>{{ record.created_by_login }}</td>
                        <td class="text-muted">{{ record.description || '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="text-center text-muted small py-2">
                  No records found for this student in this session.
                </div>
              </div>
            </td>
          </tr>
        </template>
        <tr
          v-for="(pending, index) in pendingStudents"
          :key="'pending-' + index"
          class="unsaved-row"
        >
          <td>
            <button
              class="btn btn-sm btn-outline-danger py-0 px-1"
              title="Remove"
              @click="emit('remove-pending-student', index)"
            >
              <span class="iconify" data-icon="mdi:trash-can-outline"></span>
            </button>
          </td>
          <td>
            <input
              type="text"
              class="form-control form-control-sm"
              placeholder="Student login"
              :value="pending.login"
              @input="
                (e) =>
                  emit(
                    'update-pending-student',
                    index,
                    'login',
                    (e.target as HTMLInputElement).value
                  )
              "
            />
          </td>
          <td>
            <span :class="['badge', pending.is_present ? 'bg-success' : 'bg-danger']">
              {{ pending.is_present ? 'Present' : 'Absent' }}
            </span>
            <small class="ms-2 text-warning italic">● new</small>
          </td>
          <td>{{ AttendanceRecordFormat.MANUAL_TEACHER }}</td>
          <td class="text-center">
            <input
              class="form-check-input"
              type="checkbox"
              :checked="pending.is_present"
              @change="
                (e) =>
                  emit(
                    'update-pending-student',
                    index,
                    'is_present',
                    (e.target as HTMLInputElement).checked
                  )
              "
            />
          </td>
        </tr>
        <tr :key="'add-student-row'">
          <td colspan="5">
            <button class="btn btn-sm btn-outline-primary" @click="emit('add-pending-student')">
              <span class="iconify" data-icon="mdi:account-plus"></span>
              Add Student
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.italic {
  font-style: italic;
}

.unsaved-row {
  background-color: rgba(255, 193, 7, 0.05);
  box-shadow: inset 3px 0 0 var(--bs-warning);
}

.expanded-container {
  background-color: var(--bs-tertiary-bg);
  border-bottom: 1px solid var(--bs-border-color-translucent);
}

.expanded-row td {
  padding: 0;
}
</style>
