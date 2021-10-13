import RateLimitsProfilesEditor from '@/doc-editors/RateLimitsProfilesEditor.vue'
import {beforeEach, describe, expect, jest, test} from '@jest/globals'
import {shallowMount, Wrapper} from '@vue/test-utils'
import Vue from 'vue'
import {RateLimitsProfile, RateLimit} from '@/types'
import axios from 'axios'

jest.mock('axios')

describe('RateLimitsProfilesEditor.vue', () => {
  let ratelimits: RateLimit[]
  let wrapper: Wrapper<Vue>
  let selectedDoc: RateLimitsProfile
  const ALL_RATELIMITS_NUMBER = 30
  const DOC_RATELIMITS_NUMBER = 25
  const ratelimitExample: RateLimit = {
    'id': '1000',
    'name': '1000',
    'description': 'test',
    'ttl': '60',
    'limit': '5',
    'action': {'type': 'default', 'params': {'action': {'type': 'default', 'params': {}}}},
    'include': ['blocklist'],
    'exclude': ['allowlist'],
    'key': [{'attrs': 'ip'}],
    'pairwith': {'self': 'self'},
  }
  const selectedBranch = 'master'
  beforeEach(() => {
    ratelimits = [...Array(ALL_RATELIMITS_NUMBER)].map((_d, index) => ({
      ...ratelimitExample,
      id: `${parseInt(ratelimitExample['id']) + index}`,
      name: `${parseInt(ratelimitExample['id']) + index}`,
    }))
    selectedDoc = {
      id: '1',
      name: 'test profile',
      description: 'the testing',
      limit_ids: ratelimits.slice(0, DOC_RATELIMITS_NUMBER).map(({id}: RateLimit) => id),
    }
    jest.spyOn(axios, 'get').mockImplementation((path) => {
      if (path === `/conf/api/v2/configs/${selectedBranch}/d/ratelimits/`) {
        return Promise.resolve({data: ratelimits})
      }
      return Promise.resolve({data: []})
    })
    const onUpdate = (selectedDoc: RateLimitsProfile) => {
      wrapper.setProps({selectedDoc})
    }
    wrapper = shallowMount(RateLimitsProfilesEditor, {
      propsData: {
        selectedDoc,
        selectedBranch,
      },
      listeners: {
        'update:selectedDoc': onUpdate,
      },
    })
  })

  test('should not crush if getting ratelimits from server failed', () => {
    jest.spyOn(axios, 'get').mockImplementation(() => Promise.resolve({data: undefined}))
    wrapper = shallowMount(RateLimitsProfilesEditor, {
      propsData: {
        selectedDoc,
        selectedBranch,
      },
    })
    expect((wrapper.vm as any).rateLimits).toEqual([])
    jest.clearAllMocks()
  })

  test('should have an entries list table rendered', () => {
    const tables = wrapper.findAll('.entries-table')
    expect(tables.length).toEqual(1)
    expect(tables.at(0).findAll('.entry-row').length).toEqual((wrapper.vm as any).rowsPerPage)
  })

  test('should have only unattached rate limits in the list of limits to add to the profile', async () => {
    const table = wrapper.find('.entries-table')
    const addBtn = table.find('.add-limit-button')
    addBtn.trigger('click')
    await Vue.nextTick()
    const limitSelect = table.find('.new-limit-selection')
    expect(limitSelect.findAll('option').length).toEqual(ALL_RATELIMITS_NUMBER - DOC_RATELIMITS_NUMBER)
  })

  test('should emit doc update when adding limit', async () => {
    const table = wrapper.find('.entries-table')
    const addBtn = table.find('.add-limit-button')
    addBtn.trigger('click')
    await Vue.nextTick()
    const limitSelectOptions = table.find('.new-limit-selection').findAll('option')
    limitSelectOptions.at(0).setSelected()
    await Vue.nextTick()
    table.find('.confirm-add-limit-button').trigger('click')
    await Vue.nextTick()
    expect(wrapper.emitted('update:selectedDoc')).toBeTruthy()
    expect(wrapper.emitted('update:selectedDoc')[0]).toEqual([{
      ...selectedDoc,
      limit_ids: [
        ...selectedDoc.limit_ids,
        ratelimits[DOC_RATELIMITS_NUMBER].id,
      ],
    }])
  })

  test('should not call adding function if no limit selected', async () => {
    const table = wrapper.find('.entries-table')
    const addBtn = table.find('.add-limit-button')
    addBtn.trigger('click')
    await Vue.nextTick()
    table.find('.confirm-add-limit-button').trigger('click')
    await Vue.nextTick()
    expect(wrapper.emitted('update:selectedDoc')).toBeFalsy()
  })

  test('should emit doc update when deleting limit', async () => {
    const table = wrapper.find('.entries-table')
    const removeBtns = table.findAll('.remove-limit-button')
    const indexToDelete = 10
    removeBtns.at(indexToDelete).trigger('click')
    await Vue.nextTick()
    expect(wrapper.emitted('update:selectedDoc')).toBeTruthy()
    expect(wrapper.emitted('update:selectedDoc')[0]).toEqual([{
      ...selectedDoc,
      limit_ids: selectedDoc.limit_ids.filter((id, index) => index !== indexToDelete),
    }])
  })

  test('should not navigate by paginator if current page is out of range (1, totalPages)', async () => {
    const vm = wrapper.vm as any
    const {currentPage} = vm
    vm.navigate(0)
    await Vue.nextTick()
    expect(vm.currentPage).toEqual(currentPage)
    vm.navigate(1000)
    await Vue.nextTick()
    expect(vm.currentPage).toEqual(currentPage)
    vm.navigate(2)
    await Vue.nextTick()
    expect(vm.currentPage).toEqual(2)
  })
})
