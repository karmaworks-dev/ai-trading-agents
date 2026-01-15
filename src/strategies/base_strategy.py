"""
🕉️ Karma Dev's Base Strategy Class
All custom strategies should inherit from this
"""

class BaseStrategy:
    def __init__(self, name: str):
        self.name = name

    def generate_signals(self) -> dict:
        """
        Generate trading signals
        Returns:
            dict: {
                'token': str,          # Token address
                'signal': float,       # Signal strength (0-1)
                'direction': str,      # 'BUY', 'SELL', or 'NEUTRAL'
                'metadata': dict       # Optional strategy-specific data
            }
        """
        raise NotImplementedError("Strategy must implement generate_signals()")

    def validate_signal(self, signal: dict) -> bool:
        """Validate signal format and values"""
        required_fields = ['token', 'signal', 'direction', 'metadata']
        
        # Check required fields
        for field in required_fields:
            if field not in signal:
                return False
        
        # Validate signal strength
        if not (0 <= signal['signal'] <= 1):
            return False
        
        # Validate direction
        if signal['direction'] not in ['BUY', 'SELL', 'NEUTRAL']:
            return False
        
        return True

    def format_metadata(self, metadata: dict) -> dict:
        """Format metadata for consistency"""
        formatted = metadata.copy()
        
        # Convert numeric values to float
        for key, value in formatted.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                formatted[key] = float(value)
        
        # Add strategy identifier
        formatted['strategy_id'] = self.name
        
        return formatted