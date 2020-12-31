<template>
  <div>
    <select name="region" v-model="selectedRegion">
      <option :value="null">World</option>
      <option v-for="region in regions" :key="region.iso" :value="region.iso">{{region.name}}</option>
    </select>
    <h1 v-if="errorMsg">
      {{errorMsg}}
    </h1>
    <template
      v-if="data && data.now && data.now.active && data.last && data.last.active"
    >
      <h1 v-if="difference >= 0">
        No end in sight
      </h1>
      <h1 else>
        <template v-if="endInWeeks < 0.01">
          The pandemic is over!
        </template>
        <template v-else-if="endInWeeks < 1">
          The pandemic will within a week!
        </template>
        <template v-else>
          The Pandemic will end in {{endInWeeks}} weeks.
        </template>
      </h1>
      <h2>
        {{ data.now.active.toLocaleString() }} Active Cases
      </h2>
      <h3>
        <template v-if="difference >= 0">+</template>{{ (difference).toLocaleString() }} active cases last week
      </h3>
      <div style="position: relative; margin: 0 auto; height:40vh; width:80vw">
        <canvas ref="chart" id="chart" width="400" height="400"></canvas>
      </div>
    </template>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import axios from 'axios'
import Chart from 'chart.js'
import regions from '@/assets/regions.json'

function baseLog (x, y) {
  return Math.log(y) / Math.log(x)
}

const endOn = 100

export default {
  name: 'App',
  components: {
  },
  setup (props) {
    const data = reactive({
      now: null,
      last: null
    })
    const selectedRegion = ref(window.location.hash.substr(1))
    const chart = ref(null)
    const endInWeeks = computed(() => {
      return Math.ceil(baseLog(rwk.value, endOn / data.now.active))
    })
    const rwk = computed(() => data.now.active / data.last.active)
    const errorMsg = ref(null)

    let reportUrl = 'https://covid-api.com/api/reports/total?'

    function updateReportUrl () {
      reportUrl = 'https://covid-api.com/api/reports/total?'
      if (selectedRegion.value && selectedRegion.value !== '') {
        reportUrl = `https://covid-api.com/api/reports?iso=${selectedRegion.value}`
      }
    }

    function extractData (resp) {
      if (resp.data.data.length === 0) {
        throw new Error('No data retrieved. Try again later.')
      } else if (!resp.data.data.length) {
        // single data point
        return resp.data.data
      } else {
        return resp.data.data.reduce((prev, curr) => {
          if (prev.active > curr.active) return prev
          else return curr
        }, resp.data.data[0])
      }
    }

    async function updateData () {
      const now = new Date()
      now.setDate(now.getDate() - 1)
      const dataNow = await axios
        .get(`${reportUrl}&date=${now.toISOString().split('T')[0]}`)
        .then(extractData)
        .catch(error => { errorMsg.value = error.message })
      data.now = dataNow

      const last = new Date(now)
      last.setDate(last.getDate() - 7)
      const dataLast = await axios
        .get(`${reportUrl}&date=${last.toISOString().split('T')[0]}`)
        .then(extractData)
        .catch(error => { errorMsg.value = error.message })
      data.last = dataLast
    }

    function updateGraph () {
      const cases = []
      const labels = []
      for (let i = 0; i < 26; i++) {
        if (i === 0) labels.push('Last week')
        else if (i === 1) labels.push('Now')
        else labels.push(`+ ${i - 1} weeks`)

        if (i === 0) cases.push(data.last.active)
        else if (i === 1) cases.push(data.now.active)
        else cases.push(cases[i - 1] * rwk.value)
      }

      const ctx = chart.value.getContext('2d')
      const chartObj = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Active Cases',
            backgroundColor: '#f00',
            data: cases,
            fill: true
          }]
        },
        options: {
          maintainAspectRatio: false
        }
      })
      chartObj.canvas.parentNode.style.height = '60vh'
    }

    watch(
      selectedRegion,
      async (region) => {
        if (selectedRegion.value) {
          window.location.hash = '#' + selectedRegion.value
        } else {
          window.location.hash = ''
        }
        updateReportUrl()
        await updateData()
        updateGraph()
      }
    )

    onMounted(async () => {
      updateReportUrl()
      await updateData()
      updateGraph()
    })

    const difference = computed(() => data.now.active - data.last.active)

    return {
      data,
      difference,
      rwk,
      chart,
      endInWeeks,
      selectedRegion,
      errorMsg,
      regions: regions.sort((a, b) => {
        if (a.name < b.name) return -1
        if (a.name > b.name) return 1
        return 0
      })
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
