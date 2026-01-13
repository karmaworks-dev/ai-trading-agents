document.addEventListener("DOMContentLoaded", function() {
    const socket = io.connect(location.protocol + "//" + document.domain + ":" + location.port);

    socket.on("connect", function() {
        console.log("Connected to WebSocket");
    });

    socket.on("update", function(data) {
        updateAccountSummary(data.account_summary);
    });

    function updateAccountSummary(summary) {
        if (!summary) {
            console.error("Received empty account summary");
            return;
        }

        const summaryDiv = document.getElementById("account-summary");
        if (summaryDiv) {
            summaryDiv.innerHTML = `
                <h3>Account Summary</h3>
                <p>Total Value: ${summary.total_value}</p>
                <p>Total PnL: <span class="${summary.total_pnl_raw >= 0 ? 'text-success' : 'text-danger'}">${summary.total_pnl_raw} (${summary.total_pnl_pct}%)</span></p>
            `;
        }
    }
});
