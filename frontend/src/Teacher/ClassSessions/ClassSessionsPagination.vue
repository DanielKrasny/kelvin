<script setup lang="ts">
defineProps<{
  currentPage: number;
  totalPages: number;
  offset: number;
  limit: number;
}>();

const emit = defineEmits(['changePage']);

function changePage(newOffset: number) {
  emit('changePage', newOffset);
}
</script>

<template>
  <nav v-if="totalPages > 1" class="d-flex justify-content-center mt-3">
    <ul class="pagination pagination-sm">
      <li class="page-item" :class="{ disabled: currentPage === 1 }">
        <button class="page-link" @click="changePage(offset - limit)">Previous</button>
      </li>
      <li
        v-for="page in totalPages"
        :key="page"
        class="page-item"
        :class="{ active: page === currentPage }"
      >
        <button class="page-link" @click="changePage((page - 1) * limit)">{{ page }}</button>
      </li>
      <li class="page-item" :class="{ disabled: currentPage === totalPages }">
        <button class="page-link" @click="changePage(offset + limit)">Next</button>
      </li>
    </ul>
  </nav>
</template>
