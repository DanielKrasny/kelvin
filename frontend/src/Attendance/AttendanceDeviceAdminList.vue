<script lang="ts" setup>
import { ref, onMounted, watch } from 'vue';
import type { Config, ConfigColumns, Api as DataTableObject } from 'datatables.net';
import DataTablesCore from 'datatables.net-bs5';
import DataTable from 'datatables.net-vue3';
import { type PaginatedResponse, getDataWithCSRF } from '../utilities/api';
import { toastApi } from '../utilities/toast';
import { type AttendanceDevice, DeviceState, type BulkUpdateAttendanceDevice } from './dto';
import { getStateBadgeClass, formatDeviceState, debounce } from './utils';
import VueModal from '../components/VueModal.vue';
import TimeAgo from '../components/TimeAgo.vue';

DataTable.use(DataTablesCore);

const searchLogin = ref('');
const debouncedSearchLogin = ref('');
const selectedStates = ref<DeviceState[]>([]);
const selectedDeviceIds = ref<Set<number>>(new Set());

const updateSearch = debounce((val: string) => {
  debouncedSearchLogin.value = val;
}, 500);

watch(searchLogin, (val) => {
  updateSearch(val);
});

const bulkActionModalOpen = ref(false);
const bulkActionTargetState = ref<DeviceState.ACTIVE | DeviceState.REVOKED | null>(null);
const revokeExistingActive = ref(true);

const columns = [
  {
    title: '',
    data: null,
    orderable: false,
    searchable: false,
    render: '#select',
    width: '30px'
  },
  {
    title: '#',
    data: 'id',
    orderable: false,
    searchable: false
  },
  {
    title: 'User',
    data: 'user_login',
    orderable: false,
    searchable: false
  },
  {
    title: 'Device name',
    data: 'device_name',
    orderable: false,
    searchable: false
  },
  {
    title: 'State',
    data: 'state',
    orderable: false,
    searchable: false,
    render: '#state'
  },
  {
    title: 'Created',
    data: 'created_at',
    orderable: false,
    searchable: false,
    render: '#created'
  },
  {
    title: 'Actions',
    data: null,
    orderable: false,
    searchable: false,
    render: '#actions',
    className: 'text-end'
  }
] satisfies ConfigColumns[];

const options = {
  stripeClasses: ['table-striped', 'table-hover'],
  serverSide: true,
  ajax: async (
    data: {
      length: number;
      start: number;
    },
    callback: (data: {
      data: AttendanceDevice[];
      recordsTotal: number;
      recordsFiltered: number;
    }) => void
  ) => {
    const params = new URLSearchParams();
    params.append('limit', data.length.toString());
    params.append('offset', data.start.toString());

    selectedStates.value.forEach((s) => params.append('state', s));

    let url = '/api/v2/attendance/device/all';
    if (debouncedSearchLogin.value.trim()) {
      url = `/api/v2/attendance/device/user/${encodeURIComponent(debouncedSearchLogin.value.trim())}`;
    }

    const result = await getDataWithCSRF<PaginatedResponse<AttendanceDevice>>(
      `${url}?${params.toString()}`
    );

    if (result) {
      callback({
        data: result.items,
        recordsTotal: result.count,
        recordsFiltered: result.count
      });
    } else {
      callback({ data: [], recordsTotal: 0, recordsFiltered: 0 });
    }
  },
  orderMulti: false,
  pageLength: 25,
  searching: false,
  ordering: false,
  layout: {
    topStart: null,
    topEnd: 'pageLength'
  }
} satisfies Config;

const dataTable = ref();
let table: DataTableObject<unknown>;

onMounted(() => {
  table = dataTable.value?.dt;
});

watch(
  [debouncedSearchLogin, selectedStates],
  () => {
    selectedDeviceIds.value.clear();
    table.ajax.reload();
  },
  { deep: true }
);

function toggleSelection(id: number) {
  if (selectedDeviceIds.value.has(id)) {
    selectedDeviceIds.value.delete(id);
  } else {
    selectedDeviceIds.value.add(id);
  }
}

async function updateDeviceState(
  device: AttendanceDevice,
  newState: DeviceState.ACTIVE | DeviceState.REVOKED
) {
  const response = await getDataWithCSRF(
    `/api/v2/attendance/device/${device.id}`,
    'PATCH',
    { state: newState },
    {},
    true
  );
  if (response) {
    toastApi.success(`Device ${device.id} updated to ${formatDeviceState(newState, 'passive')}.`);
    table.ajax.reload();
  }
}

function startBulkAction(state: DeviceState.ACTIVE | DeviceState.REVOKED) {
  if (selectedDeviceIds.value.size === 0) {
    toastApi.error('No devices selected.');
    return;
  }
  bulkActionTargetState.value = state;
  bulkActionModalOpen.value = true;
}

async function handleBulkActionModalClosed(proceed: boolean) {
  bulkActionModalOpen.value = false;
  if (proceed && bulkActionTargetState.value) {
    const body: BulkUpdateAttendanceDevice = {
      device_ids: Array.from(selectedDeviceIds.value),
      state: bulkActionTargetState.value,
      revoke_active_devices: revokeExistingActive.value
    };

    const response = await getDataWithCSRF(
      '/api/v2/attendance/device/bulk',
      'PATCH',
      body,
      {},
      true
    );
    if (response) {
      toastApi.success('Bulk update completed successfully.');
      selectedDeviceIds.value.clear();
      table.ajax.reload();
    }
  }
  bulkActionTargetState.value = null;
}
</script>

<template>
  <div class="mb-4">
    <h1>Manage attendance devices</h1>
  </div>

  <div class="card mb-4">
    <div class="card-body">
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label" for="login">Search by login</label>
          <input
            id="login"
            v-model="searchLogin"
            type="text"
            class="form-control"
            placeholder="username"
          />
        </div>
        <div class="col-md-8">
          <label class="form-label">Filter by state</label>
          <div class="d-flex gap-3 pt-2">
            <div
              v-for="state in [DeviceState.PENDING, DeviceState.ACTIVE, DeviceState.REVOKED]"
              :key="state"
              class="form-check"
            >
              <input
                :id="'state-' + state"
                v-model="selectedStates"
                class="form-check-input"
                type="checkbox"
                :value="state"
              />
              <label class="form-check-label" :for="'state-' + state">
                {{ formatDeviceState(state, 'passive') }}
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="d-flex justify-content-between align-items-center mb-3">
    <div>
      <span class="text-muted me-3">{{ selectedDeviceIds.size }} selected</span>
      <div class="btn-group btn-group-sm">
        <button
          class="btn btn-outline-success"
          :disabled="selectedDeviceIds.size === 0"
          @click="startBulkAction(DeviceState.ACTIVE)"
        >
          <i class="bi bi-check-lg me-1"></i>Activate selected
        </button>
        <button
          class="btn btn-outline-danger"
          :disabled="selectedDeviceIds.size === 0"
          @click="startBulkAction(DeviceState.REVOKED)"
        >
          <i class="bi bi-x-lg me-1"></i>Revoke selected
        </button>
      </div>
    </div>
  </div>

  <DataTable
    ref="dataTable"
    :columns="columns"
    :options="options"
    class="table table-hover align-middle"
  >
    <template #select="props">
      <input
        v-if="props.rowData.state !== DeviceState.REVOKED"
        type="checkbox"
        class="form-check-input"
        :checked="selectedDeviceIds.has(props.rowData.id)"
        @change="toggleSelection(props.rowData.id)"
      />
    </template>
    <template #state="props">
      <span class="badge" :class="getStateBadgeClass(props.cellData)">
        {{ formatDeviceState(props.cellData, 'passive') }}
      </span>
    </template>
    <template #created="props">
      <TimeAgo v-if="props.cellData" :datetime="props.cellData" />
      <span v-else>-</span>
    </template>
    <template #actions="props">
      <div class="btn-group btn-group-sm">
        <button
          v-if="props.rowData.state === DeviceState.PENDING"
          class="btn btn-outline-success"
          :title="formatDeviceState(DeviceState.ACTIVE, 'action')"
          @click="updateDeviceState(props.rowData, DeviceState.ACTIVE)"
        >
          <i class="bi bi-check-lg"></i>
        </button>
        <button
          v-if="props.rowData.state !== DeviceState.REVOKED"
          class="btn btn-outline-danger"
          :title="formatDeviceState(DeviceState.REVOKED, 'action')"
          @click="updateDeviceState(props.rowData, DeviceState.REVOKED)"
        >
          <i class="bi bi-trash"></i>
        </button>
      </div>
    </template>
  </DataTable>

  <VueModal
    :open="bulkActionModalOpen"
    :title="
      bulkActionTargetState ? 'Bulk ' + formatDeviceState(bulkActionTargetState, 'action') : ''
    "
    proceed-button-label="Confirm"
    @closed="handleBulkActionModalClosed"
  >
    <p v-if="bulkActionTargetState">
      Are you sure you want to
      <strong>{{ formatDeviceState(bulkActionTargetState, 'action').toLowerCase() }}</strong>
      {{ selectedDeviceIds.size }} selected device(s)?
    </p>

    <div v-if="bulkActionTargetState === DeviceState.ACTIVE" class="form-check mt-3">
      <input
        id="revokeExisting"
        v-model="revokeExistingActive"
        class="form-check-input"
        type="checkbox"
      />
      <label class="form-check-label" for="revokeExisting">
        Revoke existing active devices for these users
      </label>
      <div class="form-text">
        Users can only have one active device at a time. If checked, any currently active devices
        for the affected users will be revoked.
      </div>
    </div>
  </VueModal>
</template>

<style>
@import 'datatables.net-bs5';
</style>
