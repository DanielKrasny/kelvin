<script lang="ts" setup>
import { ref } from 'vue';
import CopyToClipboard from './CopyToClipboard.vue';

const model = defineModel<string>({ default: '' });

interface Props {
  copyToClipboard?: boolean;
  placeholder?: string;
  id?: string;
  name?: string;
  autocomplete?: string;
  readonly?: boolean;
}

withDefaults(defineProps<Props>(), {
  copyToClipboard: false,
  placeholder: 'Password',
  id: undefined,
  name: undefined,
  autocomplete: undefined,
  readonly: false
});

const showPassword = ref(false);

const toggleVisibility = () => {
  showPassword.value = !showPassword.value;
};
</script>

<template>
  <div class="input-group">
    <slot name="left"></slot>
    <input
      :id="id"
      v-model="model"
      :name="name"
      :type="showPassword ? 'text' : 'password'"
      class="form-control"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :readonly="readonly"
    />
    <slot name="before-right"></slot>
    <button
      class="btn btn-outline-secondary"
      :title="showPassword ? 'Hide password' : 'Show password'"
      type="button"
      @click="toggleVisibility"
    >
      <i :class="['bi', showPassword ? 'bi-eye-slash' : 'bi-eye']"></i>
    </button>
    <CopyToClipboard
      v-if="copyToClipboard"
      :content="model"
      title="Copy to clipboard"
      class="copy-button-wrapper"
    >
      <button class="btn btn-outline-secondary" type="button">
        <i class="bi bi-clipboard"></i>
      </button>
    </CopyToClipboard>
    <slot name="after-right"></slot>
  </div>
</template>

<style scoped>
.copy-button-wrapper {
  display: flex;
}

.copy-button-wrapper :deep(.btn) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  margin-left: -1px;
}
</style>
