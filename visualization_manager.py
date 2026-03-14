import os
import json
import torch
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np
import math # Added for mandala calculations
# Remove Matplotlib imports for geometric rendering, will be replaced by Pyglet
# import matplotlib.pyplot as plt 
# import matplotlib.patches as patches 
import pyglet
import pyglet.shapes as pyglet_shapes # Alias to avoid name conflicts
import pyglet.graphics
import logging

logger = logging.getLogger(__name__)

@dataclass
class VisualizationConfig:
    """Configuration for pattern visualization."""
    grid_size: int = 8  # E8 lattice size
    zoom_range: tuple = (0.5, 2.0)  # Min/max zoom levels
    rotation_step: int = 15  # Degrees per rotation step
    pattern_threshold: float = 0.3  # Threshold for lattice cell activation
    color_scheme: Dict[str, str] = None  # Color mapping for features

    def __post_init__(self):
        if self.color_scheme is None:
            self.color_scheme = {
                'background': '#1a1a1a',
                'card': '#2a2a2a',
                'text': '#ffffff',
                'accent': '#666666',
                'highlight': '#888888'
            }

class PatternVisualizer:
    """Handles pattern visualization and interaction."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        os.makedirs(self.template_dir, exist_ok=True)
        
    def _prepare_pattern_data(self, pattern: torch.Tensor) -> Dict[str, Any]:
        """Convert pattern tensor to visualization-friendly format with quantum/time-lattice properties."""
        pattern_np = pattern.detach().cpu().numpy()
        
        # Extract quantum properties
        quantum_coherence = float(pattern_np[0]) if len(pattern_np) > 0 else 0.0
        time_reversal = float(pattern_np[1]) if len(pattern_np) > 1 else 0.0
        lattice_stability = float(pattern_np[2]) if len(pattern_np) > 2 else 0.0
        spin_phase = float(pattern_np[3]) if len(pattern_np) > 3 else 0.0
        evaporation = float(pattern_np[4]) if len(pattern_np) > 4 else 0.0
        
        return {
            'values': pattern_np.tolist(),
            'stats': {
                'quantum_coherence': quantum_coherence,
                'time_reversal': time_reversal,
                'lattice_stability': lattice_stability,
                'spin_phase': spin_phase,
                'evaporation': evaporation
            },
            'lattice': self._generate_quantum_lattice(pattern_np)
        }
    
    def _generate_quantum_lattice(self, pattern: np.ndarray) -> List[List[Dict[str, Any]]]:
        """Generate quantum lattice representation of pattern with time-reversal and spin properties."""
        grid = []
        for i in range(self.config.grid_size):
            row = []
            for j in range(self.config.grid_size):
                # Extract quantum properties for this cell
                idx = (i * self.config.grid_size + j) % len(pattern)
                value = pattern[idx]
                
                # Calculate quantum properties
                coherence = abs(value) * 0.8 + 0.2  # Normalize to [0.2, 1.0]
                time_reversal = (np.sin(value) > 0).astype(float)
                spin = np.angle(complex(value, pattern[(idx + 1) % len(pattern)]))
                stability = np.exp(-abs(value))  # Higher stability for smaller values
                evaporation = 1.0 - np.exp(-abs(value) * 0.1)  # Evaporation rate
                
                cell_data = {
                    'active': abs(value) > self.config.pattern_threshold,
                    'quantum_properties': {
                        'coherence': float(coherence),
                        'time_reversal': float(time_reversal),
                        'spin': float(spin),
                        'stability': float(stability),
                        'evaporation': float(evaporation)
                    }
                }
                row.append(cell_data)
            grid.append(row)
        return grid
    
    def _load_template(self, template_name: str) -> str:
        """Load HTML template with framework-specific optimizations."""
        template_path = os.path.join(self.template_dir, f'{template_name}.html')
        if not os.path.exists(template_path):
            self._create_default_templates()
        with open(template_path, 'r') as f:
            return f.read()
    
    def _create_default_templates(self):
        """Create default HTML templates with framework optimizations."""
        # Main template
        main_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pattern Explorer</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="styles.css">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@3.12.0/dist/tf.min.js"></script>
        </head>
        <body>
            <div id="app"></div>
            <script src="app.js"></script>
        </body>
        </html>
        """
        
        # Styles template
        styles_template = """
        :root {
            --background: {{background}};
            --card: {{card}};
            --text: {{text}};
            --accent: {{accent}};
            --highlight: {{highlight}};
        }
        
        body {
            background: var(--background);
            color: var(--text);
            font-family: monospace;
            margin: 0;
            padding: 20px;
            overflow-x: hidden;
        }
        
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
            perspective: 1000px;
        }
        
        /* Additional styles will be added by the framework */
        """
        
        # JavaScript template
        js_template = """
        // Framework-specific optimizations
        const app = {
            state: {
                patterns: {{patterns}},
                currentView: 'both',
                selectedPatterns: [],
                zoomLevel: 1,
                rotation: 0
            },
            
            init() {
                this.setupThreeJS();
                this.setupTensorFlow();
                this.render();
            },
            
            setupThreeJS() {
                // Three.js setup for 3D visualization
            },
            
            setupTensorFlow() {
                // TensorFlow.js setup for pattern analysis
            },
            
            render() {
                // Framework-optimized rendering
            }
        };
        
        // Initialize app when DOM is ready
        document.addEventListener('DOMContentLoaded', () => app.init());
        """
        
        # Write templates
        with open(os.path.join(self.template_dir, 'main.html'), 'w') as f:
            f.write(main_template)
        with open(os.path.join(self.template_dir, 'styles.css'), 'w') as f:
            f.write(styles_template.format(**self.config.color_scheme))
        with open(os.path.join(self.template_dir, 'app.js'), 'w') as f:
            f.write(js_template)
    
    def generate_visualization(self, 
                             patterns: List[torch.Tensor],
                             mandalas: List[str],
                             concretions: List[str],
                             output_path: str = 'pattern_explorer.html') -> str:
        """Generate interactive visualization with framework optimizations."""
        # Prepare pattern data
        pattern_data = [self._prepare_pattern_data(p) for p in patterns]
        
        # Load and fill template
        template = self._load_template('main')
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write visualization files
        with open(output_path, 'w') as f:
            f.write(template)
        
        # Write pattern data
        with open(output_path.replace('.html', '_data.json'), 'w') as f:
            json.dump({
                'patterns': pattern_data,
                'mandalas': mandalas,
                'concretions': concretions
            }, f)
        
        return output_path

class PatternAnalyzer:
    """Analyzes patterns for visualization optimization."""
    
    def __init__(self):
        self.feature_weights = {
            'depth': 0.4,
            'complexity': 0.3,
            'harmony': 0.3
        }
    
    def analyze_pattern(self, pattern: torch.Tensor) -> Dict[str, float]:
        """Analyze pattern features for visualization optimization."""
        pattern_np = pattern.detach().cpu().numpy()
        return {
            'depth': float(pattern_np[2]) if len(pattern_np) > 2 else 0.0,
            'complexity': float(pattern_np[1]) if len(pattern_np) > 1 else 0.0,
            'harmony': float(pattern_np[3]) if len(pattern_np) > 3 else 0.0
        }
    
    def optimize_visualization(self, patterns: List[torch.Tensor]) -> Dict[str, Any]:
        """Optimize visualization parameters based on pattern analysis."""
        analyses = [self.analyze_pattern(p) for p in patterns]
        
        # Calculate optimal parameters
        avg_depth = np.mean([a['depth'] for a in analyses])
        avg_complexity = np.mean([a['complexity'] for a in analyses])
        avg_harmony = np.mean([a['harmony'] for a in analyses])
        
        return {
            'grid_size': max(4, min(8, int(avg_complexity * 8))),
            'pattern_threshold': max(0.2, min(0.4, avg_harmony)),
            'zoom_range': (0.5, 1.0 + avg_depth),
            'rotation_step': max(10, min(30, int(avg_complexity * 30)))
        }

class VectorDrivenVisualizer:
    """Generates vector-driven visual representations like mandalas and concretions."""

    def __init__(self, mandala_size: int = 21, concretion_size: int = 15):
        self.mandala_size = mandala_size  # Conceptual size, influences scaling
        self.concretion_size = concretion_size
        # ASCII symbols kept if old methods are somehow still used
        self.mandala_symbols = [' ', '.', ':', '-', '=', '+', '*', '#', '%', '@']
        self.concretion_symbols = ['o', '.', ':', '-', '>', '<', '^', 'v', '*']
        
        # For Pyglet shapes
        self.mandala_pyglet_shapes = []
        self.concretion_pyglet_shapes = [] # For later
        self.previous_driving_vector: Optional[torch.Tensor] = None # To track dv change
        self.debug_star: Optional[pyglet_shapes.Star] = None # For visual update diagnostic

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> tuple[int, int, int]:
        """Converts HSV color (all components in [0, 1]) to RGB (components in [0, 255])."""
        if s == 0.0:
            r = g = b = int(v * 255)
            return r, g, b
        i = int(h * 6.)
        f = (h * 6.) - i
        p = v * (1. - s)
        q = v * (1. - s * f)
        t = v * (1. - s * (1. - f))
        i %= 6
        if i == 0: r_float, g_float, b_float = v, t, p
        elif i == 1: r_float, g_float, b_float = q, v, p
        elif i == 2: r_float, g_float, b_float = p, v, t
        elif i == 3: r_float, g_float, b_float = p, q, v
        elif i == 4: r_float, g_float, b_float = t, p, v
        else: r_float, g_float, b_float = v, p, q # i == 5
        return int(r_float * 255), int(g_float * 255), int(b_float * 255)

    def _get_driving_vector(self, pattern: torch.Tensor, num_elements: int = 5) -> torch.Tensor:
        """Extracts or derives a driving vector from the pattern."""
        if pattern.numel() == 0:
            return torch.zeros(num_elements)
        
        # Use tanh to bring values into a somewhat predictable range [-1, 1]
        # Then scale to [0,1] for easier use in parameter mapping
        pattern_flat = torch.tanh(pattern.flatten()) * 0.5 + 0.5 

        if pattern_flat.numel() >= num_elements:
            return pattern_flat[:num_elements]
        else:
            # Repeat and slice if the pattern is too short
            return pattern_flat.repeat((num_elements // pattern_flat.numel()) + 1)[:num_elements]

    def create_vector_mandala(self, pattern: torch.Tensor) -> str:
        """Creates an ASCII mandala driven by the input pattern tensor."""
        dv = self._get_driving_vector(pattern, num_elements=5)

        # Map driving vector components to mandala parameters
        # Ensure values are in reasonable ranges
        num_segments = max(3, int(dv[0] * 7) + 3)  # e.g., 3 to 10 segments
        layers = max(2, int(dv[1] * (self.mandala_size / 4)) + 1) # e.g., 2 to ~6 layers
        symbol_offset = int(dv[2] * (len(self.mandala_symbols) - 5)) # Start symbol index
        hue_rotation_factor = dv[3] * 360  # For potential color mapping later, now affects symbol choice
        density = dv[4] * 0.5 + 0.3  # Base density 0.3 to 0.8

        grid = [[' ' for _ in range(self.mandala_size)] for _ in range(self.mandala_size)]
        center_x, center_y = self.mandala_size // 2, self.mandala_size // 2

        for l in range(1, layers + 1):
            radius = l * (center_x / layers) * 0.9 # Scale radius by number of layers
            points_in_layer = int(num_segments * l * density) # More points in outer, denser layers

            for i in range(points_in_layer):
                angle_rad = (2 * math.pi / points_in_layer) * i + (hue_rotation_factor * l /180 * math.pi) # Rotate layers
                
                x_offset = radius * math.cos(angle_rad)
                y_offset = radius * math.sin(angle_rad)
                
                x = center_x + int(x_offset)
                y = center_y + int(y_offset)

                if 0 <= x < self.mandala_size and 0 <= y < self.mandala_size:
                    symbol_index = (l + i + symbol_offset + int(hue_rotation_factor/36)) % len(self.mandala_symbols)
                    grid[y][x] = self.mandala_symbols[symbol_index]
        
        # Reflect to create symmetry (optional, can be driven by dv too)
        # For simplicity, basic reflection for now
        for r in range(self.mandala_size):
            for c in range(center_x):
                grid[r][self.mandala_size - 1 - c] = grid[r][c]
        for c in range(self.mandala_size):
            for r in range(center_y):
                 grid[self.mandala_size - 1 - r][c] = grid[r][c]

        return "\n".join("".join(row) for row in grid)

    def update_geometric_mandala_pyglet(self, 
                                     pattern: torch.Tensor, 
                                     batch: pyglet.graphics.Batch,
                                     group_foreground: Optional[pyglet.graphics.Group] = None,
                                     group_background: Optional[pyglet.graphics.Group] = None,
                                     window_width: int = 800, 
                                     window_height: int = 800,
                                     mandala_shape_bias: float = 0.0,
                                     overall_rotation_angle_deg: float = 0.0):
        """
        Updates or re-creates Pyglet shapes for a geometric mandala and adds them to the batch.
        Shapes are stored in self.mandala_pyglet_shapes.
        """
        # Clear existing shapes
        for shape in self.mandala_pyglet_shapes:
            shape.delete() 
        self.mandala_pyglet_shapes.clear()

        plot_center_x = window_width / 2
        plot_center_y = window_height / 2
        base_plot_radius = min(window_width, window_height) / 2.2

        error_occurred = False
        error_message = ''
        shapes_created = 0
        try:
            # --- MINIMAL EGG: Always-visible Easter egg for rendering test ---
            egg_width = min(window_width, window_height) * 0.25
            egg_height = egg_width * 1.3
            pastel_egg = pyglet_shapes.Ellipse(
                x=plot_center_x,
                y=plot_center_y,
                a=egg_width,
                b=egg_height,
                segments=32,
                color=(255, 230, 180),  # Pastel yellow
                batch=batch,
                group=group_foreground
            )
            self.mandala_pyglet_shapes.append(pastel_egg)
            logger.info(f"Created pastel egg at ({plot_center_x}, {plot_center_y}) size=({egg_width}, {egg_height})")
            shapes_created += 1
            # --- END MINIMAL EGG ---
        except Exception as e:
            logger.error(f"Error creating pastel egg: {e}", exc_info=True)
            error_occurred = True
            error_message = f"Egg error: {e}"
        try:
            # Add radial gradient lines
            num_radial_lines = 5  # Five-fold symmetry for origami
            for i in range(num_radial_lines):
                angle = (2 * math.pi * i) / num_radial_lines + math.radians(overall_rotation_angle_deg)
                end_x = plot_center_x + base_plot_radius * 1.5 * math.cos(angle)
                end_y = plot_center_y + base_plot_radius * 1.5 * math.sin(angle)
                for j in range(3):
                    try:
                        gradient_line = pyglet_shapes.Line(
                            x=plot_center_x,
                            y=plot_center_y,
                            x2=end_x * (0.8 + j * 0.1),
                            y2=end_y * (0.8 + j * 0.1),
                            color=(100, 100, 200, 30 - j * 10),
                            batch=batch,
                            group=group_background
                        )
                        self.mandala_pyglet_shapes.append(gradient_line)
                        logger.info(f"Created gradient line {i}-{j} from ({plot_center_x},{plot_center_y}) to ({end_x},{end_y})")
                        shapes_created += 1
                    except Exception as e:
                        logger.error(f"Error creating gradient line {i}-{j}: {e}", exc_info=True)
                        error_occurred = True
                        error_message = f"Line error: {e}"
        except Exception as e:
            logger.error(f"Error in radial lines block: {e}", exc_info=True)
            error_occurred = True
            error_message = f"Radial lines error: {e}"
        try:
            # Add origami-inspired planes
            num_planes = 5
            for i in range(num_planes):
                plane_radius = base_plot_radius * (1.0 + i * 0.15)
                plane_opacity = int(80 * (1.0 - i * 0.15))
                try:
                    gradient_circle = pyglet_shapes.Circle(
                        x=plot_center_x,
                        y=plot_center_y,
                        radius=plane_radius,
                        color=(50, 50, 100, plane_opacity),
                        batch=batch,
                        group=group_background
                    )
                    self.mandala_pyglet_shapes.append(gradient_circle)
                    logger.info(f"Created gradient circle {i} at ({plot_center_x},{plot_center_y}) r={plane_radius}")
                    shapes_created += 1
                except Exception as e:
                    logger.error(f"Error creating gradient circle {i}: {e}", exc_info=True)
                    error_occurred = True
                    error_message = f"Circle error: {e}"
                for j in range(5):
                    triangle_angle = (2 * math.pi * j) / 5 + math.radians(overall_rotation_angle_deg)
                    triangle_size = plane_radius * 0.2
                    center_x = plot_center_x + plane_radius * 0.7 * math.cos(triangle_angle)
                    center_y = plot_center_y + plane_radius * 0.7 * math.sin(triangle_angle)
                    try:
                        triangle = pyglet_shapes.Triangle(
                            x=center_x,
                            y=center_y - triangle_size / math.sqrt(3),
                            x2=center_x + triangle_size / 2,
                            y2=center_y + triangle_size / (2 * math.sqrt(3)),
                            x3=center_x - triangle_size / 2,
                            y3=center_y + triangle_size / (2 * math.sqrt(3)),
                            color=(100, 100, 200, plane_opacity),
                            batch=batch,
                            group=group_background
                        )
                        triangle.rotation = math.degrees(triangle_angle)
                        self.mandala_pyglet_shapes.append(triangle)
                        logger.info(f"Created triangle {i}-{j} at ({center_x},{center_y}) size={triangle_size}")
                        shapes_created += 1
                    except Exception as e:
                        logger.error(f"Error creating triangle {i}-{j}: {e}", exc_info=True)
                        error_occurred = True
                        error_message = f"Triangle error: {e}"
        except Exception as e:
            logger.error(f"Error in origami planes block: {e}", exc_info=True)
            error_occurred = True
            error_message = f"Planes error: {e}"
        logger.info(f"Total shapes created this frame: {shapes_created}")
        if error_occurred and batch is not None:
            # Display a visible error message in the window
            try:
                error_label = pyglet.text.Label(
                    text=error_message,
                    font_name='Arial',
                    font_size=18,
                    x=plot_center_x,
                    y=window_height * 0.1,
                    anchor_x='center',
                    anchor_y='center',
                    color=(255, 0, 0, 255),
                    batch=batch,
                    group=group_foreground
                )
                self.mandala_pyglet_shapes.append(error_label)
            except Exception as e:
                logger.error(f"Error displaying error label: {e}", exc_info=True)

        # Get driving vector and continue with existing mandala generation
        dv_elements = 10
        dv = self._get_driving_vector(pattern, num_elements=dv_elements)
        # Log the driving vector
        logger.info(f"Driving Vector (dv): {[f'{x:.3f}' for x in dv.tolist()]}")

        # Track and log change in driving_vector
        if self.previous_driving_vector is not None and \
           isinstance(self.previous_driving_vector, torch.Tensor) and \
           self.previous_driving_vector.shape == dv.shape and \
           self.previous_driving_vector.device == dv.device:
            dv_change_magnitude = torch.norm(dv - self.previous_driving_vector).item()
            logger.info(f"Driving Vector Change (L2 Norm): {dv_change_magnitude:.4f}")
        else:
            if self.previous_driving_vector is None:
                logger.info("Driving Vector: Initialized (no previous dv to compare).")
            else:
                logger.warning("Skipping dv change calculation due to shape/device mismatch or invalid type.")
        
        self.previous_driving_vector = dv.clone()

        # Map driving vector components to mandala parameters
        # dv[0] for layers, dv[8] for size modulation
        dv0_raw = dv[0].item()
        dv8_raw = dv[8].item() # Used for size_modulation_factor AND now layer complexity modulation

        # "Bent frame" detour: dv[8] (size tendency) also influences layer complexity range
        layer_dynamic_range_modulator = 2.0 + 8.0 * dv8_raw # Modulator from 2.0 to 10.0 (was 2.0 + 3.0 * dv8_raw)
        num_layers = max(2, int(dv0_raw * layer_dynamic_range_modulator) + 2)
        
        segments_per_layer_base = max(3, int(dv[1].item() * 17) + 3) # 3 to 20 segments (was * 9)
        
        start_hue = dv[2].item() # 0-1 for hue
        hue_increment_per_layer = dv[3].item() * 0.8 - 0.4 # Range -0.4 to 0.4 (was * 0.2 - 0.1)
        saturation_base = dv[4].item() * 0.4 + 0.6 # 0.6 to 1.0
        value_base = dv[5].item() * 0.3 + 0.5 # Brightness: 0.5 to 0.8
        alpha_base = dv[6].item() * 0.3 + 0.4 # Opacity: 0.4 to 0.7 (scaled to 0-255 later)

        shape_type_factor = dv[7].item() # Determines shape type
        size_modulation_factor = dv8_raw * 1.5 + 0.25 # Range 0.25 to 1.75 (was * 0.5 + 0.75)
        rotation_pattern_factor = dv[9].item() # For rotational effects

        # Log some key derived parameters
        logger.info(f"Derived Params: Layers={num_layers}, Hue={start_hue:.3f}, ShapeFactor={shape_type_factor:.3f}")

        for l_idx in range(num_layers):
            layer_radius_norm = (l_idx + 1) / num_layers
            # Modulated radius for the current layer
            radius = layer_radius_norm * base_plot_radius * size_modulation_factor
            
            current_segments = segments_per_layer_base + int(l_idx * dv[1].item() * 1.5) # More segments on outer layers
            if current_segments <= 0: continue

            segment_angle_deg = 360.0 / current_segments
            
            layer_hue = (start_hue + l_idx * hue_increment_per_layer) % 1.0
            layer_saturation = saturation_base * (0.9 + layer_radius_norm * 0.1)  # Increased base saturation
            layer_saturation = min(1.0, max(0.0, layer_saturation))
            layer_value = value_base * (1.0 - layer_radius_norm * 0.3)  # Adjusted value range
            layer_value = min(1.0, max(0.0, layer_value))
            
            rgb_color = self._hsv_to_rgb(layer_hue, layer_saturation, layer_value)
            # Pyglet opacity for shapes is 0-255
            opacity = int((alpha_base * (1.0 - layer_radius_norm * 0.4)) * 255)  # Adjusted opacity range
            opacity = min(255, max(0, opacity))

            for s_idx in range(current_segments):
                angle_offset_deg = rotation_pattern_factor * l_idx * 90 
                # Apply the overall_rotation_angle_deg here
                current_angle_rad = math.radians(s_idx * segment_angle_deg + angle_offset_deg + overall_rotation_angle_deg)
                
                # Position for the center of the element
                element_center_x = plot_center_x + radius * math.cos(current_angle_rad)
                element_center_y = plot_center_y + radius * math.sin(current_angle_rad)

                # Base size for elements in this layer, amplified
                element_size_base = (base_plot_radius / (num_layers * 3.5)) * (0.1 + dv[s_idx % dv_elements].item() * 1.9) # Range 0.1 to 2.0 multiplier (was 0.5 + dv_val * 0.8)
                element_size = max(1, element_size_base) # Ensure minimum size, changed from max(2,...) to allow smaller elements if base is small

                pyglet_shape = None
                current_group = group_foreground

                # Adjust thresholds based on mandala_shape_bias
                # A positive bias leans towards more complex shapes (triangles), negative towards simpler (circles).
                # The effect of the bias is scaled (e.g., by 0.1) to make it a gentle nudge.
                threshold_adjustment = mandala_shape_bias * 0.1
                
                # Initial thresholds for a three-way split (0.33, 0.66)
                base_threshold1 = 1/3
                base_threshold2 = 2/3

                adjusted_threshold1 = max(0.01, min(base_threshold1 - threshold_adjustment, 0.98))
                adjusted_threshold2 = max(adjusted_threshold1 + 0.01, min(base_threshold2 - threshold_adjustment, 0.99))
                
                # Ensure threshold2 is always greater than threshold1
                if adjusted_threshold2 <= adjusted_threshold1:
                    adjusted_threshold2 = adjusted_threshold1 + 0.01 # Maintain a small gap
                    # And re-clamp threshold2 just in case
                    adjusted_threshold2 = min(adjusted_threshold2, 0.99)

                current_shape_factor = shape_type_factor # dv[7].item()

                if current_shape_factor < adjusted_threshold1: # Circles
                    pyglet_shape = pyglet_shapes.Circle(
                        x=element_center_x, y=element_center_y, radius=element_size,
                        color=rgb_color, batch=batch, group=current_group
                    )
                elif current_shape_factor < adjusted_threshold2: # Rectangles
                    # Rectangles anchored at bottom-left, so adjust x,y
                    pyglet_shape = pyglet_shapes.Rectangle(
                        x=element_center_x - element_size / 2, 
                        y=element_center_y - element_size / 2,
                        width=element_size, height=element_size,
                        color=rgb_color, batch=batch, group=current_group
                    )
                    # Rotation for rectangles (and other shapes that support it)
                    if hasattr(pyglet_shape, 'rotation'):
                         pyglet_shape.rotation = dv[(s_idx+1) % dv_elements].item() * 360
                else: # Triangles (equilateral for simplicity)
                    pyglet_shape = pyglet_shapes.Triangle(
                        x=element_center_x, y=element_center_y - element_size / math.sqrt(3),
                        x2=element_center_x + element_size / 2, y2=element_center_y + element_size / (2 * math.sqrt(3)),
                        x3=element_center_x - element_size / 2, y3=element_center_y + element_size / (2 * math.sqrt(3)),
                        color=rgb_color, batch=batch, group=current_group
                    )
                    if hasattr(pyglet_shape, 'rotation'):
                        pyglet_shape.rotation = dv[(s_idx+2) % dv_elements].item() * 360
                
                if pyglet_shape:
                    pyglet_shape.opacity = opacity
                    self.mandala_pyglet_shapes.append(pyglet_shape)

    def create_vector_concretion(self, pattern: torch.Tensor) -> str:
        """Creates an ASCII concretion (symbolic growth) driven by the pattern."""
        dv = self._get_driving_vector(pattern, num_elements=5)

        # Map driving vector components to concretion parameters
        base_symbol_idx = int(dv[0] * (len(self.concretion_symbols)-1))
        growth_iterations = max(3, int(dv[1] * (self.concretion_size / 2))) # e.g., 3 to ~7 iterations
        angle_step_rad = dv[2] * math.pi / 2  # 0 to pi/2 radians step
        scale_factor_mod = dv[3] * 0.5 + 0.8 # 0.8 to 1.3
        symbol_variation_chance = dv[4] # 0 to 1

        grid = [[' ' for _ in range(self.concretion_size)] for _ in range(self.concretion_size)]
        center_x, center_y = self.concretion_size // 2, self.concretion_size // 2

        current_pos = [(center_x, center_y)]
        current_angle = 0.0
        current_scale = 1.0 

        grid[center_y][center_x] = self.concretion_symbols[base_symbol_idx]

        for i in range(growth_iterations):
            new_positions = []
            current_scale *= scale_factor_mod
            if current_scale < 0.5 : current_scale = 0.5 # Min scale
            if current_scale > 2.0 : current_scale = 2.0 # Max scale

            for x_orig, y_orig in current_pos:
                num_branches = max(1, int(dv[1] * 2) + 1) # 1 to 3 branches
                for branch in range(num_branches):
                    branch_angle_offset = (math.pi / 4) * (branch - num_branches // 2) # Spread branches
                    angle = current_angle + angle_step_rad * i + branch_angle_offset
                    
                    # Distance scales with iteration and overall scale_factor_mod
                    distance = (i + 1) * 0.5 * current_scale 

                    x_new = x_orig + int(distance * math.cos(angle))
                    y_new = y_orig + int(distance * math.sin(angle))

                    if 0 <= x_new < self.concretion_size and 0 <= y_new < self.concretion_size:
                        if grid[y_new][x_new] == ' ': # Only place if empty
                            symbol_idx_to_use = base_symbol_idx
                            if torch.rand(1).item() < symbol_variation_chance:
                                symbol_idx_to_use = (base_symbol_idx + i + branch) % len(self.concretion_symbols)
                            grid[y_new][x_new] = self.concretion_symbols[symbol_idx_to_use]
                            new_positions.append((x_new, y_new))
            
            current_pos = list(set(new_positions)) # Unique new positions become origins for next step
            if not current_pos: # Stop if no new positions were added
                break
            current_angle += angle_step_rad / 2 # Slightly alter global angle each iteration

        return "\n".join("".join(row) for row in grid)

class QuantumGravityVisualizer:
    """Visualizes quantum gravity ≠ statistical mechanics using complexity and connectome graphs."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.complexity_graph = None
        self.connectome_matrix = None
        self.chaos_state = torch.zeros(3)
        self.quantum_states = []
        self.statistical_states = []
        self.spin_states = []  # Track spin states for each quantum entity
        self.orbital_params = []  # Track orbital parameters
        self.glsl_shader = None  # Store GLSL shader code
        self.jitter_matrix = None  # Store Jitter matrix data
        
    def update_visualization(self, 
                           pattern: torch.Tensor,
                           batch: pyglet.graphics.Batch,
                           group_foreground: Optional[pyglet.graphics.Group] = None,
                           group_background: Optional[pyglet.graphics.Group] = None,
                           window_width: int = 800,
                           window_height: int = 800):
        """Update visualization with quantum gravity effects and orbital mechanics."""
        # Calculate complexity and update quantum states
        complexity = self._calculate_complexity(pattern)
        self._create_quantum_states(pattern)
        self._create_statistical_states(pattern)
        self._evolve_chaos_state()
        
        # Update spin and orbital mechanics
        self._update_spin_states(pattern)
        self._update_orbital_mechanics()
        
        # Generate GLSL shader code
        self._generate_glsl_shader()
        
        # Update Jitter matrix
        self._update_jitter_matrix()
        
        # Visualize the difference between quantum and statistical states
        self._visualize_difference(batch, group_foreground, group_background, window_width, window_height)
    
    def _calculate_complexity(self, pattern: torch.Tensor) -> torch.Tensor:
        """Calculates complexity measure from pattern tensor."""
        # Use fractal dimension-like measure
        pattern_np = pattern.detach().cpu().numpy()
        complexity = np.zeros_like(pattern_np)
        
        for i in range(len(pattern_np)):
            # Calculate local complexity using sliding window
            window_size = min(10, len(pattern_np) - i)
            if window_size > 0:
                window = pattern_np[i:i+window_size]
                complexity[i] = np.std(window) * np.mean(np.abs(np.diff(window)))
        
        return torch.from_numpy(complexity)
    
    def _generate_complexity_graph(self, complexity: torch.Tensor) -> np.ndarray:
        """Generates a graph representation of complexity."""
        # Create adjacency matrix based on complexity correlations
        n = len(complexity)
        graph = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Use complexity correlation as edge weight
                    graph[i,j] = torch.cosine_similarity(
                        complexity[i].unsqueeze(0),
                        complexity[j].unsqueeze(0)
                    ).item()
        
        return graph
    
    def _update_connectome(self, pattern: torch.Tensor) -> np.ndarray:
        """Updates the connectome matrix based on pattern."""
        # Create connectome matrix using pattern correlations
        pattern_np = pattern.detach().cpu().numpy()
        n = len(pattern_np)
        connectome = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Use pattern correlation as connection strength
                    connectome[i,j] = np.corrcoef(pattern_np[i], pattern_np[j])[0,1]
        
        return connectome
    
    def _evolve_chaos_state(self):
        """Evolves the chaos state from 'i' to 'iii'."""
        if self.chaos_state[0] == 0.0:
            self.chaos_state = torch.tensor([0.0, 0.0, 1.0])
        elif self.chaos_state[1] == 0.0:
            self.chaos_state = torch.tensor([0.0, 1.0, 0.0])
        elif self.chaos_state[2] == 0.0:
            self.chaos_state = torch.tensor([1.0, 0.0, 0.0])
    
    def _create_quantum_states(self, pattern: torch.Tensor):
        """Creates quantum states from pattern."""
        try:
            # Use pattern to generate quantum-like states
            pattern_np = pattern.detach().cpu().numpy()
            self.quantum_states = []
            
            for i in range(0, len(pattern_np), 3):
                try:
                    if i + 2 < len(pattern_np):
                        # Ensure we have valid position data
                        position = pattern_np[i:i+3]
                        if len(position) < 3:
                            position = np.pad(position, (0, 3 - len(position)))
                        
                        # Calculate momentum using gradient
                        momentum = np.gradient(position)
                        if len(momentum) < 3:
                            momentum = np.pad(momentum, (0, 3 - len(momentum)))
                        
                        # Calculate phase using FFT
                        phase = np.angle(np.fft.fft(position))
                        if len(phase) < 3:
                            phase = np.pad(phase, (0, 3 - len(phase)))
                        
                        state = {
                            'position': torch.tensor(position, dtype=torch.float32),
                            'momentum': torch.tensor(momentum, dtype=torch.float32),
                            'phase': torch.tensor(phase, dtype=torch.float32)
                        }
                        self.quantum_states.append(state)
                except Exception as e:
                    logger.error(f"Error creating quantum state at index {i}: {e}")
                    # Add a default state if creation fails
                    self.quantum_states.append({
                        'position': torch.zeros(3, dtype=torch.float32),
                        'momentum': torch.zeros(3, dtype=torch.float32),
                        'phase': torch.zeros(3, dtype=torch.float32)
                    })
            
            # Ensure we have at least one state
            if not self.quantum_states:
                logger.warning("No quantum states created, adding default state")
                self.quantum_states.append({
                    'position': torch.zeros(3, dtype=torch.float32),
                    'momentum': torch.zeros(3, dtype=torch.float32),
                    'phase': torch.zeros(3, dtype=torch.float32)
                })
                
        except Exception as e:
            logger.error(f"Error in quantum state creation: {e}", exc_info=True)
            # Create a default state if everything fails
            self.quantum_states = [{
                'position': torch.zeros(3, dtype=torch.float32),
                'momentum': torch.zeros(3, dtype=torch.float32),
                'phase': torch.zeros(3, dtype=torch.float32)
            }]
    
    def _create_statistical_states(self, pattern: torch.Tensor):
        """Creates statistical mechanics states from pattern."""
        # Use pattern to generate statistical mechanics-like states
        pattern_np = pattern.detach().cpu().numpy()
        self.statistical_states = []
        
        for i in range(0, len(pattern_np), 3):
            if i + 2 < len(pattern_np):
                state = {
                    'position': pattern_np[i:i+3],
                    'velocity': np.gradient(pattern_np[i:i+3]),
                    'temperature': np.std(pattern_np[i:i+3])
                }
                self.statistical_states.append(state)
    
    def _visualize_difference(self, batch, group_foreground, group_background, window_width, window_height):
        """Visualizes the difference between quantum gravity and statistical mechanics."""
        center_x = window_width / 2
        center_y = window_height / 2
        radius = min(window_width, window_height) / 3
        
        # Draw quantum gravity side
        for i, state in enumerate(self.quantum_states):
            angle = 2 * np.pi * i / len(self.quantum_states)
            x = center_x + radius * np.cos(angle)
            y = center_y + radius * np.sin(angle)
            
            # Create quantum state visualization
            quantum_circle = pyglet_shapes.Circle(
                x=x, y=y, radius=10,
                color=(100, 200, 255, 200),  # Blue-ish
                batch=batch,
                group=group_foreground
            )
            self.shapes.append(quantum_circle)
        
        # Draw statistical mechanics side
        for i, state in enumerate(self.statistical_states):
            angle = 2 * np.pi * i / len(self.statistical_states)
            x = center_x - radius * np.cos(angle)
            y = center_y - radius * np.sin(angle)
            
            # Create statistical state visualization
            stat_rect = pyglet_shapes.Rectangle(
                x=x-10, y=y-10, width=20, height=20,
                color=(255, 100, 100, 200),  # Red-ish
                batch=batch,
                group=group_foreground
            )
            self.shapes.append(stat_rect)
        
        # Draw chaos state
        chaos_text = pyglet.text.Label(
            text=f"Chaos: {self.chaos_state.tolist()}",
            font_name='Arial',
            font_size=36,
            x=center_x,
            y=center_y,
            anchor_x='center',
            anchor_y='center',
            color=(255, 255, 255, 255),
            batch=batch,
            group=group_foreground
        )
        self.shapes.append(chaos_text)
        
        # Draw connections
        for i in range(len(self.quantum_states)):
            for j in range(len(self.statistical_states)):
                if self.connectome_matrix[i,j] > 0.5:  # Only draw strong connections
                    q_angle = 2 * np.pi * i / len(self.quantum_states)
                    s_angle = 2 * np.pi * j / len(self.statistical_states)
                    
                    q_x = center_x + radius * np.cos(q_angle)
                    q_y = center_y + radius * np.sin(q_angle)
                    s_x = center_x - radius * np.cos(s_angle)
                    s_y = center_y - radius * np.sin(s_angle)
                    
                    connection = pyglet_shapes.Line(
                        x=q_x, y=q_y,
                        x2=s_x, y2=s_y,
                        color=(200, 200, 200, 100),
                        batch=batch,
                        group=group_background
                    )
                    self.shapes.append(connection)

    def _update_spin_states(self, pattern: torch.Tensor):
        """Update spin states based on pattern complexity."""
        if not self.spin_states:
            # Initialize spin states if empty
            num_states = len(self.quantum_states)
            self.spin_states = [{
                'angular_momentum': torch.zeros(3),
                'spin_axis': torch.tensor([0.0, 1.0, 0.0]),
                'spin_rate': np.random.uniform(0.1, 2.0),
                'precession': np.random.uniform(0.01, 0.1)
            } for _ in range(num_states)]
        
        # Update spin states based on pattern
        for i, state in enumerate(self.spin_states):
            # Extract relevant pattern components for spin
            pattern_slice = pattern[i % len(pattern):(i + 3) % len(pattern)]
            if len(pattern_slice) < 3:
                pattern_slice = torch.cat([pattern_slice, torch.zeros(3 - len(pattern_slice))])
            
            # Update angular momentum
            state['angular_momentum'] = pattern_slice[:3]
            
            # Update spin axis based on pattern complexity
            complexity = torch.norm(pattern_slice)
            state['spin_axis'] = torch.nn.functional.normalize(
                state['spin_axis'] + complexity * torch.randn(3),
                dim=0
            )
            
            # Update spin rate and precession
            state['spin_rate'] *= (1.0 + 0.1 * torch.sin(complexity))
            state['precession'] *= (1.0 + 0.05 * torch.cos(complexity))
    
    def _update_orbital_mechanics(self):
        """Update orbital parameters for quantum states."""
        try:
            if not self.orbital_params:
                # Initialize orbital parameters if empty
                num_states = len(self.quantum_states)
                self.orbital_params = [{
                    'semi_major_axis': np.random.uniform(1.0, 5.0),
                    'eccentricity': np.random.uniform(0.0, 0.8),
                    'inclination': np.random.uniform(0, np.pi/4),
                    'orbital_period': np.random.uniform(2.0, 10.0),
                    'phase': np.random.uniform(0, 2*np.pi)
                } for _ in range(num_states)]
            
            # Update orbital parameters based on quantum states
            for i, params in enumerate(self.orbital_params):
                if i < len(self.quantum_states):
                    quantum_state = self.quantum_states[i]
                    # Convert quantum state position to tensor if it's not already
                    if isinstance(quantum_state['position'], (list, np.ndarray)):
                        position_tensor = torch.tensor(quantum_state['position'], dtype=torch.float32)
                    else:
                        position_tensor = quantum_state['position']
                    
                    # Calculate complexity using position tensor
                    complexity = torch.norm(position_tensor)
                    
                    # Update orbital parameters with error checking
                    try:
                        params['semi_major_axis'] *= (1.0 + 0.1 * torch.sin(complexity).item())
                        params['eccentricity'] = np.clip(
                            params['eccentricity'] + 0.1 * torch.cos(complexity).item(),
                            0.0, 0.9
                        )
                        params['inclination'] += 0.1 * torch.sin(complexity).item()
                        params['orbital_period'] *= (1.0 + 0.05 * torch.cos(complexity).item())
                        params['phase'] += 0.1 * complexity.item()
                    except Exception as e:
                        logger.error(f"Error updating orbital parameters for state {i}: {e}")
                        # Use safe fallback values
                        params['semi_major_axis'] = 3.0
                        params['eccentricity'] = 0.5
                        params['inclination'] = np.pi/8
                        params['orbital_period'] = 5.0
                        params['phase'] = 0.0
                        
        except Exception as e:
            logger.error(f"Error in orbital mechanics update: {e}", exc_info=True)
            # Initialize with safe default values if something goes wrong
            if not self.orbital_params:
                self.orbital_params = [{
                    'semi_major_axis': 3.0,
                    'eccentricity': 0.5,
                    'inclination': np.pi/8,
                    'orbital_period': 5.0,
                    'phase': 0.0
                } for _ in range(max(1, len(self.quantum_states)))]
    
    def _generate_glsl_shader(self):
        """Generate GLSL shader code for visualization."""
        self.glsl_shader = """
        #version 330 core
        
        uniform float time;
        uniform vec2 resolution;
        uniform sampler2D quantum_states;
        uniform sampler2D spin_states;
        
        out vec4 fragColor;
        
        // Quantum state structure
        struct QuantumState {
            vec3 position;
            vec3 velocity;
            float energy;
        };
        
        // Spin state structure
        struct SpinState {
            vec3 angular_momentum;
            vec3 spin_axis;
            float spin_rate;
            float precession;
        };
        
        // Orbital parameters
        struct OrbitalParams {
            float semi_major_axis;
            float eccentricity;
            float inclination;
            float orbital_period;
            float phase;
        };
        
        // Calculate orbital position
        vec3 calculate_orbital_position(OrbitalParams params, float time) {
            float angle = 2.0 * 3.14159 * (time / params.orbital_period + params.phase);
            float r = params.semi_major_axis * (1.0 - params.eccentricity * params.eccentricity) /
                     (1.0 + params.eccentricity * cos(angle));
            
            vec3 position;
            position.x = r * cos(angle);
            position.y = r * sin(angle) * cos(params.inclination);
            position.z = r * sin(angle) * sin(params.inclination);
            
            return position;
        }
        
        // Calculate spin transformation
        mat3 calculate_spin_matrix(SpinState spin, float time) {
            float spin_angle = spin.spin_rate * time;
            float precession_angle = spin.precession * time;
            
            mat3 spin_matrix = mat3(
                cos(spin_angle), -sin(spin_angle), 0.0,
                sin(spin_angle), cos(spin_angle), 0.0,
                0.0, 0.0, 1.0
            );
            
            mat3 precession_matrix = mat3(
                cos(precession_angle), 0.0, -sin(precession_angle),
                0.0, 1.0, 0.0,
                sin(precession_angle), 0.0, cos(precession_angle)
            );
            
            return precession_matrix * spin_matrix;
        }
        
        void main() {
            vec2 uv = gl_FragCoord.xy / resolution;
            
            // Sample quantum and spin states
            QuantumState q_state;
            SpinState s_state;
            
            // Calculate final position with orbital and spin effects
            vec3 orbital_pos = calculate_orbital_position(orbital_params, time);
            mat3 spin_matrix = calculate_spin_matrix(s_state, time);
            vec3 final_pos = spin_matrix * orbital_pos;
            
            // Calculate color based on quantum state energy
            vec3 color = vec3(0.5 + 0.5 * sin(q_state.energy * time),
                            0.5 + 0.5 * cos(s_state.spin_rate * time),
                            0.5 + 0.5 * sin(s_state.precession * time));
            
            fragColor = vec4(color, 1.0);
        }
        """
    
    def _update_jitter_matrix(self):
        """Update Jitter matrix for Max/MSP/Jitter compatibility."""
        num_states = len(self.quantum_states)
        matrix_size = int(np.ceil(np.sqrt(num_states)))
        self.jitter_matrix = np.zeros((matrix_size, matrix_size, 4))
        
        for i, state in enumerate(self.quantum_states):
            row = i // matrix_size
            col = i % matrix_size
            
            # Convert quantum state to RGBA values
            self.jitter_matrix[row, col, 0] = float(state[0])  # R
            self.jitter_matrix[row, col, 1] = float(state[1])  # G
            self.jitter_matrix[row, col, 2] = float(state[2])  # B
            self.jitter_matrix[row, col, 3] = 1.0  # A
    
    def get_glsl_shader(self) -> str:
        """Get the current GLSL shader code."""
        return self.glsl_shader
    
    def get_jitter_matrix(self) -> np.ndarray:
        """Get the current Jitter matrix data."""
        return self.jitter_matrix
    
    def get_orbital_data(self) -> List[Dict]:
        """Get current orbital parameters."""
        return self.orbital_params
    
    def get_spin_data(self) -> List[Dict]:
        """Get current spin states."""
        return self.spin_states

# Example Usage (for testing, to be removed or placed in a main block):
if __name__ == '__main__':
    test_pattern = torch.randn(20) # Example pattern tensor
    visualizer = VectorDrivenVisualizer(mandala_size=25, concretion_size=25)
    
    print("Vector-Driven Mandala:")
    mandala_art = visualizer.create_vector_mandala(test_pattern)
    print(mandala_art)
    
    print("\nVector-Driven Concretion:")
    concretion_art = visualizer.create_vector_concretion(test_pattern)
    print(concretion_art) 