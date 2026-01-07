"""
Compact Pattern Database System
Stores only the 12 most successful examples per pattern type with rotating logs
Total storage target: ~300 KB
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PatternExample:
    """Compact pattern example structure (~4KB)"""
    # Pattern Characteristics (500 bytes)
    pattern_type: str
    formation_quality: float  # 0.0-1.0 formation quality score
    duration_bars: int        # Formation duration
    volume_pattern: str       # Volume trend during formation
    
    # Market Context (400 bytes)
    market_trend: str         # Market trend context
    volatility: float         # Current volatility
    volume_confirmation: float  # Volume spike multiple
    time_of_day: str          # Optimal timing
    
    # Trade Execution (600 bytes)
    entry_price: float
    entry_timing: str         # immediate vs pullback
    entry_confidence: float
    position_size: float      # USD position size
    
    # Risk Management (400 bytes)
    stop_loss: float
    take_profit: float
    risk_reward: float        # Risk/reward ratio
    
    # Outcome & Learning (800 bytes)
    result: str               # SUCCESS or FAILURE
    profit_pct: float         # Profit percentage
    time_to_target: int       # Bars to hit target
    confirmation_signals: List[str]
    key_insights: str         # Key learning from trade
    
    # Timing Optimization (300 bytes)
    optimal_entry_time: str
    optimal_exit_time: str
    market_session: str
    
    # Pattern Quality Metrics (200 bytes)
    shoulder_symmetry: float  # For H&S patterns
    neckline_quality: float   # For H&S patterns
    head_prominence: float    # For H&S patterns
    
    # Metadata (100 bytes)
    timestamp: str
    symbol: str
    timeframe: str
    quality_score: float      # Calculated quality score


class CompactPatternDatabase:
    """Compact pattern database with rotating logs and smart quality scoring"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the compact pattern database"""
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent / "data" / "patterns"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_file = self.data_dir / "compact_pattern_db.json"
        self.stats_file = self.data_dir / "pattern_stats.json"
        
        # Database structure
        self.pattern_examples: Dict[str, List[Dict]] = {
            "head_and_shoulders": [],
            "triangles": [],
            "double_top_bottom": [],
            "flags_pennants": [],
            "cup_handle": [],
            "wedges": []
        }
        
        self.pattern_stats: Dict[str, Dict] = {
            pattern: {
                "total_trades": 0,
                "success_rate": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "best_examples": [],    # Top 3 examples
                "worst_examples": []    # Top 3 failures
            } for pattern in self.pattern_examples.keys()
        }
        
        # Storage limits
        self.max_examples_per_pattern = 12
        self.max_best_examples = 3
        self.max_worst_examples = 3
        self.max_storage_mb = 0.3  # 300KB limit
        
        # Load existing data
        self._load_database()
        
        logger.info(f"Compact Pattern Database initialized with {len(self.pattern_examples)} pattern types")
    
    def add_successful_example(self, pattern_type: str, example_data: Dict[str, Any]) -> bool:
        """Add successful example with smart rotation"""
        try:
            if pattern_type not in self.pattern_examples:
                logger.warning(f"Unknown pattern type: {pattern_type}")
                return False
            
            # Calculate quality score
            quality_score = self._calculate_example_quality(example_data)
            example_data["quality_score"] = quality_score
            
            examples = self.pattern_examples[pattern_type]
            
            if len(examples) < self.max_examples_per_pattern:
                # Add directly if under limit
                examples.append(example_data)
                logger.info(f"Added example to {pattern_type} (total: {len(examples)})")
            else:
                # Replace lowest quality example
                min_quality_idx = min(range(len(examples)), 
                                     key=lambda i: examples[i].get("quality_score", 0))
                
                if quality_score > examples[min_quality_idx].get("quality_score", 0):
                    examples[min_quality_idx] = example_data
                    logger.info(f"Replaced low-quality example in {pattern_type}")
                else:
                    logger.info(f"New example quality ({quality_score:.2f}) too low to replace existing")
                    return False
            
            # Update pattern statistics
            self._update_pattern_statistics(pattern_type, example_data)
            
            # Update best/worst examples
            self._update_best_worst_examples(pattern_type, example_data)
            
            # Save database
            self._save_database()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding example to {pattern_type}: {e}")
            return False
    
    def _calculate_example_quality(self, example: Dict[str, Any]) -> float:
        """Calculate quality score for example (0.0-1.0)"""
        try:
            quality_factors = {}
            
            # Profit magnitude (max 10% profit = 1.0)
            quality_factors["profit_magnitude"] = min(example.get("profit_pct", 0) / 10.0, 1.0)
            
            # Timing efficiency (20 bars or less = 1.0)
            time_to_target = example.get("time_to_target", 50)
            quality_factors["timing_efficiency"] = 1.0 if time_to_target <= 20 else 0.5
            
            # Confirmation strength (each signal adds 0.25, max 1.0)
            confirmation_count = len(example.get("confirmation_signals", []))
            quality_factors["confirmation_strength"] = min(confirmation_count * 0.25, 1.0)
            
            # Pattern clarity (formation quality)
            quality_factors["pattern_clarity"] = example.get("formation_quality", 0.5)
            
            # Risk management (2.0+ R/R = 1.0)
            risk_reward = example.get("risk_reward", 1.0)
            quality_factors["risk_management"] = 1.0 if risk_reward >= 2.0 else 0.5
            
            # Formation quality bonus
            formation_quality = example.get("formation_quality", 0.5)
            quality_factors["formation_bonus"] = formation_quality * 0.2
            
            # Calculate weighted average
            total_quality = sum(quality_factors.values())
            quality_score = total_quality / len(quality_factors)
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.5  # Default medium quality
    
    def _update_pattern_statistics(self, pattern_type: str, example: Dict[str, Any]):
        """Update pattern statistics with new example"""
        try:
            stats = self.pattern_stats[pattern_type]
            
            # Update total trades
            stats["total_trades"] += 1
            
            # Update success rate
            if example.get("result") == "SUCCESS":
                # Recalculate success rate
                success_count = sum(1 for ex in self.pattern_examples[pattern_type] 
                                  if ex.get("result") == "SUCCESS")
                stats["success_rate"] = success_count / len(self.pattern_examples[pattern_type])
            
            # Update average profit/loss
            profit_pct = example.get("profit_pct", 0)
            if example.get("result") == "SUCCESS":
                # Calculate new average profit
                success_examples = [ex for ex in self.pattern_examples[pattern_type] 
                                  if ex.get("result") == "SUCCESS"]
                stats["avg_profit"] = sum(ex.get("profit_pct", 0) for ex in success_examples) / len(success_examples)
            else:
                # Calculate new average loss
                failure_examples = [ex for ex in self.pattern_examples[pattern_type] 
                                  if ex.get("result") == "FAILURE"]
                stats["avg_loss"] = sum(ex.get("profit_pct", 0) for ex in failure_examples) / len(failure_examples)
            
        except Exception as e:
            logger.error(f"Error updating statistics for {pattern_type}: {e}")
    
    def _update_best_worst_examples(self, pattern_type: str, example: Dict[str, Any]):
        """Update best and worst example lists"""
        try:
            stats = self.pattern_stats[pattern_type]
            
            if example.get("result") == "SUCCESS":
                # Add to best examples
                stats["best_examples"].append({
                    "quality_score": example.get("quality_score", 0),
                    "profit_pct": example.get("profit_pct", 0),
                    "time_to_target": example.get("time_to_target", 0),
                    "symbol": example.get("symbol", ""),
                    "timestamp": example.get("timestamp", "")
                })
                
                # Keep only top 3
                stats["best_examples"] = sorted(
                    stats["best_examples"], 
                    key=lambda x: x["quality_score"], 
                    reverse=True
                )[:self.max_best_examples]
            
            else:
                # Add to worst examples
                stats["worst_examples"].append({
                    "quality_score": example.get("quality_score", 0),
                    "profit_pct": example.get("profit_pct", 0),
                    "time_to_target": example.get("time_to_target", 0),
                    "symbol": example.get("symbol", ""),
                    "timestamp": example.get("timestamp", "")
                })
                
                # Keep only top 3 (worst)
                stats["worst_examples"] = sorted(
                    stats["worst_examples"], 
                    key=lambda x: x["quality_score"]
                )[:self.max_worst_examples]
                
        except Exception as e:
            logger.error(f"Error updating best/worst examples for {pattern_type}: {e}")
    
    def get_optimal_parameters(self, pattern_type: str, current_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimal parameters from best examples"""
        try:
            if pattern_type not in self.pattern_examples:
                logger.warning(f"Unknown pattern type: {pattern_type}")
                return self._get_default_parameters(pattern_type)
            
            examples = self.pattern_examples[pattern_type]
            
            if not examples:
                return self._get_default_parameters(pattern_type)
            
            # Filter examples by similar market context
            similar_examples = self._filter_by_context(examples, current_context)
            
            if not similar_examples:
                similar_examples = examples  # Fallback to all examples
            
            # Calculate optimal parameters from similar examples
            return {
                "entry_timing": self._calculate_optimal_entry_timing(similar_examples),
                "position_size": self._calculate_optimal_position_size(similar_examples),
                "stop_loss": self._calculate_optimal_stop_loss(similar_examples),
                "take_profit": self._calculate_optimal_take_profit(similar_examples),
                "confidence_boost": self._calculate_confidence_boost(similar_examples),
                "risk_reward": self._calculate_optimal_risk_reward(similar_examples)
            }
            
        except Exception as e:
            logger.error(f"Error getting optimal parameters for {pattern_type}: {e}")
            return self._get_default_parameters(pattern_type)
    
    def _filter_by_context(self, examples: List[Dict], current_context: Dict[str, Any]) -> List[Dict]:
        """Filter examples by similar market context"""
        try:
            similar_examples = []
            
            for example in examples:
                context_score = self._calculate_context_similarity(example, current_context)
                
                # Include if context is reasonably similar
                if context_score >= 0.7:  # 70% similarity threshold
                    similar_examples.append(example)
            
            return similar_examples
            
        except Exception as e:
            logger.error(f"Error filtering examples by context: {e}")
            return examples  # Fallback to all examples
    
    def _calculate_context_similarity(self, example: Dict[str, Any], current_context: Dict[str, Any]) -> float:
        """Calculate similarity between example and current context"""
        try:
            similarity_factors = []
            
            # Market trend similarity
            example_trend = example.get("market_trend", "")
            current_trend = current_context.get("market_trend", "")
            
            if example_trend == current_trend:
                similarity_factors.append(1.0)
            elif self._are_trends_compatible(example_trend, current_trend):
                similarity_factors.append(0.7)
            else:
                similarity_factors.append(0.2)
            
            # Volatility similarity
            example_vol = example.get("volatility", 0.02)
            current_vol = current_context.get("volatility", 0.02)
            vol_diff = abs(example_vol - current_vol)
            
            if vol_diff < 0.005:  # Within 0.5%
                similarity_factors.append(1.0)
            elif vol_diff < 0.015:  # Within 1.5%
                similarity_factors.append(0.7)
            else:
                similarity_factors.append(0.3)
            
            # Time of day similarity
            example_time = example.get("time_of_day", "12:00")
            current_time = current_context.get("time_of_day", "12:00")
            
            if self._are_times_similar(example_time, current_time):
                similarity_factors.append(0.8)
            else:
                similarity_factors.append(0.4)
            
            # Volume confirmation similarity
            example_vol_conf = example.get("volume_confirmation", 1.0)
            current_vol_conf = current_context.get("volume_confirmation", 1.0)
            vol_conf_diff = abs(example_vol_conf - current_vol_conf)
            
            if vol_conf_diff < 0.3:  # Within 30%
                similarity_factors.append(1.0)
            elif vol_conf_diff < 0.8:  # Within 80%
                similarity_factors.append(0.7)
            else:
                similarity_factors.append(0.3)
            
            return sum(similarity_factors) / len(similarity_factors)
            
        except Exception as e:
            logger.error(f"Error calculating context similarity: {e}")
            return 0.5  # Default medium similarity
    
    def _are_trends_compatible(self, trend1: str, trend2: str) -> bool:
        """Check if two trends are compatible"""
        compatible_pairs = [
            ("bullish", "bullish_to_bearish"),
            ("bearish", "bearish_to_bullish"),
            ("bullish_to_bearish", "bullish"),
            ("bearish_to_bullish", "bearish")
        ]
        return (trend1, trend2) in compatible_pairs or (trend2, trend1) in compatible_pairs
    
    def _are_times_similar(self, time1: str, time2: str) -> bool:
        """Check if two times are similar (within 2 hours)"""
        try:
            # Convert time strings to hours
            def time_to_hours(time_str: str) -> float:
                hours, minutes = map(int, time_str.split(':'))
                return hours + minutes / 60
            
            t1_hours = time_to_hours(time1)
            t2_hours = time_to_hours(time2)
            
            # Calculate time difference (considering wraparound)
            diff = abs(t1_hours - t2_hours)
            diff = min(diff, 24 - diff)  # Handle day wraparound
            
            return diff <= 2.0  # Within 2 hours
            
        except:
            return False
    
    def _calculate_optimal_entry_timing(self, examples: List[Dict]) -> str:
        """Calculate optimal entry timing from examples"""
        try:
            immediate_count = sum(1 for ex in examples if ex.get("entry_timing") == "immediate")
            pullback_count = len(examples) - immediate_count
            
            if immediate_count > pullback_count:
                return "immediate"
            else:
                return "pullback"
                
        except Exception as e:
            logger.error(f"Error calculating optimal entry timing: {e}")
            return "immediate"
    
    def _calculate_optimal_position_size(self, examples: List[Dict]) -> float:
        """Calculate optimal position size from examples"""
        try:
            if not examples:
                return 1000.0  # Default position size
            
            position_sizes = [ex.get("position_size", 1000.0) for ex in examples]
            return sum(position_sizes) / len(position_sizes)
            
        except Exception as e:
            logger.error(f"Error calculating optimal position size: {e}")
            return 1000.0
    
    def _calculate_optimal_stop_loss(self, examples: List[Dict]) -> float:
        """Calculate optimal stop loss from examples"""
        try:
            if not examples:
                return 0.02  # Default 2%
            
            stop_losses = [ex.get("stop_loss", 0.02) for ex in examples]
            return sum(stop_losses) / len(stop_losses)
            
        except Exception as e:
            logger.error(f"Error calculating optimal stop loss: {e}")
            return 0.02
    
    def _calculate_optimal_take_profit(self, examples: List[Dict]) -> float:
        """Calculate optimal take profit from examples"""
        try:
            if not examples:
                return 0.04  # Default 4%
            
            take_profits = [ex.get("take_profit", 0.04) for ex in examples]
            return sum(take_profits) / len(take_profits)
            
        except Exception as e:
            logger.error(f"Error calculating optimal take profit: {e}")
            return 0.04
    
    def _calculate_confidence_boost(self, examples: List[Dict]) -> float:
        """Calculate confidence boost from examples"""
        try:
            if not examples:
                return 0.0
            
            # Calculate average quality score
            quality_scores = [ex.get("quality_score", 0.5) for ex in examples]
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # Convert to confidence boost (0-20%)
            confidence_boost = avg_quality * 0.20
            
            return confidence_boost
            
        except Exception as e:
            logger.error(f"Error calculating confidence boost: {e}")
            return 0.0
    
    def _calculate_optimal_risk_reward(self, examples: List[Dict]) -> float:
        """Calculate optimal risk/reward ratio from examples"""
        try:
            if not examples:
                return 2.0  # Default 2:1
            
            risk_rewards = [ex.get("risk_reward", 2.0) for ex in examples]
            return sum(risk_rewards) / len(risk_rewards)
            
        except Exception as e:
            logger.error(f"Error calculating optimal risk/reward: {e}")
            return 2.0
    
    def _get_default_parameters(self, pattern_type: str) -> Dict[str, Any]:
        """Get default parameters for pattern type"""
        defaults = {
            "head_and_shoulders": {
                "entry_timing": "immediate",
                "position_size": 1200.0,
                "stop_loss": 0.02,
                "take_profit": 0.04,
                "confidence_boost": 0.05,
                "risk_reward": 2.0
            },
            "triangles": {
                "entry_timing": "immediate",
                "position_size": 1000.0,
                "stop_loss": 0.015,
                "take_profit": 0.035,
                "confidence_boost": 0.08,
                "risk_reward": 2.5
            },
            "double_top_bottom": {
                "entry_timing": "pullback",
                "position_size": 1100.0,
                "stop_loss": 0.018,
                "take_profit": 0.038,
                "confidence_boost": 0.06,
                "risk_reward": 2.2
            },
            "flags_pennants": {
                "entry_timing": "immediate",
                "position_size": 1300.0,
                "stop_loss": 0.012,
                "take_profit": 0.045,
                "confidence_boost": 0.10,
                "risk_reward": 3.0
            },
            "cup_handle": {
                "entry_timing": "pullback",
                "position_size": 1150.0,
                "stop_loss": 0.015,
                "take_profit": 0.042,
                "confidence_boost": 0.07,
                "risk_reward": 2.8
            },
            "wedges": {
                "entry_timing": "immediate",
                "position_size": 1050.0,
                "stop_loss": 0.016,
                "take_profit": 0.036,
                "confidence_boost": 0.04,
                "risk_reward": 2.1
            }
        }
        
        return defaults.get(pattern_type, {
            "entry_timing": "immediate",
            "position_size": 1000.0,
            "stop_loss": 0.02,
            "take_profit": 0.04,
            "confidence_boost": 0.0,
            "risk_reward": 2.0
        })
    
    def get_similar_examples(self, pattern_type: str, current_context: Dict[str, Any], limit: int = 3) -> List[Dict]:
        """Get similar successful examples"""
        try:
            if pattern_type not in self.pattern_examples:
                return []
            
            examples = self.pattern_examples[pattern_type]
            
            # Filter for successful examples
            success_examples = [ex for ex in examples if ex.get("result") == "SUCCESS"]
            
            if not success_examples:
                return []
            
            # Filter by context similarity
            similar_examples = self._filter_by_context(success_examples, current_context)
            
            if not similar_examples:
                similar_examples = success_examples
            
            # Sort by quality score
            similar_examples.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            
            return similar_examples[:limit]
            
        except Exception as e:
            logger.error(f"Error getting similar examples for {pattern_type}: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            total_examples = sum(len(examples) for examples in self.pattern_examples.values())
            total_storage = self._calculate_storage_size()
            
            return {
                "total_examples": total_examples,
                "storage_used_mb": total_storage,
                "storage_limit_mb": self.max_storage_mb,
                "storage_used_pct": (total_storage / self.max_storage_mb) * 100,
                "pattern_stats": self.pattern_stats,
                "compression_ratio": self._calculate_compression_ratio()
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {
                "total_examples": 0,
                "storage_used_mb": 0.0,
                "storage_limit_mb": self.max_storage_mb,
                "storage_used_pct": 0.0,
                "pattern_stats": {},
                "compression_ratio": 0.0
            }
    
    def _calculate_storage_size(self) -> float:
        """Calculate current storage size in MB"""
        try:
            # Estimate storage size based on number of examples
            total_examples = sum(len(examples) for examples in self.pattern_examples.values())
            avg_example_size_kb = 4.0  # Average example size
            total_size_kb = total_examples * avg_example_size_kb
            return total_size_kb / 1024  # Convert to MB
            
        except Exception as e:
            logger.error(f"Error calculating storage size: {e}")
            return 0.0
    
    def _calculate_compression_ratio(self) -> float:
        """Calculate compression ratio"""
        try:
            # Count compressed examples (old examples with reduced fields)
            compressed_count = 0
            total_count = 0
            
            for examples in self.pattern_examples.values():
                for example in examples:
                    total_count += 1
                    if "key_insights" not in example or "confirmation_signals" not in example:
                        compressed_count += 1
            
            if total_count == 0:
                return 0.0
            
            return (compressed_count / total_count) * 100
            
        except Exception as e:
            logger.error(f"Error calculating compression ratio: {e}")
            return 0.0
    
    def _save_database(self):
        """Save database to file"""
        try:
            # Save pattern examples
            with open(self.db_file, 'w') as f:
                json.dump(self.pattern_examples, f, indent=2)
            
            # Save pattern statistics
            with open(self.stats_file, 'w') as f:
                json.dump(self.pattern_stats, f, indent=2)
            
            logger.debug(f"Database saved: {len(self.pattern_examples)} patterns")
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    def _load_database(self):
        """Load database from file"""
        try:
            # Load pattern examples
            if self.db_file.exists():
                with open(self.db_file, 'r') as f:
                    loaded_examples = json.load(f)
                    
                # Validate and load examples
                for pattern_type, examples in loaded_examples.items():
                    if pattern_type in self.pattern_examples:
                        self.pattern_examples[pattern_type] = examples[:self.max_examples_per_pattern]
            
            # Load pattern statistics
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    loaded_stats = json.load(f)
                    
                # Validate and load statistics
                for pattern_type, stats in loaded_stats.items():
                    if pattern_type in self.pattern_stats:
                        self.pattern_stats[pattern_type] = stats
            
            logger.info(f"Database loaded: {sum(len(ex) for ex in self.pattern_examples.values())} examples")
            
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            # Initialize with empty data if loading fails
            self.pattern_examples = {k: [] for k in self.pattern_examples.keys()}
            self.pattern_stats = {k: v for k, v in self.pattern_stats.items()}
    
    def optimize_storage(self):
        """Optimize storage by compressing old examples"""
        try:
            current_time = datetime.now()
            compression_threshold = 30  # days
            
            for pattern_type, examples in self.pattern_examples.items():
                for example in examples:
                    try:
                        example_time = datetime.fromisoformat(
                            example["timestamp"].replace('Z', '+00:00')
                        )
                        
                        if (current_time - example_time).days > compression_threshold:
                            # Compress old example
                            example.pop("key_insights", None)
                            example.pop("confirmation_signals", None)
                            example.pop("failure_signals", None)
                            
                    except Exception:
                        # Skip examples with invalid timestamps
                        continue
            
            self._save_database()
            logger.info("Storage optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing storage: {e}")
    
    def clear_low_quality_examples(self, quality_threshold: float = 0.5):
        """Clear examples below quality threshold"""
        try:
            removed_count = 0
            
            for pattern_type, examples in self.pattern_examples.items():
                # Keep only high-quality examples
                filtered_examples = [
                    ex for ex in examples 
                    if ex.get("quality_score", 0) >= quality_threshold
                ]
                
                removed_count += len(examples) - len(filtered_examples)
                self.pattern_examples[pattern_type] = filtered_examples
            
            self._save_database()
            logger.info(f"Cleared {removed_count} low-quality examples")
            
        except Exception as e:
            logger.error(f"Error clearing low-quality examples: {e}")
    
    def export_database(self, export_path: str) -> bool:
        """Export database to specified path"""
        try:
            export_data = {
                "pattern_examples": self.pattern_examples,
                "pattern_stats": self.pattern_stats,
                "export_timestamp": datetime.now().isoformat(),
                "storage_info": self.get_database_stats()
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Database exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting database: {e}")
            return False
    
    def import_database(self, import_path: str) -> bool:
        """Import database from specified path"""
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            # Validate import data
            if "pattern_examples" not in import_data or "pattern_stats" not in import_data:
                logger.error("Invalid import file format")
                return False
            
            # Import data
            self.pattern_examples = import_data["pattern_examples"]
            self.pattern_stats = import_data["pattern_stats"]
            
            # Enforce limits
            for pattern_type in self.pattern_examples:
                self.pattern_examples[pattern_type] = self.pattern_examples[pattern_type][:self.max_examples_per_pattern]
            
            self._save_database()
            logger.info(f"Database imported from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing database: {e}")
            return False


# Create singleton instance
pattern_database = CompactPatternDatabase()


def get_pattern_database(data_dir: Optional[str] = None) -> CompactPatternDatabase:
    """Get the global pattern database instance"""
    global pattern_database
    if data_dir:
        pattern_database = CompactPatternDatabase(data_dir)
    return pattern_database