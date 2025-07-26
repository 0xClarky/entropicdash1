<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import { API_URL } from './config'
import RugcheckDropdown from './components/RugcheckDropdown.vue'

const tokens = ref([])
const lastUpdate = ref(new Date())
const updateCount = ref(0)
const currentTime = ref(new Date())

const sortedTokens = computed(() => {
  return [...tokens.value].sort((a, b) => {
    // Sort by created_at date, newest first
    return new Date(b.created_at) - new Date(a.created_at)
  })
})

function formatNumber(num) {
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`
  return num.toFixed(0)
}

// Update the getTimeAgo function
function getTimeAgo(date) {
  let timeAgo = formatDistanceToNow(new Date(date), { addSuffix: true })
  
  // Make replacements in correct order
  return timeAgo
    .replace('less than a minute ago', '<1m')
    .replace('about ', '')
    .replace('less than ', '<')
    .replace(' minutes ago', 'm')
    .replace(' minute ago', 'm')
    .replace(' hours ago', 'h')
    .replace(' hour ago', 'h')
    .replace(' days ago', 'd')
    .replace(' day ago', 'd')
    .replace(' months ago', 'mo')
    .replace(' month ago', 'mo')
    .replace(' years ago', 'y')
    .replace(' year ago', 'y')
    .trim()
}

function getUpdateStatus() {
  const secondsAgo = Math.round((new Date() - lastUpdate.value) / 1000)
  if (secondsAgo < 60) {
    return `Updated ${secondsAgo} seconds ago`
  }
  return `Updated ${formatDistanceToNow(lastUpdate.value)} ago`
}

async function fetchTokens() {
  try {
    const response = await fetch(`${API_URL}/api/tokens`)
    const data = await response.json()
    console.log('API Response:', data)  // Debug logging
    if (data.tokens) {
      tokens.value = data.tokens
      lastUpdate.value = new Date()  // Update timestamp
      updateCount.value++
      console.log(`Refresh #${updateCount.value} completed`)
    }
  } catch (error) {
    console.error('Error fetching tokens:', error)
  }
}

function formatPercent(num) {
  if (!num) return '0.0%'
  return `${parseFloat(num).toFixed(1)}%`
}

function formatScore(num) {
  if (!num) return '0.0'
  return num.toFixed(1)
}

function getDexScreenerUrl(address) {
  return `https://gmgn.ai/sol/token/${address}?tag=sniper`
}

// Update the computed refreshStatus function:
const refreshStatus = computed(() => {
  const secondsAgo = Math.round((currentTime.value - lastUpdate.value) / 1000)
  if (secondsAgo < 60) {
    return `Updated ${secondsAgo} seconds ago`
  } else if (secondsAgo < 3600) {
    const minutes = Math.floor(secondsAgo / 60)
    return `Updated ${minutes} minute${minutes > 1 ? 's' : ''} ago`
  } else {
    const hours = Math.floor(secondsAgo / 3600)
    return `Updated ${hours} hour${hours > 1 ? 's' : ''} ago`
  }
})

const sessionActive = ref(true)
const sessionTogglePending = ref(false)

// Update the toggleSession function
async function toggleSession() {
  try {
    sessionTogglePending.value = true;
    const endpoint = `${API_URL}/api/session/${sessionActive.value ? 'stop' : 'start'}`;
    
    console.log(`Calling ${endpoint}`); // Debug log
    
    const response = await fetch(endpoint, { 
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Session toggle response:', data); // Debug log
    
    // Update the state based on the response
    sessionActive.value = data.active;
    console.log('New session state:', sessionActive.value); // Debug log
    
  } catch (error) {
    console.error('Error toggling session:', error);
  } finally {
    sessionTogglePending.value = false;
  }
}

// Update the checkSessionStatus function
async function checkSessionStatus() {
  try {
    const response = await fetch(`${API_URL}/api/session/status`);
    const data = await response.json();
    console.log('Session status response:', data); // Debug log
    sessionActive.value = data.active;
  } catch (error) {
    console.error('Error checking session status:', error);
  }
}

onMounted(() => {
  // Check initial session status
  checkSessionStatus()

  // Set up timer for current time
  setInterval(() => {
    currentTime.value = new Date()
  }, 1000)

  // Set up token fetch interval - only if session is active
  fetchTokens()
  setInterval(() => {
    if (sessionActive.value) {
      fetchTokens()
    }
  }, 10000)
})

// Add formatting function for entropy score
function formatEntropy(score) {
  if (!score && score !== 0) return '-'
  return score.toFixed(2)
}

// Add this function with your other functions in the <script setup> section
async function clearDatabase() {
  if (!confirm('Are you sure you want to clear all tokens from the database?')) {
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/api/database/clear`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Database clear response:', data);
    
    // Refresh the tokens list
    tokens.value = [];
    await fetchTokens();
    
  } catch (error) {
    console.error('Error clearing database:', error);
  }
}

// Add column visibility state
const visibleColumns = ref({
  name: true,
  address: true,
  fdv: true,
  liquidity: true,
  volume_24h: true,
  transactions_24h: true,
  gt_score: true,
  top_holder: true,
  top_20_holders: true,
  is_honeypot: true,
  authorities: true,
  age: true,
  entropy: true
})

// Add column definitions with labels
const columns = [
  { key: 'name', label: 'Name' },
  { key: 'address', label: 'Address' },
  { key: 'fdv', label: 'FDV' },
  { key: 'liquidity', label: 'Liquidity' },
  { key: 'volume_24h', label: '24h Volume' },
  { key: 'transactions_24h', label: '24h Txns' },
  { key: 'gt_score', label: 'Score' },
  { key: 'top_holder', label: 'Top Holder' },
  { key: 'top_20_holders', label: 'Top 20' },
  { key: 'is_honeypot', label: 'Honeypot' },
  { key: 'authorities', label: 'Auth' },
  { key: 'age', label: 'Age' },
  { key: 'entropy', label: 'Entropy' }
]

// Add toggle function
function toggleColumn(key) {
  visibleColumns.value[key] = !visibleColumns.value[key]
}

// Add these to your existing script setup
const expandedTokens = ref([])
const visibleColumnCount = computed(() => 
  Object.values(visibleColumns.value).filter(v => v).length
)

// Modify the toggleTokenDetails function
const rugcheckRefs = ref({})

const toggleTokenDetails = (address) => {
  const index = expandedTokens.value.indexOf(address)
  if (index === -1) {
    expandedTokens.value.push(address)
    nextTick(() => {
      if (rugcheckRefs.value[address]) {
        rugcheckRefs.value[address].fetchData()
      }
    })
  } else {
    expandedTokens.value.splice(index, 1)
  }
}

// Add this function after your existing functions
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    // Optional: You could add a toast notification here
    console.log('Copied to clipboard:', text);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}
</script>

<template>
  <div class="container">
    <header>
      <h1>Entropic Token Tracker</h1>
      <div class="status-container">
        <div class="status">
          {{ tokens.length }} tokens tracked • {{ refreshStatus }}
        </div>
        <div class="button-group">
          <button 
            @click="toggleSession" 
            :disabled="sessionTogglePending"
            :class="{ 
              'session-button': true,
              'active': sessionActive,
              'inactive': !sessionActive
            }"
          >
            {{ sessionActive ? 'Stop Tracking' : 'Start Tracking' }}
          </button>
          <button 
            @click="clearDatabase"
            class="clear-button"
          >
            Clear Database
          </button>
        </div>
      </div>
      <div class="column-toggles">
        <button 
          v-for="col in columns" 
          :key="col.key"
          @click="toggleColumn(col.key)"
          :class="{ 
            'toggle-button': true,
            'active': visibleColumns[col.key]
          }"
        >
          {{ col.label }}
        </button>
      </div>
    </header>
    
    <div class="table-wrapper">
      <table class="token-table">
        <thead>
          <tr>
            <th v-if="visibleColumns.name">Name</th>
            <th v-if="visibleColumns.address">Address</th>
            <th v-if="visibleColumns.fdv">FDV</th>
            <th v-if="visibleColumns.liquidity">Liquidity</th>
            <th v-if="visibleColumns.volume_24h">24h Volume</th>
            <th v-if="visibleColumns.transactions_24h">24h Txns</th>
            <th v-if="visibleColumns.gt_score">Score</th>
            <th v-if="visibleColumns.top_holder">Top Holder</th>
            <th v-if="visibleColumns.top_20_holders">Top 20</th>
            <th v-if="visibleColumns.is_honeypot">Honeypot</th>
            <th v-if="visibleColumns.authorities">Auth</th>
            <th v-if="visibleColumns.age">Age</th>
            <th v-if="visibleColumns.entropy">Entropy</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="token in sortedTokens" :key="token.address">
            <!-- Main row -->
            <tr 
              @click="toggleTokenDetails(token.mint_address)" 
              :class="{ 'expandable': true, 'expanded': expandedTokens.includes(token.mint_address) }"
            >
              <td v-if="visibleColumns.name" 
                  @click.stop="copyToClipboard(token.mint_address)" 
                  class="clickable-name" 
                  :title="'Click to copy address: ' + token.mint_address">
                {{ token.name }}
              </td>
              <td v-if="visibleColumns.address" class="address">
                <a :href="getDexScreenerUrl(token.address)" 
                   target="_blank" 
                   class="address-link"
                   :title="token.address">
                  GMGN Link
                </a>
              </td>
              <td v-if="visibleColumns.fdv">${{ formatNumber(token.fdv_usd) }}</td>
              <td v-if="visibleColumns.liquidity">${{ formatNumber(token.reserve_in_usd) }}</td>
              <td v-if="visibleColumns.volume_24h">${{ formatNumber(token.volume_24h) }}</td>
              <td v-if="visibleColumns.transactions_24h">{{ token.transactions_24h }}</td>
              <td v-if="visibleColumns.gt_score">{{ formatScore(token.gt_score) }}</td>
              <td v-if="visibleColumns.top_holder">{{ formatPercent(token.top_holder) }}</td>
              <td v-if="visibleColumns.top_20_holders">{{ formatPercent(token.top_20_holders) }}</td>
              <td v-if="visibleColumns.is_honeypot" :class="{ 'honeypot': token.is_honeypot }">
                {{ token.is_honeypot ? '⚠️' : '✓' }}
              </td>
              <td v-if="visibleColumns.authorities" class="auth-icons">
                <div class="auth-status">
                  <span class="auth-icon" :class="{ active: token.mint_authority }" 
                        :title="token.mint_authority ? 'Mint Authority: Detected' : 'Mint Authority: None'">
                    {{ token.mint_authority ? '⚠️' : '✓' }}
                  </span>
                  <span class="auth-icon" :class="{ active: token.freeze_authority }" 
                        :title="token.freeze_authority ? 'Freeze Authority: Detected' : 'Freeze Authority: None'">
                    {{ token.freeze_authority ? '⚠️' : '✓' }}
                  </span>
                </div>
              </td>
              <td v-if="visibleColumns.age">{{ getTimeAgo(token.created_at) }}</td>
              <td v-if="visibleColumns.entropy" :class="{ 'low-entropy': token.entropy_score < 2.5 }">
                {{ formatEntropy(token.entropy_score) }}
              </td>
            </tr>
            <transition name="expand">
              <tr v-if="expandedTokens.includes(token.mint_address)" class="details-row">
                <td :colspan="visibleColumnCount">
                  <RugcheckDropdown 
                    :token-address="token.mint_address"
                    :ref="(el) => { if (el) rugcheckRefs[token.mint_address] = el }"
                  />
                </td>
              </tr>
            </transition>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.container {
  width: 100%;
  min-height: 100vh;
  padding: 1rem;
  background: #1a1a1a;
  color: #fff;
}

header {
  margin-bottom: 2rem;
}

h1 {
  font-size: 2rem;
  text-align: center;
  margin-bottom: 1rem;
}

.status-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.button-group {
  display: flex;
  gap: 0.5rem;
}

.session-button, .clear-button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.session-button {
  background: #646cff;
  color: white;
}

.clear-button {
  background: #dc3545;
  color: white;
}

.column-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin-bottom: 1rem;
}

.toggle-button {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #444;
  background: #2a2a2a;
  color: #888;
  cursor: pointer;
}

.toggle-button.active {
  background: #3a3a3a;
  color: white;
  border-color: #646cff;
}

.table-wrapper {
  overflow-x: auto;
  background: #242424;
  border-radius: 8px;
  padding: 1rem;
}

.token-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th, td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid #333;
}

th {
  background: #1a1a1a;
  position: sticky;
  top: 0;
}

td a {
  color: #646cff;
  text-decoration: none;
}

@media (max-width: 768px) {
  .status-container {
    flex-direction: column;
  }
  
  .button-group {
    width: 100%;
  }
  
  .session-button, .clear-button {
    flex: 1;
  }
  
  .token-table {
    font-size: 0.8rem;
  }
}

/* Add these to your existing styles */
.expandable {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.expandable:hover {
  background-color: #2a2a2a;
}

.expanded {
  background-color: #2a2a2a;
}

.details-row {
  background-color: #1a1a1a;
}

.details-row > td {
  padding: 0;
}

/* Ensure the table maintains its structure */
.token-table {
  border-collapse: collapse;
}

tr {
  border-bottom: 1px solid #333;
}

/* Add these styles */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease-out;
  max-height: 300px;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Add new styles */
.clickable-name {
  cursor: pointer;
  position: relative;
}

.clickable-name:hover {
  color: #646cff;
  text-decoration: underline;
}

/* Optional: Add a subtle highlight effect */
.clickable-name:active {
  background-color: rgba(100, 108, 255, 0.1);
}
</style>
