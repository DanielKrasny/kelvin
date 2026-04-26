<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { getDataWithCSRF, type PaginatedResponse } from '../../utilities/api';
import { toastApi } from '../../utilities/toast';
import SyncLoader from '../../components/SyncLoader.vue';
import ClassSessionsTable from './ClassSessionsTable.vue';
import ClassSessionsPagination from './ClassSessionsPagination.vue';
import BulkAddSessions from './BulkAddSessions.vue';
import VueModal from '../../components/VueModal.vue';
import type { ClassInfo, ClassSession, CreateClassSession, UpdateClassSession } from './dto';

const props = defineProps<{
  classId: string | number;
}>();

interface ClassSessionLocal extends Partial<ClassSession> {
  id?: number;
  start: string;
  end: string;
  _isNew?: boolean;
  _deleted?: boolean;
  _original?: { start: string; end: string };
}

const sessions = ref<ClassSessionLocal[]>([]);
const classInfo = ref<ClassInfo | null>(null);
const loading = ref(true);
const saving = ref(false);

// Pagination
const limit = ref(25);
const offset = ref(0);
const totalCount = ref(0);
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const totalPages = computed(() => Math.ceil(totalCount.value / limit.value));

// Selection
const selectedIndices = ref<Set<number>>(new Set());

// Deletion
const deleteModalOpen = ref(false);
const sessionIdsToDelete = ref<number[]>([]);
const dontAskDeleteAgain = ref(false);

// Page change confirmation
const pageChangeModalOpen = ref(false);
const targetOffset = ref(0);

async function loadData(newOffset = offset.value) {
  loading.value = true;
  selectedIndices.value.clear();
  try {
    const [sessionsRes, classRes] = await Promise.all([
      getDataWithCSRF<PaginatedResponse<ClassSession>>(
        `/api/v2/attendance/class-session/class/${props.classId}?limit=${limit.value}&offset=${newOffset}`
      ),
      getDataWithCSRF<ClassInfo>(`/api/v2/class/${props.classId}`)
    ]);

    if (sessionsRes) {
      sessions.value = sessionsRes.items.map((s) => ({
        ...s,
        _original: { start: s.start, end: s.end }
      }));
      totalCount.value = sessionsRes.count;
      offset.value = newOffset;
    }
    if (classRes) {
      classInfo.value = classRes;
    }
  } catch (err) {
    console.error(err);
    toastApi.error('Failed to load class sessions');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadData();
  window.addEventListener('keydown', handleGlobalKeyDown);
});

function handleGlobalKeyDown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 's') {
    e.preventDefault();
    if (canSave.value) save();
  }
}

const isDirty = (session: ClassSessionLocal) => {
  if (session._isNew || session._deleted) return true;
  if (!session._original) return false;
  return session.start !== session._original.start || session.end !== session._original.end;
};

const canSave = computed(() => {
  return sessions.value.some(isDirty);
});

async function save() {
  if (!canSave.value || saving.value) return;
  saving.value = true;

  try {
    const toCreate: CreateClassSession[] = sessions.value
      .filter((s) => s._isNew && !s._deleted)
      .map((s) => ({
        start: s.start,
        end: s.end
      }));

    const toUpdate: UpdateClassSession[] = sessions.value
      .filter((s) => s.id && isDirty(s) && !s._deleted)
      .map((s) => ({
        id: s.id as number,
        start: s.start,
        end: s.end
      }));

    const toDelete = sessions.value.filter((s) => s.id && s._deleted).map((s) => s.id as number);

    const promises = [];

    if (toCreate.length > 0) {
      promises.push(
        getDataWithCSRF(`/api/v2/attendance/class-session/class/${props.classId}/bulk`, 'POST', {
          sessions: toCreate
        })
      );
    }

    if (toUpdate.length > 0) {
      promises.push(
        getDataWithCSRF(`/api/v2/attendance/class-session/class/${props.classId}/bulk`, 'PATCH', {
          sessions: toUpdate
        })
      );
    }

    if (toDelete.length > 0) {
      promises.push(
        getDataWithCSRF(`/api/v2/attendance/class-session/class/${props.classId}/bulk`, 'DELETE', {
          session_ids: toDelete
        })
      );
    }

    const results = await Promise.all(promises);
    if (results.every((r) => r !== undefined)) {
      toastApi.success('Sessions saved successfully');
      await loadData();
    } else {
      toastApi.error('Some changes could not be saved');
    }
  } catch (e) {
    console.error(e);
    toastApi.error('Failed to save sessions');
  } finally {
    saving.value = false;
  }
}

function onBulkAdd(newSessions: ClassSessionLocal[]) {
  sessions.value = [...sessions.value, ...newSessions];
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    selectedIndices.value = new Set(sessions.value.keys());
  } else {
    selectedIndices.value.clear();
  }
}

function toggleSelect(index: number, checked: boolean) {
  if (checked) {
    selectedIndices.value.add(index);
  } else {
    selectedIndices.value.delete(index);
  }
}

function markForDeletion(indices: number[], forceDelete: boolean | null = null) {
  const needsWarning = indices.some((idx) => {
    const s = sessions.value[idx];
    return !s._isNew && (forceDelete === true || (!s._deleted && forceDelete === null));
  });

  if (needsWarning && !dontAskDeleteAgain.value) {
    sessionIdsToDelete.value = indices;
    deleteModalOpen.value = true;
  } else {
    performDeletion(indices, forceDelete);
  }
}

function performDeletion(indices: number[], forceDelete: boolean | null = null) {
  const toRemoveSet = new Set(indices);
  const newSessions: ClassSessionLocal[] = [];

  sessions.value.forEach((session, idx) => {
    if (toRemoveSet.has(idx)) {
      if (session._isNew) {
        // New session was not sent to the server, removing immediately
        return;
      }
      // Existing session should be marked for deletion
      if (forceDelete !== null) {
        session._deleted = forceDelete;
      } else {
        session._deleted = !session._deleted;
      }
    }
    newSessions.push(session);
  });

  sessions.value = newSessions;
  selectedIndices.value.clear();
}

function proceedDelete(confirmed: boolean) {
  deleteModalOpen.value = false;
  if (confirmed) {
    performDeletion(sessionIdsToDelete.value, true);
  }
  sessionIdsToDelete.value = [];
}

function changePage(newOffset: number) {
  if (canSave.value) {
    targetOffset.value = newOffset;
    pageChangeModalOpen.value = true;
  } else {
    loadData(newOffset);
  }
}

function proceedPageChange(confirmed: boolean) {
  pageChangeModalOpen.value = false;
  if (confirmed) {
    save().then(() => {
      if (!saving.value) loadData(targetOffset.value);
    });
  } else {
    loadData(targetOffset.value);
  }
}

function bulkDeleteSelected() {
  if (selectedIndices.value.size === 0) return;
  markForDeletion(Array.from(selectedIndices.value), true);
}
</script>

<template>
  <div class="container mt-4">
    <div v-if="loading" class="text-center my-5">
      <SyncLoader />
    </div>
    <div v-else-if="classInfo">
      <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
          <li class="breadcrumb-item"><a href="/">Home</a></li>
          <li class="breadcrumb-item active">
            Class sessions ({{ classInfo.subject_abbr }} {{ classInfo.room }}
            {{ classInfo.timeslot }} {{ classInfo.code }} {{ classInfo.teacher_username }})
          </li>
        </ol>
      </nav>

      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Manage class sessions</h3>
        <div class="d-flex gap-2">
          <button
            class="btn btn-outline-danger"
            :disabled="selectedIndices.size === 0"
            @click="bulkDeleteSelected"
          >
            Delete selected ({{ selectedIndices.size }})
          </button>
          <button class="btn btn-primary" :disabled="!canSave || saving" @click="save">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
            Save changes (Ctrl+S)
          </button>
        </div>
      </div>

      <BulkAddSessions :default-start-time="classInfo.time.substring(0, 5)" @add="onBulkAdd" />

      <ClassSessionsTable
        v-model:sessions="sessions"
        :selected-indices="selectedIndices"
        @toggle-select-all="toggleSelectAll"
        @toggle-select="toggleSelect"
        @mark-for-deletion="markForDeletion"
      />

      <ClassSessionsPagination
        :current-page="currentPage"
        :total-pages="totalPages"
        :offset="offset"
        :limit="limit"
        @change-page="changePage"
      />

      <VueModal
        :open="deleteModalOpen"
        title="Confirm Deletion"
        proceed-button-label="Delete"
        @closed="proceedDelete"
      >
        <p>
          Do you really want to delete
          {{
            sessionIdsToDelete.length > 1
              ? 'these ' + sessionIdsToDelete.length + ' sessions'
              : 'this session'
          }}?
          <strong
            >This action might also delete all attendance records for
            {{ sessionIdsToDelete.length > 1 ? 'these sessions' : 'this session' }}!</strong
          >
        </p>
        <div class="form-check mt-3">
          <input
            id="dontAskAgain"
            v-model="dontAskDeleteAgain"
            type="checkbox"
            class="form-check-input"
          />
          <label class="form-check-label" for="dontAskAgain">Don't ask again</label>
        </div>
      </VueModal>

      <VueModal
        :open="pageChangeModalOpen"
        title="Unsaved Changes"
        proceed-button-label="Save and continue"
        cancel-button-label="Discard and continue"
        @closed="proceedPageChange"
      >
        Do you want to save changes before you change the page?
      </VueModal>
    </div>
  </div>
</template>
