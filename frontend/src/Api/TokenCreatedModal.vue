<script lang="ts" setup>
import VueModal from '../components/VueModal.vue';
import PasswordInput from '../components/PasswordInput.vue';
import type { CreateUserToken } from './dto';
import { ref } from 'vue';

const props = defineProps<{
  open: boolean;
  token: CreateUserToken | null;
}>();

defineEmits<{
  (e: 'closed'): void;
}>();

const token = ref(props.token?.token);
</script>

<template>
  <VueModal
    :open="open"
    title="Token created successfully"
    cancel-button-label=""
    proceed-button-label="Close"
    @closed="$emit('closed')"
  >
    <div class="alert alert-warning">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      Make sure to copy the API token now. You won't be able to see it again!
    </div>
    <div v-if="token">
      <label class="form-label" for="token">Your token</label>
      <PasswordInput v-model="token" name="token" copy-to-clipboard readonly />
    </div>
  </VueModal>
</template>
