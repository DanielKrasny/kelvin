<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import type { Config, ConfigColumns, Api as DataTableObject } from 'datatables.net';
import DataTablesCore from 'datatables.net-bs5';
import DataTable from 'datatables.net-vue3';
import { type PaginatedResponse, getDataWithCSRF } from '../utilities/api';
import { toastApi } from '../utilities/toast';
import { type AttendanceDevice, DeviceState } from './dto';
import { getStateBadgeClass, formatDeviceState } from './utils';
import VueModal from '../components/VueModal.vue';
import TimeAgo from '../components/TimeAgo.vue';

DataTable.use(DataTablesCore);

const deviceToRevoke = ref<AttendanceDevice | null>(null);
const revokeModalOpen = ref(false);

const columns = [
  {
    title: '#',
    data: 'id',
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

    const result = await getDataWithCSRF<PaginatedResponse<AttendanceDevice>>(
      `/api/v2/attendance/device/?${params.toString()}`
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

function confirmRevoke(device: AttendanceDevice) {
  deviceToRevoke.value = device;
  revokeModalOpen.value = true;
}

async function handleRevokeModalClosed(proceed: boolean) {
  revokeModalOpen.value = false;
  if (proceed && deviceToRevoke.value) {
    const response = await getDataWithCSRF(
      `/api/v2/attendance/device/${deviceToRevoke.value.id}`,
      'PATCH',
      { state: DeviceState.REVOKED },
      {},
      true
    );
    if (response) {
      toastApi.success(
        `The device was successfully ${formatDeviceState(DeviceState.REVOKED, 'passive')}.`
      );
    }
    table.ajax.reload();
  }
  deviceToRevoke.value = null;
}
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1>My attendance devices</h1>
  </div>

  <DataTable
    ref="dataTable"
    :columns="columns"
    :options="options"
    class="table table-hover align-middle"
  >
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
      <button
        v-if="props.rowData.state !== DeviceState.REVOKED"
        class="btn btn-outline-danger btn-sm"
        @click="confirmRevoke(props.rowData)"
      >
        <i class="bi bi-trash me-1"></i>Revoke
      </button>
    </template>
  </DataTable>

  <VueModal
    :open="revokeModalOpen"
    :title="formatDeviceState(DeviceState.REVOKED, 'action') + ' device'"
    :proceed-button-label="formatDeviceState(DeviceState.REVOKED, 'action')"
    @closed="handleRevokeModalClosed"
  >
    <p>
      Are you sure you want to
      {{ formatDeviceState(DeviceState.REVOKED, 'action').toLowerCase() }} this attendance device?
      You will no longer be able to use it for attendance.
    </p>
    <div v-if="deviceToRevoke" class="mb-0">
      <div><strong>Device ID:</strong> {{ deviceToRevoke.id }}</div>
      <div><strong>Device Name:</strong> {{ deviceToRevoke.device_name }}</div>
      <div v-if="deviceToRevoke.created_at">
        <strong>Created:</strong> <TimeAgo :datetime="deviceToRevoke.created_at" />
      </div>
    </div>
  </VueModal>
</template>

<style>
@import 'datatables.net-bs5';
</style>
