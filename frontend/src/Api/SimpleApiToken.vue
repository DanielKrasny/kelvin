<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { getDataWithCSRF } from '../utilities/api';
import type { ApiClient, CreateUserToken } from './dto';
import SyncLoader from '../components/SyncLoader.vue';
import TokenCreatedModal from './TokenCreatedModal.vue';

const props = defineProps<{
  clientId: string;
}>();

const client = ref<ApiClient | null>(null);
const loading = ref(true);
const creating = ref(false);
const newToken = ref<CreateUserToken | null>(null);
const createModalOpen = ref(false);

onMounted(async () => {
  const data = await getDataWithCSRF<ApiClient>(`/api/v2/api/client/${props.clientId}`);
  if (data) {
    client.value = data;
    loading.value = false;
  } else {
    window.location.href = '/api_token';
  }
});

async function handleAccept() {
  creating.value = true;
  try {
    const data = await getDataWithCSRF<CreateUserToken>(
      '/api/v2/api/token/',
      'POST',
      { client_id: props.clientId },
      {},
      true
    );

    if (data) {
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
        return;
      }
      newToken.value = data;
      createModalOpen.value = true;
    } else {
      creating.value = false;
    }
  } catch (error) {
    console.error('Error creating token:', error);
    creating.value = false;
  }
}

function handleReject() {
  window.location.href = '/api_token';
}

function handleModalClosed() {
  createModalOpen.value = false;
  window.location.href = '/api_token';
}
</script>

<template>
  <div v-if="loading" class="d-flex justify-content-center my-5">
    <SyncLoader />
  </div>
  <div v-else-if="client" class="card mx-auto mt-5" style="max-width: 500px">
    <div class="card-body text-center p-4">
      <h3 class="card-title mb-4">API Token Request</h3>
      <p class="card-text fs-5">
        Do you want to create an API token for application <strong>{{ client.name }}</strong
        >?
      </p>
      <div class="d-flex justify-content-center gap-3 mt-4">
        <button class="btn btn-outline-secondary px-4" :disabled="creating" @click="handleReject">
          Reject
        </button>
        <button class="btn btn-primary px-4" :disabled="creating" @click="handleAccept">
          <span
            v-if="creating"
            class="spinner-border spinner-border-sm me-2"
            role="status"
            aria-hidden="true"
          ></span>
          Accept
        </button>
      </div>
    </div>
  </div>

  <TokenCreatedModal :open="createModalOpen" :token="newToken" @closed="handleModalClosed" />
</template>
