<template>
  <div class="rugcheck-content">
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      Loading security data...
      <div v-if="error" class="retry-message">{{ error }}</div>
    </div>
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    <div v-else class="security-details">
      <div class="section risks">
        <h4>Risk Factors:</h4>
        <div v-if="data.risks && data.risks.length" class="risk-grid">
          <div v-for="risk in data.risks" 
               :key="risk.name" 
               class="risk-item" 
               :class="risk.level || 'warn'">
            <span class="risk-name">{{ risk.name || 'Unknown Risk' }}</span>
            <span v-if="risk.value" class="risk-value">{{ risk.value }}</span>
          </div>
        </div>
        <div v-else class="no-data">No risks detected</div>
      </div>

      <div class="section">
        <div class="info-grid">
          <div class="info-item">
            <h4>Creator Tokens</h4>
            <div>{{ data.creator_tokens?.length ? `${data.creator_tokens.length} found` : 'None found' }}</div>
          </div>
          <div class="info-item">
            <h4>Insider Activity</h4>
            <div v-if="data.insider_networks && data.insider_networks.length">
              <div v-for="(network, index) in data.insider_networks" 
                   :key="index" 
                   class="network-item">
                {{ network.type || 'Unknown' }}: {{ formatNumber(network.token_amount || 0) }} 
                ({{ (network.token_percentage || 0).toFixed(2) }}%) to {{ network.distributed_to || 0 }} wallets
              </div>
            </div>
            <div v-else class="no-data">No insider activity detected</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { API_URL } from '../config'

export default {
  name: 'RugcheckDropdown',
  props: {
    tokenAddress: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const loading = ref(true)
    const error = ref(null)
    const data = ref({
      risks: [],
      creator_tokens: [],
      insider_networks: []
    })
    const retryCount = ref(0)
    const maxRetries = 3

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

    const fetchData = async (isRetry = false) => {
      if (!isRetry) {
        loading.value = true
      }
      error.value = null

      try {
        const response = await fetch(`${API_URL}/api/tokens/${props.tokenAddress}/rugcheck`)
        
        // Handle non-200 responses
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`)
        }
        
        const result = await response.json()
        
        // Sanitize the response data
        data.value = {
          risks: result.risks || [],
          creator_tokens: result.creator_tokens || [],
          insider_networks: (result.insider_networks || []).map(network => ({
            type: network.type || 'Unknown',
            token_amount: network.token_amount || 0,
            token_percentage: network.token_percentage || 0,
            distributed_to: network.distributed_to || 0
          }))
        }
        
        loading.value = false
        error.value = null
        retryCount.value = 0
        
      } catch (e) {
        console.error(`Error fetching rugcheck data for ${props.tokenAddress}:`, e)
        
        // Implement exponential backoff for retries
        if (retryCount.value < maxRetries) {
          retryCount.value++
          const backoffTime = Math.min(1000 * Math.pow(2, retryCount.value), 10000)
          error.value = `Retrying in ${backoffTime/1000}s... (${retryCount.value}/${maxRetries})`
          
          await sleep(backoffTime)
          return fetchData(true)
        } else {
          error.value = 'Failed to fetch security data'
          loading.value = false
        }
      }
    }

    return {
      loading,
      error,
      data,
      fetchData,  // Make sure fetchData is exposed here
      formatNumber: (num) => new Intl.NumberFormat('en-US').format(num || 0)
    }
  }
}
</script>

<style scoped>
.rugcheck-dropdown {
  margin: 0.5rem 0;
}

.section {
  margin-bottom: 1rem;
}

.section h4 {
  margin: 0 0 0.5rem 0;
  color: #888;
}

.risk-item {
  padding: 0.25rem 0.5rem;
  margin: 0.25rem 0;
  border-radius: 4px;
}

.risk-item.danger {
  background: rgba(220, 53, 69, 0.2);
  color: #ff6b6b;
}

.risk-item.warn {
  background: rgba(255, 193, 7, 0.2);
  color: #ffd93d;
}

.network-item {
  background: #2a2a2a;
  padding: 0.5rem;
  margin: 0.5rem 0;
  border-radius: 4px;
  font-size: 0.9em;
}

.error {
  color: #ff6b6b;
  padding: 0.5rem;
}

.no-data {
  color: #888;
  font-style: italic;
}

.rugcheck-content {
  padding: 1rem;
  background: #1a1a1a;
}

.security-details {
  display: grid;
  gap: 1rem;
}

.section {
  padding: 0.5rem;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem;
}

.risk-item {
  padding: 0.5rem;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-item.danger {
  background: rgba(220, 53, 69, 0.2);
  color: #ff6b6b;
}

.risk-item.warn {
  background: rgba(255, 193, 7, 0.2);
  color: #ffd93d;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  background: #2a2a2a;
  padding: 1rem;
  border-radius: 4px;
}

.network-item {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #333;
  border-radius: 4px;
  font-size: 0.9em;
}

h4 {
  margin: 0 0 0.5rem 0;
  color: #888;
}

.loading, .error {
  padding: 1rem;
  text-align: center;
}

.error {
  color: #ff6b6b;
}

.no-data {
  color: #666;
  font-style: italic;
}

/* Add to existing styles */
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #646cff;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 1s linear infinite;
  margin: 0 auto;
  margin-bottom: 0.5rem;
}

.retry-message {
  color: #ffd700;
  margin-top: 0.5rem;
  font-size: 0.9em;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>