<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import hljs from 'highlight.js/lib/core';
import CopyToClipboard from '../components/CopyToClipboard.vue';

const baseUrl = ref('');

onMounted(() => {
  baseUrl.value = window.location.origin + '/';
});

const curlCode = computed(() => {
  return `curl -H "Authorization: Bearer YOUR_TOKEN" ${baseUrl.value}`;
});

const pythonCode = computed(() => {
  return `import requests

url = '${baseUrl.value}'
headers = {
    'Authorization': 'Bearer YOUR_TOKEN'
}

res = requests.get(url, headers=headers)
print(res.text)`;
});

const highlightedCurl = computed(() => {
  return hljs.highlight(curlCode.value, { language: 'bash' }).value;
});

const highlightedPython = computed(() => {
  return hljs.highlight(pythonCode.value, { language: 'python' }).value;
});
</script>

<template>
  <div class="mt-5">
    <h2>Usage</h2>

    <div class="mb-4">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h5 class="mb-0">curl</h5>
        <CopyToClipboard :content="curlCode" title="Copy curl command">
          <button class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-clipboard me-1"></i>Copy
          </button>
        </CopyToClipboard>
      </div>
      <pre
        class="bg-body-tertiary p-3 rounded border"
      ><!--eslint-disable vue/no-v-html--><code class="hljs" v-html="highlightedCurl" /></pre>
    </div>

    <div class="mb-4">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h5 class="mb-0">Python requests</h5>
        <CopyToClipboard :content="pythonCode" title="Copy python code">
          <button class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-clipboard me-1"></i>Copy
          </button>
        </CopyToClipboard>
      </div>
      <pre
        class="bg-body-tertiary p-3 rounded border"
      ><!--eslint-disable vue/no-v-html--><code class="hljs" v-html="highlightedPython" /></pre>
    </div>
  </div>
</template>
