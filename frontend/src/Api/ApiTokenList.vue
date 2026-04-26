<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import type { Config, ConfigColumns, Api as DataTableObject } from 'datatables.net';
import DataTablesCore from 'datatables.net-bs5';
import DataTable from 'datatables.net-vue3';
import { type PaginatedResponse, getDataWithCSRF } from '../utilities/api';
import { toastApi } from '../utilities/toast';
import type { UserToken, CreateUserToken } from './dto';
import VueModal from '../components/VueModal.vue';
import TimeAgo from '../components/TimeAgo.vue';
import TokenCreatedModal from './TokenCreatedModal.vue';

DataTable.use(DataTablesCore);

const tokenToDelete = ref<UserToken | null>(null);
const deleteModalOpen = ref(false);

const newToken = ref<CreateUserToken | null>(null);
const createModalOpen = ref(false);

const columns = [
  {
    title: '#',
    data: 'id',
    orderable: false,
    searchable: false
  },
  {
    title: 'Client',
    data: (row: UserToken) => row.client?.name || '-',
    orderable: false,
    searchable: false
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
    callback: (data: { data: UserToken[]; recordsTotal: number; recordsFiltered: number }) => void
  ) => {
    const params = new URLSearchParams();
    params.append('limit', data.length.toString());
    params.append('offset', data.start.toString());

    const result = await getDataWithCSRF<PaginatedResponse<UserToken>>(
      `/api/v2/api/token/?${params.toString()}`
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

function confirmDelete(token: UserToken) {
  tokenToDelete.value = token;
  deleteModalOpen.value = true;
}

async function handleDeleteModalClosed(proceed: boolean) {
  deleteModalOpen.value = false;
  if (proceed && tokenToDelete.value) {
    const response = await getDataWithCSRF(
      `/api/v2/api/token/${tokenToDelete.value.id}`,
      'DELETE',
      undefined,
      {},
      true
    );
    if (response) {
      toastApi.success('The token was successfully revoked.');
    }
    table.ajax.reload();
  }
  tokenToDelete.value = null;
}

async function createToken() {
  const data = await getDataWithCSRF<CreateUserToken>('/api/v2/api/token/', 'POST', {}, {}, true);
  if (data) {
    newToken.value = data;
    createModalOpen.value = true;
    table.ajax.reload();
  }
}
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1>My API Tokens</h1>
    <button class="btn btn-primary" @click="createToken">
      <i class="bi bi-plus-lg me-1"></i>Create new token
    </button>
  </div>

  <DataTable
    ref="dataTable"
    :columns="columns"
    :options="options"
    class="table table-hover align-middle"
  >
    <template #created="props">
      <TimeAgo v-if="props.cellData" :datetime="props.cellData" />
      <span v-else>-</span>
    </template>
    <template #actions="props">
      <button class="btn btn-outline-danger btn-sm" @click="confirmDelete(props.rowData)">
        <i class="bi bi-trash me-1"></i>Revoke
      </button>
    </template>
  </DataTable>

  <VueModal
    :open="deleteModalOpen"
    title="Revoke token"
    proceed-button-label="Revoke"
    @closed="handleDeleteModalClosed"
  >
    <p>
      Are you sure you want to revoke this API token? Any applications using this token will lose
      access immediately.
    </p>
    <div v-if="tokenToDelete" class="mb-0">
      <div><strong>Token ID:</strong> {{ tokenToDelete.id }}</div>
      <div v-if="tokenToDelete.client">
        <strong>Client:</strong> {{ tokenToDelete.client.name }}
      </div>
      <div v-if="tokenToDelete.created_at">
        <strong>Created:</strong> <TimeAgo :datetime="tokenToDelete.created_at" />
      </div>
    </div>
  </VueModal>

  <TokenCreatedModal
    :open="createModalOpen"
    :token="newToken"
    @closed="() => (createModalOpen = false)"
  />
</template>

<style>
@import 'datatables.net-bs5';
</style>
