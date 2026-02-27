import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import axios from 'axios'

function App() {
  const [clusters, setClusters] = useState([])
  const [selectedCluster, setSelectedCluster] = useState('')
  const [nodes, setNodes] = useState([])
  const [clusterSummary, setClusterSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedPod, setExpandedPod] = useState(null)

  const [filterLabelKey, setFilterLabelKey] = useState('')
  const [filterLabelValue, setFilterLabelValue] = useState('')

  // Workload view states
  const [activeView, setActiveView] = useState('nodes')
  const [workloadMode, setWorkloadMode] = useState('owner')
  const [selectedOwners, setSelectedOwners] = useState([])
  const [ownerQuery, setOwnerQuery] = useState('')
  const [ownerOpen, setOwnerOpen] = useState(false)
  const ownerPickerRef = useRef(null)
  const ownerInputRef = useRef(null)
  const [wlLabelKey, setWlLabelKey] = useState('')
  const [wlLabelValue, setWlLabelValue] = useState('')
  const [expandedWlNode, setExpandedWlNode] = useState(null)
  const [wlGroupBy, setWlGroupBy] = useState('node')

  // Fetch cluster list on mount, then set active cluster
  useEffect(() => {
    axios.get('/api/clusters').then(res => {
      setClusters(res.data)
      const active = res.data.find(c => c.is_active)
      if (active) setSelectedCluster(active.name)
      else if (res.data.length > 0) setSelectedCluster(res.data[0].name)
    }).catch(() => {
      // Fallback: no multi-cluster support, use default endpoints
      setSelectedCluster('__default__')
    })
  }, [])

  const fetchData = useCallback(async () => {
    if (!selectedCluster) return
    try {
      if (selectedCluster === '__all__') {
        const clusterNames = clusters.map(c => c.name)
        const results = await Promise.all(
          clusterNames.map(name =>
            Promise.all([
              axios.get(`/api/clusters/${encodeURIComponent(name)}/nodes`),
              axios.get(`/api/clusters/${encodeURIComponent(name)}/summary`)
            ])
          )
        )
        const allNodes = []
        const allSummaries = []
        results.forEach(([nodesRes, summaryRes], i) => {
          nodesRes.data.forEach(node => {
            allNodes.push({ ...node, _clusterName: clusterNames[i] })
          })
          allSummaries.push(summaryRes.data)
        })
        setNodes(allNodes)
        setClusterSummary(aggregateSummaries(allSummaries))
      } else {
        const basePath = selectedCluster === '__default__'
          ? '/api'
          : `/api/clusters/${encodeURIComponent(selectedCluster)}`
        const [nodesRes, summaryRes] = await Promise.all([
          axios.get(`${basePath}/nodes`),
          axios.get(`${basePath}/summary`)
        ])
        setNodes(nodesRes.data)
        setClusterSummary(summaryRes.data)
      }
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedCluster, clusters])

  // Fetch data when selectedCluster changes + auto-refresh
  useEffect(() => {
    if (!selectedCluster) return
    setLoading(true)
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [selectedCluster, fetchData])

  const allPodLabelKeys = useMemo(() => {
    const keys = new Set()
    nodes.forEach(n => n.pods.forEach(p => {
      Object.keys(p.labels || {}).forEach(k => keys.add(k))
    }))
    return Array.from(keys).sort()
  }, [nodes])

  const valuesForKey = useMemo(() => {
    if (!filterLabelKey) return []
    const vals = new Set()
    nodes.forEach(n => n.pods.forEach(p => {
      const v = (p.labels || {})[filterLabelKey]
      if (v !== undefined) vals.add(v)
    }))
    return Array.from(vals).sort()
  }, [nodes, filterLabelKey])

  const hasActiveFilter = filterLabelKey && filterLabelValue

  const filteredNodes = useMemo(() => {
    if (!hasActiveFilter) return nodes
    return nodes.map(n => ({
      ...n,
      pods: n.pods.filter(p => (p.labels || {})[filterLabelKey] === filterLabelValue)
    })).filter(n => n.pods.length > 0)
  }, [nodes, filterLabelKey, filterLabelValue, hasActiveFilter])

  const displayNodes = filteredNodes
  const totalGpuUsed = displayNodes.reduce((s, n) => s + n.pods.reduce((ps, p) => ps + p.gpu_request, 0), 0)
  const totalGpuAvail = displayNodes.reduce((s, n) => s + n.gpu_allocatable, 0)
  const totalPods = displayNodes.reduce((s, n) => s + n.pods.length, 0)
  const gpuPods = displayNodes.reduce((s, n) => s + n.pods.filter(p => p.gpu_request > 0).length, 0)

  // Workload computed values
  const allOwners = useMemo(() => {
    const map = {}
    nodes.forEach(n => n.pods.forEach(p => {
      const key = `${p.owner_kind}/${p.owner_name}`
      if (!map[key]) map[key] = { kind: p.owner_kind, name: p.owner_name, count: 0 }
      map[key].count++
    }))
    return Object.values(map).sort((a, b) => a.name.localeCompare(b.name))
  }, [nodes])

  const selectedOwnerSet = useMemo(() => new Set(selectedOwners), [selectedOwners])

  const ownersWithKey = useMemo(() => {
    return allOwners.map(o => {
      const key = `${o.kind}/${o.name}`
      return { ...o, key, _search: key.toLowerCase() }
    })
  }, [allOwners])

  const filteredOwners = useMemo(() => {
    const q = ownerQuery.trim().toLowerCase()
    if (!q) return ownersWithKey
    return ownersWithKey.filter(o =>
      o._search.includes(q) ||
      o.name.toLowerCase().includes(q) ||
      o.kind.toLowerCase().includes(q)
    )
  }, [ownersWithKey, ownerQuery])

  const toggleOwner = useCallback((key) => {
    setSelectedOwners(prev => (
      prev.includes(key) ? prev.filter(x => x !== key) : [...prev, key]
    ))
  }, [])

  const selectAllVisibleOwners = useCallback(() => {
    const keys = filteredOwners.map(o => o.key)
    setSelectedOwners(prev => {
      const set = new Set(prev)
      const next = [...prev]
      keys.forEach(k => { if (!set.has(k)) { set.add(k); next.push(k) } })
      return next
    })
  }, [filteredOwners])

  const deselectAllVisibleOwners = useCallback(() => {
    const q = ownerQuery.trim()
    if (!q) { setSelectedOwners([]); return }
    const removeSet = new Set(filteredOwners.map(o => o.key))
    setSelectedOwners(prev => prev.filter(k => !removeSet.has(k)))
  }, [filteredOwners, ownerQuery])

  useEffect(() => {
    if (!ownerOpen) { setOwnerQuery(''); return }
    const onMouseDown = (e) => {
      if (ownerPickerRef.current && !ownerPickerRef.current.contains(e.target)) setOwnerOpen(false)
    }
    const onKeyDown = (e) => {
      if (e.key === 'Escape') { setOwnerOpen(false); ownerInputRef.current?.blur?.() }
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [ownerOpen])

  const wlLabelKeys = useMemo(() => {
    const keys = new Set()
    nodes.forEach(n => n.pods.forEach(p => {
      Object.keys(p.labels || {}).forEach(k => keys.add(k))
    }))
    return Array.from(keys).sort()
  }, [nodes])

  const wlValuesForKey = useMemo(() => {
    if (!wlLabelKey) return []
    const vals = new Set()
    nodes.forEach(n => n.pods.forEach(p => {
      const v = (p.labels || {})[wlLabelKey]
      if (v !== undefined) vals.add(v)
    }))
    return Array.from(vals).sort()
  }, [nodes, wlLabelKey])

  const workloadPods = useMemo(() => {
    const result = []
    nodes.forEach(n => {
      n.pods.forEach(p => {
        let match = false
        if (workloadMode === 'owner') {
          if (selectedOwners.length === 0) return
          const key = `${p.owner_kind}/${p.owner_name}`
          match = selectedOwners.includes(key)
        } else {
          if (!wlLabelKey || !wlLabelValue) return
          match = (p.labels || {})[wlLabelKey] === wlLabelValue
        }
        if (match) {
          result.push({
            pod: p,
            nodeName: n.name,
            clusterName: n._clusterName || '',
            nodeReady: n.conditions_ready,
          })
        }
      })
    })
    return result
  }, [nodes, workloadMode, selectedOwners, wlLabelKey, wlLabelValue])

  const workloadByNode = useMemo(() => {
    const map = {}
    workloadPods.forEach(({ pod, nodeName, clusterName, nodeReady }) => {
      if (!map[nodeName]) map[nodeName] = { nodeName, clusterName, ready: nodeReady, pods: [], gpu: 0, cpuMillis: 0, memBytes: 0 }
      map[nodeName].pods.push(pod)
      map[nodeName].gpu += pod.gpu_request || 0
      map[nodeName].cpuMillis += pod.cpu_request_millicores || 0
      map[nodeName].memBytes += pod.memory_request_bytes || 0
    })
    return Object.values(map).sort((a, b) => a.nodeName.localeCompare(b.nodeName))
  }, [workloadPods])

  const workloadByOwner = useMemo(() => {
    const map = {}
    workloadPods.forEach(({ pod, nodeName, clusterName, nodeReady }) => {
      const key = `${pod.owner_kind}/${pod.owner_name}`
      if (!map[key]) map[key] = { ownerKey: key, kind: pod.owner_kind, name: pod.owner_name, pods: [], gpu: 0, cpuMillis: 0, memBytes: 0, nodeSet: new Set() }
      map[key].pods.push({ pod, nodeName, clusterName, nodeReady })
      map[key].gpu += pod.gpu_request || 0
      map[key].cpuMillis += pod.cpu_request_millicores || 0
      map[key].memBytes += pod.memory_request_bytes || 0
      map[key].nodeSet.add(nodeName)
    })
    return Object.values(map)
      .map(row => ({ ...row, nodeCount: row.nodeSet.size }))
      .sort((a, b) => a.ownerKey.localeCompare(b.ownerKey))
  }, [workloadPods])

  const workloadTotals = useMemo(() => ({
    pods: workloadPods.length,
    gpu: workloadPods.reduce((s, { pod }) => s + (pod.gpu_request || 0), 0),
    cpuMillis: workloadPods.reduce((s, { pod }) => s + (pod.cpu_request_millicores || 0), 0),
    memBytes: workloadPods.reduce((s, { pod }) => s + (pod.memory_request_bytes || 0), 0),
    nodes: workloadByNode.length,
  }), [workloadPods, workloadByNode])

  const hasWorkloadFilter = workloadMode === 'owner' ? selectedOwners.length > 0 : (wlLabelKey && wlLabelValue)

  if (loading) return <div className="center">Loading...</div>
  if (error) return <div className="center error">Error: {error}</div>

  return (
    <div className="dashboard">
      <header>
        <div className="header-left">
          <h1>K8s GPU Dashboard</h1>
          {clusters.length > 1 && (
            <div className="cluster-selector">
              <select
                value={selectedCluster}
                onChange={(e) => {
                  setSelectedCluster(e.target.value)
                  setExpandedPod(null)
                  setFilterLabelKey('')
                  setFilterLabelValue('')
                }}
              >
                <option value="__all__">All Clusters</option>
                {clusters.map(c => (
                  <option key={c.name} value={c.name}>{c.name}{c.is_active ? ' (active)' : ''}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="summary">
          <span className="chip">{displayNodes.length} Nodes</span>
          <span className="chip">{totalPods} Pods</span>
          <span className="chip gpu">{totalGpuUsed} / {totalGpuAvail} GPUs</span>
          {gpuPods > 0 && <span className="chip gpu">{gpuPods} GPU Pods</span>}
        </div>
      </header>

      <div className="view-tabs">
        <button
          className={`view-tab ${activeView === 'nodes' ? 'active' : ''}`}
          onClick={() => setActiveView('nodes')}
        >Nodes</button>
        <button
          className={`view-tab ${activeView === 'workloads' ? 'active' : ''}`}
          onClick={() => setActiveView('workloads')}
        >Workloads</button>
      </div>

      {activeView === 'nodes' && (<>{clusterSummary && (
        <div className="cluster-overview">
          <div className="cluster-card">
            <div className="cluster-card-header">
              <span className="cluster-card-label">CPU</span>
              <span className="cluster-card-pct">{clusterSummary.cpu.utilization_percent}%</span>
            </div>
            <div className="cluster-card-value">{clusterSummary.cpu.used_display} <span className="cluster-card-total">/ {clusterSummary.cpu.total_display}</span></div>
            <div className="cluster-bar"><div className="cluster-bar-fill cpu" style={{ width: `${clusterSummary.cpu.utilization_percent}%` }} /></div>
            <div className="cluster-card-meta"><span>{clusterSummary.cpu.available_display} available</span></div>
          </div>
          <div className="cluster-card">
            <div className="cluster-card-header">
              <span className="cluster-card-label">Memory</span>
              <span className="cluster-card-pct">{clusterSummary.memory.utilization_percent}%</span>
            </div>
            <div className="cluster-card-value">{clusterSummary.memory.used_display} <span className="cluster-card-total">/ {clusterSummary.memory.total_display}</span></div>
            <div className="cluster-bar"><div className="cluster-bar-fill memory" style={{ width: `${clusterSummary.memory.utilization_percent}%` }} /></div>
            <div className="cluster-card-meta"><span>{clusterSummary.memory.available_display} available</span></div>
          </div>
          <div className="cluster-card">
            <div className="cluster-card-header">
              <span className="cluster-card-label">GPU</span>
              <span className="cluster-card-pct">{clusterSummary.gpu.utilization_percent}%</span>
            </div>
            <div className="cluster-card-value">{clusterSummary.gpu.used_display} <span className="cluster-card-total">/ {clusterSummary.gpu.total_display}</span></div>
            <div className="cluster-bar"><div className="cluster-bar-fill gpu" style={{ width: `${clusterSummary.gpu.utilization_percent}%` }} /></div>
            <div className="cluster-card-meta"><span>{clusterSummary.gpu.available_display} available</span></div>
          </div>
          <div className="cluster-card">
            <div className="cluster-card-header">
              <span className="cluster-card-label">Cluster</span>
              <span className="cluster-card-pct">{clusterSummary.ready_node_count}/{clusterSummary.node_count}</span>
            </div>
            <div className="cluster-card-value">{clusterSummary.pods.total} <span className="cluster-card-total">pods</span></div>
            <div className="cluster-bar"><div className="cluster-bar-fill nodes" style={{ width: clusterSummary.node_count > 0 ? `${(clusterSummary.ready_node_count / clusterSummary.node_count) * 100}%` : '0%' }} /></div>
            <div className="cluster-card-meta"><span>{clusterSummary.ready_node_count} nodes ready</span></div>
          </div>
        </div>
      )}

      {clusterSummary && clusterSummary.gpu_by_type && clusterSummary.gpu_by_type.length > 0 && (
        <div className="gpu-type-breakdown">
          <div className="gpu-type-header">GPU by Type</div>
          <div className="gpu-type-list">
            {clusterSummary.gpu_by_type.map(g => (
              <div key={g.gpu_type} className="gpu-type-row">
                <div className="gpu-type-name">{g.gpu_type}</div>
                <div className="gpu-type-bar-wrap">
                  <div className="cluster-bar"><div className="cluster-bar-fill gpu" style={{ width: `${g.utilization_percent}%` }} /></div>
                </div>
                <div className="gpu-type-stats">
                  <span className="gpu-type-usage">{g.used} <span className="gpu-type-dim">/ {g.total}</span></span>
                  <span className="gpu-type-pct">{g.utilization_percent}%</span>
                </div>
                <div className="gpu-type-meta">{g.node_count} {g.node_count === 1 ? 'node' : 'nodes'}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="filter-bar">
        <span className="filter-label">Filter by Pod Label</span>
        <select
          value={filterLabelKey}
          onChange={(e) => { setFilterLabelKey(e.target.value); setFilterLabelValue('') }}
        >
          <option value="">Key</option>
          {allPodLabelKeys.map(k => <option key={k} value={k}>{k}</option>)}
        </select>
        <select
          value={filterLabelValue}
          onChange={(e) => setFilterLabelValue(e.target.value)}
          disabled={!filterLabelKey}
        >
          <option value="">Value</option>
          {valuesForKey.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        {hasActiveFilter && (
          <button className="filter-clear" onClick={() => { setFilterLabelKey(''); setFilterLabelValue('') }}>
            Clear
          </button>
        )}
        {hasActiveFilter && (
          <span className="filter-active">{filterLabelKey}={filterLabelValue}</span>
        )}
      </div>

      <div className="nodes">
        {displayNodes.map(node => (
          <section key={node._clusterName ? `${node._clusterName}/${node.name}` : node.name} className="node">
            <div className="node-head">
              <div className="node-title">
                <span className={`ready-dot ${node.conditions_ready ? 'ok' : 'bad'}`} />
                <h2>{node.name}</h2>
              </div>
              <div className="node-meta">
                {node._clusterName && <span className="tag cluster-badge">{node._clusterName}</span>}
                <span className="tag gpu-type">{node.gpu_type}</span>
                <span className="tag">{node.arch}</span>
                <span className="tag">{node.kubelet_version}</span>
              </div>
              <div className="node-resources">
                <div className="resource-bar-group">
                  <div className="resource-bar-label">
                    <span>CPU</span>
                    <span>{(node.cpu_used_millicores / 1000).toFixed(1)} / {(node.cpu_allocatable_millicores / 1000).toFixed(1)} cores</span>
                  </div>
                  <div className="resource-bar">
                    <div 
                      className="resource-bar-fill cpu"
                      style={{ width: node.cpu_allocatable_millicores > 0 ? `${(node.cpu_used_millicores / node.cpu_allocatable_millicores) * 100}%` : '0%' }}
                    />
                  </div>
                </div>
                <div className="resource-bar-group">
                  <div className="resource-bar-label">
                    <span>Memory</span>
                    <span>{formatBytes(node.memory_used_bytes)} / {formatBytes(node.memory_allocatable_bytes)}</span>
                  </div>
                  <div className="resource-bar">
                    <div 
                      className="resource-bar-fill memory"
                      style={{ width: node.memory_allocatable_bytes > 0 ? `${(node.memory_used_bytes / node.memory_allocatable_bytes) * 100}%` : '0%' }}
                    />
                  </div>
                </div>
                <div className="gpu-bar-wrap">
                  <div className="gpu-bar-label">
                    <span>GPU</span>
                    <span>{node.gpu_used} / {node.gpu_allocatable}</span>
                  </div>
                  <div className="gpu-bar">
                    <div
                      className="gpu-bar-fill"
                      style={{ width: node.gpu_allocatable > 0 ? `${(node.gpu_used / node.gpu_allocatable) * 100}%` : '0%' }}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="pod-list">
              <div className="pod-list-header">
                <span className="col-status">Status</span>
                <span className="col-name">Pod</span>
                <span className="col-ns">Namespace</span>
                <span className="col-kind">Kind</span>
                <span className="col-gpu">GPU</span>
                <span className="col-containers">Containers</span>
              </div>

              {node.pods.map(pod => {
                const podKey = `${node._clusterName || ''}/${pod.namespace}/${pod.name}`
                const isExpanded = expandedPod === podKey
                const totalRestarts = pod.containers.reduce((s, c) => s + c.restart_count, 0)

                return (
                  <div key={podKey}>
                    <div
                      className={`pod-row ${pod.gpu_request > 0 ? 'has-gpu' : ''} ${isExpanded ? 'expanded' : ''}`}
                      onClick={() => setExpandedPod(isExpanded ? null : podKey)}
                    >
                      <span className="col-status">
                        <span className={`phase ${pod.phase.toLowerCase()}`}>{pod.phase}</span>
                      </span>
                      <span className="col-name" title={pod.name}>
                        <span className="pod-name-text">{pod.name}</span>
                      </span>
                      <span className="col-ns">{pod.namespace}</span>
                      <span className="col-kind">
                        <span className={`kind ${pod.owner_kind.toLowerCase()}`}>{pod.owner_kind}</span>
                      </span>
                      <span className="col-gpu">
                        {pod.gpu_request > 0 ? <span className="gpu-count">{pod.gpu_request}</span> : <span className="no-gpu">-</span>}
                      </span>
                      <span className="col-containers">
                        {pod.containers.map((c, i) => (
                          <span key={i} className={`c-dot ${c.ready ? 'ready' : 'not-ready'}`} title={`${c.name}: ${c.state}${c.reason ? ` (${c.reason})` : ''}`} />
                        ))}
                        {totalRestarts > 0 && <span className="restarts">{totalRestarts}R</span>}
                      </span>
                    </div>

                    {isExpanded && (
                      <div className="pod-detail">
                        <div className="detail-grid">
                          <div className="detail-item">
                            <span className="detail-label">Owner</span>
                            <span className="detail-value">{pod.owner_kind}/{pod.owner_name}</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">IP</span>
                            <span className="detail-value">{pod.ip || 'N/A'}</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">QoS</span>
                            <span className="detail-value">{pod.qos_class || 'N/A'}</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">GPU Req / Limit</span>
                            <span className="detail-value">{pod.gpu_request} / {pod.gpu_limit}</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">CPU Req / Limit</span>
                            <span className="detail-value">{(pod.cpu_request_millicores / 1000).toFixed(1)} / {(pod.cpu_limit_millicores / 1000).toFixed(1)} cores</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Memory Req / Limit</span>
                            <span className="detail-value">{formatBytes(pod.memory_request_bytes)} / {formatBytes(pod.memory_limit_bytes)}</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Created</span>
                            <span className="detail-value">{pod.created_at ? new Date(pod.created_at).toLocaleString() : 'N/A'}</span>
                          </div>
                        </div>

                        {Object.keys(pod.labels || {}).length > 0 && (
                          <div className="pod-labels">
                            <h4>Labels</h4>
                            <div className="label-list">
                              {Object.entries(pod.labels).map(([k, v]) => (
                                <span
                                  key={k}
                                  className={`label-chip ${hasActiveFilter && k === filterLabelKey && v === filterLabelValue ? 'active' : ''}`}
                                  onClick={(e) => { e.stopPropagation(); setFilterLabelKey(k); setFilterLabelValue(v) }}
                                  title={`${k}=${v} (click to filter)`}
                                >
                                  {k.split('/').pop()}={v}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="containers-detail">
                          <h4>Containers</h4>
                          {pod.containers.map((c, i) => (
                            <div key={i} className="container-row">
                              <span className={`c-state ${c.state}`}>{c.state}</span>
                              <span className="c-name">{c.name}</span>
                              <span className="c-image">{c.image}</span>
                              <span className={`c-ready ${c.ready ? 'yes' : 'no'}`}>{c.ready ? 'Ready' : 'Not Ready'}</span>
                              <span className="c-restarts">{c.restart_count} restarts</span>
                              {c.reason && <span className="c-reason">{c.reason}</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}

              {node.pods.length === 0 && (
                <div className="empty">No pods scheduled on this node</div>
              )}
            </div>
          </section>
        ))}

        {displayNodes.length === 0 && hasActiveFilter && (
          <div className="empty">No pods match label {filterLabelKey}={filterLabelValue}</div>
        )}
      </div></>)}

      {activeView === 'workloads' && (
        <div className="workload-view">
          <div className="wl-filter">
            <div className="wl-mode-toggle">
              <button
                className={`wl-mode-btn ${workloadMode === 'owner' ? 'active' : ''}`}
                onClick={() => { setWorkloadMode('owner'); setWlLabelKey(''); setWlLabelValue('') }}
              >By Owner</button>
              <button
                className={`wl-mode-btn ${workloadMode === 'label' ? 'active' : ''}`}
                onClick={() => { setWorkloadMode('label'); setSelectedOwners([]) }}
              >By Label</button>
            </div>

            {workloadMode === 'owner' && (
              <div className="wl-owner-ms" ref={ownerPickerRef}>
                <div className={`wl-owner-control ${ownerOpen ? 'open' : ''}`} onClick={() => { if (!ownerOpen) { setOwnerOpen(true); ownerInputRef.current?.focus() } }}>
                  <input
                    ref={ownerInputRef}
                    className="wl-owner-input"
                    value={ownerQuery}
                    onChange={(e) => { setOwnerQuery(e.target.value); if (!ownerOpen) setOwnerOpen(true) }}
                    onFocus={() => setOwnerOpen(true)}
                    placeholder={selectedOwners.length ? `${selectedOwners.length} selected -- type to filter...` : 'Search owners...'}
                  />
                  <span className="wl-owner-caret">{ownerOpen ? '\u25B2' : '\u25BC'}</span>
                </div>

                {ownerOpen && (
                  <div className="wl-owner-panel">
                    <div className="wl-owner-panel-head">
                      <span className="wl-owner-match">{filteredOwners.length} of {ownersWithKey.length} owners</span>
                      <div className="wl-owner-panel-actions">
                        <button type="button" className="wl-owner-action" onMouseDown={(e) => e.preventDefault()} onClick={selectAllVisibleOwners}>Select All</button>
                        <button type="button" className="wl-owner-action" onMouseDown={(e) => e.preventDefault()} onClick={deselectAllVisibleOwners}>Deselect All</button>
                      </div>
                    </div>
                    <div className="wl-owner-list">
                      {filteredOwners.length === 0 ? (
                        <div className="wl-owner-empty">No matching owners</div>
                      ) : (
                        filteredOwners.map(o => (
                          <label key={o.key} className={`wl-owner-item ${selectedOwnerSet.has(o.key) ? 'selected' : ''}`} onMouseDown={(e) => e.preventDefault()}>
                            <input type="checkbox" checked={selectedOwnerSet.has(o.key)} onChange={() => toggleOwner(o.key)} />
                            <span className="wl-owner-kind">{o.kind}</span>
                            <span className="wl-owner-name" title={o.name}>{o.name}</span>
                            <span className="wl-owner-count">{o.count} pods</span>
                          </label>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {workloadMode === 'label' && (
              <>
                <select
                  value={wlLabelKey}
                  onChange={(e) => { setWlLabelKey(e.target.value); setWlLabelValue('') }}
                >
                  <option value="">Key</option>
                  {wlLabelKeys.map(k => <option key={k} value={k}>{k}</option>)}
                </select>
                <select
                  value={wlLabelValue}
                  onChange={(e) => setWlLabelValue(e.target.value)}
                  disabled={!wlLabelKey}
                >
                  <option value="">Value</option>
                  {wlValuesForKey.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </>
            )}
          </div>

          {workloadMode === 'owner' && selectedOwners.length > 0 && (
            <div className="wl-selected">
              {selectedOwners.map(o => (
                <span key={o} className="wl-chip">
                  {o}
                  <button onClick={() => setSelectedOwners(selectedOwners.filter(x => x !== o))}>x</button>
                </span>
              ))}
              <button className="filter-clear" onClick={() => setSelectedOwners([])}>Clear All</button>
            </div>
          )}

          {hasWorkloadFilter && workloadPods.length > 0 && (
            <div className="wl-summary">
              <div className="wl-stat">
                <span className="wl-stat-value">{workloadTotals.pods}</span>
                <span className="wl-stat-label">Pods</span>
              </div>
              <div className="wl-stat">
                <span className="wl-stat-value">{workloadTotals.nodes}</span>
                <span className="wl-stat-label">Nodes</span>
              </div>
              <div className="wl-stat gpu">
                <span className="wl-stat-value">{workloadTotals.gpu}</span>
                <span className="wl-stat-label">GPUs</span>
              </div>
              <div className="wl-stat">
                <span className="wl-stat-value">{(workloadTotals.cpuMillis / 1000).toFixed(1)}</span>
                <span className="wl-stat-label">CPU Cores</span>
              </div>
              <div className="wl-stat">
                <span className="wl-stat-value">{formatBytes(workloadTotals.memBytes)}</span>
                <span className="wl-stat-label">Memory</span>
              </div>
            </div>
          )}

          {hasWorkloadFilter && workloadPods.length > 0 && (
            <div className="wl-group-bar">
              <span className="wl-group-label">Group by</span>
              <div className="wl-mode-toggle">
                <button
                  className={`wl-mode-btn ${wlGroupBy === 'node' ? 'active' : ''}`}
                  onClick={() => { setWlGroupBy('node'); setExpandedWlNode(null) }}
                >Node</button>
                <button
                  className={`wl-mode-btn ${wlGroupBy === 'owner' ? 'active' : ''}`}
                  onClick={() => { setWlGroupBy('owner'); setExpandedWlNode(null) }}
                >Owner</button>
              </div>
            </div>
          )}

          {wlGroupBy === 'node' && hasWorkloadFilter && workloadByNode.length > 0 && (
            <div className="wl-table">
              <div className="wl-table-header">
                <span className="wl-col-node">Node</span>
                <span className="wl-col-pods">Pods</span>
                <span className="wl-col-gpu">GPU</span>
                <span className="wl-col-cpu">CPU</span>
                <span className="wl-col-mem">Memory</span>
              </div>
              {workloadByNode.map(row => {
                const isExpanded = expandedWlNode === row.nodeName
                return (
                  <div key={row.nodeName} className="wl-node-group">
                    <div
                      className={`wl-node-row ${isExpanded ? 'expanded' : ''}`}
                      onClick={() => setExpandedWlNode(isExpanded ? null : row.nodeName)}
                    >
                      <span className="wl-col-node">
                        <span className={`ready-dot ${row.ready ? 'ok' : 'bad'}`} />
                        <span className="wl-node-name">{row.nodeName}</span>
                        {row.clusterName && <span className="tag cluster-badge">{row.clusterName}</span>}
                      </span>
                      <span className="wl-col-pods">{row.pods.length}</span>
                      <span className="wl-col-gpu">{row.gpu > 0 ? <span className="gpu-count">{row.gpu}</span> : <span className="no-gpu">-</span>}</span>
                      <span className="wl-col-cpu">{(row.cpuMillis / 1000).toFixed(1)}</span>
                      <span className="wl-col-mem">{formatBytes(row.memBytes)}</span>
                    </div>
                    {isExpanded && (
                      <div className="wl-pod-list">
                        {row.pods.map(pod => (
                          <div key={pod.name} className="wl-pod-row">
                            <span className={`phase ${pod.phase.toLowerCase()}`}>{pod.phase}</span>
                            <span className="wl-pod-name" title={pod.name}>{pod.name}</span>
                            <span className="wl-pod-ns">{pod.namespace}</span>
                            <span className="wl-pod-gpu">{pod.gpu_request > 0 ? pod.gpu_request : '-'}</span>
                            <span className="wl-pod-cpu">{(pod.cpu_request_millicores / 1000).toFixed(1)}</span>
                            <span className="wl-pod-mem">{formatBytes(pod.memory_request_bytes)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {wlGroupBy === 'owner' && hasWorkloadFilter && workloadByOwner.length > 0 && (
            <div className="wl-table">
              <div className="wl-table-header wl-by-owner">
                <span className="wl-col-owner">Owner</span>
                <span className="wl-col-pods">Pods</span>
                <span className="wl-col-nodes">Nodes</span>
                <span className="wl-col-gpu">GPU</span>
                <span className="wl-col-cpu">CPU</span>
                <span className="wl-col-mem">Memory</span>
              </div>
              {workloadByOwner.map(row => {
                const isExpanded = expandedWlNode === row.ownerKey
                return (
                  <div key={row.ownerKey} className="wl-node-group">
                    <div
                      className={`wl-node-row wl-by-owner ${isExpanded ? 'expanded' : ''}`}
                      onClick={() => setExpandedWlNode(isExpanded ? null : row.ownerKey)}
                    >
                      <span className="wl-col-owner">
                        <span className={`kind ${row.kind.toLowerCase()}`}>{row.kind}</span>
                        <span className="wl-owner-name">{row.name}</span>
                      </span>
                      <span className="wl-col-pods">{row.pods.length}</span>
                      <span className="wl-col-nodes">{row.nodeCount}</span>
                      <span className="wl-col-gpu">{row.gpu > 0 ? <span className="gpu-count">{row.gpu}</span> : <span className="no-gpu">-</span>}</span>
                      <span className="wl-col-cpu">{(row.cpuMillis / 1000).toFixed(1)}</span>
                      <span className="wl-col-mem">{formatBytes(row.memBytes)}</span>
                    </div>
                    {isExpanded && (
                      <div className="wl-pod-list">
                        {row.pods.map(({ pod, nodeName, clusterName }) => (
                          <div key={pod.name} className="wl-pod-row wl-pod-by-owner">
                            <span className={`phase ${pod.phase.toLowerCase()}`}>{pod.phase}</span>
                            <span className="wl-pod-name" title={pod.name}>{pod.name}</span>
                            <span className="wl-pod-node">
                              {nodeName}
                              {clusterName && <span className="tag cluster-badge">{clusterName}</span>}
                            </span>
                            <span className="wl-pod-gpu">{pod.gpu_request > 0 ? pod.gpu_request : '-'}</span>
                            <span className="wl-pod-cpu">{(pod.cpu_request_millicores / 1000).toFixed(1)}</span>
                            <span className="wl-pod-mem">{formatBytes(pod.memory_request_bytes)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {hasWorkloadFilter && workloadPods.length === 0 && (
            <div className="wl-empty">No pods match the selected filter</div>
          )}

          {!hasWorkloadFilter && (
            <div className="wl-empty">
              {workloadMode === 'owner'
                ? 'Select one or more owners to view workload distribution'
                : 'Select a label key and value to filter pods'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}

function formatBytesRaw(b) {
  for (const u of ['B', 'KiB', 'MiB', 'GiB', 'TiB']) {
    if (b < 1024) return `${b.toFixed(1)}${u}`
    b /= 1024
  }
  return `${b.toFixed(1)}PiB`
}

function aggregateSummaries(summaries) {
  const aggResource = (field) => {
    const total = summaries.reduce((s, sm) => s + (sm[field]?.total || 0), 0)
    const allocatable = summaries.reduce((s, sm) => s + (sm[field]?.allocatable || 0), 0)
    const used = summaries.reduce((s, sm) => s + (sm[field]?.used || 0), 0)
    const available = allocatable - used
    const utilization_percent = allocatable > 0 ? Math.round(used / allocatable * 1000) / 10 : 0
    return { total, allocatable, used, available, utilization_percent }
  }

  const cpu = { ...aggResource('cpu'), unit: 'millicores' }
  cpu.total_display = `${(cpu.total / 1000).toFixed(1)} cores`
  cpu.used_display = `${(cpu.used / 1000).toFixed(1)} cores`
  cpu.available_display = `${(cpu.available / 1000).toFixed(1)} cores`

  const memory = { ...aggResource('memory'), unit: 'bytes' }
  memory.total_display = formatBytesRaw(memory.total)
  memory.used_display = formatBytesRaw(memory.used)
  memory.available_display = formatBytesRaw(memory.available)

  const gpu = { ...aggResource('gpu'), unit: 'GPUs' }
  gpu.total_display = String(gpu.total)
  gpu.used_display = String(gpu.used)
  gpu.available_display = String(gpu.available)

  const pods_total = summaries.reduce((s, sm) => s + (sm.pods?.total || 0), 0)
  const node_count = summaries.reduce((s, sm) => s + (sm.node_count || 0), 0)
  const ready_node_count = summaries.reduce((s, sm) => s + (sm.ready_node_count || 0), 0)

  const gpuTypeMap = {}
  summaries.forEach(sm => {
    ;(sm.gpu_by_type || []).forEach(g => {
      if (!gpuTypeMap[g.gpu_type]) gpuTypeMap[g.gpu_type] = { total: 0, allocatable: 0, used: 0, node_count: 0 }
      gpuTypeMap[g.gpu_type].total += g.total
      gpuTypeMap[g.gpu_type].allocatable += g.allocatable
      gpuTypeMap[g.gpu_type].used += g.used
      gpuTypeMap[g.gpu_type].node_count += g.node_count
    })
  })
  const gpu_by_type = Object.entries(gpuTypeMap).sort(([a], [b]) => a.localeCompare(b)).map(([gtype, s]) => ({
    gpu_type: gtype,
    total: s.total, allocatable: s.allocatable, used: s.used,
    available: s.allocatable - s.used,
    utilization_percent: s.allocatable > 0 ? Math.round(s.used / s.allocatable * 1000) / 10 : 0,
    node_count: s.node_count,
  }))

  return {
    cpu, memory, gpu,
    pods: { total: pods_total, allocatable: pods_total, used: pods_total, available: 0, utilization_percent: 0, unit: 'pods', total_display: String(pods_total), used_display: String(pods_total), available_display: '0' },
    node_count, ready_node_count, gpu_by_type,
  }
}

export default App
