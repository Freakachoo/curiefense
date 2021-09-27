<template>
  <div class="card">
    <div class="card-content">
      <div class="content">
        <div class="columns columns-divided">
          <div class="column is-4">
            <div class="field">
              <label class="label is-small">
                Name
                <span class="has-text-grey is-pulled-right document-id"
                      title="Profile id">
                  {{ localDoc.id }}
                </span>
              </label>
              <div class="control">
                <input class="input is-small document-name"
                       title="Profile name"
                       placeholder="Profile name"
                       @change="emitDocUpdate"
                       v-model="localDoc.name" />
              </div>
            </div>
            <div class="field">
              <label class="label is-small">Description</label>
              <div class="control">
                <textarea class="is-small textarea document-description"
                          title="Description"
                          @change="emitDocUpdate"
                          v-model="localDoc.description" />
              </div>
            </div>
          </div>
          <div class="column is-8">
            <div class="tile is-ancestor">
              <div class="tile is-vertical">
                <div class="tile">
                  <div class="tile is-parent is-vertical">
                    <table class="table is-narrow entries-table mb-0">
                      <tr
                        v-for="(ruleId, ruleIndex) in rateLimitsPage"
                        :key="ruleIndex"
                        class="entry-row"
                      >
                        <td class="is-size-7 has-text-weight-medium is-80">
                          <a :href="`/config/${selectedBranch}/ratelimits/${ruleId}`"
                             target="_blank">
                          {{ getLimitName(ruleId) }}
                          </a>
                        </td>
                        <td class="is-size-7 is-20">
                          <a tabindex="0"
                            class="is-small has-text-grey remove-limit-button"
                            title="remove limit"
                            @click="removeLimit(ruleIndex)">
                              remove
                          </a>
                        </td>
                      </tr>
                      <tr v-if="addLimitMode" class="new-limit-row">
                        <td class="is-size-7 is-80">
                          <div class="select is-small is-fullwidth">
                            <select
                              v-model="newLimit"
                              title="New limit"
                              class="select new-limit-selection"
                            >
                              <option v-for="({id, name}) in localRatelimits"
                                      :key="id"
                                      :value="id">
                                {{ name }}
                              </option>
                            </select>
                          </div>
                        </td>
                        <td class="is-size-7 is-20">
                          <a class="is-size-7 has-text-grey add-button confirm-add-limit-button"
                            title="add new limit"
                            tabindex="0"
                            @click="addLimit">
                              <i class="fas fa-check" /> Add
                          </a>
                          <br/>
                          <a class="is-size-7 has-text-grey remove-button cancel-limit-button"
                            title="cancel add new row"
                            tabindex="0"
                            @click="closeAddLimitMode">
                              <i class="fas fa-times" /> Cancel
                          </a>
                        </td>
                      </tr>
                      <tr v-if="localRatelimits.length && !addLimitMode">
                        <td colspan="2">
                          <a class="is-size-7 has-text-grey-lighter add-button add-limit-button"
                            title="add limit"
                            tabindex="0"
                            @click="addLimitMode = true">
                              <i class="fas fa-plus" />
                          </a>
                        </td>
                      </tr>
                      <tr v-if="totalPages > 1">
                        <td colspan="2">
                          <nav aria-label="pagination"
                               class="pagination is-small"
                               role="navigation">
                            <a :disabled="currentPage === 1"
                              class="is-pulled-left pagination-previous"
                              tabindex="0"
                              @click="navigate(currentPage - 1)">
                                Previous page
                            </a>
                            <a :disabled="currentPage === totalPages"
                              class="is-pulled-right pagination-next"
                              tabindex="0"
                              @click="navigate(currentPage + 1)">
                                Next page
                            </a>
                          </nav>
                        </td>
                      </tr>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import Vue from 'vue'
import {RateLimitsProfile, RateLimit} from '@/types'
import _ from 'lodash'
import {AxiosResponse} from 'axios'
import RequestsUtils from '@/assets/RequestsUtils'
export default Vue.extend({
  name: 'RateLimitsProfilesEditor',
  props: {
    selectedDoc: Object,
    selectedBranch: String,
  },
  data() {
    return {
      addLimitMode: false,
      newLimit: '',
      rateLimits: [] as RateLimit[],
      rowsPerPage: 20,
      currentPage: 1,
    }
  },
  computed: {
    localDoc(): RateLimitsProfile {
      return _.cloneDeep(this.selectedDoc)
    },
    localRatelimits(): RateLimit[] {
      return this.rateLimits.filter(({id}) => !this.localDoc.limit_ids.includes(id))
    },
    totalPages(): number {
      return Math.ceil(this.localDoc.limit_ids?.length / this.rowsPerPage)
    },
    rateLimitsPage(): RateLimitsProfile['limit_ids'] {
      const {localDoc, currentPage, rowsPerPage} = this
      const firstIndex = (currentPage-1) * rowsPerPage
      const lastIndex = firstIndex + rowsPerPage
      return localDoc.limit_ids?.slice(firstIndex, lastIndex)
    },
  },
  methods: {
    emitDocUpdate() {
      this.$emit('update:selectedDoc', this.localDoc)
    },
    getLimitName(ruleId: RateLimit['id']) {
      return this.rateLimits.find(({id}) => ruleId === id)?.name
    },
    removeLimit(ruleIndex: number) {
      this.localDoc.limit_ids.splice(ruleIndex, 1)
      this.emitDocUpdate()
    },
    addLimit() {
      if (this.newLimit) {
        this.localDoc.limit_ids.push(this.newLimit)
        this.emitDocUpdate()
        this.closeAddLimitMode()
        this.$nextTick(() => this.navigate(this.totalPages))
      }
    },
    closeAddLimitMode() {
      this.addLimitMode = false
      this.newLimit = ''
    },
    navigate(pageNum: number) {
      if (pageNum && pageNum <= this.totalPages) {
        this.currentPage = pageNum
      }
    },
  },
  async mounted() {
    const response: AxiosResponse = await RequestsUtils.sendRequest({
      methodName: 'GET',
      url: `configs/${this.selectedBranch}/d/ratelimits/`,
    })
    this.rateLimits = response?.data || []
  },
})
</script>
<style scoped lang="scss">
  .is-20 {
    text-align: right;
    width: 20%;
  }

  .is-80 {
    width: 80%;
  }
</style>
