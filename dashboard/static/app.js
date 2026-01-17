// Trading Dashboard Frontend - Updated for Agent
// include BYOK and Account, User Settings Modals

let updateInterval;
let portfolioChart = null;
let positionEventSource = null;

// ============================================================================
// PULSE GRAPH VISUALIZATION
// ============================================================================

// Cache for closed trades and open positions (for pulse graph)
let closedTradesCache = [];
let openPositionsCache = [];

// Pulse Graph Configuration
const PULSE_CONFIG = {
    maxItems: 10,           // Max total items (active + closed)
    layerOffset: 5,         // Pixels between layers (Layer 0 at bottom/front)
    maxPricePoints: 50,     // Max price history points per trade
    activeStrokeWidth: 2.5,
    closedStrokeWidth: 2,
    colors: {
        profit: '#00ff88',      // var(--accent-green)
        loss: '#ff4757',        // var(--accent-red)
        closed: '#6b7280',      // Grey for closed trades
    }
};

// Calculate opacity for closed trades (smooth fade from 85% to 10%)
function getPulseOpacity(layerIndex, activeCount) {
    // Active positions always 100%
    if (layerIndex < activeCount) return 1.0;

    // Closed trades fade from 85% to 10%
    const closedIndex = layerIndex - activeCount;
    const closedCount = PULSE_CONFIG.maxItems - activeCount;
    const startOpacity = 0.85;
    const endOpacity = 0.10;

    if (closedCount <= 1) return startOpacity;

    // EaseOut quad for smooth perceptual fade
    const progress = closedIndex / (closedCount - 1);
    const eased = 1 - Math.pow(1 - progress, 2);

    return startOpacity - (eased * (startOpacity - endOpacity));
}

// Generate bezel path: flat entry → price curve → dot at 75% → bezel out → flat end
function generatePulsePath(priceHistory, entryPrice, currentPrice, svgWidth, svgHeight, yOffset) {
    // Near edge-to-edge: 20px padding each side
    const padding = { left: 20, right: 20, top: 30, bottom: 30 };
    const flatSectionWidth = 18;  // Flat horizontal section at start/end
    const bezelWidth = 35;        // Width of bezel curve transition

    const startX = padding.left;
    const endX = svgWidth - padding.right;

    if (!priceHistory || priceHistory.length < 2) {
        const y = svgHeight / 2 + yOffset;
        return {
            linePath: `M ${startX} ${y} L ${endX} ${y}`,
            fillPath: `M ${startX} ${y} L ${endX} ${y} L ${endX} ${svgHeight} L ${startX} ${svgHeight} Z`,
            entryY: y,
            startX: startX,
            currentDot: null
        };
    }

    const prices = priceHistory.map(p => p.price);
    const minPrice = Math.min(entryPrice, currentPrice, ...prices) * 0.995;
    const maxPrice = Math.max(entryPrice, currentPrice, ...prices) * 1.005;
    const priceRange = maxPrice - minPrice || entryPrice * 0.01;

    // Convert price to Y coordinate (inverted - higher price = lower Y)
    const priceToY = (price) => {
        const normalized = (price - minPrice) / priceRange;
        return padding.top + yOffset + (1 - normalized) * (svgHeight - padding.top - padding.bottom - 50);
    };

    const entryY = priceToY(entryPrice);
    const currentY = priceToY(currentPrice);

    // Zones: [flat 18px] [bezel in 35px] [price curve to 75%] [DOT] [bezel out] [flat 18px]
    const flatStartEnd = startX + flatSectionWidth;
    const bezelInEnd = flatStartEnd + bezelWidth;
    const flatEndStart = endX - flatSectionWidth;

    // Current price dot at ~75% of total width
    const totalWidth = endX - startX;
    const dotX = startX + totalWidth * 0.75;

    // Price curve spans from bezel-in-end to dot position
    const priceZoneStart = bezelInEnd;
    const priceZoneWidth = dotX - priceZoneStart;

    // Generate points along the price path (up to the dot)
    const points = priceHistory.map((point, index) => {
        const progress = index / (priceHistory.length - 1);
        const x = priceZoneStart + progress * priceZoneWidth;
        const y = priceToY(point.price);
        return { x, y };
    });

    // Build path:
    // 1. Flat start section at entry level
    let pathD = `M ${startX} ${entryY} L ${flatStartEnd} ${entryY}`;

    // 2. Bezel in: curve from entry level to first price point
    const firstPoint = points[0];
    pathD += ` C ${flatStartEnd + bezelWidth * 0.5} ${entryY}, ${firstPoint.x - bezelWidth * 0.4} ${firstPoint.y}, ${firstPoint.x} ${firstPoint.y}`;

    // 3. Smooth curve through price points
    for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const curr = points[i];
        const cpX = (prev.x + curr.x) / 2;
        pathD += ` Q ${cpX} ${prev.y}, ${curr.x} ${curr.y}`;
    }

    // 4. Continue to current price dot position
    const lastPoint = points[points.length - 1];
    pathD += ` Q ${(lastPoint.x + dotX) / 2} ${lastPoint.y}, ${dotX} ${currentY}`;

    // 5. Bezel out: curve from current price back to entry level
    const bezelOutWidth = flatEndStart - dotX;
    pathD += ` C ${dotX + bezelOutWidth * 0.4} ${currentY}, ${flatEndStart - bezelOutWidth * 0.3} ${entryY}, ${flatEndStart} ${entryY}`;

    // 6. Flat end section at entry level
    pathD += ` L ${endX} ${entryY}`;

    // Fill path for gradient
    const fillPath = pathD + ` L ${endX} ${svgHeight} L ${startX} ${svgHeight} Z`;

    // Return dot position for rendering
    const currentDot = { x: dotX, y: currentY };

    return { linePath: pathD, fillPath, entryY, startX, currentDot };
}

// Generate mock price history if not available
function generateMockPriceHistory(trade) {
    const entryPrice = trade.entry_price || trade.entryPrice || 100;
    const currentPrice = trade.mark_price || trade.exit_price || trade.currentPrice || entryPrice;
    const points = [];
    const numPoints = 35;

    for (let i = 0; i <= numPoints; i++) {
        const progress = i / numPoints;
        const basePrice = entryPrice + (currentPrice - entryPrice) * progress;
        // Add organic noise for realistic appearance
        const noise = (Math.sin(i * 0.6 + Math.random()) * 0.4 + Math.cos(i * 0.3) * 0.3) * entryPrice * 0.008;
        points.push({ time: i, price: basePrice + noise });
    }

    return points;
}

// Render the complete pulse graph
function renderPulseGraph(openPositions, closedTrades) {
    const svg = document.getElementById('pulse-svg');
    if (!svg) return;

    const svgWidth = 800;
    const svgHeight = 220;

    // Check if we have any data
    if ((!openPositions || openPositions.length === 0) && (!closedTrades || closedTrades.length === 0)) {
        svg.innerHTML = `<text x="400" y="110" text-anchor="middle" fill="#666666" font-size="13">No active positions or recent trades</text>`;
        return;
    }

    // Limit items (max 10 total)
    const activeCount = Math.min(openPositions.length, 3);
    const closedCount = Math.min(closedTrades.length, PULSE_CONFIG.maxItems - activeCount);

    const activeTrades = openPositions.slice(0, activeCount);
    const closedItems = closedTrades.slice(0, closedCount);

    // Build render list: oldest first for correct z-order (SVG renders first = back, last = front)
    // Layer 0 = newest active (rendered LAST = in front, at BOTTOM visually)
    // Layer 9 = oldest closed (rendered FIRST = in back, at TOP visually)
    const renderList = [];

    // Add closed trades first (they render in back, higher Y offset)
    for (let i = closedCount - 1; i >= 0; i--) {
        const layerIdx = activeCount + i;
        renderList.push({
            data: closedItems[i],
            layerIndex: layerIdx,
            isActive: false
        });
    }

    // Add active trades last (they render in front, lower Y offset)
    for (let i = activeCount - 1; i >= 0; i--) {
        renderList.push({
            data: activeTrades[i],
            layerIndex: i,
            isActive: true
        });
    }

    // Generate SVG content with pulsing animation
    let svgContent = `
        <defs>
            <linearGradient id="pulse-grad-profit" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="${PULSE_CONFIG.colors.profit}" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="${PULSE_CONFIG.colors.profit}" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="pulse-grad-loss" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="${PULSE_CONFIG.colors.loss}" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="${PULSE_CONFIG.colors.loss}" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="pulse-grad-closed" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="${PULSE_CONFIG.colors.closed}" stop-opacity="0.15"/>
                <stop offset="100%" stop-color="${PULSE_CONFIG.colors.closed}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <style>
            @keyframes pulse-dot {
                0%, 100% { r: 4; opacity: 1; }
                50% { r: 6; opacity: 0.8; }
            }
            .pulse-dot { animation: pulse-dot 1.5s ease-in-out infinite; }
        </style>
    `;

    // Render each trade/position
    renderList.forEach(item => {
        const { data, layerIndex, isActive } = item;
        // Y offset: Layer 0 (newest) at bottom, higher layers pushed up
        const yOffset = layerIndex * PULSE_CONFIG.layerOffset;
        const opacity = getPulseOpacity(layerIndex, activeCount);

        // Get price history or generate mock
        const priceHistory = data.priceHistory || generateMockPriceHistory(data);
        const entryPrice = data.entry_price || data.entryPrice || 100;
        const currentPrice = data.mark_price || data.exit_price || data.currentPrice || entryPrice;

        const { linePath, fillPath, entryY, startX, currentDot } = generatePulsePath(
            priceHistory, entryPrice, currentPrice, svgWidth, svgHeight, yOffset
        );

        // Determine colors based on PnL
        const pnl = data.pnl_percent || data.pnlPercent || 0;
        let strokeColor, gradientId;

        if (isActive) {
            strokeColor = pnl >= 0 ? PULSE_CONFIG.colors.profit : PULSE_CONFIG.colors.loss;
            gradientId = pnl >= 0 ? 'pulse-grad-profit' : 'pulse-grad-loss';
        } else {
            // Closed trades: subtle tint based on outcome
            strokeColor = pnl >= 0 ? '#7a9a7a' : '#9a7a7a';
            gradientId = 'pulse-grad-closed';
        }

        const strokeWidth = isActive ? PULSE_CONFIG.activeStrokeWidth : PULSE_CONFIG.closedStrokeWidth;

        // Label position: symbol at start of flat section
        const labelStartX = startX + 8;

        // Add group for this trade
        svgContent += `
            <g opacity="${opacity.toFixed(2)}">
                <path d="${fillPath}" fill="url(#${gradientId})"/>
                <path d="${linePath}"
                      fill="none"
                      stroke="${strokeColor}"
                      stroke-width="${strokeWidth}"
                      stroke-linecap="round"
                      stroke-linejoin="round"/>
                ${isActive && currentDot ? `
                    <!-- Pulsing dot at current price (75% width) -->
                    <circle class="pulse-dot" cx="${currentDot.x.toFixed(1)}" cy="${currentDot.y.toFixed(1)}" r="4" fill="${strokeColor}"/>
                    <!-- Symbol label at left flat section -->
                    <text x="${labelStartX}" y="${(entryY - 8).toFixed(1)}" fill="${strokeColor}" font-size="11" font-weight="600" font-family="Inter, sans-serif">
                        ${data.symbol || 'N/A'}
                    </text>
                    <!-- PnL percentage near the dot -->
                    <text x="${(currentDot.x + 12).toFixed(1)}" y="${(currentDot.y - 8).toFixed(1)}" fill="${strokeColor}" font-size="11" font-weight="600" font-family="Inter, sans-serif">
                        ${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%
                    </text>
                ` : ''}
            </g>
        `;
    });

    svg.innerHTML = svgContent;
}

// Generate mini price path SVG for trade cards
function generateMiniPricePath(trade) {
    const entryPrice = trade.entry_price || 100;
    const exitPrice = trade.exit_price || trade.current_price || entryPrice;
    const pnl = trade.pnl || 0;
    const isProfit = pnl >= 0;
    const color = isProfit ? '#00ff88' : '#ff4757';
    const uniqueId = trade.id || Date.now() + Math.random();

    // Generate realistic path
    const startY = 16;
    const endY = startY; // Return to entry level (bezel)
    const peakY = isProfit ? 6 : 26;

    // Create bezier path that returns to entry level
    const path = `M 8 ${startY} C 40 ${startY}, 60 ${peakY}, 100 ${(startY + peakY) / 2} C 140 ${peakY + (isProfit ? 2 : -2)}, 160 ${startY}, 192 ${endY}`;

    return `
        <defs>
            <linearGradient id="mini-grad-${uniqueId}" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="${color}" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <path d="${path} L 192 32 L 8 32 Z" fill="url(#mini-grad-${uniqueId})"/>
        <path d="${path}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="8" cy="${startY}" r="2.5" fill="${color}"/>
        <circle cx="192" cy="${endY}" r="2.5" fill="${color}"/>
        <text x="16" y="${startY - 5}" fill="${color}" font-size="7" font-weight="600" font-family="Inter, sans-serif">ENTRY</text>
        <text x="184" y="${endY - 5}" fill="${color}" font-size="7" font-weight="600" font-family="Inter, sans-serif" text-anchor="end">EXIT</text>
    `;
}

// Format trade time
function formatTradeTime(timestamp) {
    if (!timestamp) return '--:--';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
}

// Get leverage risk class
function getLeverageRiskClass(leverage) {
    if (leverage <= 5) return 'low-risk';
    if (leverage <= 15) return 'medium-risk';
    return 'high-risk';
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Dashboard initializing...');

    // Load saved timezone preference
    const savedTimezone = localStorage.getItem('preferred_timezone') || 'local';
    const timezoneSelect = document.getElementById('timezone-select');
    if (timezoneSelect) {
        timezoneSelect.value = savedTimezone;
    }

    // Load settings
    loadSettings();

    // Load agent state first
    loadAgentState();

    // Load tier info to apply feature locks
    loadTierInfo();

    // Initial updates
    updateDashboard();
    updateConsole();
    updateTimestamp(); // Initialize timestamp with saved timezone

    // Start SSE stream for real-time position updates
    startPositionStream();

    // Set up intervals (reduced frequency since positions use SSE)
    updateInterval = setInterval(updateDashboard, 30000); // Account data every 30s
    setInterval(updateConsole, 5000);
    setInterval(updateTimestamp, 1000); // Update timestamp every second

    console.log('✅ Dashboard ready - real-time positions via WebSocket');
});

// Start Server-Sent Events stream for real-time position updates
function startPositionStream() {
    if (positionEventSource) {
        positionEventSource.close();
    }

    try {
        positionEventSource = new EventSource('/api/positions/stream');

        positionEventSource.onmessage = (event) => {
            try {
                const positions = JSON.parse(event.data);
                if (!positions.error) {
                    updatePositions(positions);
                    console.log('[SSE] Position update received:', positions.length, 'positions');
                }
            } catch (e) {
                console.error('[SSE] Parse error:', e);
            }
        };

        positionEventSource.onerror = (error) => {
            console.warn('[SSE] Connection error, will retry...');
            // EventSource auto-reconnects, but we can add a fallback
            if (positionEventSource.readyState === EventSource.CLOSED) {
                setTimeout(startPositionStream, 5000);
            }
        };

        positionEventSource.onopen = () => {
            console.log('[SSE] Position stream connected');
        };

    } catch (e) {
        console.error('[SSE] Failed to start stream:', e);
        // Fall back to polling
        console.log('[SSE] Falling back to polling');
    }
}


// Main update function
// Smart update function - always do full updates regardless of execution state
async function updateDashboard() {
    try {
        // Always do full update - no skipping during execution
        const response = await fetch('/api/data');

        if (!response.ok) {
            console.error('API returned error:', response.status);

            // Handle authentication errors
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            setStatusOffline();
            return;
        }
        
        const data = await response.json();
        
        console.log('[Dashboard] Full update at', new Date().toLocaleTimeString());
        
        // Update all metrics
        updateBalance(data.account_balance, data.total_equity);
        updatePnL(data.pnl, data.starting_balance);
        updateStatus(data.status, data.agent_running);
        updateExchange(data.exchange);
        updateTimestamp();
        updatePositions(data.positions);
        
        // Get agent execution status separately
        const statusResponse = await fetch('/api/agent-status');
        const agentStatus = await statusResponse.json();
        updateAgentBadge(data.agent_running, agentStatus.executing); // Pass execution state
        
        // Fetch trades
        const tradesResponse = await fetch('/api/trades');
        const trades = await tradesResponse.json();
        updateTrades(trades);

        // Update portfolio chart
        updatePortfolioChart();

    } catch (error) {
        console.error('❌ Dashboard update error:', error);
        setStatusOffline();
    }
}

// Update account balance
function updateBalance(available, equity) {
    document.getElementById('balance').textContent = `$${available.toFixed(2)}`;
    document.getElementById('equity').textContent = `$${equity.toFixed(2)}`;
}

// Update P&L
function updatePnL(pnl, startingBalance = null) {
    const pnlEl = document.getElementById('pnl');
    const pnlPctEl = document.getElementById('pnl-pct');
    
    // If startingBalance not provided by API, try to get from UI input, fallback to 10
    if (startingBalance === null || isNaN(startingBalance)) {
        const input = document.getElementById('starting-balance');
        startingBalance = (input && input.value) ? parseFloat(input.value) : 10;
    }
    
    const pnlClass = pnl >= 0 ? 'positive' : 'negative';
    pnlEl.className = `value pnl ${pnlClass}`;
    pnlEl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
    
    const pnlPct = ((pnl / startingBalance) * 100).toFixed(2);
    pnlPctEl.className = `sublabel ${pnlClass}`;
    pnlPctEl.textContent = `${pnl >= 0 ? '+' : ''}${pnlPct}%`;
}

// Update trading status
function updateStatus(status, isRunning) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = status;
    statusEl.className = 'sublabel ' + (isRunning ? 'running' : 'ready');
}

// Update exchange display
function updateExchange(exchange) {
    const exchangeEl = document.getElementById('exchange');
    exchangeEl.textContent = exchange || 'HyperLiquid';
}

// Update timezone preference
function updateTimezone() {
    const select = document.getElementById('timezone-select');
    const selectedZone = select.value;
    localStorage.setItem('preferred_timezone', selectedZone);
    updateTimestamp(); // Refresh timestamp immediately
    updateConsole(); // Refresh console with new timezone
}

// Update timestamp with timezone support
function updateTimestamp() {
    const now = new Date();
    const timezone = localStorage.getItem('preferred_timezone') || 'local';

    let timeString;
    if (timezone === 'local') {
        timeString = now.toLocaleTimeString('en-US', { hour12: false });
    } else if (timezone === 'UTC') {
        timeString = now.toLocaleTimeString('en-US', {
            hour12: false,
            timeZone: 'UTC'
        });
    } else {
        timeString = now.toLocaleTimeString('en-US', {
            hour12: false,
            timeZone: timezone
        });
    }

    document.getElementById('timestamp').textContent = timeString;
}

// Update agent badge with execution state (no API calls - uses passed data)
function updateAgentBadge(isRunning, isExecuting = false) {
    const badge = document.getElementById('agent-badge');
    const runBtn = document.getElementById('run-btn');
    const pauseBtn = document.getElementById('pause-btn');

    if (isExecuting) {
        badge.textContent = 'RUNNING';
        badge.className = 'agent-badge running';
        runBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-flex';
    } else if (isRunning) {
        badge.textContent = 'stand by';
        badge.className = 'agent-badge running';
        runBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-flex';
    } else {
        badge.textContent = 'ready';
        badge.className = 'agent-badge ready';
        runBtn.style.display = 'inline-flex';
        pauseBtn.style.display = 'none';
    }
}

// Update positions display with headers, leverage badge, and inline buttons
function updatePositions(positions) {
    const container = document.getElementById('positions');
    const badge = document.getElementById('position-count');
    badge.textContent = positions.length;

    // Cache positions for pulse graph
    openPositionsCache = positions || [];

    if (!positions || positions.length === 0) {
        container.innerHTML = '<div class="empty-state">No open positions</div>';
        // Still render pulse graph (will show closed trades if any)
        renderPulseGraph([], closedTradesCache);
        return;
    }

    container.innerHTML = positions.map(pos => {
        const sideClass = pos.side.toLowerCase();
        // Calculate actual dollar PnL from price difference and position size
        const markPrice = pos.mark_price || pos.entry_price;
        const dollarPnl = (markPrice - pos.entry_price) * pos.size;
        const isProfit = dollarPnl >= 0;
        // Use ROE (Return on Equity) from HyperLiquid
        const pctPnl = pos.pnl_percent || 0;
        // Get leverage (default to 20 if not provided)
        const leverage = pos.leverage || 20;
        const leverageClass = getLeverageRiskClass(leverage);

        return `
        <div class="position">
            <div class="position-header">
                <div class="position-symbol-group">
                    <span class="position-value symbol-${sideClass}" style="font-weight: 600; font-size: 14px;">${pos.symbol}</span>
                    <span class="side ${sideClass}" style="font-size: 10px;">${pos.side}</span>
                    <span class="leverage-badge ${leverageClass}">${leverage}x</span>
                </div>
                <span class="position-pnl-display pnl ${isProfit ? 'positive' : 'negative'}">
                    ${isProfit ? '+' : ''}${pctPnl.toFixed(2)}%
                </span>
            </div>
            <div class="position-row">
                <div class="position-item">
                    <span class="position-label">Size</span>
                    <span class="position-value">${Math.abs(pos.size).toFixed(4)}</span>
                </div>
                <div class="position-item">
                    <span class="position-label">Value</span>
                    <span class="position-value">$${pos.position_value ? pos.position_value.toFixed(2) : '0.00'}</span>
                </div>
                <div class="position-item">
                    <span class="position-label">Entry</span>
                    <span class="position-value">$${pos.entry_price.toFixed(2)}</span>
                </div>
                <div class="position-item">
                    <span class="position-label">Mark</span>
                    <span class="position-value">$${markPrice.toFixed(2)}</span>
                </div>
                <div class="position-item">
                    <span class="position-label">P&L</span>
                    <span class="position-value pnl ${isProfit ? 'positive' : 'negative'}">
                        ${isProfit ? '+' : ''}$${dollarPnl.toFixed(2)}
                    </span>
                </div>
            </div>
            <div class="position-actions-row">
                <button class="btn-position-action btn-close-position" onclick="closePosition('${pos.symbol}')" title="Close Position">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
                <a href="https://app.hyperliquid.xyz/trade/${pos.symbol}" target="_blank" class="btn-position-action btn-chart" title="View Chart on Exchange">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"></path><path d="M18 17V9"></path><path d="M13 17V5"></path><path d="M8 17v-3"></path></svg>
                </a>
            </div>
        </div>
        `;
    }).join('');

    // Render pulse graph with current positions and cached trades
    renderPulseGraph(openPositionsCache, closedTradesCache);
}

// Close a single position
async function closePosition(symbol) {
    if (!confirm(`Are you sure you want to close your ${symbol} position?`)) {
        return;
    }

    try {
        addConsoleMessage(`Closing ${symbol} position...`, 'info');

        const response = await fetch(`/api/close-position/${symbol}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            addConsoleMessage(`${symbol} position closed successfully`, 'success');
            updateDashboard(); // Refresh data
        } else {
            addConsoleMessage(`Failed to close ${symbol}: ${data.message}`, 'error');
        }
    } catch (error) {
        addConsoleMessage(`Error closing ${symbol}: ${error.message}`, 'error');
    }
}

// Close all positions
async function closeAllPositions() {
    if (!confirm('Close ALL open positions? This cannot be undone.')) {
        return;
    }

    try {
        addConsoleMessage('Closing all positions...', 'info');

        const response = await fetch('/api/positions/close-all', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            addConsoleMessage(`Closed ${data.closed_count} positions`, 'success');
            // Refresh positions
            updateDashboard();
        } else {
            addConsoleMessage(`Failed to close positions: ${data.error}`, 'error');
        }
    } catch (error) {
        addConsoleMessage(`Error closing positions: ${error.message}`, 'error');
    }
}

// Update trades history with price path visualization

function updateTrades(trades) {
    const recentContainer = document.getElementById('recent-trades');
    const tradesCountEl = document.getElementById('trades-count');

    // Cache closed trades for pulse graph (max 10)
    closedTradesCache = (trades || []).slice(0, 10);

    if (!trades || trades.length === 0) {
        if (recentContainer) {
            recentContainer.innerHTML = '<div class="empty-state">No recent trades</div>';
        }
        if (tradesCountEl) {
            tradesCountEl.textContent = '0';
        }
        // Render pulse graph with positions only
        renderPulseGraph(openPositionsCache, []);
        return;
    }

    // Update trades count badge
    if (tradesCountEl) {
        tradesCountEl.textContent = trades.length.toString();
    }

    // Helper function to render a trade card with price path
    const renderTradeCard = (trade, index) => {
        const time = formatTradeTime(trade.timestamp);
        const pnl = trade.pnl || 0;
        const pnlStr = pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`;
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        const side = trade.side || 'LONG';
        const leverage = trade.leverage || 20;
        const leverageClass = getLeverageRiskClass(leverage);
        const duration = trade.duration || '--';

        // Calculate percentage PnL if entry value available
        const entryValue = trade.entry_value || trade.entry_price * Math.abs(trade.size || 1);
        const pctPnl = entryValue > 0 ? (pnl / entryValue) * 100 : 0;

        return `
            <div class="trade-card">
                <div class="trade-card-header">
                    <div class="trade-card-left">
                        <span class="trade-card-symbol">${trade.symbol}</span>
                        <span class="side ${side.toLowerCase()}">${side}</span>
                        <span class="leverage-badge ${leverageClass}">${leverage}x</span>
                    </div>
                    <span class="trade-card-pnl pnl ${pnlClass}">${pnlStr}</span>
                </div>
                <div class="trade-price-path">
                    <svg viewBox="0 0 200 32" preserveAspectRatio="xMidYMid meet">
                        ${generateMiniPricePath(trade)}
                    </svg>
                </div>
                <div class="trade-meta">
                    <div class="trade-meta-left">
                        <span>${time}</span>
                        <span class="trade-duration">(${duration})</span>
                    </div>
                    <span class="pnl ${pnlClass}">${pctPnl >= 0 ? '+' : ''}${pctPnl.toFixed(1)}%</span>
                </div>
            </div>
        `;
    };

    // Update Recent Trades card (last 10 with price paths)
    if (recentContainer) {
        recentContainer.innerHTML = trades.slice(0, 10).map((trade, i) => renderTradeCard(trade, i)).join('');
    }

    // Render pulse graph with current data
    renderPulseGraph(openPositionsCache, closedTradesCache);
}

// Update console logs

async function updateConsole() {
    try {
        const response = await fetch('/api/console');
        const logs = await response.json();
        
        const consoleEl = document.getElementById('console');
        
        if (logs.length === 0) {
            consoleEl.innerHTML = '<div class="console-line info">No activity yet</div>';
            return;
        }
        
        // Keep last 50 logs and REVERSE (newest first)
        const recentLogs = logs.slice(-50).reverse();
        
        // Get selected timezone
        const timezone = localStorage.getItem('preferred_timezone') || 'local';
        
        // Render with level classes and selective emojis
        consoleEl.innerHTML = recentLogs.map(log => {
            const emoji = getLogEmoji(log);
            const levelClass = log.level || 'info';
            
            // Convert timestamp to selected timezone
            const displayTime = convertTimestamp(log.timestamp, timezone);
            
            return `<div class="console-line ${levelClass}">${emoji}[${displayTime}] ${log.message}</div>`;
        }).join('');
        
    } catch (error) {
        console.error('Error updating console:', error);
    }
}

// Helper function for selective emoji usage
function getLogEmoji(log) {
    const msg = log.message.toLowerCase();
    const level = log.level || 'info';
    
    // Only add emoji for important events
    if (level === 'success' && msg.includes('started')) return '▶️ ';
    if (level === 'info' && msg.includes('stopped')) return '⏹️ ';
    if (level === 'trade') {
        // Emoji already in message from backend
        if (msg.includes('📈') || msg.includes('📉')) return '';
    }
    if (level === 'error') return '❌ ';
    
    return ''; // No emoji for most messages
}

// Convert timestamp to selected timezone
function convertTimestamp(timestamp, timezone) {
    // Backend sends HH:MM:SS in UTC
    // We need to parse it and convert to selected timezone
    
    try {
        // Get today's date and combine with the time
        const now = new Date();
        const [hours, minutes, seconds] = timestamp.split(':').map(Number);
        
        // Create UTC date object
        const utcDate = new Date(Date.UTC(
            now.getUTCFullYear(),
            now.getUTCMonth(),
            now.getUTCDate(),
            hours,
            minutes,
            seconds || 0
        ));
        
        if (timezone === 'local') {
            // Convert to user's local timezone
            return utcDate.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } else if (timezone === 'UTC') {
            // Keep as UTC
            return timestamp;
        } else {
            // Convert to specific timezone
            return utcDate.toLocaleTimeString('en-US', {
                hour12: false,
                timeZone: timezone,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    } catch (error) {
        // If conversion fails, return original
        return timestamp;
    }
}

// Load agent state on page load
async function loadAgentState() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        console.log('Agent state loaded:', data);

        // Update UI based on persisted state
        updateAgentBadge(data.running, false);  // Not executing on initial load

        // Log last action info
        if (data.last_started) {
            const lastStart = new Date(data.last_started).toLocaleTimeString();
            console.log(`Last agent start: ${lastStart}`);
        }
        if (data.last_stopped) {
            const lastStop = new Date(data.last_stopped).toLocaleTimeString();
            console.log(`Last agent stop: ${lastStop}`);
        }
        
    } catch (error) {
        console.error('Error loading agent state:', error);
    }
}

// Add console message locally (prepends to top)
function addConsoleMessage(message, level = 'info') {
    const consoleEl = document.getElementById('console');
    const time = new Date().toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const line = document.createElement('div');
    line.className = `console-line ${level}`;
    line.textContent = `[${time}] ${message}`;
    
    // Prepend to top (newest first)
    consoleEl.insertBefore(line, consoleEl.firstChild);
    
    // Keep only last 50 messages
    while (consoleEl.children.length > 50) {
        consoleEl.removeChild(consoleEl.lastChild);
    }
}

// Clear console - calls backend API to clear logs properly
async function clearConsole() {
    const consoleEl = document.getElementById('console');

    try {
        const response = await fetch('/api/console/clear', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            consoleEl.innerHTML = '<div class="console-line info">Console cleared</div>';
        } else {
            consoleEl.innerHTML = '<div class="console-line error">Failed to clear</div>';
        }
    } catch (error) {
        console.error('Error clearing console:', error);
        consoleEl.innerHTML = '<div class="console-line info">Console cleared</div>';
    }
}

// Run agent
async function runAgent() {
    try {
        addConsoleMessage('Starting trading agent...', 'info');

        // Immediate visual feedback - show starting state
        updateAgentBadge(true, false);

        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'started') {
            addConsoleMessage('Trading agent started successfully', 'success');
            updateDashboard(); // Full update to sync state
        } else if (data.status === 'already_running') {
            addConsoleMessage('Agent is already running', 'warning');
        } else {
            addConsoleMessage(data.message, 'warning');
            // Revert visual state on failure
            updateAgentBadge(false, false);
        }
    } catch (error) {
        addConsoleMessage(`Error starting agent: ${error.message}`, 'error');
        // Revert visual state on error
        updateAgentBadge(false, false);
    }
}

// Stop agent
async function stopAgent() {
    try {
        addConsoleMessage('Stopping trading agent...', 'info');

        // Immediate visual feedback - show stopping state
        const badge = document.getElementById('agent-badge');
        badge.textContent = 'stopping...';
        badge.className = 'agent-badge stopping';

        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'stopped') {
            addConsoleMessage('Trading agent stopped successfully', 'info');
            // FIX: Immediately update button state to show Start button
            updateAgentBadge(false, false);
            // Then do full dashboard update
            updateDashboard();
        } else if (data.status === 'not_running') {
            addConsoleMessage('Agent is not running', 'warning');
            updateAgentBadge(false, false);
        } else {
            addConsoleMessage(data.message, 'warning');
            // Revert to running state on unexpected response
            updateAgentBadge(true, false);
        }
    } catch (error) {
        addConsoleMessage(`Error stopping agent: ${error.message}`, 'error');
        // On error, refresh to get actual state
        updateDashboard();
    }
}

// Set offline status
function setStatusOffline() {
    document.getElementById('status').className = 'sublabel offline';
    document.getElementById('status').textContent = 'Offline';
    document.getElementById('agent-badge').textContent = 'Disconnected';
    document.getElementById('agent-badge').className = 'agent-badge offline';
}

// Auto-update cleanup
window.addEventListener('beforeunload', () => {
    clearInterval(updateInterval);
    if (positionEventSource) {
        positionEventSource.close();
    }
});

// ============================================================================
// THEME TOGGLE - REMOVED (Dark mode only)
// ============================================================================

// ============================================================================
// SETTINGS MODAL
// ============================================================================

// Global state for settings
let availableTokens = {};
let selectedTokens = [];
let availableProviders = [];
let availableModels = {};
let swarmModels = [];

function openSettings() {
    document.getElementById('settings-modal').classList.add('show');
    loadSettings();
}

function closeSettings(event) {
    if (!event || event.target.id === 'settings-modal' || event.target.classList.contains('modal-close')) {
        document.getElementById('settings-modal').classList.remove('show');
    }
}

// Tab switching
function switchSettingsTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.settings-tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// Load all settings from API
async function loadSettings() {
    try {
        // Load settings, tokens (live from Hyperliquid), models, and strategies in parallel
        const [settingsRes, tokensRes, modelsRes, strategiesRes] = await Promise.all([
            fetch('/api/settings'),
            fetch('/api/tokens?live=true'),  // Fetch live tokens from Hyperliquid
            fetch('/api/ai-models'),
            fetch('/api/strategies')  // Fetch available strategies
        ]);

        const settingsData = await settingsRes.json();
        const tokensData = await tokensRes.json();
        const modelsData = await modelsRes.json();
        const strategiesData = await strategiesRes.json();

        // Store available data
        if (tokensData.success) {
            availableTokens = tokensData.categories;
            populateTokenCategories();

            // Show source indicator
            if (tokensData.source === 'live') {
                console.log(`✅ Loaded ${tokensData.total_count} live tokens from Hyperliquid`);
            }
        }

        if (modelsData.success) {
            availableProviders = modelsData.providers;
            availableModels = modelsData.models;
            populateProviderDropdowns();
        }

        // Render strategies
        if (strategiesData.success) {
            renderStrategies(strategiesData.strategies);
            console.log(`✅ Loaded ${strategiesData.total_count} strategies`);
        }

        // Apply settings
        if (settingsData.success) {
            applySettings(settingsData.settings);

            // Validate user's selected tokens against Hyperliquid
            await validateSelectedTokens(settingsData.settings.monitored_tokens || []);
        }

    } catch (error) {
        console.error('Error loading settings:', error);
        showValidationMessage('Failed to load settings', 'error');
    }
}

// Validate that selected tokens exist on Hyperliquid
async function validateSelectedTokens(tokens) {
    if (!tokens || tokens.length === 0) return;

    try {
        const response = await fetch('/api/tokens/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tokens: tokens })
        });

        const data = await response.json();

        if (data.success && data.invalid && data.invalid.length > 0) {
            // Show warning for invalid tokens
            const invalidList = data.invalid.join(', ');
            showValidationMessage(
                `Warning: ${data.invalid.length} token(s) not available on Hyperliquid: ${invalidList}. These will be skipped during trading.`,
                'warning'
            );

            // Mark invalid tokens in the UI
            data.invalid.forEach(symbol => {
                const chip = document.querySelector(`.token-chip[data-symbol="${symbol}"]`);
                if (chip) {
                    chip.classList.add('token-invalid');
                    chip.title = 'Not available on Hyperliquid';
                }
            });
        }
    } catch (error) {
        console.error('Error validating tokens:', error);
    }
}

// Apply settings to UI
function applySettings(settings) {
    // Chart settings
    document.getElementById('timeframe-select').value = settings.timeframe || '30m';
    document.getElementById('days-back-select').value = settings.days_back || 2;
    document.getElementById('cycle-time-input').value = settings.sleep_minutes || 30;

    // Mode settings
    const swarmMode = settings.swarm_mode || 'single';
    document.querySelector(`input[name="swarm-mode"][value="${swarmMode}"]`).checked = true;
    updateSwarmModelsVisibility();

    // Confidence thresholds
    document.getElementById('min-single-confidence').value = settings.min_single_confidence || 60;
    document.getElementById('min-swarm-confidence').value = settings.min_swarm_confidence || 65;
    
    // Risk management
    document.getElementById('stop-loss-pct').value = settings.stop_loss_pct || 2.0;
    document.getElementById('take-profit-pct').value = settings.take_profit_pct || 5.0;
    
    // Position sizing
    document.getElementById('max-position-pct').value = settings.max_position_pct || 90;
    document.getElementById('leverage').value = settings.leverage || 20;
    document.getElementById('cash-buffer-pct').value = settings.cash_buffer_pct || 10;
    document.getElementById('starting-balance').value = settings.starting_balance || 10;
    
    // Position management
    document.getElementById('min-age-hours').value = settings.min_age_hours || 0.1;
    document.getElementById('min-close-confidence').value = settings.min_close_confidence || 70;

    // Token settings - tier-based defaults
    if (!settings.monitored_tokens) {
        // Check tier to set appropriate defaults
        const maxTokens = currentTierData?.features?.max_tokens || 5;
        if (maxTokens <= 5) {
            selectedTokens = ['BTC', 'ETH', 'SOL', 'LTC', 'HYPE'];
        } else {
            selectedTokens = ['BTC', 'ETH', 'SOL', 'LTC', 'AAVE', 'HYPE', 'TAO', 'DOGE'];
        }
    } else {
        selectedTokens = settings.monitored_tokens;
    }
    updateTokenSelection();

    // Main model settings - Default to OpenRouter with FREE Llama 3.1 Nemotron 70B
    const defaultProvider = settings.ai_provider || 'openrouter';
    const defaultModel = settings.ai_model || 'nvidia/llama-3.1-nemotron-70b-instruct:free';
    document.getElementById('main-provider-select').value = defaultProvider;
    updateMainModelOptions();
    document.getElementById('main-model-select').value = defaultModel;

    // Temperature and max tokens
    const tempValue = Math.round((settings.ai_temperature || 0.3) * 100);
    document.getElementById('main-temperature').value = tempValue;
    updateSliderValue('main-temperature', 'main-temp-value');

    document.getElementById('main-max-tokens').value = settings.ai_max_tokens || 2000;

    // Swarm models - Start empty, user must add their own
    swarmModels = settings.swarm_models || [];
    renderSwarmModels();
}

// Populate token categories
function populateTokenCategories() {
    const categories = ['crypto', 'altcoins', 'memecoins'];

    categories.forEach(category => {
        const container = document.getElementById(`${category}-tokens`);
        const tokens = availableTokens[category] || [];

        container.innerHTML = tokens.map(token => `
            <div class="token-chip" data-symbol="${token.symbol}" onclick="toggleToken('${token.symbol}')">
                <span class="token-symbol">${token.symbol}</span>
            </div>
        `).join('');
    });
}

// ========================================
// STRATEGY MANAGEMENT
// ========================================

// Render strategies in the settings modal
function renderStrategies(strategies) {
    const container = document.getElementById('strategies-list');

    if (!strategies || strategies.length === 0) {
        container.innerHTML = '<div class="loading-state">No strategies available</div>';
        return;
    }

    container.innerHTML = strategies.map(strategy => {
        const riskClass = `risk-${strategy.risk_level}`;
        const cardClass = strategy.enabled ? '' : 'disabled';
        const timeframes = strategy.recommended_timeframes.join(', ');
        
        // Check if strategy has parameters to show "Edit" button
        const hasParams = strategy.parameters && Object.keys(strategy.parameters).length > 0;

        return `
            <div class="strategy-card ${cardClass}" data-strategy-id="${strategy.id}">
                <div class="strategy-header">
                    <div class="strategy-info">
                        <div class="strategy-name">${strategy.name}</div>
                        <div class="strategy-category">${strategy.category}</div>
                    </div>
                    <div class="strategy-actions">
                        ${hasParams ? `
                            <button class="btn-small btn-edit-params" onclick="openStrategyParams('${strategy.id}', '${strategy.name}')" title="Edit Parameters">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33a1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06-.06a1.65 1.65 0 0 0-.33 1.82a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                            </button>
                        ` : ''}
                        <label class="strategy-toggle">
                            <input type="checkbox"
                                   ${strategy.enabled ? 'checked' : ''}
                                   onchange="toggleStrategy('${strategy.id}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
                <div class="strategy-description">${strategy.description}</div>
                <div class="strategy-meta">
                    <span class="${riskClass}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                        </svg>
                        ${strategy.risk_level} risk
                    </span>
                    <span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12,6 12,12 16,14"></polyline>
                        </svg>
                        ${timeframes}
                    </span>
                </div>
            </div>
        `;
    }).join('');
}

let activeStrategyId = null;

async function openStrategyParams(strategyId, strategyName) {
    activeStrategyId = strategyId;
    document.getElementById('strategy-params-title').textContent = `${strategyName} Parameters`;
    const container = document.getElementById('strategy-params-container');
    container.innerHTML = '<div class="loading-state">Loading parameters...</div>';
    document.getElementById('strategy-params-status').textContent = '';
    
    document.getElementById('strategy-params-modal').classList.add('show');

    try {
        const response = await fetch(`/api/strategies/${strategyId}/parameters`);
        const data = await response.json();

        if (data.success) {
            renderStrategyParams(data.parameters);
        } else {
            container.innerHTML = `<div class="error-message">${data.message}</div>`;
        }
    } catch (error) {
        console.error('Error loading strategy parameters:', error);
        container.innerHTML = '<div class="error-message">Failed to load parameters</div>';
    }
}

function closeStrategyParams(event) {
    if (!event || event.target.id === 'strategy-params-modal' || event.target.classList.contains('modal-close')) {
        document.getElementById('strategy-params-modal').classList.remove('show');
        activeStrategyId = null;
    }
}

function renderStrategyParams(parameters) {
    const container = document.getElementById('strategy-params-container');
    
    if (Object.keys(parameters).length === 0) {
        container.innerHTML = '<div class="info-box">No adjustable parameters for this strategy.</div>';
        return;
    }

    container.innerHTML = Object.entries(parameters).map(([key, config]) => {
        let inputHtml = '';
        const id = `param-${key}`;

        if (config.type === 'number') {
            inputHtml = `
                <div class="input-with-hint">
                    <input type="number" id="${id}" class="setting-input"
                           min="${config.min}" max="${config.max}" step="${config.step}"
                           value="${config.value}" />
                    <span class="input-hint">Range: ${config.min} to ${config.max}</span>
                </div>
            `;
        } else if (config.type === 'boolean') {
            inputHtml = `
                <label class="toggle-switch">
                    <input type="checkbox" id="${id}" ${config.value ? 'checked' : ''} />
                    <span class="toggle-slider"></span>
                </label>
            `;
        } else if (config.type === 'select') {
            inputHtml = `
                <select id="${id}" class="setting-input">
                    ${config.options.map(opt => `
                        <option value="${opt}" ${opt === config.value ? 'selected' : ''}>${opt}</option>
                    `).join('')}
                </select>
            `;
        }

        return `
            <div class="setting-group" data-param-key="${key}">
                <label for="${id}">${config.label}</label>
                ${inputHtml}
            </div>
        `;
    }).join('');
}

async function saveStrategyParameters() {
    if (!activeStrategyId) return;

    const container = document.getElementById('strategy-params-container');
    const statusEl = document.getElementById('strategy-params-status');
    const params = {};

    container.querySelectorAll('.setting-group').forEach(group => {
        const key = group.dataset.paramKey;
        const input = group.querySelector('input, select');
        
        if (input.type === 'checkbox') {
            params[key] = input.checked;
        } else if (input.type === 'number') {
            params[key] = parseFloat(input.value);
        } else {
            params[key] = input.value;
        }
    });

    try {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'validation-message info';

        const response = await fetch(`/api/strategies/${activeStrategyId}/parameters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const data = await response.json();

        if (data.success) {
            statusEl.textContent = 'Parameters saved successfully!';
            statusEl.className = 'validation-message success';
            addConsoleMessage(`Updated ${activeStrategyId} parameters`, 'success');
            setTimeout(() => closeStrategyParams(), 1500);
        } else {
            statusEl.textContent = data.message || 'Failed to save parameters';
            statusEl.className = 'validation-message error';
        }
    } catch (error) {
        console.error('Error saving strategy parameters:', error);
        statusEl.textContent = 'Error saving parameters';
        statusEl.className = 'validation-message error';
    }
}

// Toggle a strategy on/off
async function toggleStrategy(strategyId, enabled) {
    try {
        const response = await fetch(`/api/strategies/${strategyId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: enabled })
        });

        const data = await response.json();

        if (data.success) {
            // Update the card styling
            const card = document.querySelector(`.strategy-card[data-strategy-id="${strategyId}"]`);
            if (card) {
                card.classList.toggle('disabled', !enabled);
            }

            const status = enabled ? 'enabled' : 'disabled';
            console.log(`Strategy '${strategyId}' ${status}`);
            addConsoleMessage(`Strategy '${strategyId}' ${status}`, 'info');
        } else {
            // Revert the toggle if failed
            const checkbox = document.querySelector(`.strategy-card[data-strategy-id="${strategyId}"] input[type="checkbox"]`);
            if (checkbox) {
                checkbox.checked = !enabled;
            }
            showValidationMessage(data.message || 'Failed to toggle strategy', 'error');
        }

    } catch (error) {
        console.error('Error toggling strategy:', error);
        showValidationMessage('Failed to toggle strategy', 'error');

        // Revert the toggle
        const checkbox = document.querySelector(`.strategy-card[data-strategy-id="${strategyId}"] input[type="checkbox"]`);
        if (checkbox) {
            checkbox.checked = !enabled;
        }
    }
}

// Toggle category expand/collapse
function toggleCategory(category) {
    const tokensContainer = document.getElementById(`${category}-tokens`);
    tokensContainer.classList.toggle('collapsed');

    // Update arrow rotation
    const header = tokensContainer.previousElementSibling;
    const arrow = header.querySelector('.category-arrow');
    arrow.style.transform = tokensContainer.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
}

// Toggle token selection
function toggleToken(symbol) {
    const index = selectedTokens.indexOf(symbol);
    if (index === -1) {
        selectedTokens.push(symbol);
    } else {
        selectedTokens.splice(index, 1);
    }
    updateTokenSelection();
}

// Remove token from selection
function removeToken(symbol) {
    const index = selectedTokens.indexOf(symbol);
    if (index !== -1) {
        selectedTokens.splice(index, 1);
        updateTokenSelection();
    }
}

// Update token selection UI
function updateTokenSelection() {
    // Update chips
    document.querySelectorAll('.token-chip').forEach(chip => {
        const symbol = chip.dataset.symbol;
        chip.classList.toggle('selected', selectedTokens.includes(symbol));
    });

    // Update category counts
    const categories = ['crypto', 'altcoins', 'memecoins'];
    categories.forEach(category => {
        const tokens = availableTokens[category] || [];
        const count = tokens.filter(t => selectedTokens.includes(t.symbol)).length;
        document.getElementById(`${category}-count`).textContent = count;
    });

    // Update selected tokens summary
    const summaryContainer = document.getElementById('selected-tokens-list');
    if (selectedTokens.length === 0) {
        summaryContainer.innerHTML = '<span style="color: var(--text-muted); font-size: 12px;">No tokens selected</span>';
    } else {
        summaryContainer.innerHTML = selectedTokens.map(symbol => `
            <div class="selected-token">
                ${symbol}
                <span class="remove-token" onclick="removeToken('${symbol}')">&times;</span>
            </div>
        `).join('');
    }
}

// Populate provider dropdowns
function populateProviderDropdowns() {
    const mainProviderSelect = document.getElementById('main-provider-select');

    mainProviderSelect.innerHTML = availableProviders.map(provider => {
        const displayName = getProviderDisplayName(provider);
        return `<option value="${provider}">${displayName}</option>`;
    }).join('');

    // Set default and update models
    updateMainModelOptions();
}

// Get display name for provider
function getProviderDisplayName(provider) {
    const names = {
        'openrouter': 'OpenRouter',
        'anthropic': 'Anthropic (Claude)',
        'openai': 'OpenAI',
        'gemini': 'Google Gemini',
        'deepseek': 'DeepSeek',
        'xai': 'xAI (Grok)',
        'mistral': 'Mistral AI',
        'cohere': 'Cohere',
        'perplexity': 'Perplexity',
        'groq': 'Grok'
    };
    return names[provider] || provider;
}

// Update main model dropdown based on provider
function updateMainModelOptions() {
    const provider = document.getElementById('main-provider-select').value;
    const modelSelect = document.getElementById('main-model-select');
    const models = availableModels[provider] || {};

    modelSelect.innerHTML = Object.entries(models).map(([modelId, description]) => {
        return `<option value="${modelId}">${provider}/${modelId}</option>`;
    }).join('');
}

// Update slider value display
function updateSliderValue(sliderId, displayId) {
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    display.textContent = (slider.value / 100).toFixed(1);
}

// Update swarm models section visibility
function updateSwarmModelsVisibility() {
    const swarmMode = document.querySelector('input[name="swarm-mode"]:checked').value;
    const swarmSection = document.getElementById('swarm-models-section');
    swarmSection.classList.toggle('active', swarmMode === 'swarm');
}

// Listen for mode changes
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[name="swarm-mode"]').forEach(radio => {
        radio.addEventListener('change', updateSwarmModelsVisibility);
    });
});

// Render swarm models
function renderSwarmModels() {
    const container = document.getElementById('swarm-models-list');

    container.innerHTML = swarmModels.map((model, index) => `
        <div class="swarm-model-card" data-index="${index}">
            <div class="swarm-model-header">
                <span class="swarm-model-number">Model ${index + 1}</span>
                ${swarmModels.length > 1 ? `
                    <button class="btn-remove-model" onclick="removeSwarmModel(${index})">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                ` : ''}
            </div>
            <div class="setting-row">
                <div class="setting-group half">
                    <label>Provider</label>
                    <select class="setting-input swarm-provider" data-index="${index}" onchange="updateSwarmModelOptions(${index})">
                        ${availableProviders.map(p => `
                            <option value="${p}" ${p === model.provider ? 'selected' : ''}>${getProviderDisplayName(p)}</option>
                        `).join('')}
                    </select>
                </div>
                <div class="setting-group half">
                    <label>Model</label>
                    <select class="setting-input swarm-model" data-index="${index}">
                        ${Object.entries(availableModels[model.provider] || {}).map(([id, desc]) => `
                            <option value="${id}" ${id === model.model ? 'selected' : ''}>${desc}</option>
                        `).join('')}
                    </select>
                </div>
            </div>
            <div class="setting-row">
                <div class="setting-group half">
                    <label>Temperature</label>
                    <div class="slider-container">
                        <input type="range" class="setting-slider swarm-temp" data-index="${index}" min="0" max="100" value="${Math.round(model.temperature * 100)}" oninput="updateSwarmSliderValue(${index})" />
                        <span class="slider-value" id="swarm-temp-${index}">${model.temperature.toFixed(1)}</span>
                    </div>
                </div>
                <div class="setting-group half">
                    <label>Max Tokens</label>
                    <input type="number" class="setting-input swarm-max-tokens" data-index="${index}" min="100" max="100000" value="${model.max_tokens}" />
                </div>
            </div>
        </div>
    `).join('');

    // Update add button state
    const addBtn = document.getElementById('add-model-btn');
    addBtn.disabled = swarmModels.length >= 6;
}

// Update swarm model options
function updateSwarmModelOptions(index) {
    const providerSelect = document.querySelector(`.swarm-provider[data-index="${index}"]`);
    const modelSelect = document.querySelector(`.swarm-model[data-index="${index}"]`);
    const provider = providerSelect.value;
    const models = availableModels[provider] || {};

    modelSelect.innerHTML = Object.entries(models).map(([id, desc]) => `
        <option value="${id}">${desc}</option>
    `).join('');

    // Update swarm models array
    swarmModels[index].provider = provider;
    swarmModels[index].model = Object.keys(models)[0] || '';
}

// Update swarm slider value
function updateSwarmSliderValue(index) {
    const slider = document.querySelector(`.swarm-temp[data-index="${index}"]`);
    const display = document.getElementById(`swarm-temp-${index}`);
    display.textContent = (slider.value / 100).toFixed(1);
}

// Add new swarm model
function addSwarmModel() {
    if (swarmModels.length >= 6) return;

    swarmModels.push({
        provider: 'openrouter',
        model: 'nex-agi/deepseek-v3.1-nex-n1:free',
        temperature: 0.3,
        max_tokens: 2000
    });

    renderSwarmModels();
}

// Remove swarm model
function removeSwarmModel(index) {
    if (swarmModels.length <= 1) return;
    swarmModels.splice(index, 1);
    renderSwarmModels();
}

// Collect swarm models from UI
function collectSwarmModels() {
    const models = [];
    document.querySelectorAll('.swarm-model-card').forEach((card, index) => {
        const provider = card.querySelector('.swarm-provider').value;
        const model = card.querySelector('.swarm-model').value;
        const tempSlider = card.querySelector('.swarm-temp');
        const maxTokens = card.querySelector('.swarm-max-tokens').value;

        models.push({
            provider: provider,
            model: model,
            temperature: parseFloat((tempSlider.value / 100).toFixed(1)),
            max_tokens: parseInt(maxTokens)
        });
    });
    return models;
}

// Show validation message
function showValidationMessage(message, type) {
    const el = document.getElementById('settings-validation');
    el.textContent = message;
    el.className = `validation-message ${type}`;

    if (type === 'success') {
        setTimeout(() => {
            el.className = 'validation-message';
        }, 3000);
    }
}

// Save all settings
async function saveSettings() {
    // Validate
    if (selectedTokens.length === 0) {
        showValidationMessage('Please select at least one token', 'error');
        return;
    }

    const cycleTime = parseInt(document.getElementById('cycle-time-input').value);
    if (cycleTime < 1 || cycleTime > 1440) {
        showValidationMessage('Cycle time must be between 1 and 1440 minutes', 'error');
        return;
    }

    const maxTokens = parseInt(document.getElementById('main-max-tokens').value);
    if (maxTokens < 100 || maxTokens > 100000) {
        showValidationMessage('Max tokens must be between 100 and 100,000', 'error');
        return;
    }

    // Collect settings
    const settings = {
        // Chart settings
        timeframe: document.getElementById('timeframe-select').value,
        days_back: parseInt(document.getElementById('days-back-select').value),
        sleep_minutes: cycleTime,

        // Mode settings
        swarm_mode: document.querySelector('input[name="swarm-mode"]:checked').value,

        // Token settings
        monitored_tokens: selectedTokens,

        // Main AI model settings
        ai_provider: document.getElementById('main-provider-select').value,
        ai_model: document.getElementById('main-model-input').value || document.getElementById('main-model-select').value,
        ai_temperature: parseFloat((document.getElementById('main-temperature').value / 100).toFixed(1)),
        ai_max_tokens: maxTokens,

        // Swarm models
        swarm_models: collectSwarmModels(),

        // Risk Management Settings
        min_single_confidence: parseInt(document.getElementById('min-single-confidence').value),
        min_swarm_confidence: parseInt(document.getElementById('min-swarm-confidence').value),
        stop_loss_pct: parseFloat(document.getElementById('stop-loss-pct').value),
        take_profit_pct: parseFloat(document.getElementById('take-profit-pct').value),
        max_position_pct: parseInt(document.getElementById('max-position-pct').value),
        leverage: parseInt(document.getElementById('leverage').value),
        cash_buffer_pct: parseInt(document.getElementById('cash-buffer-pct').value),
        min_age_hours: parseFloat(document.getElementById('min-age-hours').value),
        min_close_confidence: parseInt(document.getElementById('min-close-confidence').value)
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.success) {
            showValidationMessage('Settings saved successfully', 'success');
            addConsoleMessage('Settings saved successfully', 'success');
            setTimeout(() => closeSettings(), 1500);
        } else {
            // Check if this is a tier limit error
            if (data.tier_error && data.errors && data.errors.length > 0) {
                showTierUpgradePrompt(data.errors);
            } else {
                showValidationMessage(data.message || 'Failed to save settings', 'error');
            }
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showValidationMessage('Failed to save settings', 'error');
    }
}

// Show tier upgrade prompt when settings exceed limits
function showTierUpgradePrompt(errors) {
    const errorList = errors.map(e => `• ${e}`).join('\n');
    const message = `Your current plan doesn't support these settings:\n\n${errorList}\n\nUpgrade your plan to unlock these features?`;

    if (confirm(message)) {
        // Close settings modal and open account modal to plan tab
        closeSettings();
        openAccountModal();
        setTimeout(() => switchAccountTab('plan'), 100);
    }
}

// ============================================================================
// LOGOUT
// ============================================================================

async function logout() {
    try {
        const response = await fetch('/api/logout', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            // Redirect to login page
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Logout error:', error);
        // Redirect anyway
        window.location.href = '/login';
    }
}

// ============================================================================
// PORTFOLIO CHART
// ============================================================================

async function updatePortfolioChart() {
    try {
        const response = await fetch('/api/history');
        const history = await response.json();

        if (!history || history.length === 0) {
            document.getElementById('portfolio-chart').innerHTML = 'No portfolio data yet';
            return;
        }

        // Calculate portfolio change
        const startBalance = history[0].balance;
        const currentBalance = history[history.length - 1].balance;
        const change = ((currentBalance - startBalance) / startBalance) * 100;

        const badge = document.getElementById('portfolio-change');
        badge.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
        badge.className = `badge ${change >= 0 ? 'positive' : 'negative'}`;

        // Render simple ASCII chart
        renderPortfolioChart(history);

    } catch (error) {
        console.error('Error updating portfolio chart:', error);
    }
}

function renderPortfolioChart(history) {
    const container = document.getElementById('portfolio-chart');

    // Extract balance values
    const values = history.map(h => h.balance);
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = max - min;

    if (range === 0) {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Balance: $${values[0].toFixed(2)} (No change)</div>`;
        return;
    }

    // SVG dimensions
    const width = 600;
    const height = 120;
    const padding = 10;

    // Calculate points for the line
    const points = values.map((val, i) => {
        const x = (i / (values.length - 1)) * (width - padding * 2) + padding;
        const y = height - padding - ((val - min) / range) * (height - padding * 2);
        return { x, y };
    });

    // Create smooth path using quadratic bezier curves
    let pathD = `M ${points[0].x} ${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const curr = points[i];
        const cpx = (prev.x + curr.x) / 2;
        const cpy = (prev.y + curr.y) / 2;
        pathD += ` Q ${prev.x} ${prev.y} ${cpx} ${cpy}`;
    }
    pathD += ` L ${points[points.length - 1].x} ${points[points.length - 1].y}`;

    // Create area fill path (for gradient)
    let areaD = pathD + ` L ${width - padding} ${height} L ${padding} ${height} Z`;

    // Determine color based on trend
    const trend = values[values.length - 1] >= values[0];
    const lineColor = trend ? 'var(--accent-green)' : 'var(--accent-red)';
    const gradientId = trend ? 'gradient-green' : 'gradient-red';

    container.innerHTML = `
        <svg width="100%" height="120" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="display: block;">
            <defs>
                <linearGradient id="gradient-green" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color: rgba(0, 255, 136, 0.3); stop-opacity: 1" />
                    <stop offset="100%" style="stop-color: rgba(0, 255, 136, 0); stop-opacity: 0" />
                </linearGradient>
                <linearGradient id="gradient-red" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color: rgba(255, 71, 87, 0.3); stop-opacity: 1" />
                    <stop offset="100%" style="stop-color: rgba(255, 71, 87, 0); stop-opacity: 0" />
                </linearGradient>
            </defs>

            <!-- Gradient fill under line -->
            <path d="${areaD}" fill="url(#${gradientId})" opacity="0.5"/>

            <!-- Main line -->
            <path d="${pathD}"
                  fill="none"
                  stroke="${lineColor}"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  filter="drop-shadow(0 0 3px ${lineColor})"
                  opacity="0.9"/>

            <!-- End point indicator -->
            <circle cx="${points[points.length - 1].x}"
                    cy="${points[points.length - 1].y}"
                    r="3"
                    fill="${lineColor}"
                    filter="drop-shadow(0 0 4px ${lineColor})"/>
        </svg>
    `;
}

// ============================================================================
// MENU TOGGLE
// ============================================================================

function toggleMenu() {
    const menu = document.getElementById('dropdown-menu');
    menu.classList.toggle('show');
}

// Close menu when clicking outside
document.addEventListener('click', (event) => {
    const menu = document.getElementById('dropdown-menu');
    const menuButton = event.target.closest('.icon-btn[onclick*="toggleMenu"]');

    if (!menu.contains(event.target) && !menuButton) {
        menu.classList.remove('show');
    }
});

// ============================================================================
// TIMEZONE MODAL
// ============================================================================

function openTimezoneModal() {
    document.getElementById('timezone-modal').classList.add('show');
    // Load current timezone
    const savedTimezone = localStorage.getItem('preferred_timezone') || 'local';
    document.getElementById('timezone-select').value = savedTimezone;
}

function closeTimezoneModal(event) {
    if (!event || event.target.id === 'timezone-modal' || event.target.classList.contains('modal-close')) {
        document.getElementById('timezone-modal').classList.remove('show');
    }
}

function confirmTimezone() {
    const select = document.getElementById('timezone-select');
    const selectedZone = select.value;
    localStorage.setItem('preferred_timezone', selectedZone);
    updateTimestamp(); // Refresh timestamp immediately
    updateConsole(); // Refresh console with new timezone
    closeTimezoneModal();
}

// ============================================================================
// ACCOUNT MODAL
// ============================================================================

// Global state for secrets
let providersData = {};

function openAccountModal() {
    const modal = document.getElementById('account-modal');
    modal.classList.add('show');

    // Reset to profile tab
    switchAccountTab('profile');

    // Load account data
    loadAccountProfile();
}

function closeAccountModal(event) {
    if (!event || event.target.id === 'account-modal' || event.target.classList.contains('modal-close')) {
        document.getElementById('account-modal').classList.remove('show');
    }
}

// Tab switching for account modal
function switchAccountTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('#account-modal .settings-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('#account-modal .settings-tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `account-tab-${tabName}`);
    });

    // Load secrets when switching to secrets tab
    if (tabName === 'secrets') {
        loadSecrets();
    }

    // Load tier info when switching to plan tab
    if (tabName === 'plan') {
        loadTierInfo();
    }
}

// Load account profile data
function loadAccountProfile() {
    const username = sessionStorage.getItem('username') || 'User';
    const email = sessionStorage.getItem('email') || 'user@example.com';

    document.getElementById('account-username').textContent = username;
    document.getElementById('account-email').textContent = email;

    // Load current model from settings
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.settings) {
                const provider = data.settings.ai_provider || 'gemini';
                const model = data.settings.ai_model || 'gemini-2.5-flash';
                document.getElementById('account-current-model').textContent = `${provider}/${model}`;
            }
        })
        .catch(error => {
            console.error('Error loading settings:', error);
        });

    // Calculate all-time PnL from history
    fetch('/api/history')
        .then(response => response.json())
        .then(history => {
            if (history && history.length > 0) {
                const startBalance = history[0].balance;
                const currentBalance = history[history.length - 1].balance;
                const totalPnl = currentBalance - startBalance;

                const pnlEl = document.getElementById('account-total-pnl');
                
                // Get current starting balance for the profile view too
                const startingBalanceInput = document.getElementById('starting-balance');
                const startingBalance = (startingBalanceInput && startingBalanceInput.value) ? parseFloat(startingBalanceInput.value) : 10;
                const pnlPct = ((totalPnl / startingBalance) * 100).toFixed(2);
                
                pnlEl.textContent = `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)} (${totalPnl >= 0 ? '+' : ''}${pnlPct}%)`;
                pnlEl.className = `stat-value pnl ${totalPnl >= 0 ? 'positive' : 'negative'}`;
            }
        })
        .catch(error => {
            console.error('Error loading PnL:', error);
        });
}

// ============================================================================
// SECRETS MANAGEMENT (BYOK)
// ============================================================================

async function loadSecrets() {
    const container = document.getElementById('secrets-list');
    container.innerHTML = '<div class="loading-secrets">Loading API keys...</div>';

    try {
        const response = await fetch('/api/secrets');
        const data = await response.json();

        if (data.success) {
            providersData = data.providers;
            renderSecretsList();
        } else {
            container.innerHTML = '<div class="error-message">Failed to load API keys</div>';
        }
    } catch (error) {
        console.error('Error loading secrets:', error);
        container.innerHTML = '<div class="error-message">Failed to load API keys</div>';
    }
}

function renderSecretsList() {
    const container = document.getElementById('secrets-list');

    const providersHtml = Object.entries(providersData).map(([providerId, info]) => {
        const statusClass = info.configured ? 'configured' : 'not-configured';
        const statusText = info.configured ? 'Configured' : 'Not configured';
        const sourceLabel = info.source === 'env' ? '(from .env)' : '';

        return `
            <div class="secret-item ${statusClass}" data-provider="${providerId}">
                <div class="secret-header">
                    <div class="secret-info">
                        <span class="secret-name">${info.name}</span>
                        <span class="secret-status ${statusClass}">${statusText} ${sourceLabel}</span>
                    </div>
                    <div class="secret-actions">
                        ${info.configured ? `
                            <button class="btn-secret-action btn-view" onclick="toggleSecretInput('${providerId}')" title="Edit">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
                            </button>
                            <button class="btn-secret-action btn-delete" onclick="deleteSecret('${providerId}')" title="Delete">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                            </button>
                        ` : `
                            <button class="btn-secret-action btn-add" onclick="toggleSecretInput('${providerId}')" title="Add">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                            </button>
                        `}
                    </div>
                </div>
                <div class="secret-input-row" id="secret-input-${providerId}" style="display: none;">
                    <div class="secret-input-group">
                        <input type="password"
                               class="setting-input secret-key-input"
                               id="input-${providerId}"
                               placeholder="${info.placeholder}"
                               ${info.configured ? `value="${info.masked_key}"` : ''} />
                        <button class="btn-toggle-visibility" onclick="toggleSecretVisibility('${providerId}')" title="Show/Hide">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        </button>
                    </div>
                    <div class="secret-input-actions">
                        <button class="btn btn-small btn-save" onclick="saveSecret('${providerId}')">Save</button>
                        <button class="btn btn-small btn-cancel" onclick="toggleSecretInput('${providerId}')">Cancel</button>
                        <a href="${info.docs_url}" target="_blank" class="btn btn-small btn-docs" title="Get API Key">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                            Get Key
                        </a>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = providersHtml;
}

function toggleSecretInput(providerId) {
    const inputRow = document.getElementById(`secret-input-${providerId}`);
    const isVisible = inputRow.style.display !== 'none';

    // Hide all other input rows first
    document.querySelectorAll('.secret-input-row').forEach(row => {
        row.style.display = 'none';
    });

    // Toggle this one
    if (!isVisible) {
        inputRow.style.display = 'block';
        // Clear the input if not configured
        const input = document.getElementById(`input-${providerId}`);
        if (!providersData[providerId].configured) {
            input.value = '';
        }
        input.focus();
    }
}

function toggleSecretVisibility(providerId) {
    const input = document.getElementById(`input-${providerId}`);
    input.type = input.type === 'password' ? 'text' : 'password';
}

async function saveSecret(providerId) {
    const input = document.getElementById(`input-${providerId}`);
    const apiKey = input.value.trim();

    if (!apiKey) {
        showSecretsValidation('Please enter an API key', 'error');
        return;
    }

    // Don't save if it's just the masked key
    if (apiKey.includes('*')) {
        showSecretsValidation('Please enter a new API key (not the masked one)', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/secrets/${providerId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        const data = await response.json();

        if (data.success) {
            showSecretsValidation(`${providersData[providerId].name} key saved successfully`, 'success');
            // Reload the secrets list
            await loadSecrets();
        } else {
            showSecretsValidation(data.message || 'Failed to save API key', 'error');
        }
    } catch (error) {
        console.error('Error saving secret:', error);
        showSecretsValidation('Failed to save API key', 'error');
    }
}

async function deleteSecret(providerId) {
    if (!confirm(`Are you sure you want to delete the ${providersData[providerId].name} API key?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/secrets/${providerId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showSecretsValidation(`${providersData[providerId].name} key removed`, 'success');
            // Reload the secrets list
            await loadSecrets();
        } else {
            showSecretsValidation(data.message || 'Failed to remove API key', 'error');
        }
    } catch (error) {
        console.error('Error deleting secret:', error);
        showSecretsValidation('Failed to remove API key', 'error');
    }
}

function showSecretsValidation(message, type) {
    const el = document.getElementById('secrets-validation');
    el.textContent = message;
    el.className = `validation-message ${type}`;

    if (type === 'success') {
        setTimeout(() => {
            el.className = 'validation-message';
        }, 3000);
    }
}

// ============================================================================
// TIER / PLAN MANAGEMENT
// ============================================================================

let currentTierData = null;

async function loadTierInfo() {
    try {
        const response = await fetch('/api/tier');

        // Handle authentication redirect
        if (response.status === 401) {
            console.log('User not authenticated, skipping tier info load');
            return;
        }

        const data = await response.json();

        if (data.success) {
            currentTierData = data;
            renderTierUI(data);
        } else {
            console.error('Failed to load tier info:', data.error || data.message);
        }
    } catch (error) {
        console.error('Error loading tier info:', error);
    }
}

function renderTierUI(data) {
    const currentTier = data.tier;
    const isAdmin = data.is_admin;
    const features = data.features;

    // Update current plan display
    const currentPlanName = document.getElementById('current-plan-name');
    if (currentPlanName) {
        const tierNames = {
            'based': 'Based (Free)',
            'trader': 'Trader',
            'pro': 'Pro'
        };
        currentPlanName.textContent = tierNames[currentTier] || currentTier;
        currentPlanName.className = `current-plan-name tier-${currentTier}`;
    }

    // Update plan cards
    document.querySelectorAll('.plan-card').forEach(card => {
        const tier = card.dataset.tier;
        card.classList.toggle('current', tier === currentTier);

        // Update select button
        const btn = card.querySelector('.btn-select-plan');
        if (btn) {
            if (tier === currentTier) {
                btn.textContent = 'Current Plan';
                btn.classList.add('active');
                btn.disabled = true;
            } else if (isAdmin) {
                btn.textContent = 'Select Plan';
                btn.classList.remove('active');
                btn.disabled = false;
            } else {
                // Non-admin users see upgrade/downgrade buttons
                const tierOrder = ['based', 'trader', 'pro'];
                const currentIdx = tierOrder.indexOf(currentTier);
                const targetIdx = tierOrder.indexOf(tier);

                if (targetIdx > currentIdx) {
                    btn.textContent = 'Upgrade';
                    btn.classList.remove('active');
                    btn.disabled = false;
                } else {
                    btn.textContent = 'Downgrade';
                    btn.classList.remove('active');
                    btn.disabled = false;
                }
            }
        }
    });

    // Show/hide admin notice
    const adminNotice = document.getElementById('admin-tier-notice');
    if (adminNotice) {
        adminNotice.style.display = isAdmin ? 'flex' : 'none';
    }

    // Apply tier limits to main dashboard UI
    applyTierLimits(features, currentTier);
}

async function selectTier(tier) {
    if (!currentTierData || !currentTierData.is_admin) {
        // Non-admin users would go to payment flow
        showTierUpgradeModal(tier);
        return;
    }

    // Admin users can directly switch tiers for testing
    try {
        const response = await fetch('/api/tier', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tier: tier })
        });

        const data = await response.json();
        if (data.success) {
            console.log(`✅ Tier changed to ${tier}`);
            loadTierInfo(); // Refresh UI
        } else {
            console.error('Failed to change tier:', data.error);
            alert('Failed to change tier: ' + data.error);
        }
    } catch (error) {
        console.error('Error changing tier:', error);
        alert('Error changing tier');
    }
}

function showTierUpgradeModal(tier) {
    // For non-admin users, show upgrade prompt
    const tierPrices = {
        'trader': '$5/month',
        'pro': '$20/month'
    };

    const message = tier === 'based'
        ? 'Are you sure you want to downgrade to the free tier?'
        : `Upgrade to ${tier.charAt(0).toUpperCase() + tier.slice(1)} for ${tierPrices[tier]}?\n\n(Payment integration coming soon)`;

    alert(message);
}

function applyTierLimits(features, tier) {
    // Apply visual locks to UI elements based on tier

    // Swarm mode radio buttons (name="swarm-mode")
    const swarmRadios = document.querySelectorAll('input[name="swarm-mode"]');
    const swarmSection = document.getElementById('swarm-models-section');

    swarmRadios.forEach(radio => {
        const container = radio.closest('.mode-option');
        if (radio.value === 'swarm' && !features.swarm_mode) {
            // Lock swarm option
            radio.disabled = true;
            if (container) container.classList.add('feature-locked');
        } else {
            radio.disabled = false;
            if (container) container.classList.remove('feature-locked');
        }
    });

    // Also lock swarm models section if not allowed
    if (swarmSection && !features.swarm_mode) {
        swarmSection.classList.add('feature-locked');
    } else if (swarmSection) {
        swarmSection.classList.remove('feature-locked');
    }

    // BYOK section - only lock for 'based' tier
    const secretsSection = document.getElementById('secrets-list');
    if (secretsSection && !features.byok) {
        const byokNotice = document.createElement('div');
        byokNotice.className = 'tier-validation warning';
        byokNotice.innerHTML = '🔒 BYOK (Bring Your Own Key) requires Trader tier or higher';
        byokNotice.id = 'byok-tier-notice';

        // Only add if not already there
        if (!document.getElementById('byok-tier-notice')) {
            secretsSection.parentNode.insertBefore(byokNotice, secretsSection);
        }
    } else {
        const existingNotice = document.getElementById('byok-tier-notice');
        if (existingNotice) existingNotice.remove();
    }

    // Token limit indicator
    updateTokenLimitIndicator(features.max_tokens);

    // Provider restrictions for based tier
    updateProviderRestrictions(features.providers, tier);
}

function updateTokenLimitIndicator(maxTokens) {
    // Remove existing badge
    const existingBadge = document.querySelector('.token-limit-badge');
    if (existingBadge) existingBadge.remove();

    // Find the Token Selection section title
    const tokenTab = document.getElementById('tab-token');
    if (!tokenTab) return;

    const sectionTitle = tokenTab.querySelector('.section-title');
    if (!sectionTitle) return;

    // Add limit badge if not unlimited
    if (maxTokens < 999) {
        const badge = document.createElement('span');
        badge.className = 'token-limit-badge';
        badge.innerHTML = `Max: ${maxTokens} tokens`;
        sectionTitle.appendChild(badge);
    }
}

function updateProviderRestrictions(allowedProviders, tier) {
    const providerSelect = document.getElementById('main-provider-select');
    if (!providerSelect) return;

    // For 'based' tier, disable non-free providers
    if (tier === 'based' && Array.isArray(allowedProviders)) {
        Array.from(providerSelect.options).forEach(option => {
            const provider = option.value;
            if (!allowedProviders.includes(provider)) {
                option.disabled = true;
                if (!option.textContent.includes('(BYOK Required)')) {
                    option.textContent = option.textContent + ' (BYOK Required)';
                }
            } else {
                option.disabled = false;
                option.textContent = option.textContent.replace(' (BYOK Required)', '');
            }
        });
    } else {
        // Enable all providers for paid tiers
        Array.from(providerSelect.options).forEach(option => {
            option.disabled = false;
            option.textContent = option.textContent.replace(' (BYOK Required)', '');
        });
    }
}

// Validate settings against tier before saving
async function validateSettingsForTier(settings) {
    try {
        const response = await fetch('/api/tier/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error validating settings:', error);
        return { valid: true, errors: [] }; // Allow on error
    }
}

console.log('✅ Dashboard ready');
