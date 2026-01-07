"""
Compact Pattern Database Integration for Trading Agent
Integrates the compact pattern database with the existing agent memory system
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Import the compact pattern database
from src.patterns.compact_database import get_pattern_database, PatternExample
from src.data.ohlcv_collector import collect_all_tokens
from src.config import EXCHANGE, HYPERLIQUID_SYMBOLS

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseIntegration:
    """Integrates compact pattern database with trading agent"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize database integration"""
        self.pattern_db = get_pattern_database(data_dir)
        self.exchange = EXCHANGE
        self.symbols = HYPERLIQUID_SYMBOLS
        
        logger.info("Database Integration initialized")
    
    async def enhanced_preparation_with_database(self, current_patterns: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Enhanced preparation phase using compact pattern database
        
        Args:
            current_patterns: Detected patterns from pattern scanner
            
        Returns:
            Enhanced preparation results with database insights
        """
        try:
            logger.info("Starting enhanced preparation with pattern database")
            
            pattern_recommendations = []
            
            # Process each detected pattern
            for symbol, patterns in current_patterns.items():
                for pattern in patterns:
                    try:
                        # Get current market context
                        current_context = await self._get_current_context(symbol)
                        
                        # Get optimal parameters from database
                        optimal_params = self.pattern_db.get_optimal_parameters(
                            pattern["type"], 
                            current_context
                        )
                        
                        # Get similar successful examples
                        similar_examples = self.pattern_db.get_similar_examples(
                            pattern["type"],
                            current_context,
                            limit=3
                        )
                        
                        # Calculate confidence boost from database
                        confidence_boost = self._calculate_database_confidence_boost(
                            pattern["type"], similar_examples
                        )
                        
                        # Generate database recommendation
                        database_recommendation = self._generate_database_recommendation(
                            pattern, optimal_params, similar_examples
                        )
                        
                        pattern_recommendations.append({
                            "symbol": symbol,
                            "pattern": pattern,
                            "optimal_parameters": optimal_params,
                            "similar_examples": similar_examples,
                            "confidence_boost": confidence_boost,
                            "database_recommendation": database_recommendation
                        })
                        
                        logger.debug(f"Processed {pattern['type']} for {symbol}")
                        
                    except Exception as e:
                        logger.error(f"Error processing pattern {pattern.get('type', 'unknown')} for {symbol}: {e}")
                        continue
            
            # Create enhanced preparation prompt
            prep_prompt = self._create_compact_database_prompt(pattern_recommendations)
            
            # Get database statistics for context
            db_stats = self.pattern_db.get_database_stats()
            
            return {
                "pattern_recommendations": pattern_recommendations,
                "enhanced_prompt": prep_prompt,
                "database_stats": db_stats,
                "total_patterns": len(pattern_recommendations)
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced preparation with database: {e}")
            return {
                "pattern_recommendations": [],
                "enhanced_prompt": "",
                "database_stats": {},
                "total_patterns": 0
            }
    
    async def _get_current_context(self, symbol: str) -> Dict[str, Any]:
        """Get current market context for symbol"""
        try:
            # Get current market data
            market_data = await self._get_market_data(symbol)
            
            # Analyze current market conditions
            current_context = {
                "market_trend": self._analyze_market_trend(market_data),
                "volatility": self._calculate_volatility(market_data),
                "volume_confirmation": self._calculate_volume_confirmation(market_data),
                "time_of_day": datetime.now().strftime("%H:%M"),
                "symbol": symbol,
                "timeframe": "15m"
            }
            
            return current_context
            
        except Exception as e:
            logger.error(f"Error getting current context for {symbol}: {e}")
            return {
                "market_trend": "unknown",
                "volatility": 0.02,
                "volume_confirmation": 1.0,
                "time_of_day": "12:00",
                "symbol": symbol,
                "timeframe": "15m"
            }
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get current market data for symbol"""
        try:
            # Use existing market data collection
            from src.data.ohlcv_collector import collect_token_data
            
            market_data = collect_token_data(symbol)
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {}
    
    def _analyze_market_trend(self, market_data: Dict[str, Any]) -> str:
        """Analyze current market trend"""
        try:
            if not market_data or "close" not in market_data:
                return "unknown"
            
            # Calculate trend based on moving averages
            closes = market_data["close"].tolist() if hasattr(market_data["close"], "tolist") else list(market_data["close"])
            
            if len(closes) < 20:
                return "unknown"
            
            # Simple moving average analysis
            sma_20 = sum(closes[-20:]) / 20
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
            
            current_price = closes[-1]
            
            if current_price > sma_20 > sma_50:
                return "bullish"
            elif current_price < sma_20 < sma_50:
                return "bearish"
            elif sma_20 > sma_50 and current_price < sma_20:
                return "bullish_to_bearish"
            elif sma_20 < sma_50 and current_price > sma_20:
                return "bearish_to_bullish"
            else:
                return "ranging"
                
        except Exception as e:
            logger.error(f"Error analyzing market trend: {e}")
            return "unknown"
    
    def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:
        """Calculate current volatility"""
        try:
            if not market_data or "close" not in market_data:
                return 0.02
            
            closes = market_data["close"].tolist() if hasattr(market_data["close"], "tolist") else list(market_data["close"])
            
            if len(closes) < 14:
                return 0.02
            
            # Calculate ATR-like volatility
            returns = []
            for i in range(1, min(len(closes), 14)):
                if closes[i-1] != 0:
                    returns.append(abs(closes[i] - closes[i-1]) / closes[i-1])
            
            if not returns:
                return 0.02
            
            return sum(returns) / len(returns)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.02
    
    def _calculate_volume_confirmation(self, market_data: Dict[str, Any]) -> float:
        """Calculate volume confirmation factor"""
        try:
            if not market_data or "volume" not in market_data:
                return 1.0
            
            volumes = market_data["volume"].tolist() if hasattr(market_data["volume"], "tolist") else list(market_data["volume"])
            
            if len(volumes) < 14:
                return 1.0
            
            # Calculate average volume
            avg_volume = sum(volumes[-14:]) / 14
            current_volume = volumes[-1] if volumes else 1.0
            
            if avg_volume == 0:
                return 1.0
            
            return current_volume / avg_volume
            
        except Exception as e:
            logger.error(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _calculate_database_confidence_boost(self, pattern_type: str, similar_examples: List[Dict]) -> float:
        """Calculate confidence boost from database examples"""
        try:
            if not similar_examples:
                return 0.0
            
            # Calculate average quality score of similar examples
            quality_scores = [ex.get("quality_score", 0.5) for ex in similar_examples]
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # Calculate success rate of similar examples
            success_count = sum(1 for ex in similar_examples if ex.get("result") == "SUCCESS")
            success_rate = success_count / len(similar_examples) if similar_examples else 0.0
            
            # Combine quality and success rate for confidence boost
            confidence_boost = (avg_quality * 0.6 + success_rate * 0.4) * 0.15  # Max 15% boost
            
            return confidence_boost
            
        except Exception as e:
            logger.error(f"Error calculating database confidence boost: {e}")
            return 0.0
    
    def _generate_database_recommendation(self, pattern: Dict[str, Any], 
                                        optimal_params: Dict[str, Any], 
                                        similar_examples: List[Dict]) -> str:
        """Generate database-based recommendation for pattern"""
        try:
            recommendation_parts = []
            
            # Add pattern type and confidence
            pattern_type = pattern.get("type", "unknown")
            pattern_confidence = pattern.get("confidence", 0.5)
            
            recommendation_parts.append(f"Pattern: {pattern_type} (confidence: {pattern_confidence:.1%})")
            
            # Add optimal parameters
            if optimal_params:
                entry_timing = optimal_params.get("entry_timing", "immediate")
                position_size = optimal_params.get("position_size", 1000.0)
                risk_reward = optimal_params.get("risk_reward", 2.0)
                
                recommendation_parts.append(f"Recommendation: {entry_timing} entry with ${position_size:,.0f} position")
                recommendation_parts.append(f"Risk/Reward: {risk_reward:.1f}:1")
            
            # Add insights from similar examples
            if similar_examples:
                avg_profit = sum(ex.get("profit_pct", 0) for ex in similar_examples) / len(similar_examples)
                avg_time = sum(ex.get("time_to_target", 0) for ex in similar_examples) / len(similar_examples)
                
                recommendation_parts.append(f"Similar trades averaged +{avg_profit:.1f}% profit in {avg_time:.0f} bars")
            
            # Add database statistics
            db_stats = self.pattern_db.get_database_stats()
            pattern_stats = db_stats.get("pattern_stats", {}).get(pattern_type, {})
            
            if pattern_stats:
                success_rate = pattern_stats.get("success_rate", 0.0)
                avg_profit = pattern_stats.get("avg_profit", 0.0)
                
                if success_rate > 0:
                    recommendation_parts.append(f"Database shows {success_rate:.1%} success rate, avg +{avg_profit:.1f}%")
            
            return " | ".join(recommendation_parts)
            
        except Exception as e:
            logger.error(f"Error generating database recommendation: {e}")
            return f"Pattern: {pattern.get('type', 'unknown')} - Review recommended"
    
    def _create_compact_database_prompt(self, pattern_recommendations: List[Dict]) -> str:
        """Create enhanced preparation prompt with compact database insights"""
        
        # Format database insights
        database_insights = ""
        if pattern_recommendations:
            for rec in pattern_recommendations:
                symbol = rec["symbol"]
                pattern_type = rec["pattern"]["type"]
                confidence_boost = rec["confidence_boost"]
                recommendation = rec["database_recommendation"]
                
                database_insights += f"""
**{symbol} - {pattern_type}:**
- Database Confidence Boost: +{confidence_boost:.1%}
- Recommendation: {recommendation}
"""
        
        # Format optimal parameters
        optimal_parameters = ""
        for rec in pattern_recommendations:
            symbol = rec["symbol"]
            params = rec["optimal_parameters"]
            
            optimal_parameters += f"""
**{symbol} Optimal Parameters:**
- Entry Timing: {params.get("entry_timing", "immediate")}
- Position Size: ${params.get("position_size", 1000.0):,.0f}
- Risk/Reward: {params.get("risk_reward", 2.0):.1f}:1
- Stop Loss: {params.get("stop_loss", 0.02):.1%}
- Take Profit: {params.get("take_profit", 0.04):.1%}
"""
        
        # Format similar examples
        similar_examples = ""
        for rec in pattern_recommendations:
            symbol = rec["symbol"]
            examples = rec["similar_examples"]
            
            if examples:
                similar_examples += f"""
**{symbol} Similar Successful Examples:**
"""
                for i, example in enumerate(examples[:3], 1):
                    profit = example.get("profit_pct", 0)
                    time = example.get("time_to_target", 0)
                    quality = example.get("quality_score", 0.5)
                    
                    similar_examples += f"- Example {i}: +{profit:.1f}% in {time} bars (quality: {quality:.2f})\n"
        
        # Get database statistics
        db_stats = self.pattern_db.get_database_stats()
        total_examples = db_stats.get("total_examples", 0)
        storage_used = db_stats.get("storage_used_mb", 0.0)
        
        return f"""
You are preparing for the next trading cycle with COMPACT PATTERN DATABASE.

**Database Status:**
- Total Examples: {total_examples}
- Storage Used: {storage_used:.2f} MB / 0.3 MB
- Pattern Types: {len(set(rec["pattern"]["type"] for rec in pattern_recommendations))}

**Pattern Database Insights:**
{database_insights}

**Optimal Parameters from Database:**
{optimal_parameters}

**Similar Successful Examples:**
{similar_examples}

**Current Market Context:**
- Exchange: {self.exchange}
- Symbols Monitored: {", ".join(self.symbols[:5])}...
- Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}

**Instructions:**
1. Review pattern database recommendations (only 12 best examples per pattern)
2. Focus on timing optimization from similar successful trades
3. Consider optimal parameters derived from historical success
4. Develop strategy incorporating database insights
5. Prioritize patterns with highest confidence boosts

**Key Focus:**
- Entry timing from similar successful examples
- Optimal position sizing from database
- Risk management parameters from historical data
- Confirmation signals that worked in similar contexts
- Database-backed confidence adjustments
"""
    
    def add_pattern_example_to_database(self, trade_result: Dict[str, Any]) -> bool:
        """Add successful trade result as pattern example to database"""
        try:
            # Only add successful trades
            if trade_result.get("result") != "SUCCESS":
                return False
            
            # Extract pattern information
            pattern_type = trade_result.get("pattern_type")
            if not pattern_type:
                logger.warning("No pattern type in trade result")
                return False
            
            # Create pattern example
            example_data = {
                # Pattern Characteristics
                "pattern_type": pattern_type,
                "formation_quality": trade_result.get("formation_quality", 0.7),
                "duration_bars": trade_result.get("duration_bars", 20),
                "volume_pattern": trade_result.get("volume_pattern", "decreasing"),
                
                # Market Context
                "market_trend": trade_result.get("market_trend", "unknown"),
                "volatility": trade_result.get("volatility", 0.02),
                "volume_confirmation": trade_result.get("volume_confirmation", 1.5),
                "time_of_day": trade_result.get("time_of_day", "12:00"),
                
                # Trade Execution
                "entry_price": trade_result.get("entry_price", 0.0),
                "entry_timing": trade_result.get("entry_timing", "immediate"),
                "entry_confidence": trade_result.get("entry_confidence", 0.7),
                "position_size": trade_result.get("position_size", 1000.0),
                
                # Risk Management
                "stop_loss": trade_result.get("stop_loss", 0.0),
                "take_profit": trade_result.get("take_profit", 0.0),
                "risk_reward": trade_result.get("risk_reward", 2.0),
                
                # Outcome & Learning
                "result": trade_result.get("result", "SUCCESS"),
                "profit_pct": trade_result.get("profit_pct", 0.0),
                "time_to_target": trade_result.get("time_to_target", 15),
                "confirmation_signals": trade_result.get("confirmation_signals", []),
                "key_insights": trade_result.get("key_insights", "Trade executed successfully"),
                
                # Timing Optimization
                "optimal_entry_time": trade_result.get("entry_time", "12:00"),
                "optimal_exit_time": trade_result.get("exit_time", "12:30"),
                "market_session": trade_result.get("market_session", "unknown"),
                
                # Pattern Quality Metrics
                "shoulder_symmetry": trade_result.get("shoulder_symmetry", 0.8),
                "neckline_quality": trade_result.get("neckline_quality", 0.8),
                "head_prominence": trade_result.get("head_prominence", 1.2),
                
                # Metadata
                "timestamp": datetime.now().isoformat(),
                "symbol": trade_result.get("symbol", "unknown"),
                "timeframe": trade_result.get("timeframe", "15m")
            }
            
            # Add to database
            success = self.pattern_db.add_successful_example(pattern_type, example_data)
            
            if success:
                logger.info(f"Added pattern example to database: {pattern_type} for {trade_result.get('symbol', 'unknown')}")
            else:
                logger.info(f"Pattern example not added (quality too low): {pattern_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding pattern example to database: {e}")
            return False
    
    def get_database_health_report(self) -> Dict[str, Any]:
        """Get comprehensive database health report"""
        try:
            db_stats = self.pattern_db.get_database_stats()
            
            # Analyze pattern distribution
            pattern_distribution = {}
            for pattern_type, examples in self.pattern_db.pattern_examples.items():
                pattern_distribution[pattern_type] = {
                    "count": len(examples),
                    "success_rate": db_stats.get("pattern_stats", {}).get(pattern_type, {}).get("success_rate", 0.0),
                    "avg_profit": db_stats.get("pattern_stats", {}).get(pattern_type, {}).get("avg_profit", 0.0)
                }
            
            # Calculate overall health score
            total_examples = db_stats.get("total_examples", 0)
            storage_used_pct = db_stats.get("storage_used_pct", 0.0)
            compression_ratio = db_stats.get("compression_ratio", 0.0)
            
            # Health score calculation (0-100)
            example_score = min(total_examples / 72 * 50, 50)  # Max 50 for having examples
            storage_score = max(0, 50 - storage_used_pct)       # Max 50 for storage efficiency
            compression_score = compression_ratio * 0.2         # Small bonus for compression
            
            health_score = min(100, example_score + storage_score + compression_score)
            
            return {
                "health_score": round(health_score, 1),
                "database_stats": db_stats,
                "pattern_distribution": pattern_distribution,
                "recommendations": self._generate_health_recommendations(db_stats, pattern_distribution)
            }
            
        except Exception as e:
            logger.error(f"Error generating database health report: {e}")
            return {
                "health_score": 0.0,
                "database_stats": {},
                "pattern_distribution": {},
                "recommendations": ["Database health check failed"]
            }
    
    def _generate_health_recommendations(self, db_stats: Dict[str, Any], 
                                        pattern_distribution: Dict[str, Any]) -> List[str]:
        """Generate health recommendations based on database status"""
        recommendations = []
        
        total_examples = db_stats.get("total_examples", 0)
        storage_used_pct = db_stats.get("storage_used_pct", 0.0)
        
        # Check total examples
        if total_examples < 36:  # Less than half full
            recommendations.append("Add more successful pattern examples to improve database coverage")
        
        # Check storage usage
        if storage_used_pct > 80:
            recommendations.append("Consider optimizing storage or compressing old examples")
        
        # Check pattern distribution
        low_examples_patterns = [p for p, data in pattern_distribution.items() if data["count"] < 6]
        if low_examples_patterns:
            recommendations.append(f"Focus on collecting examples for: {', '.join(low_examples_patterns)}")
        
        # Check success rates
        low_success_patterns = [p for p, data in pattern_distribution.items() if data["success_rate"] < 0.5]
        if low_success_patterns:
            recommendations.append(f"Review strategy for patterns with low success rates: {', '.join(low_success_patterns)}")
        
        if not recommendations:
            recommendations.append("Database health is optimal")
        
        return recommendations
    
    def optimize_database(self) -> Dict[str, Any]:
        """Optimize database performance and storage"""
        try:
            # Get stats before optimization
            stats_before = self.pattern_db.get_database_stats()
            
            # Perform optimizations
            self.pattern_db.optimize_storage()
            self.pattern_db.clear_low_quality_examples(quality_threshold=0.4)
            
            # Get stats after optimization
            stats_after = self.pattern_db.get_database_stats()
            
            # Calculate improvements
            removed_count = stats_before.get("total_examples", 0) - stats_after.get("total_examples", 0)
            compression_improvement = stats_after.get("compression_ratio", 0.0) - stats_before.get("compression_ratio", 0.0)
            
            return {
                "success": True,
                "removed_examples": removed_count,
                "compression_improvement": compression_improvement,
                "storage_saved_mb": stats_before.get("storage_used_mb", 0.0) - stats_after.get("storage_used_mb", 0.0),
                "final_stats": stats_after
            }
            
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            return {
                "success": False,
                "error": str(e),
                "removed_examples": 0,
                "compression_improvement": 0.0,
                "storage_saved_mb": 0.0,
                "final_stats": {}
            }


# Create singleton instance
database_integration = DatabaseIntegration()


def get_database_integration(data_dir: Optional[str] = None) -> DatabaseIntegration:
    """Get the global database integration instance"""
    global database_integration
    if data_dir:
        database_integration = DatabaseIntegration(data_dir)
    return database_integration
