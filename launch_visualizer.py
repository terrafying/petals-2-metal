#!/usr/bin/env python3
"""
Launch script for the Quantum Gravity Visualizer with sensible defaults and error handling.
"""

import os
import sys
import argparse
import logging
import torch
import numpy as np
from typing import Optional, Dict, Any
from visualization_manager import (
    VisualizationConfig,
    QuantumGravityVisualizer,
    VectorDrivenVisualizer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VisualizerLauncher:
    """Handles launching and configuration of visualizers."""
    
    DEFAULT_CONFIG = {
        'window_width': 1200,
        'window_height': 800,
        'grid_size': 8,
        'pattern_threshold': 0.3,
        'mandala_size': 25,
        'concretion_size': 25,
        'update_rate': 60,  # FPS
        'enable_glsl': True,
        'enable_jitter': True,
        'enable_orbital': True,
        'enable_spin': True
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize launcher with optional custom configuration."""
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Initialize visualizers
        self.quantum_visualizer = None
        self.vector_visualizer = None
        self.batch = None
        self.window = None
        
    def setup_visualizers(self):
        """Set up visualizers with configuration."""
        try:
            # Create visualization config
            viz_config = VisualizationConfig(
                grid_size=self.config['grid_size'],
                pattern_threshold=self.config['pattern_threshold']
            )
            
            # Initialize visualizers
            self.quantum_visualizer = QuantumGravityVisualizer(config=viz_config)
            self.vector_visualizer = VectorDrivenVisualizer(
                mandala_size=self.config['mandala_size'],
                concretion_size=self.config['concretion_size']
            )
            
            logger.info("Visualizers initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up visualizers: {e}", exc_info=True)
            return False
    
    def create_test_pattern(self, size: int = 20) -> torch.Tensor:
        """Create a test pattern tensor with controlled properties."""
        try:
            # Create base pattern with controlled properties
            base = torch.randn(size)
            
            # Add some structure to make it more interesting
            t = torch.linspace(0, 2*np.pi, size)
            structure = torch.sin(t) + 0.5 * torch.sin(2*t)
            
            # Combine and normalize
            pattern = base + structure
            pattern = (pattern - pattern.min()) / (pattern.max() - pattern.min())
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error creating test pattern: {e}", exc_info=True)
            return torch.zeros(size)
    
    def run_visualization(self):
        """Run the visualization with error handling."""
        try:
            import pyglet
            from pyglet.window import key
            
            # Create window
            self.window = pyglet.window.Window(
                width=self.config['window_width'],
                height=self.config['window_height'],
                caption="Quantum Gravity Visualizer"
            )
            
            # Create batch for efficient rendering
            self.batch = pyglet.graphics.Batch()
            
            # Create groups for layering
            group_background = pyglet.graphics.Group(0)
            group_foreground = pyglet.graphics.Group(1)
            
            # Create initial pattern
            pattern = self.create_test_pattern()
            
            @self.window.event
            def on_draw():
                """Handle window drawing."""
                try:
                    self.window.clear()
                    
                    # Update quantum visualization
                    self.quantum_visualizer.update_visualization(
                        pattern=pattern,
                        batch=self.batch,
                        group_foreground=group_foreground,
                        group_background=group_background,
                        window_width=self.config['window_width'],
                        window_height=self.config['window_height']
                    )
                    
                    # Update vector visualization
                    self.vector_visualizer.update_geometric_mandala_pyglet(
                        pattern=pattern,
                        batch=self.batch,
                        group_foreground=group_foreground,
                        group_background=group_background,
                        window_width=self.config['window_width'],
                        window_height=self.config['window_height']
                    )
                    
                    # Draw batch
                    self.batch.draw()
                    
                except Exception as e:
                    logger.error(f"Error in draw event: {e}", exc_info=True)
            
            @self.window.event
            def on_key_press(symbol, modifiers):
                """Handle key press events."""
                try:
                    if symbol == key.ESCAPE:
                        pyglet.app.exit()
                    elif symbol == key.SPACE:
                        # Generate new pattern
                        nonlocal pattern
                        pattern = self.create_test_pattern()
                    
                except Exception as e:
                    logger.error(f"Error in key press event: {e}", exc_info=True)
            
            # Set up update interval
            pyglet.clock.schedule_interval(
                lambda dt: None,  # Empty update function
                1.0 / self.config['update_rate']
            )
            
            # Run the application
            pyglet.app.run()
            
        except Exception as e:
            logger.error(f"Error running visualization: {e}", exc_info=True)
            return False
        
        return True

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch the Quantum Gravity Visualizer"
    )
    
    parser.add_argument(
        '--width',
        type=int,
        default=1200,
        help="Window width (default: 1200)"
    )
    
    parser.add_argument(
        '--height',
        type=int,
        default=800,
        help="Window height (default: 800)"
    )
    
    parser.add_argument(
        '--grid-size',
        type=int,
        default=8,
        help="Grid size for visualization (default: 8)"
    )
    
    parser.add_argument(
        '--fps',
        type=int,
        default=60,
        help="Target frames per second (default: 60)"
    )
    
    parser.add_argument(
        '--disable-glsl',
        action='store_true',
        help="Disable GLSL shader effects"
    )
    
    parser.add_argument(
        '--disable-jitter',
        action='store_true',
        help="Disable Jitter matrix output"
    )
    
    parser.add_argument(
        '--disable-orbital',
        action='store_true',
        help="Disable orbital mechanics"
    )
    
    parser.add_argument(
        '--disable-spin',
        action='store_true',
        help="Disable spin mechanics"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Create configuration
        config = {
            'window_width': args.width,
            'window_height': args.height,
            'grid_size': args.grid_size,
            'update_rate': args.fps,
            'enable_glsl': not args.disable_glsl,
            'enable_jitter': not args.disable_jitter,
            'enable_orbital': not args.disable_orbital,
            'enable_spin': not args.disable_spin
        }
        
        # Create and run launcher
        launcher = VisualizerLauncher(config)
        
        if launcher.setup_visualizers():
            logger.info("Starting visualization...")
            launcher.run_visualization()
        else:
            logger.error("Failed to set up visualizers")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 