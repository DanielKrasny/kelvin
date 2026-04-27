<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue';
import { getDataWithCSRF, type PaginatedResponse } from '../../utilities/api';
import { toastApi } from '../../utilities/toast';
import SyncLoader from '../../components/SyncLoader.vue';
import VueModal from '../../components/VueModal.vue';
import ClassAttendanceTable from './ClassAttendanceTable.vue';
import ClassAttendanceGraphs from './ClassAttendanceGraphs.vue';
import type { ClassInfo, ClassSession } from '../ClassSessions/dto';
import type { StudentPresence } from './dto';

const props = defineProps<{
  classId: string | number;
}>();

const sessions = ref<ClassSession[]>([]);
const classInfo = ref<ClassInfo | null>(null);
const currentSessionId = ref<number | null>(null);
const students = ref<StudentPresence[]>([]);
const loading = ref(true);
const loadingStudents = ref(false);
const saving = ref(false);

const showFullIdentity = ref(false);
const graphsRef = ref<InstanceType<typeof ClassAttendanceGraphs> | null>(null);

const pendingStudents = ref<{ login: string; is_present: boolean }[]>([]);

const originalPresence = ref<Record<number, boolean>>({});
const unsavedChanges = ref<Record<number, boolean>>({});

const hasUnsavedChanges = computed(
  () => Object.keys(unsavedChanges.value).length > 0 || pendingStudents.value.length > 0
);

const saveModalOpen = ref(false);
const pendingSessionId = ref<number | null>(null);

async function fetchSessions() {
  try {
    const [sessionsRes, classRes] = await Promise.all([
      getDataWithCSRF<PaginatedResponse<ClassSession>>(
        `/api/v2/attendance/class-session/class/${props.classId}?limit=1000`
      ),
      getDataWithCSRF<ClassInfo>(`/api/v2/class/${props.classId}`)
    ]);

    if (sessionsRes) {
      sessions.value = sessionsRes.items;

      if (sessions.value.length > 0) {
        const now = new Date();
        let closest = sessions.value[0];
        let minDiff = Math.abs(now.getTime() - new Date(closest.end).getTime());

        for (const session of sessions.value) {
          const diff = Math.abs(now.getTime() - new Date(session.end).getTime());
          if (diff < minDiff) {
            minDiff = diff;
            closest = session;
          }
        }
        currentSessionId.value = closest.id;
        await fetchStudents(closest.id);
      }
    }

    if (classRes) {
      classInfo.value = classRes;
    }
  } catch (e) {
    console.error(e);
    toastApi.error('Failed to fetch class data');
  } finally {
    loading.value = false;
  }
}

async function fetchStudents(sessionId: number) {
  loadingStudents.value = true;
  try {
    const data = await getDataWithCSRF<StudentPresence[]>(
      `/api/v2/attendance/class-session/${sessionId}/presence`
    );
    students.value = data;
    originalPresence.value = {};
    unsavedChanges.value = {};
    pendingStudents.value = [];
    data.forEach((s) => {
      originalPresence.value[s.id] = s.is_present;
    });
  } catch (e) {
    console.error(e);
    toastApi.error('Failed to fetch students');
  } finally {
    loadingStudents.value = false;
  }
}

function togglePresence(studentId: number, isPresent: boolean) {
  const student = students.value.find((s) => s.id === studentId);
  if (!student) return;

  student.is_present = isPresent;
  if (originalPresence.value[studentId] !== isPresent) {
    unsavedChanges.value[studentId] = true;
  } else {
    delete unsavedChanges.value[studentId];
  }
}

function addPendingStudent() {
  pendingStudents.value.push({ login: '', is_present: true });
}

function removePendingStudent(index: number) {
  pendingStudents.value.splice(index, 1);
}

function updatePendingStudent(
  index: number,
  field: 'login' | 'is_present',
  value: string | boolean
) {
  if (field === 'login' && typeof value === 'string') {
    pendingStudents.value[index].login = value;
  } else if (field === 'is_present' && typeof value === 'boolean') {
    pendingStudents.value[index].is_present = value;
  }
}

async function saveChanges() {
  if (!currentSessionId.value || !hasUnsavedChanges.value) return;

  saving.value = true;
  const records = [
    ...Object.keys(unsavedChanges.value).map((id) => {
      const studentId = parseInt(id);
      const student = students.value.find((s) => s.id === studentId);
      return {
        student_login: student?.login,
        is_present: student?.is_present
      };
    }),
    ...pendingStudents.value
      .filter((s) => s.login.trim() !== '')
      .map((s) => ({
        student_login: s.login.trim(),
        is_present: s.is_present
      }))
  ];

  try {
    const response = await getDataWithCSRF<unknown>(
      '/api/v2/attendance/teacher/manual',
      'POST',
      {
        class_session_id: currentSessionId.value,
        records
      },
      undefined,
      true
    );

    if (response !== undefined) {
      toastApi.success('Attendance saved successfully');
      unsavedChanges.value = {};
      pendingStudents.value = [];

      await fetchStudents(currentSessionId.value);

      if (graphsRef.value) {
        graphsRef.value.fetchClassPresence();
        graphsRef.value.fetchSessionTimespans();
      }
    }
  } catch (e) {
    console.error(e);
    toastApi.error('Failed to save attendance');
  } finally {
    saving.value = false;
  }
}

function onSessionChange(sessionId: number) {
  if (hasUnsavedChanges.value) {
    pendingSessionId.value = sessionId;
    saveModalOpen.value = true;
  } else {
    currentSessionId.value = sessionId;
    fetchStudents(sessionId);
  }
}

function confirmSwitchWithoutSaving() {
  if (pendingSessionId.value) {
    currentSessionId.value = pendingSessionId.value;
    fetchStudents(pendingSessionId.value);
  }
  saveModalOpen.value = false;
  pendingSessionId.value = null;
}

async function confirmSwitchWithSaving() {
  await saveChanges();
  confirmSwitchWithoutSaving();
}

function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    saveChanges();
  }
}

onMounted(() => {
  fetchSessions();
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <div class="container-fluid mt-3">
    <div v-if="loading" class="text-center mt-5">
      <SyncLoader />
    </div>
    <div v-else>
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 class="mb-0">Class attendance</h2>
          <small v-if="classInfo" class="text-muted">
            {{ classInfo.subject_abbr }} {{ classInfo.room || '' }} {{ classInfo.timeslot }}
            {{ classInfo.code }} {{ classInfo.teacher_username }}
          </small>
        </div>
        <div class="d-flex gap-2">
          <button
            class="btn btn-outline-secondary d-flex align-items-center gap-2"
            @click="showFullIdentity = !showFullIdentity"
          >
            <span
              class="iconify"
              :data-icon="showFullIdentity ? 'mdi:account-details' : 'mdi:account-outline'"
            ></span>
            {{ showFullIdentity ? 'Show logins only' : 'Show full names' }}
          </button>
          <select
            class="form-select"
            style="width: auto"
            :value="currentSessionId"
            @change="(e) => onSessionChange(parseInt((e.target as HTMLSelectElement).value))"
          >
            <option v-for="session in sessions" :key="session.id" :value="session.id">
              {{ new Date(session.start).toLocaleString() }}
            </option>
          </select>
          <button
            class="btn btn-primary d-flex align-items-center gap-2"
            :disabled="!hasUnsavedChanges || saving"
            @click="saveChanges"
          >
            <SyncLoader v-if="saving" :size="14" color="#fff" />
            <span v-show="!saving" class="iconify" data-icon="mdi:content-save"></span>
            Save
          </button>
        </div>
      </div>

      <ClassAttendanceGraphs
        ref="graphsRef"
        :class-id="classId"
        :sessions="sessions"
        :current-session-id="currentSessionId"
        @select-session="onSessionChange"
      />

      <div class="card">
        <div class="card-body">
          <div v-if="loadingStudents" class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
          </div>
          <ClassAttendanceTable
            v-else-if="currentSessionId"
            :key="currentSessionId"
            :session-id="currentSessionId"
            :students="students"
            :unsaved-changes="unsavedChanges"
            :show-full-identity="showFullIdentity"
            :pending-students="pendingStudents"
            @toggle-presence="togglePresence"
            @add-pending-student="addPendingStudent"
            @remove-pending-student="removePendingStudent"
            @update-pending-student="updatePendingStudent"
          />
          <div v-else class="text-center py-5 text-muted">
            No sessions available for this class.
          </div>
        </div>
      </div>
    </div>

    <VueModal
      :open="saveModalOpen"
      title="Unsaved changes"
      cancel-button-label="Don't save"
      proceed-button-label="Save"
      @closed="(proceed) => (proceed ? confirmSwitchWithSaving() : confirmSwitchWithoutSaving())"
    >
      You have unsaved changes in the current session. Do you want to save them before switching?
    </VueModal>
  </div>
</template>
